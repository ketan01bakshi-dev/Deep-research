@echo off
REM Example: schedule_mission.cmd missions\protein_digestion.json
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: schedule_mission.cmd path\to\mission.json [--pipeline]
  exit /b 1
)
.\.venv\Scripts\python scripts\schedule_mission.py --mission-file %*
pause
