"""
OCR 서비스 모듈

주요 기능:
1. OCR 작업 처리
2. 비동기 작업 관리
3. 결과 저장 및 조회
"""

import os
import uuid
from typing import Dict, Any, Optional, List, Union
from sqlalchemy.orm import Session

from shared.models import Document, ProcessingJob, ExtractedData
from shared.constants import DocumentStatus, JobStatus
from shared.exceptions import OCREngineError, ResourceNotFoundError
from shared.logger import log_info, log_error, log_audit
from ocr_engines.base import OCREngineFactory, OCRResult
from ocr_engines.postprocessor import OCRPostProcessor

# OCR 엔진 임포트 - 동적 등록을 위해 필요
import ocr_engines.tesseract
import ocr_engines.mistral_ocr


class OCRService:
    """OCR 서비스 클래스"""
    
    def __init__(self, engine_name: str = "tesseract", config: Optional[Dict[str, Any]] = None):
        """
        OCR 서비스 초기화
        
        Args:
            engine_name: OCR 엔진 이름
            config: OCR 엔진 설정
        """
        self.engine_name = engine_name
        self.config = config or {}
        self.engine = OCREngineFactory.create(engine_name, config)
        self.postprocessor = OCRPostProcessor(self.config.get("postprocessor", {}))
    
    def process_document(self, db: Session, document_id: uuid.UUID, job_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """
        문서 OCR 처리
        
        Args:
            db: 데이터베이스 세션
            document_id: 문서 ID
            job_id: 작업 ID (선택 사항)
            
        Returns:
            Dict[str, Any]: OCR 처리 결과
            
        Raises:
            ResourceNotFoundError: 문서를 찾을 수 없는 경우
            OCREngineError: OCR 처리 중 오류 발생 시
        """
        # 문서 조회
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ResourceNotFoundError(message=f"문서를 찾을 수 없습니다: {document_id}")
        
        # 작업 조회 또는 생성
        job = None
        if job_id:
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
            if not job:
                raise ResourceNotFoundError(message=f"작업을 찾을 수 없습니다: {job_id}")
        else:
            # 새 작업 생성
            job = ProcessingJob(
                document_id=document_id,
                job_type="ocr",
                status=JobStatus.PENDING,
                parameters={"engine": self.engine_name}
            )
            db.add(job)
            db.commit()
            db.refresh(job)
        
        try:
            # 작업 상태 업데이트
            job.status = JobStatus.STARTED
            job.started_at = None  # 자동 설정됨
            db.commit()
            
            # 문서 상태 업데이트
            document.status = DocumentStatus.PROCESSING
            db.commit()
            
            # OCR 처리
            log_info(f"OCR 처리 시작: 문서 {document_id}, 작업 {job.id}")
            ocr_results = self.engine.process_file(document.file_path)
            
            # 결과 후처리
            processed_result = self.postprocessor.process(ocr_results)
            
            # 페이지 수 업데이트
            document.page_count = len(ocr_results)
            
            # 추출 데이터 저장
            self._save_extracted_data(db, document_id, processed_result)
            
            # 작업 완료 처리
            job.status = JobStatus.SUCCESS
            job.result = {
                "page_count": document.page_count,
                "confidence": processed_result["confidence"],
                "engine": self.engine_name
            }
            db.commit()
            
            # 문서 상태 업데이트
            document.status = DocumentStatus.COMPLETED
            document.processed_date = None  # 자동 설정됨
            db.commit()
            
            log_info(f"OCR 처리 완료: 문서 {document_id}, 작업 {job.id}")
            
            return {
                "document_id": str(document_id),
                "job_id": str(job.id),
                "status": "success",
                "result": processed_result
            }
        
        except Exception as e:
            # 오류 처리
            log_error(f"OCR 처리 실패: 문서 {document_id}, 작업 {job.id}, 오류: {str(e)}", exc_info=True)
            
            # 작업 실패 처리
            job.status = JobStatus.FAILURE
            job.error_message = str(e)
            db.commit()
            
            # 문서 상태 업데이트
            document.status = DocumentStatus.FAILED
            db.commit()
            
            if isinstance(e, OCREngineError):
                raise e
            else:
                raise OCREngineError(
                    message=f"OCR 처리 중 오류가 발생했습니다: {str(e)}",
                    details={"document_id": str(document_id), "job_id": str(job.id)}
                )
    
    def _save_extracted_data(self, db: Session, document_id: uuid.UUID, processed_result: Dict[str, Any]) -> None:
        """
        추출 데이터 저장
        
        Args:
            db: 데이터베이스 세션
            document_id: 문서 ID
            processed_result: 처리된 OCR 결과
        """
        # 전체 텍스트 저장
        text_data = ExtractedData(
            document_id=document_id,
            field_name="full_text",
            field_value=processed_result["text"],
            field_type="text",
            confidence_score=processed_result["confidence"],
            extraction_method="ocr"
        )
        db.add(text_data)
        
        # 구조화된 데이터 저장
        if "structured_data" in processed_result:
            for category, items in processed_result["structured_data"].items():
                if isinstance(items, dict):
                    # 개인정보 등 딕셔너리 형태의 데이터
                    for field, value in items.items():
                        if isinstance(value, list):
                            # 리스트 형태의 값 (전화번호, 이메일 등)
                            for i, item in enumerate(value):
                                field_data = ExtractedData(
                                    document_id=document_id,
                                    field_name=f"{category}_{field}_{i+1}",
                                    field_value=str(item),
                                    field_type="text",
                                    confidence_score=processed_result["confidence"],
                                    extraction_method="ocr"
                                )
                                db.add(field_data)
                        else:
                            # 단일 값
                            field_data = ExtractedData(
                                document_id=document_id,
                                field_name=f"{category}_{field}",
                                field_value=str(value),
                                field_type="text",
                                confidence_score=processed_result["confidence"],
                                extraction_method="ocr"
                            )
                            db.add(field_data)
                elif isinstance(items, list):
                    # 날짜, 금액 등 리스트 형태의 데이터
                    for i, item in enumerate(items):
                        if isinstance(item, dict):
                            # 딕셔너리 형태의 항목 (금액 등)
                            for field, value in item.items():
                                field_data = ExtractedData(
                                    document_id=document_id,
                                    field_name=f"{category}_{i+1}_{field}",
                                    field_value=str(value),
                                    field_type="text",
                                    confidence_score=processed_result["confidence"],
                                    extraction_method="ocr"
                                )
                                db.add(field_data)
                        else:
                            # 단일 값 (날짜 등)
                            field_data = ExtractedData(
                                document_id=document_id,
                                field_name=f"{category}_{i+1}",
                                field_value=str(item),
                                field_type="text",
                                confidence_score=processed_result["confidence"],
                                extraction_method="ocr"
                            )
                            db.add(field_data)
        
        db.commit()
    
    def get_available_engines(self) -> List[str]:
        """
        사용 가능한 OCR 엔진 목록 조회
        
        Returns:
            List[str]: 엔진 이름 목록
        """
        return OCREngineFactory.get_available_engines()
    
    def get_document_ocr_results(self, db: Session, document_id: uuid.UUID) -> Dict[str, Any]:
        """
        문서 OCR 결과 조회
        
        Args:
            db: 데이터베이스 세션
            document_id: 문서 ID
            
        Returns:
            Dict[str, Any]: OCR 결과
            
        Raises:
            ResourceNotFoundError: 문서를 찾을 수 없는 경우
        """
        # 문서 조회
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ResourceNotFoundError(message=f"문서를 찾을 수 없습니다: {document_id}")
        
        # 추출 데이터 조회
        extracted_data = db.query(ExtractedData).filter(
            ExtractedData.document_id == document_id
        ).all()
        
        if not extracted_data:
            return {
                "document_id": str(document_id),
                "status": "not_processed",
                "message": "OCR 처리 결과가 없습니다."
            }
        
        # 전체 텍스트 조회
        full_text = next(
            (data.field_value for data in extracted_data if data.field_name == "full_text"),
            None
        )
        
        # 구조화된 데이터 구성
        structured_data = {}
        for data in extracted_data:
            if data.field_name != "full_text":
                field_parts = data.field_name.split("_")
                category = field_parts[0]
                
                if category not in structured_data:
                    structured_data[category] = {}
                
                if len(field_parts) == 2:
                    # category_field
                    structured_data[category][field_parts[1]] = data.field_value
                elif len(field_parts) == 3:
                    # category_field_index 또는 category_index_field
                    if field_parts[1].isdigit():
                        # category_index_field
                        index = int(field_parts[1])
                        field = field_parts[2]
                        
                        if isinstance(structured_data[category], dict):
                            structured_data[category] = []
                        
                        while len(structured_data[category]) < index:
                            structured_data[category].append({})
                        
                        structured_data[category][index-1][field] = data.field_value
                    else:
                        # category_field_index
                        field = field_parts[1]
                        index = int(field_parts[2])
                        
                        if field not in structured_data[category]:
                            structured_data[category][field] = []
                        
                        while len(structured_data[category][field]) < index:
                            structured_data[category][field].append(None)
                        
                        structured_data[category][field][index-1] = data.field_value
        
        return {
            "document_id": str(document_id),
            "status": "processed",
            "text": full_text,
            "structured_data": structured_data,
            "page_count": document.page_count,
            "confidence": next(
                (data.confidence_score for data in extracted_data if data.field_name == "full_text"),
                0.0
            )
        }
