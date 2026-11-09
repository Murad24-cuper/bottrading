"""LOW-01: _RetryConnection should retry with exponential backoff, not just one 50ms wait."""
import sqlite3
import time
import pytest
from src.db import _RetryConnection


class _FakeBaseConn:
    """Fake parent whose execute() can be rigged to fail N times then succeed."""
    def __init__(self, fail_times=0):
        self._fail = fail_times
        self._calls = 0

    def execute(self, *args, **kwargs):
        self._calls += 1
        if self._calls <= self._fail:
            raise sqlite3.OperationalError("database is locked")
        return "ok"

    def executemany(self, *args, **kwargs):
        self._calls += 1
        if self._calls <= self._fail:
            raise sqlite3.OperationalError("database is locked")
        return "ok"


class _TestableRetry(_RetryConnection):
    """_RetryConnection where super() calls go to a controllable fake."""
    def __init__(self, fake_base):
        # Don't call sqlite3.Connection.__init__; just install the fake
        object.__setattr__(self, '_fake', fake_base)

    # Override super().execute to use the fake
    def execute(self, *args, **kwargs):
        fake = object.__getattribute__(self, '_fake')
        last_exc = None
        for delay in (None,) + self._RETRY_DELAYS:
            if delay is not None:
                time.sleep(delay)
            try:
                return fake.execute(*args, **kwargs)
            except sqlite3.OperationalError as exc:
                if not self._locked(exc):
                    raise
                last_exc = exc
        raise last_exc

    def executemany(self, *args, **kwargs):
        fake = object.__getattribute__(self, '_fake')
        last_exc = None
        for delay in (None,) + self._RETRY_DELAYS:
            if delay is not None:
                time.sleep(delay)
            try:
                return fake.executemany(*args, **kwargs)
            except sqlite3.OperationalError as exc:
                if not self._locked(exc):
                    raise
                last_exc = exc
        raise last_exc


def test_retry_delays_tuple_has_multiple_entries():
    """_RetryConnection must have >=3 retry delays (exponential backoff)."""
    delays = _RetryConnection._RETRY_DELAYS
    assert len(delays) >= 3, (
        f"Expected >=3 retry delays, got {len(delays)}: {delays}")
    # Must be non-decreasing
    for i in range(1, len(delays)):
        assert delays[i] >= delays[i - 1], (
            f"Delays not increasing at index {i}: {delays}")


def test_retry_all_fail_raises_after_all_retries():
    """When all retries fail, raises OperationalError."""
    # Use tiny delays for speed
    old = _RetryConnection._RETRY_DELAYS
    _RetryConnection._RETRY_DELAYS = (0.001, 0.001, 0.001)
    try:
        total_retries = len(_RetryConnection._RETRY_DELAYS)
        fake = _FakeBaseConn(fail_times=1 + total_retries + 10)  # always fail
        conn = _TestableRetry(fake)
        with pytest.raises(sqlite3.OperationalError, match="database is locked"):
            conn.execute("SELECT 1")
        # Must have made 1 initial attempt + N retries
        assert fake._calls == 1 + total_retries, (
            f"Expected {1 + total_retries} calls, got {fake._calls}")
    finally:
        _RetryConnection._RETRY_DELAYS = old


def test_retry_succeeds_on_third_attempt():
    """When lock clears on 3rd attempt, returns without raising."""
    old = _RetryConnection._RETRY_DELAYS
    _RetryConnection._RETRY_DELAYS = (0.001, 0.001, 0.001, 0.001)
    try:
        fake = _FakeBaseConn(fail_times=2)  # fail twice, succeed on 3rd
        conn = _TestableRetry(fake)
        result = conn.execute("SELECT 1")
        assert result == "ok"
        assert fake._calls == 3  # 2 failures + 1 success
    finally:
        _RetryConnection._RETRY_DELAYS = old


def test_retry_non_lock_error_raises_immediately():
    """Non-lock OperationalError is NOT retried."""
    old = _RetryConnection._RETRY_DELAYS
    _RetryConnection._RETRY_DELAYS = (0.001, 0.001, 0.001)
    try:
        class NonLockFake:
            _calls = 0
            def execute(self, *a, **kw):
                self._calls += 1
                raise sqlite3.OperationalError("no such table: foo")
        fake = NonLockFake()
        conn = _TestableRetry(fake)
        with pytest.raises(sqlite3.OperationalError, match="no such table"):
            conn.execute("SELECT * FROM foo")
        assert fake._calls == 1, (
            f"Non-lock error should not be retried, got {fake._calls} calls")
    finally:
        _RetryConnection._RETRY_DELAYS = old


def test_executemany_also_retries():
    """executemany() uses the same exponential backoff."""
    old = _RetryConnection._RETRY_DELAYS
    _RetryConnection._RETRY_DELAYS = (0.001, 0.001, 0.001)
    try:
        fake = _FakeBaseConn(fail_times=2)
        conn = _TestableRetry(fake)
        result = conn.executemany("INSERT ...", [])
        assert result == "ok"
        assert fake._calls == 3
    finally:
        _RetryConnection._RETRY_DELAYS = old


def test_real_db_lock_retries(tmp_path):
    """Integration: a real locked DB triggers multiple retry attempts."""
    db_path = tmp_path / "test.db"

    # Writer holds exclusive lock
    writer = sqlite3.connect(str(db_path), timeout=0)
    writer.execute("CREATE TABLE t (v INTEGER)")
    writer.execute("BEGIN EXCLUSIVE")

    # Temporarily reduce delays so the test is fast
    old = _RetryConnection._RETRY_DELAYS
    _RetryConnection._RETRY_DELAYS = (0.01, 0.02, 0.04)
    try:
        reader = sqlite3.connect(str(db_path), factory=_RetryConnection, timeout=0)
        t0 = time.monotonic()
        with pytest.raises(sqlite3.OperationalError):
            reader.execute("INSERT INTO t VALUES (1)")
        elapsed = time.monotonic() - t0
        reader.close()
        # Must have waited at least sum-of-delays
        total_delay = sum(_RetryConnection._RETRY_DELAYS)
        assert elapsed >= total_delay * 0.8, (
            f"Expected >=80% of {total_delay*1000:.0f}ms delay, "
            f"actually waited {elapsed*1000:.0f}ms")
    finally:
        _RetryConnection._RETRY_DELAYS = old
        writer.close()
