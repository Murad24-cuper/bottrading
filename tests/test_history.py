from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
from src.history import download_history,_rates,refresh_incremental_batch,build_history_manifest,_write_history_manifest
from src.history import TF_MINUTES

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

def test_native_slow_timeframes_are_supported_without_synthetic_resampling():
    assert TF_MINUTES['H4']==240 and TF_MINUTES['D1']==1440
    from src.backtest.engine import TF_DELTA
    assert TF_DELTA['H4'].total_seconds()==4*3600
    assert TF_DELTA['D1'].total_seconds()==24*3600

def test_history_download_and_incremental_cache(tmp_path):
    mt5=FakeMT5(); settings=SimpleNamespace(root=tmp_path,config={'history':{'data_dir':'data/history','ranges_months':{'M1':3}}})
    start=datetime(2025,1,1,tzinfo=timezone.utc); end=datetime(2025,1,1,0,3,tzinfo=timezone.utc)
    first=download_history(mt5,['EURUSD'],['M1'],start,end,settings)
    assert len(first['EURUSD']['M1'])==4 and len(mt5.calls)==1
    path=tmp_path/'data/history/EURUSD_M1.parquet'
    assert path.exists() and (tmp_path/'data/history/symbol_specs.json').exists()
    download_history(mt5,['EURUSD'],['M1'],start,end,settings)
    assert len(mt5.calls)==1
    manifest=tmp_path/'data/history/manifests/EURUSD_M1.json'
    assert manifest.exists()
    import json
    saved=json.loads(manifest.read_text(encoding='utf-8'))
    assert saved['rows']==4 and saved['sha256'] and saved['source']=='MT5 terminal'


def test_manifest_lists_gaps_without_synthesizing_rows(tmp_path):
    import hashlib
    frame=pd.DataFrame({'open':[1,2,3]},index=pd.to_datetime(['2026-01-01T00:00:00Z','2026-01-01T00:01:00Z','2026-01-01T00:05:00Z']))
    path=tmp_path/'EURUSD_M1.parquet'; path.write_bytes(b'parquet placeholder')
    manifest=build_history_manifest(frame,path,'EURUSD','M1')
    _write_history_manifest(tmp_path,manifest)
    assert manifest['rows']==3 and manifest['gap_count']==1
    assert manifest['gaps'][0]['missing_bars']==3
    assert manifest['sha256']==hashlib.sha256(path.read_bytes()).hexdigest()

def test_long_history_range_retries_in_chunks_and_keeps_available_bars(tmp_path):
    class ChunkOnlyMT5(FakeMT5):
        def copy_rates_range(self,symbol,tf,start,end):
            self.calls.append((start,end))
            if (end-start).days>7:
                return None
            stamp=int(start.timestamp())
            return np.array([(stamp,1.,2.,.5,1.5,100,1)],dtype=[('time','i8'),('open','f8'),('high','f8'),('low','f8'),('close','f8'),('tick_volume','i8'),('spread','i8')])
        def last_error(self): return (-2,'Invalid params')

    mt5=ChunkOnlyMT5(); settings=SimpleNamespace(root=tmp_path,config={'history':{'data_dir':'data/history','ranges_months':{'M1':3}}})
    start=datetime(2025,1,1,tzinfo=timezone.utc); end=datetime(2025,1,16,tzinfo=timezone.utc)
    result=download_history(mt5,['EURUSD'],['M1'],start,end,settings)

    assert len(mt5.calls)==3
    assert len(result['EURUSD']['M1'])==3
    assert result['EURUSD']['M1'].index.is_monotonic_increasing

def test_history_uses_large_safe_chunks_before_seven_day_fallback():
    class LargeChunkMT5(FakeMT5):
        TIMEFRAME_M5=5
        def copy_rates_range(self,symbol,tf,start,end):
            self.calls.append((start,end))
            if (end-start).days>300: return None
            stamp=int(start.timestamp())
            return np.array([(stamp,1.,2.,.5,1.5,100,1)],dtype=[('time','i8'),('open','f8'),('high','f8'),('low','f8'),('close','f8'),('tick_volume','i8'),('spread','i8')])
    mt5=LargeChunkMT5(); start=datetime(2024,1,1,tzinfo=timezone.utc); end=datetime(2026,1,1,tzinfo=timezone.utc)
    result=_rates(mt5,'BTCUSD','M5',start,end,chunk_days=300,max_bars=80000)
    assert len(mt5.calls)==3 # The two-year request is split into 300-day bounded pieces.
    assert len(result)==3

def test_incremental_refresh_rotates_one_symbol_timeframe_on_same_mt5_session(tmp_path,monkeypatch):
    import json
    import src.history as history
    data_dir=tmp_path/'data'; brain=data_dir/'brain'; brain.mkdir(parents=True)
    (brain/'universe.json').write_text(json.dumps({'symbols':[{'symbol':'EURUSD'},{'symbol':'GOLD'}]}),encoding='utf-8')
    settings=SimpleNamespace(root=tmp_path,data_dir=data_dir,config={'timeframes':['M1'],'history':{'data_dir':'data/history','incremental_refresh_enabled':True,'incremental_timeframes':['M1','M5'],'incremental_batch_days':{'M1':1,'M5':7}}})
    calls=[]; monkeypatch.setattr(history,'download_history',lambda mt5,symbols,timeframes,start,end,settings:calls.append((mt5,symbols,timeframes,start,end)) or {symbols[0]:{timeframes[0]:pd.DataFrame(index=range(3))}})
    mt5=object(); now=datetime(2026,1,10,tzinfo=timezone.utc)
    first=refresh_incremental_batch(mt5,settings,now)
    second=refresh_incremental_batch(mt5,settings,now)
    assert (calls[0][1],calls[0][2])==(['EURUSD'],['M1'])
    assert (calls[1][1],calls[1][2])==(['EURUSD'],['M5'])
    assert calls[0][0] is mt5 and calls[1][0] is mt5
    assert (calls[0][4]-calls[0][3]).days==1
    assert (calls[1][4]-calls[1][3]).days==7
    assert first['cursor']==1 and second['cursor']==2

def test_incremental_refresh_backfills_oldest_missing_chunk(tmp_path,monkeypatch):
    import json
    import src.history as history
    data_dir=tmp_path/'data'; brain=data_dir/'brain'; brain.mkdir(parents=True)
    (brain/'universe.json').write_text(json.dumps({'symbols':[{'symbol':'EURUSD'}]}),encoding='utf-8')
    history_dir=data_dir/'history'; history_dir.mkdir()
    first=pd.Timestamp('2026-10-01T00:00:00Z')
    pd.DataFrame({'open':[1],'high':[1],'low':[1],'close':[1],'tick_volume':[1],'spread':[1]},index=pd.DatetimeIndex([first],name='time')).to_parquet(history_dir/'EURUSD_M1.parquet')
    settings=SimpleNamespace(root=tmp_path,data_dir=data_dir,config={'history':{'data_dir':'data/history','ranges_months':{'M1':12},'incremental_refresh_enabled':True,'incremental_timeframes':['M1'],'incremental_batch_days':{'M1':7}}})
    calls=[]
    monkeypatch.setattr(history,'download_history',lambda mt5,symbols,timeframes,start,end,settings:calls.append((start,end)) or {symbols[0]:{timeframes[0]:pd.DataFrame(index=[])}})
    now=datetime(2026,11,1,tzinfo=timezone.utc)
    refresh_incremental_batch(object(),settings,now)
    start,end=calls[0]
    assert end==first.to_pydatetime()
    assert (end-start).days==7

def test_weekend_history_uses_shorter_ranges_and_no_h1(tmp_path,monkeypatch):
    import json
    import src.history as history
    data_dir=tmp_path/'data'; brain=data_dir/'brain'; brain.mkdir(parents=True)
    (brain/'universe.json').write_text(json.dumps({'symbols':[{'symbol':'BTCUSD'}]}),encoding='utf-8')
    settings=SimpleNamespace(root=tmp_path,data_dir=data_dir,config={'universe':{'weekend_symbols':['BTCUSD']},'history':{'data_dir':'data/history','ranges_months':{'M1':12,'M5':36,'M15':36,'H1':60},'weekend_ranges_months':{'M1':6,'M5':24,'M15':24},'weekend_timeframes':['M1','M5','M15'],'incremental_refresh_enabled':True,'incremental_timeframes':['M1','M5','M15','H1'],'incremental_batch_days':{'M1':1,'M5':7,'M15':14,'H1':30}}})
    calls=[]
    monkeypatch.setattr(history,'download_history',lambda mt5,symbols,timeframes,start,end,settings:calls.append((timeframes[0],start,end)) or {'BTCUSD':{timeframes[0]:pd.DataFrame(index=[])}})
    now=datetime(2026,11,8,tzinfo=timezone.utc)
    for _ in range(3): refresh_incremental_batch(object(),settings,now)
    assert [row[0] for row in calls]==['M1','M5','M15']
    assert (now-calls[1][1]).days==7
