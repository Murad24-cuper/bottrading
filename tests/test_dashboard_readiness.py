from src.db import Database
from src.dashboard.readiness import readiness_checks,simulate_small_account


def test_readiness_requires_all_six_conditions(tmp_path):
    path=tmp_path/'readiness.db'; db=Database(path)
    start='2026-11-01T00:00:00+00:00'; end='2026-11-08T00:00:00+00:00'
    for n in range(100):
        value=1 if n<60 else -.5
        db.insert_trade(ticket=n+1,symbol='EURUSD',asset_group='forex',direction='buy',volume=.01,open_time=start,close_time='2026-11-03T00:00:00+00:00',profit=value,commission=0,swap=0,magic=1,status='closed',close_reason='tp' if value>0 else 'sl',strategy='trend_pullback')
    db.insert_equity_snapshot(time='2026-11-01T00:00:00+00:00',equity=100,balance=100,margin=0,free_margin=100,open_positions=0)
    checks=readiness_checks(start,end,path)
    assert len(checks)==6 and all(ok for _,ok in checks)
    with db.connect() as connection:
        connection.execute(
            'INSERT INTO bot_events(time,level,source,message) VALUES (?,?,?,?)',
            ('2026-11-04T00:00:00+00:00','CRITICAL','test','failure'),
        )
    assert not readiness_checks(start,end,path)[-1][1]


def test_small_account_simulation_uses_broker_minimum_lot(tmp_path):
    spec={'trade_tick_value':1,'trade_tick_size':.0001,'volume_min':.01,'volume_step':.01,'volume_max':10}
    signals=[{'symbol':'EURUSD','entry':1.1,'sl':1.099},{'symbol':'EURUSD','entry':1.1,'sl':1.0},{'symbol':'UNKNOWN','entry':1,'sl':.9}]
    result=simulate_small_account(signals,100,1.0,{'EURUSD':spec})
    assert result=={'signals':3,'possible':1,'min_lot_rejected':1,'unavailable':1}
