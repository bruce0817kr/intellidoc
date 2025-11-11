"""
파일 관리 API 엔드포인트 모듈

주요 기능:
1. 파일 업로드 API
2. 파일 다운로드 API
3. 파일 목록 조회 API
4. 파일 삭제 API
"""

from typing import Dict, Any, Optional, List
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.models import User, Document
from shared.constants import DocumentStatus
from shared.exceptions import ValidationError, ResourceNotFoundError
from auth.api import get_current_active_user
from file_manager.service import (
    upload_file, get_document, get_document_file_path, delete_document,
    get_user_documents, get_document_jobs
)
from file_manager.schemas import (
    DocumentUploadResponse, DocumentListItemResponse, DocumentDetailResponse,
    DocumentErrorResponse
)

# 라우터 설정
router = APIRouter(prefix="/documents", tags=["문서"])


@router.post(
    "/",
    response_model=DocumentUploadResponse,
    summary="문서 업로드",
    description="""
    새로운 문서를 업로드합니다.

    **지원 파일 형식:**
    - **문서**: PDF, DOCX, DOC, TXT, RTF
    - **이미지**: PNG, JPEG, JPG, TIFF, BMP, GIF, WEBP
    - **스프레드시트**: XLSX, XLS, CSV

    **파일 검증:**
    - 최대 파일 크기: 50MB
    - MIME 타입 검증: 파일 시그니처 기반 검증 수행
    - 확장자 검증: 선언된 확장자와 실제 파일 형식 일치 확인

    **자동 처리:**
    - `auto_process=true`: 업로드 후 자동으로 OCR 및 데이터 추출 시작
    - `auto_process=false`: 수동으로 처리 시작 필요

    **보안:**
    - 업로드된 파일은 UUID 기반 파일명으로 저장됩니다
    - 사용자별 업로드 디렉토리로 격리됩니다
    """,
    responses={
        200: {
            "description": "문서 업로드 성공",
            "model": DocumentUploadResponse
        },
        400: {
            "description": "잘못된 요청 - 지원하지 않는 파일 형식, 크기 초과 등",
            "model": DocumentErrorResponse
        },
        401: {
            "description": "인증 실패",
            "model": DocumentErrorResponse
        }
    }
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="업로드할 파일 (최대 50MB)"),
    auto_process: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """문서 업로드 API"""
    try:
        # 파일 크기 계산
        file.file.seek(0, 2)  # 파일 끝으로 이동
        file_size = file.file.tell()  # 현재 위치(파일 크기) 확인
        file.file.seek(0)  # 파일 시작으로 이동
        
        # 파일 업로드 처리
        document = upload_file(
            db=db,
            file_content=file.file,
            original_filename=file.filename,
            file_size=file_size,
            user_id=current_user.id,
            auto_process=auto_process
        )
        
        return {
            "id": str(document.id),
            "filename": document.original_filename,
            "file_type": document.file_type,
            "file_size": document.file_size,
            "status": document.status,
            "upload_date": document.upload_date.isoformat(),
            "auto_process": auto_process
        }
    
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 업로드 중 오류가 발생했습니다: {str(e)}"
        )


@router.get(
    "/",
    response_model=List[DocumentListItemResponse],
    summary="문서 목록 조회",
    description="""
    현재 사용자가 업로드한 문서 목록을 조회합니다.

    **페이지네이션:**
    - `skip`: 건너뛸 문서 개수 (기본값: 0)
    - `limit`: 조회할 최대 문서 개수 (기본값: 100, 최대: 1000)

    **필터링:**
    - `status`: 문서 상태로 필터링
      - `UPLOADED`: 업로드 완료
      - `PROCESSING`: 처리 중
      - `PROCESSED`: 처리 완료
      - `FAILED`: 처리 실패

    **정렬:**
    - 업로드 일시 기준 내림차순 정렬 (최신순)

    **권한:**
    - 사용자는 자신이 업로드한 문서만 조회 가능
    """,
    responses={
        200: {
            "description": "문서 목록 조회 성공",
            "model": List[DocumentListItemResponse]
        },
        400: {
            "description": "잘못된 요청 - 유효하지 않은 상태 값",
            "model": DocumentErrorResponse
        },
        401: {
            "description": "인증 실패",
            "model": DocumentErrorResponse
        }
    }
)
async def get_documents(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> List[Dict[str, Any]]:
    """문서 목록 조회 API"""
    # 상태 필터 변환
    status_filter = None
    if status:
        try:
            status_filter = DocumentStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"유효하지 않은 상태 값입니다: {status}"
            )
    
    # 문서 목록 조회
    documents = get_user_documents(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        status=status_filter
    )
    
    # 응답 데이터 변환
    result = []
    for doc in documents:
        result.append({
            "id": str(doc.id),
            "filename": doc.original_filename,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "status": doc.status,
            "upload_date": doc.upload_date.isoformat(),
            "processed_date": doc.processed_date.isoformat() if doc.processed_date else None
        })
    
    return result


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="문서 상세 조회",
    description="""
    특정 문서의 상세 정보를 조회합니다.

    **반환 정보:**
    - 문서 기본 정보 (파일명, 크기, 형식, 상태 등)
    - 문서 메타데이터 (페이지 수, 작성자, 생성일 등)
    - 처리 작업 목록 (OCR, LLM 분석 등)
    - 각 작업의 상태 및 결과

    **권한:**
    - 문서 소유자만 조회 가능
    - 다른 사용자의 문서 접근 시 403 Forbidden 반환
    """,
    responses={
        200: {
            "description": "문서 상세 정보 조회 성공",
            "model": DocumentDetailResponse
        },
        403: {
            "description": "권한 없음 - 문서 소유자가 아님",
            "model": DocumentErrorResponse
        },
        404: {
            "description": "문서를 찾을 수 없음",
            "model": DocumentErrorResponse
        }
    }
)
async def get_document_details(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """문서 상세 조회 API"""
    try:
        # 문서 조회
        document = get_document(db, document_id)
        
        # 소유자 확인
        if document.uploaded_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 문서에 대한 접근 권한이 없습니다."
            )
        
        # 작업 목록 조회
        jobs = get_document_jobs(db, document_id)
        
        # 응답 데이터
        return {
            "id": str(document.id),
            "filename": document.original_filename,
            "file_type": document.file_type,
            "file_size": document.file_size,
            "mime_type": document.mime_type,
            "status": document.status,
            "upload_date": document.upload_date.isoformat(),
            "processed_date": document.processed_date.isoformat() if document.processed_date else None,
            "page_count": document.page_count,
            "metadata": document.metadata,
            "jobs": [
                {
                    "id": str(job.id),
                    "job_type": job.job_type,
                    "status": job.status,
                    "created_at": job.created_at.isoformat(),
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "error_message": job.error_message
                }
                for job in jobs
            ]
        }
    
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )


@router.get(
    "/{document_id}/download",
    summary="문서 다운로드",
    description="""
    문서 파일을 다운로드합니다.

    **응답:**
    - 원본 파일명과 함께 파일이 다운로드됩니다
    - Content-Type 헤더에 적절한 MIME 타입이 설정됩니다
    - Content-Disposition 헤더로 파일명이 설정됩니다

    **권한:**
    - 문서 소유자만 다운로드 가능
    - 다른 사용자의 문서 다운로드 시 403 Forbidden 반환

    **보안:**
    - 파일 경로 검증을 통해 디렉토리 탐색 공격 방지
    - UUID 기반 파일명으로 저장되어 직접 접근 불가
    """,
    responses={
        200: {
            "description": "문서 다운로드 성공",
            "content": {
                "application/octet-stream": {
                    "schema": {
                        "type": "string",
                        "format": "binary"
                    }
                }
            }
        },
        403: {
            "description": "권한 없음 - 문서 소유자가 아님",
            "model": DocumentErrorResponse
        },
        404: {
            "description": "문서를 찾을 수 없음",
            "model": DocumentErrorResponse
        }
    }
)
async def download_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> FileResponse:
    """문서 다운로드 API"""
    try:
        # 문서 조회
        document = get_document(db, document_id)
        
        # 소유자 확인
        if document.uploaded_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 문서에 대한 접근 권한이 없습니다."
            )
        
        # 파일 경로 조회
        file_path = get_document_file_path(document)
        
        # 파일 응답
        return FileResponse(
            path=file_path,
            filename=document.original_filename,
            media_type=document.mime_type
        )
    
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="문서 삭제",
    description="""
    문서를 삭제합니다.

    **삭제 대상:**
    - 데이터베이스의 문서 레코드
    - 저장된 파일
    - 관련된 추출 데이터
    - 관련된 처리 작업 기록

    **권한:**
    - 문서 소유자만 삭제 가능
    - 다른 사용자의 문서 삭제 시 403 Forbidden 반환

    **주의:**
    - 삭제된 문서는 복구할 수 없습니다
    - 진행 중인 처리 작업이 있는 경우에도 삭제됩니다

    **응답:**
    - 성공 시 204 No Content 반환
    """,
    responses={
        204: {
            "description": "문서 삭제 성공"
        },
        403: {
            "description": "권한 없음 - 문서 소유자가 아님",
            "model": DocumentErrorResponse
        },
        404: {
            "description": "문서를 찾을 수 없음",
            "model": DocumentErrorResponse
        }
    }
)
async def delete_document_endpoint(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> None:
    """문서 삭제 API"""
    try:
        # 문서 조회
        document = get_document(db, document_id)
        
        # 소유자 확인
        if document.uploaded_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 문서에 대한 접근 권한이 없습니다."
            )
        
        # 문서 삭제
        delete_document(db, document_id, current_user.id)
    
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
