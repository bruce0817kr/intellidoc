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
    
    def _parse_bool(self, value: str) -> bool:
        """문자열을 불리언으로 변환"""
        return value.lower() in ("true", "1", "t", "yes", "y")
    
    def _generate_secret_key(self) -> str:
        """랜덤 시크릿 키 생성"""
        return base64.urlsafe_b64encode(os.urandom(32)).decode()
    
    def _derive_encryption_key(self, secret_key: str) -> bytes:
        """시크릿 키로부터 암호화 키 유도"""
        salt = b'intellidoc_salt'  # 실제 운영 환경에서는 안전한 방식으로 관리해야 함
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
        return key
    
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
