"""
권한 관리 모듈

주요 기능:
1. 역할 기반 접근 제어 (RBAC)
2. 권한 검증
3. 권한 데코레이터
"""

from typing import List, Dict, Any, Optional, Set, Union, Callable
from functools import wraps
import uuid

from sqlalchemy.orm import Session

from shared.models import User, Role, Permission
from shared.constants import UserRole, PERMISSIONS
from shared.exceptions import AuthorizationError
from shared.logger import log_info, log_error, log_audit


def get_user_roles(db: Session, user_id: uuid.UUID) -> List[str]:
    """
    사용자의 역할 목록 조회
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        
    Returns:
        List[str]: 역할 목록
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []
    
    return [role.name for role in user.roles]


def get_user_permissions(db: Session, user_id: uuid.UUID) -> Set[str]:
    """
    사용자의 권한 목록 조회
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        
    Returns:
        Set[str]: 권한 목록
    """
    roles = get_user_roles(db, user_id)
    permissions = set()
    
    for role in roles:
        if role in PERMISSIONS:
            permissions.update(PERMISSIONS[role])
    
    return permissions


def has_permission(db: Session, user_id: uuid.UUID, required_permission: str) -> bool:
    """
    사용자의 권한 보유 여부 확인
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        required_permission: 필요한 권한
        
    Returns:
        bool: 권한 보유 여부
    """
    permissions = get_user_permissions(db, user_id)
    return required_permission in permissions


def has_role(db: Session, user_id: uuid.UUID, required_role: str) -> bool:
    """
    사용자의 역할 보유 여부 확인
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        required_role: 필요한 역할
        
    Returns:
        bool: 역할 보유 여부
    """
    roles = get_user_roles(db, user_id)
    return required_role in roles


def require_permission(permission: str) -> Callable:
    """
    권한 요구 데코레이터
    
    Args:
        permission: 필요한 권한
        
    Returns:
        Callable: 데코레이터 함수
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 컨텍스트에서 db와 current_user 추출
            # FastAPI 의존성 주입 시스템에서 사용
            db = kwargs.get('db')
            current_user = kwargs.get('current_user')
            
            if not db or not current_user:
                raise AuthorizationError(message="인증 컨텍스트를 찾을 수 없습니다.")
            
            if not has_permission(db, current_user.id, permission):
                log_error(f"권한 부족: {current_user.id} - {permission}")
                raise AuthorizationError(message=f"이 작업을 수행할 권한이 없습니다: {permission}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(role: str) -> Callable:
    """
    역할 요구 데코레이터
    
    Args:
        role: 필요한 역할
        
    Returns:
        Callable: 데코레이터 함수
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 컨텍스트에서 db와 current_user 추출
            db = kwargs.get('db')
            current_user = kwargs.get('current_user')
            
            if not db or not current_user:
                raise AuthorizationError(message="인증 컨텍스트를 찾을 수 없습니다.")
            
            if not has_role(db, current_user.id, role):
                log_error(f"역할 부족: {current_user.id} - {role}")
                raise AuthorizationError(message=f"이 작업을 수행할 역할이 없습니다: {role}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def check_document_owner(db: Session, user_id: uuid.UUID, document_id: uuid.UUID) -> bool:
    """
    문서 소유자 확인
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        document_id: 문서 ID
        
    Returns:
        bool: 소유자 여부
    """
    from shared.models import Document
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        return False
    
    return document.uploaded_by == user_id


def require_document_owner_or_admin(func: Callable) -> Callable:
    """
    문서 소유자 또는 관리자 권한 요구 데코레이터
    
    Args:
        func: 데코레이트할 함수
        
    Returns:
        Callable: 데코레이터 함수
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 컨텍스트에서 db, current_user, document_id 추출
        db = kwargs.get('db')
        current_user = kwargs.get('current_user')
        document_id = kwargs.get('document_id')
        
        if not db or not current_user or not document_id:
            raise AuthorizationError(message="필요한 컨텍스트를 찾을 수 없습니다.")
        
        # 관리자 확인
        if has_role(db, current_user.id, UserRole.ADMIN):
            return func(*args, **kwargs)
        
        # 문서 소유자 확인
        if check_document_owner(db, current_user.id, document_id):
            return func(*args, **kwargs)
        
        log_error(f"문서 접근 권한 부족: {current_user.id} - {document_id}")
        raise AuthorizationError(message="이 문서에 대한 접근 권한이 없습니다.")
    
    return wrapper


def initialize_roles(db: Session) -> None:
    """
    기본 역할 및 권한 초기화
    
    Args:
        db: 데이터베이스 세션
    """
    # 기본 역할 생성
    roles = {
        UserRole.USER: "일반 사용자",
        UserRole.ADMIN: "관리자",
        UserRole.AUDITOR: "감사자"
    }
    
    for role_name, description in roles.items():
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            role = Role(name=role_name, description=description)
            db.add(role)
    
    db.commit()
    
    # 기본 권한 생성
    for role_name, permissions in PERMISSIONS.items():
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            continue
        
        # 기존 권한 삭제
        db.query(Permission).filter(Permission.role_name == role_name).delete()
        
        # 새 권한 추가
        for permission in permissions:
            resource, action = permission.split('.')
            perm = Permission(
                role_name=role_name,
                resource=resource,
                action=action
            )
            db.add(perm)
    
    db.commit()
    log_info("기본 역할 및 권한 초기화 완료")


def assign_role_to_user(db: Session, user_id: uuid.UUID, role_name: str) -> None:
    """
    사용자에게 역할 할당
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        role_name: 역할 이름
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"사용자를 찾을 수 없습니다: {user_id}")
    
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        raise ValueError(f"역할을 찾을 수 없습니다: {role_name}")
    
    # 이미 할당된 역할인지 확인
    if role in user.roles:
        return
    
    user.roles.append(role)
    db.commit()
    
    log_info(f"사용자에게 역할 할당: {user_id} - {role_name}")
    log_audit(user_id, "assign_role", "user", str(user_id), {"role": role_name})


def remove_role_from_user(db: Session, user_id: uuid.UUID, role_name: str) -> None:
    """
    사용자에게서 역할 제거
    
    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID
        role_name: 역할 이름
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"사용자를 찾을 수 없습니다: {user_id}")
    
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        raise ValueError(f"역할을 찾을 수 없습니다: {role_name}")
    
    # 할당된 역할인지 확인
    if role not in user.roles:
        return
    
    user.roles.remove(role)
    db.commit()
    
    log_info(f"사용자에게서 역할 제거: {user_id} - {role_name}")
    log_audit(user_id, "remove_role", "user", str(user_id), {"role": role_name})
