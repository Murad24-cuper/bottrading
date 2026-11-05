"""SQLite-only dashboard data functions. Read queries open the database read-only."""
from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import sqlite3

PROJECT_ROOT=Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH=PROJECT_ROOT/'data'/'bot.db'

def _read(path):
    db=Path(path or DEFAULT_DB_PATH).resolve()
    return sqlite3.connect(db.as_uri()+'?mode=ro',uri=True,timeout=5)

def _rows(path,sql,params=()):
    try:
        with _read(path) as connection:
            connection.row_factory=sqlite3.Row
            return [dict(row) for row in connection.execute(sql,params)]
    except (sqlite3.Error,OSError): return []

def get_bot_status(path=None):
    rows=_rows(path,'SELECT * FROM bot_status WHERE id=1')
    return rows[0] if rows else None

def get_latest_snapshot(path=None):
    rows=_rows(path,'SELECT * FROM equity_snapshots ORDER BY time DESC LIMIT 1')
    return rows[0] if rows else None

def get_day_summary(start_utc,end_utc,path=None):
    closed=_rows(path,"SELECT COALESCE(SUM(COALESCE(profit,0)+COALESCE(commission,0)+COALESCE(swap,0)),0) AS pnl,COUNT(*) AS trades FROM trades WHERE status='closed' AND close_time>=? AND close_time<?",(start_utc,end_utc))
    floats=_rows(path,"SELECT COALESCE(SUM(COALESCE(profit,0)+COALESCE(commission,0)+COALESCE(swap,0)),0) AS pnl FROM trades WHERE status='open'")
    winning=_rows(path,"SELECT COALESCE(SUM(profit+COALESCE(commission,0)+COALESCE(swap,0)),0) AS amount FROM trades WHERE status='closed' AND close_time>=? AND close_time<? AND profit+COALESCE(commission,0)+COALESCE(swap,0)>0",(start_utc,end_utc))
    losing=_rows(path,"SELECT COALESCE(SUM(-(profit+COALESCE(commission,0)+COALESCE(swap,0))),0) AS amount FROM trades WHERE status='closed' AND close_time>=? AND close_time<? AND profit+COALESCE(commission,0)+COALESCE(swap,0)<0",(start_utc,end_utc))
    wins=_rows(path,"SELECT COUNT(*) AS n FROM trades WHERE status='closed' AND close_time>=? AND close_time<? AND profit+COALESCE(commission,0)+COALESCE(swap,0)>0",(start_utc,end_utc))
    losses=_rows(path,"SELECT COUNT(*) AS n FROM trades WHERE status='closed' AND close_time>=? AND close_time<? AND profit+COALESCE(commission,0)+COALESCE(swap,0)<0",(start_utc,end_utc))
    row=closed[0] if closed else {'pnl':0,'trades':0}; floating=floats[0]['pnl'] if floats else 0; win_count=wins[0]['n'] if wins else 0; loss_count=losses[0]['n'] if losses else 0
    count=win_count+loss_count
    return {'closed_pnl':float(row['pnl']),'floating_pnl':float(floating),'net_pnl':float(row['pnl'])+float(floating),'trades':int(row['trades']),'wins':int(win_count),'losses':int(loss_count),'win_rate':win_count/count if count else 0.0,'taken':float(winning[0]['amount']) if winning else 0.0,'lost':float(losing[0]['amount']) if losing else 0.0}

def get_open_positions(path=None):
    return _rows(path,"SELECT ticket,symbol,direction,volume,open_time,open_price,sl,tp,profit,commission,swap,strategy,magic FROM trades WHERE status='open' ORDER BY open_time")

def get_closed_trades(start_utc,end_utc,path=None):
    rows=_rows(path,"SELECT close_time,symbol,direction,volume,open_price,close_price,profit,commission,swap,close_reason,strategy FROM trades WHERE status='closed' AND close_time>=? AND close_time<? ORDER BY close_time DESC",(start_utc,end_utc))
    for row in rows: row['net_profit']=float(row.get('profit') or 0)+float(row.get('commission') or 0)+float(row.get('swap') or 0)
    return rows

def get_latest_signals(path=None,limit=50):
    rows=_rows(path,'SELECT * FROM signals ORDER BY time DESC,id DESC LIMIT ?',(int(limit),))
    for row in rows: row.setdefault('score',0.0)
    return rows

def get_recent_events(path=None,limit=30):
    return _rows(path,'SELECT time,level,source,message FROM bot_events ORDER BY time DESC LIMIT ?',(int(limit),))

def get_equity_curve(start_utc,end_utc,path=None):
    return _rows(path,'SELECT time,balance,equity,margin,free_margin,open_positions FROM equity_snapshots WHERE time>=? AND time<? ORDER BY time',(start_utc,end_utc))

def get_daily_pnl(path=None,days=30):
    return _rows(path,'SELECT date,pnl FROM daily_stats ORDER BY date DESC LIMIT ?',(int(days),))[::-1]

def get_day_stats(day,path=None):
    return _rows(path,'SELECT * FROM daily_stats WHERE date=?',(day.isoformat() if hasattr(day,'isoformat') else str(day),))

def enqueue_command(command,path=None):
    if command not in {'close_all','pause','resume'}: raise ValueError('Unsupported dashboard command')
    db=Path(path or DEFAULT_DB_PATH).resolve()
    with sqlite3.connect(db,timeout=10) as connection:
        cursor=connection.execute('INSERT INTO commands(time,command,status,message) VALUES (?,?,?,?)',(datetime.now(timezone.utc).isoformat(),command,'pending',''))
        return cursor.lastrowid
