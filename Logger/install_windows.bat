@echo off
setlocal EnableExtensions

:: ─────────────────────────────────────────────────────────────────────────────
:: Screen Tracker Logger — Windows Installer
::
:: WHY TASK SCHEDULER (not a Windows Service)?
::   Windows Services run in Session 0 (isolated desktop, no GUI access).
::   GetForegroundWindow() always returns NULL in Session 0, so app_name and
::   active_window would always be "Unknown".
::
::   A Task Scheduler job with /sc ONLOGON /ru <user> runs inside the user's
::   interactive session — GetForegroundWindow() works correctly there.
::
:: Must be Run as Administrator.
:: ─────────────────────────────────────────────────────────────────────────────

echo =========================================================
echo  Screen Tracker Logger - Windows Installer
echo =========================================================

net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Please right-click and select "Run as administrator".
    pause
    exit /b 1
)

:: ── Paths ─────────────────────────────────────────────────────────────────────
set "INSTALL_DIR=C:\ProgramData\ScreenTracker"
set "EXE_SRC=%~dp0logger.exe"
set "EXE_DEST=%INSTALL_DIR%\logger.exe"
set "DB_PATH=%INSTALL_DIR%\logs.db"
set "WATCHDOG=%INSTALL_DIR%\logger_watchdog.cmd"
set "TASK_NAME=ScreenTrackerLogger"

:: ── Verify logger.exe ─────────────────────────────────────────────────────────
if not exist "%EXE_SRC%" (
    echo [ERROR] logger.exe not found next to this script.
    pause
    exit /b 1
)

:: ── Create install directory ──────────────────────────────────────────────────
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: ── Copy executable ───────────────────────────────────────────────────────────
echo [*] Copying logger.exe to %INSTALL_DIR%...
copy /Y "%EXE_SRC%" "%EXE_DEST%" >nul
if errorlevel 1 (
    echo [ERROR] Failed to copy logger.exe.
    pause
    exit /b 1
)

:: ── Clean up old WinSW service from previous installs ─────────────────────────
echo [*] Cleaning up old service (if any)...
sc stop SysLogger >nul 2>&1
sc delete SysLogger >nul 2>&1
if exist "C:\ProgramData\SysLogger\winsw.exe" (
    "C:\ProgramData\SysLogger\winsw.exe" stop      >nul 2>&1
    "C:\ProgramData\SysLogger\winsw.exe" uninstall >nul 2>&1
)

:: ── Create watchdog script (auto-restarts logger if it ever exits) ────────────
echo [*] Creating watchdog script...
> "%WATCHDOG%" echo @echo off
>> "%WATCHDOG%" echo :loop
>> "%WATCHDOG%" echo "%EXE_DEST%" --db "%DB_PATH%"
>> "%WATCHDOG%" echo timeout /t 5 /nobreak ^>nul
>> "%WATCHDOG%" echo goto loop

:: ── Remove old task if it exists ─────────────────────────────────────────────
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

:: ── Register Task Scheduler job (runs at logon, as current user) ──────────────
echo [*] Registering scheduled task "%TASK_NAME%"...
schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "\"%SystemRoot%\System32\cmd.exe\" /c \"\"%WATCHDOG%\"\"" ^
  /sc ONLOGON ^
  /ru "%USERNAME%" ^
  /rl HIGHEST ^
  /f /it >nul

if errorlevel 1 (
    echo [ERROR] Failed to create scheduled task.
    pause
    exit /b 1
)

:: ── Start it immediately ──────────────────────────────────────────────────────
echo [*] Starting logger now...
schtasks /run /tn "%TASK_NAME%" >nul 2>&1

echo.
echo =========================================================
echo  [SUCCESS] Screen Tracker Logger installed!
echo.
echo  Trigger  : On logon for %USERNAME%
echo  DB path  : %DB_PATH%
echo  Watchdog : Auto-restarts logger if it crashes
echo.
echo  Frontend reads from: %DB_PATH%
echo  To uninstall : run uninstall_windows.bat as Admin
echo =========================================================
pause
