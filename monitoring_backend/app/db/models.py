from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class SpanRecord(Base):
    __tablename__ = "span_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), index=True, default="default")
    project_id: Mapped[str] = mapped_column(String(100), index=True, default="default")
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    span_id: Mapped[str] = mapped_column(String(32), index=True)
    parent_span_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    service_name: Mapped[str] = mapped_column(String(100), index=True)
    upstream_service: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    path: Mapped[str] = mapped_column(String(255), index=True)
    method: Mapped[str] = mapped_column(String(10))
    status_code: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[float] = mapped_column(Float)
    is_error: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    environment: Mapped[str | None] = mapped_column(String(100), nullable=True)
    service_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    team: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class ServiceEdge(Base):
    __tablename__ = "service_edges"
    __table_args__ = (
        UniqueConstraint("tenant_id", "project_id", "caller", "callee", name="uq_service_edge"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), index=True, default="default")
    project_id: Mapped[str] = mapped_column(String(100), index=True, default="default")
    caller: Mapped[str] = mapped_column(String(100), index=True)
    callee: Mapped[str] = mapped_column(String(100), index=True)
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ServiceRegistry(Base):
    __tablename__ = "service_registry"
    __table_args__ = (
        UniqueConstraint("tenant_id", "project_id", "service_name", name="uq_service_registry"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), index=True, default="default")
    project_id: Mapped[str] = mapped_column(String(100), index=True, default="default")
    service_name: Mapped[str] = mapped_column(String(100), index=True)
    environment: Mapped[str | None] = mapped_column(String(100), nullable=True)
    service_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    team: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
