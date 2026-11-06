"""SQLite persistence with WAL enabled for concurrent dashboard readers."""
from __future__ import annotations
from datetime import datetime,timezone,date,timedelta
from pathlib import Path
import sqlite3

SCHEMA='''
CREATE TABLE IF NOT EXISTS trades(
 id INTEGER PRIMARY KEY, ticket INTEGER UNIQUE, symbol TEXT, asset_group TEXT, direction TEXT,
 volume REAL, open_time TEXT, close_time TEXT, open_price REAL, close_price REAL,
 sl REAL, tp REAL, profit REAL, commission REAL, swap REAL, margin_used REAL,
 strategy TEXT, reason TEXT, magic INTEGER, status TEXT, close_reason TEXT,
 timeframe TEXT, initial_risk REAL, initial_volume REAL, scale_out_done INTEGER DEFAULT 0, peak_favorable_r REAL DEFAULT 0,
 extension_until TEXT, extended_minutes INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS partial_closes(
 id INTEGER PRIMARY KEY, deal_ticket INTEGER, ticket INTEGER, symbol TEXT, time TEXT, volume REAL,
 price REAL, profit REAL, commission REAL, swap REAL, reason TEXT);
CREATE TABLE IF NOT EXISTS signals(
 id INTEGER PRIMARY KEY, time TEXT, symbol TEXT, strategy TEXT, direction TEXT,
 timeframe TEXT, confidence REAL, entry REAL, sl REAL, tp REAL, expected_cost REAL, score REAL DEFAULT 0,
 taken INTEGER, skip_reason TEXT);
CREATE TABLE IF NOT EXISTS daily_stats(
 date TEXT PRIMARY KEY, start_balance REAL, end_balance REAL, pnl REAL, trades_count INTEGER,
 wins INTEGER, losses INTEGER, max_drawdown REAL, invested_margin_peak REAL);
CREATE TABLE IF NOT EXISTS daily_report(date TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS weekly_limits(week_start TEXT PRIMARY KEY, start_balance REAL NOT NULL, stopped INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS maintenance_runs(task TEXT NOT NULL, run_key TEXT NOT NULL, completed_at TEXT NOT NULL, PRIMARY KEY(task,run_key));
CREATE TABLE IF NOT EXISTS equity_snapshots(
 time TEXT, balance REAL, equity REAL, margin REAL, free_margin REAL, open_positions INTEGER);
CREATE TABLE IF NOT EXISTS bot_events(time TEXT, level TEXT, source TEXT, message TEXT);
CREATE TABLE IF NOT EXISTS bot_status(
 id INTEGER PRIMARY KEY CHECK(id=1), time TEXT, cycle INTEGER, mode TEXT, status TEXT,
 account_type TEXT, equity REAL, last_error TEXT, mt5_connected INTEGER DEFAULT 0, scan_total INTEGER,
 scan_scanned INTEGER, scan_complete INTEGER, scan_stage1_passed INTEGER, scan_top_n INTEGER, scan_signals INTEGER,
 scan_seconds REAL, scan_rejections TEXT, strategy_diagnostics TEXT, trade_allowed INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS commands(
 id INTEGER PRIMARY KEY, time TEXT, created_at TEXT, expires_at TEXT, command TEXT, status TEXT, message TEXT, processed_time TEXT);
CREATE TABLE IF NOT EXISTS schema_migrations(name TEXT PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS adaptive_gates(
 scope TEXT NOT NULL, name TEXT NOT NULL, disabled_until TEXT NOT NULL, expectancy REAL NOT NULL,
 sample_size INTEGER NOT NULL, reason TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(scope,name));
'''

class Database:
    def __init__(self,path='data/bot.db'):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self.init()
    def connect(self):
        connection=sqlite3.connect(self.path,timeout=30)
        connection.row_factory=sqlite3.Row
        connection.execute('PRAGMA busy_timeout=30000')
        return connection
    def init(self):
        with self.connect() as connection:
            connection.execute('PRAGMA journal_mode=WAL')
            connection.executescript(SCHEMA)
            trade_columns={row['name'] for row in connection.execute('PRAGMA table_info(trades)')}
            for name, sql_type in {'timeframe':'TEXT','initial_risk':'REAL','initial_volume':'REAL','scale_out_done':'INTEGER DEFAULT 0','peak_favorable_r':'REAL DEFAULT 0','extension_until':'TEXT','extended_minutes':'INTEGER DEFAULT 0'}.items():
                if name not in trade_columns: connection.execute(f'ALTER TABLE trades ADD COLUMN {name} {sql_type}')
            connection.execute('UPDATE trades SET initial_volume=volume WHERE initial_volume IS NULL')
            partial_columns={row['name'] for row in connection.execute('PRAGMA table_info(partial_closes)')}
            if 'deal_ticket' not in partial_columns: connection.execute('ALTER TABLE partial_closes ADD COLUMN deal_ticket INTEGER')
            connection.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_partial_deal_ticket ON partial_closes(deal_ticket) WHERE deal_ticket IS NOT NULL')
            status_columns={row['name'] for row in connection.execute('PRAGMA table_info(bot_status)')}
            for name, sql_type in {'mt5_connected':'INTEGER DEFAULT 0','scan_total':'INTEGER','scan_scanned':'INTEGER','scan_complete':'INTEGER','scan_stage1_passed':'INTEGER','scan_top_n':'INTEGER','scan_signals':'INTEGER','scan_seconds':'REAL','scan_rejections':'TEXT','strategy_diagnostics':'TEXT','trade_allowed':'INTEGER DEFAULT 0'}.items():
                if name not in status_columns: connection.execute(f'ALTER TABLE bot_status ADD COLUMN {name} {sql_type}')
            columns={row['name'] for row in connection.execute('PRAGMA table_info(signals)')}
            if 'score' not in columns: connection.execute('ALTER TABLE signals ADD COLUMN score REAL DEFAULT 0')
            command_columns={row['name'] for row in connection.execute('PRAGMA table_info(commands)')}
            if 'created_at' not in command_columns: connection.execute('ALTER TABLE commands ADD COLUMN created_at TEXT')
            if 'expires_at' not in command_columns: connection.execute('ALTER TABLE commands ADD COLUMN expires_at TEXT')
            rows=connection.execute('SELECT id,time,created_at,expires_at FROM commands WHERE created_at IS NULL OR expires_at IS NULL').fetchall()
            for row in rows:
                created=row['created_at'] or row['time'] or datetime.now(timezone.utc).isoformat()
                try:
                    parsed=datetime.fromisoformat(created.replace('Z','+00:00'))
                    parsed=parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
                    expiry=(parsed+timedelta(seconds=60)).isoformat()
                except ValueError:
                    expiry=(datetime.now(timezone.utc)+timedelta(seconds=60)).isoformat()
                connection.execute('UPDATE commands SET created_at=COALESCE(created_at,?),expires_at=COALESCE(expires_at,?) WHERE id=?',(created,expiry,row['id']))
            migration='profitable_sl_close_reason_to_trail'
            applied=connection.execute('SELECT 1 FROM schema_migrations WHERE name=?',(migration,)).fetchone()
            if not applied:
                connection.execute("UPDATE trades SET close_reason='trail' WHERE status='closed' AND close_reason='sl' AND profit>0")
                connection.execute('INSERT INTO schema_migrations(name,applied_at) VALUES (?,?)',(migration,datetime.now(timezone.utc).isoformat()))
    @staticmethod
    def _insert(connection,table,values):
        columns=list(values)
        if not columns: raise ValueError('At least one value is required')
        connection.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",[values[k] for k in columns])
    def insert_trade(self,**values):
        with self.connect() as connection: self._insert(connection,'trades',values)
    def update_trade_close(self,ticket,**values):
        values['status']='closed'; columns=list(values)
        with self.connect() as connection:
            result=connection.execute(f"UPDATE trades SET {','.join(k+'=?' for k in columns)} WHERE ticket=?",[values[k] for k in columns]+[ticket])
            if not result.rowcount: raise KeyError(f'No trade row for ticket {ticket}')
    def update_open_trade(self,ticket,**values):
        if not values: return
        columns=list(values)
        with self.connect() as connection:
            result=connection.execute(f"UPDATE trades SET {','.join(k+'=?' for k in columns)} WHERE ticket=? AND status='open'",[values[k] for k in columns]+[ticket])
            return result.rowcount
    def get_open_trades(self):
        with self.connect() as connection: return [dict(row) for row in connection.execute("SELECT * FROM trades WHERE status='open' ORDER BY open_time")]
    def count_symbol_trades_since(self,symbol,since,magic=None):
        stamp=since.isoformat() if hasattr(since,'isoformat') else str(since)
        with self.connect() as connection:
            if magic is None: row=connection.execute("SELECT COUNT(*) FROM trades WHERE symbol=? AND open_time>=?",(symbol,stamp)).fetchone()
            else: row=connection.execute("SELECT COUNT(*) FROM trades WHERE symbol=? AND magic=? AND open_time>=?",(symbol,int(magic),stamp)).fetchone()
            return int(row[0])
    def count_trades_since(self,since,magic=None):
        stamp=since.isoformat() if hasattr(since,'isoformat') else str(since)
        with self.connect() as connection:
            if magic is None: row=connection.execute('SELECT COUNT(*) FROM trades WHERE open_time>=?',(stamp,)).fetchone()
            else: row=connection.execute('SELECT COUNT(*) FROM trades WHERE open_time>=? AND magic=?',(stamp,int(magic))).fetchone()
            return int(row[0])
    def symbol_closed_since(self,symbol,since,magic=None):
        stamp=since.isoformat() if hasattr(since,'isoformat') else str(since)
        with self.connect() as connection:
            if magic is None: row=connection.execute("SELECT 1 FROM trades WHERE symbol=? AND status='closed' AND close_time>=? LIMIT 1",(symbol,stamp)).fetchone()
            else: row=connection.execute("SELECT 1 FROM trades WHERE symbol=? AND magic=? AND status='closed' AND close_time>=? LIMIT 1",(symbol,int(magic),stamp)).fetchone()
            return row is not None
    def get_trade(self,ticket):
        with self.connect() as connection:
            row=connection.execute('SELECT * FROM trades WHERE ticket=?',(ticket,)).fetchone()
            return dict(row) if row else None
    def latest_trade_id(self):
        with self.connect() as connection: return int(connection.execute('SELECT COALESCE(MAX(id),0) FROM trades').fetchone()[0])
    def get_closed_trades_after_id(self,last_id):
        with self.connect() as connection:
            return [dict(row) for row in connection.execute("SELECT id,ticket,symbol,direction,strategy,profit,commission,swap,close_reason FROM trades WHERE status='closed' AND id>? ORDER BY id",(int(last_id),))]
    def get_trades_for_day(self,day=None):
        if day is None: day=datetime.now(timezone.utc).date()
        if isinstance(day,datetime): day=day.astimezone(timezone.utc).date()
        day=day.isoformat() if hasattr(day,'isoformat') else str(day)
        with self.connect() as connection: return [dict(row) for row in connection.execute('SELECT * FROM trades WHERE substr(open_time,1,10)=? ORDER BY open_time',(day,))]
    def get_closed_trades_for_day(self,day):
        day=day.isoformat() if hasattr(day,'isoformat') else str(day)
        with self.connect() as connection: return [dict(row) for row in connection.execute("SELECT * FROM trades WHERE status='closed' AND substr(close_time,1,10)=? ORDER BY close_time",(day,))]
    def get_daily_stats(self,day):
        day=day.isoformat() if hasattr(day,'isoformat') else str(day)
        with self.connect() as connection:
            row=connection.execute('SELECT * FROM daily_stats WHERE date=?',(day,)).fetchone()
            return dict(row) if row else None
    def save_daily_report(self,day,payload,created_at=None):
        import json
        stamp=created_at or datetime.now(timezone.utc).isoformat()
        data=json.dumps(payload,ensure_ascii=False,sort_keys=True)
        with self.connect() as connection:
            connection.execute('INSERT INTO daily_report(date,created_at,payload) VALUES (?,?,?) ON CONFLICT(date) DO NOTHING',(str(day),stamp,data))
    def get_daily_reports(self,days=7):
        with self.connect() as connection:
            return [dict(row) for row in connection.execute('SELECT * FROM daily_report ORDER BY date DESC LIMIT ?',(int(days),))]
    def get_or_create_week_start(self,week_start,balance):
        with self.connect() as connection:
            connection.execute('INSERT OR IGNORE INTO weekly_limits(week_start,start_balance) VALUES (?,?)',(str(week_start),float(balance)))
            return dict(connection.execute('SELECT * FROM weekly_limits WHERE week_start=?',(str(week_start),)).fetchone())
    def mark_week_stopped(self,week_start):
        with self.connect() as connection: connection.execute('UPDATE weekly_limits SET stopped=1 WHERE week_start=?',(str(week_start),))
    def maintain(self,now=None,signals_days=7,events_days=30,equity_days=30,equity_step_minutes=5):
        """Prune old signals/events and thin older equity points."""
        now=now or datetime.now(timezone.utc)
        if now.tzinfo is None: now=now.replace(tzinfo=timezone.utc)
        now=now.astimezone(timezone.utc)
        with self.connect() as connection:
            connection.execute('DELETE FROM signals WHERE time < ?',((now-timedelta(days=signals_days)).isoformat(),))
            connection.execute('DELETE FROM bot_events WHERE time < ?',((now-timedelta(days=events_days)).isoformat(),))
            cutoff=(now-timedelta(days=equity_days)).isoformat()
            connection.execute('''DELETE FROM equity_snapshots WHERE time < ? AND rowid NOT IN (
                SELECT MIN(rowid) FROM equity_snapshots WHERE time < ?
                GROUP BY strftime('%Y-%m-%dT%H',time), CAST(strftime('%M',time) AS INTEGER) / ?
            )''',(cutoff,cutoff,max(1,int(equity_step_minutes))))
    def backup(self,destination):
        """Create a consistent online SQLite backup, including committed WAL data."""
        target=Path(destination); target.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as source, sqlite3.connect(target) as dest: source.backup(dest)
        return target
    def maintenance_done(self,task,run_key):
        with self.connect() as connection:
            return connection.execute('SELECT 1 FROM maintenance_runs WHERE task=? AND run_key=?',(str(task),str(run_key))).fetchone() is not None
    def mark_maintenance_done(self,task,run_key,now=None):
        stamp=(now or datetime.now(timezone.utc)).isoformat()
        with self.connect() as connection:
            connection.execute('INSERT OR IGNORE INTO maintenance_runs(task,run_key,completed_at) VALUES (?,?,?)',(str(task),str(run_key),stamp))
    def vacuum(self):
        """Checkpoint WAL and vacuum only outside any active transaction."""
        with self.connect() as connection:
            connection.execute('PRAGMA wal_checkpoint(PASSIVE)')
            connection.execute('VACUUM')
    def insert_signal(self,**values):
        values.setdefault('time',datetime.now(timezone.utc).isoformat())
        values.setdefault('score',0.0)
        with self.connect() as connection:
            self._insert(connection,'signals',values)
            return connection.execute('SELECT last_insert_rowid()').fetchone()[0]
    def insert_partial_close(self,**values):
        values.setdefault('time',datetime.now(timezone.utc).isoformat())
        columns=list(values)
        with self.connect() as connection:
            cursor=connection.execute(f"INSERT OR IGNORE INTO partial_closes ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",[values[key] for key in columns])
            return cursor.rowcount
    def get_partial_closes(self,ticket):
        with self.connect() as connection: return [dict(row) for row in connection.execute('SELECT * FROM partial_closes WHERE ticket=? ORDER BY time,id',(int(ticket),))]
    def get_partial_deal_tickets(self,ticket):
        with self.connect() as connection: return {int(row[0]) for row in connection.execute('SELECT deal_ticket FROM partial_closes WHERE ticket=? AND deal_ticket IS NOT NULL',(int(ticket),))}
    def get_active_adaptive_gates(self,now=None):
        now=now or datetime.now(timezone.utc)
        now=now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
        with self.connect() as connection:
            return [dict(row) for row in connection.execute('SELECT * FROM adaptive_gates WHERE disabled_until>? ORDER BY scope,name',(now.isoformat(),))]
    def refresh_adaptive_gates(self,window=20,disable_hours=24,magic=None,now=None):
        """Disable strategies/groups with negative expectancy over recent closed trades."""
        now=now or datetime.now(timezone.utc)
        now=now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
        disabled=[]
        with self.connect() as connection:
            where="status='closed'"; params=[]
            if magic is not None: where+=' AND magic=?'; params.append(int(magic))
            closed=[dict(row) for row in connection.execute(f'SELECT ticket,strategy,asset_group,close_time,COALESCE(profit,0)+COALESCE(commission,0)+COALESCE(swap,0) AS net FROM trades WHERE {where} ORDER BY close_time DESC,id DESC',params)]
            partial={int(row['ticket']):float(row['pnl'] or 0) for row in connection.execute('SELECT ticket,SUM(COALESCE(profit,0)+COALESCE(commission,0)+COALESCE(swap,0)) pnl FROM partial_closes GROUP BY ticket')}
            groups={}
            for row in closed:
                value=float(row['net'])+partial.get(int(row['ticket']),0)
                for scope,name in (('strategy',row['strategy']),('group',row['asset_group'])):
                    if name: groups.setdefault((scope,str(name)),[]).append((row['close_time'],value))
            expiry=(now+timedelta(hours=float(disable_hours))).isoformat()
            for (scope,name),values in groups.items():
                values=values[:int(window)]
                if len(values)<int(window): continue
                expectancy=sum(value for _,value in values)/len(values)
                if expectancy>=0: continue
                existing=connection.execute('SELECT disabled_until FROM adaptive_gates WHERE scope=? AND name=?',(scope,name)).fetchone()
                if existing:
                    old=datetime.fromisoformat(existing['disabled_until'].replace('Z','+00:00'))
                    if old.tzinfo is None: old=old.replace(tzinfo=timezone.utc)
                    if old>now: continue
                message=f'Adaptive gate disabled {scope}={name} for {disable_hours:g}h; {len(values)} recent trades expectancy={expectancy:.4f}'
                connection.execute('INSERT INTO adaptive_gates(scope,name,disabled_until,expectancy,sample_size,reason,updated_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT(scope,name) DO UPDATE SET disabled_until=excluded.disabled_until,expectancy=excluded.expectancy,sample_size=excluded.sample_size,reason=excluded.reason,updated_at=excluded.updated_at',(scope,name,expiry,expectancy,len(values),message,now.isoformat()))
                connection.execute('INSERT INTO bot_events(time,level,source,message) VALUES (?,?,?,?)',(now.isoformat(),'WARNING','risk',message))
                disabled.append({'scope':scope,'name':name,'disabled_until':expiry,'expectancy':expectancy,'sample_size':len(values),'reason':message})
        return disabled
    def get_partial_pnl_since(self,dt):
        stamp=dt.isoformat() if hasattr(dt,'isoformat') else str(dt)
        with self.connect() as connection:
            row=connection.execute('SELECT COALESCE(SUM(COALESCE(profit,0)+COALESCE(commission,0)+COALESCE(swap,0)),0) FROM partial_closes WHERE time>=?',(stamp,)).fetchone()
            return float(row[0])
    def update_signal(self,signal_id,**values):
        if not values: return
        columns=list(values)
        with self.connect() as connection:
            connection.execute(f"UPDATE signals SET {','.join(k+'=?' for k in columns)} WHERE id=?",[values[k] for k in columns]+[signal_id])
    def upsert_daily_stats(self,**values):
        columns=list(values)
        if 'date' not in values: raise ValueError('daily_stats.date is required')
        with self.connect() as connection:
            connection.execute(f"INSERT INTO daily_stats ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)}) ON CONFLICT(date) DO UPDATE SET {','.join(k+'=excluded.'+k for k in columns if k!='date')}",[values[k] for k in columns])
    def insert_equity_snapshot(self,**values):
        values.setdefault('time',datetime.now(timezone.utc).isoformat())
        with self.connect() as connection: self._insert(connection,'equity_snapshots',values)
    def log_event(self,level,source,message):
        with self.connect() as connection:
            connection.execute('INSERT INTO bot_events(time,level,source,message) VALUES (?,?,?,?)',(datetime.now(timezone.utc).isoformat(),str(level),str(source),str(message)))
    def upsert_bot_status(self,**values):
        values.setdefault('time',datetime.now(timezone.utc).isoformat()); values['id']=1
        columns=list(values)
        with self.connect() as connection:
            connection.execute(f"INSERT INTO bot_status ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)}) ON CONFLICT(id) DO UPDATE SET {','.join(k+'=excluded.'+k for k in columns if k!='id')}",[values[k] for k in columns])
    def get_bot_status(self):
        with self.connect() as connection:
            row=connection.execute('SELECT * FROM bot_status WHERE id=1').fetchone()
            return dict(row) if row else None
    def insert_command(self,command,ttl_seconds=60):
        created=datetime.now(timezone.utc); expires=created+timedelta(seconds=int(ttl_seconds))
        if command not in {'close_all','pause','resume','stop','close_all_stop'}: raise ValueError('Unsupported bot command')
        with self.connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            active=connection.execute("SELECT id FROM commands WHERE command=? AND status IN ('pending','running') ORDER BY id LIMIT 1",(str(command),)).fetchone()
            if active: raise ValueError(f'A {command} command is already pending or running')
            cursor=connection.execute('INSERT INTO commands(time,created_at,expires_at,command,status,message) VALUES (?,?,?,?,?,?)',(created.isoformat(),created.isoformat(),expires.isoformat(),str(command),'pending',''))
            return cursor.lastrowid
    def get_recent_commands(self,limit=20):
        with self.connect() as connection: return [dict(row) for row in connection.execute('SELECT id,created_at,expires_at,command,status,message,processed_time FROM commands ORDER BY id DESC LIMIT ?',(int(limit),))]
    def get_pending_commands(self,now=None,bot_started_at=None):
        now=now or datetime.now(timezone.utc)
        now=now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
        started=bot_started_at
        if started is not None: started=started.replace(tzinfo=timezone.utc) if started.tzinfo is None else started.astimezone(timezone.utc)
        with self.connect() as connection:
            rows=connection.execute("SELECT * FROM commands WHERE status IN ('pending','running') ORDER BY id").fetchall(); ready=[]
            for row in rows:
                created=datetime.fromisoformat((row['created_at'] or row['time']).replace('Z','+00:00'))
                expires=datetime.fromisoformat(row['expires_at'].replace('Z','+00:00')) if row['expires_at'] else created+timedelta(seconds=60)
                created=created.replace(tzinfo=timezone.utc) if created.tzinfo is None else created.astimezone(timezone.utc)
                expires=expires.replace(tzinfo=timezone.utc) if expires.tzinfo is None else expires.astimezone(timezone.utc)
                before_start=started is not None and created<started and row['command'] not in {'stop','close_all_stop'}
                if expires<=now or before_start:
                    connection.execute("UPDATE commands SET status='expired',message='expired before processing',processed_time=? WHERE id=?",(now.isoformat(),row['id']))
                elif row['status']=='pending': ready.append(dict(row))
            return ready
    def update_command(self,command_id,status,message=''):
        if status not in {'pending','running','done','failed','expired'}: raise ValueError('Invalid command status')
        with self.connect() as connection:
            connection.execute('UPDATE commands SET status=?,message=?,processed_time=? WHERE id=?',(status,str(message),datetime.now(timezone.utc).isoformat() if status in {'done','failed','expired'} else None,command_id))
    def get_pnl_since(self,dt):
        stamp=dt.isoformat() if hasattr(dt,'isoformat') else str(dt)
        with self.connect() as connection:
            closed=float(connection.execute("SELECT COALESCE(SUM(COALESCE(profit,0)+COALESCE(commission,0)+COALESCE(swap,0)),0) FROM trades WHERE status='closed' AND close_time>=?",(stamp,)).fetchone()[0])
            partial=float(connection.execute("SELECT COALESCE(SUM(COALESCE(profit,0)+COALESCE(commission,0)+COALESCE(swap,0)),0) FROM partial_closes WHERE time>=?",(stamp,)).fetchone()[0])
            return closed+partial
