"""
환경변수 및 설정 관리 모듈

- DATABASE_URL, REDIS_URL 등 환경변수 로드
- API 키 암호화 저장/로드 기능
- 동적 설정 업데이트 지원
"""

import os
import json
import base64
from typing import Dict, Any, Optional
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class Settings:
    """애플리케이션 설정 관리 클래스"""

    # 프로덕션에서 금지된 기본값 패턴
    INSECURE_DEFAULTS = {
        "SECRET_KEY": [
            "your-super-secret-key-here-please-change-this",
            "your-jwt-secret-key-here",
            "change-me",
            "replace-me",
            "please-change-this",
        ],
        "ENCRYPTION_SALT": [
            "your-unique-encryption-salt-minimum-32-characters-long",
            "intellidoc_salt",
            "change-me",
        ],
        "DATABASE_PASSWORD": [
            "intellidoc123",
            "password",
            "postgres",
            "admin",
            "123456",
        ],
    }

    def __init__(self):
        """설정 초기화"""
        # 기본 설정
        self.PROJECT_NAME = "IntelliDoc"
        self.API_V1_PREFIX = "/api/v1"
        self.DEBUG = self._parse_bool(os.getenv("DEBUG", "False"))
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

        # 데이터베이스 설정
        self.DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql://intellidoc:intellidoc123@localhost:5432/intellidoc"
        )

        # Redis 및 Celery 설정
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", self.REDIS_URL)
        self.CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", self.REDIS_URL)

        # 보안 설정
        self.SECRET_KEY = os.getenv("SECRET_KEY", self._generate_secret_key())
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
        self.REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

        # CORS 설정
        self.ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
        self.ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

        # 파일 업로드 설정
        self.UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(Path(__file__).parent.parent.parent / "uploads"))
        self.MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(100 * 1024 * 1024)))  # 100MB

        # API 키 암호화 설정
        self._encryption_key = self._derive_encryption_key(self.SECRET_KEY)

        # 동적 설정 로드
        self.dynamic_settings = self._load_dynamic_settings()

        # 프로덕션 환경 보안 검증
        if self.ENVIRONMENT == "production":
            self._validate_production_security()
    
    def _parse_bool(self, value: str) -> bool:
        """문자열을 불리언으로 변환"""
        return value.lower() in ("true", "1", "t", "yes", "y")
    
    def _generate_secret_key(self) -> str:
        """랜덤 시크릿 키 생성"""
        return base64.urlsafe_b64encode(os.urandom(32)).decode()
    
    def _derive_encryption_key(self, secret_key: str) -> bytes:
        """시크릿 키로부터 암호화 키 유도"""
        # 환경변수에서 솔트 로드 (없으면 랜덤 생성 후 경고)
        salt_str = os.getenv("ENCRYPTION_SALT")

        if not salt_str:
            # 개발 환경에서만 기본값 사용, 프로덕션에서는 반드시 설정 필요
            if self.ENVIRONMENT == "production":
                raise ValueError(
                    "ENCRYPTION_SALT 환경변수가 설정되지 않았습니다. "
                    "프로덕션 환경에서는 반드시 설정해야 합니다."
                )
            # 개발 환경 기본값 (보안 경고)
            salt_str = "intellidoc_dev_salt_CHANGE_THIS_IN_PRODUCTION"
            print("⚠️  경고: ENCRYPTION_SALT가 설정되지 않아 개발용 기본값을 사용합니다.")

        salt = salt_str.encode()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
        return key
    
    def _validate_production_security(self) -> None:
        """프로덕션 환경 보안 설정 검증"""
        errors = []

        # SECRET_KEY 검증
        secret_key = os.getenv("SECRET_KEY", "")
        if not secret_key:
            errors.append("SECRET_KEY 환경변수가 설정되지 않았습니다.")
        elif secret_key in self.INSECURE_DEFAULTS["SECRET_KEY"]:
            errors.append(f"SECRET_KEY가 안전하지 않은 기본값으로 설정되어 있습니다: {secret_key[:20]}...")
        elif len(secret_key) < 32:
            errors.append(f"SECRET_KEY가 너무 짧습니다 (최소 32자 필요, 현재: {len(secret_key)}자)")

        # ENCRYPTION_SALT 검증 (이미 _derive_encryption_key에서 확인하지만 중복 체크)
        encryption_salt = os.getenv("ENCRYPTION_SALT", "")
        if not encryption_salt:
            errors.append("ENCRYPTION_SALT 환경변수가 설정되지 않았습니다.")
        elif encryption_salt in self.INSECURE_DEFAULTS["ENCRYPTION_SALT"]:
            errors.append(f"ENCRYPTION_SALT가 안전하지 않은 기본값으로 설정되어 있습니다.")
        elif len(encryption_salt) < 32:
            errors.append(f"ENCRYPTION_SALT가 너무 짧습니다 (최소 32자 필요, 현재: {len(encryption_salt)}자)")

        # DATABASE_URL 검증
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url:
            errors.append("DATABASE_URL 환경변수가 설정되지 않았습니다.")
        else:
            # 기본 DATABASE_URL 패턴 확인
            if "intellidoc:intellidoc123" in database_url:
                errors.append("DATABASE_URL이 기본 자격 증명을 사용하고 있습니다.")

            # 약한 비밀번호 패턴 확인
            for weak_password in self.INSECURE_DEFAULTS["DATABASE_PASSWORD"]:
                if weak_password in database_url:
                    errors.append(f"DATABASE_URL에 약한 비밀번호가 포함되어 있습니다: {weak_password}")
                    break

        # DEBUG 모드 확인
        if self.DEBUG:
            errors.append("프로덕션 환경에서 DEBUG 모드가 활성화되어 있습니다.")

        # ALLOWED_HOSTS 와일드카드 확인
        if "*" in self.ALLOWED_HOSTS:
            errors.append("ALLOWED_HOSTS에 와일드카드(*)가 설정되어 있습니다. 명시적인 호스트를 지정하세요.")

        # ALLOWED_ORIGINS에 localhost 확인
        for origin in self.ALLOWED_ORIGINS:
            if "localhost" in origin or "127.0.0.1" in origin:
                errors.append(f"ALLOWED_ORIGINS에 localhost가 포함되어 있습니다: {origin}")

        # 오류가 있으면 예외 발생
        if errors:
            error_message = (
                "\n\n" + "=" * 70 + "\n"
                "🚨 프로덕션 환경 보안 검증 실패!\n"
                "=" * 70 + "\n\n"
                "다음 보안 문제를 해결해야 합니다:\n\n"
            )
            for i, error in enumerate(errors, 1):
                error_message += f"  {i}. {error}\n"

            error_message += (
                "\n" + "=" * 70 + "\n"
                "환경변수를 올바르게 설정한 후 애플리케이션을 다시 시작하세요.\n"
                "=" * 70 + "\n"
            )

            raise ValueError(error_message)

    def _load_dynamic_settings(self) -> Dict[str, Any]:
        """동적 설정 로드"""
        settings_path = Path(__file__).parent / "settings.json"
        if settings_path.exists():
            with open(settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def save_dynamic_settings(self) -> None:
        """동적 설정 저장"""
        settings_path = Path(__file__).parent / "settings.json"
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(self.dynamic_settings, f, ensure_ascii=False, indent=2)
    
    def encrypt_api_key(self, api_key: str) -> str:
        """API 키 암호화"""
        f = Fernet(self._encryption_key)
        encrypted_key = f.encrypt(api_key.encode())
        return encrypted_key.decode()
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """API 키 복호화"""
        f = Fernet(self._encryption_key)
        decrypted_key = f.decrypt(encrypted_key.encode())
        return decrypted_key.decode()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """동적 설정 값 조회"""
        return self.dynamic_settings.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> None:
        """동적 설정 값 설정"""
        self.dynamic_settings[key] = value
        self.save_dynamic_settings()
    
    def get_ocr_engine_config(self, engine_name: str) -> Optional[Dict[str, Any]]:
        """OCR 엔진 설정 조회"""
        ocr_engines = self.dynamic_settings.get("ocr_engines", {})
        return ocr_engines.get(engine_name)
    
    def get_llm_processor_config(self, processor_name: str) -> Optional[Dict[str, Any]]:
        """LLM 프로세서 설정 조회"""
        llm_processors = self.dynamic_settings.get("llm_processors", {})
        return llm_processors.get(processor_name)

# 싱글톤 인스턴스 생성
settings = Settings()
