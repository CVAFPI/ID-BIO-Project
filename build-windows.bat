@echo off
setlocal
cd /d "%~dp0"

py -3 -c "import sys; raise SystemExit(not (sys.version_info >= (3, 11) and sys.maxsize > 2**32))" >nul 2>&1
if errorlevel 1 (
    if not exist "%~dp0python-manager-26.3.msix" (
        echo ERROR: Python 3.11+ was not found and python-manager-26.3.msix is missing.
        echo Place python-manager-26.3.msix beside build-windows.bat and try again.
        pause
        exit /b 1
    )

    echo Installing the Python Install Manager...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Add-AppxPackage -Path '%~dp0python-manager-26.3.msix' -ErrorAction Stop } catch { Write-Error $_; exit 1 }"
    if errorlevel 1 (
        echo ERROR: Could not install the Python Install Manager MSIX.
        pause
        exit /b 1
    )

    set "PATH=%LOCALAPPDATA%\Microsoft\WindowsApps;%PATH%"
    echo Installing 64-bit Python 3.11...
    pymanager install 3.11
    if errorlevel 1 (
        echo ERROR: Could not install Python 3.11. Check your internet connection and try again.
        pause
        exit /b 1
    )

    py -3 -c "import sys; raise SystemExit(not (sys.version_info >= (3, 11) and sys.maxsize > 2**32))" >nul 2>&1
    if errorlevel 1 (
        echo ERROR: A 64-bit Python 3.11 or newer installation is still not available.
        pause
        exit /b 1
    )
)

if not exist .venv-windows (
    py -3 -m venv .venv-windows
    if errorlevel 1 (
        echo ERROR: Could not create the Windows build environment.
        pause
        exit /b 1
    )
) else (
    .venv-windows\Scripts\python.exe -c "import sys; raise SystemExit(not (sys.version_info >= (3, 11) and sys.maxsize > 2**32))" >nul 2>&1
    if errorlevel 1 (
        echo ERROR: The existing .venv-windows uses an unsupported Python version.
        echo Remove .venv-windows and run this build script again.
        pause
        exit /b 1
    )
)
call .venv-windows\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: Could not upgrade pip in the build environment.
    pause
    exit /b 1
)
python -m pip install -r requirements-windows.txt pyinstaller
if errorlevel 1 (
    echo ERROR: Could not install the Windows build dependencies.
    pause
    exit /b 1
)
python -m PyInstaller --clean --noconfirm ID-BIO-Project.spec
if errorlevel 1 (
    echo ERROR: PyInstaller failed to build the application.
    pause
    exit /b 1
)

echo.
echo Build complete: dist\CVAFPI-IDSYS.exe
pause