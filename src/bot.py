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
from .time_utils import mt5_epoch_to_utc, server_clock_drift_seconds
from .notify import TelegramNotifier

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
        data_dir=getattr(settings,'data_dir',settings.root/'data')
        self.stop_event=False; self._connection_down=False; self.lock=BotLock(data_dir/'bot.lock')
        self._stop_after_cycle=False
        self._cycle_reservations=[]
        self.exit_reason=''
        cfg=settings.config
        notify_cfg=cfg.get('notify',{})
        self.notifier=TelegramNotifier(rate_limit_minutes=notify_cfg.get('rate_limit_minutes',5))
        self._health_failures=0; self._entries_health_blocked=False; self._trade_allowed=False; self._last_daily_summary=''; self._last_maintenance_day=''
        self._data_dir=data_dir; self._brain_drift_checked=0.0
        self._last_notified_trade_id=self.db.latest_trade_id() if hasattr(self.db,'latest_trade_id') else 0
        self._observed_utc_day=self._now().date()-timedelta(days=1)
        self._daily_limit_alert_day=''; self._weekly_limit_alert_week=''
        self._clock_checked=False
    @property
    def live(self): return self.settings.config['live']
    def _now(self):
        value=self.clock()
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    def _set_status(self,status='running',equity=None):
        stats=getattr(self.scanner,'last_scan_stats',{}) if self.scanner else {}
        self.db.upsert_bot_status(time=self._now().isoformat(),cycle=self.cycle_number,mode=self.live['mode'],status=status,account_type=self._last_account_type,equity=equity,last_error=self.last_error,mt5_connected=int(not self._connection_down),trade_allowed=int(self._trade_allowed),scan_total=stats.get('total_symbols',0),scan_scanned=stats.get('symbols_scanned',0),scan_complete=int(bool(stats.get('scan_complete',False))),scan_stage1_passed=stats.get('stage1_passed',0),scan_top_n=stats.get('top_movers',0),scan_signals=stats.get('signals',0),scan_seconds=stats.get('scan_seconds',0),scan_rejections=json.dumps(stats.get('stage1_rejections',{}),sort_keys=True),strategy_diagnostics=json.dumps(stats.get('strategy_diagnostics',{}),sort_keys=True))
    def _event(self,level,message):
        log.log(getattr(logging,level.upper(),logging.INFO),message)
        self.db.log_event(level.upper(),'bot',message)
    def _notify(self,event_type,message):
        try: self.notifier.send(event_type,message)
        except Exception as exc: log.warning('Telegram notification queue failed: %s',exc)
    def _check_brain_drift(self):
        brain=self.settings.config.get('brain',{})
        if not brain.get('enabled',False) or self.monotonic()-self._brain_drift_checked<60: return
        self._brain_drift_checked=self.monotonic()
        from .brain.drift import assess_live_drift
        rows=self.db.get_recent_brain_outcomes(int(brain.get('live_drift_window',100)),self.settings.magic_number)
        result=assess_live_drift(rows,int(brain.get('live_drift_window',100)),float(brain.get('live_max_calibration_error',.1)),float(brain.get('live_min_expectancy_r',0)))
        if not result['trigger']: return
        brain['enabled']=False; brain['shadow']=True
        path=self._data_dir/'brain'/'live_gate.json'; path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps({'mode':'shadow','checked_at':self._now().isoformat(),'result':result},ensure_ascii=False,indent=2),encoding='utf-8')
        message='Brain live rejimindən müşahidə rejiminə keçirildi: '+', '.join(result['reasons'])
        self._event('CRITICAL',message); self._notify('brain_drift',message)
    def _health(self,now):
        """Check terminal permissions and stale ticks before evaluating entries."""
        mt5=self.client.mt5
        try: terminal=mt5.terminal_info() if hasattr(mt5,'terminal_info') else None
        except Exception: terminal=None
        connected=bool(getattr(terminal,'connected',True)) if terminal is not None else not hasattr(mt5,'terminal_info')
        trade_allowed=bool(getattr(terminal,'trade_allowed',False)) if terminal is not None else not hasattr(mt5,'terminal_info')
        self._trade_allowed=trade_allowed
        self._connection_down=not connected
        if not connected:
            self._health_failures+=1
            self._connection_down=True
            if self._health_failures==1: self._notify('mt5_disconnected','🔴 MT5 ilə əlaqə kəsildi; yeni əməliyyatlar dayandırıldı.')
            try: self.client.ensure_connected()
            except Exception as exc:
                if self._health_failures>=int(self.settings.config.get('health',{}).get('reconnect_failures_before_pause',3)):
                    self._entries_health_blocked=True
                    self._event('CRITICAL',f'MT5 əlaqəsi {self._health_failures} dəfə bərpa olunmadı; yeni əməliyyatlar sağlamlıq bərpa edilənədək bloklandı: {exc}')
                return False
            terminal=mt5.terminal_info(); connected=bool(terminal and getattr(terminal,'connected',True)); trade_allowed=bool(terminal and getattr(terminal,'trade_allowed',False))
            self._trade_allowed=trade_allowed
            self._connection_down=not connected
            if not connected and self._health_failures>=int(self.settings.config.get('health',{}).get('reconnect_failures_before_pause',3)) and not self._entries_health_blocked:
                self._entries_health_blocked=True
                self._event('CRITICAL',f'MT5 bağlantısı {self._health_failures} bərpa cəhdindən sonra yoxdur; yeni əməliyyatlar bloklandı')
                self._notify('mt5_reconnect_critical','🚨 MT5 bağlantısı üç dəfə bərpa olunmadı; yeni əməliyyatlar bağlantı bərpa edilənədək bloklandı.')
        stale_limit=int(self.settings.config.get('health',{}).get('stale_ticks_seconds',120))
        positions=self._owned_positions() if hasattr(mt5,'positions_get') else []
        stale=[]
        if connected:
            for position in positions:
                try:
                    mt5.symbol_select(position.symbol,True)
                    tick=mt5.symbol_info_tick(position.symbol)
                    stamp=getattr(tick,'time_msc',0)/1000 if tick and getattr(tick,'time_msc',0) else getattr(tick,'time',0) if tick else 0
                    tick_age=(now-mt5_epoch_to_utc(stamp,mt5)).total_seconds() if stamp else float('inf')
                    if tick_age>stale_limit:
                        service=getattr(self.scanner,'symbols',None)
                        market_open=service.market_should_be_open(position.symbol,now) if service and hasattr(service,'market_should_be_open') else True
                        if market_open: stale.append(position.symbol)
                except Exception: stale.append(position.symbol)
        if connected and stale:
            self._health_failures+=1
            try:
                self.client.close(); self.client.ensure_connected()
                terminal=mt5.terminal_info(); connected=bool(terminal and getattr(terminal,'connected',True))
                if not connected: raise RuntimeError('terminal remains disconnected after reconnect')
                still_stale=[]
                for symbol in stale:
                    tick=mt5.symbol_info_tick(symbol)
                    stamp=getattr(tick,'time_msc',0)/1000 if tick and getattr(tick,'time_msc',0) else getattr(tick,'time',0) if tick else 0
                    if not stamp or (now-mt5_epoch_to_utc(stamp,mt5)).total_seconds()>stale_limit: still_stale.append(symbol)
                if still_stale: raise RuntimeError('ticks remain stale for '+', '.join(still_stale))
            except Exception as exc:
                if self._health_failures>=int(self.settings.config.get('health',{}).get('reconnect_failures_before_pause',3)):
                    self._entries_health_blocked=True
                    self._event('CRITICAL',f'MT5 qiymətləri köhnə qaldı; {self._health_failures} bərpa cəhdi uğursuz oldu: {exc}')
                    self._notify('mt5_stale_critical','🚨 MT5 qiymət axını üç bərpa cəhdindən sonra da yenilənmədi; yeni əməliyyatlar bloklandı.')
            return False
        if connected and not stale:
            if self._connection_down or self._health_failures:
                self._notify('mt5_reconnected','🟢 MT5 bağlantısı bərpa olundu.')
                self._event('INFO','MT5 bağlantısı və qiymət axını bərpa olundu.')
            self._health_failures=0; self._connection_down=False; self._entries_health_blocked=False
        if not trade_allowed:
            self._notify('trading_disallowed','⚠️ MT5 terminalında avtomatik ticarət icazəsi bağlıdır; yeni əməliyyatlar açılmır.')
            self._event('WARNING','MT5 trade_allowed=false; new entries disabled')
        return connected and trade_allowed and not stale and not self._entries_health_blocked
    def _request_supervisor_stop(self,reason):
        self.exit_reason=str(reason)
        path=getattr(self.settings,'data_dir',self.settings.root/'data')/'supervisor.stop'
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
        self._notify('started',f"🟢 Bot başladı · rejim: {self.live['mode']} · hesab: {self._last_account_type} · kapital: {state.equity:.2f} $")
        self._started=True
    def _check_clock(self,now):
        if self._clock_checked: return
        self._clock_checked=True
        try:
            service=getattr(self.scanner,'symbols',None)
            symbol=service.resolve_alias('EURUSD') if service and hasattr(service,'resolve_alias') else 'EURUSD'
            if not symbol: return
            mt5=self.client.mt5; tick=mt5.symbol_info_tick(symbol); stamp=getattr(tick,'time_msc',0)/1000 if tick and getattr(tick,'time_msc',0) else getattr(tick,'time',0) if tick else 0
            if not stamp: return
            age=(now-mt5_epoch_to_utc(stamp,mt5)).total_seconds()
            if age>int(self.settings.config.get('health',{}).get('stale_ticks_seconds',120)): return
            drift=server_clock_drift_seconds(mt5,symbol,now)
            if drift is not None and drift>30:
                self._event('WARNING',f'PC UTC saatı MT5 server vaxtından təxminən {drift:.0f} saniyə fərqlənir')
                self._notify('clock_drift','⚠️ Kompüterin UTC saatı MT5 vaxtı ilə 30 saniyədən çox fərqlənir.')
        except Exception as exc: self._event('WARNING',f'Saat uyğunluğu yoxlanıla bilmədi: {exc}')
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
        elif self._entries_health_blocked or not self._trade_allowed: reason='MT5 health or algorithmic trading permission blocks new entries'
        elif not allow_entries: reason='new trades disabled after cycle errors'
        else: reason=''
        if reason:
            self._signal_update(candidate,False,reason); return False
        from .confluence import apply_confluence
        signal=candidate.signal
        allowed,confluence_reason,adjusted_confidence=apply_confluence(getattr(candidate,'features',{}),signal.direction,signal.confidence,self.settings.config.get('confluence',{}))
        if not allowed:
            self._signal_update(candidate,False,confluence_reason); return False
        if adjusted_confidence!=signal.confidence:
            signal.confidence=adjusted_confidence; candidate.confidence=adjusted_confidence
            if candidate.signal_row_id is not None:
                with self.db.connect() as connection: connection.execute('UPDATE signals SET confidence=? WHERE id=?',(adjusted_confidence,candidate.signal_row_id))
        state=get_account_state(self.client.mt5); positions=self._owned_positions()
        spec=candidate.symbol_spec
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
        day_start=now.replace(hour=0,minute=0,second=0,microsecond=0)
        cooldown_active=self.db.underlying_closed_since(candidate.symbol,now-timedelta(minutes=self.settings.risk.symbol_cooldown_minutes),self.settings.magic_number) if hasattr(self.db,'underlying_closed_since') else self.db.symbol_closed_since(candidate.symbol,now-timedelta(minutes=self.settings.risk.symbol_cooldown_minutes),self.settings.magic_number)
        symbol_trades_today=self.db.count_underlying_trades_since(candidate.symbol,day_start,self.settings.magic_number) if hasattr(self.db,'count_underlying_trades_since') else self.db.count_symbol_trades_since(candidate.symbol,day_start,self.settings.magic_number)
        session_closing=False
        if service and hasattr(service,'next_session_close'):
            upcoming=service.next_session_close(candidate.symbol,now,0.0)
            session_closing=bool(upcoming and 0<=(upcoming[0]-now).total_seconds()/60<=self.settings.risk.no_entry_before_close_minutes)
        trades_today=self.db.count_trades_since(day_start,self.settings.magic_number)+len(self._cycle_reservations)
        group_trades_today=(self.db.count_group_trades_since(day_start,candidate.asset_group,self.settings.magic_number) if hasattr(self.db,'count_group_trades_since') else 0)+sum(r['position'].get('asset_group')==candidate.asset_group for r in self._cycle_reservations)
        allowed,why=check_trade_allowed(signal,state,open_positions,pnl_today,pnl_week,self.settings,candidate.cost,candidate.asset_group,now,margin+reserved_margin,volume,spec,cooldown_active,symbol_trades_today,session_closing,trades_today,group_trades_today)
        if not allowed:
            if why=='daily loss limit reached': self._notify('daily_loss','🛑 Gündəlik zərər limiti doldu; yeni əməliyyatlar dayandırıldı.')
            if why=='weekly loss limit reached': self._notify('weekly_loss','🛑 Həftəlik zərər limiti doldu; yeni əməliyyatlar dayandırıldı.')
            self._signal_update(candidate,False,why); return False
        result=self.executor.open_trade(signal,volume,expected_cost=candidate.cost,features=getattr(candidate,'features',{}))
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
    def _notify_closed_losses(self):
        if not hasattr(self.db,'get_closed_trades_after_id'): return
        threshold=float(self.settings.config.get('notify',{}).get('big_loss_usd',5))
        for row in self.db.get_closed_trades_after_id(self._last_notified_trade_id):
            self._last_notified_trade_id=max(self._last_notified_trade_id,int(row['id']))
            net=float(row.get('profit') or 0)+float(row.get('commission') or 0)+float(row.get('swap') or 0)
            if net<=-threshold:
                self._notify('big_trade_loss',f'⚠️ Böyük zərər: {row["symbol"]} · {row["direction"]} · {net:.2f} $.')
    def _daily_summary(self,now):
        target=self.settings.config.get('notify',{}).get('daily_summary_utc','21:00')
        if now.strftime('%H:%M')<target or self._last_daily_summary==now.date().isoformat(): return
        day=now.date().isoformat(); rows=self.db.get_closed_trades_for_day(day)
        nets=[float(r.get('profit') or 0)+float(r.get('commission') or 0)+float(r.get('swap') or 0) for r in rows]
        wins=[x for x in nets if x>0]; losses=[x for x in nets if x<0]
        best=max(nets,default=0); worst=min(nets,default=0)
        stats=self.db.get_daily_stats(day) or {}
        message=(f'📊 Günlük yekun · balans: {float(stats.get("end_balance") or 0):.2f} $ · '
                 f'nəticə: {float(stats.get("pnl") or 0):+.2f} $ · əməliyyat: {len(rows)} · '
                 f'qazanma: {len(wins)/len(nets):.1%}' if nets else '📊 Günlük yekun · əməliyyat yoxdur.')
        if nets: message+=f' · orta qazanc: {sum(wins)/len(wins):.2f} $ · orta zərər: {sum(losses)/len(losses):.2f} $' if losses else f' · orta qazanc: {sum(wins)/len(wins):.2f} $ · orta zərər: 0.00 $'
        message+=f' · ən yaxşı: {best:+.2f} $ · ən zəif: {worst:+.2f} $'
        self._notify('daily_summary',message); self._last_daily_summary=day
    def _daily_maintenance(self,now):
        day=now.date().isoformat()
        if self._last_maintenance_day==day or self.db.maintenance_done('daily',day):
            self._last_maintenance_day=day; return
        cfg=self.settings.config.get('db',{})
        self.db.maintain(now,cfg.get('signals_retention_days',7),cfg.get('events_retention_days',30),cfg.get('equity_retention_days',30),cfg.get('equity_downsample_minutes',5))
        backups=getattr(self.settings,'data_dir',self.settings.root/'data')/'backups'
        self.db.backup(backups/f'bot_{day.replace("-","")}.db')
        keep=int(cfg.get('backup_keep_days',14))
        files=sorted(backups.glob('bot_????????.db'))
        for old in files[:-keep]: old.unlink(missing_ok=True)
        self.db.mark_maintenance_done('daily',day,now)
        self._last_maintenance_day=day
    def _daily_rollover_report(self,now):
        if now.date()<=self._observed_utc_day: return
        previous=self._observed_utc_day.isoformat(); stats=self.db.get_daily_stats(previous)
        if stats: self.db.save_daily_report(previous,stats,now.isoformat())
        self._observed_utc_day=now.date()
    def _connected_cycle(self,now):
        self._cycle_reservations=[]
        self._components(); account=self._account_type(); state=get_account_state(self.client.mt5); self._startup(state)
        self._check_clock(now)
        health_ok=self._health(now)
        self.executor.sync_positions(); getattr(self.executor,'enforce_adverse_move_exit',lambda *_:None)(self.settings); self.executor.enforce_time_stop(self.settings); self.executor.enforce_session_close(self.settings,now)
        self._notify_closed_losses()
        pnl_today,pnl_week=self._pnl_periods(now)
        open_rows={int(row['ticket']):row for row in self.db.get_open_trades()}
        floating=sum(float(p.profit)+float(getattr(p,'swap',0) or 0)+float(open_rows.get(int(p.ticket),{}).get('commission') or 0) for p in self._owned_positions())
        if pnl_today+floating<=-float(state.balance)*float(self.settings.config['risk']['daily_loss_limit_pct'])/100 and self._daily_limit_alert_day!=now.date().isoformat():
            self._notify('daily_loss','🛑 Gündəlik zərər limiti doldu; yeni əməliyyatlar dayandırıldı.'); self._daily_limit_alert_day=now.date().isoformat()
        week_key=(now-timedelta(days=now.weekday())).date().isoformat()
        if pnl_week+floating<=-float(state.balance)*float(self.settings.config['risk']['weekly_loss_limit_pct'])/100 and self._weekly_limit_alert_week!=week_key:
            self._notify('weekly_loss','🛑 Həftəlik zərər limiti doldu; yeni əməliyyatlar dayandırıldı.'); self._weekly_limit_alert_week=week_key
        risk_cfg=self.settings.config['risk']
        self._check_brain_drift()
        if hasattr(self.db,'refresh_adaptive_gates'):
            disabled=self.db.refresh_adaptive_gates(risk_cfg.get('gating_window',20),risk_cfg.get('gating_disable_hours',24),self.settings.magic_number,now)
            for gate in disabled: self._notify(f'adaptive_{gate["scope"]}_{gate["name"]}',f'⚠️ {gate["scope"]}: {gate["name"]} strategiyası/qrupu mənfi nəticəyə görə 24 saat söndürüldü.')
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
        allow_entries=health_ok and self.consecutive_errors<int(self.live['max_cycle_errors']) and not self.trading_disabled
        week_start=week_key
        weekly=self.db.get_or_create_week_start(week_start,state.balance)
        weekly_limit=float(weekly['start_balance'])*(1-float(risk_cfg['weekly_loss_limit_pct'])/100)
        if float(state.equity)<=weekly_limit and not int(weekly.get('stopped') or 0):
            self.executor.close_all('weekly_stop'); self.db.mark_week_stopped(week_start)
            self._notify('weekly_drawdown_stop','🛑 Həftəlik kapital limiti aşıldı; bot mövqeləri bağladı və dayandı.')
            self._event('CRITICAL',f'Weekly drawdown stop reached: equity={state.equity:.2f}, week_start_balance={weekly["start_balance"]:.2f}')
            self._request_supervisor_stop('weekly drawdown stop'); self.stop_event=True
            self._set_status('stopped',state.equity); return CycleResult(False,0)
        for candidate in candidates:
            if self._halt_requested(): return CycleResult(False,0,market_closed)
            self._candidate(candidate,now,allow_entries)
        state=get_account_state(self.client.mt5); positions=self._owned_positions()
        open_by_group=Counter((self.scanner.symbols.get_asset_group(p.symbol) if self.scanner and getattr(self.scanner,'symbols',None) else 'other') for p in positions)
        self._event('INFO',f'Open bot positions by asset group: {dict(open_by_group)}')
        self._daily_stats(state,positions,now)
        self._daily_rollover_report(now)
        self._daily_maintenance(now)
        self._daily_summary(now)
        vacuum_key=now.strftime('%G-W%V')
        db_cfg=self.settings.config.get('db',{})
        if now.weekday()==int(db_cfg.get('vacuum_weekday_utc',6)) and not positions and not self.db.maintenance_done('vacuum',vacuum_key):
            self.db.vacuum(); self.db.mark_maintenance_done('vacuum',vacuum_key,now)
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
            self._health_failures+=1
            threshold=int(self.settings.config.get('health',{}).get('reconnect_failures_before_pause',3))
            if self._health_failures>=threshold and not self._entries_health_blocked:
                self._entries_health_blocked=True
                self._event('CRITICAL',f'MT5 bağlantısı {self._health_failures} bərpa cəhdindən sonra yoxdur; yeni əməliyyatlar bloklandı: {exc}')
                self._notify('mt5_reconnect_critical','🚨 MT5 bağlantısı üç dəfə bərpa olunmadı; yeni əməliyyatlar bağlantı bərpa edilənədək bloklandı.')
            self._record_error(exc)
            try: self._set_status('error')
            except Exception: pass
            idx=min(max(self.consecutive_errors-1,0),len(RECONNECT_BACKOFF)-1)
            return CycleResult(True,RECONNECT_BACKOFF[idx])
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
            self._notify('stopped',f'🔴 Bot dayandı · səbəb: {self.exit_reason}')
            if locked:
                try:
                    if self.client.mt5 is not None: self.client.close()
                finally:
                    try: self._set_status('stopped')
                    finally: self.lock.release()
            try: self.notifier.flush()
            except Exception: log.exception('Telegram bildirişləri dayandırılarkən tamamlanmadı')
