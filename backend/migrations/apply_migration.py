#!/usr/bin/env python3
"""
데이터베이스 마이그레이션 적용 스크립트

Usage:
    python migrations/apply_migration.py <migration_file>

Example:
    python migrations/apply_migration.py 001_add_performance_indexes.sql
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from shared.database import engine
from shared.logger import log_info, log_error


def apply_sql_migration(migration_file: str) -> bool:
    """
    SQL 마이그레이션 파일 적용

    Args:
        migration_file: 마이그레이션 파일명 또는 경로

    Returns:
        bool: 성공 여부
    """
    try:
        # 마이그레이션 파일 경로 확인
        migration_path = Path(__file__).parent / migration_file

        if not migration_path.exists():
            log_error(f"마이그레이션 파일을 찾을 수 없습니다: {migration_path}")
            return False

        # SQL 파일 읽기
        with open(migration_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # 데이터베이스 연결 및 실행
        with engine.connect() as connection:
            # 트랜잭션 시작
            with connection.begin():
                # SQL 문을 개별적으로 실행 (세미콜론으로 분리)
                statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]

                for i, statement in enumerate(statements, 1):
                    # 주석만 있는 라인 건너뛰기
                    if statement.startswith('--'):
                        continue

                    try:
                        connection.execute(text(statement))
                        log_info(f"Statement {i}/{len(statements)} 실행 완료")
                    except Exception as stmt_error:
                        # IF NOT EXISTS를 사용하므로 일부 에러는 무시 가능
                        if "already exists" in str(stmt_error).lower():
                            log_info(f"Statement {i}: 이미 존재함 (건너뛰기)")
                        else:
                            raise

        log_info(f"마이그레이션 적용 완료: {migration_file}")
        return True

    except Exception as e:
        log_error(f"마이그레이션 적용 실패: {str(e)}", exc_info=True)
        return False


def verify_indexes() -> None:
    """생성된 인덱스 확인"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT tablename, indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                AND indexname LIKE 'idx_%'
                ORDER BY tablename, indexname
            """))

            indexes = result.fetchall()

            if indexes:
                log_info(f"\n생성된 인덱스 ({len(indexes)}개):")
                for table, index in indexes:
                    log_info(f"  - {table}.{index}")
            else:
                log_info("생성된 인덱스가 없습니다.")

    except Exception as e:
        log_error(f"인덱스 확인 실패: {str(e)}")


def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("Usage: python apply_migration.py <migration_file>")
        print("Example: python apply_migration.py 001_add_performance_indexes.sql")
        sys.exit(1)

    migration_file = sys.argv[1]

    log_info(f"마이그레이션 적용 시작: {migration_file}")

    if apply_sql_migration(migration_file):
        log_info("마이그레이션이 성공적으로 적용되었습니다.")
        verify_indexes()
        sys.exit(0)
    else:
        log_error("마이그레이션 적용에 실패했습니다.")
        sys.exit(1)


if __name__ == "__main__":
    main()
