"""All project Parquet I/O uses fastparquet to avoid blocked native pyarrow DLLs."""
from __future__ import annotations

from datetime import timezone
import importlib.util
import pandas as pd

_orig_to_parquet = pd.DataFrame.to_parquet
_orig_read_parquet = pd.read_parquet
_installed = False


def assert_fastparquet_available() -> None:
    """Ensure the explicitly selected Parquet engine is installed."""
    if importlib.util.find_spec('fastparquet') is None:
        raise RuntimeError('fastparquet is required; project Parquet I/O must use it explicitly')


def write_parquet(frame, path, *args, **kwargs):
    """Write parquet through fastparquet, never probing pyarrow first."""
    kwargs.pop('engine', None)
    return _orig_to_parquet(frame, path, *args, engine='fastparquet', **kwargs)


def read_parquet(path, *args, **kwargs):
    """Read parquet through fastparquet and normalize UTC indexes."""
    kwargs.pop('engine', None)
    frame = _orig_read_parquet(path, *args, engine='fastparquet', **kwargs)
    if isinstance(frame.index, pd.DatetimeIndex) and str(frame.index.tz) == 'UTC':
        frame = frame.copy()
        frame.index = frame.index.tz_convert(timezone.utc)
    return frame


def install_parquet_fallback() -> None:
    """Keep pandas convenience methods safe for legacy/test callers."""
    global _installed
    if _installed:
        return

    def safe_to_parquet(self, path, *args, **kwargs):
        return write_parquet(self, path, *args, **kwargs)

    def safe_read_parquet(path, *args, **kwargs):
        return read_parquet(path, *args, **kwargs)

    pd.DataFrame.to_parquet = safe_to_parquet
    pd.read_parquet = safe_read_parquet
    _installed = True
