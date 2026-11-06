"""Run and supervise the bot process without coupling it to a terminal window."""
from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_settings
from src.db import Database
from src.logger import get_logger
from src.supervisor import clear_stale_pid_lock, run_restart_supervisor
from scripts.run_bot import install_crash_handlers

log = get_logger('bot.supervisor')


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def main() -> int:
    if sys.stdout is None or sys.stderr is None:
        output=(ROOT/'logs'/'bot_stdout.log'); output.parent.mkdir(parents=True,exist_ok=True)
        stream=output.open('a',encoding='utf-8',buffering=1); sys.stdout=stream; sys.stderr=stream
    install_crash_handlers()
    settings = load_settings()
    db = Database(settings.db_path)
    data_dir = settings.root / 'data'
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
        if not clear_stale_pid_lock(bot_lock,_pid_alive):
            try: existing=bot_lock.read_text(encoding='utf-8').split()[0]
            except (OSError,IndexError): existing='unknown'
            emit('CRITICAL',f'Bot child not launched; bot lock is malformed or PID {existing} is still active')
            stop_path.write_text('existing bot lock\n',encoding='utf-8')
            return 0
        base_flags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x00000200)
        breakaway = getattr(subprocess, 'CREATE_BREAKAWAY_FROM_JOB', 0x01000000)
        options = {'cwd': settings.root, 'stdin': subprocess.DEVNULL,
                   'stdout': None, 'stderr': subprocess.STDOUT, 'close_fds': True}
        try:
            child = subprocess.Popen([sys.executable, str(child_script)], creationflags=base_flags | breakaway, **options)
        except OSError:
            child = subprocess.Popen([sys.executable, str(child_script)], creationflags=base_flags, **options)
        emit('INFO', f'Bot child started PID={child.pid}')
        return int(child.wait())

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
