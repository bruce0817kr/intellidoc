"""
공통 유틸리티 함수 모듈

- 파일 검증 (크기, 형식)
- UUID 생성
- 날짜/시간 처리
- 암호화/복호화
"""

import os
import uuid
import datetime
import re
import hashlib
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Set

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from shared.constants import ALLOWED_EXTENSIONS, MIME_TYPES, KoreanConstants


def generate_uuid() -> uuid.UUID:
    """
    고유 UUID 생성
    
    Returns:
        uuid.UUID: 생성된 UUID
    """
    return uuid.uuid4()


def is_valid_file_extension(filename: str) -> bool:
    """
    파일 확장자 유효성 검사
    
    Args:
        filename: 검사할 파일명
        
    Returns:
        bool: 유효한 확장자인 경우 True
    """
    return get_file_extension(filename).lower() in ALLOWED_EXTENSIONS


def get_file_extension(filename: str) -> str:
    """
    파일 확장자 추출
    
    Args:
        filename: 파일명
        
    Returns:
        str: 파일 확장자 (점 제외)
    """
    return Path(filename).suffix.lstrip('.')


def get_mime_type(filename: str) -> Optional[str]:
    """
    파일명에서 MIME 타입 추출
    
    Args:
        filename: 파일명
        
    Returns:
        Optional[str]: MIME 타입 또는 None
    """
    ext = get_file_extension(filename).lower()
    return MIME_TYPES.get(ext)


def generate_safe_filename(original_filename: str) -> str:
    """
    안전한 파일명 생성
    
    Args:
        original_filename: 원본 파일명
        
    Returns:
        str: 안전한 파일명 (UUID + 원본 확장자)
    """
    ext = get_file_extension(original_filename)
    return f"{uuid.uuid4()}.{ext}"


def create_directory_if_not_exists(directory_path: str) -> None:
    """
    디렉토리가 없으면 생성
    
    Args:
        directory_path: 생성할 디렉토리 경로
    """
    os.makedirs(directory_path, exist_ok=True)


def format_datetime(dt: datetime.datetime, format_str: Optional[str] = None) -> str:
    """
    날짜/시간 포맷팅
    
    Args:
        dt: 날짜/시간 객체
        format_str: 포맷 문자열 (기본값: KoreanConstants.DATETIME_FORMAT)
        
    Returns:
        str: 포맷팅된 날짜/시간 문자열
    """
    if format_str is None:
        format_str = KoreanConstants.DATETIME_FORMAT
    return dt.strftime(format_str)


def parse_korean_date(date_str: str) -> Optional[datetime.date]:
    """
    한국어 날짜 문자열 파싱
    
    Args:
        date_str: 날짜 문자열 (예: "2025년 6월 1일")
        
    Returns:
        Optional[datetime.date]: 파싱된 날짜 객체 또는 None
    """
    try:
        return datetime.datetime.strptime(date_str, KoreanConstants.DATE_FORMAT).date()
    except ValueError:
        # 다양한 한국어 날짜 형식 처리
        patterns = [
            r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일',  # 2025년 6월 1일
            r'(\d{4})[./](\d{1,2})[./](\d{1,2})',     # 2025.6.1 또는 2025/6/1
            r'(\d{4})-(\d{1,2})-(\d{1,2})'            # 2025-6-1
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                year, month, day = map(int, match.groups())
                return datetime.date(year, month, day)
        
        return None


def normalize_korean_phone(phone: str) -> Optional[str]:
    """
    한국 전화번호 정규화
    
    Args:
        phone: 전화번호 문자열
        
    Returns:
        Optional[str]: 정규화된 전화번호 또는 None
    """
    if not phone:
        return None
    
    # 공백 및 특수문자 제거
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    
    # 패턴 검사
    match = re.match(KoreanConstants.PHONE_PATTERN, cleaned)
    if not match:
        return None
    
    # 그룹 추출
    groups = match.groups()
    if len(groups) == 3:
        return f"{groups[0]}-{groups[1]}-{groups[2]}"
    
    return None


def normalize_korean_postal_code(postal_code: str) -> Optional[str]:
    """
    한국 우편번호 정규화
    
    Args:
        postal_code: 우편번호 문자열
        
    Returns:
        Optional[str]: 정규화된 우편번호 또는 None
    """
    if not postal_code:
        return None
    
    # 공백 제거
    cleaned = re.sub(r'\s', '', postal_code)
    
    # 패턴 검사
    if re.match(KoreanConstants.POSTAL_CODE_PATTERN, cleaned):
        return cleaned
    
    return None


def mask_sensitive_data(text: str, pattern: str, mask_char: str = '*') -> str:
    """
    민감한 데이터 마스킹
    
    Args:
        text: 원본 텍스트
        pattern: 마스킹할 패턴 (정규식)
        mask_char: 마스킹 문자 (기본값: *)
        
    Returns:
        str: 마스킹된 텍스트
    """
    def mask_match(match):
        s = match.group(0)
        # 앞 3자리와 뒤 4자리를 제외하고 마스킹
        if len(s) > 7:
            return s[:3] + mask_char * (len(s) - 7) + s[-4:]
        # 짧은 경우 절반만 마스킹
        else:
            return s[:len(s)//2] + mask_char * (len(s) - len(s)//2)
    
    return re.sub(pattern, mask_match, text)


def mask_resident_id(text: str) -> str:
    """
    주민등록번호 마스킹
    
    Args:
        text: 원본 텍스트
        
    Returns:
        str: 마스킹된 텍스트
    """
    return mask_sensitive_data(text, KoreanConstants.RESIDENT_ID_PATTERN)


def mask_business_id(text: str) -> str:
    """
    사업자등록번호 마스킹
    
    Args:
        text: 원본 텍스트
        
    Returns:
        str: 마스킹된 텍스트
    """
    return mask_sensitive_data(text, KoreanConstants.BUSINESS_ID_PATTERN)


def derive_key(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    비밀번호에서 암호화 키 유도
    
    Args:
        password: 비밀번호
        salt: 솔트 (기본값: 랜덤 생성)
        
    Returns:
        Tuple[bytes, bytes]: (키, 솔트)
    """
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt


def encrypt_data(data: str, key: bytes) -> str:
    """
    데이터 암호화
    
    Args:
        data: 암호화할 데이터
        key: 암호화 키
        
    Returns:
        str: 암호화된 데이터 (base64 인코딩)
    """
    f = Fernet(key)
    encrypted_data = f.encrypt(data.encode())
    return encrypted_data.decode()


def decrypt_data(encrypted_data: str, key: bytes) -> str:
    """
    데이터 복호화
    
    Args:
        encrypted_data: 암호화된 데이터
        key: 암호화 키
        
    Returns:
        str: 복호화된 데이터
    """
    f = Fernet(key)
    decrypted_data = f.decrypt(encrypted_data.encode())
    return decrypted_data.decode()


def hash_password(password: str) -> str:
    """
    비밀번호 해싱 (단방향)
    
    Args:
        password: 원본 비밀번호
        
    Returns:
        str: 해시된 비밀번호
    """
    # 실제 구현에서는 passlib.hash 사용 권장
    salt = os.urandom(16)
    salt_hex = salt.hex()
    
    # SHA-256 해싱
    hash_obj = hashlib.sha256(salt + password.encode())
    password_hash = hash_obj.hexdigest()
    
    # 솔트와 해시 결합
    return f"{salt_hex}${password_hash}"


def verify_password_hash(hashed_password: str, password: str) -> bool:
    """
    비밀번호 해시 검증
    
    Args:
        hashed_password: 해시된 비밀번호
        password: 검증할 비밀번호
        
    Returns:
        bool: 비밀번호 일치 여부
    """
    # 솔트와 해시 분리
    salt_hex, password_hash = hashed_password.split('$')
    salt = bytes.fromhex(salt_hex)
    
    # 검증할 비밀번호 해싱
    hash_obj = hashlib.sha256(salt + password.encode())
    verify_hash = hash_obj.hexdigest()
    
    # 해시 비교
    return password_hash == verify_hash


def calculate_file_hash(file_path: str) -> str:
    """
    파일 해시 계산 (SHA-256)
    
    Args:
        file_path: 파일 경로
        
    Returns:
        str: 파일 해시 (16진수)
    """
    hash_obj = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()
