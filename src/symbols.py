from datetime import datetime,timezone
class SymbolService:
 def __init__(self,mt5,settings): self.mt5=mt5; self.settings=settings; self.cache=[]; self.loaded=0
 def list_all_symbols(self,refresh_minutes=5):
  import time
  if not self.cache or time.time()-self.loaded>refresh_minutes*60:
   rows=self.mt5.symbols_get()
   if rows is None: raise RuntimeError(f'symbols_get failed: {self.mt5.last_error()}')
   self.cache=list(rows); self.loaded=time.time()
  return self.cache
 def get_asset_group(self,symbol):
  i=self.mt5.symbol_info(symbol); path=(getattr(i,'path','') or '').lower() if i else ''
  for key,group in [('forex','forex'),('metal','metals'),('index','indices'),('energy','energy'),('crypto','crypto'),('stock','stocks'),('share','stocks')]:
   if key in path: return group
  n=symbol.lower()
  if any(x in n for x in ('xau','xag','xpd','xpt','gold','silver','palladium','platinum')): return 'metals'
  if any(x in n for x in ('btc','eth','crypto')): return 'crypto'
  if any(x in n for x in ('oil','wti','brent','gas')): return 'energy'
  if any(x in n for x in ('us30','us100','us500','nas','spx','dax','ger40','uk100','jp225','fra40','eu50','aus200','cash')): return 'indices'
  base=n.rstrip('#m.')
  if 1<=len(base)<=5 and base.isalpha(): return 'stocks'
  if len(n)>=6 and n[:6].isalpha(): return 'forex'
  return 'other'
 def resolve_alias(self,logical_name):
  pats=self.settings.config['universe']['symbol_aliases'].get(logical_name,[logical_name]); names=[s.name for s in self.list_all_symbols()]
  for pat in pats:
   for n in names:
    if pat.lower() in n.lower(): return n
  return None
 def is_tradable(self,symbol):
  i=self.mt5.symbol_info(symbol)
  if not i or not self.mt5.symbol_select(symbol,True): return False,'symbol unavailable'
  if i.trade_mode!=getattr(self.mt5,'SYMBOL_TRADE_MODE_FULL',4): return False,'symbol is not enabled for full trading'
  t=self.mt5.symbol_info_tick(symbol)
  stamp=getattr(t,'time_msc',0)/1000 if t and getattr(t,'time_msc',0) else (getattr(t,'time',0) if t else 0)
  age=datetime.now(timezone.utc).timestamp()-stamp
  if not t or age< -5 or age>60: return False,'stale tick / market closed'
  lim=self.settings.risk.get('max_spread_points',{}).get(symbol)
  spread=(t.ask-t.bid)/i.point
  if lim is not None and spread>lim: return False,'spread exceeds limit'
  return True,'tradable'
 def get_universe(self):
  u=self.settings.config['universe']; out=[]
  for s in self.list_all_symbols():
   if s.name in u['exclude_symbols'] or self.get_asset_group(s.name) not in u['include_groups']: continue
   if self.is_tradable(s.name)[0]: out.append(s.name)
  return out
