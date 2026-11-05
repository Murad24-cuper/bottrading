from datetime import datetime,timezone
from types import SimpleNamespace
import numpy as np
import pandas as pd
from src.db import Database
from src.models import Signal
from src.scanner import Candidate,MarketScanner,expected_value_score,rank_candidates

def candidate(symbol,score):
    signal=Signal(symbol,'buy','M1',10,9,12,.8,'test')
    return Candidate(symbol,'forex','test',signal,.8,.1,1,2,{'cost':.1},score,{}, {})

def test_score_and_rank_discard_nonpositive_and_choose_best_per_symbol():
    assert expected_value_score(.8,10,5,1)==6
    ranked=rank_candidates([candidate('EURUSD',2),candidate('EURUSD',3),candidate('GBPUSD',-1)])
    assert [(item.symbol,item.score) for item in ranked]==[('EURUSD',3)]

class FakeStrategy:
    name='fake'; required_timeframes=['M1']; allowed_groups=['forex']
    def generate_signal(self,symbol,candles): return Signal(symbol,'buy','M1',100,99,102,.8,'fake','mock signal')

class FakeSymbols:
    def get_universe(self): return ['EURUSD','GBPUSD']
    def is_tradable(self,symbol): return True,'tradable'
    def get_asset_group(self,symbol): return 'forex'

def test_scanner_mocked_market_data_logs_negative_and_ranks_positive(tmp_path,monkeypatch):
    import src.scanner as scanner_module
    monkeypatch.setattr(scanner_module,'load_strategies',lambda settings:[FakeStrategy()])
    class MT5:
        def symbol_info(self,symbol):
            return SimpleNamespace(point=.0001,_asdict=lambda:{'trade_tick_value':1,'trade_tick_size':1,'volume_min':.01,'volume_step':.01,'volume_max':5})
        def account_info(self): return SimpleNamespace(equity=1000)
    risk=SimpleNamespace(risk_per_trade_pct=.5)
    config={'risk':{},'scanner':{'max_seconds_per_cycle':5,'max_candidates':10,'candle_count':100,'min_score':0},'strategies':{}}
    settings=SimpleNamespace(config=config,risk=risk,root=tmp_path)
    db=Database(tmp_path/'scan.db'); scanner=MarketScanner(MT5(),settings,db,FakeSymbols())
    bars=pd.DataFrame({'open':np.arange(100)+1,'high':np.arange(100)+2,'low':np.arange(100),'close':np.arange(100)+1,'tick_volume':100,'spread':1},index=pd.date_range('2026-01-01',periods=100,freq='min',tz='UTC'))
    scanner._bars=lambda symbol,tf,count:bars
    from src import market_data
    monkeypatch.setattr(market_data,'get_cost_estimate',lambda mt5,symbol,volume:{'cost':1 if symbol=='EURUSD' else 100,'commission_known':True})
    monkeypatch.setattr(market_data,'price_distance_to_money',lambda mt5,symbol,distance,volume:abs(distance)*volume)
    result=scanner.scan_once()
    assert [item.symbol for item in result]==['EURUSD']
    with db.connect() as connection:
        rows=[dict(r) for r in connection.execute('SELECT symbol,taken,skip_reason FROM signals ORDER BY id')]
    assert len(rows)==2 and all(r['taken']==0 for r in rows)
    assert rows[0]['skip_reason']=='' and 'non-positive' in rows[1]['skip_reason']
