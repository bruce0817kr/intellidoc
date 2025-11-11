-- Migration: Add performance indexes for foreign keys and frequently queried columns
-- Date: 2025-11-11
-- Description: Adds indexes to improve query performance and eliminate N+1 query problems

-- ============================================================================
-- UserSession Table Indexes
-- ============================================================================

-- Index on user_id for faster session lookups by user
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id
ON user_sessions(user_id);

-- Index on expires_at for faster session cleanup queries
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at
ON user_sessions(expires_at);

-- ============================================================================
-- Document Table Indexes
-- ============================================================================

-- Index on uploaded_by for faster document lookups by user
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by
ON documents(uploaded_by);

-- Index on status for faster filtering by document status
CREATE INDEX IF NOT EXISTS idx_documents_status
ON documents(status);

-- ============================================================================
-- ExtractedData Table Indexes
-- ============================================================================

-- Index on document_id for faster extracted data lookups by document
CREATE INDEX IF NOT EXISTS idx_extracted_data_document_id
ON extracted_data(document_id);

-- ============================================================================
-- ProcessingJob Table Indexes
-- ============================================================================

-- Index on document_id for faster job lookups by document
CREATE INDEX IF NOT EXISTS idx_processing_jobs_document_id
ON processing_jobs(document_id);

-- Index on job_type for faster filtering by job type
CREATE INDEX IF NOT EXISTS idx_processing_jobs_job_type
ON processing_jobs(job_type);

-- Index on status for faster filtering by job status
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status
ON processing_jobs(status);

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- To verify indexes were created, run:
-- SELECT tablename, indexname, indexdef
-- FROM pg_indexes
-- WHERE schemaname = 'public'
-- AND indexname LIKE 'idx_%'
-- ORDER BY tablename, indexname;
