"""Live signal generators for the six strategy families from edge research v2.

Shadow by default; executed only under DEMO exploration (0.1% risk) or when qualified.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
from ..strategy_base import Strategy
from ..models import Signal
from .common import frame, signal
from .. import indicators as ind

class SessionBreakoutStrategy(Strategy):
    name = 'session_breakout'
    required_timeframes = ['M15', 'H1']
    
    def __init__(self, params: dict | None = None):
        super().__init__()
        p = params or {}
        self.variant = p.get('variant', 'v1')
        self.buf_mult = float(p.get('buf_mult', 0.1))
        self.sl_mult = float(p.get('sl_mult', 1.5))
        self.tp_mult = float(p.get('tp_mult', 2.0))
        self.asian_start = int(p.get('asian_start_hour', 0))
        self.asian_end = int(p.get('asian_end_hour', 7))
        self.window_start = int(p.get('window_start_hour', 7))
        self.window_end = int(p.get('window_end_hour', 11))
        
    def generate_signal(self, symbol: str, candles: dict[str, pd.DataFrame]) -> Signal | None:
        tf = 'M15' if 'v3' not in self.variant else 'H1'
        df = frame(candles, tf, minimum=30)
        if df is None:
            return self._skip('insufficient_bars')
            
        a = ind.atr(df, 14)
        curr_atr = float(a.iloc[-1])
        if not math.isfinite(curr_atr) or curr_atr <= 0:
            return self._skip('invalid_atr')
            
        now_bar = df.index[-1]
        now_hour = now_bar.hour
        
        # Must be in trading window
        if not (self.window_start <= now_hour < self.window_end):
            return self._skip('outside_window')
            
        # Compute Asian session high/low for today
        today = now_bar.date()
        asian_df = df[(df.index.date == today) & (df.index.hour >= self.asian_start) & (df.index.hour < self.asian_end)]
        if len(asian_df) < 2:
            return self._skip('no_asian_range')
            
        asian_high = float(asian_df['high'].max())
        asian_low = float(asian_df['low'].min())
        
        last_close = float(df['close'].iloc[-1])
        prev_close = float(df['close'].iloc[-2])
        
        upper_barrier = asian_high + self.buf_mult * curr_atr
        lower_barrier = asian_low - self.buf_mult * curr_atr
        
        if last_close > upper_barrier and prev_close <= upper_barrier:
            entry = last_close
            sl = entry - self.sl_mult * curr_atr
            tp = entry + self.tp_mult * curr_atr
            return signal(symbol, 'buy', tf, entry, sl, tp, 0.55, self.name,
                          f'family={self.name};variant={self.variant};asian_breakout_high')
        elif last_close < lower_barrier and prev_close >= lower_barrier:
            entry = last_close
            sl = entry + self.sl_mult * curr_atr
            tp = entry - self.tp_mult * curr_atr
            return signal(symbol, 'sell', tf, entry, sl, tp, 0.55, self.name,
                          f'family={self.name};variant={self.variant};asian_breakout_low')
            
        return self._skip('no_breakout')


class OpeningRangeBreakoutStrategy(Strategy):
    name = 'opening_range_breakout'
    required_timeframes = ['M15', 'H1']
    
    def __init__(self, params: dict | None = None):
        super().__init__()
        p = params or {}
        self.variant = p.get('variant', 'v1')
        self.sl_mult = float(p.get('sl_mult', 1.0))
        self.tp_mult = float(p.get('tp_mult', 1.5))
        self.use_sma = bool(p.get('use_sma', False))
        
    def generate_signal(self, symbol: str, candles: dict[str, pd.DataFrame]) -> Signal | None:
        tf = 'M15' if 'v3' not in self.variant else 'H1'
        df = frame(candles, tf, minimum=30)
        if df is None:
            return self._skip('insufficient_bars')
            
        a = ind.atr(df, 14)
        curr_atr = float(a.iloc[-1])
        if not math.isfinite(curr_atr) or curr_atr <= 0:
            return self._skip('invalid_atr')
            
        now_bar = df.index[-1]
        now_hour = now_bar.hour
        is_ger = 'GER' in symbol.upper()
        open_h, open_m = (7, 0) if is_ger else (14, 30)
        
        # Trading window: 2 hours following open
        if not (open_h + 1 <= now_hour <= open_h + 3):
            return self._skip('outside_window')
            
        today = now_bar.date()
        if tf == 'M15':
            orb_df = df[(df.index.date == today) & (df.index.hour == open_h) & (df.index.minute.isin([open_m, open_m + 15]))]
        else:
            orb_df = df[(df.index.date == today) & (df.index.hour == open_h)]
            
        if len(orb_df) < 1:
            return self._skip('no_orb_range')
            
        orb_high = float(orb_df['high'].max())
        orb_low = float(orb_df['low'].min())
        
        last_close = float(df['close'].iloc[-1])
        prev_close = float(df['close'].iloc[-2])
        
        sma50 = float(df['close'].rolling(50).mean().iloc[-1]) if self.use_sma else None
        
        if last_close > orb_high and prev_close <= orb_high:
            if self.use_sma and sma50 is not None and last_close < sma50:
                return self._skip('sma_trend_filter_block')
            entry = last_close
            sl = entry - self.sl_mult * curr_atr
            tp = entry + self.tp_mult * curr_atr
            return signal(symbol, 'buy', tf, entry, sl, tp, 0.55, self.name,
                          f'family={self.name};variant={self.variant};orb_high_break')
        elif last_close < orb_low and prev_close >= orb_low:
            if self.use_sma and sma50 is not None and last_close > sma50:
                return self._skip('sma_trend_filter_block')
            entry = last_close
            sl = entry + self.sl_mult * curr_atr
            tp = entry - self.tp_mult * curr_atr
            return signal(symbol, 'sell', tf, entry, sl, tp, 0.55, self.name,
                          f'family={self.name};variant={self.variant};orb_low_break')
            
        return self._skip('no_breakout')


class VWAPReversionStrategy(Strategy):
    name = 'vwap_reversion'
    required_timeframes = ['M15', 'H1']
    
    def __init__(self, params: dict | None = None):
        super().__init__()
        p = params or {}
        self.variant = p.get('variant', 'v1')
        self.dev_mult = float(p.get('dev_mult', 2.0))
        self.sl_mult = float(p.get('sl_mult', 1.5))
        self.use_rsi = bool(p.get('use_rsi', False))
        
    def generate_signal(self, symbol: str, candles: dict[str, pd.DataFrame]) -> Signal | None:
        tf = 'M15' if 'v3' not in self.variant else 'H1'
        df = frame(candles, tf, minimum=50)
        if df is None:
            return self._skip('insufficient_bars')
            
        a = ind.atr(df, 14)
        curr_atr = float(a.iloc[-1])
        if not math.isfinite(curr_atr) or curr_atr <= 0:
            return self._skip('invalid_atr')
            
        # 24-hour rolling VWAP
        window = 96 if tf == 'M15' else 24
        pv = df['close'] * df['tick_volume']
        vwap_series = pv.rolling(min(window, len(df))).sum() / (df['tick_volume'].rolling(min(window, len(df))).sum() + 1e-9)
        vwap_curr = float(vwap_series.iloc[-1])
        
        last_close = float(df['close'].iloc[-1])
        prev_close = float(df['close'].iloc[-2])
        prev_vwap = float(vwap_series.iloc[-2])
        
        dist = last_close - vwap_curr
        prev_dist = prev_close - prev_vwap
        threshold = self.dev_mult * curr_atr
        
        r = ind.rsi(df['close'], 14)
        curr_rsi = float(r.iloc[-1])
        
        # Mean reversion: fade deviation back toward VWAP
        if dist < -threshold and prev_dist >= -threshold:
            if self.use_rsi and curr_rsi >= 30:
                return self._skip('rsi_not_oversold')
            entry = last_close
            sl = entry - self.sl_mult * curr_atr
            tp = vwap_curr
            return signal(symbol, 'buy', tf, entry, sl, tp, 0.55, self.name,
                          f'family={self.name};variant={self.variant};vwap_oversold_revert')
        elif dist > threshold and prev_dist <= threshold:
            if self.use_rsi and curr_rsi <= 70:
                return self._skip('rsi_not_overbought')
            entry = last_close
            sl = entry + self.sl_mult * curr_atr
            tp = vwap_curr
            return signal(symbol, 'sell', tf, entry, sl, tp, 0.55, self.name,
                          f'family={self.name};variant={self.variant};vwap_overbought_revert')
            
        return self._skip('no_vwap_deviation')


class DonchianBreakoutStrategy(Strategy):
    name = 'donchian_breakout'
    required_timeframes = ['H4', 'H1', 'M15']  # Prioritize H4 for swing breakout
    
    def __init__(self, params: dict | None = None):
        super().__init__()
        p = params or {}
        self.variant = p.get('variant', 'v1')
        self.period = int(p.get('period', 20))
        self.sl_mult = float(p.get('sl_mult', 2.0))
        self.tp_mult = float(p.get('tp_mult', 4.0))
        
    def generate_signal(self, symbol: str, candles: dict[str, pd.DataFrame]) -> Signal | None:
        tf = 'D1' if 'v3' in self.variant else ('H4' if 'H4' in candles else ('H1' if 'H1' in candles else 'M15'))
        df = frame(candles, tf, minimum=self.period + 10)
        if df is None:
            return self._skip('insufficient_bars')
            
        a = ind.atr(df, 14)
        curr_atr = float(a.iloc[-1])
        if not math.isfinite(curr_atr) or curr_atr <= 0:
            return self._skip('invalid_atr')
            
        donch_h = float(df['high'].shift(1).rolling(self.period).max().iloc[-1])
        donch_l = float(df['low'].shift(1).rolling(self.period).min().iloc[-1])
        
        last_close = float(df['close'].iloc[-1])
        prev_close = float(df['close'].iloc[-2])
        
        if last_close > donch_h and prev_close <= donch_h:
            entry = last_close
            sl = entry - self.sl_mult * curr_atr
            tp = entry + self.tp_mult * curr_atr
            return signal(symbol, 'buy', tf, entry, sl, tp, 0.55, self.name,
                          f'family={self.name};variant={self.variant};donchian_upper_break')
        elif last_close < donch_l and prev_close >= donch_l:
            entry = last_close
            sl = entry + self.sl_mult * curr_atr
            tp = entry - self.tp_mult * curr_atr
            return signal(symbol, 'sell', tf, entry, sl, tp, 0.55, self.name,
                          f'family={self.name};variant={self.variant};donchian_lower_break')
            
        return self._skip('no_donchian_breakout')


class TSMomentumStrategy(Strategy):
    name = 'ts_momentum'
    required_timeframes = ['H4', 'H1', 'M15']
    
    def __init__(self, params: dict | None = None):
        super().__init__()
        p = params or {}
        self.variant = p.get('variant', 'v1')
        self.lookback = int(p.get('lookback', 12))
        self.sl_mult = float(p.get('sl_mult', 2.0))
        self.tp_mult = float(p.get('tp_mult', 3.0))
        
    def generate_signal(self, symbol: str, candles: dict[str, pd.DataFrame]) -> Signal | None:
        tf = 'D1' if 'v3' in self.variant else ('H4' if 'H4' in candles else ('H1' if 'H1' in candles else 'M15'))
        df = frame(candles, tf, minimum=self.lookback + 10)
        if df is None:
            return self._skip('insufficient_bars')
            
        a = ind.atr(df, 14)
        curr_atr = float(a.iloc[-1])
        if not math.isfinite(curr_atr) or curr_atr <= 0:
            return self._skip('invalid_atr')
            
        mom_curr = float(df['close'].iloc[-1]) - float(df['close'].iloc[-1 - self.lookback])
        mom_prev = float(df['close'].iloc[-2]) - float(df['close'].iloc[-2 - self.lookback])
        
        last_close = float(df['close'].iloc[-1])
        
        # Momentum regime shift
        if mom_curr > 0 and mom_prev <= 0:
            entry = last_close
            sl = entry - self.sl_mult * curr_atr
            tp = entry + self.tp_mult * curr_atr
            return signal(symbol, 'buy', tf, entry, sl, tp, 0.55, self.name,
                          f'family={self.name};variant={self.variant};tsmom_positive_shift')
        elif mom_curr < 0 and mom_prev >= 0:
            entry = last_close
            sl = entry + self.sl_mult * curr_atr
            tp = entry - self.tp_mult * curr_atr
            return signal(symbol, 'sell', tf, entry, sl, tp, 0.55, self.name,
                          f'family={self.name};variant={self.variant};tsmom_negative_shift')
            
        return self._skip('no_momentum_shift')


class IndexPullbackStrategy(Strategy):
    name = 'index_pullback_200d'
    required_timeframes = ['H1', 'M15']
    
    def __init__(self, params: dict | None = None):
        super().__init__()
        p = params or {}
        self.variant = p.get('variant', 'v1')
        self.sl_mult = float(p.get('sl_mult', 1.5))
        self.tp_mult = float(p.get('tp_mult', 2.5))
        
    def generate_signal(self, symbol: str, candles: dict[str, pd.DataFrame]) -> Signal | None:
        # Long-only dip buyer for equity indices
        tf = 'H1' if 'H1' in candles else 'M15'
        df = frame(candles, tf, minimum=60)
        if df is None:
            return self._skip('insufficient_bars')
            
        a = ind.atr(df, 14)
        curr_atr = float(a.iloc[-1])
        if not math.isfinite(curr_atr) or curr_atr <= 0:
            return self._skip('invalid_atr')
            
        # Trend filter: fast EMA > slow EMA (e.g. 50 > 200 or upward trend)
        sma50 = float(df['close'].rolling(min(50, len(df))).mean().iloc[-1])
        last_close = float(df['close'].iloc[-1])
        if last_close < sma50:
            return self._skip('below_trend_filter')
            
        r = ind.rsi(df['close'], 14)
        curr_rsi = float(r.iloc[-1])
        prev_rsi = float(r.iloc[-2])
        
        # Dip buy when RSI pulls back under 40 and turns back up
        if curr_rsi < 40 or (prev_rsi < 35 and curr_rsi >= 35):
            entry = last_close
            sl = entry - self.sl_mult * curr_atr
            tp = entry + self.tp_mult * curr_atr
            return signal(symbol, 'buy', tf, entry, sl, tp, 0.55, self.name,
                          f'family={self.name};variant={self.variant};index_dip_pullback')
            
        return self._skip('no_pullback')
