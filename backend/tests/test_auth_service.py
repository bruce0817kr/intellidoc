import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import uuid
from datetime import datetime
import json

# 테스트 대상 모듈 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 테스트 대상 모듈 임포트
from shared.models import Document, User, ProcessingJob
from shared.exceptions import ResourceNotFoundError, AuthenticationError
from auth.service import AuthService


class TestAuthService(unittest.TestCase):
    """인증 서비스 테스트 클래스"""

    def setUp(self):
        """테스트 설정"""
        # 모의 데이터베이스 세션 생성
        self.mock_db = MagicMock()
        
        # 인증 서비스 생성
        self.auth_service = AuthService()
        
        # 테스트 사용자 정보
        self.test_username = "testuser"
        self.test_password = "password123"
        # 유효한 bcrypt 해시 생성 (password123을 해시한 결과)
        self.test_hashed_password = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewgVDlpJH8N5T1M6"
        self.test_user_id = uuid.uuid4()
        
        # 모의 사용자 생성
        self.mock_user = MagicMock(spec=User)
        self.mock_user.id = self.test_user_id
        self.mock_user.username = self.test_username
        self.mock_user.hashed_password = self.test_hashed_password
        self.mock_user.email = "test@example.com"
        self.mock_user.is_active = True
        self.mock_user.roles = ["user"]
        
        # 모의 쿼리 설정
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_user

    @patch('auth.service.verify_password')
    def test_authenticate_user_success(self, mock_verify_password):
        """사용자 인증 성공 테스트"""
        # 비밀번호 검증 모킹
        mock_verify_password.return_value = True
        
        # 테스트 실행
        user = self.auth_service.authenticate_user(
            db=self.mock_db,
            username=self.test_username,
            password=self.test_password
        )
        
        # 검증
        self.assertEqual(user.id, self.test_user_id)
        self.assertEqual(user.username, self.test_username)
        self.assertEqual(user.email, "test@example.com")
        
        # 비밀번호 검증 호출 확인
        mock_verify_password.assert_called_once_with(self.test_password, self.test_hashed_password)

    @patch('auth.service.verify_password')
    def test_authenticate_user_wrong_password(self, mock_verify_password):
        """잘못된 비밀번호 인증 테스트"""
        # 비밀번호 검증 실패 모킹
        mock_verify_password.return_value = False
        
        # 예외 발생 확인
        with self.assertRaises(AuthenticationError):
            self.auth_service.authenticate_user(
                db=self.mock_db,
                username=self.test_username,
                password="wrong_password"
            )

    def test_authenticate_user_not_found(self):
        """존재하지 않는 사용자 인증 테스트"""
        # 사용자를 찾을 수 없도록 설정
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # 예외 발생 확인
        with self.assertRaises(AuthenticationError):
            self.auth_service.authenticate_user(
                db=self.mock_db,
                username="nonexistent_user",
                password=self.test_password
            )

    def test_authenticate_user_inactive(self):
        """비활성화된 사용자 인증 테스트"""
        # 사용자 비활성화 설정
        self.mock_user.is_active = False
        
        # 예외 발생 확인
        with self.assertRaises(AuthenticationError):
            self.auth_service.authenticate_user(
                db=self.mock_db,
                username=self.test_username,
                password=self.test_password
            )

    @patch('auth.service.authenticate_user')
    @patch('auth.service.create_access_token')
    @patch('auth.service.create_refresh_token')
    def test_login_success(self, mock_create_refresh_token, mock_create_access_token, mock_authenticate_user):
        """로그인 성공 테스트"""
        # 토큰 생성 모킹
        mock_access_token = "test_access_token"
        mock_refresh_token = "test_refresh_token"
        mock_create_access_token.return_value = mock_access_token
        mock_create_refresh_token.return_value = mock_refresh_token
        
        # 사용자 인증 모킹
        mock_authenticate_user.return_value = self.mock_user
        
        # 테스트 실행
        result = self.auth_service.login(
            db=self.mock_db,
            username=self.test_username,
            password=self.test_password
        )
        
        # 검증
        self.assertEqual(result["access_token"], mock_access_token)
        self.assertEqual(result["refresh_token"], mock_refresh_token)
        self.assertEqual(result["token_type"], "bearer")
        self.assertEqual(result["user"]["id"], str(self.test_user_id))
        self.assertEqual(result["user"]["username"], self.test_username)
        self.assertEqual(result["user"]["email"], "test@example.com")
        
        # 사용자 인증 호출 확인 (positional arguments로 수정)
        mock_authenticate_user.assert_called_once_with(
            self.mock_db,
            self.test_username,
            self.test_password
        )

    @patch('auth.service.get_password_hash')
    def test_register_user_success(self, mock_get_password_hash):
        """사용자 등록 성공 테스트"""
        # 비밀번호 해시 모킹
        mock_get_password_hash.return_value = self.test_hashed_password
        
        # 사용자가 존재하지 않도록 설정
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # 테스트 실행
        user = self.auth_service.register_user(
            db=self.mock_db,
            username=self.test_username,
            password=self.test_password,
            email="test@example.com"
        )
        
        # 검증
        self.assertEqual(user.username, self.test_username)
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.hashed_password, self.test_hashed_password)
        
        # 사용자 추가 확인
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once()

    def test_register_user_already_exists(self):
        """이미 존재하는 사용자 등록 테스트"""
        # 예외 발생 확인
        with self.assertRaises(ValueError):
            self.auth_service.register_user(
                db=self.mock_db,
                username=self.test_username,
                password=self.test_password,
                email="test@example.com"
            )

    @patch('auth.service.jwt.decode')
    def test_get_current_user_success(self, mock_jwt_decode):
        """현재 사용자 조회 성공 테스트"""
        # JWT 디코딩 모킹
        mock_jwt_decode.return_value = {"sub": str(self.test_user_id)}
        
        # 테스트 실행
        user = self.auth_service.get_current_user(
            db=self.mock_db,
            token="test_token"
        )
        
        # 검증
        self.assertEqual(user.id, self.test_user_id)
        self.assertEqual(user.username, self.test_username)

    @patch('auth.service.jwt.decode')
    def test_get_current_user_not_found(self, mock_jwt_decode):
        """존재하지 않는 현재 사용자 조회 테스트"""
        # JWT 디코딩 모킹
        mock_jwt_decode.return_value = {"sub": str(uuid.uuid4())}
        
        # 사용자를 찾을 수 없도록 설정
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # 예외 발생 확인
        with self.assertRaises(AuthenticationError):
            self.auth_service.get_current_user(
                db=self.mock_db,
                token="test_token"
            )

    @patch('auth.service.jwt.decode')
    def test_get_current_user_inactive(self, mock_jwt_decode):
        """비활성화된 현재 사용자 조회 테스트"""
        # JWT 디코딩 모킹
        mock_jwt_decode.return_value = {"sub": str(self.test_user_id)}
        
        # 사용자 비활성화 설정
        self.mock_user.is_active = False
        
        # 예외 발생 확인
        with self.assertRaises(AuthenticationError):
            self.auth_service.get_current_user(
                db=self.mock_db,
                token="test_token"
            )


if __name__ == '__main__':
    unittest.main()
