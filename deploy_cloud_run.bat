@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy_cloud_run.ps1" %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Process exited with code %ERRORLEVEL%.
    pause
)
