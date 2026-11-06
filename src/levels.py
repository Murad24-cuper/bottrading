"""Daily/weekly, pivot, and round-number context from closed price bars."""
from __future__ import annotations
import pandas as pd
from .indicators import atr

def key_levels(frame: pd.DataFrame, tp: float|None=None, sl: float|None=None, round_step: float|None=None) -> dict:
    """Return nearby levels; timestamps in the frame are expected to be UTC."""
    if frame is None or len(frame)<3: return {'levels':[],'above':None,'below':None,'tp_blocked':False,'sl_near_level':False}
    d=frame.iloc[:-1].copy()
    if not isinstance(d.index,pd.DatetimeIndex): return {'levels':[],'above':None,'below':None,'tp_blocked':False,'sl_near_level':False}
    idx=d.index
    if idx.tz is None: idx=idx.tz_localize('UTC')
    else: idx=idx.tz_convert('UTC')
    d.index=idx; now=idx[-1]; today=d[d.index.date==now.date()]; prev=d[d.index.date<(now.date())]
    levels=[]
    def put(name,value,strong=True):
        if pd.notna(value): levels.append({'name':name,'price':float(value),'strong':bool(strong)})
    if not today.empty: put('current_day_open',today.open.iloc[0])
    if not prev.empty:
        day=prev[prev.index.date==prev.index.date[-1]]
        dh=float(day.high.max()); dl=float(day.low.min()); dc=float(day.close.iloc[-1])
        put('previous_day_high',dh); put('previous_day_low',dl); put('previous_day_close',dc)
        p=(dh+dl+dc)/3; put('pivot',p); put('R1',2*p-dl); put('S1',2*p-dh); put('R2',p+(dh-dl)); put('S2',p-(dh-dl)); put('R3',dh+2*(p-dl)); put('S3',dl-2*(dh-p))
        iso=prev.index.isocalendar(); current_key=(now.isocalendar().year,now.isocalendar().week)
        keys={(int(y),int(w)) for y,w in zip(iso.year,iso.week) if (int(y),int(w))<current_key}
        if keys:
            py,pw=max(keys); week=prev[(iso.year==py)&(iso.week==pw)]
            put('previous_week_high',week.high.max()); put('previous_week_low',week.low.min())
    price=float(d.close.iloc[-1]); step=float(round_step or (100 if price>=10000 else 10 if price>=1000 else 1 if price>=100 else .1 if price>=10 else .01 if price>=1 else .0001))
    if step>0:
        put('round_number_below',price//step*step,False); put('round_number_above',(price//step+1)*step,False)
    a=float(atr(d).iloc[-1]); above=min((x for x in levels if x['price']>price),key=lambda x:x['price'],default=None); below=max((x for x in levels if x['price']<price),key=lambda x:x['price'],default=None)
    for item in (above,below):
        if item is not None: item['distance_atr']=abs(item['price']-price)/a if a>0 else None
    near=max(a*.15,0.0)
    blocked=bool(tp is not None and any(x['strong'] and price<x['price']<=float(tp) for x in levels) or tp is not None and any(x['strong'] and float(tp)<=x['price']<price for x in levels))
    sl_near=bool(sl is not None and any(x['strong'] and abs(float(sl)-x['price'])<=near for x in levels))
    return {'levels':levels,'above':above,'below':below,'tp_blocked':blocked,'sl_near_level':sl_near,'atr':a}
