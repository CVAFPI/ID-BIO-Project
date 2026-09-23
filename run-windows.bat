@echo off
setlocal
cd /d "%~dp0"
set "CVAFPI_DATA_DIR=%~dp0"
call .venv-windows\Scripts\activate.bat
python windows_launcher.py