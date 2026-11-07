@echo off
setlocal EnableExtensions
cd /d "%~dp0" || exit /b 1

if not exist ".venv-windows\Scripts\python.exe" (
    py -3 -c "import struct,sys; print('Selected Python:', sys.version); sys.exit(0 if sys.version_info >= (3,11) and struct.calcsize('P') == 8 else 1)"
    if errorlevel 1 (
        echo ERROR: Python 3.11 or newer, 64-bit, is required.
        exit /b 1
    )
    py -3 -m venv .venv-windows
)
if errorlevel 1 exit /b 1
call ".venv-windows\Scripts\activate.bat"
python -c "import struct,sys; print('Build Python:', sys.version); sys.exit(0 if sys.version_info >= (3,11) and struct.calcsize('P') == 8 else 1)"
if errorlevel 1 (
    echo ERROR: .venv-windows must use Python 3.11 or newer, 64-bit.
    echo Recreate it with: py -3 -m venv .venv-windows
    exit /b 1
)
python -m pip install --timeout 120 --retries 3 -r requirements.txt pyinstaller
if errorlevel 1 exit /b 1

python -m PyInstaller --clean --noconfirm ID-BIO-Project.spec
if errorlevel 1 exit /b 1
if not exist "dist\CVAFPI-IDSYS.exe" (
    echo ERROR: PyInstaller did not create dist\CVAFPI-IDSYS.exe.
    exit /b 1
)

copy /y data.csv dist\data.csv >nul
if errorlevel 1 exit /b 1
copy /y backup-data.csv dist\backup-data.csv >nul
if errorlevel 1 exit /b 1
copy /y settings.json dist\settings.json >nul
if errorlevel 1 exit /b 1
copy /y README.md dist\README.md >nul
if errorlevel 1 exit /b 1
copy /y LICENSE dist\LICENSE >nul
if errorlevel 1 exit /b 1
copy /y CVAIDSYSLOGO.ico dist\CVAIDSYSLOGO.ico >nul
if errorlevel 1 exit /b 1
if not exist "dist\LICENSES" mkdir "dist\LICENSES"
xcopy /y /e /i "LICENSES" "dist\LICENSES" >nul
if errorlevel 1 exit /b 1
if not exist installer mkdir installer

set "ISCC="
for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do if not defined ISCC set "ISCC=%%I"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if defined ISCC (
    "%ISCC%" installer.iss
    if errorlevel 1 exit /b 1
    if not exist "installer\CVAFPI-IDSYS-Setup.exe" (
        echo ERROR: Inno Setup completed without producing the expected installer.
        exit /b 1
    )
    echo Installer created: installer\CVAFPI-IDSYS-Setup.exe
) else (
    echo ERROR: Inno Setup 6.3 or newer was not found.
    echo Portable executable is ready, but the installer was not created.
    echo Install Inno Setup, then run this script again.
    exit /b 2
)

echo.
echo Build complete:
echo   Portable app: dist\CVAFPI-IDSYS.exe
echo   Installer:    installer\CVAFPI-IDSYS-Setup.exe