from datetime import datetime,timezone,timedelta

from src.protections import check_protections


def test_three_recent_symbol_losses_trigger_cooldown():
    now=datetime(2026,11,9,15,tzinfo=timezone.utc)
    rows=[{'symbol':'EURUSD','net':-1,'close_time':(now-timedelta(hours=1,minutes=i)).isoformat()} for i in range(3)]
    assert check_protections(rows,[],'EURUSD',now,{'enabled':True,'consecutive_losses':3,'cooldown_hours':24})==(True,'symbol cooldown after 3 consecutive losses')


def test_symbol_cooldown_expires_and_does_not_cross_symbols():
    now=datetime(2026,11,9,15,tzinfo=timezone.utc)
    rows=[{'symbol':'EURUSD','net':-1,'close_time':(now-timedelta(hours=25)).isoformat()} for _ in range(3)]
    assert check_protections(rows,[],'EURUSD',now,{'enabled':True,'consecutive_losses':3,'cooldown_hours':24})==(False,'')
    assert check_protections(rows,[],'GBPUSD',now,{'enabled':True,'consecutive_losses':3,'cooldown_hours':24})==(False,'')


def test_symbol_daily_r_loss_triggers_day_stop():
    now=datetime(2026,11,9,15,tzinfo=timezone.utc)
    rows=[{'symbol':'EURUSD','net':-1,'outcome_r':-1.6,'close_time':(now-timedelta(hours=1)).isoformat()},
          {'symbol':'EURUSD','net':1,'outcome_r':.2,'close_time':(now-timedelta(minutes=30)).isoformat()}]
    assert check_protections(rows,[],'EURUSD',now,{'enabled':True,'consecutive_losses':3,'symbol_daily_loss_r':1.3})==(True,'symbol daily loss limit reached (-1.40R)')


def test_rolling_equity_drawdown_pauses_entries():
    now=datetime(2026,11,9,15,tzinfo=timezone.utc)
    equity=[{'time':(now-timedelta(hours=2)).isoformat(),'equity':1000},
            {'time':(now-timedelta(minutes=1)).isoformat(),'equity':970}]
    assert check_protections([],equity,'EURUSD',now,{'enabled':True,'rolling_drawdown_pct':2,'drawdown_window_hours':24})==(True,'rolling drawdown pause (3.00%)')
