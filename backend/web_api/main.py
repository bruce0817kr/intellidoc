"""
IntelliDoc FastAPI 메인 애플리케이션

이 파일은 모든 API 라우터를 통합하고 FastAPI 애플리케이션을 구성하는 메인 엔트리포인트입니다.
"""

import os
from typing import Dict, Any
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
# from starlette.middleware.sessions import SessionMiddleware
import uvicorn

# 라우터 임포트
from auth.api import router as auth_router
from file_manager.api import router as documents_router
from export.api import router as export_router
from ocr_engines.api import router as ocr_router
from llm_processors.api import router as llm_router
from data_processor.api import router as data_router

# 설정 및 유틸리티 임포트
from shared.config import settings
from shared.logger import get_logger
from shared.exceptions import (
    AuthenticationError, ValidationError, ResourceNotFoundError,
    OCREngineError, LLMAPIError, DataProcessingError, ExportError
)

# 로거 설정
logger = get_logger(__name__)

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="IntelliDoc API",
    description="""
# IntelliDoc - 지능형 문서 처리 시스템 API

## 개요
IntelliDoc은 AI 기반 문서 처리 시스템으로 다음과 같은 기능을 제공합니다:
- **문서 업로드 및 관리**: 다양한 형식의 문서 업로드 및 관리
- **OCR 처리**: Tesseract, EasyOCR, PaddleOCR 등 다양한 OCR 엔진 지원
- **LLM 기반 분석**: OpenAI GPT, Claude, Gemini를 활용한 문서 분석 및 데이터 추출
- **데이터 추출 및 변환**: 구조화된 데이터 추출 및 다양한 형식으로 내보내기
- **보안 인증**: JWT 기반 인증 및 역할 기반 접근 제어 (RBAC)

## 인증
API는 **JWT 토큰 기반 인증**을 사용합니다:
1. `/api/v1/auth/login` 엔드포인트로 로그인
2. 토큰은 **HttpOnly 쿠키**에 자동 저장 (XSS 방지)
3. 이후 모든 요청에 쿠키가 자동으로 포함됨
4. 토큰 만료 시 `/api/v1/auth/refresh`로 갱신

## 보안 기능
- **HttpOnly 쿠키**: XSS 공격 방지
- **CSRF 보호**: SameSite 쿠키 설정
- **MIME 타입 검증**: 파일 시그니처 기반 검증
- **비밀번호 강도 검사**: 최소 8자, 대소문자, 숫자, 특수문자 포함
- **환경 변수 검증**: 프로덕션 환경 보안 설정 검증

## API 버전
현재 버전: **v1**
Base URL: `/api/v1`

## 지원 파일 형식
- **문서**: PDF, DOCX, DOC, TXT, RTF
- **이미지**: PNG, JPEG, JPG, TIFF, BMP, GIF, WEBP
- **스프레드시트**: XLSX, XLS, CSV

## 제한 사항
- **최대 파일 크기**: 50MB
- **동시 처리 제한**: 사용자당 10개
- **API 속도 제한**: 시간당 1000 요청
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "IntelliDoc Support",
        "url": "https://github.com/yourusername/intellidoc",
        "email": "support@intellidoc.example.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    openapi_tags=[
        {
            "name": "인증",
            "description": "사용자 인증 및 권한 관리 API. JWT 토큰 기반 인증을 사용하며, 토큰은 HttpOnly 쿠키에 저장됩니다."
        },
        {
            "name": "문서",
            "description": "문서 업로드, 조회, 다운로드, 삭제 API. 다양한 파일 형식을 지원하며, 자동 OCR 및 데이터 추출이 가능합니다."
        },
        {
            "name": "내보내기",
            "description": "추출된 데이터를 다양한 형식(JSON, CSV, Excel, PDF)으로 내보내기"
        },
        {
            "name": "OCR",
            "description": "OCR 엔진 관리 및 문서 OCR 처리. Tesseract, EasyOCR, PaddleOCR 지원."
        },
        {
            "name": "LLM",
            "description": "LLM 기반 문서 분석 및 데이터 추출. OpenAI GPT, Claude, Gemini 지원."
        },
        {
            "name": "데이터",
            "description": "추출된 데이터 조회 및 관리. 구조화된 데이터 검색 및 필터링."
        }
    ]
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    # 명시적으로 필요한 HTTP 메서드만 허용
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    # 필요한 헤더만 명시적으로 허용
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Requested-With"
    ],
    # 추가 보안 헤더
    expose_headers=["Content-Range", "X-Content-Range"],
    max_age=600,  # Preflight 요청 캐시 시간 (10분)
)

# 세션 미들웨어 설정 (itsdangerous 의존성 문제로 일시적으로 비활성화)
# app.add_middleware(
#     SessionMiddleware,
#     secret_key=settings.SECRET_KEY
# )

# 신뢰할 수 있는 호스트 미들웨어 설정
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# 정적 파일 서빙 (업로드된 파일들)
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# API 라우터 등록
API_PREFIX = "/api/v1"

# 인증 라우터
app.include_router(
    auth_router,
    prefix=API_PREFIX,
    tags=["인증"]
)

# 문서 관리 라우터
app.include_router(
    documents_router,
    prefix=API_PREFIX,
    tags=["문서"]
)

# 내보내기 라우터
app.include_router(
    export_router,
    prefix=API_PREFIX,
    tags=["내보내기"]
)

# OCR 라우터
app.include_router(
    ocr_router,
    prefix=API_PREFIX,
    tags=["OCR"]
)

# LLM 라우터
app.include_router(
    llm_router,
    prefix=API_PREFIX,
    tags=["LLM"]
)

# 데이터 처리 라우터
app.include_router(
    data_router,
    prefix=API_PREFIX,
    tags=["데이터"]
)

# 전역 예외 핸들러
@app.exception_handler(AuthenticationError)
async def authentication_exception_handler(request: Request, exc: AuthenticationError):
    """인증 오류 예외 핸들러"""
    logger.warning(f"Authentication error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"error": "인증 오류", "detail": exc.message, "code": exc.code}
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """검증 오류 예외 핸들러"""
    logger.warning(f"Validation error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "검증 오류", "detail": exc.message, "code": exc.code}
    )

@app.exception_handler(ResourceNotFoundError)
async def not_found_exception_handler(request: Request, exc: ResourceNotFoundError):
    """리소스 없음 예외 핸들러"""
    logger.warning(f"Resource not found: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": "리소스 없음", "detail": exc.message, "code": exc.code}
    )

@app.exception_handler(OCREngineError)
async def ocr_exception_handler(request: Request, exc: OCREngineError):
    """OCR 엔진 오류 예외 핸들러"""
    logger.error(f"OCR engine error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "OCR 처리 오류", "detail": exc.message, "code": exc.code}
    )

@app.exception_handler(LLMAPIError)
async def llm_exception_handler(request: Request, exc: LLMAPIError):
    """LLM API 오류 예외 핸들러"""
    logger.error(f"LLM API error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "LLM 처리 오류", "detail": exc.message, "code": exc.code}
    )

@app.exception_handler(DataProcessingError)
async def data_processing_exception_handler(request: Request, exc: DataProcessingError):
    """데이터 처리 오류 예외 핸들러"""
    logger.error(f"Data processing error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "데이터 처리 오류", "detail": exc.message, "code": exc.code}
    )

@app.exception_handler(ExportError)
async def export_exception_handler(request: Request, exc: ExportError):
    """내보내기 오류 예외 핸들러"""
    logger.error(f"Export error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "내보내기 오류", "detail": exc.message, "code": exc.code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 핸들러"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "내부 서버 오류", "detail": "서버에서 예상치 못한 오류가 발생했습니다."}
    )

# 기본 엔드포인트
@app.get("/", response_model=Dict[str, Any])
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "IntelliDoc API에 오신 것을 환영합니다!",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "healthy"
    }

@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

# 애플리케이션 시작 이벤트
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행되는 이벤트"""
    logger.info("IntelliDoc API 서버가 시작되었습니다.")
    logger.info(f"환경: {settings.ENVIRONMENT}")
    logger.info(f"디버그 모드: {settings.DEBUG}")

# 애플리케이션 종료 이벤트
@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행되는 이벤트"""
    logger.info("IntelliDoc API 서버가 종료되었습니다.")

# 개발 서버 실행
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.ENVIRONMENT == "development" else False,
        log_level="debug" if settings.DEBUG else "info"
    )
