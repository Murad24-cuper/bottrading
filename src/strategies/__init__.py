"""Strategy registry. Strategies are enabled and parameterized in config.yaml."""
from __future__ import annotations
from .trend_pullback import TrendPullbackStrategy
from .mean_reversion import MeanReversionStrategy
from .breakout import BreakoutStrategy
from .volatility_scalp import VolatilityScalpStrategy

REGISTRY={cls.name:cls for cls in (TrendPullbackStrategy,MeanReversionStrategy,BreakoutStrategy,VolatilityScalpStrategy)}

def load_strategies(settings,asset_group=None):
    config=settings.config if hasattr(settings,'config') else settings
    entries=config.get('strategies',{}); result=[]
    for name,cls in REGISTRY.items():
        entry=entries.get(name,{})
        if not entry.get('enabled',False): continue
        groups=entry.get('groups',[])
        if asset_group is not None and asset_group not in groups: continue
        strategy=cls(entry.get('params',{})); strategy.allowed_groups=list(groups)
        strategy.required_timeframes=list(entry.get('timeframes',strategy.required_timeframes))
        result.append(strategy)
    return result
