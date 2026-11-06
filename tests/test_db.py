from datetime import date
from src.db import Database
import pytest

def test_create_insert_update_and_query_trades(tmp_path):
    db=Database(tmp_path/'trades.db')
    db.insert_trade(ticket=101,symbol='EURUSD',asset_group='forex',direction='buy',volume=0.01,open_time='2026-11-05T10:00:00+00:00',open_price=1.1,sl=1.09,tp=1.12,profit=0,commission=0,swap=0,magic=20260001,status='open')
    assert len(db.get_open_trades())==1
    assert db.get_trades_for_day(date(2026,11,5))[0]['ticket']==101
    db.update_trade_close(101,close_time='2026-11-05T10:05:00+00:00',close_price=1.12,profit=2.0,commission=-0.1,swap=0.0,close_reason='tp')
    assert db.get_open_trades()==[]
    assert db.get_trades_for_day('2026-11-05')[0]['status']=='closed'
    assert db.get_pnl_since('2026-11-05T00:00:00+00:00')==1.9

def test_signal_stats_snapshot_event_and_wal(tmp_path):
    db=Database(tmp_path/'dashboard.db')
    db.insert_signal(symbol='XAUUSD',strategy='test',direction='buy',timeframe='M5',confidence=.8,entry=2000,sl=1990,tp=2020,expected_cost=.1,taken=0,skip_reason='test')
    db.upsert_daily_stats(date='2026-11-05',start_balance=100,end_balance=101,pnl=1,trades_count=1,wins=1,losses=0,max_drawdown=0,invested_margin_peak=2)
    db.upsert_daily_stats(date='2026-11-05',start_balance=100,end_balance=102,pnl=2,trades_count=2,wins=2,losses=0,max_drawdown=0,invested_margin_peak=2)
    db.insert_equity_snapshot(balance=102,equity=102,margin=2,free_margin=100,open_positions=1)
    db.log_event('WARNING','test','warning event')
    with db.connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM signals').fetchone()[0]==1
        assert conn.execute('SELECT pnl FROM daily_stats WHERE date=?',('2026-11-05',)).fetchone()[0]==2
        assert conn.execute('SELECT COUNT(*) FROM equity_snapshots').fetchone()[0]==1
        assert conn.execute('SELECT level FROM bot_events').fetchone()[0]=='WARNING'
        assert conn.execute('PRAGMA journal_mode').fetchone()[0].lower()=='wal'

def test_commands_have_utc_expiry_and_expire_stale_running_rows(tmp_path):
    from datetime import datetime,timedelta,timezone
    db=Database(tmp_path/'commands.db')
    command=db.insert_command('close_all',ttl_seconds=60)
    with db.connect() as conn:
        row=conn.execute('SELECT created_at,expires_at,status FROM commands WHERE id=?',(command,)).fetchone()
        assert row['status']=='pending'
        assert datetime.fromisoformat(row['expires_at'])-datetime.fromisoformat(row['created_at'])==timedelta(seconds=60)
        conn.execute("UPDATE commands SET status='running' WHERE id=?",(command,))
    assert db.get_pending_commands(bot_started_at=datetime.now(timezone.utc)+timedelta(seconds=1))==[]
    with db.connect() as conn: assert conn.execute('SELECT status FROM commands WHERE id=?',(command,)).fetchone()[0]=='expired'

def test_partial_closes_are_persisted_by_ticket(tmp_path):
    db=Database(tmp_path/'partial.db')
    db.insert_partial_close(ticket=42,symbol='EURUSD',volume=.01,price=1.1,profit=.2,commission=-.01,swap=0,reason='partial_tp')
    rows=db.get_partial_closes(42)
    assert len(rows)==1 and rows[0]['reason']=='partial_tp' and rows[0]['volume']==.01
    assert db.get_pnl_since('2026-11-05T00:00:00+00:00')==pytest.approx(.19)

def test_duplicate_pending_commands_are_refused(tmp_path):
    import pytest
    db=Database(tmp_path/'commands-dedupe.db')
    db.insert_command('pause')
    with pytest.raises(ValueError,match='already pending or running'):
        db.insert_command('pause')
