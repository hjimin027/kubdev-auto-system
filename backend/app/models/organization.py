"""
Organization and Team Models
조직 및 팀 관리 모델
"""

from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Organization(Base):
    """조직 모델"""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(1000), nullable=True)

    # 조직 설정
    settings = Column(JSON, default={})  # 조직별 설정 (리소스 할당량 등)
    is_active = Column(Boolean, default=True)

    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 관계
    users = relationship("User", back_populates="organization")
    teams = relationship("Team", back_populates="organization")
    project_templates = relationship("ProjectTemplate", back_populates="organization")

    def __repr__(self):
        return f"<Organization(name='{self.name}')>"


class Team(Base):
    """팀 모델"""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)

    # 조직 연결
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    # 팀 설정
    resource_quota = Column(JSON, default={})  # 팀별 리소스 할당량
    is_active = Column(Boolean, default=True)

    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 관계
    organization = relationship("Organization", back_populates="teams")
    users = relationship("User", back_populates="team")

    def __repr__(self):
        return f"<Team(name='{self.name}', organization='{self.organization.name}')>"