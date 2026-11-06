"""Range breakout entries confirmed by ATR expansion and tick volume."""
from ..strategy_base import Strategy
from .. import indicators as ind
from .common import frame,finite,signal

class BreakoutStrategy(Strategy):
    name='breakout'; required_timeframes=['M15']
    def __init__(self,params=None): self.params=dict(params or {})
    def generate_signal(self,symbol,candles):
        data=frame(candles,'M15',40)
        if data is None: return self._skip('missing_M15_history')
        n=int(self.params.get('range_bars',20)); old=data.iloc[-n-1:-1]
        if len(old)<n: return self._skip('insufficient_range_history')
        hi=float(old.high.max()); lo=float(old.low.min()); entry=float(data.close.iloc[-1]); a=ind.atr(data).iloc[-1]
        atr_series=ind.atr(data); baseline=atr_series.iloc[-n-1:-1].mean(); vol=data.tick_volume if 'tick_volume' in data else None
        vol_mean=vol.iloc[-n-1:-1].mean() if vol is not None else 0; vol_ratio=float(vol.iloc[-1]/vol_mean) if vol_mean and vol_mean>0 else 0
        if not finite(a,baseline,hi,lo,entry) or hi<=lo: return self._skip('indicator_values_not_ready')
        if a<baseline*float(self.params.get('atr_expansion',1.1)): return self._skip('atr_expansion_below_minimum')
        if vol_ratio<float(self.params.get('volume_ratio',1.2)): return self._skip('tick_volume_below_minimum')
        height=hi-lo; reward=max(height*float(self.params.get('reward_range',1.5)),a)
        if entry>hi:
            sl=max(lo,hi-.15*a); tp=entry+reward; confidence=min(.95,.55+(a/baseline-1)*.15+(vol_ratio-1)*.08)
            return signal(symbol,'buy','M15',entry,sl,tp,confidence,self.name,'Close broke range high with volatility and volume expansion')
        if entry<lo:
            sl=min(hi,lo+.15*a); tp=entry-reward; confidence=min(.95,.55+(a/baseline-1)*.15+(vol_ratio-1)*.08)
            return signal(symbol,'sell','M15',entry,sl,tp,confidence,self.name,'Close broke range low with volatility and volume expansion')
        return self._skip('range_not_broken')
