"""Small cross-platform process checks for PID locks and health reports."""
from __future__ import annotations

import os


def pid_is_running(pid: int | str | None, *, windows: bool | None = None,
                   kernel32=None, get_last_error=None) -> bool:
    """Check whether a PID exists without treating Windows error 87 as death."""
    try:
        value = int(pid)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    if value <= 0:
        return False
    if windows is None:
        windows = os.name == "nt"
    if windows:
        import ctypes
        if kernel32 is None:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            from ctypes import wintypes
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel32.GetExitCodeProcess.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            get_last_error = ctypes.get_last_error
        handle = kernel32.OpenProcess(0x1000, False, value)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return bool(get_last_error and get_last_error() == 5)  # Access denied: assume it exists.
        try:
            from ctypes import wintypes
            exit_code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return True  # Could not inspect an opened process; fail closed for lock safety.
            return exit_code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(value, 0)
        return True
    except PermissionError:
        return True
    except (OSError, ProcessLookupError):
        return False
