"""Small, causal nearest-situation memory helpers (NumPy only)."""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
import numpy as np

def situation_vector(candles: dict, context: dict | None=None) -> np.ndarray:
    """Encode recent closed-bar returns and context without using future rows."""
    values=[]
    for timeframe,count in (('M5',48),('M15',32)):
        frame=candles.get(timeframe)
        if frame is None or len(frame)<count+1:
            values.extend([0.0]*count); continue
        close=frame['close'].astype(float).iloc[-count-1:]
        returns=np.diff(np.log(np.maximum(close.to_numpy(),1e-12)))
        atr=float(frame['high'].astype(float).sub(frame['low'].astype(float)).tail(14).mean())
        price=float(close.iloc[-1]); scale=max(atr/max(price,1e-12),1e-8)
        values.extend(np.clip(returns/scale,-5,5).tolist())
    context=context or {}
    for key in ('checklist_score','trend','momentum','volatility','support_distance_atr','resistance_distance_atr','usd_strength','risk_on'):
        raw=context.get(key,0.0)
        try: value=float(raw)
        except (TypeError,ValueError): value=0.0
        values.append(float(np.clip(value,-5,5)) if np.isfinite(value) else 0.0)
    return np.asarray(values,dtype=np.float32)

def fit_pca(training_vectors: np.ndarray, components: int=28) -> dict:
    """Fit a compact PCA transform using only the supplied training rows."""
    data=np.asarray(training_vectors,dtype=np.float64)
    if data.ndim!=2 or not len(data): raise ValueError('training_vectors must be a non-empty 2D array')
    mean=data.mean(axis=0); centered=data-mean
    _,_,vectors=np.linalg.svd(centered,full_matrices=False)
    count=max(1,min(int(components),vectors.shape[0],data.shape[1]))
    return {'mean':mean.astype(np.float32),'components':vectors[:count].astype(np.float32)}

def apply_pca(vectors: np.ndarray, model: dict) -> np.ndarray:
    data=np.asarray(vectors,dtype=np.float32)
    return (data-np.asarray(model['mean'],dtype=np.float32))@np.asarray(model['components'],dtype=np.float32).T

def query_memory(vector, rows: list[dict], query_time: datetime, symbol: str,
                 k: int=300, exclude_same_symbol_days: int=1) -> dict:
    """Query only strictly earlier examples and optionally purge nearby same-symbol rows."""
    query_time=query_time.replace(tzinfo=timezone.utc) if query_time.tzinfo is None else query_time.astimezone(timezone.utc)
    query=np.asarray(vector,dtype=np.float32); candidates=[]; purge=timedelta(days=int(exclude_same_symbol_days))
    for row in rows:
        stamp=datetime.fromisoformat(str(row['time']).replace('Z','+00:00'))
        stamp=stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)
        if stamp>=query_time: continue
        if row.get('symbol')==symbol and query_time-stamp<=purge: continue
        sample=np.asarray(row['vector'],dtype=np.float32)
        if sample.shape!=query.shape: continue
        distance=float(np.linalg.norm(sample-query))
        candidates.append((distance,row,stamp))
    candidates.sort(key=lambda item:item[0]); nearest=candidates[:max(1,int(k))]
    if not nearest: return {'count':0,'probability':None,'avg_win_r':0.0,'avg_loss_r':0.0,'cases':[],'mean_distance':None}
    weights=np.asarray([1/max(distance,1e-6) for distance,_,_ in nearest]); wins=np.asarray([float(row.get('win',0)) for _,row,_ in nearest]); net=np.asarray([float(row.get('net_r',0)) for _,row,_ in nearest])
    base=float(np.mean(wins)); effective=float(weights.sum()**2/max(np.sum(weights**2),1e-12)); shrink=min(1.0,effective/50.0)
    probability=shrink*float(np.average(wins,weights=weights))+(1-shrink)*base
    win_r=net[net>0]; loss_r=-net[net<0]
    cases=[{'symbol':row.get('symbol'),'time':stamp.isoformat(),'distance':distance} for distance,row,stamp in nearest[:3]]
    return {'count':len(nearest),'probability':probability,'avg_win_r':float(np.mean(win_r)) if len(win_r) else 0.0,'avg_loss_r':float(np.mean(loss_r)) if len(loss_r) else 0.0,'cases':cases,'mean_distance':float(np.mean([x[0] for x in nearest]))}
