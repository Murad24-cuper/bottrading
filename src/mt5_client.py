from datetime import datetime,timezone
from .logger import get_logger
log=get_logger(__name__)
class MT5Client:
 def __init__(self,settings): self.settings=settings; self.mt5=None
 def connect(self):
  try: import MetaTrader5 as mt5
  except ImportError as e: raise RuntimeError('MetaTrader5 package is required on Windows') from e
  self.mt5=mt5; path=self.settings.mt5_path
  for attempt in range(2):
   ok=mt5.initialize(path) if path else mt5.initialize()
   if ok: break
   if attempt==0: continue
  if not ok: raise RuntimeError(f'MT5 initialize failed: {mt5.last_error()}')
  if self.settings.mt5_login is not None and not mt5.login(self.settings.mt5_login,password=self.settings.mt5_password,server=self.settings.mt5_server):
   err=mt5.last_error(); mt5.shutdown(); raise RuntimeError(f'MT5 login failed: {err}')
  acc=mt5.account_info()
  if acc is None: raise RuntimeError(f'MT5 account_info failed: {mt5.last_error()}')
  demo=getattr(mt5,'ACCOUNT_TRADE_MODE_DEMO',0)
  if acc.trade_mode!=demo and not self.settings.allow_real: mt5.shutdown(); raise RuntimeError('Real account refused: set ALLOW_REAL=true in .env to enable')
  ti=mt5.terminal_info()
  if ti and not ti.trade_allowed: log.warning('MT5 algorithmic trading is disabled in terminal settings')
  log.info('Connected to MT5 account ***%s',str(acc.login)[-3:]); return self
 def ensure_connected(self):
  if self.mt5 is None or self.mt5.terminal_info() is None: self.connect()
 def close(self):
  if self.mt5: self.mt5.shutdown(); self.mt5=None
 def __enter__(self): return self.connect()
 def __exit__(self,*args): self.close()
