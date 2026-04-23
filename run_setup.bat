@echo off
REM ============================================================
REM  run_setup.bat
REM  Double-click this to run the PowerShell setup script
REM  with the correct execution policy — no manual steps.
REM ============================================================

echo.
echo  Starting Currency Tracker Scheduler Setup...
echo.

PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_scheduler.ps1"

pause
