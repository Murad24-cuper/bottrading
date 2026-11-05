@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Create it and install requirements.txt first.
  exit /b 1
)
call ".venv\Scripts\activate.bat"
python scripts\run_bot.py
