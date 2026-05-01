foreach ($port in @(8000)) {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($conn in $conns) {
        $procId = $conn.OwningProcess
        if ($procId -gt 0) {
            Write-Host "Killing PID $procId on port $port"
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}
Write-Host "Done"
