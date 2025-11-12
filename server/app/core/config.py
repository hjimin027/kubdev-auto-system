"""
Core Configuration Settings
환경변수 및 앱 설정 관리
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # 앱 기본 설정
    APP_NAME: str = "KubeDev Auto System"
    DEBUG: bool = True
    VERSION: str = "1.0.0"

    # 서버 설정
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_HOSTS: List[str] = ["*"]

    # 데이터베이스 설정
    DATABASE_URL: str = Field(
        default="postgresql://postgres:password@localhost:5432/kubdev",
        env="DATABASE_URL"
    )

    # Redis 설정 (캐싱 및 세션)
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )

    # JWT 설정
    SECRET_KEY: str = Field(
        default="your-super-secret-key-change-this-in-production",
        env="SECRET_KEY"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Kubernetes 설정
    KUBECONFIG_PATH: Optional[str] = Field(default=None, env="KUBECONFIG_PATH")
    K8S_NAMESPACE: str = Field(default="kubdev", env="K8S_NAMESPACE")
    K8S_IMAGE_PULL_POLICY: str = "IfNotPresent"

    # 개발 환경 기본값
    DEFAULT_CPU_LIMIT: str = "1000m"  # 1 CPU
    DEFAULT_MEMORY_LIMIT: str = "2Gi"  # 2GB RAM
    DEFAULT_STORAGE_LIMIT: str = "10Gi"  # 10GB Storage

    # 환경 타임아웃 설정
    ENVIRONMENT_TIMEOUT_HOURS: int = 8  # 8시간 후 자동 삭제

    # 베이스 IDE 템플릿 설정
    BASE_IDE_IMAGES: dict = {
        "vscode-python": "codercom/code-server:latest",
        "vscode-node": "codercom/code-server:latest",
        "vscode-react": "codercom/code-server:latest",
        "jupyter": "jupyter/scipy-notebook:latest"
    }

    # 모니터링 설정
    PROMETHEUS_ENABLED: bool = True
    METRICS_PORT: int = 9090

    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    class Config:
        env_file = ".env"
        case_sensitive = True


# 전역 설정 인스턴스
settings = Settings()