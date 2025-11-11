"""
환경변수 및 보안 설정 테스트

주요 테스트:
- 프로덕션 환경 보안 검증
- 약한 비밀번호 감지
- 환경변수 누락 감지
"""

import pytest
import os
from unittest.mock import patch
from shared.config import Settings


class TestProductionSecurity:
    """프로덕션 환경 보안 검증 테스트"""

    def test_production_missing_secret_key(self):
        """SECRET_KEY 누락 시 실패 테스트"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "",
            "ENCRYPTION_SALT": "a" * 32,
            "DATABASE_URL": "postgresql://user:strongpass@db/intellidoc",
            "DEBUG": "false",
            "ALLOWED_HOSTS": "example.com",
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "SECRET_KEY 환경변수가 설정되지 않았습니다" in str(exc_info.value)

    def test_production_weak_secret_key(self):
        """약한 SECRET_KEY 사용 시 실패 테스트"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "short",
            "ENCRYPTION_SALT": "a" * 32,
            "DATABASE_URL": "postgresql://user:strongpass@db/intellidoc",
            "DEBUG": "false",
            "ALLOWED_HOSTS": "example.com",
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "SECRET_KEY가 너무 짧습니다" in str(exc_info.value)

    def test_production_insecure_default_secret_key(self):
        """기본값 SECRET_KEY 사용 시 실패 테스트"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "your-super-secret-key-here-please-change-this",
            "ENCRYPTION_SALT": "a" * 32,
            "DATABASE_URL": "postgresql://user:strongpass@db/intellidoc",
            "DEBUG": "false",
            "ALLOWED_HOSTS": "example.com",
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "안전하지 않은 기본값" in str(exc_info.value)

    def test_production_weak_database_password(self):
        """약한 데이터베이스 비밀번호 사용 시 실패 테스트"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "a" * 32,
            "ENCRYPTION_SALT": "b" * 32,
            "DATABASE_URL": "postgresql://intellidoc:intellidoc123@db/intellidoc",
            "DEBUG": "false",
            "ALLOWED_HOSTS": "example.com",
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "기본 자격 증명" in str(exc_info.value) or "약한 비밀번호" in str(exc_info.value)

    def test_production_debug_enabled(self):
        """프로덕션에서 DEBUG 모드 활성화 시 실패 테스트"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "a" * 32,
            "ENCRYPTION_SALT": "b" * 32,
            "DATABASE_URL": "postgresql://user:VeryStr0ng!Pass@db/intellidoc",
            "DEBUG": "true",
            "ALLOWED_HOSTS": "example.com",
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "DEBUG 모드가 활성화되어 있습니다" in str(exc_info.value)

    def test_production_wildcard_hosts(self):
        """ALLOWED_HOSTS 와일드카드 사용 시 실패 테스트"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "a" * 32,
            "ENCRYPTION_SALT": "b" * 32,
            "DATABASE_URL": "postgresql://user:VeryStr0ng!Pass@db/intellidoc",
            "DEBUG": "false",
            "ALLOWED_HOSTS": "*",
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "와일드카드" in str(exc_info.value)

    def test_production_localhost_in_cors(self):
        """ALLOWED_ORIGINS에 localhost 포함 시 실패 테스트"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "a" * 32,
            "ENCRYPTION_SALT": "b" * 32,
            "DATABASE_URL": "postgresql://user:VeryStr0ng!Pass@db/intellidoc",
            "DEBUG": "false",
            "ALLOWED_HOSTS": "example.com",
            "ALLOWED_ORIGINS": "http://localhost:3000",
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "localhost가 포함되어 있습니다" in str(exc_info.value)

    def test_production_valid_config(self):
        """유효한 프로덕션 설정 테스트"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "a" * 32,
            "ENCRYPTION_SALT": "b" * 32,
            "DATABASE_URL": "postgresql://user:VeryStr0ng!P@ssw0rd@db/intellidoc",
            "DEBUG": "false",
            "ALLOWED_HOSTS": "example.com,www.example.com",
            "ALLOWED_ORIGINS": "https://example.com",
        }, clear=True):
            # 예외가 발생하지 않아야 함
            settings = Settings()
            assert settings.ENVIRONMENT == "production"
            assert settings.DEBUG == False

    def test_development_relaxed_validation(self):
        """개발 환경에서는 검증 완화 테스트"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "SECRET_KEY": "dev-key",
            "DEBUG": "true",
        }, clear=True):
            # 개발 환경에서는 예외가 발생하지 않아야 함
            settings = Settings()
            assert settings.ENVIRONMENT == "development"
            assert settings.DEBUG == True


class TestEncryptionKeyDerivation:
    """암호화 키 유도 테스트"""

    def test_encryption_salt_missing_in_production(self):
        """프로덕션에서 ENCRYPTION_SALT 누락 시 실패 테스트"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "a" * 32,
            "ENCRYPTION_SALT": "",
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "ENCRYPTION_SALT" in str(exc_info.value)

    def test_encryption_key_generation(self):
        """암호화 키 생성 테스트"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "SECRET_KEY": "test-secret-key",
            "ENCRYPTION_SALT": "test-salt",
        }, clear=True):
            settings = Settings()
            # 암호화 키가 생성되었는지 확인
            assert settings._encryption_key is not None
            assert len(settings._encryption_key) > 0

    def test_api_key_encryption_decryption(self):
        """API 키 암호화/복호화 테스트"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "SECRET_KEY": "test-secret-key",
            "ENCRYPTION_SALT": "test-salt",
        }, clear=True):
            settings = Settings()

            # API 키 암호화
            original_key = "test-api-key-12345"
            encrypted_key = settings.encrypt_api_key(original_key)

            # 암호화되었는지 확인 (원본과 달라야 함)
            assert encrypted_key != original_key

            # 복호화 후 원본과 일치하는지 확인
            decrypted_key = settings.decrypt_api_key(encrypted_key)
            assert decrypted_key == original_key
