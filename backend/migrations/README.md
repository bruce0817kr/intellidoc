# Database Migrations

This directory contains database migration scripts for IntelliDoc.

## Migration Files

### 001_add_performance_indexes.sql

**Date**: 2025-11-11
**Purpose**: Phase 2 Performance Optimization - Add database indexes

**Changes**:
- Adds indexes to `user_sessions` table:
  - `user_id` - Improves session lookup performance
  - `expires_at` - Speeds up session cleanup queries

- Adds indexes to `documents` table:
  - `uploaded_by` - Improves user document queries
  - `status` - Speeds up status-based filtering

- Adds indexes to `extracted_data` table:
  - `document_id` - Eliminates N+1 queries when loading document data

- Adds indexes to `processing_jobs` table:
  - `document_id` - Eliminates N+1 queries when loading document jobs
  - `job_type` - Speeds up job type filtering
  - `status` - Speeds up status-based filtering

**Impact**:
- Significantly improves query performance for document and job listings
- Eliminates N+1 query problems identified in Phase 2
- Reduces database load for user-specific queries

## How to Apply Migrations

### Option 1: Using psql (Manual)

```bash
# Connect to your database
psql -U <username> -d <database_name>

# Run the migration
\i backend/migrations/001_add_performance_indexes.sql
```

### Option 2: Using Python Script

```bash
cd /home/user/intellidoc/backend
python migrations/apply_migration.py 001_add_performance_indexes.sql
```

### Option 3: Automatic on Startup (Development Only)

The indexes are already defined in the SQLAlchemy models (`backend/shared/models.py`).
When running in DEBUG mode, `Base.metadata.create_all()` will automatically create these indexes.

**Note**: This is only for development. In production, use explicit migrations.

## Verifying Indexes

After applying the migration, verify the indexes were created:

```sql
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
```

Expected output should include:
- `idx_user_sessions_user_id`
- `idx_user_sessions_expires_at`
- `idx_documents_uploaded_by`
- `idx_documents_status`
- `idx_extracted_data_document_id`
- `idx_processing_jobs_document_id`
- `idx_processing_jobs_job_type`
- `idx_processing_jobs_status`

## Performance Impact

These indexes specifically address:

1. **N+1 Query Problem**: Eager loading with `joinedload()` and `selectinload()` combined with these indexes eliminates N+1 queries in:
   - `backend/file_manager/service.py::get_user_documents()`
   - `backend/file_manager/service.py::get_document_jobs()`
   - `backend/auth/permissions.py::get_user_roles()`

2. **Query Optimization**: Indexes on frequently filtered columns (`status`, `job_type`) significantly improve query performance for:
   - Document status filtering
   - Job type and status filtering
   - Session expiration cleanup

## Future Migrations

When creating new migrations:

1. Use sequential numbering: `002_`, `003_`, etc.
2. Include date and description in the SQL file header
3. Use `IF NOT EXISTS` or `IF EXISTS` to make migrations idempotent
4. Update this README with migration details
5. Test on a development database before applying to production
