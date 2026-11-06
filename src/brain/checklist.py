"""Causal multi-timeframe checklist built from closed-bar feature snapshots."""
from __future__ import annotations
import math

def evaluate(features: dict, direction: str, weights: dict | None=None,
             observations: dict | None=None, entry: float | None=None,
             target: float | None=None) -> dict:
    """Return weighted checklist score, item explanations, and blocking failures."""
    direction=direction.lower(); sign=1 if direction=='buy' else -1
    observations=observations or features.get('observations',{})
    weights=weights or {}
    m15=features.get('M15') or {}; h1=features.get('H1') or {}; m5=features.get('M5') or {}; m1=features.get('M1') or {}
    trend_values=[float(row['ema_slope']) for row in (m15,h1) if row.get('ema_slope') is not None]
    trend=bool(trend_values) and all(sign*value>0 for value in trend_values)
    location_row=m15 or m5; support=location_row.get('support_distance_atr'); resistance=location_row.get('resistance_distance_atr')
    location=(support is not None and support>=0 and support<=1.5) if direction=='buy' else (resistance is not None and resistance>=0 and resistance<=1.5)
    patterns=[p for rows in (observations.get('chart_patterns') or {}).values() for p in rows]
    pattern_names={p.get('name') for p in patterns if p.get('direction')==('bullish' if sign>0 else 'bearish')}
    opposing=[p for p in patterns if p.get('direction')==('bearish' if sign>0 else 'bullish') and p.get('state')=='confirmed']
    pattern=bool(pattern_names) and not opposing
    candle_patterns=observations.get('candlestick_patterns') or []
    candle=any(item.get('direction')==('bullish' if sign>0 else 'bearish') and item.get('timeframe') in {'M1','M5'} for item in candle_patterns)
    fibs=observations.get('fibonacci') or {}
    fibonacci=any(bool(item.get('reacting')) and item.get('swing_direction')==('up' if sign>0 else 'down') for item in fibs.values())
    key_levels=observations.get('key_levels') or {}
    blocked_level=False
    if entry is not None and target is not None:
        opposing_level=key_levels.get('resistance' if sign>0 else 'support')
        if isinstance(opposing_level,(int,float)):
            blocked_level=(entry<float(opposing_level)<=target) if sign>0 else (target<=float(opposing_level)<entry)
    levels=not blocked_level
    rsi=m5.get('rsi'); roc=m5.get('roc'); momentum=(rsi is not None and roc is not None and 35<=float(rsi)<=70 and sign*float(roc)>0) if sign>0 else (rsi is not None and roc is not None and 30<=float(rsi)<=65 and sign*float(roc)>0)
    vol=m15.get('atr_pct'); baseline=m15.get('atr_pct_baseline')
    volatility=(vol is not None and float(vol)>0 and (baseline is None or .5<=float(vol)/max(float(baseline),1e-12)<=2.0))
    session=bool((observations.get('session') or {}).get('active',False))
    context=observations.get('signal_context') or observations.get('market_context') or {}
    context_direction=context.get('direction') if isinstance(context,dict) else None
    context_ok=not context_direction or context_direction in {'neutral','mixed',direction,'bullish' if sign>0 else 'bearish'}
    values={'trend':trend,'location':bool(location),'pattern':pattern,'candle':candle,'fibonacci':fibonacci,'levels':levels,'momentum':bool(momentum),'volatility':bool(volatility),'session':session,'context':bool(context_ok)}
    blockers=[]
    if opposing: blockers.append('confirmed opposing chart pattern')
    if blocked_level: blockers.append('take-profit blocked by key level')
    total=sum(max(0,float(weights.get(name,1.0))) for name in values)
    score=sum(max(0,float(weights.get(name,1.0))) for name,passed in values.items() if passed)/total if total else 0.0
    az={'trend':'Trend istiqaməti uyğundur','location':'Qiymət dəstək/müqavimət zonasındadır','pattern':'Qrafik quruluşu istiqaməti dəstəkləyir','candle':'Təsdiq şamı var','fibonacci':'Fibonacci reaksiyası var','levels':'Hədəf əsas səviyyə ilə tutulmur','momentum':'Momentum istiqaməti dəstəkləyir','volatility':'Dəyişkənlik normal həddədir','session':'Alətin sessiyası aktivdir','context':'Bazar konteksti uyğundur'}
    passed=[name for name,value in values.items() if value]
    reason='; '.join(az[name] for name in passed[:3]) or 'Təsdiqləyici amil aşkarlanmadı'
    return {'score':float(score),'items':values,'passed':passed,'blocking_failures':blockers,'reason':reason}
