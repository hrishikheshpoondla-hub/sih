@echo off
title SIH26146 - Bitcoin Traffic Intelligence Platform (NTRO)
color 0B
cls
echo ======================================================================
echo    SIH26146: AI-Powered Monitoring ^& Analysis of Bitcoin Traffic
echo    National Technical Research Organisation (NTRO) - SIH 2026
echo ======================================================================
echo.

cd /d "%~dp0"

echo [1/3] Verifying Python Environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Python is not found on PATH. Please install Python 3.11+ and try again.
    pause
    exit /b 1
)

echo [2/3] Checking Database Status...
python -c "from backend.app.database.connection import DatabaseManager; conn = DatabaseManager.get_instance().get_connection(); cnt = conn.execute('SELECT count(*) FROM transactions;').fetchone()[0]; print(f'Database verified: {cnt} transactions present.'); conn.close()" >nul 2>&1
if %errorlevel% neq 0 (
    echo Initializing database schema and ingesting demo data...
    python scripts/init_database.py --reset
    python scripts/generate_demo_data.py
    python scripts/run_ingest.py data/sample/synthetic_demo.csv
)

echo [3/3] Launching Core Application at http://localhost:8000/ ...
echo.
echo ======================================================================
echo    The Investigation Dashboard is opening in your default browser.
echo    Press Ctrl+C in this window to stop the server.
echo ======================================================================
echo.

start "" "http://localhost:8000/"
cd backend
python run.py
pause
