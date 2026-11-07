@echo off
setlocal EnableExtensions

title CVAFPI Identification System
set "APP_DIR=%~dp0"
set "VENV_DIR=%APP_DIR%venv"

cd /d "%APP_DIR%" || (
    echo [ERROR] Unable to access %APP_DIR%
    pause
    exit /b 1
)

echo ================================================================
echo                 CVAFPI IDENTIFICATION SYSTEM
echo                    Windows 11 CSV Edition
echo ================================================================
echo.

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [1/4] Creating Python virtual environment...
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3.11 -m venv "%VENV_DIR%"
    ) else (
        where python >nul 2>&1
        if errorlevel 1 goto :python_missing
        python -m venv "%VENV_DIR%"
    )
    if errorlevel 1 goto :venv_error
)

set "PYTHON=%VENV_DIR%\Scripts\python.exe"
"%PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 goto :python_version_error
echo [2/4] Installing or updating Python dependencies...
"%PYTHON%" -m pip install --timeout 120 --retries 3 -r "%APP_DIR%requirements.txt"
if errorlevel 1 goto :dependency_error

if not exist "%APP_DIR%data.csv" (
    echo [ERROR] data.csv is missing. The CSV database file is required.
    pause
    exit /b 1
)
if not exist "%APP_DIR%backup-data.csv" copy /y "%APP_DIR%data.csv" "%APP_DIR%backup-data.csv" >nul

echo [3/4] Starting the local kiosk server and browser...
"%PYTHON%" "%APP_DIR%windows_launcher.py"
if errorlevel 1 (
    echo [ERROR] The kiosk could not start. Check that port 5000 is available and Edge or Chrome is installed.
    pause
    exit /b 1
)
echo [4/4] Kiosk closed.
endlocal
exit /b 0

:dependency_error
echo [ERROR] Python dependencies could not be installed.
pause
endlocal
exit /b 1

:python_missing
echo [ERROR] Python was not found. Install Python 3.11 or newer and try again.
pause
endlocal
exit /b 1

:python_version_error
echo [ERROR] Python 3.11 or newer is required.
pause
endlocal
exit /b 1

:venv_error
echo [ERROR] Unable to create the Python virtual environment.
pause
endlocal
exit /b 1