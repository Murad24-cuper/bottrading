"""Small Windows-only runtime helpers with safe no-op behavior elsewhere."""
from __future__ import annotations
import os


ES_CONTINUOUS=0x80000000
ES_SYSTEM_REQUIRED=0x00000001


def set_system_awake(enabled: bool, kernel32=None) -> bool:
    """Prevent system sleep while supervising, or clear the execution request."""
    if os.name!='nt' and kernel32 is None: return False
    if kernel32 is None:
        import ctypes
        kernel32=ctypes.WinDLL('kernel32',use_last_error=True)
    flags=ES_CONTINUOUS|(ES_SYSTEM_REQUIRED if enabled else 0)
    return bool(kernel32.SetThreadExecutionState(flags))
