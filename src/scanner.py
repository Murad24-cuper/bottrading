"""Sequential, read-only live-market scanner with bounded work per cycle."""
from __future__ import annotations
from dataclasses import dataclass
from time import perf_counter
from datetime import datetime,timezone
from collections import Counter, defaultdict
import math
from . import market_data
from . import indicators as ind
from .features import build_features
from .risk import calc_volume
from .strategies import load_strategies
from .symbols import SymbolService

@dataclass
class Candidate:
    symbol:str
    asset_group:str
    strategy:str
    signal:object
    confidence:float
    volume:float
    risk_money:float
    reward_money:float
    cost:dict
    score:float
    features:dict
    symbol_spec:dict
    skip_reason:str=''
    signal_row_id:int|None=None

def expected_value_score(confidence,reward_money,risk_money,cost):
    return float(confidence)*float(reward_money)-(1-float(confidence))*float(risk_money)-float(cost)

def rank_candidates(candidates):
    """Discard non-positive scores and keep the best signal for each symbol."""
    best={}
    for item in candidates:
        if item.score<=0: continue
        prior=best.get(item.symbol)
        if prior is None or item.score>prior.score: best[item.symbol]=item
    return sorted(best.values(),key=lambda item:item.score,reverse=True)

class MarketScanner:
    def __init__(self,mt5,settings,db,symbol_service=None):
        self.mt5,self.settings,self.db=mt5,settings,db
        self.symbols=symbol_service or SymbolService(mt5,settings)
        self._cache={}; self._cursor=0; self._strategies=load_strategies(settings); self.last_universe_size=0
        self._volatility_cache={}; self.last_scan_stats={}; self.last_strategy_diagnostics={}
    def _bars(self,symbol,timeframe,count):
        key=(symbol,timeframe); cached=self._cache.get(key)
        try:
            latest=market_data.get_closed_candles(self.mt5,symbol,timeframe,1)
        except RuntimeError as exc:
            self.db.log_event('WARNING','scanner',f'Skipping {symbol} {timeframe}: closed-bar read failed: {exc}')
            return None
        if latest.empty: return cached
        if cached is None or cached.empty or latest.index[-1]>cached.index[-1]:
            try:
                cached=market_data.get_closed_candles(self.mt5,symbol,timeframe,count)
            except RuntimeError as exc:
                self.db.log_event('WARNING','scanner',f'Skipping {symbol} {timeframe}: history refresh failed: {exc}')
                return None
            info=self.mt5.symbol_info(symbol); point=float(self.settings.config['scanner'].get('timeframe_point_sizes',{}).get(symbol) or (info.point if info and info.point else 0.0))
            cached=cached.copy(); cached['spread_points']=cached['spread']; cached['point_size']=point; cached['spread_price']=cached['spread']*point
            self._cache[key]=cached
        return cached
    def scan_once(self):
        started=perf_counter(); cfg=self.settings.config['scanner']
        candidates=self.symbols.get_candidates() if hasattr(self.symbols,'get_candidates') else self.symbols.get_universe()
        owned=[p for p in (self.mt5.positions_get() or []) if int(p.magic)==self.settings.magic_number] if hasattr(self.mt5,'positions_get') else []
        open_symbols={str(p.symbol) for p in owned}
        universe=list(dict.fromkeys([*candidates,*sorted(open_symbols)])); self.last_universe_size=len(universe)
        stage1=[]; rejection=Counter(); snapshots={}; movement=[]; move_rejections=Counter()
        budget=float(cfg['max_seconds_per_cycle']); start=self._cursor%max(1,len(universe)); visited=0
        minutes=int(cfg['movement_timeframe_minutes']); m1_count=max(10,minutes)
        while visited<len(universe):
            if visited and perf_counter()-started>=budget: break
            symbol=universe[(start+visited)%len(universe)]; visited+=1
            force=symbol in open_symbols
            if not force:
                ok,reason=self.symbols.is_tradable(symbol)
                if not ok: rejection[reason]+=1; continue
            info=self.mt5.symbol_info(symbol); tick=self.mt5.symbol_info_tick(symbol) if hasattr(self.mt5,'symbol_info_tick') else None
            if not force and (info is None or tick is None): rejection['tick unavailable']+=1; continue
            point=float(getattr(info,'point',0) or 0) if info else 0.0
            spread_price=max(0.0,float(tick.ask)-float(tick.bid)) if tick else 0.0
            cached=self._volatility_cache.get(symbol); max_ratio=float(cfg['max_spread_volatility_ratio'])
            if not force and cached and (datetime.now(timezone.utc)-cached['time']).total_seconds()<=int(cfg['movement_timeframe_minutes'])*60 and cached['atr']>0 and spread_price/cached['atr']>max_ratio:
                rejection['spread too high relative to recent volatility']+=1; continue
            snapshots[symbol]={'point':point,'spread_price':spread_price}
            stage1.append(symbol)
            frame=self._bars(symbol,'M1',m1_count)
            if frame is None or len(frame)<5:
                frame=self._bars(symbol,'M5',max(3,(minutes+4)//5))
            if frame is None or len(frame)<3:
                if symbol in open_symbols: movement.append((float('-inf'),symbol)); continue
                move_rejections['recent movement unavailable']+=1; continue
            price=float(frame.close.iloc[-1]); recent_range=float(frame.high.tail(m1_count).max()-frame.low.tail(m1_count).min())
            atr=float(ind.atr(frame).iloc[-1]); spread_price=snapshots.get(symbol,{}).get('spread_price',0.0)
            if spread_price<=0 and 'spread' in frame:
                point=snapshots.get(symbol,{}).get('point',0.0); spread_price=float(frame.spread.iloc[-1])*point
            if not price or not math.isfinite(price) or not math.isfinite(atr) or atr<=0:
                if symbol in open_symbols: movement.append((float('-inf'),symbol)); continue
                move_rejections['movement indicators unavailable']+=1; continue
            spread_ratio=spread_price/atr if spread_price else 0.0
            self._volatility_cache[symbol]={'atr':atr,'time':datetime.now(timezone.utc)}
            if symbol not in open_symbols and spread_ratio>max_ratio:
                move_rejections['spread too high relative to recent volatility']+=1; continue
            relative_range=recent_range/max(spread_price,snapshots.get(symbol,{}).get('point',0.0)*.01,1e-12)
            score=(recent_range/price)*math.log1p(relative_range)
            movement.append((score,symbol))
        self._cursor=(start+visited)%max(1,len(universe))
        top_n=int(cfg['top_movers'])
        ranked=sorted(movement,key=lambda item:item[0],reverse=True)
        top_symbols=[symbol for _,symbol in ranked[:top_n]]
        top_symbols.extend(symbol for symbol in sorted(open_symbols) if symbol not in top_symbols)
        results=[]; strategy_diagnostics=defaultdict(Counter)
        for symbol in top_symbols:
            group=self.symbols.get_asset_group(symbol); strategies=[s for s in self._strategies if group in s.allowed_groups]
            needed=sorted({tf for strategy in strategies for tf in strategy.required_timeframes})
            if not needed: continue
            candles={tf:self._bars(symbol,tf,int(cfg['candle_count'])) for tf in needed}
            candles={tf:df for tf,df in candles.items() if df is not None and len(df)>=60}
            if not candles: continue
            features=build_features(candles); info=self.mt5.symbol_info(symbol)
            if info is None: continue
            spec=info._asdict(); account=self.mt5.account_info()
            if account is None: continue
            for strategy in strategies:
                if any(tf not in candles for tf in strategy.required_timeframes):
                    strategy_diagnostics[strategy.name]['required_timeframe_missing']+=1; continue
                strategy.last_skip_reason='conditions_not_met'
                signal=strategy.generate_signal(symbol,candles)
                if signal is None:
                    strategy_diagnostics[strategy.name][getattr(strategy,'last_skip_reason','conditions_not_met')]+=1; continue
                if signal.sl_price is None or signal.tp_price is None or signal.entry_hint is None:
                    self._write_signal(signal,0,'signal missing entry, SL, or TP'); continue
                if signal.direction=='buy' and not signal.sl_price<signal.entry_hint<signal.tp_price:
                    self._write_signal(signal,0,'invalid stop/target side'); continue
                if signal.direction=='sell' and not signal.tp_price<signal.entry_hint<signal.sl_price:
                    self._write_signal(signal,0,'invalid stop/target side'); continue
                volume,volume_reason=calc_volume(account.equity,self.settings.risk.risk_per_trade_pct,signal.entry_hint,signal.sl_price,spec)
                if volume<=0:
                    self._write_signal(signal,0,volume_reason); continue
                cost=market_data.get_cost_estimate(self.mt5,symbol,volume)
                risk_money=market_data.price_distance_to_money(self.mt5,symbol,abs(signal.entry_hint-signal.sl_price),volume)
                reward_money=market_data.price_distance_to_money(self.mt5,symbol,abs(signal.tp_price-signal.entry_hint),volume)
                score=expected_value_score(signal.confidence,reward_money,risk_money,cost['cost'])
                reason='expected value is non-positive' if score<=0 else ('below scanner.min_score' if score<float(cfg['min_score']) else '')
                candidate=Candidate(symbol,group,strategy.name,signal,signal.confidence,volume,risk_money,reward_money,cost,score,features,spec,reason)
                candidate.signal_row_id=self._write_signal(signal,cost['cost'],reason,score); results.append(candidate)
        self.last_strategy_diagnostics={name:dict(counts) for name,counts in strategy_diagnostics.items()}
        self._cursor=0
        best=rank_candidates([c for c in results if not c.skip_reason])
        winners={c.symbol:c for c in best}
        for item in results:
            if item.symbol in winners and winners[item.symbol] is not item: item.skip_reason='superseded by higher-scoring signal for symbol'
            if item.skip_reason and item.signal_row_id is not None: self._set_skip_reason(item.signal_row_id,item.skip_reason)
        limit=int(cfg['max_candidates'])
        selected=best[:limit]
        for item in best[limit:]:
            item.skip_reason='scanner candidate limit reached'
            if item.signal_row_id is not None: self._set_skip_reason(item.signal_row_id,item.skip_reason)
        elapsed=perf_counter()-started
        self.last_scan_stats={'total_symbols':len(universe),'symbols_scanned':visited,'scan_complete':visited>=len(universe),'stage1_passed':len(stage1),'top_movers':len(top_symbols),'signals':len(results),'scan_seconds':round(elapsed,3),'stage1_rejections':dict(rejection+move_rejections),'strategy_diagnostics':self.last_strategy_diagnostics}
        if visited<len(universe): self.db.log_event('INFO','scanner',f'Scan budget reached after {visited}/{len(universe)} symbols; rotation resumes at {self._cursor}')
        self.db.log_event('INFO','scanner',f"Scan total={len(universe)} scanned={visited} complete={visited>=len(universe)} stage1_passed={len(stage1)} top_movers={len(top_symbols)} signals={len(results)} seconds={elapsed:.3f} stage1_rejections={dict(rejection+move_rejections)} strategy_diagnostics={self.last_strategy_diagnostics}")
        return selected
    def scan(self):
        """Part 3 live-loop interface; performs one bounded, read-only scan."""
        return self.scan_once()
    def _write_signal(self,signal,cost,skip_reason,score=0.0):
        return self.db.insert_signal(time=datetime.now(timezone.utc).isoformat(),symbol=signal.symbol,strategy=signal.strategy_name,direction=signal.direction,timeframe=signal.timeframe,confidence=signal.confidence,entry=signal.entry_hint,sl=signal.sl_price,tp=signal.tp_price,expected_cost=cost,score=score,taken=0,skip_reason=skip_reason or '')
    def _set_skip_reason(self,row_id,reason):
        with self.db.connect() as connection:
            connection.execute('UPDATE signals SET skip_reason=? WHERE id=?',(reason,row_id))
