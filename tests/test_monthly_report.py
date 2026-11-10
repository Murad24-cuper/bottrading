from datetime import datetime, timezone

from src.db import Database
from src.monthly_report import build_monthly_report, write_monthly_report
from src.scheduler import due_scheduler_jobs


def test_monthly_report_is_report_only_and_filters_to_forex_gold(tmp_path):
    db=Database(tmp_path/'bot.db')
    db.insert_trade(ticket=1,symbol='EURUSDmicro',asset_group='forex',direction='buy',volume=.01,
        open_time='2026-11-03T10:00:00+00:00',close_time='2026-11-03T11:00:00+00:00',open_price=1.1,
        close_price=1.101,sl=1.09,tp=1.12,profit=2,commission=-.1,swap=0,strategy='ts_momentum',
        magic=7,status='closed',initial_risk=1,features='{"exploration":{"variant":"v1"},"sizing":{"planned_stop_risk_money":1}}',mode='exploration')
    db.insert_trade(ticket=2,symbol='US500Cash',asset_group='indices',direction='buy',volume=.01,
        open_time='2026-11-03T10:00:00+00:00',close_time='2026-11-03T11:00:00+00:00',open_price=1,close_price=2,
        sl=.5,tp=3,profit=99,commission=0,swap=0,strategy='ts_momentum',magic=7,status='closed',mode='exploration')
    report=build_monthly_report(db,'2026-11')
    assert 'ts_momentum' not in report
    assert 'TS Momentum' in report and '| 1 | 100.0% | +1.900 |' in report
    assert 'avtomatik' in report
    target=write_monthly_report(db,tmp_path/'MONTHLY_REPORT.md','2026-11')
    assert target.read_text(encoding='utf-8')==report
    assert db.maintenance_done('monthly_report','2026-11')


def test_monthly_job_due_on_first_utc_day():
    jobs=due_scheduler_jobs(datetime(2026,12,1,3,tzinfo=timezone.utc),{})
    assert ('monthly_report','2026-12') in jobs
    assert ('monthly_report','2026-12') not in due_scheduler_jobs(datetime(2026,12,2,3,tzinfo=timezone.utc),{})
