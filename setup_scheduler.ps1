# ============================================================
#  setup_scheduler.ps1
#  Run this ONCE as Administrator to register the daily task.
#
#  What it does:
#    - Finds your Python automatically
#    - Creates a Windows Task Scheduler job
#    - Runs currency_tracker.py every morning at 08:00 AM
#    - Logs output to scheduler_run.log in the same folder
#
#  How to run:
#    Right-click this file → "Run with PowerShell as Administrator"
# ============================================================

# ── CONFIG — change these if needed ──────────────────────────
$TaskName    = "CurrencyTrackerDaily"
$RunTime     = "08:00"                         # 24-hr format
$ScriptName  = "currency_tracker.py"
# ─────────────────────────────────────────────────────────────

# Find the folder this .ps1 lives in
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ScriptPath  = Join-Path $ScriptDir $ScriptName
$LogPath     = Join-Path $ScriptDir "scheduler_run.log"

# Auto-detect Python executable
$PythonPath = $null
$candidates = @(
    (Get-Command python  -ErrorAction SilentlyContinue)?.Source,
    (Get-Command python3 -ErrorAction SilentlyContinue)?.Source,
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
    "C:\Python312\python.exe",
    "C:\Python311\python.exe"
)
foreach ($c in $candidates) {
    if ($c -and (Test-Path $c)) { $PythonPath = $c; break }
}

if (-not $PythonPath) {
    Write-Host ""
    Write-Host "  ERROR: Python not found on this machine." -ForegroundColor Red
    Write-Host "  Install Python from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "  Then re-run this script." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Verify the tracker script exists
if (-not (Test-Path $ScriptPath)) {
    Write-Host ""
    Write-Host "  ERROR: $ScriptName not found in:" -ForegroundColor Red
    Write-Host "  $ScriptDir" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Make sure currency_tracker.py is in the same folder as this script." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host "   Currency Tracker — Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Python found  : $PythonPath" -ForegroundColor Green
Write-Host "  Script path   : $ScriptPath" -ForegroundColor Green
Write-Host "  Run time      : $RunTime daily" -ForegroundColor Green
Write-Host "  Log output    : $LogPath" -ForegroundColor Green
Write-Host ""

# ── Remove existing task with same name (clean re-register) ──
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "  Removing existing task '$TaskName'..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# ── Build the action ─────────────────────────────────────────
# We run: python "C:\path\to\currency_tracker.py" >> scheduler_run.log 2>&1
# Wrap in cmd /c so we can redirect output to log file
$CmdArgs = "/c `"$PythonPath`" `"$ScriptPath`" >> `"$LogPath`" 2>&1"

$Action  = New-ScheduledTaskAction `
    -Execute  "cmd.exe" `
    -Argument $CmdArgs `
    -WorkingDirectory $ScriptDir

# ── Build the trigger — daily at configured time ─────────────
$Trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At $RunTime

# ── Settings ─────────────────────────────────────────────────
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit    (New-TimeSpan -Minutes 10) `
    -StartWhenAvailable                                `
    -RunOnlyIfNetworkAvailable                         `
    -MultipleInstances     IgnoreNew

# Run as current user (no password popup, full network access)
$Principal = New-ScheduledTaskPrincipal `
    -UserId    "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel  Highest

# ── Register the task ────────────────────────────────────────
Register-ScheduledTask `
    -TaskName   $TaskName `
    -Action     $Action `
    -Trigger    $Trigger `
    -Settings   $Settings `
    -Principal  $Principal `
    -Description "Fetches daily USD exchange rates from frankfurter.app and writes CSV + log report." `
    -Force | Out-Null

# ── Verify it was created ────────────────────────────────────
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) {
    Write-Host "  Task registered successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Task name : $TaskName" -ForegroundColor White
    Write-Host "  Status    : $($task.State)" -ForegroundColor White
    Write-Host "  Next run  : $(($task | Get-ScheduledTaskInfo).NextRunTime)" -ForegroundColor White
    Write-Host ""

    # Ask user if they want a test run right now
    $test = Read-Host "  Run the tracker right now to test it? (y/n)"
    if ($test -eq "y" -or $test -eq "Y") {
        Write-Host ""
        Write-Host "  Running now..." -ForegroundColor Cyan
        Start-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 5
        $info = Get-ScheduledTaskInfo -TaskName $TaskName
        Write-Host "  Last run result : $($info.LastTaskResult)" -ForegroundColor White
        if ($info.LastTaskResult -eq 0) {
            Write-Host "  SUCCESS — check exchange_rate_report.csv and scheduler_run.log" -ForegroundColor Green
        } else {
            Write-Host "  Check scheduler_run.log for error details." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  ERROR: Task registration failed. Try running as Administrator." -ForegroundColor Red
}

Write-Host ""
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host "   Done! The tracker will run every day at $RunTime" -ForegroundColor Cyan
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to close"
