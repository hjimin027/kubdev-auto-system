"""
Resource Metrics Model
리소스 사용량 메트릭 모델
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ResourceMetric(Base):
    """리소스 메트릭 모델"""
    __tablename__ = "resource_metrics"

    id = Column(Integer, primary_key=True, index=True)

    # 환경 연결
    environment_id = Column(Integer, ForeignKey("environment_instances.id"), nullable=False)

    # CPU 메트릭
    cpu_usage_percent = Column(Float, default=0.0)      # CPU 사용률 (%)
    cpu_usage_cores = Column(Float, default=0.0)        # CPU 사용량 (cores)
    cpu_limit_cores = Column(Float, default=1.0)        # CPU 제한 (cores)

    # 메모리 메트릭
    memory_usage_bytes = Column(Integer, default=0)     # 메모리 사용량 (bytes)
    memory_usage_percent = Column(Float, default=0.0)   # 메모리 사용률 (%)
    memory_limit_bytes = Column(Integer, default=0)     # 메모리 제한 (bytes)

    # 스토리지 메트릭
    storage_usage_bytes = Column(Integer, default=0)    # 스토리지 사용량 (bytes)
    storage_usage_percent = Column(Float, default=0.0)  # 스토리지 사용률 (%)
    storage_limit_bytes = Column(Integer, default=0)    # 스토리지 제한 (bytes)

    # 네트워크 메트릭
    network_rx_bytes = Column(Integer, default=0)       # 수신 바이트
    network_tx_bytes = Column(Integer, default=0)       # 송신 바이트
    network_rx_packets = Column(Integer, default=0)     # 수신 패킷
    network_tx_packets = Column(Integer, default=0)     # 송신 패킷

    # 추가 메트릭 (JSON으로 확장 가능)
    additional_metrics = Column(JSON, default={})

    # 타임스탬프
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    collected_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계
    environment = relationship("EnvironmentInstance", back_populates="resource_metrics")

    def __repr__(self):
        return f"<ResourceMetric(env_id={self.environment_id}, cpu={self.cpu_usage_percent}%, mem={self.memory_usage_percent}%)>"

    @property
    def cpu_usage_millicores(self) -> int:
        """CPU 사용량을 millicores 단위로 반환"""
        return int(self.cpu_usage_cores * 1000)

    @property
    def memory_usage_mb(self) -> float:
        """메모리 사용량을 MB 단위로 반환"""
        return self.memory_usage_bytes / (1024 * 1024)

    @property
    def storage_usage_gb(self) -> float:
        """스토리지 사용량을 GB 단위로 반환"""
        return self.storage_usage_bytes / (1024 * 1024 * 1024)