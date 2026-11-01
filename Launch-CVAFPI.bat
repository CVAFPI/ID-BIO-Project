@echo off
setlocal
set "CVAFPI_DATA_DIR=%LOCALAPPDATA%\CVAFPI"
if not exist "%CVAFPI_DATA_DIR%" mkdir "%CVAFPI_DATA_DIR%"
if errorlevel 1 exit /b 1
start "" /D "%~dp0" "%~dp0CVAFPI-IDSYS.exe"
