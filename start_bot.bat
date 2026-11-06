@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Create it and install requirements.txt first.
  exit /b 1
)
call ".venv\Scripts\activate.bat"
if not exist "logs" mkdir "logs"
if exist "data\supervisor.stop" del "data\supervisor.stop"
python scripts\run_forever.py >> "logs\bot_stdout.log" 2>&1
exit /b %ERRORLEVEL%
