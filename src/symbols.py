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
  cleaned=re.sub(r'(?:CASH|#|MICRO|MIC|M)$','',name,flags=re.IGNORECASE)
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
 def __init__(self,mt5,settings): self.mt5=mt5; self.settings=settings; self.cache=[]; self.loaded=0; self._session_cache={}; self._candidate_cache=[]; self._candidate_loaded=0
 def _session_frame(self,symbol):
  import time
  from .market_data import get_closed_candles
  cached=self._session_cache.get(symbol)
  if cached is None or time.monotonic()-cached[0]>900:
   try: frame=get_closed_candles(self.mt5,symbol,'H1',24*35)
   except (RuntimeError,ValueError): frame=None
   cached=(time.monotonic(),frame); self._session_cache[symbol]=cached
  return cached[1]
 def session_history_available(self,symbol):
  """Require a week of H1 bars before treating inferred sessions as known."""
  frame=self._session_frame(symbol)
  return frame is not None and len(frame)>=24*7
 def market_should_be_open(self,symbol,now_utc=None):
  """Infer whether the current UTC instant falls inside a recurring broker closure."""
  from collections import Counter
  import statistics
  from datetime import timedelta
  from .sessions import session_closures
  now=now_utc or datetime.now(timezone.utc)
  now=now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
  frame=self._session_frame(symbol)
  if frame is None or len(frame)<24*7: return True
  gaps=session_closures(frame)
  counts=Counter((weekday,minute) for weekday,minute,_ in gaps)
  for key,count in counts.items():
   if count<2: continue
   durations=[gap for weekday,minute,gap in gaps if (weekday,minute)==key]
   gap_hours=statistics.median(durations); weekday,minute=key
   days_since=(now.weekday()-weekday)%7
   for offset in (days_since,days_since+7):
    day=(now-timedelta(days=offset)).date()
    closed_at=datetime(day.year,day.month,day.day,minute//60,minute%60,tzinfo=timezone.utc)
    if closed_at<=now<closed_at+timedelta(hours=gap_hours): return False
  return True
 def forex_session_open(self,now_utc=None):
  """Treat the weekly forex session as open only with a fresh tradable EURUSD quote."""
  symbol=self.resolve_alias('EURUSD')
  if not symbol or not self.market_should_be_open(symbol,now_utc): return False
  try: return self.is_tradable(symbol,now_utc=now_utc)[0]
  except TypeError: return self.is_tradable(symbol)[0]
 def next_session_close(self,symbol,now_utc=None,min_gap_hours=0.0):
  """Infer the next close from recurring gaps in the broker's H1 history."""
  from .sessions import next_session_close
  frame=self._session_frame(symbol); now=now_utc or datetime.now(timezone.utc)
  if frame is None or len(frame)<24*7: return None
  return next_session_close(frame,now,float(min_gap_hours))
 def list_all_symbols(self,refresh_minutes=5):
  import time
  if not self.cache or time.time()-self.loaded>refresh_minutes*60:
   rows=self.mt5.symbols_get()
   if rows is None: raise RuntimeError(f'symbols_get failed: {self.mt5.last_error()}')
   self.cache=list(rows); self.loaded=time.time()
  return self.cache
 def get_asset_group(self,symbol):
  i=self.mt5.symbol_info(symbol); path=(getattr(i,'path','') or '').lower() if i else ''
  for key,group in [('forex','forex'),('metal','metals'),('indices','indices'),('index','indices'),('energy','energy'),('crypto','crypto'),('stock','stocks'),('share','stocks')]:
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
    # Some brokers expose an exact alias as disabled while the tradable
    # contract uses a suffix (for example EURUSD and EURUSD#). Prefer a full
    # trading-mode match within this alias before falling back to name order.
    full_mode=getattr(self.mt5,'SYMBOL_TRADE_MODE_FULL',4)
    tradable=[]
    for name in matches:
     get_info=getattr(self.mt5,'symbol_info',None)
     info=get_info(name) if callable(get_info) else None
     if info is not None and getattr(info,'trade_mode',None)==full_mode:
      tradable.append(name)
    selected=(exact if exact in tradable else None) or (tradable[0] if tradable else (exact or matches[0]))
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
 def is_tradable(self,symbol,check_session=True,now_utc=None):
  i=self.mt5.symbol_info(symbol)
  if not i or not self.mt5.symbol_select(symbol,True): return False,'symbol unavailable'
  if i.trade_mode!=getattr(self.mt5,'SYMBOL_TRADE_MODE_FULL',4): return False,'symbol is not enabled for full trading'
  t=self.mt5.symbol_info_tick(symbol)
  stamp=getattr(t,'time_msc',0)/1000 if t and getattr(t,'time_msc',0) else (getattr(t,'time',0) if t else 0)
  tick_utc=mt5_epoch_to_utc(stamp,self.mt5) if stamp else None
  age=(datetime.now(timezone.utc)-tick_utc).total_seconds() if tick_utc else float('inf')
  group=self.get_asset_group(symbol)
  fresh_limits=self.settings.config['universe'].get('tick_freshness_seconds_by_group',{})
  freshness=float(fresh_limits.get(group,fresh_limits.get('other',60)))
  if not t or age< -5 or age>freshness: return False,'stale tick / market closed'
  history_known=self.session_history_available(symbol) if check_session else True
  if check_session and not history_known:
   # Sparse newly-listed symbols may not have enough bars to infer sessions;
   # require fresh closed-bar activity in addition to the fresh quote.
   from .market_data import get_closed_candles
   try: recent=get_closed_candles(self.mt5,symbol,'M1',5)
   except (RuntimeError,ValueError): recent=None
   if recent is None or recent.empty or (datetime.now(timezone.utc)-recent.index[-1].to_pydatetime()).total_seconds()>freshness+60:
    return False,'no recent bar activity'
  upcoming=self.next_session_close(symbol,now_utc,0.0) if check_session else None
  if upcoming:
   now=now_utc or datetime.now(timezone.utc)
   now=now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
   minutes=(upcoming[0]-now).total_seconds()/60
   if 0<=minutes<=self.settings.risk.no_entry_before_close_minutes: return False,'symbol session closes soon'
  lim=self.settings.risk.max_spread_points.get(symbol)
  spread=(t.ask-t.bid)/i.point
  if lim is not None and spread>lim: return False,'spread exceeds limit'
  return True,'tradable'
 def active_logical_universe(self, now_utc=None):
  """Return configured weekday focus symbols or the weekend instruments."""
  now=now_utc or datetime.now(timezone.utc)
  now=now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
  universe=self.settings.config['universe']
  forex_open=self.forex_session_open(now) if now.weekday()>=5 else False
  weekend=now.weekday()>=5 and not forex_open
  names=universe.get('weekend_symbols',[]) if weekend else universe.get('focus_symbols',[])
  resolved=[self.resolve_alias(str(name)) for name in names]
  resolved=[name for name in resolved if name]
  if weekend and universe.get('weekend_include_open_indices',True):
   for item in self.list_all_symbols():
    if self.get_asset_group(item.name)!='indices' or not self.market_should_be_open(item.name,now):
     continue
    tick=self.mt5.symbol_info_tick(item.name)
    stamp=(getattr(tick,'time_msc',0)/1000 if tick and getattr(tick,'time_msc',0) else getattr(tick,'time',0) if tick else 0)
    if stamp:
     from .time_utils import mt5_epoch_to_utc
     age=(now-mt5_epoch_to_utc(stamp,self.mt5)).total_seconds()
     if -5<=age<=float(universe.get('weekend_index_tick_freshness_seconds',180)):
      resolved.append(item.name)
  return list(dict.fromkeys(resolved))
 def get_candidates(self,select=True):
  """Return only the active configured universe plus any open-symbol management candidates."""
  import time
  now=datetime.now(timezone.utc)
  cache_key=(now.weekday()>=5,now.hour)
  if (self._candidate_cache and getattr(self,'_candidate_cache_key',None)==cache_key
      and time.monotonic()-self._candidate_loaded<int(self.settings.config['universe']['refresh_minutes'])*60):
   return list(self._candidate_cache)
  u=self.settings.config['universe']; out=[]
  if 'focus_symbols' not in u:
   preferred=self.select_liquid_symbols(); legacy=[]
   for item in self.list_all_symbols():
    name=item.name
    if name in u.get('exclude_symbols',[]) or self.get_asset_group(name) not in u.get('include_groups',[]): continue
    if u.get('exclude_dated_futures',True) and is_dated_future(name): continue
    if select and not self.mt5.symbol_select(name,True): continue
    legacy.append(name)
   preferred=[name for name in preferred if name in legacy]
   self._candidate_cache=list(dict.fromkeys([*preferred,*legacy])); self._candidate_loaded=time.monotonic(); self._candidate_cache_key=cache_key
   return list(self._candidate_cache)
  for name in self.active_logical_universe(now):
   if name in u.get('exclude_symbols',[]) or (u.get('exclude_dated_futures',True) and is_dated_future(name)):
    continue
   if select and not self.mt5.symbol_select(name,True): continue
   out.append(name)
  self._candidate_cache=list(dict.fromkeys(out)); self._candidate_cache_key=cache_key
  self._candidate_loaded=time.monotonic()
  return list(self._candidate_cache)
 def get_universe(self):
  return [name for name in self.get_candidates() if self.is_tradable(name)[0]]

def get_universe(settings,mt5=None):
 """Return tradable configured symbols; may use an explicit connected MT5 API."""
 if mt5 is not None: return SymbolService(mt5,settings).get_universe()
 from .mt5_client import MT5Client
 with MT5Client(settings) as client: return SymbolService(client.mt5,settings).get_universe()
