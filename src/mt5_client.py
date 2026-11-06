"""Connection wrapper; MetaTrader5 is imported only when a connection is requested."""
from __future__ import annotations
from .logger import get_logger
log=get_logger(__name__)

class MT5Client:
    def __init__(self,settings): self.settings=settings; self.mt5=None
    def connect(self):
        try: import MetaTrader5 as mt5
        except ImportError as exc: raise RuntimeError('MetaTrader5 is not installed; install requirements on Windows') from exc
        self.mt5=mt5
        last_error=None
        for _ in range(2):
            initialized=mt5.initialize(self.settings.mt5_path) if self.settings.mt5_path else mt5.initialize()
            if initialized: break
            last_error=mt5.last_error()
            mt5.shutdown()
        else: raise RuntimeError(f'MT5 initialize failed after retry: {last_error}')
        if not mt5.login(self.settings.mt5_login,password=self.settings.mt5_password,server=self.settings.mt5_server):
            err=mt5.last_error(); mt5.shutdown(); raise RuntimeError(f'MT5 login failed: {err}')
        account=mt5.account_info()
        if account is None:
            err=mt5.last_error(); mt5.shutdown(); raise RuntimeError(f'MT5 account_info failed: {err}')
        demo_mode=getattr(mt5,'ACCOUNT_TRADE_MODE_DEMO',0)
        configured_mode=self.settings.config['account']['mode']
        if account.trade_mode!=demo_mode and (not self.settings.allow_real or configured_mode!='real'):
            mt5.shutdown(); raise RuntimeError('Real account refused: set account.mode=real in config.yaml and ALLOW_REAL=true in .env to enable trading')
        terminal=mt5.terminal_info()
        if terminal is None:
            err=mt5.last_error(); mt5.shutdown(); raise RuntimeError(f'MT5 terminal_info failed: {err}')
        if not terminal.trade_allowed: log.warning('MT5 algorithmic trading is disabled in terminal settings')
        mode='hedging' if account.margin_mode==getattr(mt5,'ACCOUNT_MARGIN_MODE_RETAIL_HEDGING',2) else 'netting'
        log.info('Connected to account ***%s; margin mode=%s',str(account.login)[-3:],mode)
        return self
    def ensure_connected(self):
        terminal=None
        if self.mt5 is not None:
            try: terminal=self.mt5.terminal_info()
            except Exception: terminal=None
        if self.mt5 is None or terminal is None or not bool(getattr(terminal,'connected',True)):
            self.close(); self.connect()
        return True
    def close(self):
        if self.mt5 is not None:
            self.mt5.shutdown(); self.mt5=None
    def __enter__(self): return self.connect()
    def __exit__(self,*exc): self.close()
