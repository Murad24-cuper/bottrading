import numpy as np
import pandas as pd
from src.market_context import build_market_context,context_for_signal

def _bars(change):
    close=100*np.cumprod(1+np.r_[np.full(39,.0001),change])
    return pd.DataFrame({'open':close,'high':close*1.001,'low':close*.999,'close':close,'tick_volume':1})

def test_context_uses_closed_m15_bars_and_maps_signal_alignment():
    candles={'EURUSD':{'M15':_bars(.002)},'USDJPY':{'M15':_bars(-.001)},'US30':{'M15':_bars(.001)},'GOLD':{'M15':_bars(-.001)}}
    context=build_market_context(candles,{'US30':'indices','GOLD':'metals'})
    assert context['usd_strength_m15_z'] is not None
    assert context['risk_on_off_score'] is not None
    assert context['group_direction']['indices']=='bullish'
    assert context_for_signal(context,'EURUSD','buy','forex')['with_usd_context'] is True

def test_context_ignores_forming_bar():
    frame=_bars(.001); expected=build_market_context({'EURUSD':{'M15':frame}})
    frame.loc[len(frame)-1,'close']=1e9
    assert build_market_context({'EURUSD':{'M15':frame}})==expected
