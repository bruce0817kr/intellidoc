"""
내보내기 API 엔드포인트 모듈

주요 기능:
1. 엑셀 내보내기 API
2. CSV 내보내기 API
3. PDF 내보내기 API
"""

import uuid
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.models import User, Document
from shared.exceptions import ExportError, ResourceNotFoundError
from auth.api import get_current_active_user
from data_processor.service import DataProcessor
from export.service import ExportManager

# 라우터 설정
router = APIRouter(prefix="/export", tags=["내보내기"])


@router.get("/{document_id}/excel", response_class=FileResponse)
async def export_to_excel(
    document_id: uuid.UUID,
    filename: Optional[str] = None,
    sheet_name: str = "Data",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> FileResponse:
    """
    엑셀 내보내기 API
    
    Args:
        document_id: 문서 ID
        filename: 파일명 (선택 사항)
        sheet_name: 시트명
        db: 데이터베이스 세션
        current_user: 현재 사용자
        
    Returns:
        FileResponse: 엑셀 파일 응답
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
        
        # 파일명 설정
        if not filename:
            filename = f"{document.original_filename.split('.')[0]}_export.xlsx"
        
        # 엑셀 내보내기
        export_manager = ExportManager()
        file_path = export_manager.export_to_excel(
            data=document_data,
            filename=filename,
            sheet_name=sheet_name
        )
        
        # 파일 응답
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except ExportError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )


@router.get("/{document_id}/csv", response_class=FileResponse)
async def export_to_csv(
    document_id: uuid.UUID,
    filename: Optional[str] = None,
    delimiter: str = ",",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> FileResponse:
    """
    CSV 내보내기 API
    
    Args:
        document_id: 문서 ID
        filename: 파일명 (선택 사항)
        delimiter: 구분자
        db: 데이터베이스 세션
        current_user: 현재 사용자
        
    Returns:
        FileResponse: CSV 파일 응답
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
        
        # 파일명 설정
        if not filename:
            filename = f"{document.original_filename.split('.')[0]}_export.csv"
        
        # CSV 내보내기
        export_manager = ExportManager()
        file_path = export_manager.export_to_csv(
            data=document_data,
            filename=filename,
            delimiter=delimiter
        )
        
        # 파일 응답
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="text/csv"
        )
    
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except ExportError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )


@router.get("/{document_id}/pdf", response_class=FileResponse)
async def export_to_pdf(
    document_id: uuid.UUID,
    filename: Optional[str] = None,
    template: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> FileResponse:
    """
    PDF 내보내기 API
    
    Args:
        document_id: 문서 ID
        filename: 파일명 (선택 사항)
        template: PDF 템플릿 경로
        db: 데이터베이스 세션
        current_user: 현재 사용자
        
    Returns:
        FileResponse: PDF 파일 응답
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
        
        # 파일명 설정
        if not filename:
            filename = f"{document.original_filename.split('.')[0]}_export.pdf"
        
        # PDF 내보내기
        export_manager = ExportManager()
        file_path = export_manager.export_to_pdf(
            data=document_data,
            filename=filename,
            template=template
        )
        
        # 파일 응답
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/pdf"
        )
    
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except ExportError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )
