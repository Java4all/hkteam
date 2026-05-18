# Start crisis API and/or Chainlit in background.
# Usage: .\scripts\start.ps1 [api|ui|all]

param(
    [ValidateSet("api", "ui", "all")]
    [string]$Target = "all"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$PidsDir = Join-Path $Root ".pids"
$LogsDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $PidsDir, $LogsDir | Out-Null

# Load .env into process environment
$EnvFile = Join-Path $Root ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
        $k, $v = $_ -split '=', 2
        [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim(), "Process")
    }
}

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    Write-Error "Virtualenv not found. Run: make install"
}

function Start-ServiceProcess {
    param(
        [string]$Name,
        [string[]]$ArgumentList,
        [string]$LogFile
    )
    $PidFile = Join-Path $PidsDir "$Name.pid"
    if (Test-Path $PidFile) {
        $old = Get-Content $PidFile -ErrorAction SilentlyContinue
        if ($old -and (Get-Process -Id $old -ErrorAction SilentlyContinue)) {
            Write-Host "$Name already running (PID $old)"
            return
        }
    }
    $proc = Start-Process -FilePath $Py -ArgumentList $ArgumentList `
        -WorkingDirectory $Root -RedirectStandardOutput $LogFile -RedirectStandardError $LogFile `
        -PassThru -WindowStyle Hidden
    $proc.Id | Set-Content $PidFile
    Write-Host "Started $Name PID $($proc.Id) -> $LogFile"
}

if ($Target -eq "api" -or $Target -eq "all") {
    Start-ServiceProcess -Name "api" `
        -ArgumentList @("-m", "uvicorn", "crisis.api.main:app", "--host", "127.0.0.1", "--port", "8080") `
        -LogFile (Join-Path $LogsDir "api.log")
    Start-Sleep -Seconds 2
}

if ($Target -eq "ui" -or $Target -eq "all") {
    Start-ServiceProcess -Name "chainlit" `
        -ArgumentList @("-m", "chainlit", "run", "src/crisis/ui/chainlit_app.py", "--port", "7860", "--host", "127.0.0.1") `
        -LogFile (Join-Path $LogsDir "chainlit.log")
}

Write-Host ""
Write-Host "API:      http://127.0.0.1:8080/health"
Write-Host "Chainlit: http://127.0.0.1:7860"
Write-Host "Logs:     logs\"
Write-Host "Stop:     make stop  or  .\scripts\stop.ps1"
