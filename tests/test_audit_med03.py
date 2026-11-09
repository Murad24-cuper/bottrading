import pandas as pd
import pytest
from src.patterns.fibonacci import fibonacci_retracement

def test_fibonacci_retracement_does_not_crash_when_atr_is_zero():
    # Construct a dataframe with a swing, but recent bars flat so ATR becomes 0
    # First 15 bars create high=100 and low=50
    data = []
    for i in range(15):
        data.append({"open": 50 + i * 3, "high": 52 + i * 3, "low": 48 + i * 3, "close": 51 + i * 3})
    # Peak at bar 15: high=100
    data.append({"open": 95, "high": 100, "low": 90, "close": 95})
    # Then flat bars where high == low == open == close, so ATR decays to 0
    # Touching a fib level with a rejection candle
    fib_price = 100 - (100 - 48) * 0.382  # ~80.136
    for _ in range(25):
        data.append({"open": fib_price, "high": fib_price, "low": fib_price, "close": fib_price})
    # Last closed bar is wide enough to touch both 0.382 and 0.50 levels
    data.append({"open": 60, "high": 90, "low": 60, "close": 85})
    # Final unclosed bar
    data.append({"open": 85, "high": 85, "low": 85, "close": 85})

    df = pd.DataFrame(data)

    # Monkeypatch atr to return 0.0 to guarantee a=0 branch is exercised
    import src.patterns.fibonacci as fib_mod
    orig_atr = fib_mod.atr
    fib_mod.atr = lambda d: pd.Series([0.0] * len(d), index=d.index)
    try:
        res = fibonacci_retracement(df, "M15")
        assert res["nearest"] is not None
        assert res["levels"][0]["distance_atr"] is None
        # Must not raise TypeError when rejection is True and distance_atr is None
        if res["reacting"]:
            assert res["reaction_level"] is not None
    finally:
        fib_mod.atr = orig_atr
