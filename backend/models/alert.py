"""Pydantic models for incoming alert payloads."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class AlertSeverity(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class AlertType(str, Enum):
    DB_CONNECTION_TIMEOUT = "DB_CONNECTION_TIMEOUT"
    HIGH_ERROR_RATE = "HIGH_ERROR_RATE"
    MEMORY_LEAK = "MEMORY_LEAK"
    DEPLOY_REGRESSION = "DEPLOY_REGRESSION"
    DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"
    LATENCY_SPIKE = "LATENCY_SPIKE"
    CPU_SPIKE = "CPU_SPIKE"
    DISK_FULL = "DISK_FULL"


class AlertMetrics(BaseModel):
    error_rate: Optional[str] = None
    latency_p99: Optional[str] = None
    throughput_drop: Optional[str] = None
    cpu_usage: Optional[str] = None
    memory_usage: Optional[str] = None
    request_count: Optional[int] = None


class AlertPayload(BaseModel):
    incident_id: str = Field(..., description="Unique incident identifier")
    service: str = Field(..., description="Affected service name")
    alert_type: str = Field(..., description="Type of alert fired")
    severity: AlertSeverity = Field(default=AlertSeverity.P2)
    region: str = Field(default="us-east-1")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error_code: Optional[str] = None
    affected_endpoints: List[str] = Field(default_factory=list)
    metrics: Optional[AlertMetrics] = None
    description: Optional[str] = None
    source: str = Field(default="mock-pusher", description="Originating alert system")

    model_config = {
        "json_schema_extra": {
            "example": {
                "incident_id": "INC-2025-001",
                "service": "payment-service",
                "alert_type": "DB_CONNECTION_TIMEOUT",
                "severity": "P1",
                "region": "us-east-1",
                "timestamp": "2025-05-27T14:32:00Z",
                "error_code": "CONN_TIMEOUT_5023",
                "affected_endpoints": ["/api/checkout", "/api/payment"],
                "metrics": {
                    "error_rate": "23%",
                    "latency_p99": "8200ms",
                    "throughput_drop": "67%",
                },
            }
        }
    }
