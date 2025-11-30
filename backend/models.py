from typing import List, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl


class GitSpec(BaseModel):
    repoUrl: HttpUrl
    ref: Optional[str] = None


class Commands(BaseModel):
    init: Optional[str] = None
    start: Optional[str] = None


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(..., description="Environment name identifier")
    template_id: Optional[str] = Field(None, description="Template identifier")
    git_repository: Optional[HttpUrl] = Field(None, description="Git repository URL")
    ref: Optional[str] = Field(None, description="Git ref")
    image: Optional[str] = Field(None, description="Container image override")
    start_command: Optional[str] = Field(None, description="Start command")
    init_command: Optional[str] = Field(None, description="Init command")
    ports: Optional[List[int]] = Field(default=None, description="Additional ports to expose")
    gitpod_compat: Optional[bool] = Field(default=False, description="If true, parse .gitpod.yml")
    mode: Optional[Literal["personal", "team"]] = Field(default="personal", description="Workspace mode")


class WorkspaceCreateResponse(BaseModel):
    id: str
    status: str
    namespace: Optional[str] = None
    ideUrl: Optional[str] = None


class WorkspaceItem(BaseModel):
    id: str
    userName: str
    status: Optional[str] = None
    namespace: Optional[str] = None
    ideUrl: Optional[str] = None
    createdAt: Optional[str] = None
    templateId: Optional[str] = None


class AdminBatchCreateRequest(BaseModel):
    name: str
    users: List[str]
    template_id: Optional[str] = None
    git_repository: Optional[HttpUrl] = None
    ref: Optional[str] = None
    image: Optional[str] = None
    start_command: Optional[str] = None
    init_command: Optional[str] = None
    ports: Optional[List[int]] = None
    gitpod_compat: Optional[bool] = False
    mode: Optional[Literal["personal", "team"]] = "personal"


class AdminBatchCreateResponse(BaseModel):
    created: List[WorkspaceCreateResponse]
    failed: List[str]
