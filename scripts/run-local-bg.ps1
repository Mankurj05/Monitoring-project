$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
$npmCommand = Get-Command npm -ErrorAction SilentlyContinue
$logDir = Join-Path $root "logs"

if (-not (Test-Path $py)) {
  Write-Error "Virtual environment not found at .venv. Run scripts/setup-local.ps1 first."
  exit 1
}

if (-not $npmCommand) {
  Write-Error "npm not found. Install Node.js and retry."
  exit 1
}

New-Item -ItemType Directory -Path $logDir -Force | Out-Null

# Clean up stale processes that still hold required ports from previous runs.
$ports = @(8000, 8001, 8002, 8003, 5173)
foreach ($port in $ports) {
  $connections = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
  foreach ($conn in $connections) {
    try {
      Stop-Process -Id $conn.OwningProcess -Force -ErrorAction Stop
      Write-Host "Stopped stale process $($conn.OwningProcess) on port $port"
    } catch {
      Write-Host "Could not stop process $($conn.OwningProcess) on port $port"
    }
  }
}

Start-Sleep -Seconds 1

function Start-ServiceProcess {
  param(
    [string]$Name,
    [string]$WorkingDir,
    [string]$FilePath,
    [string]$Arguments,
    [hashtable]$EnvVars
  )

  $stdout = Join-Path $logDir "$Name.out.log"
  $stderr = Join-Path $logDir "$Name.err.log"

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $FilePath
  $psi.Arguments = $Arguments
  $psi.WorkingDirectory = $WorkingDir
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true

  foreach ($key in $EnvVars.Keys) {
    $psi.Environment[$key] = $EnvVars[$key]
  }

  $proc = New-Object System.Diagnostics.Process
  $proc.StartInfo = $psi

  $null = $proc.Start()
  $proc.BeginOutputReadLine()
  $proc.BeginErrorReadLine()

  $proc.add_OutputDataReceived({
    $e = $args[1]
    if ($e.Data) { Add-Content -Path $stdout -Value $e.Data }
  })

  $proc.add_ErrorDataReceived({
    $e = $args[1]
    if ($e.Data) { Add-Content -Path $stderr -Value $e.Data }
  })

  Start-Sleep -Milliseconds 300

  if ($proc.HasExited) {
    Write-Host "$Name failed to stay up. See logs: $stdout and $stderr"
  } else {
    Write-Host "$Name started (PID: $($proc.Id))"
  }

  return $proc
}

Write-Host "Starting local stack in background..."

$apiKey = "dev-monitor-key"
$tenantId = "default"
$projectId = "demo"
$serviceEnv = "local"
$serviceVersion = "0.2.0"
$serviceTeam = "platform"

$backend = Start-ServiceProcess -Name "monitoring-backend" -WorkingDir (Join-Path $root "monitoring_backend") -FilePath $py -Arguments "-m uvicorn app.main:app --host 0.0.0.0 --port 8000" -EnvVars @{ DATABASE_URL = "sqlite:///./monitoring.db"; MONITORING_API_KEY = $apiKey; RESET_DB_ON_STARTUP = "1" }
$payments = Start-ServiceProcess -Name "payments" -WorkingDir (Join-Path $root "services\payments") -FilePath $py -Arguments "-m uvicorn app.main:app --host 0.0.0.0 --port 8003" -EnvVars @{ SERVICE_NAME = "payments"; API_PORT = "8003"; MONITORING_INGEST_URL = "http://127.0.0.1:8000/ingest/span"; MONITORING_API_KEY = $apiKey; TENANT_ID = $tenantId; PROJECT_ID = $projectId; SERVICE_ENVIRONMENT = $serviceEnv; SERVICE_VERSION = $serviceVersion; SERVICE_TEAM = $serviceTeam }
$orders = Start-ServiceProcess -Name "orders" -WorkingDir (Join-Path $root "services\orders") -FilePath $py -Arguments "-m uvicorn app.main:app --host 0.0.0.0 --port 8002" -EnvVars @{ SERVICE_NAME = "orders"; API_PORT = "8002"; DOWNSTREAM_PAYMENTS_URL = "http://127.0.0.1:8003/payments"; MONITORING_INGEST_URL = "http://127.0.0.1:8000/ingest/span"; MONITORING_API_KEY = $apiKey; TENANT_ID = $tenantId; PROJECT_ID = $projectId; SERVICE_ENVIRONMENT = $serviceEnv; SERVICE_VERSION = $serviceVersion; SERVICE_TEAM = $serviceTeam }
$gateway = Start-ServiceProcess -Name "gateway" -WorkingDir (Join-Path $root "services\gateway") -FilePath $py -Arguments "-m uvicorn app.main:app --host 0.0.0.0 --port 8001" -EnvVars @{ SERVICE_NAME = "gateway"; API_PORT = "8001"; DOWNSTREAM_ORDERS_URL = "http://127.0.0.1:8002/orders"; DOWNSTREAM_PAYMENTS_URL = "http://127.0.0.1:8003/payments"; MONITORING_INGEST_URL = "http://127.0.0.1:8000/ingest/span"; MONITORING_API_KEY = $apiKey; TENANT_ID = $tenantId; PROJECT_ID = $projectId; SERVICE_ENVIRONMENT = $serviceEnv; SERVICE_VERSION = $serviceVersion; SERVICE_TEAM = $serviceTeam }
$frontend = Start-ServiceProcess -Name "frontend" -WorkingDir (Join-Path $root "frontend") -FilePath "cmd.exe" -Arguments "/c npm run dev" -EnvVars @{ VITE_API_BASE_URL = "http://127.0.0.1:8000"; VITE_MONITORING_API_KEY = $apiKey; VITE_TENANT_ID = $tenantId; VITE_PROJECT_ID = $projectId }

$pids = @($backend.Id, $payments.Id, $orders.Id, $gateway.Id, $frontend.Id)
Set-Content -Path (Join-Path $logDir "pids.txt") -Value ($pids -join "`n")

Write-Host "Started services."
Write-Host "Dashboard: http://localhost:5173"
Write-Host "Backend:   http://localhost:8000/health"
Write-Host "Gateway:   http://localhost:8001/checkout?item_id=book-1&quantity=2"
Write-Host "Logs folder: $logDir"
Write-Host "Use scripts/stop-local-bg.ps1 to stop all background services."
