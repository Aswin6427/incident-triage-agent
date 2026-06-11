# ============================================================
#  Incident Triage Agent - Stop Script
#  Stops: 4 mock services + FastAPI backend + React frontend
# ============================================================

$ErrorActionPreference = "Continue"

# -- Colour helpers ------------------------------------------
function Write-Header { param($msg) Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Ok     { param($msg) Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Write-Warn   { param($msg) Write-Host "  [!!]  $msg" -ForegroundColor Yellow }
function Write-Fail   { param($msg) Write-Host "  [ERR] $msg" -ForegroundColor Red }
function Write-Info   { param($msg) Write-Host "  [>>]  $msg" -ForegroundColor White }

# -- Service definitions -------------------------------------
$Services = @(
    [PSCustomObject]@{ Name = "Mock Jira";       Port = 8001 },
    [PSCustomObject]@{ Name = "Mock Splunk";      Port = 8002 },
    [PSCustomObject]@{ Name = "Mock ServiceNow";  Port = 8003 },
    [PSCustomObject]@{ Name = "Mock Slack";       Port = 8004 },
    [PSCustomObject]@{ Name = "FastAPI Backend";  Port = 8000 },
    [PSCustomObject]@{ Name = "Mock On-Call";     Port = 8005 },
    [PSCustomObject]@{ Name = "React Frontend";   Port = 5173 }
)

# -- Helper: kill a PID tree (process + all descendants) -----
function Kill-Tree {
    param([int]$RootPid)
    # taskkill /T kills the whole tree; /F forces; errors suppressed
    taskkill /F /T /PID $RootPid 2>&1 | Out-Null
}

# -- Helper: stop service on a given port --------------------
function Stop-ServiceOnPort {
    param(
        [string]$ServiceName,
        [int]   $Port
    )

    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue

    if (-not $conn) {
        Write-Warn "$ServiceName (port $Port) is not running - skipping"
        return
    }

    $ownerPid = $conn.OwningProcess
    Write-Info "Stopping $ServiceName (port $Port) - owner PID $ownerPid"

    # Kill the port owner and its full process tree (uvicorn reloader + worker)
    Kill-Tree -RootPid $ownerPid

    # Kill any orphaned child processes that inherited the socket handle.
    # When uvicorn --reload workers die, Python multiprocessing may leave
    # spawn-children whose ParentProcessId still points to the dead owner PID.
    $orphans = Get-WmiObject Win32_Process -ErrorAction SilentlyContinue |
               Where-Object { $_.ParentProcessId -eq $ownerPid }
    foreach ($orphan in $orphans) {
        Write-Info "  Killing orphan PID $($orphan.ProcessId) [$($orphan.Name)]"
        Kill-Tree -RootPid $orphan.ProcessId
    }

    # Wait up to 8 s for the port to be released
    $waited = 0
    while ((Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) -and $waited -lt 8) {
        Start-Sleep -Milliseconds 500
        $waited += 0.5
    }

    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
        Write-Warn "$ServiceName stopped but port $Port still in use (may need a moment to release)"
    } else {
        Write-Ok "$ServiceName stopped"
    }
}

# -- 1. Stop all services ------------------------------------
Write-Header "Stopping Services"

foreach ($svc in $Services) {
    Stop-ServiceOnPort -ServiceName $svc.Name -Port $svc.Port
}

# -- 2. Final status check -----------------------------------
Write-Header "Final Status"

$anyRunning = $false
foreach ($svc in $Services) {
    $conn = Get-NetTCPConnection -LocalPort $svc.Port -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        Write-Warn "$($svc.Name) (port $($svc.Port)) still running - PID $($conn.OwningProcess)"
        $anyRunning = $true
    } else {
        Write-Ok "$($svc.Name) (port $($svc.Port)) is stopped"
    }
}

Write-Host ""
if ($anyRunning) {
    Write-Host "  Some services could not be stopped. Try running as Administrator." -ForegroundColor Yellow
} else {
    Write-Host "  All services stopped successfully." -ForegroundColor Green
}
Write-Host ""
