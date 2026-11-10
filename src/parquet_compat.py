"""Transparent fallback for parquet reading/writing when native parquet DLLs are blocked by WDAC/AppLocker."""
from __future__ import annotations
import pickle
import pandas as pd
from datetime import timezone

_orig_to_parquet = pd.DataFrame.to_parquet
_orig_read_parquet = pd.read_parquet
_installed = False

def install_parquet_fallback() -> None:
    global _installed
    if _installed:
        return

    def safe_to_parquet(self, path, *args, **kwargs):
        try:
            return _orig_to_parquet(self, path, *args, **kwargs)
        except Exception:
            try:
                return _orig_to_parquet(self, path, *args, engine='fastparquet', **kwargs)
            except Exception:
                with open(path, 'wb') as f:
                    pickle.dump(self, f)

    def safe_read_parquet(path, *args, **kwargs):
        try:
            frame=_orig_read_parquet(path, *args, **kwargs)
        except Exception:
            try:
                frame=_orig_read_parquet(path, *args, engine='fastparquet', **kwargs)
            except Exception:
                with open(path, 'rb') as f:
                    frame=pickle.load(f)
        if isinstance(frame.index,pd.DatetimeIndex) and str(frame.index.tz)=='UTC':
            frame=frame.copy()
            frame.index=frame.index.tz_convert(timezone.utc)
        return frame

    pd.DataFrame.to_parquet = safe_to_parquet
    pd.read_parquet = safe_read_parquet
    _installed = True

install_parquet_fallback()
