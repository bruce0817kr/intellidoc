"""
OCR API 엔드포인트 모듈

주요 기능:
1. OCR 처리 API
2. OCR 결과 조회 API
3. OCR 엔진 관리 API
4. 배치 처리 API
"""

import uuid
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.models import User, Document
from shared.exceptions import OCREngineError, ResourceNotFoundError
from auth.api import get_current_active_user
from auth.permissions import require_permission
from ocr_engines.service import OCRService
from ocr_engines.batch_processor import get_batch_processor, BatchJob
from pydantic import BaseModel

# 라우터 설정
router = APIRouter(prefix="/ocr", tags=["OCR"])


class BatchProcessRequest(BaseModel):
    """배치 처리 요청 모델"""
    document_ids: List[uuid.UUID]
    engine: str = "tesseract"
    options: Optional[Dict[str, Any]] = None


class BatchStatusResponse(BaseModel):
    """배치 상태 응답 모델"""
    batch_id: str
    status: str
    total_documents: int
    processed_documents: int
    failed_documents: int
    progress_percentage: float
    success_rate: float
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


@router.post("/process/{document_id}", response_model=Dict[str, Any])
async def process_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    engine: str = "tesseract",
    async_mode: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    문서 OCR 처리 API
    
    Args:
        document_id: 문서 ID
        background_tasks: 백그라운드 작업
        engine: OCR 엔진 이름
        async_mode: 비동기 처리 여부
        db: 데이터베이스 세션
        current_user: 현재 사용자
        
    Returns:
        Dict[str, Any]: 처리 결과 또는 작업 상태
    """
    try:
        # 문서 소유자 확인
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ResourceNotFoundError(message=f"문서를 찾을 수 없습니다: {document_id}")
        
        if document.uploaded_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 문서에 대한 접근 권한이 없습니다."
            )
        
        # OCR 서비스 생성
        ocr_service = OCRService(engine_name=engine)
        
        if async_mode:
            # 비동기 처리
            background_tasks.add_task(
                ocr_service.process_document,
                db=db,
                document_id=document_id
            )
            
            return {
                "document_id": str(document_id),
                "status": "processing",
                "message": "OCR 처리가 백그라운드에서 진행 중입니다."
            }
        else:
            # 동기 처리
            result = ocr_service.process_document(db=db, document_id=document_id)
            return result
    
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except OCREngineError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )


@router.get("/results/{document_id}", response_model=Dict[str, Any])
async def get_ocr_results(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    OCR 결과 조회 API
    
    Args:
        document_id: 문서 ID
        db: 데이터베이스 세션
        current_user: 현재 사용자
        
    Returns:
        Dict[str, Any]: OCR 결과
    """
    try:
        # 문서 소유자 확인
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ResourceNotFoundError(message=f"문서를 찾을 수 없습니다: {document_id}")
        
        if document.uploaded_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 문서에 대한 접근 권한이 없습니다."
            )
        
        # OCR 결과 조회
        ocr_service = OCRService()
        result = ocr_service.get_document_ocr_results(db=db, document_id=document_id)
        
        return result
    
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )


@router.get("/engines", response_model=List[str])
async def get_available_engines(
    current_user: User = Depends(get_current_active_user)
) -> List[str]:
    """
    사용 가능한 OCR 엔진 목록 조회 API
    
    Args:
        current_user: 현재 사용자
        
    Returns:
        List[str]: 엔진 이름 목록
    """
    ocr_service = OCRService()
    return ocr_service.get_available_engines()


@router.post("/engines/test", response_model=Dict[str, Any])
@require_permission("settings.manage")
async def test_ocr_engine(
    engine: str,
    config: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    OCR 엔진 테스트 API
    
    Args:
        engine: 엔진 이름
        config: 엔진 설정
        db: 데이터베이스 세션
        current_user: 현재 사용자
        
    Returns:
        Dict[str, Any]: 테스트 결과
    """
    try:
        # OCR 서비스 생성
        ocr_service = OCRService(engine_name=engine, config=config)
        
        # 테스트 결과
        return {
            "engine": engine,
            "status": "available",
            "message": "OCR 엔진이 정상적으로 초기화되었습니다."
        }
    
    except OCREngineError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )


@router.post("/batch/process", response_model=Dict[str, Any])
async def create_batch_process(
    request: BatchProcessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    배치 OCR 처리 시작 API
    
    Args:
        request: 배치 처리 요청
        background_tasks: 백그라운드 작업
        db: 데이터베이스 세션
        current_user: 현재 사용자
        
    Returns:
        Dict[str, Any]: 배치 작업 정보
    """
    try:
        # 문서 소유자 확인
        for document_id in request.document_ids:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"문서를 찾을 수 없습니다: {document_id}"
                )
            if document.uploaded_by != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"문서에 대한 접근 권한이 없습니다: {document_id}"
                )
        
        # 배치 처리기 가져오기
        batch_processor = get_batch_processor()
        
        # 배치 작업 생성
        batch_id = batch_processor.create_batch_job(
            document_ids=request.document_ids,
            engine_name=request.engine,
            options=request.options
        )
        
        # 배치 처리 함수 정의
        def process_document_batch(doc_id: uuid.UUID, engine: str, options: Dict[str, Any]):
            ocr_service = OCRService(engine_name=engine, config=options)
            return ocr_service.process_document(db=db, document_id=doc_id)
        
        # 백그라운드에서 배치 처리 시작
        background_tasks.add_task(
            batch_processor.process_batch,
            batch_id,
            process_document_batch
        )
        
        return {
            "status": "success",
            "data": {
                "batch_id": batch_id,
                "total_documents": len(request.document_ids),
                "engine": request.engine,
                "status": "pending",
                "message": "배치 처리가 시작되었습니다."
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"배치 처리 생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/batch/{batch_id}/status", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: str,
    current_user: User = Depends(get_current_active_user)
) -> BatchStatusResponse:
    """
    배치 처리 상태 조회 API
    
    Args:
        batch_id: 배치 작업 ID
        current_user: 현재 사용자
        
    Returns:
        BatchStatusResponse: 배치 상태 정보
    """
    try:
        batch_processor = get_batch_processor()
        batch_job = batch_processor.get_batch_status(batch_id)
        
        if not batch_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"배치 작업을 찾을 수 없습니다: {batch_id}"
            )
        
        return BatchStatusResponse(
            batch_id=batch_job.id,
            status=batch_job.status.value,
            total_documents=batch_job.total_documents,
            processed_documents=batch_job.processed_documents,
            failed_documents=batch_job.failed_documents,
            progress_percentage=batch_job.progress_percentage,
            success_rate=batch_job.success_rate,
            created_at=batch_job.created_at.isoformat(),
            started_at=batch_job.started_at.isoformat() if batch_job.started_at else None,
            completed_at=batch_job.completed_at.isoformat() if batch_job.completed_at else None,
            error_message=batch_job.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"배치 상태 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/batch/{batch_id}/results", response_model=Dict[str, Any])
async def get_batch_results(
    batch_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    배치 처리 결과 조회 API
    
    Args:
        batch_id: 배치 작업 ID
        current_user: 현재 사용자
        
    Returns:
        Dict[str, Any]: 배치 처리 결과
    """
    try:
        batch_processor = get_batch_processor()
        batch_job = batch_processor.get_batch_status(batch_id)
        
        if not batch_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"배치 작업을 찾을 수 없습니다: {batch_id}"
            )
        
        return {
            "status": "success",
            "data": {
                "batch_id": batch_job.id,
                "status": batch_job.status.value,
                "total_documents": batch_job.total_documents,
                "processed_documents": batch_job.processed_documents,
                "failed_documents": batch_job.failed_documents,
                "success_rate": batch_job.success_rate,
                "results": batch_job.results,
                "created_at": batch_job.created_at.isoformat(),
                "completed_at": batch_job.completed_at.isoformat() if batch_job.completed_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"배치 결과 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.delete("/batch/{batch_id}", response_model=Dict[str, Any])
async def cancel_batch_process(
    batch_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    배치 처리 취소 API
    
    Args:
        batch_id: 배치 작업 ID
        current_user: 현재 사용자
        
    Returns:
        Dict[str, Any]: 취소 결과
    """
    try:
        batch_processor = get_batch_processor()
        success = batch_processor.cancel_batch(batch_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"취소할 수 있는 배치 작업을 찾을 수 없습니다: {batch_id}"
            )
        
        return {
            "status": "success",
            "data": {
                "batch_id": batch_id,
                "message": "배치 처리가 취소되었습니다."
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"배치 취소 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/batch/active", response_model=List[BatchStatusResponse])
async def get_active_batches(
    current_user: User = Depends(get_current_active_user)
) -> List[BatchStatusResponse]:
    """
    활성 배치 목록 조회 API
    
    Args:
        current_user: 현재 사용자
        
    Returns:
        List[BatchStatusResponse]: 활성 배치 목록
    """
    try:
        batch_processor = get_batch_processor()
        active_batches = batch_processor.get_active_batches()
        
        return [
            BatchStatusResponse(
                batch_id=batch.id,
                status=batch.status.value,
                total_documents=batch.total_documents,
                processed_documents=batch.processed_documents,
                failed_documents=batch.failed_documents,
                progress_percentage=batch.progress_percentage,
                success_rate=batch.success_rate,
                created_at=batch.created_at.isoformat(),
                started_at=batch.started_at.isoformat() if batch.started_at else None,
                completed_at=batch.completed_at.isoformat() if batch.completed_at else None,
                error_message=batch.error_message
            )
            for batch in active_batches
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"활성 배치 조회 중 오류가 발생했습니다: {str(e)}"
        )
