@echo off
setlocal
cd /d "%~dp0" || exit /b 1

if exist "dist\portable\CVAFPI-IDSYS.exe" (
    start "CVAFPI Identification System" /wait "dist\portable\CVAFPI-IDSYS.exe"
) else (
    call "CVAFPI IDENTIFICATION SYSTEM.bat"
)