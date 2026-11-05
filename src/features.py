"""Latest multi-timeframe feature snapshots and a coarse market regime."""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import indicators as ind

def _last(series):
    value=series.iloc[-1] if hasattr(series,'iloc') and len(series) else series
    return None if pd.isna(value) else (value.item() if hasattr(value,'item') else value)

def _timeframe_features(candles: pd.DataFrame) -> dict:
    if candles.empty: return {}
    close=candles['close']; atr=ind.atr(candles); adx=ind.adx(candles); bands=ind.bollinger(close); swings=ind.nearest_levels(candles); breaks=ind.breakout(candles); candleshape=ind.candle_structure(candles)
    ema20=ind.ema(close,20); ema50=ind.ema(close,50); levels=swings.iloc[-1]; atr_now=_last(atr); price=float(close.iloc[-1])
    atr_pct_series=atr/candles['close'].replace(0,np.nan)
    baseline=atr_pct_series.iloc[-101:-1].median()
    values={'close':price,'ema20':_last(ema20),'ema50':_last(ema50),'sma20':_last(ind.sma(close,20)),'ema_slope':_last(ind.ema_slope(close,20)),
      'adx':_last(adx['adx']),'plus_di':_last(adx['plus_di']),'minus_di':_last(adx['minus_di']),'higher_highs_lows':_last(ind.higher_highs_lows(candles)),
      'rsi':_last(ind.rsi(close)),'roc':_last(ind.roc(close)),'atr':atr_now,'atr_pct':atr_now/price if atr_now is not None and price else None,'atr_pct_baseline':_last(baseline),
      'realized_volatility':_last(ind.realized_volatility(close)),'bb_lower':_last(bands['bb_lower']),'bb_mid':_last(bands['bb_mid']),'bb_upper':_last(bands['bb_upper']),'bb_width':_last(bands['bb_width']),
      'support':None if pd.isna(levels['support']) else float(levels['support']),'resistance':None if pd.isna(levels['resistance']) else float(levels['resistance']),
      'breakout_up':bool(breaks['breakout_up'].iloc[-1]),'breakout_down':bool(breaks['breakout_down'].iloc[-1]),'range_high':_last(breaks['range_high']),'range_low':_last(breaks['range_low']),
      'tick_volume_relative':_last(ind.relative_tick_volume(candles))}
    values.update({k:_last(v) if not isinstance(v,(bool,np.bool_)) else bool(v) for k,v in candleshape.iloc[-1].items()})
    values.update({k:_last(v) for k,v in ind.macd(close).iloc[-1].items()})
    if atr_now:
        values['support_distance_atr']=(price-values['support'])/atr_now if values['support'] is not None else None
        values['resistance_distance_atr']=(values['resistance']-price)/atr_now if values['resistance'] is not None else None
    else: values['support_distance_atr']=values['resistance_distance_atr']=None
    return values

def _regime(tf_features: dict[str,dict]) -> str:
    current=tf_features.get('M15') or tf_features.get('M5') or next(iter(tf_features.values()),{})
    if not current: return 'quiet'
    vol=current.get('atr_pct'); adx=current.get('adx'); slope=current.get('ema_slope'); close=current.get('close'); ema=current.get('ema20')
    baseline=current.get('atr_pct_baseline')
    if vol is not None and baseline is not None and baseline>0:
        if vol>baseline*1.8: return 'high_volatility'
        if vol<baseline*.55: return 'quiet'
    if adx is not None and adx>=20 and slope is not None and close is not None and ema is not None:
        if slope>0 and close>ema: return 'trending_up'
        if slope<0 and close<ema: return 'trending_down'
    if vol is not None and vol==0: return 'quiet'
    return 'ranging'

def build_features(candles: dict[str,pd.DataFrame]) -> dict:
    """Build latest causal values by timeframe and a single regime label."""
    by_tf={tf:_timeframe_features(frame) for tf,frame in candles.items()}
    return {**by_tf,'market_regime':_regime(by_tf)}
