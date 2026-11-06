"""Crash restart policy kept independent from process and MT5 details."""
from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence
from pathlib import Path
import time
from .notify import TelegramNotifier

_notifier=None


def clear_stale_pid_lock(path: str | Path, pid_is_alive: Callable[[int], bool]) -> bool:
    """Remove a bot lock only when its recorded owner process is confirmed dead."""
    lock=Path(path)
    if not lock.exists(): return True
    try: pid=int(lock.read_text(encoding='utf-8').split()[0])
    except (OSError,ValueError,IndexError): return False
    if pid<=0 or pid_is_alive(pid): return False
    try: lock.unlink(missing_ok=True)
    except OSError: return False
    return True


def run_restart_supervisor(
    run_child: Callable[[], int],
    stop_requested: Callable[[], bool],
    log_event: Callable[[str, str], None],
    backoff_seconds: Sequence[int] = (10, 30, 60),
    max_restarts: int = 5,
    window_seconds: int = 3600,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.time,
) -> int:
    """Restart unexpected exits with bounded backoff and a sliding hourly cap."""
    restarts: deque[float] = deque()
    while True:
        if stop_requested():
            log_event('INFO', 'bot exiting reason=stop requested')
            return 0
        try:
            return_code = int(run_child())
        except BaseException as exc:
            return_code = 1
            log_event('ERROR', f'Child launch/wait failed: {type(exc).__name__}: {exc}')
        if stop_requested():
            log_event('INFO', 'bot exiting reason=dashboard stop command')
            return 0
        now = clock()
        while restarts and now - restarts[0] >= window_seconds:
            restarts.popleft()
        if len(restarts) >= max_restarts:
            log_event('CRITICAL', f'Supervisor restart limit reached: {max_restarts} restarts within {window_seconds} seconds; last child exit={return_code}')
            log_event('INFO', 'bot exiting reason=supervisor restart limit exceeded')
            return 1
        delay = int(backoff_seconds[min(len(restarts), len(backoff_seconds) - 1)])
        restarts.append(now)
        message=f'Restarting bot after exit code {return_code}; restart {len(restarts)}/{max_restarts} in window, delay={delay}s'
        log_event('WARNING', message)
        global _notifier
        if _notifier is None: _notifier=TelegramNotifier()
        _notifier.send('supervisor_restart',f'🔄 Nəzarətçi botu yenidən başladır · cəhd {len(restarts)}/{max_restarts}.')
        sleep(delay)
