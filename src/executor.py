"""MT5 order execution limited to positions carrying the configured magic."""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
import math
from .models import TradeResult
from .logger import get_logger
from .time_utils import mt5_epoch_to_utc
from . import market_data, indicators as ind
from .risk import calc_volume

log=get_logger(__name__)

class Executor:
    def __init__(self,mt5,settings,db,symbol_service=None):
        self.mt5,self.settings,self.db,self.symbol_service=mt5,settings,db,symbol_service
    def kill_switch_active(self): return (self.settings.root/'STOP').exists()
    def _event(self,message,level='INFO'):
        log.log(getattr(__import__('logging'),level),message)
        self.db.log_event(level,'executor',message)
    def _failure(self,message,volume=0,ticket=None,retcode=None):
        self._event(message,'WARNING'); return TradeResult(False,ticket,None,volume,retcode,message)
    def _asset_group(self,symbol):
        if self.symbol_service: return self.symbol_service.get_asset_group(symbol)
        n=symbol.upper()
        for group,patterns in {'metals':('XAU','XAG','GOLD','SILVER'),'indices':('US30','US100','NAS','SPX','DAX','UK100'),'energy':('OIL','WTI','BRENT','GAS'),'crypto':('BTC','ETH')}.items():
            if any(p in n for p in patterns): return group
        return 'forex' if len(n)>=6 and n[:6].isalpha() else 'other'
    def _filling_mode(self,info):
        m=self.mt5; flags=int(getattr(info,'filling_mode',0) or 0)
        if flags & int(getattr(m,'SYMBOL_FILLING_FOK',1)): return m.ORDER_FILLING_FOK
        if flags & int(getattr(m,'SYMBOL_FILLING_IOC',2)): return m.ORDER_FILLING_IOC
        if getattr(info,'trade_exemode',None)==getattr(m,'SYMBOL_TRADE_EXECUTION_MARKET',2): return None
        return m.ORDER_FILLING_RETURN
    def open_trade(self,signal,volume):
        m=self.mt5
        if self.kill_switch_active(): return self._failure('Refused open: STOP kill switch is active',volume)
        if signal.sl_price is None: return self._failure('Refused open: stop-loss is required',volume)
        if signal.tp_price is None: return self._failure('Refused open: take-profit is required',volume)
        info=m.symbol_info(signal.symbol); tick=m.symbol_info_tick(signal.symbol)
        if info is None or tick is None: return self._failure(f'Symbol or tick unavailable: {m.last_error()}',volume)
        service=self.symbol_service
        if service is None:
            from .symbols import SymbolService
            service=SymbolService(m,self.settings); self.symbol_service=service
        tradable,trade_reason=service.is_tradable(signal.symbol)
        if not tradable: return self._failure(f'Refused open: {trade_reason}',volume)
        if info.trade_mode!=getattr(m,'SYMBOL_TRADE_MODE_FULL',4): return self._failure('Refused open: symbol is not enabled for full trading',volume)
        account=m.account_info()
        if account is None: return self._failure(f'Account info unavailable: {m.last_error()}',volume)
        demo_mode=getattr(m,'ACCOUNT_TRADE_MODE_DEMO',0)
        if account.trade_mode!=demo_mode and (not self.settings.allow_real or self.settings.config['account']['mode']!='real'):
            return self._failure('Refused open: real account requires account.mode=real and ALLOW_REAL=true',volume)
        if account.margin_mode==getattr(m,'ACCOUNT_MARGIN_MODE_RETAIL_NETTING',0):
            existing=m.positions_get(symbol=signal.symbol) or []
            if existing: return self._failure('Refused open: netting account already has a position on this symbol',volume)
        buy=signal.direction=='buy'
        if signal.direction not in ('buy','sell'): return self._failure('Refused open: direction must be buy or sell',volume)
        if buy and not signal.sl_price<tick.ask<signal.tp_price: return self._failure('Refused open: invalid stop/target side for buy',volume)
        if not buy and not signal.tp_price<tick.bid<signal.sl_price: return self._failure('Refused open: invalid stop/target side for sell',volume)
        distance=float(info.trade_stops_level)*float(info.point)
        if distance and (abs((tick.ask if buy else tick.bid)-signal.sl_price)<distance or abs((tick.ask if buy else tick.bid)-signal.tp_price)<distance):
            return self._failure('Refused open: SL/TP inside broker trade_stops_level',volume)
        filling=self._filling_mode(info)
        if filling is None: return self._failure('Refused open: no supported filling mode for market execution',volume)
        price=tick.ask if buy else tick.bid
        minimum=float(getattr(info,'volume_min',0) or 0); step=float(getattr(info,'volume_step',0) or 0); maximum=float(getattr(info,'volume_max',0) or 0)
        if minimum<=0 or step<=0 or maximum<minimum or volume<minimum or volume>maximum or abs((float(volume)-minimum)/step-round((float(volume)-minimum)/step))>1e-7:
            return self._failure('Refused open: volume is outside the broker minimum/step/maximum grid',volume)
        safe_volume,why=calc_volume(float(account.equity),self.settings.risk.risk_per_trade_pct,float(price),signal.sl_price,info._asdict())
        if safe_volume<=0 or float(volume)>safe_volume+1e-9:
            return self._failure(f'Refused open: requested volume exceeds stop-risk size ({why})',volume)
        req={'action':m.TRADE_ACTION_DEAL,'symbol':signal.symbol,'volume':float(volume),'type':m.ORDER_TYPE_BUY if buy else m.ORDER_TYPE_SELL,'price':price,'sl':signal.sl_price,'tp':signal.tp_price,'deviation':self.settings.config['executor']['deviation_points'],'magic':self.settings.magic_number,'comment':signal.strategy_name[:31],'type_time':m.ORDER_TIME_GTC,'type_filling':filling}
        result=m.order_send(req)
        if result and result.retcode in (getattr(m,'TRADE_RETCODE_REQUOTE',10004),getattr(m,'TRADE_RETCODE_PRICE_CHANGED',10020)):
            tick=m.symbol_info_tick(signal.symbol)
            if tick is None: return self._failure(f'Retry tick unavailable: {m.last_error()}',volume,result.retcode)
            req['price']=tick.ask if buy else tick.bid
            result=m.order_send(req)
        if result is None: return self._failure(f'order_send failed: {m.last_error()}',volume)
        if result.retcode!=m.TRADE_RETCODE_DONE: return self._failure(f'order_send rejected ({result.retcode}): {result.comment}',volume,retcode=result.retcode)
        ticket=int(getattr(result,'position',0) or getattr(result,'order',0) or getattr(result,'deal',0))
        now=datetime.now(timezone.utc).isoformat()
        try:
            self.db.insert_trade(ticket=ticket,symbol=signal.symbol,asset_group=self._asset_group(signal.symbol),direction=signal.direction,volume=volume,initial_volume=volume,open_time=now,open_price=result.price,sl=signal.sl_price,tp=signal.tp_price,profit=0,commission=0,swap=0,strategy=signal.strategy_name,reason=signal.reason,magic=self.settings.magic_number,status='open',timeframe=signal.timeframe,initial_risk=abs(float(result.price)-float(signal.sl_price)),scale_out_done=0,peak_favorable_r=0)
        except Exception as exc:
            # The broker position is open; surface the persistence failure loudly for reconciliation.
            self._event(f'CRITICAL: opened ticket {ticket} but could not write trade row: {exc}','ERROR')
        self._event(f'Opened {signal.direction} {signal.symbol} ticket={ticket} volume={volume}')
        return TradeResult(True,ticket,result.price,volume,result.retcode,str(result.comment))
    def close_position(self,ticket,reason):
        m=self.mt5
        if reason not in {'tp','partial_tp','trail','momentum_lost','stagnant','sl','time','session_close','manual','kill'}: return self._failure(f'Refused close: unsupported reason {reason!r}',ticket=ticket)
        p=next((x for x in (m.positions_get() or []) if (int(x.ticket)==int(ticket) or int(getattr(x,'identifier',-1) or -1)==int(ticket)) and int(x.magic)==self.settings.magic_number),None)
        if p is None: return self._failure(f'Refused close: owned position {ticket} not found',ticket=ticket)
        tick=m.symbol_info_tick(p.symbol)
        if tick is None: return self._failure(f'Close tick failed: {m.last_error()}',p.volume,ticket)
        is_buy=p.type==m.POSITION_TYPE_BUY; order_type=m.ORDER_TYPE_SELL if is_buy else m.ORDER_TYPE_BUY; price=tick.bid if is_buy else tick.ask
        info=m.symbol_info(p.symbol); filling=self._filling_mode(info) if info else None
        if filling is None: return self._failure('Refused close: unsupported filling mode',p.volume,ticket)
        req={'action':m.TRADE_ACTION_DEAL,'symbol':p.symbol,'position':p.ticket,'volume':p.volume,'type':order_type,'price':price,'deviation':self.settings.config['executor']['deviation_points'],'magic':self.settings.magic_number,'comment':str(reason)[:31],'type_time':m.ORDER_TIME_GTC,'type_filling':filling}
        result=m.order_send(req)
        if result is None or result.retcode!=m.TRADE_RETCODE_DONE:
            return self._failure(f'Close ticket {ticket} failed: {getattr(result,"comment",m.last_error())}',p.volume,ticket,getattr(result,'retcode',None))
        aliases={int(ticket),int(p.ticket),int(getattr(p,'identifier',p.ticket) or p.ticket)}
        self.sync_positions(close_reasons={key:reason for key in aliases},close_data={key:{'close_price':float(result.price),'profit':float(p.profit),'swap':float(p.swap)} for key in aliases})
        self._event(f'Close accepted ticket={ticket} reason={reason}')
        return TradeResult(True,int(ticket),result.price,p.volume,result.retcode,str(result.comment))
    def close_all(self,reason):
        results=[self.close_position(p.ticket,reason) for p in (self.mt5.positions_get() or []) if int(p.magic)==self.settings.magic_number]
        self._event(f'Close-all requested reason={reason}; positions={len(results)}')
        return results
    def _close_partial(self,p,volume,reason='partial_tp'):
        m=self.mt5; info=m.symbol_info(p.symbol)
        if int(getattr(p,'magic',0))!=self.settings.magic_number: return self._failure('Refused partial close: position is not owned',volume,int(p.ticket))
        if info is None: return self._failure(f'Partial close symbol unavailable: {m.last_error()}',volume,int(p.ticket))
        minimum=float(getattr(info,'volume_min',0) or 0); step=float(getattr(info,'volume_step',0) or 0)
        if minimum<=0 or step<=0 or volume<minimum-1e-9 or volume>float(p.volume)+1e-9 or abs((float(volume)-minimum)/step-round((float(volume)-minimum)/step))>1e-7:
            return self._failure('Refused partial close: volume is outside the open volume or broker minimum/step grid',volume,int(p.ticket))
        tick=m.symbol_info_tick(p.symbol)
        if tick is None: return self._failure(f'Partial close quote unavailable: {m.last_error()}',volume,int(p.ticket))
        buy=p.type==m.POSITION_TYPE_BUY; order_type=m.ORDER_TYPE_SELL if buy else m.ORDER_TYPE_BUY; price=tick.bid if buy else tick.ask
        filling=self._filling_mode(info)
        if filling is None: return self._failure('Refused partial close: unsupported filling mode',volume,int(p.ticket))
        req={'action':m.TRADE_ACTION_DEAL,'symbol':p.symbol,'position':p.ticket,'volume':float(volume),'type':order_type,'price':price,'deviation':self.settings.config['executor']['deviation_points'],'magic':self.settings.magic_number,'comment':reason[:31],'type_time':m.ORDER_TIME_GTC,'type_filling':filling}
        result=m.order_send(req)
        if result is None or result.retcode!=m.TRADE_RETCODE_DONE: return self._failure(f'Partial close ticket {p.ticket} failed: {getattr(result,"comment",m.last_error())}',volume,int(p.ticket),getattr(result,'retcode',None))
        self.sync_positions()
        self.db.update_open_trade(int(p.ticket),scale_out_done=1,volume=max(0.0,float(p.volume)-float(volume)))
        self._event(f'Partial close ticket={p.ticket} volume={volume} reason={reason}')
        return TradeResult(True,int(p.ticket),float(result.price),float(volume),result.retcode,str(result.comment))
    def modify_sl_tp(self,ticket,sl,tp):
        m=self.mt5; p=next((x for x in (m.positions_get() or []) if (int(x.ticket)==int(ticket) or int(getattr(x,'identifier',-1) or -1)==int(ticket)) and int(x.magic)==self.settings.magic_number),None)
        if p is None:
            self._event(f'Refused SL/TP modification: ticket={ticket} is not owned','WARNING'); return False
        if float(sl or 0)<=0 or float(tp or 0)<=0:
            self._event(f'Refused SL/TP modification: ticket={ticket} must retain positive SL and TP','WARNING'); return False
        is_buy=p.type==self.mt5.POSITION_TYPE_BUY; current_sl=float(p.sl or 0)
        if (is_buy and current_sl>0 and float(sl)<current_sl-1e-10) or (not is_buy and current_sl>0 and float(sl)>current_sl+1e-10):
            self._event(f'Refused SL/TP modification: ticket={ticket} would loosen its stop','WARNING'); return False
        tick=self.mt5.symbol_info_tick(p.symbol)
        if tick is None or (is_buy and float(sl)>=float(tick.bid)) or (not is_buy and float(sl)<=float(tick.ask)):
            self._event(f'Refused SL/TP modification: ticket={ticket} stop is not on the protective side of the market','WARNING'); return False
        req={'action':m.TRADE_ACTION_SLTP,'position':ticket,'symbol':p.symbol,'sl':sl,'tp':tp,'magic':self.settings.magic_number}
        result=m.order_send(req); ok=bool(result and result.retcode==m.TRADE_RETCODE_DONE)
        if ok:
            try: self.db.update_open_trade(int(p.ticket),sl=float(sl),tp=float(tp))
            except Exception as exc: self._event(f'Could not persist updated SL/TP for ticket={p.ticket}: {exc}','WARNING')
        self._event(f'Modify SL/TP ticket={ticket} success={ok}'+('' if ok else f' error={getattr(result,"comment",m.last_error())}'), 'INFO' if ok else 'WARNING')
        return ok
    def enforce_time_stop(self,settings=None):
        """Manage scale-outs, protective stops, momentum exits and the safety ceiling."""
        config=(settings or self.settings).risk; now=datetime.now(timezone.utc); actions=[]
        for p in (self.mt5.positions_get() or []):
            if int(p.magic)!=self.settings.magic_number: continue
            row=next((item for item in self.db.get_open_trades() if int(item['ticket']) in {int(p.ticket),int(getattr(p,'identifier',p.ticket) or p.ticket)}),None)
            if row is None: continue
            opened=mt5_epoch_to_utc(p.time,self.mt5); age=(now-opened).total_seconds()/60
            if age>=config.max_hold_minutes: actions.append(self.close_position(p.ticket,'time')); continue
            info=self.mt5.symbol_info(p.symbol); tick=self.mt5.symbol_info_tick(p.symbol)
            if info is None or tick is None: continue
            is_buy=p.type==self.mt5.POSITION_TYPE_BUY; current=float(tick.bid if is_buy else tick.ask); entry=float(p.price_open)
            initial_risk=float(row.get('initial_risk') or abs(entry-float(row.get('sl') or p.sl)))
            if initial_risk<=0: continue
            favorable=(current-entry) if is_buy else (entry-current); current_r=favorable/initial_risk
            peak=max(float(row.get('peak_favorable_r') or 0),current_r)
            self.db.update_open_trade(row['ticket'],peak_favorable_r=peak)
            if not int(row.get('scale_out_done') or 0) and current_r>=config.first_target_r:
                step=float(info.volume_step); minimum=float(info.volume_min)
                desired=float(p.volume)*float(config.scale_out_pct)/100
                partial=math.floor(desired/step+1e-10)*step
                if partial<minimum-1e-9 or float(p.volume)-partial<minimum-1e-9:
                    actions.append(self.close_position(p.ticket,'partial_tp')); continue
                actions.append(self._close_partial(p,partial))
                # Refresh the position after the partial fill before managing its stop.
                refreshed=next((x for x in (self.mt5.positions_get() or []) if int(x.ticket)==int(p.ticket)),None)
                if refreshed: p=refreshed
                row=self.db.get_trade(int(row['ticket'])) or row
            if int(row.get('scale_out_done') or 0):
                protective_sl=float(p.sl or 0)
                try:
                    cost=market_data.get_cost_estimate(self.mt5,p.symbol,float(p.volume))['cost']
                    tick_value=float(info.trade_tick_value or 0); tick_size=float(info.trade_tick_size or 0)
                    cost_distance=(cost*float(config.breakeven_cost_multiplier)/max(float(p.volume),1e-12))*tick_size/tick_value if tick_size>0 and tick_value>0 else 0.0
                    breakeven=entry+cost_distance if is_buy else entry-cost_distance
                    tighter=breakeven>protective_sl if is_buy else (protective_sl==0 or breakeven<protective_sl)
                    stop_ok=breakeven<current if is_buy else breakeven>current
                    if tighter and stop_ok and self.modify_sl_tp(p.ticket,breakeven,float(p.tp or 0)): protective_sl=breakeven
                except Exception as exc:
                    self._event(f'Could not estimate breakeven costs ticket={p.ticket}: {exc}','WARNING')
                try: frame=market_data.get_closed_candles(self.mt5,p.symbol,row.get('timeframe') or 'M5',max(30,int(config.momentum_lookback_bars)+2))
                except Exception as exc:
                    self._event(f'Could not read management candles ticket={p.ticket}: {exc}','WARNING'); frame=None
                if frame is not None and len(frame)>=int(config.momentum_lookback_bars)+1:
                    momentum=float(frame.close.iloc[-1])-float(frame.close.iloc[-1-int(config.momentum_lookback_bars)])
                    if (is_buy and momentum<0) or (not is_buy and momentum>0):
                        actions.append(self.close_position(p.ticket,'momentum_lost')); continue
                atr_frame=frame
                if atr_frame is not None and not atr_frame.empty:
                    atr=float(ind.atr(atr_frame).iloc[-1]); trail_distance=atr*float(config.trail_atr_mult)
                    trail=current-trail_distance if is_buy else current+trail_distance
                    tighter=trail>protective_sl if is_buy else (protective_sl==0 or trail<protective_sl)
                    valid=trail<current if is_buy else trail>current
                    if math.isfinite(trail) and tighter and valid: self.modify_sl_tp(p.ticket,trail,float(p.tp or 0))
            if age>=config.stagnation_minutes and peak<float(config.stagnation_min_r): actions.append(self.close_position(p.ticket,'stagnant'))
        return actions
    def enforce_session_close(self,settings=None,now_utc=None):
        """Close only symbols approaching a broker-observed long session gap."""
        risk=(settings or self.settings).risk; now=now_utc or datetime.now(timezone.utc)
        service=self.symbol_service
        if service is None:
            from .symbols import SymbolService
            service=SymbolService(self.mt5,self.settings)
            self.symbol_service=service
        actions=[]
        for position in (self.mt5.positions_get() or []):
            if int(position.magic)!=self.settings.magic_number: continue
            upcoming=service.next_session_close(position.symbol,now,risk.max_session_gap_hours)
            if not upcoming: continue
            minutes=(upcoming[0]-now).total_seconds()/60
            if 0<=minutes<=risk.no_entry_before_close_minutes:
                actions.append(self.close_position(position.ticket,'session_close'))
        return actions
    def _history(self,ticket):
        try: return list(self.mt5.history_deals_get(position=int(ticket)) or [])
        except Exception:
            try:
                deals=self.mt5.history_deals_get(datetime.now(timezone.utc)-timedelta(days=30),datetime.now(timezone.utc),group='*') or []
                return [deal for deal in deals if int(getattr(deal,'position_id',-1))==int(ticket)]
            except Exception: return []
    def _record_partial_deal(self,row,deal):
        deal_ticket=int(getattr(deal,'ticket',0) or 0)
        reason=str(getattr(deal,'comment','') or '').strip().lower()
        if reason not in {'tp','partial_tp','trail','momentum_lost','stagnant','sl','time','session_close','manual','kill'}:
            reason=self._close_reason([deal],forced='partial_tp')
        self.db.insert_partial_close(deal_ticket=deal_ticket or None,ticket=int(row['ticket']),symbol=row['symbol'],time=mt5_epoch_to_utc(deal.time,self.mt5).isoformat(),volume=float(getattr(deal,'volume',0) or 0),price=float(getattr(deal,'price',0) or 0),profit=float(getattr(deal,'profit',0) or 0),commission=float(getattr(deal,'commission',0) or 0),swap=float(getattr(deal,'swap',0) or 0),reason=reason)
    def _close_reason(self,deals,forced=None,row=None):
        if forced in {'partial_tp','trail','momentum_lost','stagnant','time','session_close','manual','kill'}: return forced
        m=self.mt5
        for deal in reversed(deals):
            reason=getattr(deal,'reason',None)
            if reason==getattr(m,'DEAL_REASON_TP',5): return 'tp'
            if reason==getattr(m,'DEAL_REASON_SL',4):
                if float(getattr(deal,'profit',0) or 0)>0 or self._sl_was_moved(row): return 'trail'
                return 'sl'
        return forced or 'manual'
    @staticmethod
    def _sl_was_moved(row):
        if not row: return False
        try:
            entry=float(row.get('open_price') or 0); risk=float(row.get('initial_risk') or 0); current=float(row.get('sl') or 0)
            if entry<=0 or risk<=0 or current<=0: return False
            original=entry-risk if row.get('direction')=='buy' else entry+risk
            return abs(current-original)>max(1e-9,abs(original)*1e-9)
        except (TypeError,ValueError,AttributeError): return False
    def sync_positions(self,close_reasons=None,close_data=None):
        """Reconcile DB open rows against broker positions and closing deal history."""
        live=set()
        for position in (self.mt5.positions_get() or []):
            if int(position.magic)==self.settings.magic_number:
                live.add(int(position.ticket))
                if getattr(position,'identifier',None): live.add(int(position.identifier))
        reasons=close_reasons or {}; fallbacks=close_data or {}; reconciled=[]
        # Import broker-side positions missed by a prior database write. Manual trades are excluded.
        open_rows=self.db.get_open_trades(); db_open={int(row['ticket']) for row in open_rows}
        for position in (self.mt5.positions_get() or []):
            if int(position.magic)!=self.settings.magic_number: continue
            ticket=int(position.ticket)
            identifier=int(getattr(position,'identifier',ticket))
            if ticket in db_open or identifier in db_open or self.db.get_trade(ticket) or self.db.get_trade(identifier): continue
            opened=mt5_epoch_to_utc(position.time,self.mt5).isoformat()
            direction='buy' if position.type==self.mt5.POSITION_TYPE_BUY else 'sell'
            self.db.insert_trade(ticket=ticket,symbol=position.symbol,asset_group=self._asset_group(position.symbol),direction=direction,volume=position.volume,initial_volume=position.volume,open_time=opened,open_price=position.price_open,sl=position.sl,tp=position.tp,profit=position.profit,commission=0,swap=position.swap,magic=self.settings.magic_number,status='open',strategy='',reason='recovered from broker')
            self._event(f'Recovered missing DB row for owned ticket={ticket}','WARNING')
            db_open.add(ticket)
        current_positions=[p for p in (self.mt5.positions_get() or []) if int(p.magic)==self.settings.magic_number]
        for position in current_positions:
            identifiers={int(position.ticket),int(getattr(position,'identifier',position.ticket) or position.ticket)}
            row=next((item for item in self.db.get_open_trades() if int(item['ticket']) in identifiers),None)
            if row:
                deals=self._history(int(getattr(position,'identifier',position.ticket) or position.ticket))
                closing=[deal for deal in deals if getattr(deal,'entry',None) in (getattr(self.mt5,'DEAL_ENTRY_OUT',1),getattr(self.mt5,'DEAL_ENTRY_OUT_BY',3),getattr(self.mt5,'DEAL_ENTRY_INOUT',2))]
                for deal in closing: self._record_partial_deal(row,deal)
                partial_tickets=self.db.get_partial_deal_tickets(int(row['ticket']))
                open_commission=sum(float(getattr(deal,'commission',0) or 0) for deal in deals if int(getattr(deal,'ticket',0) or 0) not in partial_tickets)
                updates={'profit':float(position.profit),'commission':open_commission,'sl':position.sl,'tp':position.tp,'swap':float(position.swap),'volume':float(position.volume)}
                try:
                    margin=self.mt5.order_calc_margin(position.type,position.symbol,position.volume,position.price_current)
                    if margin is not None: updates['margin_used']=float(margin)
                except Exception: pass
                self.db.update_open_trade(row['ticket'],**updates)
                if closing: self.db.update_open_trade(row['ticket'],scale_out_done=1)
        for row in self.db.get_open_trades():
            ticket=int(row['ticket'])
            forced=ticket in reasons
            if int(row.get('magic') or 0)!=self.settings.magic_number or (ticket in live and not forced): continue
            deals=self._history(ticket)
            if not deals and ticket not in reasons: continue
            closing=[d for d in deals if getattr(d,'entry',None) in (getattr(self.mt5,'DEAL_ENTRY_OUT',1),getattr(self.mt5,'DEAL_ENTRY_OUT_BY',3),getattr(self.mt5,'DEAL_ENTRY_INOUT',2))]
            initial_volume=float(row.get('initial_volume') or row.get('volume') or 0)
            partial_tickets=self.db.get_partial_deal_tickets(ticket)
            partial_volume=sum(float(item.get('volume') or 0) for item in self.db.get_partial_closes(ticket))
            accumulated=partial_volume
            for deal in closing:
                deal_ticket=int(getattr(deal,'ticket',0) or 0); deal_volume=float(getattr(deal,'volume',0) or 0)
                if deal_ticket in partial_tickets: continue
                if initial_volume and accumulated+deal_volume<initial_volume-1e-8:
                    self._record_partial_deal(row,deal)
                    if deal_ticket: partial_tickets.add(deal_ticket)
                    accumulated+=deal_volume
            final_closing=[d for d in closing if int(getattr(d,'ticket',0) or 0) not in partial_tickets]
            source=final_closing or closing or deals
            if source:
                last=source[-1]; close_price=float(last.price); close_time=mt5_epoch_to_utc(last.time,self.mt5).isoformat()
                profit=sum(float(getattr(d,'profit',0) or 0) for d in final_closing)
                commission=sum(float(getattr(d,'commission',0) or 0) for d in deals if int(getattr(d,'ticket',0) or 0) not in partial_tickets)
                swap=sum(float(getattr(d,'swap',0) or 0) for d in deals if int(getattr(d,'ticket',0) or 0) not in partial_tickets)
            else:
                fallback=fallbacks.get(ticket,{})
                close_price=float(fallback.get('close_price',row.get('open_price') or 0)); close_time=datetime.now(timezone.utc).isoformat()
                profit=float(fallback.get('profit',0)); commission=0.0; swap=float(fallback.get('swap',0))
            close_reason=self._close_reason(final_closing,reasons.get(ticket),row)
            self.db.update_trade_close(ticket,close_time=close_time,close_price=close_price,profit=profit,commission=commission,swap=swap,close_reason=close_reason)
            self._event(f'Synced closed ticket={ticket} reason={close_reason} profit={profit}')
            reconciled.append(ticket)
        return reconciled
