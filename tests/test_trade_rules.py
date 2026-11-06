import numpy as np
import pandas as pd

from src.trade_rules import adverse_exit_score, confidence_allowed, mtf_direction_agrees, scale_out_volume, should_exit_early, stop_only_tightens, stagnation_due, stop_target_from_atr, spread_within_median, may_extend


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


def test_early_exit_score_and_r_band():
    cfg={'early_exit_ema_fast':5,'early_exit_ema_slow':13,'early_exit_swing_lookback':5,
         'early_exit_rsi_period':14,'early_exit_roc_period':5,'early_exit_volume_lookback':20,
         'early_exit_volume_spike_ratio':1.5,'early_exit_weights':{'ema_cross':1,'swing_break':1,'momentum':1,'volume_spike':1},
         'early_exit_enabled':True,'early_exit_min_r':-.7,'early_exit_max_r':-.2,'early_exit_score_threshold':3}
    close=np.r_[np.arange(60,0,-1,dtype=float)]
    frame=pd.DataFrame({'open':close+0.2,'high':close+0.3,'low':close-0.3,'close':close,
                        'tick_volume':np.r_[np.full(59,10.),100.]})
    score,reasons=adverse_exit_score(frame,'buy',cfg)
    assert score>=3 and len(reasons)>=3
    assert should_exit_early(-.4,score,cfg)
    assert not should_exit_early(-.1,score,cfg)
    assert not should_exit_early(-.8,score,cfg)


def test_scale_out_respects_step_minimum_and_closes_all_if_unsplittable():
    assert scale_out_volume(.10,.01,.01,50)==(.05,False)
    assert scale_out_volume(.01,.01,.01,50)==(.01,True)


def test_trailing_stop_only_tightens_and_stagnation_rule():
    assert stop_only_tightens('buy',100,100.1)
    assert not stop_only_tightens('buy',100,99.9)
    assert stop_only_tightens('sell',100,99.9)
    assert not stop_only_tightens('sell',100,100.1)
    assert stagnation_due(4,.1,4,.2)
    assert not stagnation_due(3,.1,4,.2)
