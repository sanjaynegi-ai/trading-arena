param(
    [switch]$DashboardOnly,
    [switch]$ApiOnly,
    [switch]$SchedulerOnly
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RunDir = Join-Path $ProjectRoot ".run"

function Get-DescendantProcessIds {
    param([int]$ParentProcessId)

    $children = Get-CimInstance Win32_Process `
        -Filter "ParentProcessId = $ParentProcessId" `
        -ErrorAction SilentlyContinue

    foreach ($child in $children) {
        Get-DescendantProcessIds -ParentProcessId ([int]$child.ProcessId)
        [int]$child.ProcessId
    }
}

function Stop-ProcessTree {
    param([int]$RootProcessId)

    $processIds = @(
        Get-DescendantProcessIds -ParentProcessId $RootProcessId
        $RootProcessId
    )

    foreach ($processId in $processIds) {
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        }
    }
}

function Get-FallbackProcessIds {
    param([string]$Name)

    $pattern = switch ($Name) {
        "dashboard" { "app.py" }
        "api" { "backend.api:app" }
        "scheduler" { "backend.trading_arena" }
        default { "" }
    }

    if (-not $pattern) {
        return @()
    }

    $processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine.Contains($pattern) -and
            $_.CommandLine.Contains($ProjectRoot)
        }

    return @($processes | ForEach-Object { [int]$_.ProcessId })
}

if (-not (Test-Path $RunDir)) {
    New-Item -ItemType Directory -Force -Path $RunDir | Out-Null
}

$names = @("dashboard", "api", "scheduler")
if ($DashboardOnly) {
    $names = @("dashboard")
}
elseif ($ApiOnly) {
    $names = @("api")
}
elseif ($SchedulerOnly) {
    $names = @("scheduler")
}

foreach ($name in $names) {
    $pidPath = Join-Path $RunDir "$name.pid"
    $stopped = $false

    if (-not (Test-Path $pidPath)) {
        foreach ($fallbackId in (Get-FallbackProcessIds -Name $name)) {
            Stop-ProcessTree -RootProcessId $fallbackId
            Write-Host "Stopped $name fallback process $fallbackId."
            $stopped = $true
        }

        if (-not $stopped) {
            Write-Host "$name is not running."
        }
        continue
    }

    $processId = Get-Content $pidPath -ErrorAction SilentlyContinue
    if (-not $processId) {
        Remove-Item $pidPath -Force
        Write-Host "$name had an empty PID file. Removed it."
        continue
    }

    $process = Get-Process -Id ([int]$processId) -ErrorAction SilentlyContinue
    if ($process) {
        Stop-ProcessTree -RootProcessId $process.Id
        Write-Host "Stopped $name with PID $processId."
        $stopped = $true
    }
    else {
        Write-Host "$name process $processId was not running."
    }

    foreach ($fallbackId in (Get-FallbackProcessIds -Name $name)) {
        Stop-ProcessTree -RootProcessId $fallbackId
        Write-Host "Stopped $name fallback process $fallbackId."
        $stopped = $true
    }

    Remove-Item $pidPath -Force
}
