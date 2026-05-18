# Show crisis service status.

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PidsDir = Join-Path $Root ".pids"

function Show-Service {
    param([string]$Name, [int]$Port)
    $PidFile = Join-Path $PidsDir "$Name.pid"
    $running = $false
    if (Test-Path $PidFile) {
        $pid = Get-Content $PidFile
        if ($pid -and (Get-Process -Id $pid -ErrorAction SilentlyContinue)) {
            Write-Host "[OK] $Name PID $pid (port $Port)"
            $running = $true
        }
    }
    if (-not $running) {
        $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($conn) {
            Write-Host "[OK] $Name listening on port $Port (PID $($conn.OwningProcess))"
        } else {
            Write-Host "[--] $Name not running (port $Port)"
        }
    }
}

Show-Service "api" 8080
Show-Service "chainlit" 7860

try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:8080/health" -TimeoutSec 2
    Write-Host "Health: $($r.status) | profile=$($r.llm_profile) | mock=$($r.mock_llm)"
} catch {
    Write-Host "Health: API not reachable"
}
