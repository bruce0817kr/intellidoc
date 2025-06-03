-- IntelliDoc 개발용 데이터베이스 초기화 스크립트
-- PostgreSQL 초기화 스크립트 (Docker 컨테이너 첫 실행 시 자동 실행)

-- UTF8 인코딩 설정
SET client_encoding = 'UTF8';

-- 개발 전용 스키마 생성
CREATE SCHEMA IF NOT EXISTS dev;
COMMENT ON SCHEMA dev IS 'IntelliDoc 개발용 스키마';

-- 필요한 확장 모듈 설치
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 텍스트 검색용
CREATE EXTENSION IF NOT EXISTS "ltree";    -- 계층 구조용

-- 사용자 테이블
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 문서 테이블
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    file_type VARCHAR(50),
    content_type VARCHAR(50),
    page_count INTEGER DEFAULT 1,
    ocr_engine VARCHAR(50),
    is_processed BOOLEAN DEFAULT FALSE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 문서 콘텐츠 테이블 (페이지별 OCR 결과)
CREATE TABLE IF NOT EXISTS document_contents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    content TEXT,
    language VARCHAR(10),
    confidence FLOAT,
    UNIQUE (document_id, page_number)
);

-- 배치 작업 테이블
CREATE TABLE IF NOT EXISTS batch_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    job_type VARCHAR(50) NOT NULL,
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    success_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 개발용 테스트 사용자 추가
INSERT INTO users (username, email, password_hash, full_name, is_active, is_admin)
VALUES
    ('admin', 'admin@example.com', '$2b$12$Ih/iZ0CxmX/QyD3cooisPeGLFMpTGYRHH8WH0viUu0XO8OPyO4Q1G', '관리자', true, true),
    ('user', 'user@example.com', '$2b$12$dHN0Y3eUG3GOJzb.8tmZoekTq9FMML2i9riJ76fJBFP.CN01xnwUK', '일반 사용자', true, false)
ON CONFLICT (username) DO NOTHING;

-- 권한 부여
ALTER TABLE users OWNER TO intellidoc;
ALTER TABLE documents OWNER TO intellidoc;
ALTER TABLE document_contents OWNER TO intellidoc;
ALTER TABLE batch_jobs OWNER TO intellidoc;

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_documents_created_by ON documents(created_by);
CREATE INDEX IF NOT EXISTS idx_document_contents_document_id ON document_contents(document_id);
CREATE INDEX IF NOT EXISTS idx_batch_jobs_status ON batch_jobs(status);
CREATE INDEX IF NOT EXISTS idx_batch_jobs_created_by ON batch_jobs(created_by);
