"""Closed-bar candlestick observations on M1, M5, and M15."""
from __future__ import annotations
import pandas as pd
from ..indicators import candle_structure

def detect_candlestick_patterns(frame: pd.DataFrame, timeframe: str, tolerance: float=.001) -> list[dict]:
    """Return named candle patterns; the newest possibly-forming bar is ignored."""
    if frame is None or len(frame)<2: return []
    d=frame.iloc[:-1]
    if len(d)<2: return []
    i=len(d)-1; r=d.iloc[i]; p=d.iloc[i-1]
    o,h,l,c=map(float,(r.open,r.high,r.low,r.close)); po,ph,pl,pc=map(float,(p.open,p.high,p.low,p.close))
    rng=max(h-l,1e-12); body=abs(c-o); upper=h-max(o,c); lower=min(o,c)-l
    prior=float(d.close.iloc[max(0,i-5)])
    out=[]
    def add(name,direction): out.append({'name':name,'direction':direction,'timeframe':timeframe})
    if body/rng<=.1: add('doji','bullish' if c>=o else 'bearish')
    if lower/rng>=.6 and upper/rng<=.1: add('dragonfly_doji','bullish')
    if upper/rng>=.6 and lower/rng<=.1: add('gravestone_doji','bearish')
    if lower>=2*max(body,1e-12) and upper<=.6*max(body,1e-12): add('hammer' if c>=prior else 'hanging_man','bullish' if c>=prior else 'bearish')
    if upper>=2*max(body,1e-12) and lower<=.6*max(body,1e-12): add('inverted_hammer' if c<=prior else 'shooting_star','bullish' if c<=prior else 'bearish')
    shapes=candle_structure(d)
    if bool(shapes.bullish_engulfing.iloc[-1]): add('bullish_engulfing','bullish')
    if bool(shapes.bearish_engulfing.iloc[-1]): add('bearish_engulfing','bearish')
    if bool(shapes.inside_bar.iloc[-1]): add('inside_bar','bullish' if c>=o else 'bearish')
    if h>ph and l<pl: add('outside_bar','bullish' if c>=o else 'bearish')
    if len(d)>=3:
        a,b=d.iloc[-3],d.iloc[-2]; ao,ac,bo,bc=map(float,(a.open,a.close,b.open,b.close))
        if ac<ao and abs(bc-bo)<abs(ac-ao)*.5 and c>o and c>(ao+ac)/2: add('morning_star','bullish')
        if ac>ao and abs(bc-bo)<abs(ac-ao)*.5 and c<o and c<(ao+ac)/2: add('evening_star','bearish')
        if all(float(d.close.iloc[j])>float(d.open.iloc[j]) for j in (-3,-2,-1)) and all(float(d.close.iloc[j])>=float(d.high.iloc[j])-(float(d.high.iloc[j])-float(d.low.iloc[j]))*.25 for j in (-3,-2,-1)): add('three_white_soldiers','bullish')
        if all(float(d.close.iloc[j])<float(d.open.iloc[j]) for j in (-3,-2,-1)) and all(float(d.close.iloc[j])<=float(d.low.iloc[j])+(float(d.high.iloc[j])-float(d.low.iloc[j]))*.25 for j in (-3,-2,-1)): add('three_black_crows','bearish')
        if pc<po and c>o and c>(po+pc)/2 and c<po: add('piercing_line','bullish')
        if pc>po and c<o and c<(po+pc)/2 and c>po: add('dark_cloud_cover','bearish')
    near=max(rng,ph-pl)*max(0.0,float(tolerance))
    if abs(h-ph)<=near and c<o: add('tweezer_top','bearish')
    if abs(l-pl)<=near and c>o: add('tweezer_bottom','bullish')
    return out
