"""Run and supervise the bot process without coupling it to a terminal window."""
from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import time
import shutil
from datetime import datetime,timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import assert_runtime_location,load_settings
from src.db import Database
from src.logger import get_logger
from src.process_utils import pid_is_running
from src.supervisor import clear_stale_pid_lock, run_restart_supervisor, heartbeat_is_stale, hang_watchdog_should_terminate, write_hang_report, detached_python_executable
from scripts.run_bot import install_crash_handlers
from src.paths import project_paths
from src.scheduler import due_scheduler_jobs,run_scheduler_tick,run_daily_backup,should_restart_for_memory

log = get_logger('bot.supervisor')

def health_check_due(last_check: float, now: float, interval: float=60.0) -> bool:
    """Return whether the supervisor's periodic child-health check is due."""
    return float(now)-float(last_check)>=float(interval)

def utc_now() -> datetime:
    """Return an aware UTC timestamp for supervisor schedules and events."""
    return datetime.now(timezone.utc)


def _pid_alive(pid: int) -> bool:
    return pid_is_running(pid)

def _process_memory_mb(pid: int) -> float|None:
    """Read process working-set size with the Windows API, without psutil."""
    if os.name!='nt': return None
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD),('PeakWorkingSetSize',ctypes.c_size_t),('WorkingSetSize',ctypes.c_size_t),('QuotaPeakPagedPoolUsage',ctypes.c_size_t),('QuotaPagedPoolUsage',ctypes.c_size_t),('QuotaPeakNonPagedPoolUsage',ctypes.c_size_t),('QuotaNonPagedPoolUsage',ctypes.c_size_t),('PagefileUsage',ctypes.c_size_t),('PeakPagefileUsage',ctypes.c_size_t)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]; kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x0400|0x0010,False,int(pid))
    if not handle: return None
    try:
        counters=Counters(); counters.cb=ctypes.sizeof(counters)
        psapi=ctypes.WinDLL('psapi',use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype=wintypes.BOOL
        if not psapi.GetProcessMemoryInfo(handle,ctypes.byref(counters),counters.cb): return None
        return counters.WorkingSetSize/1024**2
    finally: kernel.CloseHandle(handle)


def main() -> int:
    if sys.stdout is None or sys.stderr is None:
        _,log_dir=project_paths(ROOT); output=log_dir/'bot_stdout.log'; output.parent.mkdir(parents=True,exist_ok=True)
        stream=output.open('a',encoding='utf-8',buffering=1); sys.stdout=stream; sys.stderr=stream
    install_crash_handlers()
    settings = load_settings()
    assert_runtime_location(settings.config)
    db = Database(settings.db_path)
    data_dir = settings.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    pid_path = data_dir / 'supervisor.pid'
    stop_path = data_dir / 'supervisor.stop'
    for attempt in range(2):
        try:
            with pid_path.open('x',encoding='utf-8') as handle: handle.write(str(os.getpid()))
            break
        except FileExistsError:
            try: prior_pid=int(pid_path.read_text(encoding='utf-8').strip())
            except (OSError,ValueError): prior_pid=0
            if prior_pid and _pid_alive(prior_pid):
                db.log_event('WARNING','supervisor',f'Supervisor start refused; PID {prior_pid} is already running')
                return 1
            try: pid_path.unlink(missing_ok=True)
            except OSError:
                db.log_event('CRITICAL','supervisor','Supervisor could not remove its stale PID file')
                return 1
    else:
        db.log_event('CRITICAL','supervisor','Supervisor could not claim its PID file')
        return 1
    backoff = settings.config['supervisor']
    child_script = settings.root / 'scripts' / 'run_bot.py'
    bot_lock = data_dir / 'bot.lock'
    child = None

    def emit(level: str, message: str) -> None:
        getattr(log, level.lower(), log.info)(message)
        db.log_event(level, 'supervisor', message)

    def should_stop() -> bool:
        return stop_path.exists()

    def run_child() -> int:
        nonlocal child
        last_health_check=0.0; last_disk_warning=0.0
        if not clear_stale_pid_lock(bot_lock,_pid_alive):
            try: existing=bot_lock.read_text(encoding='utf-8').split()[0]
            except (OSError,IndexError): existing='unknown'
            emit('CRITICAL',f'Bot child not launched; bot lock is malformed or PID {existing} is still active')
            stop_path.write_text('existing bot lock\n',encoding='utf-8')
            return 0
        base_flags = getattr(subprocess, 'DETACHED_PROCESS',0x00000008) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x00000200)
        breakaway = getattr(subprocess, 'CREATE_BREAKAWAY_FROM_JOB', 0x01000000)
        output_path=settings.logs_dir/'bot_stdout.log'; output_path.parent.mkdir(parents=True,exist_ok=True)
        output_handle=output_path.open('a',encoding='utf-8',buffering=1)
        options = {'cwd': settings.root, 'stdin': subprocess.DEVNULL,
                   'stdout': output_handle, 'stderr': subprocess.STDOUT, 'close_fds': True}
        try:
            interpreter=detached_python_executable(sys.executable)
            try: child = subprocess.Popen([interpreter, str(child_script)], creationflags=base_flags | breakaway, **options)
            except OSError: child = subprocess.Popen([interpreter, str(child_script)], creationflags=base_flags, **options)
        finally: output_handle.close()
        emit('INFO', f'Bot child started PID={child.pid}')
        hang_seconds=int(backoff['hang_seconds'])
        child_started=time.monotonic()
        while True:
            try: return int(child.wait(timeout=1))
            except subprocess.TimeoutExpired: pass
            tick=time.monotonic()
            if health_check_due(last_health_check,tick):
                last_health_check=tick
                free=shutil.disk_usage(settings.data_dir).free
                health=settings.config.get('health',{})
                if free<float(health.get('warn_disk_free_gb',5))*1024**3 and tick-last_disk_warning>=3600:
                    emit('WARNING',f'Disk free space is low: {free/1024**3:.2f} GB')
                    last_disk_warning=tick
                memory=_process_memory_mb(child.pid)
                if should_restart_for_memory(memory,float(health.get('max_memory_mb',1500))):
                    emit('CRITICAL',f'Bot working set {memory:.0f} MB exceeds limit; restarting process without closing broker positions')
                    child.terminate()
                    try: child.wait(timeout=5)
                    except subprocess.TimeoutExpired: child.kill(); child.wait()
                    return 125
                completed=set()
                for task,key in due_scheduler_jobs(utc_now(),settings.config):
                    if db.maintenance_done(task,key): completed.add((task,key))
                def daily_backup_job(key):
                    try: run_daily_backup(settings,db,utc_now())
                    except Exception as exc: emit('ERROR',f'Daily DB backup failed: {type(exc).__name__}: {exc}')
                def hourly_history_job(key):
                    emit('INFO','Incremental history refresh runs in small batches through the bot child shared MT5 session')
                    db.mark_maintenance_done('hourly_history',key,utc_now())
                def weekly_job(key):
                    emit('WARNING','Weekly brain retraining deferred: no complete training pipeline/data is available; brain remains shadow-only')
                    db.mark_maintenance_done('weekly_retrain',key,utc_now())
                    db.mark_maintenance_done('weekly_maintenance',key,utc_now())
                run_scheduler_tick(utc_now(),settings.config,completed,{'daily_backup':daily_backup_job,'hourly_history':hourly_history_job,'weekly_maintenance':weekly_job})
            if hang_watchdog_should_terminate(heartbeat_is_stale(settings.db_path,hang_seconds),time.monotonic()-child_started,hang_seconds):
                reason=f'heartbeat older than {hang_seconds}s; child PID={child.pid}'
                write_hang_report(settings.logs_dir,reason)
                emit('CRITICAL',f'Hang watchdog: {reason}; terminating child for supervised restart')
                try: child.terminate(); child.wait(timeout=5)
                except subprocess.TimeoutExpired: child.kill(); child.wait()
                return 124

    emit('INFO', f'Supervisor started PID={os.getpid()}')
    try:
        return run_restart_supervisor(
            run_child, should_stop, emit,
            backoff['restart_backoff_seconds'],
            backoff['max_restarts_per_hour'],
            int(backoff['restart_window_minutes']) * 60,
        )
    finally:
        try:
            if pid_path.read_text(encoding='utf-8').strip() == str(os.getpid()):
                pid_path.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == '__main__':
    raise SystemExit(main())
