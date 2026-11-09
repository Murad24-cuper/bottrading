"""Idempotent UTC maintenance jobs owned by the supervisor process."""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from pathlib import Path
import sqlite3

def should_restart_for_memory(memory_mb: float|None, maximum_mb: float) -> bool:
    """Check a reported process working set against its configured ceiling."""
    return memory_mb is not None and float(memory_mb)>float(maximum_mb)

def prune_old_logs(directory,retention_days=14,now=None):
    """Remove only project log files older than the configured retention."""
    now=now or datetime.now(timezone.utc)
    cutoff=now.timestamp()-max(1,int(retention_days))*86400
    removed=[]
    for path in Path(directory).glob('*.log*'):
        try:
            if path.is_file() and path.stat().st_mtime<cutoff:
                path.unlink(); removed.append(path.name)
        except OSError: continue
    return removed

def run_daily_backup(settings,db,now=None) -> Path|None:
    """Create one SQLite online backup per UTC day and retain the configured count."""
    now=now or datetime.now(timezone.utc); now=now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    key=now.date().isoformat()
    if db.maintenance_done('daily_backup',key): return None
    folder=settings.data_dir/'backups'; folder.mkdir(parents=True,exist_ok=True); target=folder/f'bot_{key}.db'
    source=sqlite3.connect(db.path,timeout=20)
    destination=sqlite3.connect(target)
    try: source.backup(destination)
    finally: destination.close(); source.close()
    keep=max(1,int(settings.config.get('schedule',{}).get('daily_backup_keep',14)))
    backups=sorted(folder.glob('bot_????-??-??.db'),key=lambda path:path.name,reverse=True)
    for stale in backups[keep:]: stale.unlink(missing_ok=True)
    db.mark_maintenance_done('daily_backup',key,now)
    db.log_event('INFO','supervisor',f'Daily database backup completed: {target.name}; retained={min(keep,len(backups))}')
    return target

def due_scheduler_jobs(now: datetime, config: dict) -> list[tuple[str,str]]:
    """Return UTC maintenance jobs that are due, including missed boundary minutes."""
    now=now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    schedule=config.get('schedule',{}); jobs=[]
    hourly_minute=int(schedule.get('hourly_minute_utc',0))
    if now.minute>=hourly_minute:
        jobs.append(('hourly_history',now.strftime('%Y-%m-%dT%H')))
    daily_hour=int(schedule.get('daily_rollover_hour_utc',0))
    if now.hour>=daily_hour:
        jobs.append(('daily_backup',now.date().isoformat()))
    if now.weekday()==int(schedule.get('weekly_day_utc',6)) and now.hour>=int(schedule.get('weekly_hour_utc',2)):
        jobs.append(('weekly_maintenance',now.strftime('%G-W%V')))
    return jobs

def run_scheduler_tick(now: datetime, config: dict, completed: set[tuple[str,str]], handlers: dict) -> list[tuple[str,str]]:
    """Run each due job once per UTC key, isolating errors so later jobs still run."""
    executed=[]
    for task,key in due_scheduler_jobs(now,config):
        identity=(task,key)
        if identity in completed: continue
        handler=handlers.get(task)
        if handler is None: continue
        handler(key)
        completed.add(identity); executed.append(identity)
    return executed

def scheduler_status(db,now=None) -> list[dict]:
    """Build a small dashboard view of last execution and next UTC schedule."""
    now=now or datetime.now(timezone.utc); now=now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    rows=[]
    with db.connect() as connection:
        completed=[dict(row) for row in connection.execute('SELECT task,run_key,completed_at FROM maintenance_runs ORDER BY completed_at DESC LIMIT 20')]
    for task in ('daily_backup','hourly_history','weekly_retrain','weekly_vacuum'):
        last=next((row for row in completed if row['task']==task),None)
        rows.append({'task':task,'last_run':last.get('completed_at') if last else None,'run_key':last.get('run_key') if last else None})
    return rows
