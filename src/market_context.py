"""Cross-market context observations computed from closed bars."""
from __future__ import annotations
import numpy as np
import pandas as pd

USD_PAIRS=('EURUSD','GBPUSD','USDJPY','USDCHF','AUDUSD','USDCAD','NZDUSD')
INDEX_NAMES=('US30','US100','NAS100','SPX','GER40','UK100')

def _zchange(frame: pd.DataFrame|None) -> float|None:
    if frame is None or len(frame)<20 or 'close' not in frame: return None
    close=frame.close.iloc[:-1].astype(float); returns=close.pct_change().dropna()
    if len(returns)<10: return None
    std=float(returns.tail(96).std()); last=float(returns.iloc[-1])
    return last/std if std>0 and np.isfinite(std) else None

def build_market_context(candles: dict[str,dict[str,pd.DataFrame]], asset_groups: dict[str,str]|None=None) -> dict:
    """Aggregate USD, risk appetite, and per-asset-group directions once per scan."""
    changes={next((pair for pair in USD_PAIRS if name.upper().startswith(pair)),name):_zchange(frames.get('M15')) for name,frames in candles.items() if any(name.upper().startswith(pair) for pair in USD_PAIRS)}
    usd=[]
    for pair,value in changes.items():
        if value is None: continue
        usd.append(value if pair.startswith('USD') else -value)
    strength=float(np.mean(usd)) if usd else None
    group_values={}
    for symbol,frames in candles.items():
        value=_zchange(frames.get('M15'))
        if value is None: continue
        group=(asset_groups or {}).get(symbol,'other')
        group_values.setdefault(group,[]).append(value)
    group_direction={group:('bullish' if np.mean(values)>0 else 'bearish' if np.mean(values)<0 else 'neutral') for group,values in group_values.items()}
    risk_values=[]
    for symbol,frames in candles.items():
        value=_zchange(frames.get('M15'))
        if value is None: continue
        if any(token in symbol.upper() for token in INDEX_NAMES): risk_values.append(value)
        elif any(token in symbol.upper() for token in ('GOLD','XAUUSD')): risk_values.append(-value)
    risk_score=float(np.mean(risk_values)) if risk_values else None
    return {'usd_strength_m15_z':strength,'risk_on_off_score':risk_score,'group_direction':group_direction}

def context_for_signal(context: dict, symbol: str, direction: str, group: str) -> dict:
    """Describe alignment of a signal with currency and group context."""
    upper=symbol.upper(); side=1 if direction=='buy' else -1
    usd=float(context['usd_strength_m15_z']) if context.get('usd_strength_m15_z') is not None else None
    usd_exposure=side if upper.startswith('USD') else -side if upper.endswith('USD') else 0
    group_dir=context.get('group_direction',{}).get(group)
    return {'with_usd_context':None if usd is None or usd_exposure==0 else (usd*usd_exposure)>=0,
            'with_group_direction':None if group_dir in (None,'neutral') else (group_dir=='bullish')==(direction=='buy'),
            'risk_on_off_score':context.get('risk_on_off_score'),'group_direction':group_dir}
