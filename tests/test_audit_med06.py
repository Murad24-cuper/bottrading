from unittest.mock import patch, MagicMock
from pathlib import Path
import pytest
from src.supervisor import write_hang_report

def test_write_hang_report_accepts_child_pid_and_requests_traceback(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    # Before fix: write_hang_report does not take child_pid or call request_child_traceback
    with patch("src.supervisor.request_child_traceback") as mock_req:
        write_hang_report(log_dir, "test hang", child_pid=12345)
        mock_req.assert_called_once_with(12345)

    crash_log = (log_dir / "crash.log").read_text(encoding="utf-8")
    assert "PID=12345" in crash_log
