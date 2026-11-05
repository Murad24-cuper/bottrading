from datetime import datetime,timezone
from .models import AccountState

def get_account_state(mt5):
 a=mt5.account_info()
 if a is None: raise RuntimeError(f'account_info failed: {mt5.last_error()}')
 return AccountState(a.balance,a.equity,a.margin,a.margin_free,a.margin_level,a.currency,a.margin_leverage,a.trade_mode,a.margin_mode)

def _tf(mt5,name): return getattr(mt5,'TIMEFRAME_'+name)
def get_candles(mt5,symbol,timeframe,count):
 import pandas as pd
 if not mt5.symbol_select(symbol,True): raise RuntimeError(f'symbol_select {symbol} failed: {mt5.last_error()}')
 arr=mt5.copy_rates_from_pos(symbol,_tf(mt5,timeframe),0,count)
 if arr is None: raise RuntimeError(f'copy_rates failed: {mt5.last_error()}')
 df=pd.DataFrame(arr); df['time']=pd.to_datetime(df['time'],unit='s',utc=True); return df.set_index('time')[['open','high','low','close','tick_volume','spread']]
def get_candles_multi(mt5,symbol,timeframes,count): return {tf:get_candles(mt5,symbol,tf,count) for tf in timeframes}
def get_tick(mt5,symbol):
 t=mt5.symbol_info_tick(symbol)
 if t is None: raise RuntimeError(f'tick failed: {mt5.last_error()}')
 return t
def get_spread_points(mt5,symbol):
 t=get_tick(mt5,symbol); i=mt5.symbol_info(symbol); return (t.ask-t.bid)/i.point

def price_distance_to_money(mt5,symbol,distance,volume):
 i=mt5.symbol_info(symbol); return abs(distance)/i.trade_tick_size*i.trade_tick_value*volume
def get_cost_estimate(mt5,symbol,volume):
 i=mt5.symbol_info(symbol); spread=get_spread_points(mt5,symbol)*i.point
 return {'cost':price_distance_to_money(mt5,symbol,spread,volume),'commission_known':False}
