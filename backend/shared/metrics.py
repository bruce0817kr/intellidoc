"""
Prometheus 메트릭 수집 모듈

주요 메트릭:
- HTTP 요청 수/응답 시간
- 데이터베이스 쿼리 수/시간
- 파일 업로드 수/크기
- OCR/LLM 처리 시간
- 에러 발생 수
"""

from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps
from typing import Callable

# HTTP 요청 메트릭
http_requests_total = Counter(
    'intellidoc_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'intellidoc_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# 데이터베이스 메트릭
db_queries_total = Counter(
    'intellidoc_db_queries_total',
    'Total database queries',
    ['operation']  # select, insert, update, delete
)

db_query_duration_seconds = Histogram(
    'intellidoc_db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation']
)

# 파일 처리 메트릭
file_uploads_total = Counter(
    'intellidoc_file_uploads_total',
    'Total file uploads',
    ['file_type', 'status']  # success, failed
)

file_upload_size_bytes = Histogram(
    'intellidoc_file_upload_size_bytes',
    'File upload size in bytes',
    buckets=(1024, 10240, 102400, 1048576, 10485760, 104857600)  # 1KB, 10KB, 100KB, 1MB, 10MB, 100MB
)

# OCR/LLM 처리 메트릭
ocr_processing_duration_seconds = Histogram(
    'intellidoc_ocr_processing_duration_seconds',
    'OCR processing duration in seconds',
    ['engine']  # tesseract, mistral, google_vision
)

llm_processing_duration_seconds = Histogram(
    'intellidoc_llm_processing_duration_seconds',
    'LLM processing duration in seconds',
    ['model']
)

# 작업 큐 메트릭
celery_tasks_total = Counter(
    'intellidoc_celery_tasks_total',
    'Total Celery tasks',
    ['task_name', 'status']  # success, failed, retry
)

celery_queue_length = Gauge(
    'intellidoc_celery_queue_length',
    'Current Celery queue length',
    ['queue_name']
)

# 에러 메트릭
errors_total = Counter(
    'intellidoc_errors_total',
    'Total errors',
    ['error_type', 'severity']  # validation, authentication, server, severity: low, medium, high
)

# 시스템 정보
app_info = Info(
    'intellidoc_app',
    'IntelliDoc application info'
)

# 활성 세션 메트릭
active_sessions = Gauge(
    'intellidoc_active_sessions',
    'Number of active user sessions'
)

# 문서 통계 메트릭
documents_by_status = Gauge(
    'intellidoc_documents_by_status',
    'Number of documents by status',
    ['status']
)


def track_http_request(method: str, endpoint: str):
    """HTTP 요청 추적 데코레이터"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = 200

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = getattr(e, 'status_code', 500)
                raise
            finally:
                duration = time.time() - start_time
                http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code
                ).inc()
                http_request_duration_seconds.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(duration)

        return wrapper
    return decorator


def track_db_query(operation: str):
    """데이터베이스 쿼리 추적 데코레이터"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                db_queries_total.labels(operation=operation).inc()
                db_query_duration_seconds.labels(operation=operation).observe(duration)

        return wrapper
    return decorator


def track_file_upload(file_type: str, file_size: int, success: bool):
    """파일 업로드 추적"""
    status = "success" if success else "failed"
    file_uploads_total.labels(file_type=file_type, status=status).inc()

    if success:
        file_upload_size_bytes.observe(file_size)


def track_ocr_processing(engine: str, duration: float):
    """OCR 처리 추적"""
    ocr_processing_duration_seconds.labels(engine=engine).observe(duration)


def track_llm_processing(model: str, duration: float):
    """LLM 처리 추적"""
    llm_processing_duration_seconds.labels(model=model).observe(duration)


def track_celery_task(task_name: str, status: str):
    """Celery 작업 추적"""
    celery_tasks_total.labels(task_name=task_name, status=status).inc()


def track_error(error_type: str, severity: str):
    """에러 추적"""
    errors_total.labels(error_type=error_type, severity=severity).inc()


def update_active_sessions(count: int):
    """활성 세션 수 업데이트"""
    active_sessions.set(count)


def update_documents_by_status(status: str, count: int):
    """상태별 문서 수 업데이트"""
    documents_by_status.labels(status=status).set(count)


def set_app_info(version: str, environment: str):
    """애플리케이션 정보 설정"""
    app_info.info({
        'version': version,
        'environment': environment,
        'app_name': 'IntelliDoc'
    })
