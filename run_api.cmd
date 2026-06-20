@echo off
cd /d "%~dp0"
.\.venv\Scripts\uvicorn apps.api.main:app --host 127.0.0.1 --port 8765
pause
