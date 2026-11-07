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
python -m pip install --timeout 120 --retries 3 -r requirements-windows.txt
if errorlevel 1 exit /b 1

python -m PyInstaller --clean --noconfirm ID-BIO-Project.spec
if errorlevel 1 exit /b 1
if not exist "dist\CVAFPI-IDSYS.exe" (
    echo ERROR: PyInstaller did not create dist\CVAFPI-IDSYS.exe.
    exit /b 1
)

if not exist "dist\portable" mkdir "dist\portable"
if errorlevel 1 exit /b 1
if exist "dist\portable\settings.json" (
    echo ERROR: dist\portable contains a local settings.json file.
    echo Move it to a safe location before preparing a distributable build.
    exit /b 1
)
for %%F in ("dist\portable\data.csv" "dist\portable\backup-data.csv") do (
    if exist "%%~F" (
        fc /b data.example.csv "%%~F" >nul
        if errorlevel 1 (
            echo ERROR: %%~F is not the clean example CSV.
            echo Preserve local student records and clear the portable staging folder manually.
            exit /b 1
        )
    )
)
copy /y "dist\CVAFPI-IDSYS.exe" "dist\portable\CVAFPI-IDSYS.exe" >nul
if errorlevel 1 exit /b 1
copy /y data.example.csv dist\portable\data.csv >nul
if errorlevel 1 exit /b 1
copy /y data.example.csv dist\portable\backup-data.csv >nul
if errorlevel 1 exit /b 1
copy /y README.md dist\portable\README.md >nul
if errorlevel 1 exit /b 1
copy /y LICENSE dist\portable\LICENSE >nul
if errorlevel 1 exit /b 1
copy /y CVAIDSYSLOGO.ico dist\portable\CVAIDSYSLOGO.ico >nul
if errorlevel 1 exit /b 1
if not exist "dist\portable\LICENSES" mkdir "dist\portable\LICENSES"
xcopy /y /e /i "LICENSES" "dist\portable\LICENSES" >nul
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
echo   Portable app: dist\portable\CVAFPI-IDSYS.exe
echo   Installer:    installer\CVAFPI-IDSYS-Setup.exe