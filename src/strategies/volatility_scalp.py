"""Short-horizon momentum scalps with an explicit spread/target gate."""
from ..strategy_base import Strategy
from .. import indicators as ind
from .common import frame,finite,signal

class VolatilityScalpStrategy(Strategy):
    name='volatility_scalp'; required_timeframes=['M1','M5']
    def __init__(self,params=None): self.params=dict(params or {})
    def generate_signal(self,symbol,candles):
        data=frame(candles,'M1',40)
        if data is None: data=frame(candles,'M5',40)
        if data is None: return None
        period=int(self.params.get('atr_period',14)); atr=ind.atr(data,period); current=atr.iloc[-1]; baseline=atr.iloc[-30:-1].mean()
        entry=float(data.close.iloc[-1]); target_mult=float(self.params.get('target_atr',.4)); stop_mult=float(self.params.get('stop_atr',.3))
        if not finite(current,baseline,entry) or baseline<=0 or current<baseline*float(self.params.get('volatility_ratio',1.25)): return None
        target=current*target_mult; stop=current*stop_mult
        spread_price=None
        if 'spread_price' in data: spread_price=float(data.spread_price.iloc[-1])
        elif 'spread_points' in data and 'point_size' in self.params: spread_price=float(data.spread_points.iloc[-1])*float(self.params['point_size'])
        if spread_price is None or spread_price<0 or spread_price/target>float(self.params.get('max_spread_target_ratio',.2)): return None
        delta=entry-float(data.close.iloc[-2]);
        if delta>0:
            sl=entry-stop; tp=entry+target; confidence=min(.9,.52+min(.25,abs(delta)/current*.2)+(current/baseline-1)*.05)
            return signal(symbol,'buy','M1' if 'M1' in candles else 'M5',entry,sl,tp,confidence,self.name,'High volatility momentum; spread below target limit')
        if delta<0:
            sl=entry+stop; tp=entry-target; confidence=min(.9,.52+min(.25,abs(delta)/current*.2)+(current/baseline-1)*.05)
            return signal(symbol,'sell','M1' if 'M1' in candles else 'M5',entry,sl,tp,confidence,self.name,'High volatility momentum; spread below target limit')
        return None
