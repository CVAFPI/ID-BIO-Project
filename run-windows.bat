@echo off
setlocal
cd /d "%~dp0" || exit /b 1

if exist "dist\CVAFPI-IDSYS.exe" (
    start "CVAFPI Identification System" /wait "dist\CVAFPI-IDSYS.exe"
) else (
    call "CVAFPI IDENTIFICATION SYSTEM.bat"
)