"""
데이터 처리 모듈

주요 기능:
1. 추출된 데이터 구조화
2. 데이터 변환 및 매핑
3. 데이터 검증 및 정규화
"""

import uuid
import json
import re
from typing import Dict, Any, Optional, List, Union
from sqlalchemy.orm import Session

from shared.models import Document, ExtractedData
from shared.constants import DocumentStatus
from shared.exceptions import DataProcessingError, ResourceNotFoundError
from shared.logger import log_info, log_error


class DataProcessor:
    """데이터 처리 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        데이터 처리기 초기화
        
        Args:
            config: 처리 설정
        """
        self.config = config or {}
    
    def process_document_data(self, db: Session, document_id: uuid.UUID) -> Dict[str, Any]:
        """
        문서 데이터 처리
        
        Args:
            db: 데이터베이스 세션
            document_id: 문서 ID
            
        Returns:
            Dict[str, Any]: 처리된 데이터
            
        Raises:
            ResourceNotFoundError: 문서를 찾을 수 없는 경우
            DataProcessingError: 데이터 처리 중 오류 발생 시
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
            raise DataProcessingError(
                message=f"처리할 추출 데이터가 없습니다: {document_id}",
                details={"document_id": str(document_id)}
            )
        
        try:
            # 데이터 구조화
            structured_data = self._structure_data(extracted_data)
            
            # 데이터 정규화
            normalized_data = self._normalize_data(structured_data)
            
            # 데이터 검증
            validated_data = self._validate_data(normalized_data)
            
            # 메타데이터 업데이트
            document.metadata = {
                "processed": True,
                "data_fields": list(validated_data.keys())
            }
            db.commit()
            
            log_info(f"데이터 처리 완료: 문서 {document_id}")
            
            return validated_data
        
        except Exception as e:
            log_error(f"데이터 처리 실패: 문서 {document_id}, 오류: {str(e)}", exc_info=True)
            raise DataProcessingError(
                message=f"데이터 처리 중 오류가 발생했습니다: {str(e)}",
                details={"document_id": str(document_id)}
            )
    
    def _structure_data(self, extracted_data: List[ExtractedData]) -> Dict[str, Any]:
        """
        데이터 구조화
        
        Args:
            extracted_data: 추출 데이터 목록
            
        Returns:
            Dict[str, Any]: 구조화된 데이터
        """
        structured_data = {}
        
        # 전체 텍스트 처리
        full_text = next(
            (data.field_value for data in extracted_data if data.field_name == "full_text"),
            None
        )
        if full_text:
            structured_data["full_text"] = full_text
        
        # 요약 처리
        summary = next(
            (data.field_value for data in extracted_data if data.field_name == "summary"),
            None
        )
        if summary:
            structured_data["summary"] = summary
        
        # 카테고리 처리
        category = next(
            (data.field_value for data in extracted_data if data.field_name == "category"),
            None
        )
        if category:
            structured_data["category"] = category
        
        # 기타 필드 처리
        for data in extracted_data:
            if data.field_name not in ["full_text", "summary", "category"]:
                # 필드 그룹화 (예: personal_info_name -> personal_info.name)
                field_parts = data.field_name.split("_")
                
                if len(field_parts) > 1:
                    # 그룹 필드
                    group = field_parts[0]
                    field = "_".join(field_parts[1:])
                    
                    if group not in structured_data:
                        structured_data[group] = {}
                    
                    structured_data[group][field] = data.field_value
                else:
                    # 일반 필드
                    structured_data[data.field_name] = data.field_value
        
        return structured_data
    
    def _normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        데이터 정규화
        
        Args:
            data: 구조화된 데이터
            
        Returns:
            Dict[str, Any]: 정규화된 데이터
        """
        normalized = {}
        
        for key, value in data.items():
            if isinstance(value, dict):
                # 중첩 딕셔너리 정규화
                normalized[key] = self._normalize_data(value)
            elif isinstance(value, str):
                # 문자열 정규화
                normalized[key] = self._normalize_string(key, value)
            else:
                # 기타 값
                normalized[key] = value
        
        return normalized
    
    def _normalize_string(self, field: str, value: str) -> str:
        """
        문자열 정규화
        
        Args:
            field: 필드명
            value: 문자열 값
            
        Returns:
            str: 정규화된 문자열
        """
        # 공백 정규화
        normalized = value.strip()
        
        # 필드별 정규화
        if "date" in field.lower():
            # 날짜 정규화
            normalized = self._normalize_date(normalized)
        elif "phone" in field.lower() or "tel" in field.lower():
            # 전화번호 정규화
            normalized = self._normalize_phone(normalized)
        elif "amount" in field.lower() or "price" in field.lower() or "cost" in field.lower():
            # 금액 정규화
            normalized = self._normalize_amount(normalized)
        elif "address" in field.lower():
            # 주소 정규화
            normalized = self._normalize_address(normalized)
        
        return normalized
    
    def _normalize_date(self, date_str: str) -> str:
        """
        날짜 정규화
        
        Args:
            date_str: 날짜 문자열
            
        Returns:
            str: 정규화된 날짜
        """
        # 한국어 날짜 형식 정규화 (YYYY년 MM월 DD일 -> YYYY-MM-DD)
        kr_date_match = re.search(r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일', date_str)
        if kr_date_match:
            year, month, day = kr_date_match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"
        
        # 슬래시 형식 정규화 (YYYY/MM/DD -> YYYY-MM-DD)
        slash_date_match = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', date_str)
        if slash_date_match:
            year, month, day = slash_date_match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"
        
        # 점 형식 정규화 (YYYY.MM.DD -> YYYY-MM-DD)
        dot_date_match = re.search(r'(\d{4})\.(\d{1,2})\.(\d{1,2})', date_str)
        if dot_date_match:
            year, month, day = dot_date_match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"
        
        return date_str
    
    def _normalize_phone(self, phone_str: str) -> str:
        """
        전화번호 정규화
        
        Args:
            phone_str: 전화번호 문자열
            
        Returns:
            str: 정규화된 전화번호
        """
        # 특수문자 제거
        normalized = re.sub(r'[^\d+]', '', phone_str)
        
        # 한국 전화번호 형식화 (01012345678 -> 010-1234-5678)
        if re.match(r'^01[016789]\d{7,8}$', normalized):
            if len(normalized) == 10:
                return f"{normalized[:3]}-{normalized[3:6]}-{normalized[6:]}"
            elif len(normalized) == 11:
                return f"{normalized[:3]}-{normalized[3:7]}-{normalized[7:]}"
        
        # 한국 지역번호 형식화 (021234567 -> 02-123-4567)
        kr_area_match = re.match(r'^(0[2-6]\d)(\d{3,4})(\d{4})$', normalized)
        if kr_area_match:
            area, mid, last = kr_area_match.groups()
            return f"{area}-{mid}-{last}"
        
        return normalized
    
    def _normalize_amount(self, amount_str: str) -> str:
        """
        금액 정규화
        
        Args:
            amount_str: 금액 문자열
            
        Returns:
            str: 정규화된 금액
        """
        # 숫자만 추출
        digits = re.sub(r'[^\d.]', '', amount_str)
        
        try:
            # 숫자 변환
            if '.' in digits:
                amount = float(digits)
                # 소수점 처리
                return f"{amount:,.2f}"
            else:
                amount = int(digits)
                return f"{amount:,}"
        except ValueError:
            return amount_str
    
    def _normalize_address(self, address_str: str) -> str:
        """
        주소 정규화
        
        Args:
            address_str: 주소 문자열
            
        Returns:
            str: 정규화된 주소
        """
        # 공백 정규화
        normalized = re.sub(r'\s+', ' ', address_str).strip()
        
        # 한국 주소 정규화
        # 도로명 주소 패턴
        road_pattern = r'([가-힣]+시[가-힣]*구?[가-힣]*동?)\s*([가-힣]+로|길)\s*(\d+)'
        road_match = re.search(road_pattern, normalized)
        
        if road_match:
            area, road, number = road_match.groups()
            # 도로명 주소 형식화
            road_address = f"{area} {road} {number}"
            return road_address
        
        return normalized
    
    def _validate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        데이터 검증
        
        Args:
            data: 정규화된 데이터
            
        Returns:
            Dict[str, Any]: 검증된 데이터
        """
        validated = {}
        
        for key, value in data.items():
            if isinstance(value, dict):
                # 중첩 딕셔너리 검증
                validated_dict = self._validate_data(value)
                if validated_dict:  # 빈 딕셔너리가 아닌 경우만 포함
                    validated[key] = validated_dict
            elif isinstance(value, str):
                # 빈 문자열 제외
                if value.strip():
                    validated[key] = value
            elif value is not None:
                # None이 아닌 값만 포함
                validated[key] = value
        
        return validated
    
    def get_document_data(self, db: Session, document_id: uuid.UUID) -> Dict[str, Any]:
        """
        문서 데이터 조회
        
        Args:
            db: 데이터베이스 세션
            document_id: 문서 ID
            
        Returns:
            Dict[str, Any]: 문서 데이터
            
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
                "filename": document.original_filename,
                "status": document.status,
                "message": "추출된 데이터가 없습니다."
            }
        
        # 데이터 구조화
        structured_data = self._structure_data(extracted_data)
        
        return {
            "document_id": str(document_id),
            "filename": document.original_filename,
            "status": document.status,
            "upload_date": document.upload_date.isoformat(),
            "processed_date": document.processed_date.isoformat() if document.processed_date else None,
            "data": structured_data
        }


class DataMapper:
    """데이터 매핑 클래스"""
    
    def __init__(self, mapping_config: Optional[Dict[str, Any]] = None):
        """
        데이터 매핑기 초기화
        
        Args:
            mapping_config: 매핑 설정
        """
        self.mapping_config = mapping_config or {}
    
    def map_data(self, data: Dict[str, Any], target_schema: str) -> Dict[str, Any]:
        """
        데이터 매핑
        
        Args:
            data: 원본 데이터
            target_schema: 대상 스키마
            
        Returns:
            Dict[str, Any]: 매핑된 데이터
            
        Raises:
            DataProcessingError: 매핑 중 오류 발생 시
        """
        # 스키마 설정 조회
        schema_config = self.mapping_config.get(target_schema)
        if not schema_config:
            raise DataProcessingError(
                message=f"지원하지 않는 스키마입니다: {target_schema}",
                details={"supported_schemas": list(self.mapping_config.keys())}
            )
        
        try:
            # 매핑 수행
            mapped_data = {}
            
            for target_field, source_path in schema_config.items():
                # 소스 필드 경로 파싱
                if isinstance(source_path, str):
                    # 단일 필드 매핑
                    value = self._get_nested_value(data, source_path)
                    if value is not None:
                        mapped_data[target_field] = value
                elif isinstance(source_path, dict) and "transform" in source_path:
                    # 변환 함수 적용
                    transform_func = source_path["transform"]
                    source_fields = source_path.get("fields", [])
                    
                    # 소스 필드 값 추출
                    field_values = []
                    for field in source_fields:
                        value = self._get_nested_value(data, field)
                        field_values.append(value)
                    
                    # 변환 함수 적용
                    if transform_func == "concat":
                        # 문자열 연결
                        non_empty_values = [str(v) for v in field_values if v is not None]
                        if non_empty_values:
                            mapped_data[target_field] = " ".join(non_empty_values)
                    elif transform_func == "first_non_empty":
                        # 첫 번째 비어있지 않은 값
                        for value in field_values:
                            if value is not None:
                                mapped_data[target_field] = value
                                break
            
            return mapped_data
        
        except Exception as e:
            raise DataProcessingError(
                message=f"데이터 매핑 중 오류가 발생했습니다: {str(e)}",
                details={"target_schema": target_schema}
            )
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """
        중첩 데이터에서 값 조회
        
        Args:
            data: 데이터 딕셔너리
            path: 필드 경로 (점 구분)
            
        Returns:
            Any: 조회된 값
        """
        parts = path.split(".")
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
