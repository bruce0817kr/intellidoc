-- Migration: Add composite indexes for better query performance
-- Date: 2025-11-11
-- Description: Adds composite indexes to optimize common query patterns

-- ============================================================================
-- Document Table Composite Indexes
-- ============================================================================

-- Composite index for filtering documents by user and status
-- Usage: SELECT * FROM documents WHERE uploaded_by = ? AND status = ?
CREATE INDEX IF NOT EXISTS idx_documents_user_status
ON documents(uploaded_by, status);

-- ============================================================================
-- ProcessingJob Table Composite Indexes
-- ============================================================================

-- Composite index for filtering jobs by document and status
-- Usage: SELECT * FROM processing_jobs WHERE document_id = ? AND status = ?
CREATE INDEX IF NOT EXISTS idx_processing_jobs_doc_status
ON processing_jobs(document_id, status);

-- Composite index for filtering jobs by type and status
-- Usage: SELECT * FROM processing_jobs WHERE job_type = ? AND status = ?
CREATE INDEX IF NOT EXISTS idx_processing_jobs_type_status
ON processing_jobs(job_type, status);

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- To verify indexes were created, run:
-- SELECT tablename, indexname, indexdef
-- FROM pg_indexes
-- WHERE schemaname = 'public'
-- AND indexname LIKE 'idx_%composite%' OR indexname LIKE 'idx_%user_status' OR indexname LIKE 'idx_%doc_status' OR indexname LIKE 'idx_%type_status'
-- ORDER BY tablename, indexname;

-- To check index usage statistics:
-- SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
-- FROM pg_stat_user_indexes
-- WHERE indexname LIKE 'idx_%'
-- ORDER BY idx_scan DESC;
