from datetime import datetime,timezone
from types import SimpleNamespace
import numpy as np
import pandas as pd
from src.db import Database
from src.models import Signal
from src.scanner import Candidate,MarketScanner,adaptive_top_movers,expected_value_score,rank_candidates,select_diverse_movers,weekend_index_names
from src.news import CalendarEvent

def candidate(symbol,score):
    signal=Signal(symbol,'buy','M1',10,9,12,.8,'test')
    return Candidate(symbol,'forex','test',signal,.8,.1,1,2,{'cost':.1},score,{}, {})

def test_score_and_rank_discard_nonpositive_and_choose_best_per_symbol():
    assert expected_value_score(.8,10,5,1)==6
    ranked=rank_candidates([candidate('EURUSD',2),candidate('EURUSD',3),candidate('GBPUSD',-1)])
    assert [(item.symbol,item.score) for item in ranked]==[('EURUSD',3)]

def test_scan_breadth_expands_below_target_without_forcing_orders():
    assert adaptive_top_movers(40,15,0)==100
    assert adaptive_top_movers(40,15,10)==60


def test_news_events_are_logged_once_per_calendar_refresh(monkeypatch,tmp_path):
    from datetime import timedelta
    import time
    import src.news as news
    now=datetime(2026,11,9,15,tzinfo=timezone.utc)
    event=CalendarEvent(now+timedelta(hours=1),'USD','HIGH','CPI')
    class DB:
        def __init__(self): self.rows=[]
        def log_event(self,level,source,message): self.rows.append((level,source,message))
    scanner=MarketScanner.__new__(MarketScanner)
    scanner.mt5=object(); scanner.settings=SimpleNamespace(config={'news':{'enabled':True,'refresh_hours':6,'stale_after_hours':24}},root=tmp_path)
    scanner.db=DB(); scanner._news_loaded_at=0; scanner._news_notice_at=0; scanner._news_logged_updated=None; scanner._news_events_logged_marker=None
    monkeypatch.setattr(news,'terminal_calendar_path',lambda mt5:None)
    updated=now-timedelta(minutes=1)
    monkeypatch.setattr(news,'load_calendar',lambda *args,**kwargs:([event],updated,'ForexFactory cache',.02))
    ticks=iter((100.0,100.0,161.0,161.0)); monkeypatch.setattr(time,'monotonic',lambda:next(ticks))
    scanner._load_news_calendar(now); scanner._load_news_calendar(now+timedelta(minutes=1))
    assert sum('Yaxın xəbər' in row[2] for row in scanner.db.rows)==1
    assert sum('Calendar source active' in row[2] for row in scanner.db.rows)==1
    assert adaptive_top_movers(40,15,15)==40
    assert adaptive_top_movers(40,15,20)==40

def test_diverse_movers_round_robin_groups_and_prefer_untraded_underlying():
    ranked=[(100,'EURUSD'),(99,'GBPUSD'),(98,'US30Cash'),(97,'US100Cash'),(96,'BTCUSD'),(95,'ETHUSD')]
    groups={'EURUSD':'forex','GBPUSD':'forex','US30Cash':'indices','US100Cash':'indices','BTCUSD':'crypto','ETHUSD':'crypto'}
    selected=select_diverse_movers(ranked,groups,1,4,{'EURUSD'})
    assert {groups[s] for s in selected[:3]}=={'forex','indices','crypto'}
    assert selected[0]!='EURUSD'

def test_weekend_index_names_reports_only_discovered_index_symbols():
    symbols=['BTCUSD','US30Cash','US500Cash','ETHUSD']
    groups={'BTCUSD':'crypto','US30Cash':'indices','US500Cash':'indices','ETHUSD':'crypto'}
    assert weekend_index_names(symbols,groups)==['US30Cash','US500Cash']

def test_repeat_penalty_is_in_expected_risk_units():
    item=candidate('EURUSD',.5); item.risk_money=2
    assert rank_candidates([item],{'EURUSD':2},{'forex':1},.15,.05)==[]

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
        def symbol_info_tick(self,symbol): return SimpleNamespace(bid=1.0,ask=1.0001)
        def account_info(self): return SimpleNamespace(equity=1000)
    risk=SimpleNamespace(risk_per_trade_pct=.5)
    config={'risk':{'sl_move_mult':.8,'tp_move_mult':1.2,'move_horizon_minutes':10},'scanner':{'max_seconds_per_cycle':5,'max_candidates':10,'candle_count':100,'min_score':0,'min_confidence':.6,'require_mtf_agreement':True,'spread_median_lookback_hours':24,'spread_median_cache_seconds':300,'max_spread_vs_median':1.5,'movement_timeframe_minutes':30,'max_spread_volatility_ratio':0.35,'top_movers':40,'timeframe_point_sizes':{}},'strategies':{}}
    settings=SimpleNamespace(config=config,risk=risk,root=tmp_path)
    db=Database(tmp_path/'scan.db'); scanner=MarketScanner(MT5(),settings,db,FakeSymbols())
    scanner._spread_cache={symbol:{'median_points':0.0,'time':datetime.now(timezone.utc)} for symbol in ('EURUSD','GBPUSD')}
    bars=pd.DataFrame({'open':np.arange(100)+1,'high':np.arange(100)+2,'low':np.arange(100),'close':np.arange(100)+1,'tick_volume':100,'spread':1},index=pd.date_range('2026-01-01',periods=100,freq='min',tz='UTC'))
    scanner._bars=lambda symbol,tf,count:bars
    from src import market_data
    monkeypatch.setattr(market_data,'get_cost_estimate',lambda mt5,symbol,volume:{'cost':1 if symbol=='EURUSD' else 100,'commission_known':True})
    monkeypatch.setattr(market_data,'price_distance_to_money',lambda mt5,symbol,distance,volume:abs(distance)*volume)
    result=scanner.scan_once()
    assert [item.symbol for item in result]==['EURUSD']
    assert result[0].signal.entry_hint==1.0001
    with db.connect() as connection:
        rows=[dict(r) for r in connection.execute('SELECT symbol,taken,skip_reason,features FROM signals ORDER BY id')]
    assert len(rows)==2 and all(r['taken']==0 for r in rows)
    assert rows[0]['skip_reason']=='' and 'non-positive' in rows[1]['skip_reason']
    import json
    feature_json=json.loads(rows[0]['features'])
    assert 'observations' in feature_json and 'candlestick_patterns' in feature_json['observations']
    assert 'brain' in feature_json and feature_json['brain']['memory']['probability'] is None
    assert feature_json['brain']['suggested_risk_pct']==0
    assert scanner.last_scan_stats['total_symbols']==2
    assert scanner.last_scan_stats['symbols_scanned']==2
    assert scanner.last_scan_stats['scan_complete'] is True
    assert scanner.last_scan_stats['top_movers']==2
    assert scanner.last_scan_stats['groups_open']=={'forex':2}

def test_open_groups_include_fresh_quotes_rejected_by_volatility_filter(tmp_path,monkeypatch):
    import src.scanner as scanner_module
    monkeypatch.setattr(scanner_module,'load_strategies',lambda settings:[])
    class MT5:
        def symbol_info(self,symbol): return SimpleNamespace(point=.0001)
        def symbol_info_tick(self,symbol): return SimpleNamespace(bid=1.0,ask=1.0001)
        def positions_get(self): return []
    config={'risk':{'move_horizon_minutes':10},'scanner':{'max_seconds_per_cycle':5,'candle_count':100,'movement_timeframe_minutes':30,'max_spread_volatility_ratio':0,'top_movers':40,'target_open_positions':10,'min_movers_per_group':1,'spread_median_lookback_hours':24,'spread_median_cache_seconds':300,'max_spread_vs_median':1.5,'timeframe_point_sizes':{},'max_candidates':10,'min_score':0},'universe':{'refresh_minutes':5}}
    settings=SimpleNamespace(config=config,risk=SimpleNamespace(no_entry_before_close_minutes=60,max_spread_points={}),root=tmp_path)
    scanner=MarketScanner(MT5(),settings,Database(tmp_path/'open-groups.db'),FakeSymbols())
    scanner._spread_cache={name:{'median_points':1.0,'time':datetime.now(timezone.utc)} for name in ('EURUSD','GBPUSD')}
    bars=pd.DataFrame({'open':np.arange(100)+1,'high':np.arange(100)+2,'low':np.arange(100),'close':np.arange(100)+1,'tick_volume':100,'spread':1},index=pd.date_range('2026-01-01',periods=100,freq='min',tz='UTC'))
    scanner._bars=lambda symbol,tf,count:bars
    scanner.scan_once()
    assert scanner.last_scan_stats['groups_open']=={'forex':2}
    assert scanner.last_scan_stats['stage1_passed']==2
    assert scanner.last_scan_stats['signals']==0

def test_cached_m1_history_refetches_when_longer_spread_window_is_needed(tmp_path,monkeypatch):
    import src.scanner as scanner_module
    from src import market_data
    class MT5:
        def symbol_info(self,symbol): return SimpleNamespace(point=.0001)
    settings=SimpleNamespace(config={'scanner':{'timeframe_point_sizes':{}}},risk=SimpleNamespace(),root=tmp_path)
    scanner=MarketScanner(MT5(),settings,Database(tmp_path/'cache.db'),FakeSymbols())
    calls=[]
    def candles(mt5,symbol,timeframe,count):
        calls.append(count)
        length=min(count,30 if count<100 else 1500)
        return pd.DataFrame({'open':np.ones(length),'high':np.ones(length),'low':np.ones(length),'close':np.ones(length),
                             'tick_volume':np.ones(length),'spread':np.ones(length)},index=pd.date_range('2026-01-01',periods=length,freq='min',tz='UTC'))
    monkeypatch.setattr(market_data,'get_closed_candles',candles)
    scanner._bars('EURUSD','M1',30)
    assert len(scanner._bars('EURUSD','M1',1445))==1445
    assert calls==[1,30,1,1445]
