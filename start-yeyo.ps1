# YeyoOS - Script de arranque automático
$projectRoot = "C:\Users\yeyoa\yeyo-os"
$redisExe   = "C:\Users\yeyoa\redis\redis-server.exe"
$psqlBin    = "C:\Program Files\PostgreSQL\17\bin"

# --- Redis ---
$redisRunning = Get-Process redis-server -ErrorAction SilentlyContinue
if (-not $redisRunning) {
    Write-Host "[YeyoOS] Iniciando Redis..."
    Start-Process $redisExe -WindowStyle Hidden
    Start-Sleep 2
} else {
    Write-Host "[YeyoOS] Redis ya estaba corriendo."
}

# --- Backend (FastAPI) ---
$backendRunning = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if (-not $backendRunning) {
    Write-Host "[YeyoOS] Iniciando Backend API..."
    $backendCmd = @"
`$env:PYTHONPATH = '$projectRoot'
Set-Location '$projectRoot'
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
"@
    Start-Process powershell -ArgumentList "-WindowStyle Hidden -Command $backendCmd" -WindowStyle Hidden
    Start-Sleep 3
} else {
    Write-Host "[YeyoOS] Backend ya estaba corriendo en :8000."
}

# --- Frontend (Next.js) ---
$frontendRunning = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue
if (-not $frontendRunning) {
    Write-Host "[YeyoOS] Iniciando Frontend..."
    $frontendCmd = "Set-Location '$projectRoot\frontend'; pnpm dev"
    Start-Process powershell -ArgumentList "-WindowStyle Hidden -Command $frontendCmd" -WindowStyle Hidden
} else {
    Write-Host "[YeyoOS] Frontend ya estaba corriendo en :3000."
}

Write-Host "[YeyoOS] Todo listo. Backend: http://localhost:8000 | Frontend: http://localhost:3000"
