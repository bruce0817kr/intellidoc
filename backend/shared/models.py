"""
데이터베이스 모델 정의 모듈

필수 테이블:
1. users - 사용자 정보
2. documents - 문서 메타데이터
3. extracted_data - 추출된 데이터
4. processing_jobs - 작업 큐
5. audit_logs - 감사 로그
6. feedback - 학습 피드백
7. api_configurations - 동적 API 설정
8. system_settings - 시스템 설정
"""

import uuid
import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, Text, Enum, Table
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship

from shared.constants import DocumentStatus, JobStatus

Base = declarative_base()

# 사용자-역할 다대다 관계 테이블
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id')),
    Column('role_name', String(50), ForeignKey('roles.name'), nullable=False)
)

class User(Base):
    """사용자 모델"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(100), nullable=False)
    full_name = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # 관계 설정
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    documents = relationship("Document", back_populates="uploaded_by_user")
    sessions = relationship("UserSession", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    feedback = relationship("Feedback", back_populates="user")

class Role(Base):
    """역할 모델"""
    __tablename__ = "roles"
    
    name = Column(String(50), primary_key=True)
    description = Column(String(200), nullable=True)
    
    # 관계 설정
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", back_populates="role")

class Permission(Base):
    """권한 모델"""
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(50), ForeignKey("roles.name"), nullable=False)
    resource = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    
    # 관계 설정
    role = relationship("Role", back_populates="permissions")

class UserSession(Base):
    """사용자 세션 모델"""
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    refresh_token = Column(String(255), nullable=False, unique=True)
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 관계 설정
    user = relationship("User", back_populates="sessions")

class Document(Base):
    """문서 메타데이터 모델"""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)  # 바이트 단위
    file_type = Column(String(10), nullable=False)
    mime_type = Column(String(100), nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED, nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    upload_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    processed_date = Column(DateTime, nullable=True)
    page_count = Column(Integer, nullable=True)
    document_metadata = Column(JSONB, nullable=True)  # 추가 메타데이터 (renamed from metadata)
    
    # 관계 설정
    uploaded_by_user = relationship("User", back_populates="documents")
    extracted_data = relationship("ExtractedData", back_populates="document")
    processing_jobs = relationship("ProcessingJob", back_populates="document")
    feedback = relationship("Feedback", back_populates="document")

class ExtractedData(Base):
    """추출된 데이터 모델"""
    __tablename__ = "extracted_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    field_name = Column(String(100), nullable=False)
    field_value = Column(Text, nullable=True)
    field_type = Column(String(50), nullable=True)  # 문자열, 숫자, 날짜 등
    confidence_score = Column(Float, nullable=True)
    page_number = Column(Integer, nullable=True)
    bounding_box = Column(JSON, nullable=True)  # [x1, y1, x2, y2] 형식
    extraction_method = Column(String(50), nullable=False)  # OCR, LLM, 수동 등
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # 관계 설정
    document = relationship("Document", back_populates="extracted_data")

class ProcessingJob(Base):
    """처리 작업 모델"""
    __tablename__ = "processing_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    job_type = Column(String(50), nullable=False)  # OCR, LLM, 내보내기 등
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    result = Column(JSONB, nullable=True)
    parameters = Column(JSONB, nullable=True)  # 작업 파라미터
    
    # 관계 설정
    document = relationship("Document", back_populates="processing_jobs")

class AuditLog(Base):
    """감사 로그 모델"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    details = Column(JSONB, nullable=True)
    
    # 관계 설정
    user = relationship("User", back_populates="audit_logs")

class Feedback(Base):
    """피드백 모델"""
    __tablename__ = "feedback"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    feedback_type = Column(String(50), nullable=False)  # 정확도, 만족도 등
    rating = Column(Integer, nullable=True)  # 1-5 등급
    comment = Column(Text, nullable=True)
    original_value = Column(Text, nullable=True)
    corrected_value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 관계 설정
    document = relationship("Document", back_populates="feedback")
    user = relationship("User", back_populates="feedback")

class APIConfiguration(Base):
    """API 설정 모델"""
    __tablename__ = "api_configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    api_type = Column(String(50), nullable=False)  # OCR, LLM 등
    is_active = Column(Boolean, default=True)
    config = Column(JSONB, nullable=False)  # API 설정 (암호화된 키 포함)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

class SystemSetting(Base):
    """시스템 설정 모델"""
    __tablename__ = "system_settings"
    
    key = Column(String(100), primary_key=True)
    value = Column(JSONB, nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
