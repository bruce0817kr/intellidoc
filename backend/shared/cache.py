"""
Redis 캐싱 유틸리티 모듈

주요 기능:
- 사용자 권한 캐싱
- 문서 메타데이터 캐싱
- API 응답 캐싱
"""

import json
import hashlib
from typing import Any, Optional, Callable
from functools import wraps
import redis

from shared.config import settings
from shared.logger import log_info, log_error


# Redis 클라이언트 초기화
try:
    redis_client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    # 연결 테스트
    redis_client.ping()
    log_info("Redis 연결 성공")
except Exception as e:
    log_error(f"Redis 연결 실패: {str(e)}")
    redis_client = None


class CacheManager:
    """캐시 관리자"""

    def __init__(self, client: Optional[redis.Redis] = None):
        self.client = client or redis_client
        self.default_ttl = 3600  # 1시간

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        if not self.client:
            return None

        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            log_error(f"캐시 조회 실패 ({key}): {str(e)}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """캐시에 값 저장"""
        if not self.client:
            return False

        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, default=str)
            self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            log_error(f"캐시 저장 실패 ({key}): {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        if not self.client:
            return False

        try:
            self.client.delete(key)
            return True
        except Exception as e:
            log_error(f"캐시 삭제 실패 ({key}): {str(e)}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """패턴에 매칭되는 모든 키 삭제"""
        if not self.client:
            return 0

        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            log_error(f"캐시 패턴 삭제 실패 ({pattern}): {str(e)}")
            return 0

    def exists(self, key: str) -> bool:
        """캐시 키 존재 여부 확인"""
        if not self.client:
            return False

        try:
            return bool(self.client.exists(key))
        except Exception as e:
            log_error(f"캐시 존재 확인 실패 ({key}): {str(e)}")
            return False


# 싱글톤 인스턴스
cache_manager = CacheManager()


def cache_key_builder(*args, **kwargs) -> str:
    """캐시 키 생성"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    key_string = ":".join(key_parts)

    # 해시로 변환 (긴 키 방지)
    if len(key_string) > 100:
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"cache:{key_hash}"

    return f"cache:{key_string}"


def cached(ttl: int = 3600, key_prefix: str = ""):
    """
    함수 결과를 캐싱하는 데코레이터

    Args:
        ttl: 캐시 TTL (초)
        key_prefix: 캐시 키 접두사

    Example:
        @cached(ttl=300, key_prefix="user_perms")
        def get_user_permissions(user_id: str):
            # ... DB 조회
            return permissions
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            key_parts = [key_prefix or func.__name__]
            key_parts.extend([str(arg) for arg in args])
            cache_key = cache_key_builder(*key_parts, **kwargs)

            # 캐시 조회
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                log_info(f"캐시 히트: {cache_key}")
                return cached_value

            # 함수 실행
            result = func(*args, **kwargs)

            # 캐시 저장
            cache_manager.set(cache_key, result, ttl=ttl)
            log_info(f"캐시 저장: {cache_key}")

            return result

        # 캐시 무효화 함수 추가
        def invalidate(*args, **kwargs):
            key_parts = [key_prefix or func.__name__]
            key_parts.extend([str(arg) for arg in args])
            cache_key = cache_key_builder(*key_parts, **kwargs)
            cache_manager.delete(cache_key)
            log_info(f"캐시 무효화: {cache_key}")

        wrapper.invalidate = invalidate
        return wrapper

    return decorator


# 특정 도메인용 캐시 함수
def cache_user_permissions(user_id: str, permissions: list, ttl: int = 300):
    """사용자 권한 캐싱"""
    key = f"user:permissions:{user_id}"
    cache_manager.set(key, permissions, ttl=ttl)


def get_cached_user_permissions(user_id: str) -> Optional[list]:
    """캐시된 사용자 권한 조회"""
    key = f"user:permissions:{user_id}"
    return cache_manager.get(key)


def invalidate_user_permissions(user_id: str):
    """사용자 권한 캐시 무효화"""
    key = f"user:permissions:{user_id}"
    cache_manager.delete(key)


def cache_document_metadata(document_id: str, metadata: dict, ttl: int = 600):
    """문서 메타데이터 캐싱"""
    key = f"document:metadata:{document_id}"
    cache_manager.set(key, metadata, ttl=ttl)


def get_cached_document_metadata(document_id: str) -> Optional[dict]:
    """캐시된 문서 메타데이터 조회"""
    key = f"document:metadata:{document_id}"
    return cache_manager.get(key)


def invalidate_document_cache(document_id: str):
    """문서 캐시 무효화 (메타데이터, 작업 등)"""
    pattern = f"document:*:{document_id}"
    deleted_count = cache_manager.delete_pattern(pattern)
    log_info(f"문서 캐시 무효화: {document_id} ({deleted_count}개 키 삭제)")
