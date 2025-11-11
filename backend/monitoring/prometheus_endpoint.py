"""
Prometheus 메트릭 엔드포인트

주요 기능:
- /metrics 엔드포인트 제공
- 시스템 메트릭 자동 수집
- 주기적 통계 업데이트
"""

from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
from prometheus_client import multiprocess, generate_latest as generate_latest_multiprocess
import os

from shared.metrics import (
    set_app_info,
    update_active_sessions,
    update_documents_by_status,
)
from shared.config import settings


router = APIRouter(prefix="/monitoring", tags=["모니터링"])


@router.get("/metrics")
async def metrics():
    """
    Prometheus 메트릭 엔드포인트

    Returns:
        Response: Prometheus 메트릭 데이터
    """
    # 애플리케이션 정보 설정
    set_app_info(
        version="1.0.0",
        environment=settings.ENVIRONMENT
    )

    # 메트릭 생성
    metrics_data = generate_latest()

    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )


@router.get("/health")
async def health_check():
    """
    헬스 체크 엔드포인트

    Returns:
        dict: 헬스 체크 결과
    """
    # TODO: 데이터베이스, Redis 연결 상태 확인
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


@router.get("/ready")
async def readiness_check():
    """
    준비 상태 체크 엔드포인트

    Returns:
        dict: 준비 상태 결과
    """
    # TODO: 필수 서비스 준비 상태 확인
    return {
        "status": "ready",
        "version": "1.0.0"
    }


async def update_system_metrics():
    """
    주기적으로 시스템 메트릭 업데이트

    Celery Beat 또는 별도 스케줄러로 실행
    """
    from sqlalchemy import func
    from shared.database import SessionLocal
    from shared.models import UserSession, Document
    from shared.constants import DocumentStatus

    db = SessionLocal()

    try:
        # 활성 세션 수
        active_session_count = db.query(func.count(UserSession.id)).filter(
            UserSession.expires_at > func.now()
        ).scalar()
        update_active_sessions(active_session_count or 0)

        # 상태별 문서 수
        for status in DocumentStatus:
            doc_count = db.query(func.count(Document.id)).filter(
                Document.status == status
            ).scalar()
            update_documents_by_status(status.value, doc_count or 0)

    finally:
        db.close()
