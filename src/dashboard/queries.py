"""SQLite-only dashboard data functions. Read queries open the database read-only."""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from pathlib import Path
import sqlite3
import yaml
import os
from ..paths import project_paths

PROJECT_ROOT=Path(__file__).resolve().parents[2]
_data_dir,_log_dir=project_paths(PROJECT_ROOT)
_config=yaml.safe_load((PROJECT_ROOT/'config.yaml').read_text(encoding='utf-8')) or {}
_db_path=Path(_config.get('db_path','data/bot.db'))
DEFAULT_DB_PATH=Path(os.getenv('BOT_DB_PATH')) if os.getenv('BOT_DB_PATH') else (_db_path if _db_path.is_absolute() else PROJECT_ROOT/_db_path)

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
    closed=_rows(path,"SELECT COALESCE(SUM(COALESCE(profit,0)+COALESCE(commission,0)+COALESCE(swap,0)),0) AS pnl,COUNT(*) AS trades FROM trades WHERE status='closed' AND mode='main' AND close_time>=? AND close_time<?",(start_utc,end_utc))
    partial=_rows(path,"SELECT COALESCE(SUM(COALESCE(p.profit,0)+COALESCE(p.commission,0)+COALESCE(p.swap,0)),0) AS pnl,COALESCE(SUM(CASE WHEN p.profit+COALESCE(p.commission,0)+COALESCE(p.swap,0)>0 THEN p.profit+COALESCE(p.commission,0)+COALESCE(p.swap,0) ELSE 0 END),0) AS taken,COALESCE(SUM(CASE WHEN p.profit+COALESCE(p.commission,0)+COALESCE(p.swap,0)<0 THEN -(p.profit+COALESCE(p.commission,0)+COALESCE(p.swap,0)) ELSE 0 END),0) AS lost FROM partial_closes p JOIN trades t ON t.ticket=p.ticket WHERE t.mode='main' AND p.time>=? AND p.time<?",(start_utc,end_utc))
    floats=_rows(path,"SELECT COALESCE(SUM(COALESCE(profit,0)+COALESCE(commission,0)+COALESCE(swap,0)),0) AS pnl FROM trades WHERE status='open' AND mode='main'")
    winning=_rows(path,"SELECT COALESCE(SUM(profit+COALESCE(commission,0)+COALESCE(swap,0)),0) AS amount FROM trades WHERE status='closed' AND mode='main' AND close_time>=? AND close_time<? AND profit+COALESCE(commission,0)+COALESCE(swap,0)>0",(start_utc,end_utc))
    losing=_rows(path,"SELECT COALESCE(SUM(-(profit+COALESCE(commission,0)+COALESCE(swap,0))),0) AS amount FROM trades WHERE status='closed' AND mode='main' AND close_time>=? AND close_time<? AND profit+COALESCE(commission,0)+COALESCE(swap,0)<0",(start_utc,end_utc))
    wins=_rows(path,"SELECT COUNT(*) AS n FROM trades WHERE status='closed' AND mode='main' AND close_time>=? AND close_time<? AND profit+COALESCE(commission,0)+COALESCE(swap,0)>0",(start_utc,end_utc))
    losses=_rows(path,"SELECT COUNT(*) AS n FROM trades WHERE status='closed' AND mode='main' AND close_time>=? AND close_time<? AND profit+COALESCE(commission,0)+COALESCE(swap,0)<0",(start_utc,end_utc))
    row=closed[0] if closed else {'pnl':0,'trades':0}; part=partial[0] if partial else {'pnl':0,'taken':0,'lost':0}; floating=floats[0]['pnl'] if floats else 0; win_count=wins[0]['n'] if wins else 0; loss_count=losses[0]['n'] if losses else 0
    count=win_count+loss_count
    return {'closed_pnl':float(row['pnl'])+float(part['pnl']),'floating_pnl':float(floating),'net_pnl':float(row['pnl'])+float(part['pnl'])+float(floating),'trades':int(row['trades']),'wins':int(win_count),'losses':int(loss_count),'win_rate':win_count/count if count else 0.0,'taken':(float(winning[0]['amount']) if winning else 0.0)+float(part['taken']),'lost':(float(losing[0]['amount']) if losing else 0.0)+float(part['lost'])}

def get_open_positions(path=None):
    return _rows(path,"SELECT ticket,symbol,direction,volume,open_time,open_price,sl,tp,profit,commission,swap,strategy,magic,extended_minutes,features FROM trades WHERE status='open' AND mode='main' ORDER BY open_time")

def get_closed_trades(start_utc,end_utc,path=None):
    rows=_rows(path,"SELECT close_time,symbol,direction,volume,open_price,close_price,sl,tp,profit,commission,swap,close_reason,strategy FROM trades WHERE status='closed' AND mode='main' AND close_time>=? AND close_time<? ORDER BY close_time DESC",(start_utc,end_utc))
    for row in rows: row['net_profit']=float(row.get('profit') or 0)+float(row.get('commission') or 0)+float(row.get('swap') or 0)
    return rows

def get_exploration_trades(start_utc,end_utc,path=None):
    """Return isolated demo exploration trades for the dedicated dashboard section."""
    rows=_rows(path,"SELECT open_time,close_time,symbol,direction,volume,profit,commission,swap,strategy,status,close_reason FROM trades WHERE mode IN ('exploration','weekend_exploration') AND ((open_time>=? AND open_time<?) OR (close_time>=? AND close_time<?) OR status='open') ORDER BY open_time DESC",(start_utc,end_utc,start_utc,end_utc))
    for row in rows: row['net_profit']=sum(float(row.get(key) or 0) for key in ('profit','commission','swap'))
    return rows

def get_weekend_control(path=None):
    rows=_rows(path,'SELECT disabled_until,expectancy,sample_size,updated_at FROM weekend_control WHERE id=1')
    return rows[0] if rows else None

def get_today_diversity(start_utc,end_utc,path=None):
    rows=_rows(path,"SELECT symbol,asset_group,COUNT(*) AS trades FROM trades WHERE mode='main' AND open_time>=? AND open_time<? GROUP BY symbol,asset_group",(start_utc,end_utc))
    from ..symbols import underlying_key
    symbols={underlying_key(row['symbol']) for row in rows}
    groups={row.get('asset_group') or 'other' for row in rows}
    per_group={}
    for row in rows: per_group[row.get('asset_group') or 'other']=per_group.get(row.get('asset_group') or 'other',0)+int(row['trades'])
    per_symbol={}
    for row in rows:
        key=underlying_key(row['symbol']); per_symbol[key]=per_symbol.get(key,0)+int(row['trades'])
    return {'symbols':len(symbols),'groups':len(groups),'per_group':per_group,'top_symbols':sorted(per_symbol.items(),key=lambda item:(-item[1],item[0]))[:10]}

def get_scheduler_status(path=None,now=None):
    """Expose last and next UTC times for supervisor maintenance jobs."""
    now=now or datetime.now(timezone.utc); now=now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    config=_config.get('schedule',{}); db_path=Path(path or DEFAULT_DB_PATH)
    try:
        with _read(db_path) as connection:
            connection.row_factory=sqlite3.Row
            completed=[dict(row) for row in connection.execute('SELECT task,run_key,completed_at FROM maintenance_runs ORDER BY completed_at DESC LIMIT 50')]
    except (sqlite3.Error,OSError): completed=[]
    def weekly_next(day,hour):
        days=(int(day)-now.weekday())%7; candidate=(now+timedelta(days=days)).replace(hour=int(hour),minute=0,second=0,microsecond=0)
        return candidate+timedelta(days=7) if candidate<=now else candidate
    hourly=(now+timedelta(hours=1)).replace(minute=0,second=0,microsecond=0)
    daily=now.replace(hour=int(config.get('daily_rollover_hour_utc',0)),minute=0,second=0,microsecond=0)
    if daily<=now: daily+=timedelta(days=1)
    rows=[]
    for task,next_run in [('hourly_history',hourly),('daily_backup',daily),('weekly_retrain',weekly_next(config.get('weekly_day_utc',6),config.get('weekly_hour_utc',2))),('weekly_vacuum',weekly_next(config.get('weekly_day_utc',6),config.get('weekly_hour_utc',2)))]:
        last=next((row for row in completed if row['task']==task),None)
        rows.append({'task':task,'last_run':last['completed_at'] if last else None,'next_run':next_run.isoformat(),'status':'tamamlanıb' if last else 'gözləyir'})
    return rows

def get_partial_closes(start_utc,end_utc,path=None):
    return _rows(path,'SELECT time,symbol,ticket,volume,price,profit,commission,swap,reason FROM partial_closes WHERE time>=? AND time<? ORDER BY time DESC',(start_utc,end_utc))

def get_latest_signals(path=None,limit=50):
    rows=_rows(path,'SELECT * FROM signals ORDER BY time DESC,id DESC LIMIT ?',(int(limit),))
    for row in rows: row.setdefault('score',0.0)
    return rows

def get_top_skip_reasons_since(since_utc,path=None,limit=5):
    """Aggregate the most common recent signal rejection reasons."""
    return _rows(path,"SELECT skip_reason,COUNT(*) AS count FROM signals WHERE time>=? AND taken=0 AND COALESCE(skip_reason,'')<>'' GROUP BY skip_reason ORDER BY count DESC,skip_reason LIMIT ?",(since_utc,int(limit)))

def get_feature_impact(path=None):
    """Return closed-trade feature observations for the analysis tab."""
    from ..analysis.feature_impact import analyze_feature_impact
    return analyze_feature_impact(_rows(path,"SELECT profit,commission,swap,features FROM trades WHERE status='closed' AND mode='main' ORDER BY close_time"))

def get_signals_period(start_utc,end_utc,path=None,limit=5000):
    rows=_rows(path,'SELECT time,symbol,direction,entry,sl,tp,strategy,confidence,taken FROM signals WHERE time>=? AND time<? ORDER BY time DESC LIMIT ?',(start_utc,end_utc,int(limit)))
    return rows

def get_recent_events(path=None,limit=30):
    return _rows(path,'SELECT time,level,source,message FROM bot_events ORDER BY time DESC LIMIT ?',(int(limit),))

def get_supervisor_restart_count(start_utc,end_utc,path=None):
    rows=_rows(path,"SELECT COUNT(*) AS count FROM bot_events WHERE source='supervisor' AND message LIKE 'Restarting bot after exit code %' AND time>=? AND time<?",(start_utc,end_utc))
    return int(rows[0]['count']) if rows else 0

def get_adaptive_gates(path=None):
    return _rows(path,'SELECT scope,name,disabled_until,expectancy,sample_size,reason FROM adaptive_gates WHERE disabled_until>? ORDER BY scope,name',(datetime.now(timezone.utc).isoformat(),))

def get_equity_curve(start_utc,end_utc,path=None):
    return _rows(path,'SELECT time,balance,equity,margin,free_margin,open_positions FROM equity_snapshots WHERE time>=? AND time<? ORDER BY time',(start_utc,end_utc))

def get_daily_pnl(path=None,days=30):
    return _rows(path,'SELECT date,pnl FROM daily_stats ORDER BY date DESC LIMIT ?',(int(days),))[::-1]

def get_performance_report(start_utc,end_utc,path=None):
    """Return trade metrics and breakdowns for a UTC interval."""
    trades=_rows(path,"SELECT id,ticket,symbol,asset_group,strategy,close_reason,close_time,profit,commission,swap,estimated_spread_cost FROM trades WHERE status='closed' AND mode='main' AND close_time>=? AND close_time<? ORDER BY close_time",(start_utc,end_utc))
    partials=_rows(path,'SELECT ticket,profit,commission,swap FROM partial_closes WHERE time>=? AND time<?',(start_utc,end_utc))
    partial_by_ticket={}; partial_cost_by_ticket={}
    for row in partials:
        key=int(row['ticket']); partial_by_ticket[key]=partial_by_ticket.get(key,0.0)+sum(float(row.get(k) or 0) for k in ('profit','commission','swap'))
        partial_cost_by_ticket[key]=partial_cost_by_ticket.get(key,0.0)+abs(float(row.get('commission') or 0))
    for row in trades:
        row['net']=sum(float(row.get(k) or 0) for k in ('profit','commission','swap'))+partial_by_ticket.get(int(row['ticket']),0.0)
        row['costs']=abs(float(row.get('commission') or 0))+partial_cost_by_ticket.get(int(row['ticket']),0.0)+float(row.get('estimated_spread_cost') or 0)
    values=[float(row['net']) for row in trades]
    winners=[value for value in values if value>0]; losers=[value for value in values if value<0]
    snapshots=_rows(path,'SELECT time,equity FROM equity_snapshots WHERE time>=? AND time<? ORDER BY time',(start_utc,end_utc))
    peak=None; max_dd=0.0
    for row in snapshots:
        equity=float(row['equity'] or 0); peak=equity if peak is None else max(peak,equity)
        if peak>0: max_dd=max(max_dd,(peak-equity)/peak*100)
    def metrics(rows):
        outcomes=[float(row['net']) for row in rows]; win=[x for x in outcomes if x>0]; loss=[x for x in outcomes if x<0]
        n=len(outcomes)
        return {'trades':n,'win_rate':len(win)/n if n else 0.0,'average_win':sum(win)/len(win) if win else 0.0,'average_loss':abs(sum(loss)/len(loss)) if loss else 0.0,'expectancy':sum(outcomes)/n if n else 0.0,'total_pnl':sum(outcomes),'estimated_costs':sum(float(row.get('costs') or 0) for row in rows)}
    def breakdown(key):
        groups={}
        for row in trades: groups.setdefault(str(row.get(key) or 'unknown'),[]).append(row)
        return {name:metrics(rows) for name,rows in sorted(groups.items())}
    overall=metrics(trades); overall['max_drawdown_pct']=max_dd if snapshots else None; overall['equity_samples']=len(snapshots)
    return {'overall':overall,'by_strategy':breakdown('strategy'),'by_asset_group':breakdown('asset_group'),'by_close_reason':breakdown('close_reason')}

def get_daily_report_rows(path=None,days=30):
    rows=_rows(path,'SELECT date,created_at,payload FROM daily_report ORDER BY date DESC LIMIT ?',(int(days),))
    for row in rows:
        try:
            import json
            row['payload']=json.loads(row['payload'])
        except (ValueError,TypeError): row['payload']={}
    return rows

def get_day_stats(day,path=None):
    return _rows(path,'SELECT * FROM daily_stats WHERE date=?',(day.isoformat() if hasattr(day,'isoformat') else str(day),))

def enqueue_command(command,path=None,ttl_seconds=60):
    if command not in {'close_all','pause','resume','stop','close_all_stop'}: raise ValueError('Unsupported dashboard command')
    db=Path(path or DEFAULT_DB_PATH).resolve()
    now=datetime.now(timezone.utc); created=now.isoformat(); expires=(now+timedelta(seconds=int(ttl_seconds))).isoformat()
    with sqlite3.connect(db,timeout=10,isolation_level=None) as connection:
        connection.execute('BEGIN IMMEDIATE')
        active=connection.execute("SELECT id FROM commands WHERE command=? AND status IN ('pending','running') ORDER BY id LIMIT 1",(command,)).fetchone()
        if active: raise ValueError(f'A {command} command is already pending or running')
        cursor=connection.execute('INSERT INTO commands(time,created_at,expires_at,command,status,message) VALUES (?,?,?,?,?,?)',(created,created,expires,command,'pending',''))
        return cursor.lastrowid

def get_recent_commands(path=None,limit=20):
    return _rows(path,'SELECT id,created_at,expires_at,command,status,message,processed_time FROM commands ORDER BY id DESC LIMIT ?',(int(limit),))
