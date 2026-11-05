"""Shared safe helpers for candle-close strategy calculations."""
from __future__ import annotations
import numpy as np
import pandas as pd
from ..models import Signal
from .. import indicators as ind

def frame(candles,tf,minimum=30):
    value=candles.get(tf)
    return value if isinstance(value,pd.DataFrame) and len(value)>=minimum else None

def finite(*values): return all(value is not None and np.isfinite(value) for value in values)

def signal(symbol,direction,tf,entry,sl,tp,confidence,name,reason):
    if direction=='buy' and not sl<entry<tp: return None
    if direction=='sell' and not tp<entry<sl: return None
    return Signal(symbol,direction,tf,float(entry),float(sl),float(tp),float(np.clip(confidence,0,1)),name,reason)

def latest(candles,period=14):
    f=ind.adx(candles,period); b=ind.bollinger(candles.close); a=ind.atr(candles,period); r=ind.rsi(candles.close,period)
    return {'atr':a.iloc[-1],'rsi':r.iloc[-1],'adx':f.adx.iloc[-1],'plus_di':f.plus_di.iloc[-1],'minus_di':f.minus_di.iloc[-1],'bb_lower':b.bb_lower.iloc[-1],'bb_mid':b.bb_mid.iloc[-1],'bb_upper':b.bb_upper.iloc[-1]}
