"""
파일 관리 모듈

주요 기능:
1. 파일 업로드 처리
2. 파일 저장 및 관리
3. 파일 메타데이터 추출
4. 파일 처리 큐 관리
"""

import os
import uuid
import shutil
import datetime
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, BinaryIO

from sqlalchemy.orm import Session

from shared.config import settings
from shared.models import Document, ProcessingJob
from shared.constants import DocumentStatus, JobStatus, FileType
from shared.exceptions import ValidationError, ResourceNotFoundError
from shared.utils import generate_safe_filename, is_valid_file_extension, get_file_extension, get_mime_type
from shared.validators import validate_file_extension, validate_file_size
from shared.logger import log_info, log_error, log_audit


def create_upload_directories() -> None:
    """
    업로드 디렉토리 생성
    """
    upload_dir = Path(settings.UPLOAD_DIR)

    # 기본 업로드 디렉토리
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 연도/월 기반 하위 디렉토리
    today = datetime.datetime.now()
    year_month_dir = upload_dir / f"{today.year}" / f"{today.month:02d}"
    year_month_dir.mkdir(parents=True, exist_ok=True)


def get_file_upload_path(original_filename: str) -> Tuple[str, str]:
    """
    파일 업로드 경로 생성
    
    Args:
        original_filename: 원본 파일명
        
    Returns:
        Tuple[str, str]: (저장 경로, 안전한 파일명)
    """
    # 연도/월 기반 디렉토리 경로
    today = datetime.datetime.now()
    year_month_dir = Path(settings.UPLOAD_DIR) / f"{today.year}" / f"{today.month:02d}"

    # 안전한 파일명 생성
    safe_filename = generate_safe_filename(original_filename)

    # 전체 경로
    file_path = year_month_dir / safe_filename

    return str(file_path), safe_filename


def save_uploaded_file(file_content: BinaryIO, file_path: str) -> None:
    """
    업로드된 파일 저장
    
    Args:
        file_content: 파일 내용
        file_path: 저장 경로
    """
    # 디렉토리 확인
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # 파일 저장
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file_content, f)


def create_document_record(
    db: Session,
    original_filename: str,
    file_path: str,
    file_size: int,
    user_id: uuid.UUID
) -> Document:
    """
    문서 레코드 생성
    
    Args:
        db: 데이터베이스 세션
        original_filename: 원본 파일명
        file_path: 저장 경로
        file_size: 파일 크기
        user_id: 사용자 ID
        
    Returns:
        Document: 생성된 문서 객체
    """
    # 파일 확장자 및 MIME 타입
    file_ext = get_file_extension(original_filename)
    mime_type = get_mime_type(original_filename) or "application/octet-stream"

    # 파일명 추출
    safe_filename = os.path.basename(file_path)

    # 문서 레코드 생성
    document = Document(
        filename=safe_filename,
        original_filename=original_filename,
        file_path=file_path,
        file_size=file_size,
        file_type=file_ext,
        mime_type=mime_type,
        status=DocumentStatus.UPLOADED,
        uploaded_by=user_id,
        upload_date=datetime.datetime.utcnow()
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    log_info(f"문서 레코드 생성: {document.id}")
    log_audit(user_id, "upload", "document", str(document.id), {
        "filename": original_filename,
        "file_size": file_size,
        "file_type": file_ext
    })

    return document


def create_processing_job(
    db: Session,
    document_id: uuid.UUID,
    job_type: str,
    parameters: Optional[Dict[str, Any]] = None
) -> ProcessingJob:
    """
    처리 작업 생성
    
    Args:
        db: 데이터베이스 세션
        document_id: 문서 ID
        job_type: 작업 유형
        parameters: 작업 파라미터
        
    Returns:
        ProcessingJob: 생성된 작업 객체
    """
    job = ProcessingJob(
        document_id=document_id,
        job_type=job_type,
        status=JobStatus.PENDING,
        parameters=parameters or {}
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    log_info(f"처리 작업 생성: {job.id}, 문서: {document_id}, 유형: {job_type}")

    return job


def upload_file(
    db: Session,
    file_content: BinaryIO,
    original_filename: str,
    file_size: int,
    user_id: uuid.UUID,
    auto_process: bool = True
) -> Document:
    """
    파일 업로드 처리
    
    Args:
        db: 데이터베이스 세션
        file_content: 파일 내용
        original_filename: 원본 파일명
        file_size: 파일 크기
        user_id: 사용자 ID
        auto_process: 자동 처리 여부
        
    Returns:
        Document: 생성된 문서 객체
    """
    try:
        # 파일 유효성 검사
        validate_file_extension(original_filename)
        validate_file_size(file_size, settings.MAX_UPLOAD_SIZE)

        # 업로드 디렉토리 생성
        create_upload_directories()

        # 파일 저장 경로 생성
        file_path, _ = get_file_upload_path(original_filename)

        # 파일 저장
        save_uploaded_file(file_content, file_path)

        # 문서 레코드 생성
        document = create_document_record(db, original_filename, file_path, file_size, user_id)

        # 자동 처리 작업 생성
        if auto_process:
            # OCR 작업 생성
            create_processing_job(db, document.id, "ocr")

        return document

    except Exception as e:
        log_error(f"파일 업로드 실패: {str(e)}", exc_info=True)
        # 파일 삭제 시도
        try:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        raise


def get_document(db: Session, document_id: uuid.UUID) -> Document:
    """
    문서 조회
    
    Args:
        db: 데이터베이스 세션
        document_id: 문서 ID
        
    Returns:
        Document: 문서 객체
        
    Raises:
        ResourceNotFoundError: 문서를 찾을 수 없는 경우
    """
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise ResourceNotFoundError(message=f"문서를 찾을 수 없습니다: {document_id}")

    return document


def get_document_file_path(document: Document) -> str:
    """
    문서 파일 경로 조회
    
    Args:
        document: 문서 객체
        
    Returns:
        str: 파일 경로
        
    Raises:
        ResourceNotFoundError: 파일이 존재하지 않는 경우
    """
    file_path = document.file_path

    if not os.path.exists(file_path):
        raise ResourceNotFoundError(message=f"문서 파일을 찾을 수 없습니다: {document.id}")

    return file_path


def delete_document(db: Session, document_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """
    문서 삭제
    
    Args:
        db: 데이터베이스 세션
        document_id: 문서 ID
        user_id: 사용자 ID
        
    Raises:
        ResourceNotFoundError: 문서를 찾을 수 없는 경우
    """
    document = get_document(db, document_id)

    # 파일 삭제
    try:
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
    except Exception as e:
        log_error(f"문서 파일 삭제 실패: {str(e)}")

    # 문서 상태 변경
    document.status = DocumentStatus.DELETED
    db.commit()

    log_info(f"문서 삭제: {document_id}")
    log_audit(user_id, "delete", "document", str(document_id), {
        "filename": document.original_filename
    })


def get_user_documents(
    db: Session,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    status: Optional[DocumentStatus] = None
) -> List[Document]:
    """
    사용자 문서 목록 조회
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        skip: 건너뛸 개수
        limit: 최대 개수
        status: 문서 상태 필터
        
    Returns:
        List[Document]: 문서 목록
    """
    query = db.query(Document).filter(Document.uploaded_by == user_id)

    if status:
        query = query.filter(Document.status == status)
    else:
        # 삭제된 문서는 제외
        query = query.filter(Document.status != DocumentStatus.DELETED)

    # 최신 업로드 순으로 정렬
    query = query.order_by(Document.upload_date.desc())

    return query.offset(skip).limit(limit).all()


def get_document_jobs(
    db: Session,
    document_id: uuid.UUID,
    job_type: Optional[str] = None
) -> List[ProcessingJob]:
    """
    문서 작업 목록 조회
    
    Args:
        db: 데이터베이스 세션
        document_id: 문서 ID
        job_type: 작업 유형 필터
        
    Returns:
        List[ProcessingJob]: 작업 목록
    """
    query = db.query(ProcessingJob).filter(ProcessingJob.document_id == document_id)

    if job_type:
        query = query.filter(ProcessingJob.job_type == job_type)

    # 최신 작업 순으로 정렬
    query = query.order_by(ProcessingJob.created_at.desc())

    return query.all()


def update_document_status(db: Session, document_id: uuid.UUID, status: DocumentStatus) -> Document:
    """
    문서 상태 업데이트
    
    Args:
        db: 데이터베이스 세션
        document_id: 문서 ID
        status: 새 상태
        
    Returns:
        Document: 업데이트된 문서 객체
    """
    document = get_document(db, document_id)

    document.status = status

    if status == DocumentStatus.COMPLETED:
        document.processed_date = datetime.datetime.utcnow()

    db.commit()
    db.refresh(document)

    log_info(f"문서 상태 업데이트: {document_id}, 상태: {status}")

    return document


def update_job_status(
    db: Session,
    job_id: uuid.UUID,
    status: JobStatus,
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> ProcessingJob:
    """
    작업 상태 업데이트
    
    Args:
        db: 데이터베이스 세션
        job_id: 작업 ID
        status: 새 상태
        result: 작업 결과
        error_message: 오류 메시지
        
    Returns:
        ProcessingJob: 업데이트된 작업 객체
    """
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()

    if not job:
        raise ResourceNotFoundError(message=f"작업을 찾을 수 없습니다: {job_id}")

    job.status = status

    if status == JobStatus.STARTED and not job.started_at:
        job.started_at = datetime.datetime.utcnow()

    if status in (JobStatus.SUCCESS, JobStatus.FAILURE):
        job.completed_at = datetime.datetime.utcnow()

    if result:
        job.result = result

    if error_message:
        job.error_message = error_message

    db.commit()
    db.refresh(job)

    log_info(f"작업 상태 업데이트: {job_id}, 상태: {status}")

    return job


class FileManager:
    """파일 관리 서비스 클래스"""

    def __init__(self):
        # 보안 개선: 하드코드된 임시 디렉토리 대신 시스템 임시 디렉토리 사용
        import tempfile
        self.upload_dir = os.path.join(tempfile.gettempdir(), 'intellidoc_uploads')
        os.makedirs(self.upload_dir, exist_ok=True)

    def save_uploaded_file(self, file_data: bytes, filename: str) -> str:
        """업로드된 파일 저장"""
        try:
            # 안전한 파일명 생성
            safe_filename = self._sanitize_filename(filename)
            filepath = os.path.join(self.upload_dir, safe_filename)

            with open(filepath, 'wb') as f:
                f.write(file_data)

            return filepath

        except Exception as e:
            raise ValueError(f"파일 저장 실패: {str(e)}")

    def get_file_info(self, filepath: str) -> Dict[str, Any]:
        """파일 정보 조회"""
        try:
            file_path = Path(filepath)

            if not file_path.exists():
                raise ValueError(f"파일을 찾을 수 없습니다: {filepath}")

            stat = file_path.stat()
            mime_type, _ = mimetypes.guess_type(filepath)

            return {
                'filename': file_path.name,
                'size': stat.st_size,
                'mime_type': mime_type,
                'created_at': datetime.datetime.fromtimestamp(stat.st_ctime),
                'modified_at': datetime.datetime.fromtimestamp(stat.st_mtime)
            }

        except Exception as e:
            raise ValueError(f"파일 정보 조회 실패: {str(e)}")

    def delete_file(self, filepath: str) -> bool:
        """파일 삭제"""
        try:
            file_path = Path(filepath)

            if file_path.exists():
                file_path.unlink()
                return True

            return False

        except Exception as e:
            raise ValueError(f"파일 삭제 실패: {str(e)}")

    def _sanitize_filename(self, filename: str) -> str:
        """파일명 안전화"""
        # 기본적인 파일명 안전화
        safe_name = filename.replace('..', '').replace('/', '_').replace('\\', '_')
        return safe_name
