@echo off
setlocal EnableExtensions
cd /d "%~dp0" || exit /b 1

if not exist ".venv-windows\Scripts\python.exe" py -3 -m venv .venv-windows
if errorlevel 1 exit /b 1
call ".venv-windows\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 exit /b 1

python -m PyInstaller --clean --noconfirm ID-BIO-Project.spec
if errorlevel 1 exit /b 1

copy /y data.csv dist\data.csv >nul
copy /y backup-data.csv dist\backup-data.csv >nul
if exist settings.json copy /y settings.json dist\settings.json >nul
if not exist dist\CVA_Database mkdir dist\CVA_Database
if not exist dist\logs mkdir dist\logs

echo.
echo Build complete: dist\CVAFPI-IDSYS.exe
pause