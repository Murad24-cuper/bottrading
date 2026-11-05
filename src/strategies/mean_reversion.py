"""Range-bound Bollinger/RSI reversion toward the rolling mean."""
from ..strategy_base import Strategy
from .. import indicators as ind
from ..features import _regime,_timeframe_features
from .common import frame,finite,signal

class MeanReversionStrategy(Strategy):
    name='mean_reversion'; required_timeframes=['M15']
    def __init__(self,params=None): self.params=dict(params or {})
    def generate_signal(self,symbol,candles):
        data=frame(candles,'M15',40)
        if data is None or _regime({'M15':_timeframe_features(data)})!='ranging': return None
        period=int(self.params.get('bb_period',20)); dev=float(self.params.get('bb_std',2)); rperiod=int(self.params.get('rsi_period',14))
        bands=ind.bollinger(data.close,period,dev); rsi=ind.rsi(data.close,rperiod); atr=ind.atr(data,rperiod)
        entry=float(data.close.iloc[-1]); lower=bands.bb_lower.iloc[-1]; mid=bands.bb_mid.iloc[-1]; upper=bands.bb_upper.iloc[-1]; a=atr.iloc[-1]; rv=rsi.iloc[-1]
        support=ind.nearest_levels(data).support.iloc[-1]; resistance=ind.nearest_levels(data).resistance.iloc[-1]
        if not finite(entry,lower,mid,upper,a,rv): return None
        near=float(self.params.get('near_level_atr',.75)); stop_mult=float(self.params.get('stop_atr',1.2))
        if entry<lower and rv<=float(self.params.get('rsi_low',30)) and finite(support) and abs(entry-support)<=near*a:
            sl=min(entry-stop_mult*a,float(data.low.iloc[-5:].min())-.05*a); tp=mid
            confidence=min(.9,.55+(float(lower)-entry)/a*.08+(float(self.params.get('rsi_low',30))-rv)/100)
            return signal(symbol,'buy','M15',entry,sl,tp,confidence,self.name,'Range stretch below lower band; target mean')
        if entry>upper and rv>=float(self.params.get('rsi_high',70)) and finite(resistance) and abs(resistance-entry)<=near*a:
            sl=max(entry+stop_mult*a,float(data.high.iloc[-5:].max())+.05*a); tp=mid
            confidence=min(.9,.55+(entry-float(upper))/a*.08+(rv-float(self.params.get('rsi_high',70)))/100)
            return signal(symbol,'sell','M15',entry,sl,tp,confidence,self.name,'Range stretch above upper band; target mean')
        return None
