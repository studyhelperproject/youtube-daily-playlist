@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& '.\.venv\Scripts\python.exe' 'reauth.py'"
pause
