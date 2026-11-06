"""Heuristic chart pattern observations using closed OHLC bars only."""
from __future__ import annotations
import numpy as np
import pandas as pd
from ..indicators import atr

def _pivots(frame: pd.DataFrame, window: int=2):
    hi=frame.high.to_numpy(float); lo=frame.low.to_numpy(float); points=[]
    for i in range(window,len(frame)-window):
        if hi[i]>=max(hi[i-window:i+window+1]): points.append((i,'H',hi[i]))
        if lo[i]<=min(lo[i-window:i+window+1]): points.append((i,'L',lo[i]))
    return sorted(points)

def detect_chart_patterns(frame: pd.DataFrame, timeframe: str, tolerance: float=.015, swing_window: int=2) -> list[dict]:
    """Detect approximate structures; distances are measured in current ATRs."""
    if frame is None or len(frame)<30: return []
    data=frame.iloc[:-1]  # newest row may still be forming
    if len(data)<30: return []
    atr_now=float(atr(data).iloc[-1]); price=float(data.close.iloc[-1])
    if not np.isfinite(atr_now) or atr_now<=0: return []
    piv=_pivots(data,swing_window); out=[]
    def add(name,direction,level,state='forming'):
        out.append({'name':name,'direction':direction,'timeframe':timeframe,'state':state,
                    'breakout_level':float(level),'distance_atr':float((float(level)-price)/atr_now)})
    recent=piv[-12:]
    highs=[p for p in recent if p[1]=='H']; lows=[p for p in recent if p[1]=='L']
    if len(highs)>=2:
        a,b=highs[-2:]; tol=max(abs(a[2]),abs(b[2]))*tolerance
        if abs(a[2]-b[2])<=tol:
            trough=[p[2] for p in lows if a[0]<p[0]<b[0]]
            if trough: add('double_top','bearish',min(trough), 'confirmed breakout' if price<min(trough) else 'forming')
    if len(lows)>=2:
        a,b=lows[-2:]; tol=max(abs(a[2]),abs(b[2]))*tolerance
        if abs(a[2]-b[2])<=tol:
            peak=[p[2] for p in highs if a[0]<p[0]<b[0]]
            if peak: add('double_bottom','bullish',max(peak), 'confirmed breakout' if price>max(peak) else 'forming')
    # Head-and-shoulders and inverse variants use five alternating pivots.
    for seq,name,direction,kind in ((recent[-5:],'head_shoulders','bearish','H'),(recent[-5:],'inverse_head_shoulders','bullish','L')):
        if len(seq)==5 and ''.join(p[1] for p in seq)==(kind+('L' if kind=='H' else 'H')+kind+('L' if kind=='H' else 'H')+kind):
            x,y,z=seq[0],seq[2],seq[4]; tol=max(abs(x[2]),abs(z[2]))*tolerance
            if abs(x[2]-z[2])<=tol and ((kind=='H' and y[2]>x[2]) or (kind=='L' and y[2]<x[2])):
                neckline=float((seq[1][2]+seq[3][2])/2); add(name,direction,neckline,'confirmed breakout' if (price<neckline if direction=='bearish' else price>neckline) else 'forming')
    # Three-point regression detects converging and parallel boundaries.
    if len(highs)>=3 and len(lows)>=3:
        hs=highs[-3:]; ls=lows[-3:]
        sh=np.polyfit([p[0] for p in hs],[p[2] for p in hs],1)[0]; sl=np.polyfit([p[0] for p in ls],[p[2] for p in ls],1)[0]
        width0=hs[0][2]-ls[0][2]; width1=hs[-1][2]-ls[-1][2]
        if width0>0 and width1<width0*.8:
            if sh<0<sl: add('symmetrical_triangle','bullish',hs[-1][2])
            elif sh<0 and sl<0: add('descending_triangle','bearish',ls[-1][2])
            elif sh>0 and sl>0: add('rising_wedge','bearish',ls[-1][2])
            elif sh<0 and sl>0: add('falling_wedge','bullish',hs[-1][2])
        elif abs(sh)<atr_now/len(data)*.3 and sl>0: add('ascending_triangle','bullish',hs[-1][2])
        elif abs(sl)<atr_now/len(data)*.3 and sh<0: add('descending_triangle','bearish',ls[-1][2])
        elif abs(sh-sl)<atr_now/len(data)*.3: add('rectangle','bullish' if price>(hs[-1][2]+ls[-1][2])/2 else 'bearish',hs[-1][2])
        # Impulse followed by a tight ten-bar consolidation: flag/pennant.
        if len(data)>=30:
            impulse=float(data.close.iloc[-11]-data.close.iloc[-21]); consolidation=float(data.high.iloc[-10:].max()-data.low.iloc[-10:].min())
            if abs(impulse)>atr_now*3 and consolidation<abs(impulse)*.55:
                add('pennant' if abs(sh-sl)>atr_now/len(data)*.3 else 'flag','bullish' if impulse>0 else 'bearish',price)
    return out
