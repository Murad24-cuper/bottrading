"""Pure position sizing and risk gates; this module never calls MT5."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime

def calc_volume(equity: float, risk_pct: float, entry: float, sl: float, symbol_spec: dict) -> tuple[float,str]:
    """Size from stop risk and round down to the broker volume step."""
    distance=abs(float(entry)-float(sl))
    tick_value=float(symbol_spec.get('trade_tick_value_loss') or symbol_spec.get('trade_tick_value') or symbol_spec.get('tick_value') or 0)
    tick_size=float(symbol_spec.get('trade_tick_size') or symbol_spec.get('tick_size') or 0)
    minimum=float(symbol_spec.get('volume_min') or 0); step=float(symbol_spec.get('volume_step') or 0); maximum=float(symbol_spec.get('volume_max') or 0)
    if distance<=0 or tick_value<=0 or tick_size<=0: return 0,'invalid stop or tick specification'
    if equity<=0 or risk_pct<=0: return 0,'equity and risk percent must be positive'
    if minimum<=0 or step<=0 or maximum<minimum: return 0,'invalid volume specification'
    per_lot=distance/tick_size*tick_value; allowed=float(equity)*float(risk_pct)/100
    if per_lot*minimum>allowed+1e-12: return 0,'min lot exceeds risk'
    raw=min(allowed/per_lot,maximum)
    # Volume grids start at volume_min; floor avoids exceeding the requested risk.
    units=int((raw-minimum+1e-12)/step); volume=min(maximum,minimum+units*step)
    volume=round(volume,8)
    if per_lot*volume>allowed+1e-9:
        volume=round(max(0,volume-step),8)
    return (volume,'ok') if volume>=minimum else (0,'min lot exceeds risk')

def _value(obj,key,default=None): return obj.get(key,default) if isinstance(obj,dict) else getattr(obj,key,default)

def _group(position):
    explicit=_value(position,'asset_group')
    if explicit: return explicit
    symbol=str(_value(position,'symbol','')).upper()
    patterns={'metals':('XAU','XAG','GOLD','SILVER'),'crypto':('BTC','ETH','CRYPTO'),'energy':('OIL','WTI','BRENT','GAS'),'indices':('US30','US100','NAS','SPX','DAX','UK100')}
    for group,parts in patterns.items():
        if any(part in symbol for part in parts): return group
    return 'forex' if len(symbol)>=6 and symbol[:6].isalpha() else 'other'

def check_trade_allowed(signal, account, open_positions, pnl_today, pnl_week, settings, cost_estimate, symbol_group, now_utc: datetime, required_margin):
    """Apply all configured risk gates in the fixed order defined by the brief."""
    config=settings.config if hasattr(settings,'config') else settings
    risk=config['risk']; root=Path(getattr(settings,'root',Path.cwd()))
    if (root/'STOP').exists(): return False,'kill switch active'
    if now_utc.weekday()==4 and now_utc.strftime('%H:%M')>=risk['no_new_trades_friday_after_utc']: return False,'Friday trading cutoff'
    floating=sum(float(_value(p,'profit',0) or 0) for p in open_positions)
    balance=float(_value(account,'balance',_value(account,'equity',0)))
    if float(pnl_today)+floating<=-balance*risk['daily_loss_limit_pct']/100: return False,'daily loss limit reached'
    if float(pnl_week)+floating<=-balance*risk['weekly_loss_limit_pct']/100: return False,'weekly loss limit reached'
    if len(open_positions)>=risk['max_open_positions']: return False,'maximum open positions reached'
    if sum(_group(p)==symbol_group for p in open_positions)>=risk['max_positions_per_group']: return False,'maximum positions for asset group reached'
    if any(_value(p,'symbol')==signal.symbol for p in open_positions): return False,'symbol already has open position'
    sl,tp,entry=signal.sl_price,signal.tp_price,signal.entry_hint
    if sl is None: return False,'stop-loss is required'
    if tp is None or entry is None: return False,'entry and take-profit are required'
    if signal.direction=='buy' and not sl<entry<tp: return False,'invalid SL/TP side for buy'
    if signal.direction=='sell' and not tp<entry<sl: return False,'invalid SL/TP side for sell'
    rr=abs(tp-entry)/abs(entry-sl)
    if rr<risk['min_risk_reward']: return False,'risk/reward below minimum'
    if isinstance(cost_estimate,dict):
        cost=float(cost_estimate.get('cost',0) or 0)
        target_value=cost_estimate.get('target_value')
        ratio=cost_estimate.get('cost_to_target_ratio')
        if ratio is None and target_value is not None: ratio=cost/float(target_value) if float(target_value)>0 else float('inf')
    else: cost=float(cost_estimate or 0); ratio=None
    if ratio is None and cost>0: return False,'cost-to-target estimate is incomplete'
    if ratio is not None and float(ratio)>risk['max_cost_to_target_ratio']: return False,'cost-to-target ratio too high'
    equity=float(_value(account,'equity',balance)); margin=float(_value(account,'margin',0))
    if equity<=0 or (margin+float(required_margin))/equity*100>risk['max_margin_usage_pct']: return False,'margin usage cap exceeded'
    return True,'allowed'
