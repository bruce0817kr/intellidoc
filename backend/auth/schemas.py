"""
인증 API 스키마 정의

이 모듈은 인증 관련 API의 요청/응답 스키마를 정의합니다.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator
from shared.validators import validate_password_strength


# ============================================================================
# 요청 스키마 (Request Schemas)
# ============================================================================

class LoginRequest(BaseModel):
    """로그인 요청 스키마"""
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="사용자 이름",
        example="admin"
    )
    password: str = Field(
        ...,
        min_length=8,
        description="비밀번호",
        example="SecurePassword123!"
    )

    class Config:
        schema_extra = {
            "example": {
                "username": "admin",
                "password": "SecurePassword123!"
            }
        }


class ChangePasswordRequest(BaseModel):
    """비밀번호 변경 요청 스키마"""
    current_password: str = Field(
        ...,
        min_length=8,
        description="현재 비밀번호"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        description="새 비밀번호 (최소 8자, 대소문자, 숫자, 특수문자 포함)"
    )

    @validator('new_password')
    def validate_new_password(cls, v):
        """새 비밀번호 강도 검증"""
        try:
            validate_password_strength(v)
        except ValueError as e:
            raise ValueError(str(e))
        return v

    class Config:
        schema_extra = {
            "example": {
                "current_password": "OldPassword123!",
                "new_password": "NewSecurePassword456!"
            }
        }


# ============================================================================
# 응답 스키마 (Response Schemas)
# ============================================================================

class UserInfoResponse(BaseModel):
    """사용자 정보 응답 스키마"""
    id: str = Field(..., description="사용자 ID (UUID)")
    username: str = Field(..., description="사용자 이름")
    email: Optional[EmailStr] = Field(None, description="이메일 주소")
    full_name: Optional[str] = Field(None, description="전체 이름")
    department: Optional[str] = Field(None, description="부서")
    roles: List[str] = Field(default_factory=list, description="사용자 역할 목록")
    permissions: List[str] = Field(default_factory=list, description="사용자 권한 목록")
    created_at: Optional[str] = Field(None, description="계정 생성 일시 (ISO 8601)")

    class Config:
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "admin",
                "email": "admin@example.com",
                "full_name": "관리자",
                "department": "IT",
                "roles": ["admin", "user"],
                "permissions": ["document:read", "document:write", "document:delete"],
                "created_at": "2025-01-01T00:00:00Z"
            }
        }


class LoginResponse(BaseModel):
    """로그인 응답 스키마"""
    user: UserInfoResponse = Field(..., description="사용자 정보")
    token_type: str = Field(..., description="토큰 타입", example="bearer")
    message: str = Field(..., description="응답 메시지", example="로그인 성공")

    class Config:
        schema_extra = {
            "example": {
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "username": "admin",
                    "email": "admin@example.com",
                    "full_name": "관리자",
                    "department": "IT",
                    "roles": ["admin"],
                    "permissions": ["document:read", "document:write"],
                    "created_at": "2025-01-01T00:00:00Z"
                },
                "token_type": "bearer",
                "message": "로그인 성공"
            }
        }


class TokenRefreshResponse(BaseModel):
    """토큰 갱신 응답 스키마"""
    token_type: str = Field(..., description="토큰 타입", example="bearer")
    message: str = Field(..., description="응답 메시지", example="토큰 갱신 성공")

    class Config:
        schema_extra = {
            "example": {
                "token_type": "bearer",
                "message": "토큰 갱신 성공"
            }
        }


# ============================================================================
# 에러 응답 스키마 (Error Response Schemas)
# ============================================================================

class ErrorResponse(BaseModel):
    """에러 응답 스키마"""
    error: str = Field(..., description="에러 타입")
    detail: str = Field(..., description="에러 상세 메시지")
    code: Optional[str] = Field(None, description="에러 코드")

    class Config:
        schema_extra = {
            "example": {
                "error": "인증 오류",
                "detail": "사용자 이름 또는 비밀번호가 올바르지 않습니다.",
                "code": "INVALID_CREDENTIALS"
            }
        }
