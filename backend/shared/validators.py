"""
데이터 검증 함수 모듈

- 파일 형식 검증
- API 키 형식 검증
- 사용자 입력 검증
"""

import re
import os
from typing import List, Dict, Any, Optional, Set, Union
from pathlib import Path

from shared.constants import ALLOWED_EXTENSIONS, MIME_TYPES, KoreanConstants
from shared.exceptions import ValidationError


def validate_file_extension(filename: str) -> bool:
    """
    파일 확장자 검증
    
    Args:
        filename: 검증할 파일명
        
    Returns:
        bool: 유효한 확장자인 경우 True
        
    Raises:
        ValidationError: 유효하지 않은 확장자인 경우
    """
    ext = Path(filename).suffix.lstrip('.').lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            message=f"지원하지 않는 파일 형식입니다: {ext}",
            details={"allowed_extensions": list(ALLOWED_EXTENSIONS)}
        )
    return True


def validate_file_size(file_size: int, max_size: int = 100 * 1024 * 1024) -> bool:
    """
    파일 크기 검증
    
    Args:
        file_size: 파일 크기 (바이트)
        max_size: 최대 허용 크기 (기본값: 100MB)
        
    Returns:
        bool: 유효한 크기인 경우 True
        
    Raises:
        ValidationError: 파일 크기가 너무 큰 경우
    """
    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        raise ValidationError(
            message=f"파일 크기가 너무 큽니다. 최대 {max_size_mb}MB까지 허용됩니다.",
            details={"max_size_bytes": max_size, "max_size_mb": max_size_mb}
        )
    return True


def validate_file_exists(file_path: str) -> bool:
    """
    파일 존재 여부 검증
    
    Args:
        file_path: 파일 경로
        
    Returns:
        bool: 파일이 존재하는 경우 True
        
    Raises:
        ValidationError: 파일이 존재하지 않는 경우
    """
    if not os.path.isfile(file_path):
        raise ValidationError(
            message=f"파일이 존재하지 않습니다: {file_path}",
            details={"file_path": file_path}
        )
    return True


def validate_api_key_format(api_key: str, min_length: int = 16) -> bool:
    """
    API 키 형식 검증
    
    Args:
        api_key: 검증할 API 키
        min_length: 최소 길이 (기본값: 16)
        
    Returns:
        bool: 유효한 API 키인 경우 True
        
    Raises:
        ValidationError: 유효하지 않은 API 키인 경우
    """
    if len(api_key) < min_length:
        raise ValidationError(
            message=f"API 키는 최소 {min_length}자 이상이어야 합니다.",
            details={"min_length": min_length}
        )
    
    # 일반적인 API 키 형식 검증 (영숫자 및 일부 특수문자)
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', api_key):
        raise ValidationError(
            message="API 키는 영문자, 숫자, 밑줄(_), 하이픈(-), 점(.)만 포함할 수 있습니다.",
            details={"pattern": r'^[a-zA-Z0-9_\-\.]+$'}
        )
    
    return True


def validate_email(email: str) -> bool:
    """
    이메일 주소 검증
    
    Args:
        email: 검증할 이메일 주소
        
    Returns:
        bool: 유효한 이메일인 경우 True
        
    Raises:
        ValidationError: 유효하지 않은 이메일인 경우
    """
    # 간단한 이메일 형식 검증
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(pattern, email):
        raise ValidationError(
            message="유효하지 않은 이메일 주소입니다.",
            details={"email": email}
        )
    return True


def validate_password_strength(password: str) -> bool:
    """
    비밀번호 강도 검증
    
    Args:
        password: 검증할 비밀번호
        
    Returns:
        bool: 유효한 비밀번호인 경우 True
        
    Raises:
        ValidationError: 비밀번호 강도가 약한 경우
    """
    # 최소 8자, 대소문자/숫자/특수문자 조합
    if len(password) < 8:
        raise ValidationError(
            message="비밀번호는 최소 8자 이상이어야 합니다.",
            details={"min_length": 8}
        )
    
    # 대문자 포함 여부
    if not re.search(r'[A-Z]', password):
        raise ValidationError(
            message="비밀번호는 최소 하나의 대문자를 포함해야 합니다.",
            details={"missing": "uppercase_letter"}
        )
    
    # 소문자 포함 여부
    if not re.search(r'[a-z]', password):
        raise ValidationError(
            message="비밀번호는 최소 하나의 소문자를 포함해야 합니다.",
            details={"missing": "lowercase_letter"}
        )
    
    # 숫자 포함 여부
    if not re.search(r'[0-9]', password):
        raise ValidationError(
            message="비밀번호는 최소 하나의 숫자를 포함해야 합니다.",
            details={"missing": "number"}
        )
    
    # 특수문자 포함 여부
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError(
            message="비밀번호는 최소 하나의 특수문자를 포함해야 합니다.",
            details={"missing": "special_character"}
        )
    
    return True


def validate_korean_phone(phone: str) -> bool:
    """
    한국 전화번호 검증
    
    Args:
        phone: 검증할 전화번호
        
    Returns:
        bool: 유효한 전화번호인 경우 True
        
    Raises:
        ValidationError: 유효하지 않은 전화번호인 경우
    """
    # 공백 및 특수문자 제거
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    
    # 패턴 검사
    if not re.match(KoreanConstants.PHONE_PATTERN, cleaned):
        raise ValidationError(
            message="유효하지 않은 한국 전화번호 형식입니다.",
            details={"phone": phone, "pattern": KoreanConstants.PHONE_PATTERN}
        )
    
    return True


def validate_korean_postal_code(postal_code: str) -> bool:
    """
    한국 우편번호 검증
    
    Args:
        postal_code: 검증할 우편번호
        
    Returns:
        bool: 유효한 우편번호인 경우 True
        
    Raises:
        ValidationError: 유효하지 않은 우편번호인 경우
    """
    # 공백 제거
    cleaned = re.sub(r'\s', '', postal_code)
    
    # 패턴 검사
    if not re.match(KoreanConstants.POSTAL_CODE_PATTERN, cleaned):
        raise ValidationError(
            message="유효하지 않은 한국 우편번호 형식입니다.",
            details={"postal_code": postal_code, "pattern": KoreanConstants.POSTAL_CODE_PATTERN}
        )
    
    return True


def validate_korean_resident_id(resident_id: str) -> bool:
    """
    한국 주민등록번호 검증
    
    Args:
        resident_id: 검증할 주민등록번호
        
    Returns:
        bool: 유효한 주민등록번호인 경우 True
        
    Raises:
        ValidationError: 유효하지 않은 주민등록번호인 경우
    """
    # 공백 및 하이픈 제거
    cleaned = re.sub(r'[\s\-]', '', resident_id)
    
    # 패턴 검사
    if not re.match(KoreanConstants.RESIDENT_ID_PATTERN, cleaned):
        raise ValidationError(
            message="유효하지 않은 주민등록번호 형식입니다.",
            details={"pattern": KoreanConstants.RESIDENT_ID_PATTERN}
        )
    
    # 주민등록번호 유효성 검사 (체크섬)
    if len(cleaned) == 13:
        weights = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5]
        sum_value = sum(int(cleaned[i]) * weights[i] for i in range(12))
        check_digit = (11 - (sum_value % 11)) % 10
        
        if int(cleaned[12]) != check_digit:
            raise ValidationError(
                message="유효하지 않은 주민등록번호입니다.",
                details={"reason": "checksum_failed"}
            )
    
    return True


def validate_korean_business_id(business_id: str) -> bool:
    """
    한국 사업자등록번호 검증
    
    Args:
        business_id: 검증할 사업자등록번호
        
    Returns:
        bool: 유효한 사업자등록번호인 경우 True
        
    Raises:
        ValidationError: 유효하지 않은 사업자등록번호인 경우
    """
    # 공백 및 하이픈 제거
    cleaned = re.sub(r'[\s\-]', '', business_id)
    
    # 패턴 검사
    if not re.match(KoreanConstants.BUSINESS_ID_PATTERN, cleaned):
        raise ValidationError(
            message="유효하지 않은 사업자등록번호 형식입니다.",
            details={"pattern": KoreanConstants.BUSINESS_ID_PATTERN}
        )
    
    # 사업자등록번호 유효성 검사 (체크섬)
    if len(cleaned) == 10:
        weights = [1, 3, 7, 1, 3, 7, 1, 3, 5]
        sum_value = sum(int(cleaned[i]) * weights[i] for i in range(9))
        remainder = sum_value % 10
        check_digit = (10 - remainder) % 10
        
        if int(cleaned[9]) != check_digit:
            raise ValidationError(
                message="유효하지 않은 사업자등록번호입니다.",
                details={"reason": "checksum_failed"}
            )
    
    return True


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> bool:
    """
    필수 필드 검증
    
    Args:
        data: 검증할 데이터
        required_fields: 필수 필드 목록
        
    Returns:
        bool: 모든 필수 필드가 존재하는 경우 True
        
    Raises:
        ValidationError: 필수 필드가 누락된 경우
    """
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    
    if missing_fields:
        raise ValidationError(
            message="필수 필드가 누락되었습니다.",
            details={"missing_fields": missing_fields}
        )
    
    return True


def validate_field_length(value: str, field_name: str, min_length: int = 0, max_length: Optional[int] = None) -> bool:
    """
    필드 길이 검증
    
    Args:
        value: 검증할 값
        field_name: 필드 이름
        min_length: 최소 길이 (기본값: 0)
        max_length: 최대 길이 (기본값: None)
        
    Returns:
        bool: 유효한 길이인 경우 True
        
    Raises:
        ValidationError: 길이가 유효하지 않은 경우
    """
    if len(value) < min_length:
        raise ValidationError(
            message=f"{field_name}은(는) 최소 {min_length}자 이상이어야 합니다.",
            details={"field": field_name, "min_length": min_length}
        )
    
    if max_length is not None and len(value) > max_length:
        raise ValidationError(
            message=f"{field_name}은(는) 최대 {max_length}자까지 허용됩니다.",
            details={"field": field_name, "max_length": max_length}
        )
    
    return True


def validate_numeric_range(value: Union[int, float], field_name: str, 
                          min_value: Optional[Union[int, float]] = None, 
                          max_value: Optional[Union[int, float]] = None) -> bool:
    """
    숫자 범위 검증
    
    Args:
        value: 검증할 값
        field_name: 필드 이름
        min_value: 최소값 (기본값: None)
        max_value: 최대값 (기본값: None)
        
    Returns:
        bool: 유효한 범위인 경우 True
        
    Raises:
        ValidationError: 범위가 유효하지 않은 경우
    """
    if min_value is not None and value < min_value:
        raise ValidationError(
            message=f"{field_name}은(는) {min_value} 이상이어야 합니다.",
            details={"field": field_name, "min_value": min_value}
        )
    
    if max_value is not None and value > max_value:
        raise ValidationError(
            message=f"{field_name}은(는) {max_value} 이하여야 합니다.",
            details={"field": field_name, "max_value": max_value}
        )
    
    return True
