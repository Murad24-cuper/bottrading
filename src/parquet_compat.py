"""Transparent fallback for parquet reading/writing when native parquet DLLs are blocked by WDAC/AppLocker."""
from __future__ import annotations
import pickle
import pandas as pd

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
        except (ImportError, Exception):
            with open(path, 'wb') as f:
                pickle.dump(self, f)

    def safe_read_parquet(path, *args, **kwargs):
        try:
            return _orig_read_parquet(path, *args, **kwargs)
        except (ImportError, Exception):
            with open(path, 'rb') as f:
                return pickle.load(f)

    pd.DataFrame.to_parquet = safe_to_parquet
    pd.read_parquet = safe_read_parquet
    _installed = True

install_parquet_fallback()
