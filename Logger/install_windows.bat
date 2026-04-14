@echo off
setlocal

cd /d "%~dp0"

echo =============================================
echo  Screen Tracker - Windows Build
echo =============================================

if not exist "sqlite3.h" (
    echo [ERROR] sqlite3.h not found in Logger folder.
    echo Download sqlite-amalgamation and place sqlite3.h + sqlite3.c here.
    pause
    exit /b 1
)

if not exist "sqlite3.c" (
    echo [ERROR] sqlite3.c not found in Logger folder.
    pause
    exit /b 1
)

where gcc >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] gcc not found in PATH.
    pause
    exit /b 1
)

where g++ >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] g++ not found in PATH.
    pause
    exit /b 1
)

if not exist "dist" mkdir dist

echo.
echo [1/3] Compiling sqlite3.c with gcc...
gcc -c sqlite3.c -O2 -I . -o dist\sqlite3.o
if %ERRORLEVEL% neq 0 (
    echo [ERROR] sqlite3.c compilation failed.
    pause
    exit /b 1
)

echo.
echo [2/3] Compiling logger with g++...
g++ main.cpp dist\sqlite3.o -o dist\screen_tracker.exe -std=c++17 -O2 -I . -lpsapi -lpdh -luser32
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Logger compilation failed.
    pause
    exit /b 1
)

del /q dist\sqlite3.o >nul 2>&1
echo [OK] dist\screen_tracker.exe created.

echo.
echo [3/3] Installing Python dependencies for Frontedn...
::if exist "..\Frontedn\requirements.txt" (
::    pip install -r ..\Frontedn\requirements.txt
::    if %ERRORLEVEL% neq 0 (
::        echo [WARNING] pip install had errors. Check your Python/pip setup.
::    )
::) else (
::    echo [WARNING] Could not find ..\Frontedn\requirements.txt
::)

echo.
echo =============================================
echo  Build complete!
echo.
echo  Run logger:
echo    dist\screen_tracker.exe
echo.
echo  Run GUI in another terminal:
echo    cd ..\Frontedn
echo    python main.py
echo =============================================
pause
