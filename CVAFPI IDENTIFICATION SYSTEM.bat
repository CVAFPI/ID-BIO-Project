@echo off
setlocal EnableExtensions

title CVAFPI Identification System
set "APP_DIR=%~dp0"
set "VENV_DIR=%APP_DIR%venv"
set "PORT=5000"
set "SERVER_URL=http://127.0.0.1:%PORT%/"
set "SERVER_STARTED=0"

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
        py -3 -m venv "%VENV_DIR%"
    ) else (
        where python >nul 2>&1
        if errorlevel 1 (
            echo [ERROR] Python 3 was not found. Install Python 3.11 or newer and try again.
            pause
            exit /b 1
        )
        python -m venv "%VENV_DIR%"
    )
)

set "PYTHON=%VENV_DIR%\Scripts\python.exe"
echo [2/4] Installing or updating Python dependencies...
"%PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto :dependency_error
"%PYTHON%" -m pip install -r "%APP_DIR%requirements.txt"
if errorlevel 1 goto :dependency_error

if not exist "%APP_DIR%data.csv" (
    echo [ERROR] data.csv is missing. The CSV database file is required.
    pause
    exit /b 1
)
if not exist "%APP_DIR%backup-data.csv" copy /y "%APP_DIR%data.csv" "%APP_DIR%backup-data.csv" >nul

echo [3/4] Starting Waitress production server on port %PORT%...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do set "OLD_PID=%%P"
if defined OLD_PID (
    echo [INFO] Port %PORT% is already in use. Reusing the existing server.
) else (
    start "CVAFPI Waitress Server" /b "%VENV_DIR%\Scripts\waitress-serve.exe" --listen=0.0.0.0:%PORT% --threads=4 --url-scheme=http wsgi:app > "%APP_DIR%server.log" 2>&1
    set "SERVER_STARTED=1"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$deadline=(Get-Date).AddSeconds(30); do { try { Invoke-WebRequest -UseBasicParsing -Uri '%SERVER_URL%' -TimeoutSec 2 | Out-Null; exit 0 } catch { Start-Sleep -Milliseconds 500 } } while ((Get-Date) -lt $deadline); exit 1"
    if errorlevel 1 (
        echo [ERROR] Waitress did not respond on %SERVER_URL%
        type "%APP_DIR%server.log"
        goto :shutdown
    )
)

echo [4/4] Opening the kiosk browser...
where msedge >nul 2>&1
if not errorlevel 1 (
    start "CVAFPI Kiosk" /wait msedge --kiosk "%SERVER_URL%" --no-first-run --disable-session-crashed-bubble --user-data-dir="%TEMP%\cva_kiosk_profile"
) else (
    where chrome >nul 2>&1
    if not errorlevel 1 (
        start "CVAFPI Kiosk" /wait chrome --kiosk "%SERVER_URL%" --no-first-run --disable-session-crashed-bubble --user-data-dir="%TEMP%\cva_kiosk_profile"
    ) else (
        echo [WARNING] Microsoft Edge or Google Chrome was not found.
        start "" "%SERVER_URL%"
        pause
    )
)

:shutdown
if "%SERVER_STARTED%"=="1" (
    for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do taskkill /PID %%P /T /F >nul 2>&1
)
endlocal
exit /b 0

:dependency_error
echo [ERROR] Python dependencies could not be installed.
pause
endlocal
exit /b 1