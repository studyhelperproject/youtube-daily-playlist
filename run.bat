@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Process exited with code %ERRORLEVEL%.
    pause
)
