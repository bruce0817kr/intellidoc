"""
문서 관리 API 스키마 정의

이 모듈은 문서 관리 관련 API의 요청/응답 스키마를 정의합니다.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ============================================================================
# 응답 스키마 (Response Schemas)
# ============================================================================

class DocumentUploadResponse(BaseModel):
    """문서 업로드 응답 스키마"""
    id: str = Field(..., description="문서 ID (UUID)")
    filename: str = Field(..., description="원본 파일명")
    file_type: str = Field(..., description="파일 확장자")
    file_size: int = Field(..., description="파일 크기 (바이트)")
    status: str = Field(..., description="문서 처리 상태")
    upload_date: str = Field(..., description="업로드 일시 (ISO 8601)")
    auto_process: bool = Field(..., description="자동 처리 여부")

    class Config:
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "filename": "sample_document.pdf",
                "file_type": "pdf",
                "file_size": 2048000,
                "status": "UPLOADED",
                "upload_date": "2025-01-01T12:00:00Z",
                "auto_process": True
            }
        }


class DocumentListItemResponse(BaseModel):
    """문서 목록 항목 응답 스키마"""
    id: str = Field(..., description="문서 ID (UUID)")
    filename: str = Field(..., description="원본 파일명")
    file_type: str = Field(..., description="파일 확장자")
    file_size: int = Field(..., description="파일 크기 (바이트)")
    status: str = Field(..., description="문서 처리 상태")
    upload_date: str = Field(..., description="업로드 일시 (ISO 8601)")
    processed_date: Optional[str] = Field(None, description="처리 완료 일시 (ISO 8601)")

    class Config:
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "filename": "sample_document.pdf",
                "file_type": "pdf",
                "file_size": 2048000,
                "status": "PROCESSED",
                "upload_date": "2025-01-01T12:00:00Z",
                "processed_date": "2025-01-01T12:05:00Z"
            }
        }


class ProcessingJobResponse(BaseModel):
    """처리 작업 응답 스키마"""
    id: str = Field(..., description="작업 ID (UUID)")
    job_type: str = Field(..., description="작업 타입")
    status: str = Field(..., description="작업 상태")
    created_at: str = Field(..., description="작업 생성 일시 (ISO 8601)")
    started_at: Optional[str] = Field(None, description="작업 시작 일시 (ISO 8601)")
    completed_at: Optional[str] = Field(None, description="작업 완료 일시 (ISO 8601)")
    error_message: Optional[str] = Field(None, description="에러 메시지")

    class Config:
        schema_extra = {
            "example": {
                "id": "456e7890-e89b-12d3-a456-426614174111",
                "job_type": "OCR",
                "status": "COMPLETED",
                "created_at": "2025-01-01T12:00:00Z",
                "started_at": "2025-01-01T12:00:30Z",
                "completed_at": "2025-01-01T12:02:00Z",
                "error_message": None
            }
        }


class DocumentDetailResponse(BaseModel):
    """문서 상세 정보 응답 스키마"""
    id: str = Field(..., description="문서 ID (UUID)")
    filename: str = Field(..., description="원본 파일명")
    file_type: str = Field(..., description="파일 확장자")
    file_size: int = Field(..., description="파일 크기 (바이트)")
    mime_type: Optional[str] = Field(None, description="MIME 타입")
    status: str = Field(..., description="문서 처리 상태")
    upload_date: str = Field(..., description="업로드 일시 (ISO 8601)")
    processed_date: Optional[str] = Field(None, description="처리 완료 일시 (ISO 8601)")
    page_count: Optional[int] = Field(None, description="페이지 수")
    metadata: Optional[Dict[str, Any]] = Field(None, description="문서 메타데이터")
    jobs: List[ProcessingJobResponse] = Field(
        default_factory=list,
        description="관련 처리 작업 목록"
    )

    class Config:
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "filename": "sample_document.pdf",
                "file_type": "pdf",
                "file_size": 2048000,
                "mime_type": "application/pdf",
                "status": "PROCESSED",
                "upload_date": "2025-01-01T12:00:00Z",
                "processed_date": "2025-01-01T12:05:00Z",
                "page_count": 10,
                "metadata": {
                    "author": "John Doe",
                    "title": "Sample Document",
                    "created": "2025-01-01"
                },
                "jobs": [
                    {
                        "id": "456e7890-e89b-12d3-a456-426614174111",
                        "job_type": "OCR",
                        "status": "COMPLETED",
                        "created_at": "2025-01-01T12:00:00Z",
                        "started_at": "2025-01-01T12:00:30Z",
                        "completed_at": "2025-01-01T12:02:00Z",
                        "error_message": None
                    }
                ]
            }
        }


# ============================================================================
# 에러 응답 스키마 (Error Response Schemas)
# ============================================================================

class DocumentErrorResponse(BaseModel):
    """문서 관련 에러 응답 스키마"""
    error: str = Field(..., description="에러 타입")
    detail: str = Field(..., description="에러 상세 메시지")
    code: Optional[str] = Field(None, description="에러 코드")

    class Config:
        schema_extra = {
            "example": {
                "error": "검증 오류",
                "detail": "지원하지 않는 파일 형식입니다.",
                "code": "UNSUPPORTED_FILE_TYPE"
            }
        }
