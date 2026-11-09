"""Future perturbation tests for the feature primitives used by strategies/brain."""
import numpy as np
import pandas as pd
import pandas.testing as pdt

from src import indicators as ind
from src.features import build_features


def _bars(n=900):
    rng=np.random.default_rng(41)
    close=100+np.cumsum(rng.normal(0,.2,n))
    return pd.DataFrame({'open':close+rng.normal(0,.04,n),'high':close+.2,
                         'low':close-.2,'close':close,
                         'tick_volume':rng.integers(10,100,n)},
                        index=pd.date_range('2026-01-01',periods=n,freq='min',tz='UTC'))


def _indicators(frame):
    return {'ema':ind.ema(frame.close,20),'atr':ind.atr(frame),'adx':ind.adx(frame),
            'rsi':ind.rsi(frame.close),'roc':ind.roc(frame.close),
            'macd':ind.macd(frame.close),'bands':ind.bollinger(frame.close),
            'levels':ind.nearest_levels(frame),'breakout':ind.breakout(frame),
            'candles':ind.candle_structure(frame),'volume':ind.relative_tick_volume(frame)}


def _at(value, pos):
    if isinstance(value,pd.DataFrame): return value.iloc[pos]
    return value.iloc[pos]


def test_indicators_and_brain_features_ignore_bars_after_sample_time():
    frame=_bars()
    for pos in (150,333,700):
        changed=frame.copy()
        future=changed.index>changed.index[pos]
        changed.loc[future,['open','high','low','close']]=1_000_000
        changed.loc[future,'tick_volume']=10**9
        original=_indicators(frame); perturbed=_indicators(changed)
        for name in original:
            left,right=_at(original[name],pos),_at(perturbed[name],pos)
            if isinstance(left,pd.Series): pdt.assert_series_equal(left,right,check_names=False)
            else: assert left==right or (pd.isna(left) and pd.isna(right)), (pos,name,left,right)
        # The brain's current feature vector is built from these causal series.
        assert build_features({'M15':frame.iloc[:pos+1]})==build_features({'M15':changed.iloc[:pos+1]})
