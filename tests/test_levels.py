import numpy as np
import pandas as pd
from src.levels import key_levels

def test_key_levels_have_daily_weekly_pivots_and_nearby_distances():
    index=pd.date_range('2026-10-19',periods=30*24,freq='h',tz='UTC'); close=100+np.sin(np.arange(len(index))/12)
    frame=pd.DataFrame({'open':close,'high':close+.5,'low':close-.5,'close':close,'tick_volume':1},index=index)
    result=key_levels(frame,tp=float(close[-2]+5),sl=float(close[-2]-.1))
    names={x['name'] for x in result['levels']}
    assert {'previous_day_high','previous_day_low','previous_day_close','current_day_open','pivot','R1','S1','R2','S2','R3','S3','previous_week_high','previous_week_low'}<=names
    assert result['above']['distance_atr']>=0 and result['below']['distance_atr']>=0

def test_key_levels_ignore_forming_bar():
    index=pd.date_range('2026-10-19',periods=100,freq='h',tz='UTC'); close=np.linspace(99,101,100)
    frame=pd.DataFrame({'open':close,'high':close+.1,'low':close-.1,'close':close,'tick_volume':1},index=index)
    expected=key_levels(frame); frame.iloc[-1,frame.columns.get_loc('high')]=1e9
    assert key_levels(frame)==expected

def test_key_levels_flags_stop_just_beyond_a_strong_level():
    index=pd.date_range('2026-10-19',periods=100,freq='h',tz='UTC'); close=np.linspace(99,101,100)
    frame=pd.DataFrame({'open':close,'high':close+.1,'low':close-.1,'close':close,'tick_volume':1},index=index)
    base=key_levels(frame); price=float(frame.close.iloc[-2])
    support=max(x['price'] for x in base['levels'] if x['strong'] and x['price']<price)
    assert key_levels(frame,sl=support-.001)['sl_near_level'] is True
