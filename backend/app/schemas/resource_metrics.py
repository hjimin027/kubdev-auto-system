"""
Resource Metrics Schemas
리소스 메트릭 관련 Pydantic 스키마
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ResourceMetricResponse(BaseModel):
    """리소스 메트릭 응답 스키마"""
    id: int
    environment_id: int

    # CPU 메트릭
    cpu_usage_percent: float = Field(..., ge=0, le=100)
    cpu_usage_cores: float = Field(..., ge=0)
    cpu_limit_cores: float = Field(..., ge=0)

    # 메모리 메트릭
    memory_usage_bytes: int = Field(..., ge=0)
    memory_usage_percent: float = Field(..., ge=0, le=100)
    memory_limit_bytes: int = Field(..., ge=0)

    # 스토리지 메트릭
    storage_usage_bytes: int = Field(..., ge=0)
    storage_usage_percent: float = Field(..., ge=0, le=100)
    storage_limit_bytes: int = Field(..., ge=0)

    # 네트워크 메트릭
    network_rx_bytes: int = Field(..., ge=0)
    network_tx_bytes: int = Field(..., ge=0)
    network_rx_packets: int = Field(..., ge=0)
    network_tx_packets: int = Field(..., ge=0)

    # 추가 메트릭
    additional_metrics: Dict[str, Any] = {}

    # 타임스탬프
    timestamp: datetime
    collected_at: datetime

    class Config:
        from_attributes = True


class MetricsSummary(BaseModel):
    """메트릭 요약"""
    avg_cpu_usage: float
    avg_memory_usage: float
    avg_storage_usage: float
    max_cpu_usage: float
    max_memory_usage: float
    max_storage_usage: float
    data_points: int
    time_range_hours: int


class ResourceUsageAlert(BaseModel):
    """리소스 사용량 알림"""
    environment_id: int
    environment_name: str
    alert_type: str  # "cpu_high", "memory_high", "storage_high"
    current_usage: float
    threshold: float
    severity: str  # "warning", "critical"
    timestamp: datetime