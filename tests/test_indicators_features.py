import numpy as np
import pandas as pd
from src import indicators as ind
from src.features import build_features

def candles(close):
    close=pd.Series(close,dtype=float)
    return pd.DataFrame({'open':close,'high':close+1,'low':close-1,'close':close,'tick_volume':100,'spread':2})

def test_constant_series_sma_rsi_roc_and_atr():
    data=candles(np.full(80,10.0))
    assert ind.sma(data.close,10).iloc[-1]==10
    assert ind.rsi(data.close,14).iloc[-1]==50
    assert ind.roc(data.close,12).iloc[-1]==0
    assert ind.atr(data,14).iloc[-1]==2

def test_linear_trend_ema_and_adx_are_causal_and_directional():
    close=np.arange(1,121,dtype=float); data=candles(close)
    assert ind.ema(data.close,10).iloc[-1]>ind.ema(data.close,50).iloc[-1]
    result=ind.adx(data)
    assert result.plus_di.iloc[-1]>result.minus_di.iloc[-1]
    prefix=ind.ema(data.close.iloc[:80],10)
    changed=data.copy(); changed.loc[changed.index[80]:,'close']+=10000
    assert np.allclose(prefix.to_numpy(),ind.ema(changed.close.iloc[:80],10).to_numpy(),equal_nan=True)

def test_breakout_and_confirmed_swings_do_not_look_ahead():
    x=np.sin(np.arange(120)/4)+np.arange(120)*.05; data=candles(x)
    prefix=ind.breakout(data.iloc[:80],10); full=ind.breakout(data,10)
    assert prefix.iloc[-1].equals(full.iloc[79])
    swings_prefix=ind.swing_points(data.iloc[:80],3); swings_full=ind.swing_points(data,3)
    assert swings_prefix.iloc[-1].equals(swings_full.iloc[79])

def test_features_include_timeframes_and_a_known_trend_regime():
    close=np.arange(1,180,dtype=float)
    data=candles(close)
    values=build_features({'M15':data,'H1':data})
    assert values['market_regime']=='trending_up'
    assert {'adx','rsi','atr','bb_mid','support','resistance','macd_hist'}<=values['M15'].keys()
