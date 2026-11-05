from datetime import datetime, timezone, timedelta
import logging
from .models import TradeResult
from .logger import get_logger

log = get_logger(__name__)

class Executor:
    def __init__(self, mt5, settings, db): self.mt5, self.settings, self.db = mt5, settings, db
    def kill_switch_active(self): return (self.settings.root / 'STOP').exists()
    def _event(self, message):
        log.info(message); self.db.log_event('INFO','executor',message)
    def open_trade(self, signal, volume):
        m=self.mt5
        if self.kill_switch_active(): return TradeResult(False,None,None,volume,None,'kill switch active')
        if signal.sl_price is None or signal.tp_price is None: return TradeResult(False,None,None,volume,None,'SL and TP required')
        info=m.symbol_info(signal.symbol); tick=m.symbol_info_tick(signal.symbol)
        if info is None or tick is None: return TradeResult(False,None,None,volume,None,f'Missing symbol/tick: {m.last_error()}')
        buy=signal.direction=='buy'; price=tick.ask if buy else tick.bid
        min_dist=info.trade_stops_level*info.point
        if min_dist and (abs(price-signal.sl_price)<min_dist or abs(price-signal.tp_price)<min_dist): return TradeResult(False,None,None,volume,None,'SL/TP inside broker stop level')
        req={'action':m.TRADE_ACTION_DEAL,'symbol':signal.symbol,'volume':volume,'type':m.ORDER_TYPE_BUY if buy else m.ORDER_TYPE_SELL,'price':price,'sl':signal.sl_price,'tp':signal.tp_price,'deviation':20,'magic':self.settings.magic_number,'comment':signal.strategy_name[:31],'type_time':m.ORDER_TIME_GTC,'type_filling':getattr(m,'ORDER_FILLING_IOC',1)}
        r=m.order_send(req)
        if r and r.retcode in (getattr(m,'TRADE_RETCODE_REQUOTE',10004),getattr(m,'TRADE_RETCODE_PRICE_CHANGED',10020)):
            tick=m.symbol_info_tick(signal.symbol); req['price']=tick.ask if buy else tick.bid; r=m.order_send(req)
        if not r or r.retcode!=m.TRADE_RETCODE_DONE: return TradeResult(False,None,None,volume,getattr(r,'retcode',None),str(getattr(r,'comment',m.last_error())))
        ticket=int(getattr(r,'order',0) or getattr(r,'deal',0)); now=datetime.now(timezone.utc).isoformat()
        self.db.insert_trade(ticket=ticket,symbol=signal.symbol,asset_group='other',direction=signal.direction,volume=volume,open_time=now,open_price=r.price,sl=signal.sl_price,tp=signal.tp_price,profit=0,commission=0,swap=0,strategy=signal.strategy_name,reason=signal.reason,magic=self.settings.magic_number,status='open')
        self._event(f'Opened {signal.symbol}, ticket {ticket}')
        return TradeResult(True,ticket,r.price,volume,r.retcode,str(r.comment))
    def close_position(self,ticket,reason):
        m=self.mt5; p=next((x for x in (m.positions_get() or []) if x.ticket==ticket and x.magic==self.settings.magic_number),None)
        if p is None: return TradeResult(False,ticket,None,0,None,'owned position not found')
        tick=m.symbol_info_tick(p.symbol); buy=p.type==m.POSITION_TYPE_BUY; typ=m.ORDER_TYPE_SELL if buy else m.ORDER_TYPE_BUY; price=tick.bid if buy else tick.ask
        r=m.order_send({'action':m.TRADE_ACTION_DEAL,'symbol':p.symbol,'position':p.ticket,'volume':p.volume,'type':typ,'price':price,'deviation':20,'magic':self.settings.magic_number,'comment':reason[:31],'type_time':m.ORDER_TIME_GTC,'type_filling':getattr(m,'ORDER_FILLING_IOC',1)})
        if not r or r.retcode!=m.TRADE_RETCODE_DONE: return TradeResult(False,ticket,None,p.volume,getattr(r,'retcode',None),str(getattr(r,'comment',m.last_error())))
        self.db.update_trade_close(ticket,close_time=datetime.now(timezone.utc).isoformat(),close_price=r.price,profit=p.profit,commission=0,swap=p.swap,close_reason=reason); self._event(f'Closed ticket {ticket}: {reason}')
        return TradeResult(True,ticket,r.price,p.volume,r.retcode,str(r.comment))
    def close_all(self,reason): return [self.close_position(p.ticket,reason) for p in (self.mt5.positions_get() or []) if p.magic==self.settings.magic_number]
    def modify_sl_tp(self,ticket,sl,tp):
        m=self.mt5; p=next((x for x in (m.positions_get() or []) if x.ticket==ticket and x.magic==self.settings.magic_number),None)
        if p is None: return False
        r=m.order_send({'action':m.TRADE_ACTION_SLTP,'position':ticket,'symbol':p.symbol,'sl':sl,'tp':tp,'magic':self.settings.magic_number})
        return bool(r and r.retcode==m.TRADE_RETCODE_DONE)
    def enforce_time_stop(self,settings=None):
        limit=(settings or self.settings).risk['max_hold_minutes']; now=datetime.now(timezone.utc)
        for p in (self.mt5.positions_get() or []):
            if p.magic==self.settings.magic_number and now-datetime.fromtimestamp(p.time,timezone.utc)>timedelta(minutes=limit): self.close_position(p.ticket,'time')
    def enforce_weekend_close(self,settings=None,now_utc=None):
        risk=(settings or self.settings).risk; now=now_utc or datetime.now(timezone.utc)
        if now.weekday()==4 and now.strftime('%H:%M')>=risk['close_all_friday_utc']: self.close_all('weekend')
    def sync_positions(self): return self.db.get_open_trades()
