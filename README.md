# Microservices Monitoring and Debugging Tool (MVP)

A production-style MVP inspired by Jaeger + Grafana, built for learning and interviews.

## What this project does

- Tracks requests across multiple FastAPI services
- Stores span-like telemetry, errors, and latency in PostgreSQL
- Builds a service dependency graph (caller -> callee)
- Exposes monitoring query APIs
- Visualizes traces, service map, errors, and latency in a React dashboard

## Architecture

- Demo microservices: `gateway`, `orders`, `payments`
- OpenTelemetry SDK in each service
- OpenTelemetry Collector for telemetry receiving/batching
- Monitoring backend (FastAPI) for ingest + query
- PostgreSQL for persistence
- React dashboard for visualization
- Docker Compose for one-command run

## Quick Start

### First-time local setup (fix VS Code yellow underlines)

1. Install Python 3.11+ and Node.js 20+.
2. Run:

   ```powershell
   ./scripts/setup-local.ps1
   ```

3. In VS Code, select interpreter: `.venv\\Scripts\\python.exe`.

The common yellow import warnings (FastAPI, SQLAlchemy, OpenTelemetry, requests, React modules) are usually caused by missing local dependencies or wrong interpreter selection.

1. Build and start everything:

   ```bash
   docker compose up --build
   ```

2. Generate traffic:

   ```bash
   curl "http://localhost:8001/checkout?item_id=book-1&quantity=2"
   curl "http://localhost:8001/checkout?item_id=book-2&quantity=1&fail_payments=true"
   ```

3. Open dashboard:

   - http://localhost:5173

4. Useful APIs:

   - http://localhost:8000/health
   - http://localhost:8000/api/traces?limit=20
   - http://localhost:8000/api/service-map?minutes=60
   - http://localhost:8000/api/metrics/latency?minutes=60
   - http://localhost:8000/api/metrics/errors?minutes=60

## No-Docker mode (for WSL/Docker policy restrictions)

If your machine blocks WSL or Docker (for example `Forbidden (403)`), you can still run the full MVP locally.

1. Ensure setup is complete:

   ```powershell
   ./scripts/setup-local.ps1
   ```

2. Launch all services in separate PowerShell windows:

   ```powershell
   ./scripts/run-local.ps1
   ```

If your environment does not keep spawned windows alive, use background mode:

```powershell
./scripts/run-local-bg.ps1
```

Stop background services:

```powershell
./scripts/stop-local-bg.ps1
```

Service logs are written to `logs/*.log`.

3. Generate traffic:

   ```powershell
   curl "http://localhost:8001/checkout?item_id=book-1&quantity=2"
   curl "http://localhost:8001/checkout?item_id=book-2&quantity=1&fail_payments=true"
   ```

4. Open dashboard:

   - http://localhost:5173

Notes:

- In no-Docker mode, monitoring backend defaults to SQLite (`monitoring.db`) for local development.
- In Docker mode, `DATABASE_URL` still points to PostgreSQL from `docker-compose.yml`.

## MVP Features Covered

- Distributed trace correlation via trace IDs
- Service dependency graph
- Error tracking
- Latency visualization
- Basic log-like span event storage
- OTLP protobuf trace ingestion endpoint (`/ingest/otlp/v1/traces`)
- Service metadata registry (`/api/services`)
- API key auth + tenant/project isolation

## Auth and Scope Headers

Monitoring ingestion and query APIs require:

- `x-api-key`: `dev-monitor-key`
- `x-tenant-id`: `default`
- `x-project-id`: `demo`

The frontend and local run scripts set these automatically.

## Language-Agnostic OTLP Ingestion

Services in any language can send OTLP protobuf traces to:

- `POST /ingest/otlp/v1/traces`

Include the auth/scope headers above.

## Notes

- OTel data is exported to collector for standards-based instrumentation.
- For beginner clarity, the monitoring backend ingestion endpoint receives summarized request telemetry from each service middleware.
- This keeps implementation approachable while preserving real-world observability concepts.
