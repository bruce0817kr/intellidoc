"""
LLM 서비스 모듈

주요 기능:
1. LLM 작업 처리
2. 프롬프트 관리
3. 결과 저장 및 조회
"""

import os
import uuid
from typing import Dict, Any, Optional, List, Union
from sqlalchemy.orm import Session

from shared.models import Document, ProcessingJob, ExtractedData
from shared.constants import DocumentStatus, JobStatus
from shared.exceptions import LLMAPIError, ResourceNotFoundError
from shared.logger import log_info, log_error, log_audit
from llm_processors.base import LLMEngineFactory, LLMResult, PromptManager, PromptTemplate


class LLMService:
    """LLM 서비스 클래스"""
    
    def __init__(self, engine_name: str = "openai", config: Optional[Dict[str, Any]] = None):
        """
        LLM 서비스 초기화
        
        Args:
            engine_name: LLM 엔진 이름
            config: LLM 엔진 설정
        """
        self.engine_name = engine_name
        self.config = config or {}
        self.engine = LLMEngineFactory.create(engine_name, config)
        self.prompt_manager = PromptManager()
        
        # 기본 프롬프트 템플릿 등록
        self._register_default_templates()
    
    def _register_default_templates(self) -> None:
        """기본 프롬프트 템플릿 등록"""
        # 문서 요약 템플릿
        summary_template = PromptTemplate(
            name="document_summary",
            description="문서 내용 요약",
            template=(
                "다음 문서 내용을 간결하게 요약해주세요. 핵심 정보만 포함하고, "
                "중요한 사실, 날짜, 이름, 금액 등을 정확히 유지해주세요.\n\n"
                "문서 내용:\n{document_text}\n\n"
                "요약:"
            ),
            variables=["document_text"]
        )
        
        # 정보 추출 템플릿
        extraction_template = PromptTemplate(
            name="information_extraction",
            description="문서에서 특정 정보 추출",
            template=(
                "다음 문서에서 요청한 정보를 추출해주세요. JSON 형식으로 응답해주세요.\n\n"
                "문서 내용:\n{document_text}\n\n"
                "추출할 정보: {fields}\n\n"
                "JSON 형식으로 응답:"
            ),
            variables=["document_text", "fields"]
        )
        
        # 문서 분류 템플릿
        classification_template = PromptTemplate(
            name="document_classification",
            description="문서 유형 분류",
            template=(
                "다음 문서의 유형을 분류해주세요. 가능한 문서 유형은 다음과 같습니다: {categories}\n\n"
                "문서 내용:\n{document_text}\n\n"
                "문서 유형:"
            ),
            variables=["document_text", "categories"]
        )
        
        # 질의응답 템플릿
        qa_template = PromptTemplate(
            name="document_qa",
            description="문서 기반 질의응답",
            template=(
                "다음 문서 내용을 바탕으로 질문에 답변해주세요.\n\n"
                "문서 내용:\n{document_text}\n\n"
                "질문: {question}\n\n"
                "답변:"
            ),
            variables=["document_text", "question"]
        )
        
        # 템플릿 등록
        for template in [summary_template, extraction_template, classification_template, qa_template]:
            if template.name not in self.prompt_manager.templates:
                self.prompt_manager.add_template(template)
    
    def process_document(
        self,
        db: Session,
        document_id: uuid.UUID,
        task_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        job_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        문서 LLM 처리
        
        Args:
            db: 데이터베이스 세션
            document_id: 문서 ID
            task_type: 작업 유형 (summary, extraction, classification, qa)
            parameters: 작업 파라미터
            job_id: 작업 ID (선택 사항)
            
        Returns:
            Dict[str, Any]: LLM 처리 결과
            
        Raises:
            ResourceNotFoundError: 문서를 찾을 수 없는 경우
            LLMAPIError: LLM 처리 중 오류 발생 시
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
                job_type=f"llm_{task_type}",
                status=JobStatus.PENDING,
                parameters=parameters or {}
            )
            db.add(job)
            db.commit()
            db.refresh(job)
        
        try:
            # 작업 상태 업데이트
            job.status = JobStatus.STARTED
            job.started_at = None  # 자동 설정됨
            db.commit()
            
            # 문서 텍스트 조회
            document_text = self._get_document_text(db, document_id)
            if not document_text:
                raise ResourceNotFoundError(message=f"문서 텍스트를 찾을 수 없습니다: {document_id}")
            
            # 작업 유형에 따른 처리
            result = None
            if task_type == "summary":
                result = self._process_summary(document_text, parameters)
            elif task_type == "extraction":
                result = self._process_extraction(document_text, parameters)
            elif task_type == "classification":
                result = self._process_classification(document_text, parameters)
            elif task_type == "qa":
                result = self._process_qa(document_text, parameters)
            else:
                raise LLMAPIError(
                    message=f"지원하지 않는 작업 유형입니다: {task_type}",
                    details={"supported_types": ["summary", "extraction", "classification", "qa"]}
                )
            
            # 결과 저장
            self._save_llm_result(db, document_id, task_type, result)
            
            # 작업 완료 처리
            job.status = JobStatus.SUCCESS
            job.result = result
            db.commit()
            
            log_info(f"LLM 처리 완료: 문서 {document_id}, 작업 {job.id}, 유형 {task_type}")
            
            return {
                "document_id": str(document_id),
                "job_id": str(job.id),
                "task_type": task_type,
                "status": "success",
                "result": result
            }
        
        except Exception as e:
            # 오류 처리
            log_error(f"LLM 처리 실패: 문서 {document_id}, 작업 {job.id}, 오류: {str(e)}", exc_info=True)
            
            # 작업 실패 처리
            job.status = JobStatus.FAILURE
            job.error_message = str(e)
            db.commit()
            
            if isinstance(e, (LLMAPIError, ResourceNotFoundError)):
                raise e
            else:
                raise LLMAPIError(
                    message=f"LLM 처리 중 오류가 발생했습니다: {str(e)}",
                    details={"document_id": str(document_id), "job_id": str(job.id)}
                )
    
    def _get_document_text(self, db: Session, document_id: uuid.UUID) -> Optional[str]:
        """
        문서 텍스트 조회
        
        Args:
            db: 데이터베이스 세션
            document_id: 문서 ID
            
        Returns:
            Optional[str]: 문서 텍스트
        """
        # OCR 결과에서 텍스트 조회
        text_data = db.query(ExtractedData).filter(
            ExtractedData.document_id == document_id,
            ExtractedData.field_name == "full_text"
        ).first()
        
        if text_data:
            return text_data.field_value
        
        return None
    
    def _process_summary(
        self,
        document_text: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        문서 요약 처리
        
        Args:
            document_text: 문서 텍스트
            parameters: 작업 파라미터
            
        Returns:
            Dict[str, Any]: 요약 결과
        """
        params = parameters or {}
        
        # 프롬프트 템플릿 조회
        template = self.prompt_manager.get_template("document_summary")
        
        # 프롬프트 생성
        prompt = template.format(document_text=document_text)
        
        # LLM 생성
        llm_result = self.engine.generate(
            prompt,
            model=params.get("model", self.config.get("model")),
            temperature=params.get("temperature", 0.3),
            max_tokens=params.get("max_tokens", 500)
        )
        
        return {
            "summary": llm_result.text,
            "model": llm_result.model,
            "tokens": llm_result.tokens
        }
    
    def _process_extraction(
        self,
        document_text: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        정보 추출 처리
        
        Args:
            document_text: 문서 텍스트
            parameters: 작업 파라미터
            
        Returns:
            Dict[str, Any]: 추출 결과
        """
        params = parameters or {}
        
        # 추출할 필드
        fields = params.get("fields", ["이름", "날짜", "금액", "주소", "연락처"])
        if isinstance(fields, list):
            fields_str = ", ".join(fields)
        else:
            fields_str = fields
        
        # 프롬프트 템플릿 조회
        template = self.prompt_manager.get_template("information_extraction")
        
        # 프롬프트 생성
        prompt = template.format(document_text=document_text, fields=fields_str)
        
        # LLM 생성
        llm_result = self.engine.generate(
            prompt,
            model=params.get("model", self.config.get("model")),
            temperature=params.get("temperature", 0.2),
            max_tokens=params.get("max_tokens", 1000)
        )
        
        # JSON 파싱 시도
        extracted_data = {}
        try:
            # JSON 형식 응답 추출
            json_text = llm_result.text
            
            # JSON 블록 추출 시도
            import re
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', json_text)
            if json_match:
                json_text = json_match.group(1)
            
            # JSON 파싱
            import json
            extracted_data = json.loads(json_text)
        except Exception as e:
            log_error(f"JSON 파싱 실패: {str(e)}")
            extracted_data = {"raw_text": llm_result.text}
        
        return {
            "extracted_data": extracted_data,
            "model": llm_result.model,
            "tokens": llm_result.tokens
        }
    
    def _process_classification(
        self,
        document_text: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        문서 분류 처리
        
        Args:
            document_text: 문서 텍스트
            parameters: 작업 파라미터
            
        Returns:
            Dict[str, Any]: 분류 결과
        """
        params = parameters or {}
        
        # 분류 카테고리
        categories = params.get("categories", ["계약서", "영수증", "청구서", "보고서", "기타"])
        if isinstance(categories, list):
            categories_str = ", ".join(categories)
        else:
            categories_str = categories
        
        # 프롬프트 템플릿 조회
        template = self.prompt_manager.get_template("document_classification")
        
        # 프롬프트 생성
        prompt = template.format(document_text=document_text, categories=categories_str)
        
        # LLM 생성
        llm_result = self.engine.generate(
            prompt,
            model=params.get("model", self.config.get("model")),
            temperature=params.get("temperature", 0.2),
            max_tokens=params.get("max_tokens", 100)
        )
        
        return {
            "category": llm_result.text.strip(),
            "model": llm_result.model,
            "tokens": llm_result.tokens
        }
    
    def _process_qa(
        self,
        document_text: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        질의응답 처리
        
        Args:
            document_text: 문서 텍스트
            parameters: 작업 파라미터
            
        Returns:
            Dict[str, Any]: 질의응답 결과
        """
        params = parameters or {}
        
        # 질문
        question = params.get("question")
        if not question:
            raise LLMAPIError(
                message="질문이 제공되지 않았습니다.",
                details={"parameters": params}
            )
        
        # 프롬프트 템플릿 조회
        template = self.prompt_manager.get_template("document_qa")
        
        # 프롬프트 생성
        prompt = template.format(document_text=document_text, question=question)
        
        # LLM 생성
        llm_result = self.engine.generate(
            prompt,
            model=params.get("model", self.config.get("model")),
            temperature=params.get("temperature", 0.3),
            max_tokens=params.get("max_tokens", 500)
        )
        
        return {
            "question": question,
            "answer": llm_result.text,
            "model": llm_result.model,
            "tokens": llm_result.tokens
        }
    
    def _save_llm_result(
        self,
        db: Session,
        document_id: uuid.UUID,
        task_type: str,
        result: Dict[str, Any]
    ) -> None:
        """
        LLM 결과 저장
        
        Args:
            db: 데이터베이스 세션
            document_id: 문서 ID
            task_type: 작업 유형
            result: 결과 데이터
        """
        # 작업 유형에 따른 저장
        if task_type == "summary":
            # 요약 저장
            summary_data = ExtractedData(
                document_id=document_id,
                field_name="summary",
                field_value=result["summary"],
                field_type="text",
                confidence_score=0.0,  # LLM은 신뢰도 제공 안함
                extraction_method="llm"
            )
            db.add(summary_data)
        
        elif task_type == "extraction":
            # 추출 데이터 저장
            extracted_data = result.get("extracted_data", {})
            for field, value in extracted_data.items():
                if isinstance(value, (str, int, float, bool)):
                    field_data = ExtractedData(
                        document_id=document_id,
                        field_name=field,
                        field_value=str(value),
                        field_type="text",
                        confidence_score=0.0,
                        extraction_method="llm"
                    )
                    db.add(field_data)
        
        elif task_type == "classification":
            # 분류 결과 저장
            category_data = ExtractedData(
                document_id=document_id,
                field_name="category",
                field_value=result["category"],
                field_type="text",
                confidence_score=0.0,
                extraction_method="llm"
            )
            db.add(category_data)
        
        elif task_type == "qa":
            # 질의응답 결과는 저장하지 않음 (임시 결과)
            pass
        
        db.commit()
    
    def get_available_engines(self) -> List[str]:
        """
        사용 가능한 LLM 엔진 목록 조회
        
        Returns:
            List[str]: 엔진 이름 목록
        """
        return LLMEngineFactory.get_available_engines()
    
    def get_available_templates(self) -> List[Dict[str, Any]]:
        """
        사용 가능한 프롬프트 템플릿 목록 조회
        
        Returns:
            List[Dict[str, Any]]: 템플릿 목록
        """
        return [
            {
                "name": template.name,
                "description": template.description,
                "variables": template.variables
            }
            for template in self.prompt_manager.templates.values()
        ]
    
    def add_template(
        self,
        name: str,
        template: str,
        variables: List[str],
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        프롬프트 템플릿 추가
        
        Args:
            name: 템플릿 이름
            template: 템플릿 문자열
            variables: 변수 이름 목록
            description: 템플릿 설명
            
        Returns:
            Dict[str, Any]: 추가된 템플릿 정보
        """
        prompt_template = PromptTemplate(
            name=name,
            template=template,
            variables=variables,
            description=description
        )
        
        self.prompt_manager.add_template(prompt_template)
        
        return prompt_template.to_dict()
    
    def get_document_llm_results(
        self,
        db: Session,
        document_id: uuid.UUID,
        task_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        문서 LLM 결과 조회
        
        Args:
            db: 데이터베이스 세션
            document_id: 문서 ID
            task_type: 작업 유형 필터
            
        Returns:
            Dict[str, Any]: LLM 결과
            
        Raises:
            ResourceNotFoundError: 문서를 찾을 수 없는 경우
        """
        # 문서 조회
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ResourceNotFoundError(message=f"문서를 찾을 수 없습니다: {document_id}")
        
        # 작업 조회
        query = db.query(ProcessingJob).filter(
            ProcessingJob.document_id == document_id,
            ProcessingJob.job_type.like("llm_%")
        )
        
        if task_type:
            query = query.filter(ProcessingJob.job_type == f"llm_{task_type}")
        
        jobs = query.all()
        
        if not jobs:
            return {
                "document_id": str(document_id),
                "status": "not_processed",
                "message": "LLM 처리 결과가 없습니다."
            }
        
        # 결과 구성
        results = {}
        for job in jobs:
            job_type = job.job_type.replace("llm_", "")
            results[job_type] = {
                "job_id": str(job.id),
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "result": job.result,
                "error_message": job.error_message
            }
        
        return {
            "document_id": str(document_id),
            "status": "processed",
            "results": results
        }
