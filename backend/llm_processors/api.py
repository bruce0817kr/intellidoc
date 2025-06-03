"""
LLM API 엔드포인트 모듈

주요 기능:
1. LLM 처리 API
2. LLM 결과 조회 API
3. 프롬프트 템플릿 관리 API
"""

import uuid
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.models import User, Document
from shared.exceptions import LLMAPIError, ResourceNotFoundError
from auth.api import get_current_active_user
from auth.permissions import require_permission
from llm_processors.service import LLMService

# 라우터 설정
router = APIRouter(prefix="/llm", tags=["LLM"])


@router.post("/process/{document_id}", response_model=Dict[str, Any])
async def process_document(
    document_id: uuid.UUID,
    task_type: str,
    parameters: Optional[Dict[str, Any]] = None,
    background_tasks: BackgroundTasks = None,
    engine: str = "openai",
    async_mode: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    문서 LLM 처리 API
    
    Args:
        document_id: 문서 ID
        task_type: 작업 유형 (summary, extraction, classification, qa)
        parameters: 작업 파라미터
        background_tasks: 백그라운드 작업
        engine: LLM 엔진 이름
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
        
        # LLM 서비스 생성
        llm_service = LLMService(engine_name=engine)
        
        if async_mode and background_tasks:
            # 비동기 처리
            background_tasks.add_task(
                llm_service.process_document,
                db=db,
                document_id=document_id,
                task_type=task_type,
                parameters=parameters
            )
            
            return {
                "document_id": str(document_id),
                "task_type": task_type,
                "status": "processing",
                "message": "LLM 처리가 백그라운드에서 진행 중입니다."
            }
        else:
            # 동기 처리
            result = llm_service.process_document(
                db=db,
                document_id=document_id,
                task_type=task_type,
                parameters=parameters
            )
            return result
    
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except LLMAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )


@router.get("/results/{document_id}", response_model=Dict[str, Any])
async def get_llm_results(
    document_id: uuid.UUID,
    task_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    LLM 결과 조회 API
    
    Args:
        document_id: 문서 ID
        task_type: 작업 유형 필터
        db: 데이터베이스 세션
        current_user: 현재 사용자
        
    Returns:
        Dict[str, Any]: LLM 결과
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
        
        # LLM 결과 조회
        llm_service = LLMService()
        result = llm_service.get_document_llm_results(
            db=db,
            document_id=document_id,
            task_type=task_type
        )
        
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
    사용 가능한 LLM 엔진 목록 조회 API
    
    Args:
        current_user: 현재 사용자
        
    Returns:
        List[str]: 엔진 이름 목록
    """
    llm_service = LLMService()
    return llm_service.get_available_engines()


@router.get("/templates", response_model=List[Dict[str, Any]])
async def get_available_templates(
    current_user: User = Depends(get_current_active_user)
) -> List[Dict[str, Any]]:
    """
    사용 가능한 프롬프트 템플릿 목록 조회 API
    
    Args:
        current_user: 현재 사용자
        
    Returns:
        List[Dict[str, Any]]: 템플릿 목록
    """
    llm_service = LLMService()
    return llm_service.get_available_templates()


@router.post("/templates", response_model=Dict[str, Any])
@require_permission("settings.manage")
async def add_template(
    name: str,
    template: str,
    variables: List[str],
    description: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    프롬프트 템플릿 추가 API
    
    Args:
        name: 템플릿 이름
        template: 템플릿 문자열
        variables: 변수 이름 목록
        description: 템플릿 설명
        current_user: 현재 사용자
        
    Returns:
        Dict[str, Any]: 추가된 템플릿 정보
    """
    try:
        llm_service = LLMService()
        result = llm_service.add_template(
            name=name,
            template=template,
            variables=variables,
            description=description
        )
        
        return result
    
    except LLMAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.post("/engines/test", response_model=Dict[str, Any])
@require_permission("settings.manage")
async def test_llm_engine(
    engine: str,
    prompt: str,
    config: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    LLM 엔진 테스트 API
    
    Args:
        engine: 엔진 이름
        prompt: 테스트 프롬프트
        config: 엔진 설정
        current_user: 현재 사용자
        
    Returns:
        Dict[str, Any]: 테스트 결과
    """
    try:
        # LLM 서비스 생성
        llm_service = LLMService(engine_name=engine, config=config)
        
        # 테스트 생성
        result = llm_service.engine.generate(prompt)
        
        return {
            "engine": engine,
            "prompt": prompt,
            "response": result.text,
            "model": result.model,
            "tokens": result.tokens
        }
    
    except LLMAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message
        )
