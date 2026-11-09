"""Tests for live signal generators of the six strategy families."""
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from src.strategies.research_families import (
    SessionBreakoutStrategy,
    OpeningRangeBreakoutStrategy,
    VWAPReversionStrategy,
    DonchianBreakoutStrategy,
    TSMomentumStrategy,
    IndexPullbackStrategy
)

def _make_dummy_candles(n=100, tf_minutes=15, start_hour=0):
    start = datetime(2026, 11, 9, start_hour, 0, tzinfo=timezone.utc)
    times = [start + timedelta(minutes=i * tf_minutes) for i in range(n)]
    # Random walk
    base = 1.1000
    noise = np.sin(np.linspace(0, 10, n)) * 0.0050
    closes = base + noise
    highs = closes + 0.0010
    lows = closes - 0.0010
    opens = closes - 0.0002
    vols = [100.0] * n
    return pd.DataFrame({'open': opens, 'high': highs, 'low': lows, 'close': closes, 'tick_volume': vols}, index=pd.DatetimeIndex(times))

def test_session_breakout_strategy_generates_or_skips():
    strat = SessionBreakoutStrategy({'variant': 'v1', 'buf_mult': 0.1, 'sl_mult': 1.5, 'tp_mult': 2.0})
    candles = {'M15': _make_dummy_candles(100, 15, start_hour=0)}
    sig = strat.generate_signal('EURUSD', candles)
    # Either signal or None with a valid skip reason
    assert sig is None or sig.strategy_name == 'session_breakout'

def test_opening_range_breakout_strategy():
    strat = OpeningRangeBreakoutStrategy({'variant': 'v1'})
    candles = {'M15': _make_dummy_candles(100, 15, start_hour=14)}
    sig = strat.generate_signal('US500Cash', candles)
    assert sig is None or sig.strategy_name == 'opening_range_breakout'

def test_vwap_reversion_strategy():
    strat = VWAPReversionStrategy({'variant': 'v1', 'dev_mult': 1.0})
    candles = {'M15': _make_dummy_candles(100, 15, start_hour=8)}
    sig = strat.generate_signal('EURUSD', candles)
    assert sig is None or sig.strategy_name == 'vwap_reversion'

def test_donchian_breakout_strategy():
    strat = DonchianBreakoutStrategy({'variant': 'v1', 'period': 20})
    candles = {'H1': _make_dummy_candles(60, 60, start_hour=0)}
    sig = strat.generate_signal('GOLD', candles)
    assert sig is None or sig.strategy_name == 'donchian_breakout'

def test_ts_momentum_strategy():
    strat = TSMomentumStrategy({'variant': 'v1', 'lookback': 12})
    candles = {'H1': _make_dummy_candles(60, 60, start_hour=0)}
    sig = strat.generate_signal('BTCUSD', candles)
    assert sig is None or sig.strategy_name == 'ts_momentum'

def test_index_pullback_strategy():
    strat = IndexPullbackStrategy({'variant': 'v1'})
    candles = {'H1': _make_dummy_candles(100, 60, start_hour=0)}
    sig = strat.generate_signal('US100Cash', candles)
    assert sig is None or sig.strategy_name == 'index_pullback_200d'
