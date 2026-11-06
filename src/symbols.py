from datetime import datetime,timezone
import re
from .time_utils import mt5_epoch_to_utc

_DATED_FUTURE=re.compile(r'(?:[-_.]?(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(?:20)?\d{2})$',re.IGNORECASE)

def is_dated_future(symbol):
 return bool(_DATED_FUTURE.search(str(symbol).strip()))

def underlying_key(symbol):
 """Remove common broker suffixes and futures expiry from a symbol name."""
 name=_DATED_FUTURE.sub('',str(symbol).strip().upper())
 while True:
  cleaned=re.sub(r'(?:CASH|#|M)$','',name,flags=re.IGNORECASE)
  if cleaned==name: break
  name=cleaned
 return name.rstrip('._-')

def underlying_group(symbol,asset_group):
 if asset_group!='indices': return None
 key=underlying_key(symbol)
 if key.startswith('US'): return 'us_indices'
 if key.startswith(('GER','DAX','DE','EU','FRA','UK')): return 'europe_indices'
 if key.startswith(('JP','JPN','AUS','HK','SG')): return 'asia_pacific_indices'
 return 'other_indices'
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
   matches=[n for n in names if pat.lower() in n.lower()]
   if matches:
    # Prefer an exact match to avoid resolving e.g. BTC to a similarly named CFD.
    exact=next((n for n in matches if n.lower()==pat.lower()),None)
    selected=exact or matches[0]
    self.mt5.symbol_select(selected,True)
    return selected
  return None
 def select_liquid_symbols(self):
  """Select configured liquid instruments in Market Watch before reading ticks."""
  selected=[]
  for alias in self.settings.config.get('history',{}).get('liquid_aliases',[]):
   symbol=self.resolve_alias(alias)
   if symbol and self.mt5.symbol_select(symbol,True): selected.append(symbol)
  return list(dict.fromkeys(selected))
 def is_tradable(self,symbol):
  i=self.mt5.symbol_info(symbol)
  if not i or not self.mt5.symbol_select(symbol,True): return False,'symbol unavailable'
  if i.trade_mode!=getattr(self.mt5,'SYMBOL_TRADE_MODE_FULL',4): return False,'symbol is not enabled for full trading'
  t=self.mt5.symbol_info_tick(symbol)
  stamp=getattr(t,'time_msc',0)/1000 if t and getattr(t,'time_msc',0) else (getattr(t,'time',0) if t else 0)
  tick_utc=mt5_epoch_to_utc(stamp,self.mt5) if stamp else None
  age=(datetime.now(timezone.utc)-tick_utc).total_seconds() if tick_utc else float('inf')
  if not t or age< -5 or age>60: return False,'stale tick / market closed'
  lim=self.settings.risk.max_spread_points.get(symbol)
  spread=(t.ask-t.bid)/i.point
  if lim is not None and spread>lim: return False,'spread exceeds limit'
  return True,'tradable'
 def get_candidates(self,select=True):
  """Return all included broker names, selecting each into Market Watch."""
  self.select_liquid_symbols()
  u=self.settings.config['universe']; out=[]
  for item in self.list_all_symbols():
   name=item.name
   if name in u['exclude_symbols'] or self.get_asset_group(name) not in u['include_groups']: continue
   if u.get('exclude_dated_futures',True) and is_dated_future(name): continue
   if select and not self.mt5.symbol_select(name,True): continue
   out.append(name)
  return out
 def get_universe(self):
  return [name for name in self.get_candidates() if self.is_tradable(name)[0]]

def get_universe(settings,mt5=None):
 """Return tradable configured symbols; may use an explicit connected MT5 API."""
 if mt5 is not None: return SymbolService(mt5,settings).get_universe()
 from .mt5_client import MT5Client
 with MT5Client(settings) as client: return SymbolService(client.mt5,settings).get_universe()
