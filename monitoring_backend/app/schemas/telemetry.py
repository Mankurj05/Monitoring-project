from datetime import datetime

from pydantic import BaseModel, Field


class SpanIngest(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    service_name: str
    upstream_service: str | None = None
    path: str
    method: str
    status_code: int
    duration_ms: float = Field(..., ge=0)
    is_error: bool = False
    error_message: str | None = None
    started_at: datetime
    tenant_id: str | None = None
    project_id: str | None = None
    environment: str | None = None
    service_version: str | None = None
    team: str | None = None


class TraceSummary(BaseModel):
    trace_id: str
    span_count: int
    started_at: datetime
    has_error: bool
    total_duration_ms: float


class ServiceEdgeOut(BaseModel):
    caller: str
    callee: str
    request_count: int
    error_count: int
    avg_latency_ms: float


class LatencyPoint(BaseModel):
    service_name: str
    request_count: int
    avg_ms: float
    p95_ms: float


class ErrorPoint(BaseModel):
    service_name: str
    errors: int
    total: int


class ServiceMetadataOut(BaseModel):
    tenant_id: str
    project_id: str
    service_name: str
    environment: str | None = None
    service_version: str | None = None
    team: str | None = None
    last_seen_at: datetime
