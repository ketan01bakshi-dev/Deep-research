@echo off
cd /d "%~dp0"
.\.venv\Scripts\python.exe -m pytest tests packages\cursor_agent_core\tests -v --tb=short
exit /b %ERRORLEVEL%
