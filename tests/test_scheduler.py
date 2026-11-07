from datetime import datetime,timezone,timedelta
from pathlib import Path
from types import SimpleNamespace
from src.db import Database
from src.scheduler import due_scheduler_jobs,run_daily_backup,run_scheduler_tick,should_restart_for_memory

def test_daily_backup_is_atomic_per_utc_day_and_idempotent(tmp_path):
    db=Database(tmp_path/'bot.db'); db.log_event('INFO','test','backup source')
    settings=SimpleNamespace(data_dir=tmp_path/'data',config={'schedule':{'daily_backup_keep':14}})
    now=datetime(2026,11,6,0,0,tzinfo=timezone.utc)
    path=run_daily_backup(settings,db,now)
    assert path and path.exists() and run_daily_backup(settings,db,now) is None
    with Database(path).connect() as connection:
        assert connection.execute('select count(*) from bot_events').fetchone()[0]==1

def test_schedule_due_times_are_utc_and_weekly_jobs_are_sunday():
    config={'schedule':{'daily_rollover_hour_utc':0,'weekly_day_utc':6,'weekly_hour_utc':2}}
    baku=datetime(2026,11,7,4,0,tzinfo=timezone(timedelta(hours=4)))
    assert due_scheduler_jobs(baku,config)==[('hourly_history','2026-11-07T00'),('daily_backup','2026-11-07')]
    sunday=datetime(2026,11,8,2,0,tzinfo=timezone.utc)
    assert due_scheduler_jobs(sunday,config)==[('hourly_history','2026-11-08T02'),('daily_backup','2026-11-08'),('weekly_maintenance','2026-W45')]

def test_scheduler_simulates_minutes_hours_and_utc_day_rollovers_once():
    config={'schedule':{'hourly_minute_utc':0,'daily_rollover_hour_utc':0,'weekly_day_utc':6,'weekly_hour_utc':2}}
    completed=set(); runs=[]
    handlers={task:(lambda key,task=task:runs.append((task,key))) for task in ('hourly_history','daily_backup','weekly_maintenance')}
    now=datetime(2026,11,7,23,58,tzinfo=timezone.utc)
    for minute in range(48*60+5):
        run_scheduler_tick(now,config,completed,handlers)
        now+=timedelta(minutes=1)
    assert len([row for row in runs if row[0]=='hourly_history'])==50
    assert [key for task,key in runs if task=='daily_backup']==['2026-11-07','2026-11-08','2026-11-09','2026-11-10']
    assert [key for task,key in runs if task=='weekly_maintenance']==['2026-W45']
    assert len(runs)==len(completed)

def test_memory_limit_triggers_only_above_ceiling():
    assert not should_restart_for_memory(None,1500)
    assert not should_restart_for_memory(1500,1500)
    assert should_restart_for_memory(1501,1500)
