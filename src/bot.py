"""Resilient single-process live loop; shadow mode never submits orders."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime,timezone,timedelta
from pathlib import Path
import logging,os,signal,time,re,json
from collections import Counter
from .config import Settings
from .db import Database
from .executor import Executor
from .logger import get_logger
from .market_data import get_account_state
from .mt5_client import MT5Client
from .risk import calc_volume,check_trade_allowed
from .scanner import MarketScanner
from .symbols import SymbolService
from .symbols import underlying_group,underlying_key

log=get_logger(__name__)
RECONNECT_BACKOFF=(5,15,60)

class BotLock:
    """Exclusive lock file for one bot process per project directory."""
    def __init__(self,path): self.path=Path(path); self.token=f'{os.getpid()} {time.time_ns()}'; self.held=False
    def acquire(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        try:
            with self.path.open('x',encoding='utf-8') as handle: handle.write(self.token+'\n')
        except FileExistsError as exc: raise RuntimeError(f'Bot lock already exists: {self.path}; verify no bot is running before removing it') from exc
        self.held=True
    def release(self):
        if not self.held: return
        try:
            if self.path.read_text(encoding='utf-8').strip()==self.token: self.path.unlink(missing_ok=True)
        finally: self.held=False
    def __enter__(self): self.acquire(); return self
    def __exit__(self,*args): self.release()

@dataclass
class CycleResult:
    continue_running:bool=True
    sleep_seconds:float=5.0
    market_closed:bool=False

class TradingBot:
    def __init__(self,settings:Settings,client=None,db=None,scanner=None,executor=None,clock=None,sleep=None,monotonic=None):
        self.settings=settings; self.client=client or MT5Client(settings); self.db=db or Database(settings.db_path)
        self.scanner=scanner; self.executor=executor; self.clock=clock or (lambda:datetime.now(timezone.utc)); self.sleep_fn=sleep or time.sleep; self.monotonic=monotonic or time.monotonic
        self.process_started_at=self._now()
        self.cycle_number=0; self.consecutive_errors=0; self.trading_disabled=False; self.last_error=''; self._critical_reported=False
        self._market_closed_logged=False; self._last_snapshot=0.0; self._started=False; self._last_account_type='unknown'; self._daily_peak_equity=0.0
        self.stop_event=False; self._connection_down=False; self.lock=BotLock(settings.root/'data'/'bot.lock')
        self._stop_after_cycle=False
        self._cycle_reservations=[]
        self.exit_reason=''
    @property
    def live(self): return self.settings.config['live']
    def _now(self):
        value=self.clock()
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    def _set_status(self,status='running',equity=None):
        stats=getattr(self.scanner,'last_scan_stats',{}) if self.scanner else {}
        self.db.upsert_bot_status(time=self._now().isoformat(),cycle=self.cycle_number,mode=self.live['mode'],status=status,account_type=self._last_account_type,equity=equity,last_error=self.last_error,mt5_connected=int(not self._connection_down),scan_total=stats.get('total_symbols',0),scan_scanned=stats.get('symbols_scanned',0),scan_complete=int(bool(stats.get('scan_complete',False))),scan_stage1_passed=stats.get('stage1_passed',0),scan_top_n=stats.get('top_movers',0),scan_signals=stats.get('signals',0),scan_seconds=stats.get('scan_seconds',0),scan_rejections=json.dumps(stats.get('stage1_rejections',{}),sort_keys=True),strategy_diagnostics=json.dumps(stats.get('strategy_diagnostics',{}),sort_keys=True))
    def _event(self,level,message):
        log.log(getattr(logging,level.upper(),logging.INFO),message)
        self.db.log_event(level.upper(),'bot',message)
    def _request_supervisor_stop(self,reason):
        self.exit_reason=str(reason)
        path=self.settings.root/'data'/'supervisor.stop'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(self.exit_reason+'\n',encoding='utf-8')
    def _components(self):
        mt5=self.client.mt5
        service=SymbolService(mt5,self.settings)
        if self.scanner is None: self.scanner=MarketScanner(mt5,self.settings,self.db,service)
        if self.executor is None: self.executor=Executor(mt5,self.settings,self.db,service)
    def _account_type(self):
        account=self.client.mt5.account_info()
        if account is None: raise RuntimeError(f'account_info failed: {self.client.mt5.last_error()}')
        self._last_account_type='DEMO' if account.trade_mode==getattr(self.client.mt5,'ACCOUNT_TRADE_MODE_DEMO',0) else 'REAL'
        return account
    def _startup(self,state):
        if self._started: return
        enabled=[s.name for s in getattr(self.scanner,'_strategies',[])] if self.scanner else []
        allowed=[name for name in enabled if name in self.live['strategies']]
        self._event('INFO',f"Bot started mode={self.live['mode']} account={self._last_account_type} equity={state.equity:.2f} enabled={enabled} allowed_live={allowed}")
        self._started=True
    def _halt_requested(self):
        path=self.settings.root/'STOP'
        if not path.exists(): return False
        try: content=path.read_text(encoding='utf-8')
        except OSError: content=''
        if re.search(r'\bHALT\b',content,re.IGNORECASE):
            self._event('WARNING','STOP contains HALT; exiting cleanly without closing positions')
            self._request_supervisor_stop('HALT kill switch')
            self._set_status('stopped')
            return True
        return False
    def _process_commands(self):
        for command in self.db.get_pending_commands(now=self._now(),bot_started_at=self.process_started_at):
            command_id=int(command['id']); action=command['command']
            self.db.update_command(command_id,'running')
            try:
                if action=='close_all':
                    results=self.executor.close_all('manual')
                    failed=[r.message for r in results if not r.success]
                    if failed: raise RuntimeError('; '.join(failed))
                elif action=='stop':
                    self._stop_after_cycle=True
                    self._request_supervisor_stop('dashboard stop command')
                elif action=='close_all_stop':
                    self._stop_after_cycle=True
                    self._request_supervisor_stop('dashboard close-all-and-stop command')
                    results=self.executor.close_all('kill')
                    failed=[r.message for r in results if not r.success]
                    if failed: raise RuntimeError('; '.join(failed))
                elif action=='pause':
                    (self.settings.root/'STOP').write_text('PAUSE\n',encoding='utf-8')
                elif action=='resume':
                    (self.settings.root/'STOP').unlink(missing_ok=True)
                else: raise ValueError(f'Unknown bot command: {action}')
                self.db.update_command(command_id,'done','completed')
                self._event('INFO',f'Processed command {command_id}: {action}')
            except Exception as exc:
                self.db.update_command(command_id,'failed',str(exc))
                self._event('ERROR',f'Command {command_id} ({action}) failed: {exc}')
    def _signal_update(self,candidate,taken,reason):
        row_id=getattr(candidate,'signal_row_id',None)
        if row_id is not None: self.db.update_signal(row_id,taken=int(taken),skip_reason=reason or '')
        else:
            signal=candidate.signal
            self.db.insert_signal(time=self._now().isoformat(),symbol=signal.symbol,strategy=signal.strategy_name,direction=signal.direction,timeframe=signal.timeframe,confidence=signal.confidence,entry=signal.entry_hint,sl=signal.sl_price,tp=signal.tp_price,expected_cost=float(candidate.cost.get('cost',0)),score=float(candidate.score),taken=int(taken),skip_reason=reason or '')
    def _owned_positions(self):
        mt5=self.client.mt5
        return [p for p in (mt5.positions_get() or []) if int(p.magic)==self.settings.magic_number]
    def _pnl_periods(self,now):
        day=now.replace(hour=0,minute=0,second=0,microsecond=0)
        monday=(now-timedelta(days=now.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)
        return self.db.get_pnl_since(day),self.db.get_pnl_since(monday)
    def _candidate(self,candidate,now,allow_entries):
        live_mode=self.live['mode']=='trade'
        allowed_strategy=candidate.strategy in self.live['strategies']
        active_gates=self.db.get_active_adaptive_gates(now) if hasattr(self.db,'get_active_adaptive_gates') else []
        gate=next((entry for entry in active_gates if (entry['scope']=='strategy' and entry['name']==candidate.strategy) or (entry['scope']=='group' and entry['name']==candidate.asset_group)),None)
        if gate: reason=f'adaptive gate active: {gate["scope"]}={gate["name"]} until {gate["disabled_until"]}'
        elif (self.settings.root/'STOP').exists(): reason='kill switch active'
        elif self.consecutive_errors>=int(self.live['max_cycle_errors']) or self.trading_disabled: reason='consecutive cycle error limit reached'
        elif not live_mode: reason='shadow mode'
        elif not allowed_strategy: reason='strategy not allowed live'
        elif not allow_entries: reason='new trades disabled after cycle errors'
        else: reason=''
        if reason:
            self._signal_update(candidate,False,reason); return False
        state=get_account_state(self.client.mt5); positions=self._owned_positions()
        spec=candidate.symbol_spec; signal=candidate.signal
        volume,volume_reason=calc_volume(state.equity,self.settings.risk.risk_per_trade_pct,signal.entry_hint,signal.sl_price,spec)
        if volume<=0:
            self._signal_update(candidate,False,volume_reason); return False
        order_type=self.client.mt5.ORDER_TYPE_BUY if signal.direction=='buy' else self.client.mt5.ORDER_TYPE_SELL
        margin=self.client.mt5.order_calc_margin(order_type,candidate.symbol,volume,signal.entry_hint)
        if margin is None:
            reason=f'order_calc_margin failed: {self.client.mt5.last_error()}'; self._signal_update(candidate,False,reason); return False
        service=getattr(self.scanner,'symbols',None)
        open_positions=[]
        db_open={int(row['ticket']):row for row in self.db.get_open_trades()}
        for p in positions:
            info=self.client.mt5.symbol_info(p.symbol); group=service.get_asset_group(p.symbol) if service else candidate.asset_group
            row=db_open.get(int(p.ticket),{})
            open_positions.append({'symbol':p.symbol,'asset_group':group,'exposure_group':underlying_group(p.symbol,group),'underlying':underlying_key(p.symbol),'direction':'buy' if p.type==self.client.mt5.POSITION_TYPE_BUY else 'sell','currency_base':getattr(info,'currency_base','') if info else '','currency_profit':getattr(info,'currency_profit','') if info else '','profit':float(p.profit)+float(getattr(p,'swap',0) or 0)+float(row.get('commission') or 0)})
        visible_symbols={str(position['symbol']) for position in open_positions}
        reserved_margin=0.0
        for reservation in self._cycle_reservations:
            if reservation['position']['symbol'] not in visible_symbols:
                open_positions.append(reservation['position']); reserved_margin+=reservation['margin']
        pnl_today,pnl_week=self._pnl_periods(now)
        cooldown=self.settings.risk.symbol_cooldown_minutes
        cooldown_active=cooldown>0 and self.db.symbol_closed_since(candidate.symbol,now-timedelta(minutes=cooldown),self.settings.magic_number)
        day_start=now.replace(hour=0,minute=0,second=0,microsecond=0)
        symbol_trades_today=self.db.count_symbol_trades_since(candidate.symbol,day_start,self.settings.magic_number)
        session_closing=False
        if service and hasattr(service,'next_session_close'):
            upcoming=service.next_session_close(candidate.symbol,now,0.0)
            session_closing=bool(upcoming and 0<=(upcoming[0]-now).total_seconds()/60<=self.settings.risk.no_entry_before_close_minutes)
        allowed,why=check_trade_allowed(signal,state,open_positions,pnl_today,pnl_week,self.settings,candidate.cost,candidate.asset_group,now,margin+reserved_margin,volume,spec,cooldown_active,symbol_trades_today,session_closing)
        if not allowed:
            self._signal_update(candidate,False,why); return False
        result=self.executor.open_trade(signal,volume)
        if not result.success:
            self._signal_update(candidate,False,result.message); return False
        self._cycle_reservations.append({'position':{'symbol':candidate.symbol,'asset_group':candidate.asset_group,'exposure_group':underlying_group(candidate.symbol,candidate.asset_group),'underlying':underlying_key(candidate.symbol),'direction':signal.direction,'currency_base':spec.get('currency_base',''),'currency_profit':spec.get('currency_profit',''),'profit':0.0},'margin':float(margin)})
        self._signal_update(candidate,True,'')
        # Refresh portfolio state before the next ranked candidate.
        get_account_state(self.client.mt5); self._owned_positions()
        return True
    def _daily_stats(self,state,positions,now):
        day=now.date().isoformat(); previous=self.db.get_daily_stats(day)
        closed=self.db.get_closed_trades_for_day(day)
        net=lambda row:float(row.get('profit') or 0)+float(row.get('commission') or 0)+float(row.get('swap') or 0)
        closed_pnl=sum(net(row) for row in closed)+self.db.get_partial_pnl_since(datetime.fromisoformat(now.date().isoformat()+'T00:00:00+00:00'))
        open_rows={int(row['ticket']):row for row in self.db.get_open_trades()}
        floating=sum(float(p.profit)+float(getattr(p,'swap',0) or 0)+float(open_rows.get(int(p.ticket),{}).get('commission') or 0) for p in positions)
        start=previous['start_balance'] if previous else state.balance
        if not self._daily_peak_equity or not previous: self._daily_peak_equity=max(float(start),float(state.equity))
        self._daily_peak_equity=max(self._daily_peak_equity,float(state.equity))
        peak_margin=max(float(previous.get('invested_margin_peak') or 0) if previous else 0,float(state.margin))
        self.db.upsert_daily_stats(date=day,start_balance=float(start),end_balance=float(state.balance),pnl=closed_pnl+floating,trades_count=len(closed),wins=sum(net(x)>0 for x in closed),losses=sum(net(x)<0 for x in closed),max_drawdown=max(float(previous.get('max_drawdown') or 0) if previous else 0,self._daily_peak_equity-float(state.equity)),invested_margin_peak=peak_margin)
    def _connected_cycle(self,now):
        self._cycle_reservations=[]
        self._components(); account=self._account_type(); state=get_account_state(self.client.mt5); self._startup(state)
        self.executor.sync_positions(); getattr(self.executor,'enforce_adverse_move_exit',lambda *_:None)(self.settings); self.executor.enforce_time_stop(self.settings); self.executor.enforce_session_close(self.settings,now)
        risk_cfg=self.settings.config['risk']
        if hasattr(self.db,'refresh_adaptive_gates'):
            self.db.refresh_adaptive_gates(risk_cfg.get('gating_window',20),risk_cfg.get('gating_disable_hours',24),self.settings.magic_number,now)
        self._process_commands()
        if self._stop_after_cycle:
            self._set_status('stopped',state.equity)
            return CycleResult(False,0)
        scan=getattr(self.scanner,'scan',None) or getattr(self.scanner,'scan_once')
        candidates=scan()
        scan_stats=getattr(self.scanner,'last_scan_stats',{})
        market_closed=bool(scan_stats.get('scan_complete',False)) and int(scan_stats.get('stage1_passed',0))==0
        if market_closed and not self._market_closed_logged:
            self._event('INFO','No tradable symbols: markets appear closed; scan interval extended')
            self._market_closed_logged=True
        elif not market_closed and self._market_closed_logged:
            self._event('INFO','Tradable market symbols are available again')
            self._market_closed_logged=False
        allow_entries=self.consecutive_errors<int(self.live['max_cycle_errors']) and not self.trading_disabled
        for candidate in candidates:
            if self._halt_requested(): return CycleResult(False,0,market_closed)
            self._candidate(candidate,now,allow_entries)
        state=get_account_state(self.client.mt5); positions=self._owned_positions()
        open_by_group=Counter((self.scanner.symbols.get_asset_group(p.symbol) if self.scanner and getattr(self.scanner,'symbols',None) else 'other') for p in positions)
        self._event('INFO',f'Open bot positions by asset group: {dict(open_by_group)}')
        self._daily_stats(state,positions,now)
        if self.monotonic()-self._last_snapshot>=int(self.live['equity_snapshot_seconds']):
            self.db.insert_equity_snapshot(time=now.isoformat(),balance=state.balance,equity=state.equity,margin=state.margin,free_margin=state.free_margin,open_positions=len(positions))
            self._last_snapshot=self.monotonic()
        if not self.trading_disabled: self.last_error=''
        self._set_status('managing_only' if self.trading_disabled else 'running',state.equity)
        return CycleResult(True,60.0 if market_closed else float(self.settings.config['loop']['interval_seconds']),market_closed)
    def _record_error(self,exc):
        self.consecutive_errors+=1; self.last_error=str(exc)[:500]
        self._event('ERROR',f'Cycle {self.cycle_number} failed ({self.consecutive_errors}/{self.live["max_cycle_errors"]}): {self.last_error}')
        if self.consecutive_errors>=int(self.live['max_cycle_errors']):
            self.trading_disabled=True
            if not self._critical_reported:
                self._event('CRITICAL','Maximum consecutive cycle errors reached; new entries disabled, position management continues')
                self._critical_reported=True
            self.exit_reason='error limit reached'
            self.stop_event=True
    def cycle(self):
        self.cycle_number+=1; now=self._now()
        if self._halt_requested(): return CycleResult(False,0)
        try:
            self.client.ensure_connected()
        except Exception as exc:
            self._connection_down=True
            self._record_error(exc)
            try: self._set_status('error')
            except Exception: pass
            idx=min(max(self.consecutive_errors-1,0),len(RECONNECT_BACKOFF)-1)
            return CycleResult(True,RECONNECT_BACKOFF[idx])
        self._connection_down=False
        now=self._now()
        try:
            result=self._connected_cycle(now)
            self.consecutive_errors=0
            return result
        except Exception as exc:
            self._record_error(exc)
            try: self._set_status('error')
            except Exception: pass
            return CycleResult(True,float(self.settings.config['loop']['interval_seconds']))
    def _heartbeat_sleep(self,seconds):
        remaining=float(seconds); heartbeat=max(1,int(self.live['heartbeat_seconds']))
        while remaining>0 and not self.stop_event:
            span=min(remaining,heartbeat); self.sleep_fn(span); remaining-=span
            if not self.stop_event:
                try: self._set_status('error' if self._connection_down or (self.last_error and not self.trading_disabled) else ('managing_only' if self.trading_disabled else 'running'))
                except Exception: pass
    def run_forever(self,max_cycles=None):
        cycles=0; previous_handlers={}
        def request_stop(signum,*_):
            try: label=signal.Signals(signum).name
            except (ValueError,AttributeError): label='process signal'
            self.exit_reason=f'signal {label}'
            self.stop_event=True
            try: self._request_supervisor_stop(self.exit_reason)
            except OSError: pass
        locked=False
        try:
            self.lock.acquire(); locked=True
            for name in ('SIGINT','SIGTERM','SIGBREAK'):
                signum=getattr(signal,name,None)
                if signum is None: continue
                try: previous_handlers[signum]=signal.signal(signum,request_stop)
                except (ValueError,OSError): pass
            while not self.stop_event:
                cycle_started=self.monotonic(); result=self.cycle(); cycles+=1
                if not result.continue_running:
                    self.exit_reason=self.exit_reason or 'bot requested normal stop'
                    break
                if max_cycles is not None and cycles>=max_cycles:
                    self.exit_reason='test cycle limit reached'
                    break
                elapsed=max(0.0,self.monotonic()-cycle_started)
                self._heartbeat_sleep(max(0.0,result.sleep_seconds-elapsed))
        finally:
            for signum,handler in previous_handlers.items():
                try: signal.signal(signum,handler)
                except (ValueError,OSError): pass
            if not self.exit_reason: self.exit_reason='stop event received' if self.stop_event else 'normal loop exit'
            try: self._event('INFO',f'bot exiting reason={self.exit_reason}')
            except Exception: log.exception('Could not persist bot exiting event')
            if locked:
                try:
                    if self.client.mt5 is not None: self.client.close()
                finally:
                    try: self._set_status('stopped')
                    finally: self.lock.release()
