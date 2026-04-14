@echo off
:: This script installs the logger to run automatically on Windows boot.
:: It must be Run as Administrator.

echo ----------------------------------------
echo Installing System Process Logger
echo ----------------------------------------

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Please right-click this script and select "Run as administrator".
    pause
    exit /b 1
)

:: Define installation directory
set "INSTALL_DIR=C:\ProgramData\SysLogger"
set "EXE_NAME=logger.exe"
set "WINSW_EXE=%INSTALL_DIR%\winsw.exe"
set "WINSW_XML=%INSTALL_DIR%\winsw.xml"

:: Create the installation directory if it doesn't exist
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
)

:: Copy the executable to the installation directory
echo [*] Copying files to %INSTALL_DIR%...
copy /Y "%~dp0%EXE_NAME%" "%INSTALL_DIR%\%EXE_NAME%" >nul
if %errorLevel% neq 0 (
    echo [ERROR] Failed to copy %EXE_NAME%. Make sure it is compiled and in the same folder as this script.
    pause
    exit /b 1
)

:: Download WinSW if not present
if not exist "%WINSW_EXE%" (
    echo [*] Downloading Windows Service Wrapper - WinSW...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe' -OutFile '%WINSW_EXE%'"
)

if not exist "%WINSW_EXE%" (
    echo [ERROR] Failed to download WinSW. Please check your internet connection.
    pause
    exit /b 1
)

:: Verify the integrity and genuineness of WinSW (SHA-256 Check)
echo [*] Verifying the integrity of WinSW (SHA-256 Hash Check)...
set "EXPECTED_HASH=05B82D46AD331CC16BDC00DE5C6332C1EF818DF8CEEFCD49C726553209B3A0DA"
for /f %%A in ('powershell -Command "(Get-FileHash -Algorithm SHA256 '%WINSW_EXE%').Hash"') do set "ACTUAL_HASH=%%A"

if /I "%ACTUAL_HASH%"=="%EXPECTED_HASH%" goto hash_ok
echo [ERROR] Security check failed! The downloaded WinSW wrapper is corrupted or not genuine.
echo Expected: %EXPECTED_HASH%
echo Actual:   %ACTUAL_HASH%
del /f /q "%WINSW_EXE%"
pause
exit /b 1

:hash_ok
echo [*] WinSW verified genuine from the official GitHub repository.

:: Generate winsw.xml
echo [*] Generating service configuration...
echo ^<service^> > "%WINSW_XML%"
echo   ^<id^>SysLogger^</id^> >> "%WINSW_XML%"
echo   ^<name^>System Process Logger^</name^> >> "%WINSW_XML%"
echo   ^<description^>Logs running processes in the background.^</description^> >> "%WINSW_XML%"
echo   ^<executable^>%INSTALL_DIR%\%EXE_NAME%^</executable^> >> "%WINSW_XML%"
echo   ^<log mode="roll"^>^</log^> >> "%WINSW_XML%"
set "CLEAN_PATH=%PATH:"=%"
setlocal EnableDelayedExpansion
echo   ^<env name="PATH" value="!CLEAN_PATH!"/^> >> "%WINSW_XML%"
endlocal
echo   ^<onfailure action="restart" delay="5 sec"/^> >> "%WINSW_XML%"
echo ^</service^> >> "%WINSW_XML%"

:: Stop and remove old service if it exists
echo [*] Cleaning up old service (if any)...
"%WINSW_EXE%" stop >nul 2>&1
"%WINSW_EXE%" uninstall >nul 2>&1

:: Also clean up the old Scheduled Task if it was installed from the old batch file
schtasks /delete /tn "SysLogger" /f >nul 2>&1

:: Install new service
echo [*] Installing SysLogger as a Windows Service...
"%WINSW_EXE%" install

:: Start the service
echo [*] Starting the SysLogger service...
"%WINSW_EXE%" start

echo ----------------------------------------
echo [SUCCESS] Logger is installed as a Windows Service!
echo It is now running in the background and will start automatically on boot.
echo It will also automatically restart if it crashes.
echo Logs will be saved in %INSTALL_DIR%\logs.db
echo ----------------------------------------
pause
