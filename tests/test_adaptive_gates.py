from datetime import datetime, timezone, timedelta

from src.db import Database


def _add_trade(db, ticket, strategy='breakout', group='forex', pnl=-1.0, close='2026-11-01T00:00:00+00:00'):
    db.insert_trade(ticket=ticket,symbol=f'S{ticket}',asset_group=group,direction='buy',volume=.01,
                    open_time=close,close_time=close,open_price=10,close_price=9,sl=9,tp=12,
                    profit=pnl,commission=0,swap=0,strategy=strategy,magic=17,status='closed')


def test_adaptive_gates_require_window_and_report_strategy_and_group(tmp_path):
    db=Database(tmp_path/'gates.db'); now=datetime(2026,11,6,tzinfo=timezone.utc)
    for i in range(19): _add_trade(db,i+1)
    assert db.refresh_adaptive_gates(20,24,17,now)==[]
    _add_trade(db,20,pnl=-.5)
    disabled=db.refresh_adaptive_gates(20,24,17,now)
    assert {(r['scope'],r['name']) for r in disabled}=={('strategy','breakout'),('group','forex')}
    active=db.get_active_adaptive_gates(now)
    assert len(active)==2 and all(r['expectancy']<0 and r['sample_size']==20 for r in active)
    with db.connect() as conn:
        assert conn.execute("select count(*) from bot_events where source='risk'").fetchone()[0]==2


def test_adaptive_gate_uses_partial_close_net_profit_and_expires(tmp_path):
    db=Database(tmp_path/'gates-partial.db'); now=datetime(2026,11,6,tzinfo=timezone.utc)
    for i in range(20): _add_trade(db,i+1,pnl=1.0)
    db.insert_partial_close(ticket=20,symbol='S20',volume=.01,price=9,profit=-25,commission=0,swap=0)
    gated=db.refresh_adaptive_gates(20,24,17,now)
    assert len(gated)==2
    later=now+timedelta(hours=24,seconds=1)
    assert db.get_active_adaptive_gates(later)==[]
    assert db.refresh_adaptive_gates(20,24,17,later)
