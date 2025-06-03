"""
데이터베이스 연결 관리 모듈

- 연결 풀 설정
- 트랜잭션 관리
- 마이그레이션 스크립트
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from shared.config import settings

# 데이터베이스 엔진 생성
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # 연결 유효성 검사
    pool_size=10,        # 연결 풀 크기
    max_overflow=20,     # 최대 초과 연결 수
    pool_recycle=3600    # 연결 재활용 시간 (1시간)
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 베이스 클래스 (models.py에서 이미 정의됨)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    데이터베이스 세션을 제공하는 의존성 함수
    
    FastAPI 의존성 주입 시스템에서 사용
    
    Yields:
        Session: 데이터베이스 세션
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    """
    데이터베이스 초기화 함수
    
    애플리케이션 시작 시 호출
    """
    # 테이블 생성 (개발 환경에서만 사용, 운영 환경에서는 Alembic 사용)
    if settings.DEBUG:
        Base.metadata.create_all(bind=engine)

class DBTransaction:
    """
    데이터베이스 트랜잭션 컨텍스트 매니저
    
    with 문을 사용하여 트랜잭션 관리
    
    Example:
        with DBTransaction(db) as tx:
            db.add(user)
            db.add(document)
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.db.rollback()
        else:
            self.db.commit()
