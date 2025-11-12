"""
FastAPI Dependencies
API 종속성 및 인증 미들웨어
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from .database import get_session
from .security import verify_access_token, verify_api_key, check_user_permissions
from app.models.user import User, UserRole

# Bearer Token 스키마
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session)
) -> User:
    """현재 사용자 조회 (JWT 토큰 기반)"""

    token = credentials.credentials

    # JWT 토큰 검증
    try:
        payload = verify_access_token(token)
    except HTTPException:
        # API 키로도 시도
        try:
            payload = verify_api_key(token)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 사용자 조회
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """활성 사용자만 허용"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def require_role(required_role: UserRole):
    """특정 역할 이상의 사용자만 허용하는 의존성"""
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not check_user_permissions(current_user, required_role.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user

    return role_checker


def require_organization_access(organization_id: Optional[int] = None):
    """특정 조직에 대한 접근 권한이 있는 사용자만 허용"""
    async def org_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not check_user_permissions(current_user, organization_id=organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No access to this organization"
            )
        return current_user

    return org_checker


# 역할별 의존성 생성
get_admin_user = require_role(UserRole.ORG_ADMIN)
get_team_leader = require_role(UserRole.TEAM_LEADER)
get_super_admin = require_role(UserRole.SUPER_ADMIN)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_session)
) -> Optional[User]:
    """선택적 사용자 인증 (토큰이 없어도 OK)"""

    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None