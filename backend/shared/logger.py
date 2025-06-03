"""
구조화된 로깅 시스템 모듈

- JSON 형태 로그 출력
- 사용자별 로그 컨텍스트
- 에러 추적 및 알림
"""

import json
import logging
import traceback
import datetime
import uuid
from typing import Dict, Any, Optional, Union
from contextvars import ContextVar

# 로그 컨텍스트 (사용자 ID, 요청 ID 등)
log_context: ContextVar[Dict[str, Any]] = ContextVar('log_context', default={})

# 로거 설정
logger = logging.getLogger("intellidoc")

class JSONFormatter(logging.Formatter):
    """JSON 형식 로그 포맷터"""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        로그 레코드를 JSON 형식으로 포맷팅
        
        Args:
            record: 로그 레코드
            
        Returns:
            str: JSON 형식의 로그 문자열
        """
        log_data = {
            "timestamp": datetime.datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 컨텍스트 정보 추가
        context = log_context.get()
        if context:
            log_data.update(context)
        
        # 예외 정보 추가
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # 추가 데이터 추가
        if hasattr(record, 'data') and record.data:
            log_data.update(record.data)
        
        return json.dumps(log_data, ensure_ascii=False)

def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None) -> None:
    """
    로깅 시스템 설정
    
    Args:
        level: 로그 레벨 (기본값: INFO)
        log_file: 로그 파일 경로 (기본값: None)
    """
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # JSON 포맷터 생성
    formatter = JSONFormatter()
    
    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러 추가 (지정된 경우)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # IntelliDoc 로거 설정
    intellidoc_logger = logging.getLogger("intellidoc")
    intellidoc_logger.setLevel(level)

def set_context(key: str, value: Any) -> None:
    """
    로그 컨텍스트에 값 설정
    
    Args:
        key: 컨텍스트 키
        value: 컨텍스트 값
    """
    context = log_context.get().copy()
    context[key] = value
    log_context.set(context)

def clear_context() -> None:
    """로그 컨텍스트 초기화"""
    log_context.set({})

def set_user_context(user_id: Union[str, uuid.UUID], username: Optional[str] = None) -> None:
    """
    사용자 컨텍스트 설정
    
    Args:
        user_id: 사용자 ID
        username: 사용자명 (기본값: None)
    """
    set_context("user_id", str(user_id))
    if username:
        set_context("username", username)

def set_request_context(request_id: Optional[Union[str, uuid.UUID]] = None) -> None:
    """
    요청 컨텍스트 설정
    
    Args:
        request_id: 요청 ID (기본값: 자동 생성)
    """
    if request_id is None:
        request_id = uuid.uuid4()
    set_context("request_id", str(request_id))

def log_with_data(level: int, msg: str, data: Dict[str, Any]) -> None:
    """
    추가 데이터와 함께 로그 기록
    
    Args:
        level: 로그 레벨
        msg: 로그 메시지
        data: 추가 데이터
    """
    record = logging.LogRecord(
        name=logger.name,
        level=level,
        pathname="",
        lineno=0,
        msg=msg,
        args=(),
        exc_info=None
    )
    record.data = data
    logger.handle(record)

def log_info(msg: str, data: Optional[Dict[str, Any]] = None) -> None:
    """
    INFO 레벨 로그 기록
    
    Args:
        msg: 로그 메시지
        data: 추가 데이터 (기본값: None)
    """
    if data:
        log_with_data(logging.INFO, msg, data)
    else:
        logger.info(msg)

def log_warning(msg: str, data: Optional[Dict[str, Any]] = None) -> None:
    """
    WARNING 레벨 로그 기록
    
    Args:
        msg: 로그 메시지
        data: 추가 데이터 (기본값: None)
    """
    if data:
        log_with_data(logging.WARNING, msg, data)
    else:
        logger.warning(msg)

def log_error(msg: str, exc_info: bool = False, data: Optional[Dict[str, Any]] = None) -> None:
    """
    ERROR 레벨 로그 기록
    
    Args:
        msg: 로그 메시지
        exc_info: 예외 정보 포함 여부 (기본값: False)
        data: 추가 데이터 (기본값: None)
    """
    if data:
        log_with_data(logging.ERROR, msg, data)
    else:
        logger.error(msg, exc_info=exc_info)

def log_critical(msg: str, exc_info: bool = True, data: Optional[Dict[str, Any]] = None) -> None:
    """
    CRITICAL 레벨 로그 기록
    
    Args:
        msg: 로그 메시지
        exc_info: 예외 정보 포함 여부 (기본값: True)
        data: 추가 데이터 (기본값: None)
    """
    if data:
        log_with_data(logging.CRITICAL, msg, data)
    else:
        logger.critical(msg, exc_info=exc_info)

def log_exception(msg: str, data: Optional[Dict[str, Any]] = None) -> None:
    """
    현재 예외 정보와 함께 로그 기록
    
    Args:
        msg: 로그 메시지
        data: 추가 데이터 (기본값: None)
    """
    if data:
        data_with_exc = data.copy()
        logger.exception(msg, extra={"data": data_with_exc})
    else:
        logger.exception(msg)

def log_audit(user_id: Union[str, uuid.UUID], action: str, resource_type: str, 
             resource_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
    """
    감사 로그 기록
    
    Args:
        user_id: 사용자 ID
        action: 수행한 작업
        resource_type: 리소스 유형
        resource_id: 리소스 ID (기본값: None)
        details: 추가 상세 정보 (기본값: None)
    """
    audit_data = {
        "audit": True,
        "user_id": str(user_id),
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details or {}
    }
    log_with_data(logging.INFO, f"AUDIT: {action} on {resource_type}", audit_data)

def get_logger(name: str) -> logging.Logger:
    """
    이름으로 로거 인스턴스 반환
    
    Args:
        name: 로거 이름
        
    Returns:
        logging.Logger: 로거 인스턴스
    """
    return logging.getLogger(name)

# 초기 로깅 설정
setup_logging()
