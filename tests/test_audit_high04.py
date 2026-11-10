import pandas as pd
import pytest
from src.parquet_compat import install_parquet_fallback

def test_parquet_fallback_preserves_dataframe_structure(tmp_path):
    install_parquet_fallback()
    df = pd.DataFrame(
        {
            "open": [1.1000, 1.1010],
            "high": [1.1020, 1.1030],
            "low": [1.0990, 1.1005],
            "close": [1.1015, 1.1025],
            "tick_volume": [100, 150],
            "spread": [15, 12],
        },
        index=pd.date_range("2026-01-01", periods=2, freq="15min", tz="UTC")
    )

    path = tmp_path / "EURUSD_M15.parquet"
    from src.parquet_compat import write_parquet
    write_parquet(df,path)
    assert path.exists()

    from src.parquet_compat import read_parquet
    loaded = read_parquet(path)
    assert loaded.shape == df.shape
    assert list(loaded.columns) == list(df.columns)
    assert loaded.index.tz == df.index.tz
    assert (loaded["close"] == df["close"]).all()
