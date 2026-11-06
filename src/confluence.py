"""Optional entry confluence rules; disabled mode preserves the original signal."""
from __future__ import annotations

def apply_confluence(features: dict, direction: str, confidence: float, config: dict) -> tuple[bool,str,float]:
    """Apply only explicitly enabled observational rules."""
    original=float(confidence)
    if not config.get('enabled',False): return True,'',original
    observations=(features or {}).get('observations',{}); signal=observations.get('signal_context',{})
    rules=set(config.get('rules',[])); opp='bearish' if direction=='buy' else 'bullish'
    if 'require_with_usd_context' in rules and signal.get('with_usd_context') is not True: return False,'confluence: USD context does not agree',original
    if 'require_with_group_direction' in rules and signal.get('with_group_direction') is not True: return False,'confluence: asset group direction does not agree',original
    levels=observations.get('key_levels',{})
    if 'skip_tp_blocked_by_level' in rules and levels.get('tp_blocked') is True: return False,'confluence: take-profit blocked by strong level',original
    if 'skip_against_confirmed_chart_pattern' in rules:
        patterns=[p for values in observations.get('chart_patterns',{}).values() for p in values]
        if any(p.get('state')=='confirmed breakout' and p.get('direction')==opp for p in patterns): return False,'confluence: against confirmed chart pattern',original
    if 'require_candle_confirmation' in rules:
        patterns=observations.get('candlestick_patterns',[])
        if not any(p.get('direction')==('bullish' if direction=='buy' else 'bearish') for p in patterns): return False,'confluence: candle confirmation missing',original
    if 'skip_off_hours' in rules and observations.get('session',{}).get('session')=='off-hours': return False,'confluence: off-hours session',original
    if 'prefer_fib_reaction' in rules and any(v.get('reacting') is True for v in observations.get('fibonacci',{}).values()):
        return True,'',min(1.0,original+.05)
    return True,'',original
