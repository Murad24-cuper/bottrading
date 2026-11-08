from datetime import datetime,timezone,timedelta
from types import SimpleNamespace

from src.executor import Executor


def test_session_close_only_closes_our_positions_on_any_weekday():
    now=datetime(2026,11,3,12,0,tzinfo=timezone.utc)
    positions=[SimpleNamespace(ticket=1,magic=7,symbol='EURUSD'),SimpleNamespace(ticket=2,magic=8,symbol='GBPUSD')]
    mt5=SimpleNamespace(positions_get=lambda:positions)
    settings=SimpleNamespace(magic_number=7,risk=SimpleNamespace(max_session_gap_hours=6,no_entry_before_close_minutes=60))
    class Sessions:
        def next_session_close(self,symbol,when,gap):
            assert gap==6
            return (now+timedelta(minutes=30),12.0)
    executor=Executor(mt5,settings,None,Sessions())
    closed=[]
    executor.close_position=lambda ticket,reason: closed.append((ticket,reason)) or True
    assert executor.enforce_session_close(now_utc=now)==[True]
    assert closed==[(1,'session_close')]

def test_news_preclose_only_manages_owned_positions_and_closes_losers_five_minutes_before(monkeypatch):
    from src.news import CalendarEvent
    now=datetime(2026,11,9,12,55,tzinfo=timezone.utc)
    event=CalendarEvent(now+timedelta(minutes=4),'USD','HIGH','CPI')
    positions=[SimpleNamespace(ticket=1,magic=7,symbol='EURUSD',type=0,price_open=1.1,volume=.1,sl=1.09,tp=1.12),SimpleNamespace(ticket=2,magic=8,symbol='EURUSD',type=0,price_open=1.1,volume=.1,sl=1.09,tp=1.12)]
    mt5=SimpleNamespace(positions_get=lambda:positions,POSITION_TYPE_BUY=0,symbol_info_tick=lambda s:SimpleNamespace(bid=1.09,ask=1.0901),symbol_info=lambda s:SimpleNamespace(trade_tick_value=1,trade_tick_value_profit=1,trade_tick_size=.0001))
    settings=SimpleNamespace(magic_number=7)
    executor=Executor(mt5,settings,None)
    closed=[]; executor.close_position=lambda ticket,reason:closed.append((ticket,reason)) or True
    monkeypatch.setattr('src.market_data.get_cost_estimate',lambda *args,**kwargs:{'cost':.1})
    assert executor.enforce_news_positions([event],now)==[True]
    assert closed==[(1,'news')]
