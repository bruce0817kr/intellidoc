"""
JWT 토큰 기반 인증 시스템

주요 기능:
1. 로그인/로그아웃 처리
2. 토큰 생성 및 검증
3. 리프레시 토큰 관리
4. 비밀번호 해싱 (bcrypt)
"""

import os
import uuid
import datetime
from typing import Dict, Any, Optional, Union, Tuple

from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from shared.config import settings
from shared.models import User, UserSession
from shared.exceptions import AuthenticationError, ValidationError
from shared.logger import log_info, log_error, log_audit

# 비밀번호 해싱 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 설정
JWT_SECRET_KEY = settings.SECRET_KEY
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    비밀번호 검증
    
    Args:
        plain_password: 평문 비밀번호
        hashed_password: 해시된 비밀번호
        
    Returns:
        bool: 비밀번호 일치 여부
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    비밀번호 해싱
    
    Args:
        password: 평문 비밀번호
        
    Returns:
        str: 해시된 비밀번호
    """
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[datetime.timedelta] = None) -> str:
    """
    액세스 토큰 생성
    
    Args:
        data: 토큰에 포함할 데이터
        expires_delta: 만료 시간 (기본값: ACCESS_TOKEN_EXPIRE_MINUTES)
        
    Returns:
        str: JWT 액세스 토큰
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # 토큰 타입 및 발급 시간 추가
    to_encode.update({
        "exp": expire,
        "iat": datetime.datetime.utcnow(),
        "token_type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[datetime.timedelta] = None) -> str:
    """
    리프레시 토큰 생성
    
    Args:
        data: 토큰에 포함할 데이터
        expires_delta: 만료 시간 (기본값: REFRESH_TOKEN_EXPIRE_DAYS)
        
    Returns:
        str: JWT 리프레시 토큰
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "token_type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    토큰 디코딩
    
    Args:
        token: JWT 토큰
        
    Returns:
        Dict[str, Any]: 디코딩된 토큰 데이터
        
    Raises:
        AuthenticationError: 토큰이 유효하지 않은 경우
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        log_error(f"토큰 디코딩 실패: {str(e)}")
        raise AuthenticationError(message="유효하지 않은 인증 토큰입니다.")


def authenticate_user(db: Session, username: str, password: str) -> User:
    """
    사용자 인증
    
    Args:
        db: 데이터베이스 세션
        username: 사용자명
        password: 비밀번호
        
    Returns:
        User: 인증된 사용자 객체
        
    Raises:
        AuthenticationError: 인증 실패 시
    """
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        log_error(f"사용자 인증 실패: 사용자 없음 - {username}")
        raise AuthenticationError(message="잘못된 사용자명 또는 비밀번호입니다.")
    
    if not user.is_active:
        log_error(f"사용자 인증 실패: 비활성화된 계정 - {username}")
        raise AuthenticationError(message="비활성화된 계정입니다.")
    
    if not verify_password(password, user.hashed_password):
        log_error(f"사용자 인증 실패: 잘못된 비밀번호 - {username}")
        raise AuthenticationError(message="잘못된 사용자명 또는 비밀번호입니다.")
    
    log_info(f"사용자 인증 성공: {username}")
    log_audit(user.id, "login", "user", str(user.id), {"username": user.username})
    
    return user


def create_user_session(db: Session, user_id: uuid.UUID, refresh_token: str, 
                       user_agent: Optional[str] = None, ip_address: Optional[str] = None) -> UserSession:
    """
    사용자 세션 생성
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        refresh_token: 리프레시 토큰
        user_agent: 사용자 에이전트 (기본값: None)
        ip_address: IP 주소 (기본값: None)
        
    Returns:
        UserSession: 생성된 세션 객체
    """
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    session = UserSession(
        user_id=user_id,
        refresh_token=refresh_token,
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=expires_at
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    log_info(f"사용자 세션 생성: {user_id}")
    
    return session


def invalidate_user_session(db: Session, refresh_token: str) -> None:
    """
    사용자 세션 무효화 (로그아웃)
    
    Args:
        db: 데이터베이스 세션
        refresh_token: 리프레시 토큰
    """
    session = db.query(UserSession).filter(UserSession.refresh_token == refresh_token).first()
    
    if session:
        db.delete(session)
        db.commit()
        
        log_info(f"사용자 세션 무효화: {session.user_id}")
        log_audit(session.user_id, "logout", "user", str(session.user_id), {})


def refresh_access_token(db: Session, refresh_token: str) -> Tuple[str, str]:
    """
    액세스 토큰 갱신
    
    Args:
        db: 데이터베이스 세션
        refresh_token: 리프레시 토큰
        
    Returns:
        Tuple[str, str]: (새 액세스 토큰, 새 리프레시 토큰)
        
    Raises:
        AuthenticationError: 리프레시 토큰이 유효하지 않은 경우
    """
    try:
        # 리프레시 토큰 디코딩
        payload = decode_token(refresh_token)
        
        # 토큰 타입 확인
        if payload.get("token_type") != "refresh":
            raise AuthenticationError(message="유효하지 않은 리프레시 토큰입니다.")
        
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError(message="유효하지 않은 리프레시 토큰입니다.")
        
        # 세션 확인
        session = db.query(UserSession).filter(UserSession.refresh_token == refresh_token).first()
        if not session:
            raise AuthenticationError(message="만료되거나 유효하지 않은 세션입니다.")

        # 세션 만료 시간 확인
        if session.expires_at < datetime.datetime.utcnow():
            log_error(f"만료된 세션 사용 시도: user_id={session.user_id}")
            # 만료된 세션 삭제
            db.delete(session)
            db.commit()
            raise AuthenticationError(message="세션이 만료되었습니다. 다시 로그인해주세요.")
        
        # 사용자 확인
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise AuthenticationError(message="사용자를 찾을 수 없거나 비활성화되었습니다.")
        
        # 새 토큰 생성
        access_token_data = {"sub": str(user.id), "username": user.username}
        refresh_token_data = {"sub": str(user.id)}
        
        new_access_token = create_access_token(access_token_data)
        new_refresh_token = create_refresh_token(refresh_token_data)
        
        # 세션 업데이트
        db.delete(session)
        create_user_session(
            db=db,
            user_id=user.id,
            refresh_token=new_refresh_token,
            user_agent=session.user_agent,
            ip_address=session.ip_address
        )
        
        log_info(f"액세스 토큰 갱신: {user.id}")
        
        return new_access_token, new_refresh_token
        
    except (JWTError, AuthenticationError) as e:
        log_error(f"토큰 갱신 실패: {str(e)}")
        raise AuthenticationError(message="리프레시 토큰이 유효하지 않거나 만료되었습니다.")


def change_password(db: Session, user_id: uuid.UUID, current_password: str, new_password: str) -> None:
    """
    비밀번호 변경
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        current_password: 현재 비밀번호
        new_password: 새 비밀번호
        
    Raises:
        AuthenticationError: 현재 비밀번호가 일치하지 않는 경우
        ValidationError: 새 비밀번호가 유효하지 않은 경우
    """
    # 사용자 조회
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AuthenticationError(message="사용자를 찾을 수 없습니다.")
    
    # 현재 비밀번호 확인
    if not verify_password(current_password, user.hashed_password):
        log_error(f"비밀번호 변경 실패: 현재 비밀번호 불일치 - {user_id}")
        raise AuthenticationError(message="현재 비밀번호가 일치하지 않습니다.")
    
    # 새 비밀번호 검증
    if len(new_password) < 8:
        raise ValidationError(message="비밀번호는 최소 8자 이상이어야 합니다.")
    
    # 비밀번호 업데이트
    user.hashed_password = get_password_hash(new_password)
    user.updated_at = datetime.datetime.utcnow()
    
    db.commit()
    
    # 모든 세션 무효화 (강제 로그아웃)
    sessions = db.query(UserSession).filter(UserSession.user_id == user_id).all()
    for session in sessions:
        db.delete(session)
    
    db.commit()
    
    log_info(f"비밀번호 변경 성공: {user_id}")
    log_audit(user_id, "change_password", "user", str(user_id), {})


def get_current_user(db: Session, token: str) -> User:
    """
    현재 사용자 조회
    
    Args:
        db: 데이터베이스 세션
        token: 액세스 토큰
        
    Returns:
        User: 현재 사용자 객체
        
    Raises:
        AuthenticationError: 토큰이 유효하지 않은 경우
    """
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise AuthenticationError(message="유효하지 않은 인증 토큰입니다.")
    except JWTError:
        raise AuthenticationError(message="유효하지 않은 인증 토큰입니다.")
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise AuthenticationError(message="사용자를 찾을 수 없습니다.")
    
    if not user.is_active:
        raise AuthenticationError(message="비활성화된 계정입니다.")
    
    return user


def login(db: Session, username: str, password: str, user_agent: Optional[str] = None, 
         ip_address: Optional[str] = None) -> Dict[str, Any]:
    """
    로그인 처리
    
    Args:
        db: 데이터베이스 세션
        username: 사용자명
        password: 비밀번호
        user_agent: 사용자 에이전트 (기본값: None)
        ip_address: IP 주소 (기본값: None)
        
    Returns:
        Dict[str, Any]: 토큰 및 사용자 정보
    """
    # 사용자 인증
    user = authenticate_user(db, username, password)
    
    # 토큰 생성
    access_token_data = {"sub": str(user.id), "username": user.username}
    refresh_token_data = {"sub": str(user.id)}
    
    access_token = create_access_token(access_token_data)
    refresh_token = create_refresh_token(refresh_token_data)
    
    # 세션 생성
    create_user_session(db, user.id, refresh_token, user_agent, ip_address)
    
    # 응답 데이터
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "department": user.department
        }
    }


def logout(db: Session, refresh_token: str) -> None:
    """
    로그아웃 처리

    Args:
        db: 데이터베이스 세션
        refresh_token: 리프레시 토큰
    """
    invalidate_user_session(db, refresh_token)


def cleanup_expired_sessions(db: Session) -> int:
    """
    만료된 세션 정리

    주기적으로 실행하여 만료된 세션을 데이터베이스에서 삭제합니다.
    Celery Beat 스케줄러에서 호출하여 사용할 수 있습니다.

    Args:
        db: 데이터베이스 세션

    Returns:
        int: 삭제된 세션 수
    """
    try:
        now = datetime.datetime.utcnow()

        # 만료된 세션 조회
        expired_sessions = db.query(UserSession).filter(
            UserSession.expires_at < now
        ).all()

        count = len(expired_sessions)

        if count > 0:
            # 만료된 세션 삭제
            for session in expired_sessions:
                db.delete(session)

            db.commit()
            log_info(f"만료된 세션 {count}개 정리 완료")

        return count

    except Exception as e:
        db.rollback()
        log_error(f"세션 정리 중 오류 발생: {str(e)}")
        raise


class AuthService:
    """인증 서비스 클래스 - 기존 함수들을 클래스 메서드로 래핑"""
    
    def authenticate_user(self, db: Session, username: str, password: str) -> User:
        """사용자 인증"""
        return authenticate_user(db, username, password)
    
    def login(self, db: Session, username: str, password: str, user_agent: Optional[str] = None, 
             ip_address: Optional[str] = None) -> Dict[str, Any]:
        """로그인 처리"""
        return login(db, username, password, user_agent, ip_address)
    
    def logout(self, db: Session, refresh_token: str) -> None:
        """로그아웃 처리"""
        return logout(db, refresh_token)
    
    def register_user(self, db: Session, username: str, password: str, email: str) -> User:
        """사용자 등록"""
        # 기존 사용자 확인
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            raise ValueError("이미 존재하는 사용자명입니다.")
        
        # 새 사용자 생성
        new_user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            is_active=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user
    
    def get_current_user(self, db: Session, token: str) -> User:
        """현재 사용자 조회"""
        return get_current_user(db, token)
    
    def change_password(self, db: Session, user_id: uuid.UUID, current_password: str, new_password: str) -> None:
        """비밀번호 변경"""
        return change_password(db, user_id, current_password, new_password)
    
    def refresh_access_token(self, db: Session, refresh_token: str) -> Tuple[str, str]:
        """액세스 토큰 갱신"""
        return refresh_access_token(db, refresh_token)
