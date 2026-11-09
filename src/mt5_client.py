"""Timeout-protected connection to the local MetaTrader 5 terminal."""
from __future__ import annotations
import queue
import threading
from .logger import get_logger

log=get_logger(__name__)

class MT5CallTimeoutError(TimeoutError):
    """Raised when an MT5 extension call does not return in time."""

class MT5CallProxy:
    """Run package calls on a single dedicated worker thread with a queue so the bot loop can time out safely."""
    def __init__(self, module, timeout: float, unhealthy=None):
        self._module = module
        self._timeout = float(timeout)
        self._unhealthy = unhealthy
        self._is_unhealthy = False
        self._queue: queue.Queue = queue.Queue()
        self._worker = threading.Thread(target=self._worker_loop, name='mt5-worker', daemon=True)
        self._worker.start()

    def is_single_worker(self) -> bool:
        return True

    def _worker_loop(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                break
            fn, args, kwargs, res_q = item
            try:
                res = fn(*args, **kwargs)
                res_q.put((True, res))
            except BaseException as exc:
                res_q.put((False, exc))

    def __getattr__(self, name):
        value = getattr(self._module, name)
        if not callable(value):
            return value

        def call(*args, **kwargs):
            if self._is_unhealthy:
                raise MT5CallTimeoutError(f"MT5 session is marked unhealthy; call '{name}' rejected")
            res_q = queue.Queue(maxsize=1)
            self._queue.put((value, args, kwargs, res_q))
            try:
                ok, payload = res_q.get(timeout=self._timeout)
            except queue.Empty as exc:
                self._is_unhealthy = True
                if self._unhealthy:
                    self._unhealthy(name, self._timeout)
                raise MT5CallTimeoutError(
                    f'MT5 call {name} exceeded {self._timeout:g}s timeout; terminal marked unhealthy'
                ) from exc
            if ok:
                return payload
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
            except Exception: pass
            finally: self.mt5=None; self._module=None; self._unhealthy=False
    def __enter__(self): return self.connect()
    def __exit__(self,*exc): self.close()
