@echo off
title SIH26146 - Windows Automated Tests
color 0B
cls
echo ======================================================================
echo    SIH26146 Test Suite ^& Offline Verification
echo ======================================================================
echo.

cd /d "%~dp0"

echo [1/2] Running Pytest Suite...
python -m pytest backend/tests/ -v
if %errorlevel% neq 0 (
    color 0C
    echo [FAIL] One or more unit tests failed!
    pause
    exit /b 1
)

echo.
echo [2/2] Running 100%% Offline Compliance Verification...
python scripts/test_offline.py
if %errorlevel% neq 0 (
    color 0C
    echo [FAIL] Offline compliance test failed!
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo    ALL TESTS AND OFFLINE CHECKS PASSED ON WINDOWS!
echo ======================================================================
pause
