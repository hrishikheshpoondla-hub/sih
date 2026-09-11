# SIH26146 - PowerShell Launcher
$Host.UI.RawUI.WindowTitle = "SIH26146 - Bitcoin Traffic Intelligence Platform (NTRO)"
Clear-Host

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Traffic" -ForegroundColor Cyan
Write-Host "   National Technical Research Organisation (NTRO) - SIH 2026" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

Write-Host "[1/3] Verifying Python environment..." -ForegroundColor Yellow
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "[ERROR] Python was not found on PATH. Please install Python 3.11+." -ForegroundColor Red
    pause
    exit 1
}

Write-Host "[2/3] Checking Analytical Database..." -ForegroundColor Yellow
$checkCmd = @"
from backend.app.database.connection import DatabaseManager
conn = DatabaseManager.get_instance().get_connection()
cnt = conn.execute('SELECT count(*) FROM transactions;').fetchone()[0]
conn.close()
exit(0 if cnt > 0 else 1)
"@
$res = python -c $checkCmd 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Initializing DuckDB database and seeding benchmark records..." -ForegroundColor Yellow
    python scripts/init_database.py --reset
    python scripts/generate_demo_data.py
    python scripts/run_ingest.py data/sample/synthetic_demo.csv
}

Write-Host "[3/3] Launching platform at http://localhost:8000/ ..." -ForegroundColor Green
Write-Host ""
Write-Host "Opening dashboard in your default browser..." -ForegroundColor Cyan
Start-Process "http://localhost:8000/"

Set-Location (Join-Path $PSScriptRoot "backend")
python run.py
