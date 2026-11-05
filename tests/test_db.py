from src.db import Database

def test_trade_and_stats(tmp_path):
    db=Database(tmp_path/'test.db')
    db.insert_trade(ticket=1,symbol='EURUSD',status='open',open_time='2026-11-05T00:00:00Z')
    assert len(db.get_open_trades())==1
    db.update_trade_close(1,close_time='2026-11-05T00:01:00Z',profit=1,commission=0,swap=0,close_reason='tp')
    assert not db.get_open_trades()
    db.upsert_daily_stats(date='2026-11-05',pnl=1)
    assert db.get_pnl_since('2026-11-05')==1
