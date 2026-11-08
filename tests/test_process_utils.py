from src.process_utils import pid_is_running


class FakeKernel:
    def __init__(self, handle=10, exit_code=259, query_ok=True):
        self.handle = handle
        self.exit_code = exit_code
        self.query_ok = query_ok
        self.closed = []

    def OpenProcess(self, access, inherit, pid):
        return self.handle

    def GetExitCodeProcess(self, handle, output):
        if self.query_ok:
            output._obj.value = self.exit_code
            return 1
        return 0

    def CloseHandle(self, handle):
        self.closed.append(handle)


def test_windows_pid_check_uses_still_active_code():
    kernel = FakeKernel()
    assert pid_is_running(42, windows=True, kernel32=kernel)
    assert kernel.closed == [10]
    assert not pid_is_running(42, windows=True, kernel32=FakeKernel(exit_code=0))


def test_windows_pid_check_fails_closed_on_query_error_and_access_denied():
    assert pid_is_running(42, windows=True, kernel32=FakeKernel(query_ok=False))
    assert pid_is_running(42, windows=True, kernel32=FakeKernel(handle=0), get_last_error=lambda: 5)
    assert not pid_is_running(42, windows=True, kernel32=FakeKernel(handle=0), get_last_error=lambda: 87)


def test_pid_check_rejects_invalid_and_nonpositive_ids():
    assert not pid_is_running(None)
    assert not pid_is_running("not-a-pid")
    assert not pid_is_running(0)
