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


@router.post("/login", response_model=Dict[str, Any])
async def login_endpoint(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    로그인 API

    HttpOnly 쿠키에 토큰을 저장하여 XSS 공격으로부터 보호합니다.

    Args:
        response: HTTP 응답 객체 (쿠키 설정용)
        request: HTTP 요청 객체
        form_data: 로그인 폼 데이터
        db: 데이터베이스 세션

    Returns:
        Dict[str, Any]: 사용자 정보 (토큰은 쿠키에 설정)
    """
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


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_endpoint(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> None:
    """
    로그아웃 API

    쿠키에서 리프레시 토큰을 읽어 세션을 무효화하고 쿠키를 삭제합니다.

    Args:
        response: HTTP 응답 객체 (쿠키 삭제용)
        refresh_token: 리프레시 토큰 (쿠키에서 읽음)
        db: 데이터베이스 세션
        current_user: 현재 사용자
    """
    if refresh_token:
        logout(db, refresh_token)

    # 쿠키 삭제
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")


@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token_endpoint(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    토큰 갱신 API

    쿠키에서 리프레시 토큰을 읽어 새로운 액세스 토큰과 리프레시 토큰을 발급합니다.

    Args:
        response: HTTP 응답 객체 (쿠키 설정용)
        refresh_token: 리프레시 토큰 (쿠키에서 읽음)
        db: 데이터베이스 세션

    Returns:
        Dict[str, Any]: 토큰 갱신 성공 메시지
    """
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


@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    현재 사용자 정보 조회 API
    
    Args:
        current_user: 현재 사용자
        db: 데이터베이스 세션
        
    Returns:
        Dict[str, Any]: 사용자 정보
    """
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
