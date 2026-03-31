import os
import random
import threading
import time
import uuid
from datetime import UTC, datetime

import requests
from fastapi import FastAPI, Request

from app.telemetry import configure_otel

SERVICE_NAME = os.getenv("SERVICE_NAME", "orders")
PAYMENTS_URL = os.getenv("DOWNSTREAM_PAYMENTS_URL", "http://payments:8003/payments")
MONITORING_INGEST_URL = os.getenv("MONITORING_INGEST_URL", "http://monitoring-backend:8000/ingest/span")
MONITORING_API_KEY = os.getenv("MONITORING_API_KEY", "dev-monitor-key")
TENANT_ID = os.getenv("TENANT_ID", "default")
PROJECT_ID = os.getenv("PROJECT_ID", "demo")
SERVICE_ENVIRONMENT = os.getenv("SERVICE_ENVIRONMENT", "local")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.1.0")
SERVICE_TEAM = os.getenv("SERVICE_TEAM", "platform")

app = FastAPI(title="Orders Service", version="0.1.0")
configure_otel(app, SERVICE_NAME)


def _ship_span(payload: dict) -> None:
    try:
        requests.post(
            MONITORING_INGEST_URL,
            json=payload,
            headers={
                "x-api-key": MONITORING_API_KEY,
                "x-tenant-id": TENANT_ID,
                "x-project-id": PROJECT_ID,
            },
            timeout=0.4,
        )
    except requests.RequestException:
        return


@app.middleware("http")
async def telemetry_ingest_middleware(request: Request, call_next):
    start = time.perf_counter()
    started_at = datetime.now(UTC)
    error_message = None
    response = None
    trace_id = request.headers.get("x-trace-id") or uuid.uuid4().hex
    request.state.trace_id = trace_id

    try:
        response = await call_next(request)
        response.headers["x-trace-id"] = trace_id
        return response
    except Exception as exc:
        error_message = str(exc)
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        payload = {
            "trace_id": trace_id,
            "span_id": uuid.uuid4().hex[:16],
            "parent_span_id": request.headers.get("x-parent-span-id"),
            "service_name": SERVICE_NAME,
            "upstream_service": request.headers.get("x-upstream-service"),
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code if response else 500,
            "duration_ms": round(duration_ms, 2),
            "is_error": (response.status_code >= 500 if response else True),
            "error_message": error_message,
            "started_at": started_at.isoformat(),
            "tenant_id": TENANT_ID,
            "project_id": PROJECT_ID,
            "environment": SERVICE_ENVIRONMENT,
            "service_version": SERVICE_VERSION,
            "team": SERVICE_TEAM,
        }

        threading.Thread(target=_ship_span, args=(payload,), daemon=True).start()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/orders")
def create_order(request: Request, item_id: str, quantity: int = 1, fail_payments: bool = False):
    time.sleep(random.uniform(0.03, 0.12))
    trace_id = getattr(request.state, "trace_id", uuid.uuid4().hex)

    payment_resp = requests.get(
        PAYMENTS_URL,
        params={"amount": round(10.0 * quantity, 2), "fail": fail_payments},
        headers={
            "x-upstream-service": SERVICE_NAME,
            "x-trace-id": trace_id,
            "x-tenant-id": TENANT_ID,
            "x-project-id": PROJECT_ID,
        },
        timeout=3,
    )

    return {
        "order_id": f"ord-{int(time.time() * 1000)}",
        "item_id": item_id,
        "quantity": quantity,
        "payment_status": payment_resp.json().get("status", "unknown"),
    }
