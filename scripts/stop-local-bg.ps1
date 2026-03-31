$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $PSScriptRoot
$pidsFile = Join-Path $root "logs\pids.txt"

if (-not (Test-Path $pidsFile)) {
  Write-Host "No pids file found at logs/pids.txt. Falling back to stopping known service ports."

  $ports = @(8000, 8001, 8002, 8003, 5173)
  foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
      try {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction Stop
        Write-Host "Stopped PID $($conn.OwningProcess) on port $port"
      } catch {
        Write-Host "Could not stop PID $($conn.OwningProcess) on port $port"
      }
    }
  }

  Write-Host "Done."
  exit 0
}

$pids = Get-Content $pidsFile | Where-Object { $_ -match '^[0-9]+$' }
foreach ($pidStr in $pids) {
  $targetPid = [int]$pidStr
  try {
    Stop-Process -Id $targetPid -Force -ErrorAction Stop
    Write-Host "Stopped PID $targetPid"
  } catch {
    Write-Host "PID $targetPid already stopped or inaccessible"
  }
}

Remove-Item $pidsFile -ErrorAction SilentlyContinue
Write-Host "Done."
