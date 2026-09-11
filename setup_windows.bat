@echo off
title SIH26146 - Windows Setup
color 0A
cls
echo ======================================================================
echo    SIH26146 Windows Setup ^& Preparation
echo ======================================================================
echo.

cd /d "%~dp0"

echo [1/4] Installing Python Requirements...
pip install -r backend/requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install python dependencies.
    pause
    exit /b 1
)

echo.
echo [2/4] Initializing Analytical Database...
python scripts/init_database.py --reset

echo.
echo [3/4] Generating Benchmark Datasets...
python scripts/generate_demo_data.py

echo.
echo [4/4] Ingesting Initial CSV Sample...
python scripts/run_ingest.py data/sample/synthetic_demo.csv

echo.
echo ======================================================================
echo    Setup Completed Successfully!
echo    You can now run 'start_windows.bat' to launch the platform.
echo ======================================================================
pause
