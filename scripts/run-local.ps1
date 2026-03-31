$ErrorActionPreference = "Stop"

Write-Host "Starting local stack without Docker..."

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  Write-Error "Virtual environment not found at .venv. Run scripts/setup-local.ps1 first."
  exit 1
}

$env:DATABASE_URL = "sqlite:///./monitoring.db"
$env:MONITORING_API_KEY = "dev-monitor-key"
$env:TENANT_ID = "default"
$env:PROJECT_ID = "demo"
$env:SERVICE_ENVIRONMENT = "local"
$env:SERVICE_VERSION = "0.2.0"
$env:SERVICE_TEAM = "platform"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\monitoring_backend'; $env:DATABASE_URL='sqlite:///./monitoring.db'; $env:MONITORING_API_KEY='dev-monitor-key'; $env:RESET_DB_ON_STARTUP='1'; ..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
Start-Sleep -Seconds 1

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\services\payments'; $env:SERVICE_NAME='payments'; $env:API_PORT='8003'; $env:MONITORING_INGEST_URL='http://127.0.0.1:8000/ingest/span'; $env:MONITORING_API_KEY='dev-monitor-key'; $env:TENANT_ID='default'; $env:PROJECT_ID='demo'; $env:SERVICE_ENVIRONMENT='local'; $env:SERVICE_VERSION='0.2.0'; $env:SERVICE_TEAM='platform'; ..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8003"
Start-Sleep -Seconds 1

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\services\orders'; $env:SERVICE_NAME='orders'; $env:API_PORT='8002'; $env:DOWNSTREAM_PAYMENTS_URL='http://127.0.0.1:8003/payments'; $env:MONITORING_INGEST_URL='http://127.0.0.1:8000/ingest/span'; $env:MONITORING_API_KEY='dev-monitor-key'; $env:TENANT_ID='default'; $env:PROJECT_ID='demo'; $env:SERVICE_ENVIRONMENT='local'; $env:SERVICE_VERSION='0.2.0'; $env:SERVICE_TEAM='platform'; ..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8002"
Start-Sleep -Seconds 1

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\services\gateway'; $env:SERVICE_NAME='gateway'; $env:API_PORT='8001'; $env:DOWNSTREAM_ORDERS_URL='http://127.0.0.1:8002/orders'; $env:DOWNSTREAM_PAYMENTS_URL='http://127.0.0.1:8003/payments'; $env:MONITORING_INGEST_URL='http://127.0.0.1:8000/ingest/span'; $env:MONITORING_API_KEY='dev-monitor-key'; $env:TENANT_ID='default'; $env:PROJECT_ID='demo'; $env:SERVICE_ENVIRONMENT='local'; $env:SERVICE_VERSION='0.2.0'; $env:SERVICE_TEAM='platform'; ..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001"
Start-Sleep -Seconds 1

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\frontend'; $env:VITE_API_BASE_URL='http://127.0.0.1:8000'; $env:VITE_MONITORING_API_KEY='dev-monitor-key'; $env:VITE_TENANT_ID='default'; $env:VITE_PROJECT_ID='demo'; npm run dev"

Write-Host "Local stack launched."
Write-Host "Dashboard: http://localhost:5173"
Write-Host "Gateway:   http://localhost:8001/checkout?item_id=book-1&quantity=2"
Write-Host "Backend:   http://localhost:8000/api/traces?limit=20"
