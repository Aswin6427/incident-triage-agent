# ============================================================
#  Incident Triage Agent - Startup Script
#  Starts: 4 mock services + FastAPI backend + React frontend
# ============================================================

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$BackendDir  = Join-Path $ProjectRoot "backend"

# ── Colour helpers ───────────────────────────────────────────
function Write-Header { param($msg) Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Ok     { param($msg) Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Write-Warn   { param($msg) Write-Host "  [!!]  $msg" -ForegroundColor Yellow }
function Write-Fail   { param($msg) Write-Host "  [ERR] $msg" -ForegroundColor Red }
function Write-Info   { param($msg) Write-Host "  [>>]  $msg" -ForegroundColor White }

# ── 1. Prerequisites ─────────────────────────────────────────
Write-Header "Checking Prerequisites"

# Python
try {
    $pyVersion = python --version 2>&1
    if ($pyVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 8)) {
            Write-Fail "Python 3.8+ required. Found: $pyVersion"
            exit 1
        }
        Write-Ok "Python $($Matches[0]) found"
    }
} catch {
    Write-Fail "Python not found. Install from https://python.org"
    exit 1
}

# Node.js
try {
    $nodeVersion = node --version 2>&1
    if ($nodeVersion -match "v(\d+)") {
        if ([int]$Matches[1] -lt 16) {
            Write-Fail "Node.js 16+ required. Found: $nodeVersion"
            exit 1
        }
        Write-Ok "Node.js $nodeVersion found"
    }
} catch {
    Write-Fail "Node.js not found. Install from https://nodejs.org"
    exit 1
}

# npm
try {
    $npmVersion = npm --version 2>&1
    Write-Ok "npm $npmVersion found"
} catch {
    Write-Fail "npm not found. Reinstall Node.js"
    exit 1
}

# ── 2. Virtual Environment ───────────────────────────────────
Write-Header "Virtual Environment"

$VenvDir = Join-Path $ProjectRoot "venv"
$VenvPy  = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"
$VenvAct = Join-Path $VenvDir "Scripts\Activate.ps1"

if (-not (Test-Path $VenvPy)) {
    Write-Info "Creating virtual environment at .\venv ..."
    python -m venv $VenvDir
    Write-Ok "Virtual environment created"
} else {
    Write-Ok "Virtual environment already exists"
}

Write-Info "Upgrading pip..."
& $VenvPy -m pip install --upgrade pip --quiet --no-cache-dir

# Remove orphan dist-info directories (dual-version leftovers cause [Errno 22] on Python 3.14)
$sitePackages = Join-Path $VenvDir "Lib\site-packages"
$groups = (Get-ChildItem $sitePackages -Filter "*.dist-info" -Directory) |
    Group-Object { ($_.Name -replace '-\d[\d.]*\.dist-info$', '') }
$orphans = foreach ($g in $groups) {
    if ($g.Count -gt 1) { $g.Group | Sort-Object Name | Select-Object -SkipLast 1 }
}
if ($orphans) {
    $orphans | ForEach-Object { Remove-Item $_.FullName -Recurse -Force -Confirm:$false }
    Write-Info "Removed $($orphans.Count) orphan dist-info(s)"
}

# ── 3. Install Python Dependencies ──────────────────────────
Write-Header "Python Dependencies"

$ReqFile = Join-Path $ProjectRoot "requirements.txt"
Write-Info "Installing from requirements.txt (prefer binary wheels)..."

& $VenvPip install -r $ReqFile --prefer-binary --quiet --no-cache-dir
if ($LASTEXITCODE -ne 0) {
    Write-Fail "pip install failed. Check network/proxy settings."
    exit 1
}
Write-Ok "All Python dependencies installed"

# ── 4. Environment File ──────────────────────────────────────
Write-Header "Environment Configuration"

$EnvFile    = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Copy-Item $EnvExample $EnvFile
        Write-Warn ".env created from .env.example - set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY before running the agent"
    } else {
        Write-Warn ".env not found and no .env.example to copy from"
    }
} else {
    Write-Ok ".env file exists"
    $EnvContent = Get-Content $EnvFile -Raw
    if ($EnvContent -match 'your[_-]|<.*>|PLACEHOLDER|changeme') {
        Write-Warn ".env may still have placeholder values - verify AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are set"
    } else {
        Write-Ok ".env credentials look configured"
    }
}

# ── 5. RAG Knowledge Base (Azure Postgres + pgvector) ────────
Write-Header "RAG Knowledge Base"

$EnvContentRag = if (Test-Path $EnvFile) { Get-Content $EnvFile -Raw } else { "" }
$DbConfigured = ($EnvContentRag -match 'DATABASE_URL=postgresql') -and ($EnvContentRag -notmatch 'CHANGE_ME|<password>|<user>')

if (-not $DbConfigured) {
    Write-Warn "DATABASE_URL not configured in .env - skipping RAG index build. Set it to your Azure Postgres (pgvector) URL, then run: python -m backend.rag.pipeline"
} else {
    Write-Info "Building RAG index into Azure Postgres (pgvector)..."
    $env:PYTHONPATH = $ProjectRoot
    Push-Location $BackendDir
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $ragOutput = & $VenvPy -m rag.pipeline 2>&1
    $ragExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    Pop-Location
    $ragOutput | ForEach-Object { Write-Info $_ }
    if ($ragExit -ne 0) {
        Write-Warn "RAG pipeline build failed - continuing without it (some features may be limited)"
    } else {
        Write-Ok "RAG knowledge base built in pgvector"
    }
}

# ── 6. Frontend Dependencies ─────────────────────────────────
Write-Header "Frontend Dependencies"

$FrontendDir = Join-Path $ProjectRoot "frontend"
$NodeModules = Join-Path $FrontendDir "node_modules"

if (-not (Test-Path $NodeModules)) {
    Write-Info "Running npm install in frontend/..."
    Push-Location $FrontendDir
    npm install --silent
    $npmExit = $LASTEXITCODE
    Pop-Location
    if ($npmExit -ne 0) {
        Write-Fail "npm install failed"
        exit 1
    }
    Write-Ok "Frontend dependencies installed"
} else {
    Write-Ok "node_modules already present"
}

# ── 7. Launch All Services ───────────────────────────────────
Write-Header "Starting Services"

# Helper: spawn a named PowerShell window running a uvicorn service inside the venv
function Start-BackendService {
    param(
        [string]$Title,
        [string]$WorkDir,
        [string]$UvicornArgs
    )
    $cmd = "Set-Location '$WorkDir'; `$env:PYTHONPATH = '$ProjectRoot'; . '$VenvAct'; uvicorn $UvicornArgs; Read-Host 'Press Enter to close'"
    $proc = @{
        FilePath         = "powershell"
        ArgumentList     = "-NoExit", "-Command", $cmd
        WorkingDirectory = $WorkDir
        WindowStyle      = "Normal"
    }
    Start-Process @proc
    Write-Ok "Launched: $Title"
}

# Mock services - run from backend/ so mocks.* module paths resolve
Start-BackendService "Mock Jira        (8001)" $BackendDir "mocks.mock_jira:app --port 8001 --reload"
Start-Sleep 1
Start-BackendService "Mock Splunk      (8002)" $BackendDir "mocks.mock_splunk:app --port 8002 --reload"
Start-Sleep 1
Start-BackendService "Mock ServiceNow  (8003)" $BackendDir "mocks.mock_servicenow:app --port 8003 --reload"
Start-Sleep 1
Start-BackendService "Mock Slack       (8004)" $BackendDir "mocks.mock_slack:app --port 8004 --reload"
Start-Sleep 1
Start-BackendService "Mock On-Call     (8005)" $BackendDir "mocks.mock_oncall:app --port 8005 --reload"

# Give mocks a head-start before the main backend connects to them
Start-Sleep 3

# Main FastAPI backend
Start-BackendService "Backend          (8000)" $BackendDir "main:app --host 0.0.0.0 --port 8000 --reload"

# Let backend initialise its WebSocket before the frontend loads
Start-Sleep 3

# React frontend (no venv needed)
$feCmd  = "Set-Location '$FrontendDir'; npm run dev; Read-Host 'Press Enter to close'"
$feProc = @{
    FilePath         = "powershell"
    ArgumentList     = "-NoExit", "-Command", $feCmd
    WorkingDirectory = $FrontendDir
    WindowStyle      = "Normal"
}
Start-Process @feProc
Write-Ok "Launched: Frontend         (5173)"

# ── 8. Summary ───────────────────────────────────────────────
Write-Header "All Services Running"
Write-Host ""
Write-Host "  Service          URL" -ForegroundColor Cyan
Write-Host "  ───────────────  ─────────────────────────────" -ForegroundColor DarkGray
Write-Host "  React UI         " -NoNewline; Write-Host "http://localhost:5173" -ForegroundColor Yellow
Write-Host "  FastAPI backend  " -NoNewline; Write-Host "http://localhost:8000" -ForegroundColor Yellow
Write-Host "  API docs         " -NoNewline; Write-Host "http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "  Mock Jira        " -NoNewline; Write-Host "http://localhost:8001" -ForegroundColor DarkYellow
Write-Host "  Mock Splunk      " -NoNewline; Write-Host "http://localhost:8002" -ForegroundColor DarkYellow
Write-Host "  Mock ServiceNow  " -NoNewline; Write-Host "http://localhost:8003" -ForegroundColor DarkYellow
Write-Host "  Mock Slack       " -NoNewline; Write-Host "http://localhost:8004" -ForegroundColor DarkYellow
Write-Host "  Mock On-Call     " -NoNewline; Write-Host "http://localhost:8005" -ForegroundColor DarkYellow
Write-Host ""
Write-Host "  Push a test alert (run in a new terminal):" -ForegroundColor Cyan
Write-Host "    python scripts/push_alert.py --scenario db_timeout" -ForegroundColor White
Write-Host ""
Write-Host "  Available scenarios:" -ForegroundColor Cyan
Write-Host "    db_timeout | high_error_rate | memory_leak | deploy_regression | dependency_failure"
Write-Host ""
