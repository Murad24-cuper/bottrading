from datetime import datetime,timezone,timedelta
import numpy as np
import pandas as pd

from src.brain.training import chronological_splits,split_name,label_trade,fit_probability_calibration,calibrate_probability


def test_splits_are_chronological_and_purge_between_periods():
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    times=[start+timedelta(hours=i) for i in range(100)]
    splits=chronological_splits(times,purge_minutes=20)
    assert splits['train_end']<splits['validation_start']<=splits['validation_end']<splits['test_start']
    assert splits['purge_minutes']==20
    assert split_name(start+timedelta(hours=10),splits)=='train'
    assert split_name(start+timedelta(hours=99),splits)=='test'


def test_label_trade_uses_next_bar_and_stop_first_when_both_hit():
    frame=pd.DataFrame({'open':[100,100],'high':[101,110],'low':[99,90],'close':[100,105],'spread':[0,0]})
    label=label_trade(frame,0,'buy',1,{'point_size':.01,'trade_tick_size':.01},horizon_minutes=1,sl_mult=1,tp_mult=1,slippage_points=0)
    assert label['reason']=='sl' and label['net_r']<0 and label['win'] is False

def test_label_trade_uses_separate_time_barrier_and_commission_cost():
    frame=pd.DataFrame({'open':[100,100,100,100],'high':[101,101,101,101],'low':[99.5,99.5,99.5,99.5],'close':[100,100.5,101,100.5],'spread':[0,0,0,0]})
    spec={'point_size':.01,'trade_tick_size':.01,'trade_tick_value':1}
    label=label_trade(frame,0,'buy',1,spec,horizon_minutes=1,sl_mult=1,tp_mult=10,slippage_points=0,timeout_minutes=3,commission_per_lot_per_side=.01)
    assert label['reason']=='time'
    assert label['net_r'] < .5


def test_validation_calibration_is_reused_as_bin_lookup():
    probs=[.1,.2,.8,.9]; labels=[0,0,1,1]
    calibration=fit_probability_calibration(probs,labels,bins=2)
    assert calibrate_probability(.8,calibration)==1
    assert calibrate_probability(.2,calibration)==0
