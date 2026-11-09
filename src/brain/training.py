"""Causal labels and chronological splits for offline brain experiments."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import numpy as np


def chronological_splits(times, train_fraction=.60, validation_fraction=.20, purge_minutes=120):
    """Split unique timestamps chronologically with a max-hold purge between sets."""
    values=sorted({np.datetime64(value.replace(tzinfo=None) if value.tzinfo else value,'ns') for value in times})
    if len(values)<5: raise ValueError('At least five distinct timestamps are required')
    train_end=max(1,int(len(values)*float(train_fraction)))-1
    valid_end=max(train_end+1,int(len(values)*(float(train_fraction)+float(validation_fraction)))-1)
    purge=np.timedelta64(max(0,int(purge_minutes)),'m')
    train_cut=values[train_end]; valid_start=train_cut+purge
    valid_cut=values[valid_end]; test_start=valid_cut+purge
    return {'train_end':str(train_cut),'validation_start':str(valid_start),'validation_end':str(valid_cut),'test_start':str(test_start),'purge_minutes':int(purge_minutes)}


def split_name(timestamp,split):
    """Classify one timestamp under a previously frozen split map."""
    stamp=np.datetime64(timestamp.replace(tzinfo=None) if timestamp.tzinfo else timestamp,'ns')
    if stamp<=np.datetime64(split['train_end']): return 'train'
    if np.datetime64(split['validation_start'])<=stamp<=np.datetime64(split['validation_end']): return 'validation'
    if stamp>=np.datetime64(split['test_start']): return 'test'
    return 'purged'


def label_trade(frame,entry_index,direction,atr,spec,horizon_minutes=20,sl_mult=.8,tp_mult=1.2,slippage_points=1.0,timeout_minutes=None,commission_per_lot_per_side=0.0):
    """Label a causal triple-barrier trade with spread, slippage, and commission."""
    if direction not in {'buy','sell'} or atr<=0 or entry_index<0 or entry_index+1>=len(frame): return None
    point=float(spec.get('point_size',spec.get('point',spec.get('trade_tick_size',1e-5))) or 1e-5)
    tick_size=float(spec.get('trade_tick_size',spec.get('tick_size',point)) or point)
    spread_points=float(frame['spread'].iloc[entry_index+1]) if 'spread' in frame else 0.0
    spread=max(0.0,spread_points)*point; slip=max(0.0,float(slippage_points))*point
    entry_bar=frame.iloc[entry_index+1]; entry=float(entry_bar.open)+(spread if direction=='buy' else 0.0)+slip*(1 if direction=='buy' else -1)
    risk=float(atr)*np.sqrt(max(1.0,float(horizon_minutes)))*float(sl_mult)
    reward=float(atr)*np.sqrt(max(1.0,float(horizon_minutes)))*float(tp_mult)+spread
    if risk<=0 or tick_size<=0: return None
    stop=entry-risk if direction=='buy' else entry+risk; target=entry+reward if direction=='buy' else entry-reward
    timeout=int(max(1,timeout_minutes if timeout_minutes is not None else horizon_minutes))
    first_future=entry_index+1
    if hasattr(frame.index,'__getitem__') and first_future<len(frame):
        try:
            from pandas import DatetimeIndex,Timestamp
            if isinstance(frame.index,DatetimeIndex):
                opened=frame.index[first_future]
                deadline=opened+__import__('pandas').Timedelta(minutes=timeout)
                stop_index=int(frame.index.searchsorted(deadline,side='right'))
                future_indices=range(first_future,max(first_future,min(stop_index,len(frame))))
            else: future_indices=range(first_future,min(len(frame),entry_index+timeout+1))
        except (TypeError,ValueError): future_indices=range(first_future,min(len(frame),entry_index+timeout+1))
    else: future_indices=range(first_future,min(len(frame),entry_index+timeout+1))
    if not future_indices: return None
    last=frame.iloc[future_indices[-1]]
    exit_price=float(last.close); reason='time'
    for idx in future_indices:
        bar=frame.iloc[idx]
        sl_hit=float(bar.low)<=stop if direction=='buy' else float(bar.high)+spread>=stop
        tp_hit=float(bar.high)>=target if direction=='buy' else float(bar.low)+spread<=target
        if sl_hit:
            exit_price=stop; reason='sl'; break
        if tp_hit:
            exit_price=target; reason='tp'; break
        last=bar
    if reason=='time': exit_price=float(last.close)+(spread if direction=='sell' else 0.0)
    exit_price-=slip if direction=='buy' else -slip
    net_distance=(exit_price-entry) if direction=='buy' else (entry-exit_price)
    cost_distance=2*slip
    commission=float(commission_per_lot_per_side)
    tick_value=float(spec.get('trade_tick_value_loss',spec.get('trade_tick_value',spec.get('tick_value',0))) or 0)
    if commission<0 or (commission and (tick_value<=0 or tick_size<=0)): return None
    money_per_price=tick_value/tick_size
    commission_distance=(2*commission/money_per_price) if commission else 0.0
    net_distance-=commission_distance
    net_r=net_distance/risk
    return {'win':bool(net_r>0),'net_r':float(net_r),'reason':reason,'entry':entry,'exit':exit_price,'risk_distance':risk,'cost_distance':float(cost_distance+commission_distance)}


def fit_probability_calibration(probabilities,labels,bins=10):
    """Build a monotone bin map using validation predictions only."""
    probabilities=np.asarray(probabilities,dtype=float); labels=np.asarray(labels,dtype=float)
    if probabilities.shape!=labels.shape: raise ValueError('probabilities and labels must have the same shape')
    edges=np.linspace(0,1,int(bins)+1); values=[]
    for low,high in zip(edges[:-1],edges[1:]):
        mask=(probabilities>=low)&((probabilities<high) if high<1 else (probabilities<=high))
        values.append(float(labels[mask].mean()) if mask.any() else float((low+high)/2))
    return {'edges':edges.tolist(),'values':np.maximum.accumulate(np.clip(values,0,1)).tolist()}


def calibrate_probability(probability,calibration):
    edges=np.asarray(calibration['edges'],dtype=float); values=np.asarray(calibration['values'],dtype=float)
    index=int(np.clip(np.searchsorted(edges,float(probability),side='right')-1,0,len(values)-1))
    return float(values[index])
