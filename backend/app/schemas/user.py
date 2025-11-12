"""
User Schemas
사용자 관련 Pydantic 스키마
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    """사용자 기본 스키마"""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = UserRole.DEVELOPER


class UserCreate(UserBase):
    """사용자 생성 스키마"""
    password: str = Field(..., min_length=8, max_length=100)
    organization_id: Optional[int] = None
    team_id: Optional[int] = None


class UserUpdate(BaseModel):
    """사용자 업데이트 스키마"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    organization_id: Optional[int] = None
    team_id: Optional[int] = None


class UserResponse(UserBase):
    """사용자 응답 스키마"""
    id: int
    is_active: bool
    is_verified: bool
    organization_id: Optional[int]
    team_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """로그인 요청 스키마"""
    email: EmailStr
    password: str


class UserTokenResponse(BaseModel):
    """토큰 응답 스키마"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse