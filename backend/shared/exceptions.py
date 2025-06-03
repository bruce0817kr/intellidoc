"""
커스텀 예외 클래스 모듈

- DocumentProcessingError
- OCREngineError
- LLMAPIError
- AuthenticationError
"""

from typing import Optional, Dict, Any
from shared.constants import ErrorCode


class BaseIntelliDocException(Exception):
    """IntelliDoc 기본 예외 클래스"""
    
    def __init__(
        self, 
        message: str, 
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """예외 정보를 딕셔너리로 변환"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ValidationError(BaseIntelliDocException):
    """입력값 검증 오류"""
    
    def __init__(
        self, 
        message: str = "입력값이 유효하지 않습니다.", 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details=details
        )


class AuthenticationError(BaseIntelliDocException):
    """인증 오류"""
    
    def __init__(
        self, 
        message: str = "인증에 실패했습니다.", 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHENTICATION_ERROR,
            status_code=401,
            details=details
        )


class AuthorizationError(BaseIntelliDocException):
    """권한 오류"""
    
    def __init__(
        self, 
        message: str = "권한이 없습니다.", 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHORIZATION_ERROR,
            status_code=403,
            details=details
        )


class ResourceNotFoundError(BaseIntelliDocException):
    """리소스 찾을 수 없음 오류"""
    
    def __init__(
        self, 
        message: str = "요청한 리소스를 찾을 수 없습니다.", 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.NOT_FOUND,
            status_code=404,
            details=details
        )


class ResourceAlreadyExistsError(BaseIntelliDocException):
    """리소스 이미 존재 오류"""
    
    def __init__(
        self, 
        message: str = "이미 존재하는 리소스입니다.", 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.ALREADY_EXISTS,
            status_code=409,
            details=details
        )


class DataProcessingError(BaseIntelliDocException):
    """데이터 처리 오류"""
    
    def __init__(
        self, 
        message: str = "데이터 처리 중 오류가 발생했습니다.", 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.PROCESSING_ERROR,
            status_code=500,
            details=details
        )


class DocumentProcessingError(BaseIntelliDocException):
    """문서 처리 오류"""
    
    def __init__(
        self, 
        message: str = "문서 처리 중 오류가 발생했습니다.", 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.PROCESSING_ERROR,
            status_code=500,
            details=details
        )


class OCREngineError(BaseIntelliDocException):
    """OCR 엔진 오류"""
    
    def __init__(
        self, 
        message: str = "OCR 처리 중 오류가 발생했습니다.", 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.EXTERNAL_API_ERROR,
            status_code=500,
            details=details
        )


class LLMAPIError(BaseIntelliDocException):
    """LLM API 오류"""
    
    def __init__(
        self, 
        message: str = "LLM API 호출 중 오류가 발생했습니다.", 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.EXTERNAL_API_ERROR,
            status_code=500,
            details=details
        )


class DatabaseError(BaseIntelliDocException):
    """데이터베이스 오류"""
    
    def __init__(
        self, 
        message: str = "데이터베이스 오류가 발생했습니다.", 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_ERROR,
            status_code=500,
            details=details
        )


class ConfigurationError(BaseIntelliDocException):
    """설정 오류"""
    
    def __init__(
        self, 
        message: str = "설정 오류가 발생했습니다.", 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=500,
            details=details
        )


class ExternalServiceError(BaseIntelliDocException):
    """외부 서비스 오류"""
    
    def __init__(
        self, 
        message: str = "외부 서비스 호출 중 오류가 발생했습니다.", 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.EXTERNAL_API_ERROR,
            status_code=502,
            details=details
        )


class ExportError(BaseIntelliDocException):
    """내보내기 오류"""
    
    def __init__(
        self, 
        message: str = "내보내기 중 오류가 발생했습니다.", 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.PROCESSING_ERROR,
            status_code=500,
            details=details
        )


class OCRError(BaseIntelliDocException):
    """OCR 처리 오류"""
    
    def __init__(
        self, 
        message: str = "OCR 처리 중 오류가 발생했습니다.", 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.EXTERNAL_API_ERROR,
            status_code=500,
            details=details
        )
