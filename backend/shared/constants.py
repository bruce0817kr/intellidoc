"""
시스템 상수 정의 모듈

- 파일 형식, 상태 코드, 에러 메시지
- API 엔드포인트 상수
- 권한 레벨 정의
"""

from enum import Enum, auto
from typing import Dict, List, Set

# 파일 관련 상수
class FileType(str, Enum):
    """지원하는 파일 형식"""
    PDF = "pdf"
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    TIFF = "tiff"
    TIF = "tif"
    DOC = "doc"
    DOCX = "docx"
    HWP = "hwp"
    XLS = "xls"
    XLSX = "xlsx"

# 파일 확장자 매핑
ALLOWED_EXTENSIONS: Set[str] = {
    FileType.PDF, FileType.JPG, FileType.JPEG, FileType.PNG, 
    FileType.TIFF, FileType.TIF, FileType.DOC, FileType.DOCX, 
    FileType.HWP, FileType.XLS, FileType.XLSX
}

# MIME 타입 매핑
MIME_TYPES: Dict[str, str] = {
    FileType.PDF: "application/pdf",
    FileType.JPG: "image/jpeg",
    FileType.JPEG: "image/jpeg",
    FileType.PNG: "image/png",
    FileType.TIFF: "image/tiff",
    FileType.TIF: "image/tiff",
    FileType.DOC: "application/msword",
    FileType.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    FileType.HWP: "application/x-hwp",
    FileType.XLS: "application/vnd.ms-excel",
    FileType.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
}

# 문서 처리 상태
class DocumentStatus(str, Enum):
    """문서 처리 상태"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"

# 작업 상태
class JobStatus(str, Enum):
    """작업 상태"""
    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    REVOKED = "revoked"

# 사용자 역할
class UserRole(str, Enum):
    """사용자 역할"""
    USER = "user"
    ADMIN = "admin"
    AUDITOR = "auditor"

# 권한 정의
PERMISSIONS: Dict[str, List[str]] = {
    UserRole.USER: [
        "document.upload",
        "document.view",
        "document.process",
        "document.export",
        "document.delete_own",
    ],
    UserRole.ADMIN: [
        "document.upload",
        "document.view",
        "document.process",
        "document.export",
        "document.delete_own",
        "document.delete_any",
        "user.manage",
        "settings.manage",
        "api.manage",
    ],
    UserRole.AUDITOR: [
        "document.view",
        "document.export",
        "audit.view",
        "report.generate",
    ]
}

# 에러 코드
class ErrorCode(str, Enum):
    """에러 코드"""
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    ALREADY_EXISTS = "already_exists"
    PROCESSING_ERROR = "processing_error"
    EXTERNAL_API_ERROR = "external_api_error"
    DATABASE_ERROR = "database_error"
    UNKNOWN_ERROR = "unknown_error"

# 에러 메시지
ERROR_MESSAGES: Dict[str, str] = {
    ErrorCode.AUTHENTICATION_ERROR: "인증에 실패했습니다.",
    ErrorCode.AUTHORIZATION_ERROR: "권한이 없습니다.",
    ErrorCode.VALIDATION_ERROR: "입력값이 유효하지 않습니다.",
    ErrorCode.NOT_FOUND: "요청한 리소스를 찾을 수 없습니다.",
    ErrorCode.ALREADY_EXISTS: "이미 존재하는 리소스입니다.",
    ErrorCode.PROCESSING_ERROR: "처리 중 오류가 발생했습니다.",
    ErrorCode.EXTERNAL_API_ERROR: "외부 API 호출 중 오류가 발생했습니다.",
    ErrorCode.DATABASE_ERROR: "데이터베이스 오류가 발생했습니다.",
    ErrorCode.UNKNOWN_ERROR: "알 수 없는 오류가 발생했습니다."
}

# API 엔드포인트
class APIEndpoint:
    """API 엔드포인트 상수"""
    # 인증 관련
    AUTH_LOGIN = "/auth/login"
    AUTH_LOGOUT = "/auth/logout"
    AUTH_ME = "/auth/me"
    AUTH_PASSWORD = "/auth/password"
    
    # 문서 관련
    DOCUMENTS = "/documents"
    DOCUMENT_DETAIL = "/documents/{id}"
    DOCUMENT_PROCESS = "/documents/{id}/process"
    DOCUMENT_STATUS = "/documents/{id}/status"
    DOCUMENT_EXPORT = "/documents/{id}/export"
    
    # 관리자 관련
    ADMIN_USERS = "/admin/users"
    ADMIN_USER_DETAIL = "/admin/users/{id}"
    ADMIN_LOGS = "/admin/logs"
    ADMIN_STATS = "/admin/stats"
    ADMIN_SETTINGS = "/admin/settings"
    
    # API 설정 관련
    CONFIG_OCR_ENGINES = "/config/ocr-engines"
    CONFIG_OCR_ENGINE_DETAIL = "/config/ocr-engines/{id}"
    CONFIG_OCR_ENGINE_TEST = "/config/ocr-engines/{id}/test"
    CONFIG_LLM_PROCESSORS = "/config/llm-processors"
    CONFIG_LLM_PROCESSOR_DETAIL = "/config/llm-processors/{id}"
    CONFIG_LLM_PROCESSOR_TEST = "/config/llm-processors/{id}/test"
    
    # 헬스체크
    HEALTH = "/health"

# 한국어 특화 상수
class KoreanConstants:
    """한국어 특화 상수"""
    # 한국 전화번호 정규식 패턴
    PHONE_PATTERN = r"^(01[016789]|02|0[3-9]\d{1})-?(\d{3,4})-?(\d{4})$"
    
    # 한국 우편번호 정규식 패턴
    POSTAL_CODE_PATTERN = r"^\d{5}$"
    
    # 한국 주민등록번호 정규식 패턴 (마스킹 처리용)
    RESIDENT_ID_PATTERN = r"^\d{6}-?[1-4]\d{6}$"
    
    # 한국 사업자등록번호 정규식 패턴
    BUSINESS_ID_PATTERN = r"^\d{3}-?(\d{2})-?(\d{5})$"
    
    # 한국 법인등록번호 정규식 패턴
    CORPORATE_ID_PATTERN = r"^\d{6}-?(\d{7})$"
    
    # 한국 날짜 형식 (YYYY년 MM월 DD일)
    DATE_FORMAT = "%Y년 %m월 %d일"
    
    # 한국 시간 형식 (HH시 MM분 SS초)
    TIME_FORMAT = "%H시 %M분 %S초"
    
    # 한국 날짜/시간 형식
    DATETIME_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"
