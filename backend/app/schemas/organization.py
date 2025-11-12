"""
Organization and Team Schemas
조직 및 팀 관련 Pydantic 스키마
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class OrganizationBase(BaseModel):
    """조직 기본 스키마"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    """조직 생성 스키마"""
    settings: Dict[str, Any] = Field(default={}, description="조직 설정")


class OrganizationUpdate(BaseModel):
    """조직 업데이트 스키마"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class OrganizationResponse(OrganizationBase):
    """조직 응답 스키마"""
    id: int
    settings: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TeamBase(BaseModel):
    """팀 기본 스키마"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    organization_id: int


class TeamCreate(TeamBase):
    """팀 생성 스키마"""
    resource_quota: Dict[str, Any] = Field(default={}, description="팀 리소스 할당량")


class TeamUpdate(BaseModel):
    """팀 업데이트 스키마"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    resource_quota: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class TeamResponse(TeamBase):
    """팀 응답 스키마"""
    id: int
    resource_quota: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True