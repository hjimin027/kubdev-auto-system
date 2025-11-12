"""
Environment Schemas
환경 관련 Pydantic 스키마
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.environment import EnvironmentStatus


class EnvironmentBase(BaseModel):
    """환경 기본 스키마"""
    name: str = Field(..., min_length=1, max_length=255)
    template_id: int


class EnvironmentCreate(EnvironmentBase):
    """환경 생성 스키마"""
    git_repository: Optional[str] = None
    git_branch: Optional[str] = "main"
    environment_config: Dict[str, Any] = {}
    expires_at: Optional[datetime] = None


class EnvironmentUpdate(BaseModel):
    """환경 업데이트 스키마"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[EnvironmentStatus] = None
    expires_at: Optional[datetime] = None
    auto_stop_enabled: Optional[bool] = None


class EnvironmentResponse(EnvironmentBase):
    """환경 응답 스키마"""
    id: int
    user_id: int
    status: EnvironmentStatus
    status_message: Optional[str]
    access_url: Optional[str]

    # K8s 정보
    k8s_namespace: str
    k8s_deployment_name: str
    k8s_service_name: Optional[str]

    # Git 정보
    git_repository: Optional[str]
    git_branch: Optional[str]
    git_commit_hash: Optional[str]

    # 리소스 사용량
    current_resource_usage: Dict[str, Any]

    # 시간 정보
    created_at: datetime
    updated_at: Optional[datetime]
    started_at: Optional[datetime]
    stopped_at: Optional[datetime]
    expires_at: Optional[datetime]
    last_accessed_at: Optional[datetime]

    class Config:
        from_attributes = True


class EnvironmentActionRequest(BaseModel):
    """환경 액션 요청 스키마"""
    action: str = Field(..., description="start, stop, restart, delete")


class EnvironmentListResponse(BaseModel):
    """환경 목록 응답 스키마"""
    environments: List[EnvironmentResponse]
    total: int
    page: int
    size: int