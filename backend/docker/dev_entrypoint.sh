#!/bin/sh
# IntelliDoc 백엔드 개발용 엔트리포인트

set -e

echo "=== IntelliDoc 백엔드 개발 환경 시작 ==="

# 환경 변수 확인
echo "환경: $ENVIRONMENT"
echo "DEBUG: $DEBUG"

# 디렉토리 권한 설정
chmod -R 755 /app/uploads /app/logs

# 데이터베이스 연결 확인
echo "데이터베이스 연결 확인 중..."
python << END
import time
import sys
import psycopg2
from urllib.parse import urlparse
import os

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    sys.exit(1)

result = urlparse(db_url)
dbname = result.path[1:]
user = result.username
password = result.password
host = result.hostname
port = result.port

retries = 10
while retries > 0:
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.close()
        print("데이터베이스 연결 성공!")
        break
    except psycopg2.OperationalError as e:
        retries -= 1
        if retries == 0:
            print(f"데이터베이스 연결 실패: {e}")
            sys.exit(1)
        print(f"데이터베이스 연결 시도 중... (남은 시도: {retries})")
        time.sleep(2)
END

# Redis 연결 확인
echo "Redis 연결 확인 중..."
python << END
import time
import sys
import os
import redis

redis_url = os.environ.get('REDIS_URL')
if not redis_url:
    print("REDIS_URL 환경 변수가 설정되지 않았습니다.")
    sys.exit(1)

retries = 10
while retries > 0:
    try:
        r = redis.from_url(redis_url)
        r.ping()
        print("Redis 연결 성공!")
        break
    except redis.ConnectionError as e:
        retries -= 1
        if retries == 0:
            print(f"Redis 연결 실패: {e}")
            sys.exit(1)
        print(f"Redis 연결 시도 중... (남은 시도: {retries})")
        time.sleep(2)
END

# 개발 모드에서는 데이터베이스 마이그레이션 실행
if [ "$ENVIRONMENT" = "development" ] || [ "$DEBUG" = "true" ]; then
    echo "개발 환경 감지: 데이터베이스 마이그레이션 실행..."
    
    # 이 부분은 실제 마이그레이션 명령어로 대체하세요
    # python -m alembic upgrade head
    
    echo "개발용 초기 데이터 로드 중..."
    # python -m scripts.seed_dev_data
    
    echo "API 서버 시작 중 (개발 모드)..."
    exec uvicorn web_api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app
else
    echo "API 서버 시작 중..."
    exec uvicorn web_api.main:app --host 0.0.0.0 --port 8000
fi
