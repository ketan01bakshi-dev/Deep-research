@echo off
cd /d "%~dp0"
.\.venv\Scripts\python scripts\generate_all_docs.py
pause
