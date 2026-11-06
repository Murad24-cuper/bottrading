"""Conservative fractional-Kelly sizing helpers."""
from __future__ import annotations

def fractional_kelly_risk_pct(probability: float, avg_win_r: float, fraction: float=.25,
                              minimum: float=.1, maximum: float=.5) -> float:
    """Return a bounded risk percentage; non-positive edge always maps to zero."""
    p=float(probability); b=float(avg_win_r)
    if not 0<p<1 or b<=0: return 0.0
    kelly=float(fraction)*(p*b-(1-p))/b
    return min(float(maximum),max(float(minimum),kelly*100)) if kelly>0 else 0.0
