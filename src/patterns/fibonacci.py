"""Fibonacci retracement observations on closed bars."""
from __future__ import annotations
import numpy as np
import pandas as pd
from ..indicators import atr

RATIOS=(.236,.382,.5,.618,.786)

def fibonacci_retracement(frame: pd.DataFrame, timeframe: str, lookback: int=100) -> dict:
    """Measure price distance to retracements of the latest closed swing."""
    if frame is None or len(frame)<10: return {'timeframe':timeframe,'levels':[],'nearest':None,'reacting':False}
    d=frame.iloc[:-1].tail(max(10,int(lookback)))
    if len(d)<10: return {'timeframe':timeframe,'levels':[],'nearest':None,'reacting':False}
    hi_i=d.high.idxmax(); lo_i=d.low.idxmin(); hi=float(d.loc[hi_i,'high']); lo=float(d.loc[lo_i,'low'])
    if hi<=lo: return {'timeframe':timeframe,'levels':[],'nearest':None,'reacting':False}
    up=hi_i>lo_i; span=hi-lo
    price=float(d.close.iloc[-1]); a=float(atr(d).iloc[-1]); last=d.iloc[-1]
    levels=[]
    for ratio in RATIOS:
        value=hi-span*ratio if up else lo+span*ratio
        levels.append({'ratio':ratio,'price':float(value),'distance_atr':float(abs(price-value)/a) if a>0 else None})
    nearest=min(levels,key=lambda x:x['distance_atr'] if x['distance_atr'] is not None else float('inf'))
    touched=[level for level in levels if float(last.low)<=level['price']<=float(last.high)]
    rejection=bool(touched and ((up and float(last.close)>float(last.open)) or (not up and float(last.close)<float(last.open))))
    return {'timeframe':timeframe,'swing_direction':'up' if up else 'down','levels':levels,'nearest':nearest,'reacting':rejection,'reaction_level':min(touched,key=lambda x:x['distance_atr'] if x['distance_atr'] is not None else float('inf')) if rejection else None}
