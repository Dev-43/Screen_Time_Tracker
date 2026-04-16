@echo off
setlocal EnableExtensions

echo =========================================================
echo  Screen Tracker Logger - Windows Uninstaller
echo =========================================================

net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Please right-click and select "Run as administrator".
    pause
    exit /b 1
)

set "INSTALL_DIR=C:\ProgramData\ScreenTracker"
set "TASK_NAME=ScreenTrackerLogger"

:: ── Stop and kill any running logger.exe / watchdog ───────────────────────────
echo [*] Stopping running logger process...
taskkill /f /im logger.exe >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq logger_watchdog*" >nul 2>&1

:: ── Stop and delete the Scheduled Task ───────────────────────────────────────
echo [*] Stopping scheduled task "%TASK_NAME%"...
schtasks /end /tn "%TASK_NAME%" >nul 2>&1

echo [*] Deleting scheduled task "%TASK_NAME%"...
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

:: ── Also clean up legacy WinSW service (old installs) ────────────────────────
echo [*] Cleaning up legacy service (if any)...
sc stop SysLogger >nul 2>&1
sc delete SysLogger >nul 2>&1
if exist "C:\ProgramData\SysLogger\winsw.exe" (
    "C:\ProgramData\SysLogger\winsw.exe" stop      >nul 2>&1
    "C:\ProgramData\SysLogger\winsw.exe" uninstall >nul 2>&1
)
if exist "C:\ProgramData\SysLogger" (
    rmdir /s /q "C:\ProgramData\SysLogger"
)

:: ── Remove logger binary and watchdog (keep logs.db) ─────────────────────────
if exist "%INSTALL_DIR%\logger.exe"         del /f /q "%INSTALL_DIR%\logger.exe"
if exist "%INSTALL_DIR%\logger_watchdog.cmd" del /f /q "%INSTALL_DIR%\logger_watchdog.cmd"

echo.
echo =========================================================
echo  [SUCCESS] Logger has been uninstalled.
echo.
echo  NOTE: The database was kept at:
echo    %INSTALL_DIR%\logs.db
echo  Delete it manually if you want to wipe all history.
echo =========================================================
pause
