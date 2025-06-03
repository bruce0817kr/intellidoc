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

# 라우터 설정
router = APIRouter(prefix="/documents", tags=["문서"])


@router.post("/", response_model=Dict[str, Any])
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_process: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    문서 업로드 API
    
    Args:
        background_tasks: 백그라운드 작업
        file: 업로드할 파일
        auto_process: 자동 처리 여부
        db: 데이터베이스 세션
        current_user: 현재 사용자
        
    Returns:
        Dict[str, Any]: 업로드된 문서 정보
    """
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


@router.get("/", response_model=List[Dict[str, Any]])
async def get_documents(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> List[Dict[str, Any]]:
    """
    문서 목록 조회 API
    
    Args:
        skip: 건너뛸 개수
        limit: 최대 개수
        status: 문서 상태 필터
        db: 데이터베이스 세션
        current_user: 현재 사용자
        
    Returns:
        List[Dict[str, Any]]: 문서 목록
    """
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


@router.get("/{document_id}", response_model=Dict[str, Any])
async def get_document_details(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    문서 상세 조회 API
    
    Args:
        document_id: 문서 ID
        db: 데이터베이스 세션
        current_user: 현재 사용자
        
    Returns:
        Dict[str, Any]: 문서 상세 정보
    """
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


@router.get("/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> FileResponse:
    """
    문서 다운로드 API
    
    Args:
        document_id: 문서 ID
        db: 데이터베이스 세션
        current_user: 현재 사용자
        
    Returns:
        FileResponse: 파일 응답
    """
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


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_endpoint(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> None:
    """
    문서 삭제 API
    
    Args:
        document_id: 문서 ID
        db: 데이터베이스 세션
        current_user: 현재 사용자
    """
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
