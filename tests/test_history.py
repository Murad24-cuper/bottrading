from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
from src.history import download_history

class FakeMT5:
    TIMEFRAME_M1=1
    def __init__(self): self.calls=[]
    def symbol_select(self,symbol,selected): return True
    def symbol_info(self,symbol):
        return SimpleNamespace(point=.0001,_asdict=lambda:{'digits':5,'point':.0001,'trade_tick_size':.0001,'trade_tick_value':1,'volume_min':.01,'volume_step':.01,'volume_max':10})
    def copy_rates_range(self,symbol,tf,start,end):
        self.calls.append((start,end))
        times=pd.date_range(start,end,freq='min',tz='UTC') if start.tzinfo is None else pd.date_range(start,end,freq='min')
        return np.array([(int(t.timestamp()),1.,2.,.5,1.5,100,1) for t in times],dtype=[('time','i8'),('open','f8'),('high','f8'),('low','f8'),('close','f8'),('tick_volume','i8'),('spread','i8')])
    def last_error(self): return (0,'ok')

def test_history_download_and_incremental_cache(tmp_path):
    mt5=FakeMT5(); settings=SimpleNamespace(root=tmp_path,config={'history':{'data_dir':'data/history','ranges_months':{'M1':3}}})
    start=datetime(2025,1,1,tzinfo=timezone.utc); end=datetime(2025,1,1,0,3,tzinfo=timezone.utc)
    first=download_history(mt5,['EURUSD'],['M1'],start,end,settings)
    assert len(first['EURUSD']['M1'])==4 and len(mt5.calls)==1
    path=tmp_path/'data/history/EURUSD_M1.parquet'
    assert path.exists() and (tmp_path/'data/history/symbol_specs.json').exists()
    download_history(mt5,['EURUSD'],['M1'],start,end,settings)
    assert len(mt5.calls)==1
