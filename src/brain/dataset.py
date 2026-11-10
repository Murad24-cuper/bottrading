"""Causal triple-barrier samples built from local MT5 history Parquets."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
import numpy as np
import pandas as pd

from .memory import situation_vector
from .training import label_trade, split_name
from .. import parquet_compat


def _as_utc_index(frame: pd.DataFrame) -> pd.DataFrame:
    result=frame.sort_index().copy()
    index=pd.DatetimeIndex(result.index)
    result.index=index.tz_localize('UTC') if index.tz is None else index.tz_convert('UTC')
    return result


def _context(m5: pd.DataFrame, m15: pd.DataFrame) -> dict:
    """Calculate scale-free context from bars already closed at the sample time."""
    def scaled(frame, bars):
        close=frame.close.astype(float)
        atr=float((frame.high.astype(float)-frame.low.astype(float)).tail(14).mean())
        price=float(close.iloc[-1])
        if not np.isfinite(atr) or atr<=0 or price<=0: return 0.0
        return float(np.clip((price-float(close.iloc[-bars-1]))/atr,-5,5)) if len(close)>bars else 0.0
    return {'trend':scaled(m15,8),'momentum':scaled(m5,5),
            'volatility':float(np.clip((m15.high-m15.low).tail(14).mean()/max(float(m15.close.iloc[-1]),1e-12)*10000,0,5)),
            'support_distance_atr':0.0,'resistance_distance_atr':0.0,
            'minutes_to_next_event':None}


def build_labeled_outcomes(history_dir: str|Path, symbols: list[str], specs: dict,
                           split: dict, config: dict, sample_minutes: int=30) -> pd.DataFrame:
    """Label both directions at every available sampled timestamp without feature lookahead."""
    history=Path(history_dir); rows=[]
    focus=set(config['universe'].get('focus_symbols',[]))
    weekend_symbols=set(config['universe'].get('weekend_symbols',[]))
    aliases=config['universe'].get('symbol_aliases',{})
    logical_for_actual: dict[str, str] = {}
    for logical in (*focus,*weekend_symbols):
        for pattern in aliases.get(logical,[logical]):
            logical_for_actual.setdefault(str(pattern).upper(),logical)
    weekend_actual=set()
    for symbol in symbols:
        actual=symbol.upper()
        if any(pattern in actual for name in weekend_symbols for pattern in aliases.get(name,[name])):
            weekend_actual.add(symbol)
    risk=config['risk']; backtest=config.get('backtest',{})
    forex_path=history/'EURUSD_M1.parquet'
    forex_index=None
    if forex_path.is_file():
        forex_frame=_as_utc_index(parquet_compat.read_parquet(forex_path,columns=['close']))
        forex_index=forex_frame.index
    def forex_open_at(stamp):
        if stamp.weekday()<5: return True
        if forex_index is None: return False
        pos=int(forex_index.searchsorted(stamp,side='right'))-1
        return pos>=0 and stamp-forex_index[pos]<=pd.Timedelta(minutes=2)
    for symbol in symbols:
        paths={tf:history/f'{symbol}_{tf}.parquet' for tf in ('M1','M5','M15')}
        if not all(path.is_file() for path in paths.values()): continue
        frames={tf:_as_utc_index(parquet_compat.read_parquet(path)) for tf,path in paths.items()}
        m1,m5,m15=frames['M1'],frames['M5'],frames['M15']
        spec=specs.get(symbol,{})
        group=str(spec.get('asset_group','other'))
        weekend=symbol in weekend_actual
        target_horizon=int(config.get('weekend',{}).get('move_horizon_minutes',60) if weekend else risk.get('move_horizon_minutes',10))
        timeout=int(config.get('weekend',{}).get('max_hold_extended_minutes',120) if weekend else risk.get('max_hold_extended_minutes',risk.get('max_hold_minutes',20)))
        atr=(m1['high'].astype(float)-m1['low'].astype(float)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
        sample_ids=np.flatnonzero((m1.index.minute.to_numpy()%sample_minutes)==0)
        for decision_idx in sample_ids:
            entry_index=int(decision_idx)-1
            if entry_index<1 or entry_index+timeout>=len(m1): continue
            stamp=m1.index[decision_idx]
            active_weekend=stamp.weekday()>=5 and not forex_open_at(stamp)
            if weekend_actual and symbol in weekend_actual and not active_weekend: continue
            if symbol not in weekend_actual and active_weekend: continue
            # Use only completed M5/M15 bars whose close time is no later than the decision time.
            i5=int(m5.index.searchsorted(stamp-pd.Timedelta(minutes=5),side='right'))-1
            i15=int(m15.index.searchsorted(stamp-pd.Timedelta(minutes=15),side='right'))-1
            if i5<49 or i15<33: continue
            sample_m5=m5.iloc[:i5+1]; sample_m15=m15.iloc[:i15+1]
            context=_context(sample_m5,sample_m15)
            for direction in ('buy','sell'):
                vector=situation_vector({'M5':sample_m5,'M15':sample_m15},context,direction)
                atr_value=float(atr.iloc[entry_index])
                if not np.isfinite(atr_value) or atr_value<=0: continue
                label=label_trade(m1,entry_index,direction,atr_value,spec,
                    horizon_minutes=target_horizon,sl_mult=float(risk['sl_move_mult']),
                    tp_mult=float(risk['tp_move_mult']),slippage_points=float(backtest.get('slippage_points',0)),
                    timeout_minutes=timeout,
                    commission_per_lot_per_side=float(backtest.get('commission_per_lot_per_side',0)))
                if label is None: continue
                rows.append({'time':stamp.isoformat(),'symbol':symbol,'asset_group':group,
                    'weekend':weekend,'direction':direction,'vector':vector.tolist(),
                    'win':int(label['win']),'net_r':float(label['net_r']),'reason':label['reason'],
                    'entry':float(label['entry']),'exit':float(label['exit']),
                    'risk_distance':float(label['risk_distance']),'cost_distance':float(label['cost_distance']),
                    'split':split_name(stamp.to_pydatetime(),split)})
    return pd.DataFrame(rows)
