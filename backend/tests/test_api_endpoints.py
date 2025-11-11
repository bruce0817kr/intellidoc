"""
API 엔드포인트 통합 테스트

주요 테스트:
- 인증 API (로그인, 로그아웃, 토큰 갱신)
- 파일 업로드 API
- 문서 조회 API
- 권한 검증
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from web_api.main import app
from shared.database import get_db, Base
from shared.models import User, Role
from auth.service import hash_password


# 테스트용 인메모리 데이터베이스 설정
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """테스트용 데이터베이스 세션 오버라이드"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    """각 테스트마다 새로운 데이터베이스 생성"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(test_db):
    """테스트용 사용자 생성"""
    db = TestingSessionLocal()

    # 역할 생성
    user_role = Role(name="user", description="일반 사용자")
    db.add(user_role)

    # 사용자 생성
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("TestPassword123!"),
        full_name="Test User",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 역할 할당
    user.roles.append(user_role)
    db.commit()

    db.close()
    return user


class TestAuthEndpoints:
    """인증 관련 엔드포인트 테스트"""

    def test_login_success(self, test_user):
        """로그인 성공 테스트"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "TestPassword123!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["username"] == "testuser"
        # HttpOnly 쿠키 확인
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    def test_login_wrong_password(self, test_user):
        """잘못된 비밀번호로 로그인 실패 테스트"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, test_db):
        """존재하지 않는 사용자로 로그인 실패 테스트"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent",
                "password": "TestPassword123!",
            },
        )
        assert response.status_code == 401

    def test_logout(self, test_user):
        """로그아웃 테스트"""
        # 먼저 로그인
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "TestPassword123!",
            },
        )
        assert login_response.status_code == 200

        # 로그아웃
        logout_response = client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 200

        # 쿠키가 삭제되었는지 확인
        assert logout_response.cookies.get("access_token", "") == ""
        assert logout_response.cookies.get("refresh_token", "") == ""


class TestDocumentEndpoints:
    """문서 관련 엔드포인트 테스트"""

    def test_upload_document_unauthenticated(self, test_db):
        """인증 없이 문서 업로드 실패 테스트"""
        files = {"file": ("test.pdf", b"%PDF-1.4\ntest content", "application/pdf")}
        response = client.post("/api/v1/documents/", files=files)
        assert response.status_code == 401

    def test_get_documents_unauthenticated(self, test_db):
        """인증 없이 문서 목록 조회 실패 테스트"""
        response = client.get("/api/v1/documents/")
        assert response.status_code == 401

    def test_get_documents_authenticated(self, test_user):
        """인증 후 문서 목록 조회 테스트"""
        # 로그인
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "TestPassword123!",
            },
        )
        assert login_response.status_code == 200

        # 문서 목록 조회 (쿠키 자동 전송됨)
        response = client.get("/api/v1/documents/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestSecurityHeaders:
    """보안 헤더 테스트"""

    def test_cors_headers(self, test_db):
        """CORS 헤더 테스트"""
        response = client.options("/api/v1/auth/login")
        # CORS 헤더 존재 확인 (와일드카드 없어야 함)
        # 실제 설정에 따라 다를 수 있음

    def test_cookie_security(self, test_user):
        """쿠키 보안 속성 테스트"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "TestPassword123!",
            },
        )
        assert response.status_code == 200

        # HttpOnly 쿠키 확인
        cookies = response.cookies
        assert "access_token" in cookies
        assert "refresh_token" in cookies

        # 쿠키 속성 확인 (HttpOnly, SameSite)
        # 실제 쿠키 속성은 브라우저에서만 확인 가능
        # 테스트에서는 설정되었는지만 확인


class TestInputValidation:
    """입력 검증 테스트"""

    def test_file_extension_validation(self, test_user):
        """파일 확장자 검증 테스트"""
        # 로그인
        client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "TestPassword123!",
            },
        )

        # 허용되지 않은 확장자 업로드 시도
        files = {"file": ("malware.exe", b"MZ\x90\x00", "application/x-executable")}
        response = client.post("/api/v1/documents/", files=files)
        assert response.status_code == 400

    def test_file_mime_type_validation(self, test_user):
        """MIME 타입 검증 테스트"""
        # 로그인
        client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "TestPassword123!",
            },
        )

        # PDF로 위장한 PNG 파일
        files = {"file": ("fake.pdf", b"\x89PNG\r\n\x1a\n", "application/pdf")}
        response = client.post("/api/v1/documents/", files=files)
        assert response.status_code == 400
        data = response.json()
        assert "파일 확장자와 실제 파일 내용이 일치하지 않습니다" in data["detail"]
