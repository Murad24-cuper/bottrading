@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Create it and install requirements.txt first.
  exit /b 1
)
.venv\Scripts\python.exe -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd())); from src.paths import project_paths; project_paths(Path.cwd())[0].joinpath('supervisor.stop').unlink(missing_ok=True)"
if errorlevel 1 exit /b %ERRORLEVEL%
start "" /b .venv\Scripts\pythonw.exe scripts\run_forever.py
exit /b 0
