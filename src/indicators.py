"""Causal technical indicators implemented with pandas and numpy only."""
from __future__ import annotations
import numpy as np
import pandas as pd

def ema(values: pd.Series, period: int) -> pd.Series:
    return values.ewm(span=period,adjust=False,min_periods=period).mean()

def sma(values: pd.Series, period: int) -> pd.Series:
    return values.rolling(period,min_periods=period).mean()

def ema_slope(values: pd.Series, period: int=20, lookback: int=3) -> pd.Series:
    line=ema(values,period)
    return (line-line.shift(lookback))/lookback

def true_range(candles: pd.DataFrame) -> pd.Series:
    prev=candles['close'].shift(1)
    return pd.concat([candles['high']-candles['low'],(candles['high']-prev).abs(),(candles['low']-prev).abs()],axis=1).max(axis=1)

def atr(candles: pd.DataFrame, period: int=14) -> pd.Series:
    return true_range(candles).ewm(alpha=1/period,adjust=False,min_periods=period).mean()

def adx(candles: pd.DataFrame, period: int=14) -> pd.DataFrame:
    up=candles['high'].diff(); down=-candles['low'].diff()
    plus=up.where((up>down)&(up>0),0.0); minus=down.where((down>up)&(down>0),0.0)
    smooth=lambda x:x.ewm(alpha=1/period,adjust=False,min_periods=period).mean()
    tr=smooth(true_range(candles)).replace(0,np.nan)
    plus_di=100*smooth(plus)/tr; minus_di=100*smooth(minus)/tr
    denom=(plus_di+minus_di).replace(0,np.nan)
    dx=100*(plus_di-minus_di).abs()/denom
    return pd.DataFrame({'adx':dx.ewm(alpha=1/period,adjust=False,min_periods=period).mean(),'plus_di':plus_di,'minus_di':minus_di},index=candles.index)

def higher_highs_lows(candles: pd.DataFrame, period: int=10) -> pd.Series:
    hh=candles['high'].diff().gt(0).rolling(period,min_periods=period).sum()
    hl=candles['low'].diff().gt(0).rolling(period,min_periods=period).sum()
    return hh+hl

def rsi(close: pd.Series, period: int=14) -> pd.Series:
    delta=close.diff(); gain=delta.clip(lower=0).ewm(alpha=1/period,adjust=False,min_periods=period).mean()
    loss=(-delta.clip(upper=0)).ewm(alpha=1/period,adjust=False,min_periods=period).mean()
    rs=gain/loss.replace(0,np.nan); result=100-100/(1+rs)
    result=result.mask((loss==0)&(gain>0),100).mask((gain==0)&(loss>0),0).mask((gain==0)&(loss==0),50)
    return result

def roc(close: pd.Series, period: int=12) -> pd.Series:
    return close.pct_change(periods=period)*100

def macd(close: pd.Series, fast: int=12, slow: int=26, signal: int=9) -> pd.DataFrame:
    line=ema(close,fast)-ema(close,slow); sig=line.ewm(span=signal,adjust=False,min_periods=signal).mean()
    return pd.DataFrame({'macd':line,'macd_signal':sig,'macd_hist':line-sig},index=close.index)

def bollinger(close: pd.Series, period: int=20, deviations: float=2.0) -> pd.DataFrame:
    mid=sma(close,period); std=close.rolling(period,min_periods=period).std(ddof=0)
    upper=mid+deviations*std; lower=mid-deviations*std
    width=(upper-lower)/mid.replace(0,np.nan)
    return pd.DataFrame({'bb_lower':lower,'bb_mid':mid,'bb_upper':upper,'bb_width':width},index=close.index)

def realized_volatility(close: pd.Series, period: int=20, annualization: float=1.0) -> pd.Series:
    returns=np.log(close/close.shift(1))
    return returns.rolling(period,min_periods=period).std(ddof=0)*np.sqrt(annualization)

def swing_points(candles: pd.DataFrame, window: int=3) -> pd.DataFrame:
    """Mark a pivot only at its confirmation bar, avoiding future leakage."""
    n=len(candles); highs=np.zeros(n,dtype=bool); lows=np.zeros(n,dtype=bool); span=2*window+1
    h=candles['high'].to_numpy(); l=candles['low'].to_numpy()
    for confirmed in range(span-1,n):
        center=confirmed-window; start=confirmed-span+1; stop=confirmed+1
        highs[confirmed]=h[center]>=np.max(h[start:stop]) and np.count_nonzero(h[start:stop]==h[center])==1
        lows[confirmed]=l[center]<=np.min(l[start:stop]) and np.count_nonzero(l[start:stop]==l[center])==1
    return pd.DataFrame({'swing_high':highs,'swing_low':lows},index=candles.index)

def nearest_levels(candles: pd.DataFrame, window: int=3, lookback: int=100) -> pd.DataFrame:
    swings=swing_points(candles,window); support=[]; resistance=[]; lows=[]; highs=[]
    for i in range(len(candles)):
        if swings['swing_low'].iloc[i]: lows.append(float(candles['low'].iloc[i-window]))
        if swings['swing_high'].iloc[i]: highs.append(float(candles['high'].iloc[i-window]))
        recent_lows=lows[-lookback:]; recent_highs=highs[-lookback:]; price=float(candles['close'].iloc[i])
        below=[x for x in recent_lows if x<=price]; above=[x for x in recent_highs if x>=price]
        support.append(max(below) if below else np.nan); resistance.append(min(above) if above else np.nan)
    return pd.DataFrame({'support':support,'resistance':resistance},index=candles.index)

def breakout(candles: pd.DataFrame, period: int=20) -> pd.DataFrame:
    prior_high=candles['high'].shift(1).rolling(period,min_periods=period).max()
    prior_low=candles['low'].shift(1).rolling(period,min_periods=period).min()
    return pd.DataFrame({'range_high':prior_high,'range_low':prior_low,'breakout_up':candles['close']>prior_high,'breakout_down':candles['close']<prior_low},index=candles.index)

def candle_structure(candles: pd.DataFrame) -> pd.DataFrame:
    spread=(candles['high']-candles['low']).replace(0,np.nan)
    body=(candles['close']-candles['open']).abs(); top=candles[['open','close']].max(axis=1); bottom=candles[['open','close']].min(axis=1)
    prev_open=candles['open'].shift(1); prev_close=candles['close'].shift(1)
    bull=(candles['close']>candles['open'])&(prev_close<prev_open)&(candles['open']<=prev_close)&(candles['close']>=prev_open)
    bear=(candles['close']<candles['open'])&(prev_close>prev_open)&(candles['open']>=prev_close)&(candles['close']<=prev_open)
    return pd.DataFrame({'body_range_ratio':body/spread,'upper_wick_ratio':(candles['high']-top)/spread,'lower_wick_ratio':(bottom-candles['low'])/spread,'bullish_engulfing':bull,'bearish_engulfing':bear,'inside_bar':(candles['high']<candles['high'].shift(1))&(candles['low']>candles['low'].shift(1))},index=candles.index)

def relative_tick_volume(candles: pd.DataFrame, period: int=20) -> pd.Series:
    volume=candles['tick_volume'] if 'tick_volume' in candles else pd.Series(0.0,index=candles.index)
    mean=volume.rolling(period,min_periods=period).mean().replace(0,np.nan)
    return volume/mean
