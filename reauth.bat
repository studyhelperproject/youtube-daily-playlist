@echo off
chcp 65001 > nul
title YouTube API 再認証

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [エラー] Python仮想環境 (.venv) が見つかりません。
    pause
    exit /b 1
)

.venv\Scripts\python.exe reauth.py

echo.
pause
