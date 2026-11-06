from datetime import datetime,timezone
import numpy as np
import pandas as pd
from src.sessions import session_context

def test_session_context_names_and_elapsed_minutes_use_utc():
    result=session_context(None,datetime(2026,11,6,14,30,tzinfo=timezone.utc))
    assert result['session']=='London-NY overlap' and result['minutes_since_open']==150

def test_session_context_range_uses_closed_bars_only():
    idx=pd.date_range('2026-11-06 07:00',periods=40,freq='15min',tz='UTC'); close=np.arange(40,dtype=float)
    frame=pd.DataFrame({'open':close,'high':close+1,'low':close-1,'close':close,'tick_volume':1},index=idx)
    expected=session_context(frame,datetime(2026,11,6,14,30,tzinfo=timezone.utc))
    frame.iloc[-1,frame.columns.get_loc('high')]=1e9
    assert session_context(frame,datetime(2026,11,6,14,30,tzinfo=timezone.utc))==expected
