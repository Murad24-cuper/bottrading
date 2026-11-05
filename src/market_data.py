"""MT5 market and account data adapters. MT5 is passed in for easy mocking."""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from .models import AccountState

def get_account_state(mt5) -> AccountState:
    a=mt5.account_info()
    if a is None: raise RuntimeError(f'account_info failed: {mt5.last_error()}')
    return AccountState(a.balance,a.equity,a.margin,a.margin_free,a.margin_level,a.currency,a.margin_leverage,a.trade_mode,a.margin_mode)

def get_candles(mt5,symbol,timeframe,count):
    import pandas as pd
    if not mt5.symbol_select(symbol,True): raise RuntimeError(f'symbol_select {symbol} failed: {mt5.last_error()}')
    tf=getattr(mt5,'TIMEFRAME_'+timeframe,None)
    if tf is None: raise ValueError(f'Unsupported timeframe: {timeframe}')
    arr=mt5.copy_rates_from_pos(symbol,tf,0,count)
    if arr is None: raise RuntimeError(f'copy_rates_from_pos failed: {mt5.last_error()}')
    df=pd.DataFrame(arr)
    if df.empty: return pd.DataFrame(columns=['open','high','low','close','tick_volume','spread'],index=pd.DatetimeIndex([],tz='UTC',name='time'))
    df['time']=pd.to_datetime(df['time'],unit='s',utc=True)
    return df.set_index('time')[['open','high','low','close','tick_volume','spread']]

def get_closed_candles(mt5,symbol,timeframe,count):
    """Read completed bars only (MT5 shift 1 excludes the forming bar)."""
    import pandas as pd
    if not mt5.symbol_select(symbol,True): raise RuntimeError(f'symbol_select {symbol} failed: {mt5.last_error()}')
    tf=getattr(mt5,'TIMEFRAME_'+timeframe,None)
    if tf is None: raise ValueError(f'Unsupported timeframe: {timeframe}')
    rows=mt5.copy_rates_from_pos(symbol,tf,1,count)
    if rows is None: raise RuntimeError(f'copy_rates_from_pos closed bars failed: {mt5.last_error()}')
    df=pd.DataFrame(rows)
    if df.empty: return pd.DataFrame(columns=['open','high','low','close','tick_volume','spread'],index=pd.DatetimeIndex([],tz='UTC',name='time'))
    df['time']=pd.to_datetime(df.time,unit='s',utc=True)
    return df.set_index('time')[['open','high','low','close','tick_volume','spread']]

def get_candles_multi(mt5,symbol,timeframes,count): return {tf:get_candles(mt5,symbol,tf,count) for tf in timeframes}

def get_tick(mt5,symbol):
    if not mt5.symbol_select(symbol,True): raise RuntimeError(f'symbol_select {symbol} failed: {mt5.last_error()}')
    tick=mt5.symbol_info_tick(symbol)
    if tick is None: raise RuntimeError(f'symbol_info_tick failed: {mt5.last_error()}')
    return tick

def get_spread_points(mt5,symbol):
    tick=get_tick(mt5,symbol); info=mt5.symbol_info(symbol)
    if info is None or not info.point: raise RuntimeError(f'symbol_info({symbol}) failed: {mt5.last_error()}')
    return (tick.ask-tick.bid)/info.point

def price_distance_to_money(mt5,symbol,distance,volume):
    info=mt5.symbol_info(symbol)
    if info is None: raise RuntimeError(f'symbol_info({symbol}) failed: {mt5.last_error()}')
    tick_size=float(getattr(info,'trade_tick_size',0) or 0); tick_value=float(getattr(info,'trade_tick_value',0) or 0)
    if tick_size<=0 or tick_value<=0: raise ValueError(f'Invalid tick value/size for {symbol}')
    return abs(float(distance))/tick_size*tick_value*float(volume)

def get_cost_estimate(mt5,symbol,volume):
    """Return spread plus estimated round-trip commission in account currency."""
    info=mt5.symbol_info(symbol); tick=get_tick(mt5,symbol)
    if info is None: raise RuntimeError(f'symbol_info({symbol}) failed: {mt5.last_error()}')
    spread_cost=price_distance_to_money(mt5,symbol,tick.ask-tick.bid,volume)
    commission_per_lot=None
    try:
        deals=mt5.history_deals_get(datetime.now(timezone.utc)-timedelta(days=30),datetime.now(timezone.utc))
        samples=[]
        for deal in deals or []:
            if getattr(deal,'symbol',None)==symbol and float(getattr(deal,'volume',0) or 0)>0:
                commission=abs(float(getattr(deal,'commission',0) or 0))
                if commission: samples.append(commission/float(deal.volume))
        if samples: commission_per_lot=sum(samples)/len(samples)
    except Exception:
        commission_per_lot=None
    commission_known=commission_per_lot is not None
    commission=2*commission_per_lot*float(volume) if commission_known else 0.0
    return {'cost':spread_cost+commission,'spread_cost':spread_cost,'commission':commission,'commission_known':commission_known}
