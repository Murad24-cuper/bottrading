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
