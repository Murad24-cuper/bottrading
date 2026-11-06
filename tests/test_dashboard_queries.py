from src.db import Database
from src.dashboard import queries

def test_dashboard_queries_return_database_only_views_and_queue_commands(tmp_path):
    path=tmp_path/'dashboard.db'; db=Database(path)
    db.insert_trade(ticket=1,symbol='EURUSD',asset_group='forex',direction='buy',volume=.1,open_time='2026-11-05T10:00:00+00:00',close_time='2026-11-05T10:10:00+00:00',open_price=1.1,close_price=1.11,sl=1.09,tp=1.12,profit=2,commission=-.2,swap=0,magic=20260001,status='closed',close_reason='tp',strategy='breakout')
    db.insert_trade(ticket=2,symbol='XAUUSD',asset_group='metals',direction='sell',volume=.01,open_time='2026-11-05T10:05:00+00:00',open_price=2000,profit=-.5,commission=0,swap=0,magic=20260001,status='open',strategy='trend_pullback')
    db.insert_partial_close(ticket=2,symbol='XAUUSD',volume=.01,price=1999,profit=.3,commission=-.02,swap=0,reason='partial_tp',time='2026-11-05T10:08:00+00:00')
    db.insert_signal(time='2026-11-05T10:00:00+00:00',symbol='EURUSD',strategy='breakout',direction='buy',timeframe='M5',confidence=.8,entry=1.1,sl=1.09,tp=1.12,expected_cost=.1,score=1.5,taken=1,skip_reason='')
    db.upsert_daily_stats(date='2026-11-05',start_balance=100,end_balance=102,pnl=1.5,trades_count=1,wins=1,losses=0,max_drawdown=0,invested_margin_peak=12)
    db.insert_equity_snapshot(time='2026-11-05T10:00:00+00:00',balance=102,equity=101.5,margin=12,free_margin=89.5,open_positions=1)
    db.log_event('WARNING','bot','mock warning')
    db.upsert_bot_status(time='2026-11-05T10:00:00+00:00',cycle=3,mode='shadow',status='running',account_type='DEMO',equity=101.5,last_error='')
    start='2026-11-05T00:00:00+00:00'; end='2026-11-06T00:00:00+00:00'
    summary=queries.get_day_summary(start,end,path)
    assert summary['closed_pnl']==2.08 and summary['floating_pnl']==-.5 and summary['net_pnl']==1.58
    assert summary['wins']==1 and summary['taken']==2.08
    assert queries.get_open_positions(path)[0]['symbol']=='XAUUSD'
    assert queries.get_closed_trades(start,end,path)[0]['net_profit']==1.8
    assert queries.get_closed_trades(start,end,path)[0]['sl']==1.09
    assert queries.get_latest_signals(path)[0]['score']==1.5
    assert queries.get_recent_events(path)[0]['level']=='WARNING'
    with db.connect() as conn:
        conn.execute("INSERT INTO bot_events(time,level,source,message) VALUES (?,?,?,?)",('2026-11-05T12:00:00+00:00','WARNING','supervisor','Restarting bot after exit code 1; restart 1/5 in window, delay=10s'))
    assert queries.get_supervisor_restart_count(start,end,path)==1
    assert queries.get_equity_curve(start,end,path)[0]['equity']==101.5
    assert queries.get_daily_pnl(path)[0]['pnl']==1.5
    assert queries.get_bot_status(path)['status']=='running'
    command_id=queries.enqueue_command('close_all',path)
    assert db.get_pending_commands()[0]['id']==command_id
    assert queries.get_recent_commands(path)[0]['command']=='close_all'
    import pytest
    with pytest.raises(ValueError,match='already pending or running'):
        queries.enqueue_command('close_all',path)
