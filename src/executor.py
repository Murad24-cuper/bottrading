"""MT5 order execution limited to positions carrying the configured magic."""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from .models import TradeResult
from .logger import get_logger

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
        if info.trade_mode!=getattr(m,'SYMBOL_TRADE_MODE_FULL',4): return self._failure('Refused open: symbol is not enabled for full trading',volume)
        account=m.account_info()
        if account and account.margin_mode==getattr(m,'ACCOUNT_MARGIN_MODE_RETAIL_NETTING',0):
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
            self.db.insert_trade(ticket=ticket,symbol=signal.symbol,asset_group=self._asset_group(signal.symbol),direction=signal.direction,volume=volume,open_time=now,open_price=result.price,sl=signal.sl_price,tp=signal.tp_price,profit=0,commission=0,swap=0,strategy=signal.strategy_name,reason=signal.reason,magic=self.settings.magic_number,status='open')
        except Exception as exc:
            # The broker position is open; surface the persistence failure loudly for reconciliation.
            self._event(f'CRITICAL: opened ticket {ticket} but could not write trade row: {exc}','ERROR')
        self._event(f'Opened {signal.direction} {signal.symbol} ticket={ticket} volume={volume}')
        return TradeResult(True,ticket,result.price,volume,result.retcode,str(result.comment))
    def close_position(self,ticket,reason):
        m=self.mt5
        if reason not in {'tp','sl','time','manual','kill','weekend','error'}: return self._failure(f'Refused close: unsupported reason {reason!r}',ticket=ticket)
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
    def modify_sl_tp(self,ticket,sl,tp):
        m=self.mt5; p=next((x for x in (m.positions_get() or []) if (int(x.ticket)==int(ticket) or int(getattr(x,'identifier',-1) or -1)==int(ticket)) and int(x.magic)==self.settings.magic_number),None)
        if p is None:
            self._event(f'Refused SL/TP modification: ticket={ticket} is not owned','WARNING'); return False
        req={'action':m.TRADE_ACTION_SLTP,'position':ticket,'symbol':p.symbol,'sl':sl,'tp':tp,'magic':self.settings.magic_number}
        result=m.order_send(req); ok=bool(result and result.retcode==m.TRADE_RETCODE_DONE)
        self._event(f'Modify SL/TP ticket={ticket} success={ok}'+('' if ok else f' error={getattr(result,"comment",m.last_error())}'), 'INFO' if ok else 'WARNING')
        return ok
    def enforce_time_stop(self,settings=None):
        limit=(settings or self.settings).risk.max_hold_minutes; now=datetime.now(timezone.utc); closed=[]
        for p in (self.mt5.positions_get() or []):
            if int(p.magic)==self.settings.magic_number and now-datetime.fromtimestamp(p.time,timezone.utc)>timedelta(minutes=limit): closed.append(self.close_position(p.ticket,'time'))
        return closed
    def enforce_weekend_close(self,settings=None,now_utc=None):
        risk=(settings or self.settings).risk; now=now_utc or datetime.now(timezone.utc)
        if now.weekday()==4 and now.strftime('%H:%M')>=risk.close_all_friday_utc: return self.close_all('weekend')
        return []
    def _history(self,ticket):
        try: return list(self.mt5.history_deals_get(position=int(ticket)) or [])
        except Exception:
            try:
                deals=self.mt5.history_deals_get(datetime.now(timezone.utc)-timedelta(days=30),datetime.now(timezone.utc),group='*') or []
                return [deal for deal in deals if int(getattr(deal,'position_id',-1))==int(ticket)]
            except Exception: return []
    def _close_reason(self,deals,forced=None):
        if forced in {'time','manual','kill','weekend','error'}: return forced
        m=self.mt5
        for deal in reversed(deals):
            reason=getattr(deal,'reason',None)
            if reason==getattr(m,'DEAL_REASON_TP',5): return 'tp'
            if reason==getattr(m,'DEAL_REASON_SL',4): return 'sl'
        return forced or 'manual'
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
            opened=datetime.fromtimestamp(position.time,timezone.utc).isoformat()
            direction='buy' if position.type==self.mt5.POSITION_TYPE_BUY else 'sell'
            self.db.insert_trade(ticket=ticket,symbol=position.symbol,asset_group=self._asset_group(position.symbol),direction=direction,volume=position.volume,open_time=opened,open_price=position.price_open,sl=position.sl,tp=position.tp,profit=position.profit,commission=0,swap=position.swap,magic=self.settings.magic_number,status='open',strategy='',reason='recovered from broker')
            self._event(f'Recovered missing DB row for owned ticket={ticket}','WARNING')
            db_open.add(ticket)
        for row in self.db.get_open_trades():
            ticket=int(row['ticket'])
            forced=ticket in reasons
            if int(row.get('magic') or 0)!=self.settings.magic_number or (ticket in live and not forced): continue
            deals=self._history(ticket)
            if not deals and ticket not in reasons: continue
            closing=[d for d in deals if getattr(d,'entry',None) in (getattr(self.mt5,'DEAL_ENTRY_OUT',1),getattr(self.mt5,'DEAL_ENTRY_OUT_BY',3),getattr(self.mt5,'DEAL_ENTRY_INOUT',2))]
            source=closing or deals
            if source:
                last=source[-1]; close_price=float(last.price); close_time=datetime.fromtimestamp(last.time,timezone.utc).isoformat()
                profit=sum(float(getattr(d,'profit',0) or 0) for d in source)
                commission=sum(float(getattr(d,'commission',0) or 0) for d in deals)
                swap=sum(float(getattr(d,'swap',0) or 0) for d in deals)
            else:
                fallback=fallbacks.get(ticket,{})
                close_price=float(fallback.get('close_price',row.get('open_price') or 0)); close_time=datetime.now(timezone.utc).isoformat()
                profit=float(fallback.get('profit',0)); commission=0.0; swap=float(fallback.get('swap',0))
            close_reason=self._close_reason(source,reasons.get(ticket))
            self.db.update_trade_close(ticket,close_time=close_time,close_price=close_price,profit=profit,commission=commission,swap=swap,close_reason=close_reason)
            self._event(f'Synced closed ticket={ticket} reason={close_reason} profit={profit}')
            reconciled.append(ticket)
        return reconciled
