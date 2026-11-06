"""Pure helpers for short-horizon entries and exits."""
from __future__ import annotations
import math
import decimal
import pandas as pd
from . import indicators as ind


def mtf_direction_agrees(candles: dict[str, pd.DataFrame], direction: str, timeframes=('M1', 'M5', 'M15'), fast=5, slow=13) -> bool:
    """Require price and fast/slow EMA structure to agree on each timeframe."""
    for timeframe in timeframes:
        frame = candles.get(timeframe)
        if frame is None or len(frame) < slow + 2:
            return False
        fast_ema = ind.ema(frame.close, fast).iloc[-1]
        slow_ema = ind.ema(frame.close, slow).iloc[-1]
        close = float(frame.close.iloc[-1])
        if not all(math.isfinite(float(x)) for x in (fast_ema, slow_ema, close)):
            return False
        if direction == 'buy' and not (close > fast_ema > slow_ema):
            return False
        if direction == 'sell' and not (close < fast_ema < slow_ema):
            return False
    return True


def stop_target_from_atr(entry: float, direction: str, atr: float, spread: float, sl_mult: float, tp_mult: float) -> tuple[float, float]:
    """Build symmetric directional stop and target distances for a short horizon."""
    stop_distance = float(atr) * math.sqrt(10) * float(sl_mult)
    target_distance = float(atr) * math.sqrt(10) * float(tp_mult)
    # Include the current spread in the target's required distance.
    target_distance += max(0.0, float(spread))
    if not math.isfinite(stop_distance) or not math.isfinite(target_distance) or stop_distance <= 0:
        raise ValueError('ATR must be finite and positive')
    sign = 1 if direction == 'buy' else -1
    return float(entry) - sign * stop_distance, float(entry) + sign * target_distance


def spread_within_median(current: float, median: float, ratio: float) -> bool:
    """Reject absent/invalid baseline spreads and abnormally wide current spreads."""
    return all(math.isfinite(float(x)) for x in (current, median, ratio)) and median > 0 and current <= median * ratio


def confidence_allowed(confidence: float, minimum: float) -> bool:
    """Check a normalized strategy confidence against its configured floor."""
    return math.isfinite(float(confidence)) and 0 <= float(confidence) <= 1 and float(confidence) >= float(minimum)


def adverse_exit_score(frame: pd.DataFrame, direction: str, config: dict) -> tuple[int, list[str]]:
    """Score adverse M1 conditions using closed bars only."""
    needed = max(int(config['early_exit_ema_slow']) + 2, int(config['early_exit_swing_lookback']) + 2,
                 int(config['early_exit_rsi_period']) + 2, int(config['early_exit_roc_period']) + 2,
                 int(config['early_exit_volume_lookback']) + 2)
    if frame is None or len(frame) < needed:
        return 0, []
    buy = direction == 'buy'
    close = frame.close
    fast = ind.ema(close, int(config['early_exit_ema_fast']))
    slow = ind.ema(close, int(config['early_exit_ema_slow']))
    previous = len(frame) - 2
    current = len(frame) - 1
    reasons = []
    weights = config.get('early_exit_weights', {})
    score = 0
    def add(key, condition, reason):
        nonlocal score
        if condition:
            score += int(weights.get(key, 1)); reasons.append(reason)
    add('ema_cross', fast.iloc[current] < slow.iloc[current] if buy else fast.iloc[current] > slow.iloc[current], 'EMA kəsişməsi əks istiqamətdə')
    lookback = int(config['early_exit_swing_lookback'])
    prior = frame.iloc[-lookback-1:-1]
    add('swing_break', float(close.iloc[-1]) < float(prior.low.min()) if buy else float(close.iloc[-1]) > float(prior.high.max()), 'son M1 diapazonu qırıldı')
    rsi = ind.rsi(close, int(config['early_exit_rsi_period']))
    roc = ind.roc(close, int(config['early_exit_roc_period']))
    add('momentum', (rsi.iloc[-1] < 50 and roc.iloc[-1] < 0) if buy else (rsi.iloc[-1] > 50 and roc.iloc[-1] > 0), 'RSI/ROC impulsu zəifləyib')
    volumes = frame.tick_volume if 'tick_volume' in frame else pd.Series(0, index=frame.index)
    baseline = float(volumes.iloc[-int(config['early_exit_volume_lookback'])-1:-1].mean())
    adverse_candle = float(frame.close.iloc[-1]) < float(frame.open.iloc[-1]) if buy else float(frame.close.iloc[-1]) > float(frame.open.iloc[-1])
    add('volume_spike', baseline > 0 and float(volumes.iloc[-1]) >= baseline * float(config['early_exit_volume_spike_ratio']) and adverse_candle, 'əks istiqamətdə həcm sıçrayışı')
    return score, reasons


def should_exit_early(current_r: float, score: int, config: dict) -> bool:
    """Trigger within the configured adverse R band once enough evidence agrees."""
    return (bool(config.get('early_exit_enabled', True)) and
            float(config['early_exit_min_r']) <= float(current_r) <= float(config['early_exit_max_r']) and
            int(score) >= int(config['early_exit_score_threshold']))


def scale_out_volume(open_volume: float, step: float, minimum: float, percent: float) -> tuple[float, bool]:
    """Return a valid partial close; flag a full close when the remainder cannot be split."""
    if min(open_volume, step, minimum, percent) <= 0 or percent >= 100:
        raise ValueError('volume grid and scale-out percent must be positive')
    unit = decimal.Decimal(str(step)); desired = decimal.Decimal(str(open_volume))*decimal.Decimal(str(percent))/100
    partial = (desired/unit).to_integral_value(rounding=decimal.ROUND_FLOOR)*unit
    opened = decimal.Decimal(str(open_volume)); min_volume=decimal.Decimal(str(minimum))
    if partial < min_volume or opened-partial < min_volume:
        return float(opened), True
    return float(partial), False


def stop_only_tightens(direction: str, old_stop: float, new_stop: float) -> bool:
    """True when a proposed stop is no farther from entry than the existing stop."""
    return new_stop >= old_stop if direction == 'buy' else new_stop <= old_stop


def stagnation_due(age_minutes: float, peak_r: float, after_minutes: float, minimum_r: float) -> bool:
    """Check whether a trade failed to make the configured progress in time."""
    return float(age_minutes) >= float(after_minutes) and float(peak_r) < float(minimum_r)


def may_extend(in_profit: bool, scaled_out: bool, stop_protects_profit: bool, mtf_agrees: bool,
               momentum_rising: bool, continuation_score: float, minimum_score: float, age_minutes: float,
               max_minutes: float) -> bool:
    """Allow an extension only when every profit-protection condition is met."""
    return (age_minutes >= max_minutes and age_minutes < 60 and in_profit and scaled_out and
            stop_protects_profit and mtf_agrees and momentum_rising and continuation_score >= minimum_score)


def stop_protects_profit(direction: str, stop: float, entry: float, cost_distance: float) -> bool:
    """Require the stop to cover entry and estimated round-trip costs."""
    return float(stop) >= float(entry)+float(cost_distance) if direction == 'buy' else float(stop) <= float(entry)-float(cost_distance)


def continuation_metrics(candles: dict[str, pd.DataFrame], direction: str, fast=5, slow=13, roc_period=5) -> tuple[bool, bool, float]:
    """Return directional MTF agreement, improving directional momentum and score."""
    aligned=mtf_direction_agrees(candles,direction,('M1','M5','M15'),fast,slow)
    frame=candles.get('M1')
    if frame is None or len(frame)<roc_period*2+1: return aligned,False,0.0
    close=frame.close.astype(float)
    latest=float(close.iloc[-1]/close.iloc[-1-roc_period]-1)
    previous=float(close.iloc[-1-roc_period]/close.iloc[-1-2*roc_period]-1)
    rising=(latest>0 and latest>previous) if direction=='buy' else (latest<0 and latest<previous)
    score=float(aligned)+float(rising)
    return aligned,rising,score/2
