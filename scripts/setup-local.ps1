$ErrorActionPreference = "Stop"

Write-Host "[1/4] Checking Python..."
$pythonCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
  $pythonCmd = "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  $pythonCmd = "python"
}

if (-not $pythonCmd) {
  Write-Host "Python not found. Install Python 3.11+ first, then re-run this script."
  exit 1
}

Write-Host "[2/4] Creating virtual environment..."
if ($pythonCmd -eq "py") {
  py -m venv .venv
} else {
  python -m venv .venv
}

Write-Host "[3/4] Installing Python dependencies..."
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

Write-Host "[4/4] Installing frontend dependencies..."
Push-Location .\frontend
npm install
Pop-Location

Write-Host "Setup complete. In VS Code, run: Python: Select Interpreter -> .venv\\Scripts\\python.exe"
