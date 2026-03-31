from datetime import UTC, datetime, timedelta
import math
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from google.protobuf.message import DecodeError
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import ServiceEdge, ServiceRegistry, SpanRecord
from app.schemas.telemetry import (
    ErrorPoint,
    LatencyPoint,
    ServiceEdgeOut,
    ServiceMetadataOut,
    SpanIngest,
    TraceSummary,
)

API_KEY = os.getenv("MONITORING_API_KEY", "dev-monitor-key")


def _require_api_key(request: Request) -> None:
    if request.headers.get("x-api-key") != API_KEY:
        raise HTTPException(status_code=401, detail="invalid API key")


def _request_scope(request: Request) -> tuple[str, str]:
    tenant_id = request.headers.get("x-tenant-id", "default")
    project_id = request.headers.get("x-project-id", "default")
    return tenant_id, project_id


def _any_value_to_python(value) -> str | float | int | bool | None:
    kind = value.WhichOneof("value")
    if kind == "string_value":
        return value.string_value
    if kind == "int_value":
        return value.int_value
    if kind == "double_value":
        return value.double_value
    if kind == "bool_value":
        return value.bool_value
    return None


def _upsert_service_registry(
    db: Session,
    tenant_id: str,
    project_id: str,
    service_name: str,
    environment: str | None,
    service_version: str | None,
    team: str | None,
) -> None:
    svc = (
        db.query(ServiceRegistry)
        .filter(
            ServiceRegistry.tenant_id == tenant_id,
            ServiceRegistry.project_id == project_id,
            ServiceRegistry.service_name == service_name,
        )
        .first()
    )

    if not svc:
        svc = ServiceRegistry(
            tenant_id=tenant_id,
            project_id=project_id,
            service_name=service_name,
        )
        db.add(svc)

    svc.environment = environment
    svc.service_version = service_version
    svc.team = team


def _upsert_edge(
    db: Session,
    tenant_id: str,
    project_id: str,
    caller: str,
    callee: str,
    duration_ms: float,
    is_error: bool,
) -> None:
    edge = (
        db.query(ServiceEdge)
        .filter(
            ServiceEdge.tenant_id == tenant_id,
            ServiceEdge.project_id == project_id,
            ServiceEdge.caller == caller,
            ServiceEdge.callee == callee,
        )
        .first()
    )

    if not edge:
        edge = ServiceEdge(
            tenant_id=tenant_id,
            project_id=project_id,
            caller=caller,
            callee=callee,
            request_count=0,
            error_count=0,
            avg_latency_ms=0.0,
        )
        db.add(edge)
        db.flush()

    previous_count = edge.request_count
    edge.request_count += 1
    if is_error:
        edge.error_count += 1

    edge.avg_latency_ms = (
        (edge.avg_latency_ms * previous_count + duration_ms) / edge.request_count
        if edge.request_count
        else duration_ms
    )


ingest_router = APIRouter(prefix="/ingest", tags=["ingest"], dependencies=[Depends(_require_api_key)])
query_router = APIRouter(prefix="/api", tags=["query"], dependencies=[Depends(_require_api_key)])


@ingest_router.post("/span")
def ingest_span(request: Request, payload: SpanIngest, db: Session = Depends(get_db)) -> dict[str, str]:
    request_tenant_id, request_project_id = _request_scope(request)
    tenant_id = payload.tenant_id or request_tenant_id
    project_id = payload.project_id or request_project_id

    span = SpanRecord(
        **payload.model_dump(exclude={"tenant_id", "project_id", "environment", "service_version", "team"}),
        tenant_id=tenant_id,
        project_id=project_id,
        environment=payload.environment,
        service_version=payload.service_version,
        team=payload.team,
    )
    db.add(span)

    _upsert_service_registry(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        service_name=payload.service_name,
        environment=payload.environment,
        service_version=payload.service_version,
        team=payload.team,
    )

    if payload.upstream_service and payload.upstream_service != payload.service_name:
        _upsert_edge(
            db,
            tenant_id=tenant_id,
            project_id=project_id,
            caller=payload.upstream_service,
            callee=payload.service_name,
            duration_ms=payload.duration_ms,
            is_error=payload.is_error,
        )

    db.commit()
    return {"status": "ingested"}


@ingest_router.post("/otlp/v1/traces")
async def ingest_otlp_traces(request: Request, db: Session = Depends(get_db)) -> dict[str, int]:
    tenant_id, project_id = _request_scope(request)

    raw = await request.body()
    envelope = ExportTraceServiceRequest()
    try:
        envelope.ParseFromString(raw)
    except DecodeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid OTLP payload: {exc}") from exc

    ingested = 0
    for resource_spans in envelope.resource_spans:
        resource_attrs = {
            attr.key: _any_value_to_python(attr.value)
            for attr in resource_spans.resource.attributes
        }

        service_name = str(resource_attrs.get("service.name") or "unknown-service")
        environment = (
            str(resource_attrs.get("deployment.environment"))
            if resource_attrs.get("deployment.environment") is not None
            else None
        )
        service_version = (
            str(resource_attrs.get("service.version"))
            if resource_attrs.get("service.version") is not None
            else None
        )
        team = (
            str(resource_attrs.get("service.team") or resource_attrs.get("team"))
            if (resource_attrs.get("service.team") or resource_attrs.get("team")) is not None
            else None
        )

        _upsert_service_registry(
            db,
            tenant_id=tenant_id,
            project_id=project_id,
            service_name=service_name,
            environment=environment,
            service_version=service_version,
            team=team,
        )

        for scope_spans in resource_spans.scope_spans:
            for span in scope_spans.spans:
                span_attrs = {
                    attr.key: _any_value_to_python(attr.value)
                    for attr in span.attributes
                }

                method = str(span_attrs.get("http.method") or "N/A")
                path = str(span_attrs.get("http.route") or span_attrs.get("url.path") or span.name or "/")

                raw_status = span_attrs.get("http.status_code")
                if raw_status is not None and str(raw_status).isdigit():
                    status_code = int(raw_status)
                else:
                    status_code = 500 if span.status.code == 2 else 200

                duration_ms = max((span.end_time_unix_nano - span.start_time_unix_nano) / 1_000_000, 0.0)
                is_error = span.status.code == 2 or status_code >= 500
                upstream_service = (
                    str(span_attrs.get("peer.service") or span_attrs.get("upstream.service"))
                    if (span_attrs.get("peer.service") or span_attrs.get("upstream.service")) is not None
                    else None
                )
                started_at = (
                    datetime.fromtimestamp(span.start_time_unix_nano / 1_000_000_000, tz=UTC)
                    if span.start_time_unix_nano
                    else datetime.now(UTC)
                )

                db.add(
                    SpanRecord(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        trace_id=span.trace_id.hex(),
                        span_id=span.span_id.hex(),
                        parent_span_id=span.parent_span_id.hex() if span.parent_span_id else None,
                        service_name=service_name,
                        upstream_service=upstream_service,
                        path=path,
                        method=method,
                        status_code=status_code,
                        duration_ms=duration_ms,
                        is_error=is_error,
                        error_message=span.status.message or None,
                        started_at=started_at,
                        environment=environment,
                        service_version=service_version,
                        team=team,
                    )
                )

                if upstream_service and upstream_service != service_name:
                    _upsert_edge(
                        db,
                        tenant_id=tenant_id,
                        project_id=project_id,
                        caller=upstream_service,
                        callee=service_name,
                        duration_ms=duration_ms,
                        is_error=is_error,
                    )

                ingested += 1

    db.commit()
    return {"ingested_spans": ingested}


@query_router.get("/traces", response_model=list[TraceSummary])
def list_traces(request: Request, limit: int = Query(default=20, le=100), db: Session = Depends(get_db)):
    tenant_id, project_id = _request_scope(request)

    grouped = (
        db.query(
            SpanRecord.trace_id.label("trace_id"),
            func.count(SpanRecord.id).label("span_count"),
            func.min(SpanRecord.started_at).label("started_at"),
            func.max(SpanRecord.duration_ms).label("total_duration_ms"),
            func.max(case((SpanRecord.is_error.is_(True), 1), else_=0)).label("has_error"),
        )
        .filter(SpanRecord.tenant_id == tenant_id, SpanRecord.project_id == project_id)
        .group_by(SpanRecord.trace_id)
        .order_by(func.min(SpanRecord.started_at).desc())
        .limit(limit)
        .all()
    )

    return [
        TraceSummary(
            trace_id=g.trace_id,
            span_count=int(g.span_count),
            started_at=g.started_at,
            total_duration_ms=float(g.total_duration_ms or 0.0),
            has_error=bool(g.has_error),
        )
        for g in grouped
    ]


@query_router.get("/traces/{trace_id}")
def get_trace(request: Request, trace_id: str, db: Session = Depends(get_db)):
    tenant_id, project_id = _request_scope(request)

    rows = (
        db.query(SpanRecord)
        .filter(
            SpanRecord.tenant_id == tenant_id,
            SpanRecord.project_id == project_id,
            SpanRecord.trace_id == trace_id,
        )
        .order_by(SpanRecord.started_at.asc())
        .all()
    )

    return [
        {
            "trace_id": r.trace_id,
            "span_id": r.span_id,
            "parent_span_id": r.parent_span_id,
            "service_name": r.service_name,
            "upstream_service": r.upstream_service,
            "path": r.path,
            "method": r.method,
            "status_code": r.status_code,
            "duration_ms": r.duration_ms,
            "is_error": r.is_error,
            "error_message": r.error_message,
            "started_at": r.started_at,
            "tenant_id": r.tenant_id,
            "project_id": r.project_id,
        }
        for r in rows
    ]


@query_router.get("/service-map", response_model=list[ServiceEdgeOut])
def service_map(
    request: Request,
    minutes: int = Query(default=60, ge=1, le=24 * 60),
    db: Session = Depends(get_db),
):
    tenant_id, project_id = _request_scope(request)
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)

    edges = (
        db.query(ServiceEdge)
        .filter(
            ServiceEdge.tenant_id == tenant_id,
            ServiceEdge.project_id == project_id,
            ServiceEdge.last_seen_at >= cutoff,
        )
        .order_by(ServiceEdge.request_count.desc())
        .all()
    )
    return [
        ServiceEdgeOut(
            caller=e.caller,
            callee=e.callee,
            request_count=e.request_count,
            error_count=e.error_count,
            avg_latency_ms=e.avg_latency_ms,
        )
        for e in edges
    ]


@query_router.get("/metrics/latency", response_model=list[LatencyPoint])
def latency_metrics(
    request: Request,
    minutes: int = Query(default=60, ge=1, le=24 * 60),
    db: Session = Depends(get_db),
):
    tenant_id, project_id = _request_scope(request)
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)

    rows = (
        db.query(
            SpanRecord.service_name.label("service_name"),
            SpanRecord.duration_ms.label("duration_ms"),
        )
        .filter(
            SpanRecord.tenant_id == tenant_id,
            SpanRecord.project_id == project_id,
            SpanRecord.started_at >= cutoff,
        )
        .all()
    )

    durations_by_service: dict[str, list[float]] = {}
    for row in rows:
        service_name, duration_ms = row
        durations_by_service.setdefault(service_name, []).append(float(duration_ms))

    points: list[LatencyPoint] = []
    for service_name, durations in durations_by_service.items():
        sorted_durations = sorted(durations)
        count = len(sorted_durations)
        p95_index = max(0, math.ceil(0.95 * count) - 1)
        avg_ms = sum(sorted_durations) / count if count else 0.0
        p95_ms = sorted_durations[p95_index] if count else 0.0

        points.append(
            LatencyPoint(
                service_name=service_name,
                request_count=count,
                avg_ms=avg_ms,
                p95_ms=p95_ms,
            )
        )

    return points


@query_router.get("/metrics/errors", response_model=list[ErrorPoint])
def error_metrics(
    request: Request,
    minutes: int = Query(default=60, ge=1, le=24 * 60),
    db: Session = Depends(get_db),
):
    tenant_id, project_id = _request_scope(request)
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)

    totals = (
        db.query(
            SpanRecord.service_name.label("service_name"),
            func.count(SpanRecord.id).label("total"),
            func.sum(case((SpanRecord.is_error.is_(True), 1), else_=0)).label("errors"),
        )
        .filter(
            SpanRecord.tenant_id == tenant_id,
            SpanRecord.project_id == project_id,
            SpanRecord.started_at >= cutoff,
        )
        .group_by(SpanRecord.service_name)
        .all()
    )

    return [
        ErrorPoint(
            service_name=t.service_name,
            total=int(t.total),
            errors=int(t.errors or 0),
        )
        for t in totals
    ]


@query_router.get("/services", response_model=list[ServiceMetadataOut])
def list_services(request: Request, db: Session = Depends(get_db)):
    tenant_id, project_id = _request_scope(request)
    rows = (
        db.query(ServiceRegistry)
        .filter(
            ServiceRegistry.tenant_id == tenant_id,
            ServiceRegistry.project_id == project_id,
        )
        .order_by(ServiceRegistry.service_name.asc())
        .all()
    )

    return [
        ServiceMetadataOut(
            tenant_id=r.tenant_id,
            project_id=r.project_id,
            service_name=r.service_name,
            environment=r.environment,
            service_version=r.service_version,
            team=r.team,
            last_seen_at=r.last_seen_at,
        )
        for r in rows
    ]
