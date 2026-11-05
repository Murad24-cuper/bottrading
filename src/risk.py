from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path

def calc_volume(equity,risk_pct,entry,sl,symbol_spec):
 distance=abs(float(entry)-float(sl)); tv=float(symbol_spec.get('trade_tick_value',symbol_spec.get('tick_value',0)) or 0); ts=float(symbol_spec.get('trade_tick_size',symbol_spec.get('tick_size',0)) or 0)
 if distance<=0 or tv<=0 or ts<=0: return 0,'invalid stop or tick specification'
 allowed=equity*risk_pct/100; per_lot=distance/ts*tv
 vmin=float(symbol_spec.get('volume_min',0)); step=float(symbol_spec.get('volume_step',vmin)); vmax=float(symbol_spec.get('volume_max',float('inf')))
 if vmin<=0 or step<=0: return 0,'invalid volume specification'
 if per_lot*vmin>allowed+1e-10: return 0,'min lot exceeds risk'
 raw=min(allowed/per_lot,vmax); volume=(int((raw-vmin+1e-10)/step)*step)+vmin
 volume=round(min(volume,vmax),8)
 if volume<vmin: return 0,'min lot exceeds risk'
 return volume,'ok'

def check_trade_allowed(signal,account,open_positions,pnl_today,pnl_week,settings,cost_estimate,symbol_group,now_utc,required_margin):
 cfg=settings.config if hasattr(settings,'config') else settings; risk=cfg['risk']; root=getattr(settings,'root',Path.cwd())
 if (root/'STOP').exists(): return False,'kill switch active'
 if now_utc.weekday()==4 and now_utc.strftime('%H:%M')>=risk['no_new_trades_friday_after_utc']: return False,'Friday trading cutoff'
 floating=sum(float((p.get('profit',0) if isinstance(p,dict) else getattr(p,'profit',0)) or 0) for p in open_positions)
 if pnl_today+floating <= -account.equity*risk['daily_loss_limit_pct']/100: return False,'daily loss limit reached'
 if pnl_week+floating <= -account.equity*risk['weekly_loss_limit_pct']/100: return False,'weekly loss limit reached'
 if len(open_positions)>=risk['max_open_positions']: return False,'maximum open positions reached'
 def group_of(p):
  explicit=p.get('asset_group') if isinstance(p,dict) else getattr(p,'asset_group',None)
  if explicit: return explicit
  sym=(p.get('symbol','') if isinstance(p,dict) else getattr(p,'symbol','')).upper()
  if any(x in sym for x in ('XAU','XAG','GOLD','SILVER')): return 'metals'
  if any(x in sym for x in ('BTC','ETH','CRYPTO')): return 'crypto'
  if any(x in sym for x in ('OIL','WTI','BRENT','GAS')): return 'energy'
  if any(x in sym for x in ('US30','US100','NAS','SPX','DAX','UK100')): return 'indices'
  return 'forex' if len(sym)>=6 and sym[:6].isalpha() else 'other'
 if sum(group_of(p)==symbol_group for p in open_positions)>=risk['max_positions_per_group']: return False,'maximum positions for asset group reached'
 if any((getattr(p,'symbol',None) if not isinstance(p,dict) else p.get('symbol'))==signal.symbol for p in open_positions): return False,'symbol already has open position'
 sl,tp,entry=signal.sl_price,signal.tp_price,signal.entry_hint
 if sl is None or tp is None or entry is None: return False,'SL and TP required'
 if signal.direction=='buy' and not sl<entry<tp: return False,'invalid SL/TP side for buy'
 if signal.direction=='sell' and not tp<entry<sl: return False,'invalid SL/TP side for sell'
 rr=abs(tp-entry)/abs(entry-sl)
 if rr<risk['min_risk_reward']: return False,'risk/reward below minimum'
 target=abs(tp-entry)
 cost=cost_estimate.get('cost',0) if isinstance(cost_estimate,dict) else cost_estimate
 ratio=cost_estimate.get('cost_to_target_ratio') if isinstance(cost_estimate,dict) else None
 if target<=0 or (ratio is not None and ratio>risk['max_cost_to_target_ratio']): return False,'cost-to-target ratio too high'
 if (account.margin+required_margin)/max(account.equity,1e-9)*100>risk['max_margin_usage_pct']: return False,'margin usage cap exceeded'
 return True,'allowed'
