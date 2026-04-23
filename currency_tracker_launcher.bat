@echo off
REM ─────────────────────────────────────────────────────────────
REM  currency_tracker_launcher.bat
REM  Called by Windows Task Scheduler to run the currency tracker.
REM
REM  HOW TO SCHEDULE:
REM   1. Open Task Scheduler → Create Basic Task
REM   2. Trigger  : Daily, 08:00 AM
REM   3. Action   : Start a program
REM      Program  : C:\Users\Suraj\Downloads\AssignmentAis\currency_tracker_launcher.bat
REM ─────────────────────────────────────────────────────────────

"C:\Users\Suraj\anaconda3\python.exe" "C:\Users\Suraj\Downloads\AssignmentAis\currency_tracker.py"
