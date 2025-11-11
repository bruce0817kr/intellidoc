"""
인증 관련 API 엔드포인트 모듈

주요 기능:
1. 로그인/로그아웃 API
2. 토큰 갱신 API
3. 비밀번호 변경 API
4. 사용자 정보 조회 API
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.config import settings
from shared.exceptions import AuthenticationError, ValidationError
from auth.service import login, logout, refresh_access_token, change_password, get_current_user
from shared.models import User
from auth.schemas import (
    LoginResponse, TokenRefreshResponse, UserInfoResponse,
    ChangePasswordRequest, ErrorResponse
)

# OAuth2 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# 라우터 설정
router = APIRouter(prefix="/auth", tags=["인증"])


# 의존성 함수: 쿠키 또는 헤더에서 토큰 가져오기
def get_token_from_cookie_or_header(
    access_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = Depends(oauth2_scheme)
) -> str:
    """
    쿠키 또는 Authorization 헤더에서 토큰 추출

    우선순위:
    1. HttpOnly 쿠키의 access_token
    2. Authorization 헤더의 Bearer 토큰

    Args:
        access_token: 쿠키의 액세스 토큰
        authorization: Authorization 헤더의 토큰

    Returns:
        str: 추출된 액세스 토큰

    Raises:
        HTTPException: 토큰이 없는 경우
    """
    # 쿠키에서 토큰 확인 (우선순위 1)
    if access_token:
        return access_token

    # Authorization 헤더에서 토큰 확인 (우선순위 2, 하위 호환성)
    if authorization:
        return authorization

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 토큰이 없습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )


# 의존성 함수: 현재 인증된 사용자 가져오기
def get_current_active_user(
    db: Session = Depends(get_db),
    token: str = Depends(get_token_from_cookie_or_header)
) -> User:
    """
    현재 인증된 사용자 가져오기

    Args:
        db: 데이터베이스 세션
        token: 액세스 토큰 (쿠키 또는 헤더)

    Returns:
        User: 현재 사용자 객체
    """
    try:
        return get_current_user(db, token)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="사용자 로그인",
    description="""
    사용자 인증을 수행하고 JWT 토큰을 발급합니다.

    **보안 특징:**
    - 토큰은 HttpOnly 쿠키에 저장되어 XSS 공격으로부터 보호됩니다
    - SameSite=Lax 설정으로 CSRF 공격을 방지합니다
    - Access Token은 15분 유효, Refresh Token은 7일 유효합니다

    **요청 형식:**
    OAuth2 Password Flow를 사용합니다 (username, password)

    **응답:**
    - 성공 시 사용자 정보와 함께 쿠키에 토큰이 설정됩니다
    - 이후 모든 API 요청에 쿠키가 자동으로 포함됩니다
    """,
    responses={
        200: {
            "description": "로그인 성공",
            "model": LoginResponse
        },
        401: {
            "description": "인증 실패 - 잘못된 사용자명 또는 비밀번호",
            "model": ErrorResponse
        }
    }
)
async def login_endpoint(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """로그인 API - HttpOnly 쿠키에 토큰을 저장하여 XSS 공격으로부터 보호합니다."""
    try:
        # 클라이언트 정보 추출
        user_agent = request.headers.get("user-agent")
        client_host = request.client.host if request.client else None

        # 로그인 처리
        result = login(
            db=db,
            username=form_data.username,
            password=form_data.password,
            user_agent=user_agent,
            ip_address=client_host
        )

        # HttpOnly 쿠키에 토큰 설정
        # Access Token (15분 유효)
        response.set_cookie(
            key="access_token",
            value=result["access_token"],
            httponly=True,  # XSS 방지
            secure=settings.ENVIRONMENT == "production",  # HTTPS만 허용 (프로덕션)
            samesite="lax",  # CSRF 방지
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # 초 단위
            path="/",
        )

        # Refresh Token (7일 유효)
        response.set_cookie(
            key="refresh_token",
            value=result["refresh_token"],
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # 초 단위
            path="/",
        )

        # 응답에서 토큰 제거 (쿠키로만 전송)
        return {
            "user": result["user"],
            "token_type": "bearer",
            "message": "로그인 성공"
        }

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="로그아웃",
    description="""
    현재 사용자를 로그아웃합니다.

    **동작 방식:**
    1. 데이터베이스에서 현재 세션을 무효화합니다
    2. HttpOnly 쿠키에서 모든 토큰을 삭제합니다

    **응답:**
    - 성공 시 204 No Content를 반환합니다
    """,
    responses={
        204: {
            "description": "로그아웃 성공"
        },
        401: {
            "description": "인증 실패 - 유효하지 않은 토큰",
            "model": ErrorResponse
        }
    }
)
async def logout_endpoint(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> None:
    """로그아웃 API - 세션을 무효화하고 쿠키를 삭제합니다."""
    if refresh_token:
        logout(db, refresh_token)

    # 쿠키 삭제
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="토큰 갱신",
    description="""
    만료된 Access Token을 갱신합니다.

    **동작 방식:**
    1. 쿠키에서 Refresh Token을 읽어옵니다
    2. Refresh Token이 유효한 경우 새로운 Access Token과 Refresh Token을 발급합니다
    3. 새로운 토큰을 HttpOnly 쿠키에 저장합니다

    **보안:**
    - Refresh Token도 함께 갱신하여 Rotation 방식으로 보안을 강화합니다
    - 이전 Refresh Token은 자동으로 무효화됩니다
    """,
    responses={
        200: {
            "description": "토큰 갱신 성공",
            "model": TokenRefreshResponse
        },
        401: {
            "description": "인증 실패 - 유효하지 않거나 만료된 Refresh Token",
            "model": ErrorResponse
        }
    }
)
async def refresh_token_endpoint(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """토큰 갱신 API - 쿠키에서 리프레시 토큰을 읽어 새로운 토큰을 발급합니다."""
    try:
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="리프레시 토큰이 없습니다.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token, new_refresh_token = refresh_access_token(db, refresh_token)

        # 새로운 토큰을 HttpOnly 쿠키에 설정
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
        )

        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/",
        )

        return {
            "token_type": "bearer",
            "message": "토큰 갱신 성공"
        }

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password_endpoint(
    current_password: str,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> None:
    """
    비밀번호 변경 API
    
    Args:
        current_password: 현재 비밀번호
        new_password: 새 비밀번호
        db: 데이터베이스 세션
        current_user: 현재 사용자
    """
    try:
        change_password(db, current_user.id, current_password, new_password)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.get(
    "/me",
    response_model=UserInfoResponse,
    summary="현재 사용자 정보 조회",
    description="""
    현재 인증된 사용자의 정보를 조회합니다.

    **반환 정보:**
    - 사용자 기본 정보 (ID, username, email, full_name, department)
    - 사용자 역할 (roles)
    - 사용자 권한 (permissions)
    - 계정 생성 일시

    **인증 필요:**
    - 유효한 Access Token이 쿠키에 포함되어야 합니다
    """,
    responses={
        200: {
            "description": "사용자 정보 조회 성공",
            "model": UserInfoResponse
        },
        401: {
            "description": "인증 실패 - 유효하지 않은 토큰",
            "model": ErrorResponse
        }
    }
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """현재 사용자 정보 조회 API"""
    from auth.permissions import get_user_roles, get_user_permissions
    
    # 사용자 역할 및 권한 조회
    roles = get_user_roles(db, current_user.id)
    permissions = list(get_user_permissions(db, current_user.id))
    
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "department": current_user.department,
        "roles": roles,
        "permissions": permissions,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }
