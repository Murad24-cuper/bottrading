import numpy as np
import pandas as pd

from src.trade_rules import confidence_allowed, mtf_direction_agrees, stop_target_from_atr, spread_within_median, may_extend


def _frame(direction='buy', bars=80):
    close = np.arange(bars, dtype=float) if direction == 'buy' else np.arange(bars, dtype=float)[::-1]
    return pd.DataFrame({'open': close, 'high': close + .2, 'low': close - .2, 'close': close,
                         'tick_volume': np.full(bars, 10.)})


def test_mtf_agreement_requires_all_three_directions():
    candles = {tf: _frame() for tf in ('M1', 'M5', 'M15')}
    assert mtf_direction_agrees(candles, 'buy')
    candles['M5'] = _frame('sell')
    assert not mtf_direction_agrees(candles, 'buy')


def test_stop_target_from_atr_scales_expected_ten_minute_move():
    sl, tp = stop_target_from_atr(100, 'buy', 2, .5, .8, 1.2)
    assert sl == 100 - 2 * np.sqrt(10) * .8
    assert tp == 100 + 2 * np.sqrt(10) * 1.2 + .5


def test_spread_must_be_within_median_multiple():
    assert spread_within_median(15, 10, 1.5)
    assert not spread_within_median(15.01, 10, 1.5)
    assert not spread_within_median(1, 0, 1.5)


def test_confidence_gate():
    assert confidence_allowed(.6, .6)
    assert not confidence_allowed(.59, .6)


def test_extension_requires_protected_profitable_trade_and_score():
    args = dict(in_profit=True, scaled_out=True, stop_protects_profit=True, mtf_agrees=True,
                momentum_rising=True, continuation_score=.8, minimum_score=.7,
                age_minutes=10, max_minutes=10)
    assert may_extend(**args)
    assert not may_extend(**{**args, 'in_profit': False})
    assert not may_extend(**{**args, 'stop_protects_profit': False})
    assert not may_extend(**{**args, 'age_minutes': 60})
