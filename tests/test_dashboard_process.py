import os

from src.dashboard.app import _pid_running


def test_process_probe_recognizes_current_and_missing_pid():
    assert _pid_running(os.getpid())
    assert not _pid_running(2147483647)
    assert not _pid_running(None)
