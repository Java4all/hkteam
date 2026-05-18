# Stop crisis API and Chainlit background processes.

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PidsDir = Join-Path $Root ".pids"

function Stop-ByPidFile {
    param([string]$Name)
    $PidFile = Join-Path $PidsDir "$Name.pid"
    if (-not (Test-Path $PidFile)) { return }
    $pid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($pid) {
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped $Name (PID $pid)"
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

foreach ($svc in @("api", "chainlit")) {
    Stop-ByPidFile $svc
}

# Fallback: processes on known ports
foreach ($port in @(8080, 7860)) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($conn) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped process on port $port"
    }
}

Write-Host "All services stopped."
