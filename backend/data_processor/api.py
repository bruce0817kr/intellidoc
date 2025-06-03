"""
데이터 처리 API 엔드포인트 모듈

주요 기능:
1. 데이터 처리 API
2. 데이터 조회 API
3. 데이터 매핑 API
"""

import uuid
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.models import User, Document
from shared.exceptions import DataProcessingError, ResourceNotFoundError
from auth.api import get_current_active_user
from data_processor.service import DataProcessor, DataMapper

# 라우터 설정
router = APIRouter(prefix="/data", tags=["데이터"])


@router.post("/process/{document_id}", response_model=Dict[str, Any])
async def process_document_data(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    async_mode: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    문서 데이터 처리 API
    
    Args:
        document_id: 문서 ID
        background_tasks: 백그라운드 작업
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
        
        # 데이터 처리기 생성
        data_processor = DataProcessor()
        
        if async_mode:
            # 비동기 처리
            background_tasks.add_task(
                data_processor.process_document_data,
                db=db,
                document_id=document_id
            )
            
            return {
                "document_id": str(document_id),
                "status": "processing",
                "message": "데이터 처리가 백그라운드에서 진행 중입니다."
            }
        else:
            # 동기 처리
            result = data_processor.process_document_data(db=db, document_id=document_id)
            return {
                "document_id": str(document_id),
                "status": "success",
                "data": result
            }
    
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except DataProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )


@router.get("/{document_id}", response_model=Dict[str, Any])
async def get_document_data(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    문서 데이터 조회 API
    
    Args:
        document_id: 문서 ID
        db: 데이터베이스 세션
        current_user: 현재 사용자
        
    Returns:
        Dict[str, Any]: 문서 데이터
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
        
        # 데이터 조회
        data_processor = DataProcessor()
        result = data_processor.get_document_data(db=db, document_id=document_id)
        
        return result
    
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )


@router.post("/{document_id}/map", response_model=Dict[str, Any])
async def map_document_data(
    document_id: uuid.UUID,
    target_schema: str,
    mapping_config: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    문서 데이터 매핑 API
    
    Args:
        document_id: 문서 ID
        target_schema: 대상 스키마
        mapping_config: 매핑 설정
        db: 데이터베이스 세션
        current_user: 현재 사용자
        
    Returns:
        Dict[str, Any]: 매핑된 데이터
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
        
        # 데이터 조회
        data_processor = DataProcessor()
        document_data = data_processor.get_document_data(db=db, document_id=document_id)
        
        # 데이터 매핑
        data_mapper = DataMapper(mapping_config)
        mapped_data = data_mapper.map_data(
            data=document_data.get("data", {}),
            target_schema=target_schema
        )
        
        return {
            "document_id": str(document_id),
            "target_schema": target_schema,
            "mapped_data": mapped_data
        }
    
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except DataProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
