from datetime import datetime,timezone
from src.backtest.engine import BacktestResult
from src.backtest.report import save_report,validate,walk_forward,monte_carlo

def sample_trades():
    return [
      {'symbol':'EURUSD','asset_group':'forex','strategy':'breakout','open_time':'2026-01-01T00:00:00+00:00','close_time':'2026-01-01T01:00:00+00:00','profit':10,'commission':-1,'swap':0,'net_profit':9,'costs':1,'holding_minutes':60,'hour':0},
      {'symbol':'GBPUSD','asset_group':'forex','strategy':'breakout','open_time':'2026-10-01T00:00:00+00:00','close_time':'2026-10-01T01:00:00+00:00','profit':-4,'commission':-1,'swap':0,'net_profit':-5,'costs':1,'holding_minutes':60,'hour':0},
    ]

def test_report_saves_summary_csv_and_equity_plot(tmp_path):
    trades=sample_trades(); curve=[{'time':'2026-01-01T00:00:00+00:00','equity':1000},{'time':'2026-10-01T00:00:00+00:00','equity':1004}]
    directory,metrics=save_report(BacktestResult(trades,curve),tmp_path)
    for name in ('summary.md','trades.csv','equity.png','per_symbol.csv','per_strategy.csv','per_asset_group.csv','per_hour.csv'):
        assert (directory/name).exists()
    assert metrics['overall']['trades']==2
    assert metrics['in_sample']['trades']==1 and metrics['out_of_sample']['trades']==1

def test_walk_forward_caps_each_grid_to_twenty_combinations():
    calls=[]
    def run_window(start,end,strategy,params):
        calls.append((strategy,params))
        return [{'symbol':'EURUSD','strategy':strategy,'close_time':end.isoformat(),'profit':1,'commission':0,'net_profit':1,'costs':0}]
    rows=walk_forward(datetime(2020,1,1,tzinfo=timezone.utc),datetime(2020,9,1,tzinfo=timezone.utc),{'x':{'a':list(range(5)),'b':list(range(5))}},run_window,6,2)
    assert len(rows)==1
    assert len([x for x in calls if x[0]=='x'])==21 # twenty candidates plus selected out-of-sample run


def test_report_metrics_include_trade_sharpe_sortino_and_calmar():
    result=validate(sample_trades(),[],.5)['overall']
    assert {'sharpe','sortino','calmar'}.issubset(result)
    assert result['sharpe']>0 and result['sortino']>0


def test_monte_carlo_bootstrap_is_reproducible_and_reports_ruin():
    trades=[{'net_profit':-20},{'net_profit':-10},{'net_profit':5}]
    a=monte_carlo(trades,15,iterations=500,seed=13)
    b=monte_carlo(trades,15,iterations=500,seed=13)
    assert a==b and a['iterations']==500
    assert a['ruin_probability']>0
    assert set(a['terminal_equity_percentiles'])=={'5','50','95'}
