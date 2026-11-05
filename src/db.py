import sqlite3
from pathlib import Path
from datetime import datetime,timezone,date
SCHEMA='''
CREATE TABLE IF NOT EXISTS trades(id INTEGER PRIMARY KEY,ticket INTEGER UNIQUE,symbol TEXT,asset_group TEXT,direction TEXT,volume REAL,open_time TEXT,close_time TEXT,open_price REAL,close_price REAL,sl REAL,tp REAL,profit REAL,commission REAL,swap REAL,margin_used REAL,strategy TEXT,reason TEXT,magic INTEGER,status TEXT,close_reason TEXT);
CREATE TABLE IF NOT EXISTS signals(id INTEGER PRIMARY KEY,time TEXT,symbol TEXT,strategy TEXT,direction TEXT,timeframe TEXT,confidence REAL,entry REAL,sl REAL,tp REAL,expected_cost REAL,taken INTEGER,skip_reason TEXT);
CREATE TABLE IF NOT EXISTS daily_stats(date TEXT PRIMARY KEY,start_balance REAL,end_balance REAL,pnl REAL,trades_count INTEGER,wins INTEGER,losses INTEGER,max_drawdown REAL,invested_margin_peak REAL);
CREATE TABLE IF NOT EXISTS equity_snapshots(time TEXT,balance REAL,equity REAL,margin REAL,free_margin REAL,open_positions INTEGER);
CREATE TABLE IF NOT EXISTS bot_events(time TEXT,level TEXT,source TEXT,message TEXT);
'''
class Database:
 def __init__(self,path='data/bot.db'):
  self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self.init()
 def connect(self):
  c=sqlite3.connect(self.path,timeout=30); c.row_factory=sqlite3.Row; return c
 def init(self):
  with self.connect() as c: c.execute('PRAGMA journal_mode=WAL'); c.executescript(SCHEMA)
 def insert_trade(self,**v):
  keys=list(v); sql=f"INSERT OR REPLACE INTO trades ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})"
  with self.connect() as c: c.execute(sql,[v[k] for k in keys])
 def update_trade_close(self,ticket,**v):
  v.update(status='closed'); keys=list(v)
  with self.connect() as c: c.execute(f"UPDATE trades SET {','.join(k+'=?' for k in keys)} WHERE ticket=?",[v[k] for k in keys]+[ticket])
 def get_open_trades(self):
  with self.connect() as c: return [dict(r) for r in c.execute("SELECT * FROM trades WHERE status='open'")]
 def get_trades_for_day(self,day=None):
  day=(day or datetime.now(timezone.utc).date()).isoformat()
  with self.connect() as c: return [dict(r) for r in c.execute('SELECT * FROM trades WHERE substr(open_time,1,10)=?',(day,))]
 def insert_signal(self,**v):
  keys=list(v)
  with self.connect() as c: c.execute(f"INSERT INTO signals ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})",[v[k] for k in keys])
 def upsert_daily_stats(self,**v):
  keys=list(v)
  with self.connect() as c: c.execute(f"INSERT OR REPLACE INTO daily_stats ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})",[v[k] for k in keys])
 def insert_equity_snapshot(self,**v):
  keys=list(v)
  with self.connect() as c: c.execute(f"INSERT INTO equity_snapshots ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})",[v[k] for k in keys])
 def log_event(self,level,source,message):
  with self.connect() as c: c.execute('INSERT INTO bot_events VALUES (?,?,?,?)',(datetime.now(timezone.utc).isoformat(),level,source,message))
 def get_pnl_since(self,dt):
  stamp=dt.isoformat() if hasattr(dt,'isoformat') else str(dt)
  with self.connect() as c: return c.execute("SELECT COALESCE(SUM(COALESCE(profit,0)+COALESCE(commission,0)+COALESCE(swap,0)),0) FROM trades WHERE status='closed' AND close_time>=?",(stamp,)).fetchone()[0]
