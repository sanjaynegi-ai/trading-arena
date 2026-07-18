param(
    [switch]$NoDashboard,
    [switch]$NoApi,
    [switch]$NoScheduler,
    [int]$DashboardPort = 7860,
    [int]$ApiPort = 8000
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RunDir = Join-Path $ProjectRoot ".run"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

function Test-Running {
    param([string]$Name)

    $pidPath = Join-Path $RunDir "$Name.pid"
    if (-not (Test-Path $pidPath)) {
        return $false
    }

    $processId = Get-Content $pidPath -ErrorAction SilentlyContinue
    if (-not $processId) {
        return $false
    }

    return [bool](Get-Process -Id ([int]$processId) -ErrorAction SilentlyContinue)
}

function Start-TradingArenaProcess {
    param(
        [string]$Name,
        [string[]]$Arguments
    )

    if (Test-Running $Name) {
        Write-Host "$Name is already running."
        return
    }

    $stdoutPath = Join-Path $RunDir "$Name.out.log"
    $stderrPath = Join-Path $RunDir "$Name.err.log"
    $pidPath = Join-Path $RunDir "$Name.pid"

    $process = Start-Process `
        -FilePath "uv" `
        -ArgumentList $Arguments `
        -WorkingDirectory $ProjectRoot `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath `
        -WindowStyle Hidden `
        -PassThru

    Set-Content -Path $pidPath -Value $process.Id
    Write-Host "Started $Name with PID $($process.Id)."
}

if (-not $NoDashboard) {
    Start-TradingArenaProcess `
        -Name "dashboard" `
        -Arguments @("run", "python", "app.py", "--server-port", "$DashboardPort")
}

if (-not $NoApi) {
    Start-TradingArenaProcess `
        -Name "api" `
        -Arguments @("run", "uvicorn", "backend.api:app", "--port", "$ApiPort")
}

if (-not $NoScheduler) {
    Start-TradingArenaProcess `
        -Name "scheduler" `
        -Arguments @("run", "-m", "backend.trading_arena")
}

Write-Host ""
Write-Host "Dashboard: http://127.0.0.1:$DashboardPort"
Write-Host "API:       http://127.0.0.1:$ApiPort"
Write-Host "Logs:      $RunDir"
Write-Host ""
Write-Host "Stop with: powershell -ExecutionPolicy Bypass -File script\stop.ps1"
