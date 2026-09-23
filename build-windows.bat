@echo off
setlocal
cd /d "%~dp0"

if not exist .venv-windows (
    py -3 -m venv .venv-windows
)
call .venv-windows\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-windows.txt pyinstaller
python -m PyInstaller --clean --noconfirm ID-BIO-Project.spec

echo.
echo Build complete: dist\CVAFPI-IDSYS.exe
pause