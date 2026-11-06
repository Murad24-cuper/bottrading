"""Short-horizon pullback entries aligned with M15 and M5 trend."""
from ..strategy_base import Strategy
from .. import indicators as ind
from .common import frame,finite,signal

class TrendPullbackStrategy(Strategy):
    name='trend_pullback'; required_timeframes=['M1','M5','M15']
    def __init__(self,params=None): self.params=dict(params or {})
    def generate_signal(self,symbol,candles):
        m1=frame(candles,'M1',60); m15=frame(candles,'M15',60); m5=frame(candles,'M5',60)
        if any(x is None for x in (m1,m15,m5)): return self._skip('missing_required_timeframe')
        fast=int(self.params.get('trend_ema_fast',20)); slow=int(self.params.get('trend_ema_slow',50)); adx_min=float(self.params.get('adx_min',18))
        def trend(data):
            efast=ind.ema(data.close,fast).iloc[-1]; eslow=ind.ema(data.close,slow).iloc[-1]; a=ind.adx(data).adx.iloc[-1]
            return efast,eslow,a
        m1fast,m1slow,m1a=trend(m1); mfast,mslow,ma=trend(m15)
        atr=ind.atr(m5).iloc[-1]; entry=float(m5.close.iloc[-1]); line=ind.ema(m5.close,fast); prev_line=line.iloc[-2]
        if not finite(m1fast,m1slow,m1a,mfast,mslow,ma,atr,entry,prev_line): return self._skip('indicator_values_not_ready')
        tolerance=float(self.params.get('pullback_atr',.45))*atr; stop_mult=float(self.params.get('stop_atr',1.5)); rr=float(self.params.get('reward_risk',1.8))
        pclose=float(m5.close.iloc[-2]); plow=float(m5.low.iloc[-2]); phigh=float(m5.high.iloc[-2]); rsi=ind.rsi(m5.close).iloc[-1]
        uptrend=m1fast>m1slow and mfast>mslow; downtrend=m1fast<m1slow and mfast<mslow
        if not uptrend and not downtrend: return self._skip('higher_timeframe_trend_not_aligned')
        if m1a<adx_min or ma<adx_min: return self._skip('adx_below_minimum')
        if uptrend and entry>line.iloc[-1] and plow<=prev_line+tolerance and rsi>=48:
            structure=float(m5.low.iloc[-8:].min()); sl=min(entry-stop_mult*atr,structure-.05*atr); tp=entry+(entry-sl)*rr
            confidence=min(.95,.55+(m1a+ma)/300+max(0,(entry-line.iloc[-1])/atr)*.05)
            return signal(symbol,'buy','M5',entry,sl,tp,confidence,self.name,'M1/M15 uptrend; M5 pullback resumed')
        if downtrend and entry<line.iloc[-1] and phigh>=prev_line-tolerance and rsi<=52:
            structure=float(m5.high.iloc[-8:].max()); sl=max(entry+stop_mult*atr,structure+.05*atr); tp=entry-(sl-entry)*rr
            confidence=min(.95,.55+(m1a+ma)/300+max(0,(line.iloc[-1]-entry)/atr)*.05)
            return signal(symbol,'sell','M5',entry,sl,tp,confidence,self.name,'M1/M15 downtrend; M5 pullback resumed')
        if (uptrend and rsi<48) or (downtrend and rsi>52): return self._skip('rsi_confirmation_failed')
        return self._skip('pullback_not_confirmed')
