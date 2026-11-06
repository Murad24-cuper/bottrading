"""Timeout-protected connection to the local MetaTrader 5 terminal."""
from __future__ import annotations
import queue
import threading
from .logger import get_logger

log=get_logger(__name__)

class MT5CallTimeoutError(TimeoutError):
    """Raised when an MT5 extension call does not return in time."""

class MT5CallProxy:
    """Run each package call on a daemon worker so the bot loop can time out."""
    def __init__(self, module, timeout: float, unhealthy=None):
        self._module=module; self._timeout=float(timeout); self._unhealthy=unhealthy
    def __getattr__(self, name):
        value=getattr(self._module,name)
        if not callable(value): return value
        def call(*args,**kwargs):
            result=queue.Queue(maxsize=1)
            def invoke():
                try: result.put((True,value(*args,**kwargs)))
                except BaseException as exc: result.put((False,exc))
            worker=threading.Thread(target=invoke,name=f'mt5-{name}',daemon=True); worker.start()
            try: ok,payload=result.get(timeout=self._timeout)
            except queue.Empty as exc:
                if self._unhealthy: self._unhealthy(name,self._timeout)
                raise MT5CallTimeoutError(f'MT5 call {name} exceeded {self._timeout:g}s timeout; terminal marked unhealthy') from exc
            if ok: return payload
            raise payload
        return call

class MT5Client:
    def __init__(self,settings):
        self.settings=settings; self.mt5=None; self._module=None; self._unhealthy=False
        self.call_timeout=float(settings.config.get('mt5',{}).get('call_timeout_seconds',20))
    def _mark_unhealthy(self,name,timeout):
        self._unhealthy=True
        log.error('MT5 call %s timed out after %.1fs; marking connection unhealthy',name,timeout)
    def connect(self):
        try: import MetaTrader5 as module
        except ImportError as exc: raise RuntimeError('MetaTrader5 is not installed; install requirements on Windows') from exc
        self._module=module
        self.mt5=MT5CallProxy(module,self.call_timeout,self._mark_unhealthy)
        last_error=None
        for _ in range(2):
            initialized=self.mt5.initialize(self.settings.mt5_path) if self.settings.mt5_path else self.mt5.initialize()
            if initialized: break
            last_error=self.mt5.last_error(); self.mt5.shutdown()
        else: raise RuntimeError(f'MT5 initialize failed after retry: {last_error}')
        if not self.mt5.login(self.settings.mt5_login,password=self.settings.mt5_password,server=self.settings.mt5_server):
            err=self.mt5.last_error(); self.mt5.shutdown(); raise RuntimeError(f'MT5 login failed: {err}')
        account=self.mt5.account_info()
        if account is None:
            err=self.mt5.last_error(); self.mt5.shutdown(); raise RuntimeError(f'MT5 account_info failed: {err}')
        demo_mode=getattr(self.mt5,'ACCOUNT_TRADE_MODE_DEMO',0)
        configured_mode=self.settings.config['account']['mode']
        if account.trade_mode!=demo_mode and (not self.settings.allow_real or configured_mode!='real'):
            self.mt5.shutdown(); raise RuntimeError('Real account refused: set account.mode=real in config.yaml and ALLOW_REAL=true in .env to enable trading')
        terminal=self.mt5.terminal_info()
        if terminal is None:
            err=self.mt5.last_error(); self.mt5.shutdown(); raise RuntimeError(f'MT5 terminal_info failed: {err}')
        if not terminal.trade_allowed: log.warning('MT5 algorithmic trading is disabled in terminal settings')
        mode='hedging' if account.margin_mode==getattr(self.mt5,'ACCOUNT_MARGIN_MODE_RETAIL_HEDGING',2) else 'netting'
        log.info('Connected to account ***%s; margin mode=%s',str(account.login)[-3:],mode)
        self._unhealthy=False
        return self
    def ensure_connected(self):
        terminal=None
        if self.mt5 is not None and not self._unhealthy:
            try: terminal=self.mt5.terminal_info()
            except Exception: terminal=None
        if self.mt5 is None or terminal is None or not bool(getattr(terminal,'connected',True)) or self._unhealthy:
            self.close(); self.connect()
        return True
    def close(self):
        if self.mt5 is not None:
            try: self.mt5.shutdown()
            finally: self.mt5=None; self._module=None; self._unhealthy=False
    def __enter__(self): return self.connect()
    def __exit__(self,*exc): self.close()
