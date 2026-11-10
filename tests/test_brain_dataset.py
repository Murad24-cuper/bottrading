from datetime import datetime,timezone
import numpy as np
import pandas as pd

from src.brain.dataset import build_labeled_outcomes
from src.brain.training import chronological_splits


def bars(index):
    x=np.arange(len(index),dtype=float)
    return pd.DataFrame({'open':100+x*.01,'high':100.2+x*.01,'low':99.8+x*.01,
                         'close':100.1+x*.01,'tick_volume':100,'spread':1},index=index)


def test_labeled_dataset_is_causal_and_contains_both_directions(tmp_path):
    m1_index=pd.date_range('2026-01-01',periods=24*60,freq='min',tz='UTC')
    m1=bars(m1_index); m5=bars(m1_index[::5]); m15=bars(m1_index[::15])
    from src.parquet_compat import write_parquet
    for tf,frame in [('M1',m1),('M5',m5),('M15',m15)]: write_parquet(frame,tmp_path/f'EURUSD_{tf}.parquet')
    times=[stamp.to_pydatetime() for stamp in m1_index[::30]]
    split=chronological_splits(times,purge_minutes=120)
    config={'universe':{'focus_symbols':['EURUSD'],'weekend_symbols':[],'symbol_aliases':{'EURUSD':['EURUSD']}},
            'risk':{'move_horizon_minutes':10,'max_hold_minutes':20,'max_hold_extended_minutes':60,'sl_move_mult':.8,'tp_move_mult':1.2},
            'backtest':{'slippage_points':0,'commission_per_lot_per_side':0},'weekend':{},'brain':{}}
    result=build_labeled_outcomes(tmp_path,['EURUSD'],{'EURUSD':{'asset_group':'forex','point_size':.01,'trade_tick_size':.01,'trade_tick_value':1}},split,config,30)
    assert len(result)>20
    assert set(result.direction)=={'buy','sell'}
    assert result.groupby(['time','direction']).size().max()==1
    assert set(result.split).issubset({'train','validation','test','purged'})
    assert all(len(vector)==90 for vector in result.vector)
