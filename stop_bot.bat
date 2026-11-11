@echo off
cd /d "%~dp0"
echo [INFO] Bot dayandirilir...

:: STOP fayli yaradiriq ki, hec bir modul yeni emeliyyat acmasin ve derhal dayansin
echo HALT > STOP
echo HALT > STOP.txt

:: supervisor.stop fayli yaradiriq
if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python.exe -c "from pathlib import Path; from src.paths import project_paths; project_paths(Path.cwd())[0].joinpath('supervisor.stop').write_text('stop_bot.bat invoked\n', encoding='utf-8')"
)

:: Fon prosesleri ucun taskkill (lazim olarsa)
echo [INFO] Fon prosesleri yoxlanilir...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'scripts\\\\run_bot.py|scripts\\\\run_forever.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

echo [OK] Bot ve supervisor dayandirildi.
echo MT5 terminali aciq qalibsa ve istemirsinizse, onu manual baglaya bilersiniz.
timeout /t 2 >nul
exit /b 0
