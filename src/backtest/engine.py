"""Bar-by-bar multi-symbol simulator with conservative fills and risk checks."""
from __future__ import annotations
from dataclasses import dataclass,replace
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
import math
import pandas as pd
from ..risk import calc_volume,check_trade_allowed
from ..market_data import price_distance_to_money
from ..scanner import expected_value_score
from ..strategies import load_strategies
from .. import indicators as ind

TF_DELTA={'M1':timedelta(minutes=1),'M5':timedelta(minutes=5),'M15':timedelta(minutes=15),'H1':timedelta(hours=1)}

@dataclass
class BacktestResult:
    trades:list[dict]
    equity_curve:list[dict]

class Backtester:
    def __init__(self,settings,symbol_specs=None,equity=None,strategies=None):
        self.settings=settings; self.specs=symbol_specs or {}; self.start_equity=float(equity if equity is not None else settings.config['backtest']['start_equity'])
        self.strategies=strategies if strategies is not None else load_strategies(settings)
    def _point(self,symbol,spec): return float(spec.get('point_size',spec.get('point',spec.get('trade_tick_size',1e-5))) or 1e-5)
    def _spread_points(self,row):
        value=row.get('spread',self.settings.config['backtest']['fallback_spread_points'])
        try: value=float(value)
        except (TypeError,ValueError): value=float(self.settings.config['backtest']['fallback_spread_points'])
        if not math.isfinite(value) or value<0: value=float(self.settings.config['backtest']['fallback_spread_points'])
        return value
    def run(self,history:dict[str,dict[str,pd.DataFrame]]) -> BacktestResult:
        data={sym:{tf:frame.sort_index() for tf,frame in frames.items() if tf in TF_DELTA and frame is not None and not frame.empty} for sym,frames in history.items()}
        scalpers=[strategy for strategy in self.strategies if strategy.name=='volatility_scalp']
        if scalpers:
            scalp=scalpers[0]; period=int(scalp.params.get('atr_period',14))
            for symbol,frames in data.items():
                tf='M1' if 'M1' in frames else 'M5' if 'M5' in frames else None
                if tf is None: continue
                frame=frames[tf].copy(); points=float(self.specs.get(symbol,{}).get('point_size',self.specs.get(symbol,{}).get('point',1e-5)) or 1e-5)
                spread=frame['spread'] if 'spread' in frame else self.settings.config['backtest']['fallback_spread_points']
                frame['__scalp_atr']=ind.atr(frame,period)
                frame['__scalp_baseline']=frame['__scalp_atr'].shift(1).rolling(29,min_periods=29).mean()
                frame['__scalp_spread_price']=spread*points
                frames[tf]=frame
        base_tf={}; timeline=set()
        for symbol,frames in data.items():
            choices=[tf for tf in ('M1','M5','M15','H1') if tf in frames]
            if choices: base_tf[symbol]=choices[0]; timeline.update(frames[choices[0]].index.to_pydatetime())
        timeline=sorted(timeline)
        signal_lookback=int(self.settings.config['backtest'].get('signal_lookback_bars',300))
        balance=self.start_equity; positions={}; pending={}; trades=[]; curve=[]; last_prices={}; last_signal_bar={}; daily_pnl={}; weekly_pnl={}; symbol_trade_counts={}; symbol_last_close={}; commission=float(self.settings.config['backtest']['commission_per_lot_per_side']); slippage=float(self.settings.config['backtest']['slippage_points'])
        account_currency='USD'
        def floating_total(): return sum(float(p.get('profit',0)) for p in positions.values())
        def close_position(symbol,pos,when,price,reason,spread_price):
            nonlocal balance
            spec=self.specs.get(symbol,{})
            exit_slip=slippage*self._point(symbol,spec)
            if pos['direction']=='buy': exit_price=price-exit_slip; sign=1
            else: exit_price=price+spread_price+exit_slip; sign=-1
            tick_size=float(spec.get('trade_tick_size',spec.get('tick_size',0)) or 0)
            tick_value=float(spec.get('trade_tick_value',spec.get('tick_value',spec.get('trade_tick_value_loss',0))) or 0)
            factor=tick_value/tick_size if tick_size>0 and tick_value>0 else 1.0
            gross=(exit_price-pos['entry_price'])*sign*pos['volume']*factor
            exit_commission=commission*pos['volume']; balance+=gross-exit_commission
            net=gross-pos['entry_commission']-exit_commission
            cost=pos['spread_cost']+pos['entry_commission']+exit_commission+pos['slippage_cost']+abs(exit_price-price)*factor*pos['volume']
            trades.append({'symbol':symbol,'asset_group':pos['asset_group'],'strategy':pos['strategy'],'direction':pos['direction'],'volume':pos['volume'],'open_time':pos['open_time'].isoformat(),'close_time':when.isoformat(),'open_price':pos['entry_price'],'close_price':exit_price,'sl':pos['sl'],'tp':pos['tp'],'profit':gross,'commission':-(pos['entry_commission']+exit_commission),'swap':0.0,'net_profit':net,'costs':cost,'close_reason':reason,'holding_minutes':(when-pos['open_time']).total_seconds()/60,'hour':pos['open_time'].hour})
            symbol_last_close[symbol]=when
            return net
        for open_time in timeline:
            event_positions=[]
            for symbol,tf in base_tf.items():
                frame=data[symbol][tf]
                if open_time in frame.index: event_positions.append((symbol,tf,frame.loc[open_time]))
            for symbol,tf,row in event_positions:
                spec=self.specs.get(symbol,{})
                point=self._point(symbol,spec); spread_pts=self._spread_points(row); spread_price=spread_pts*point; bar_end=open_time+TF_DELTA[tf]
                last_prices[symbol]=(float(row.close),spread_price)
                # Fill signals formed on the preceding closed bar at this bar's open.
                for queued in pending.pop((symbol,open_time),[]):
                    if symbol in positions: continue
                    signal=queued['signal']; entry_base=float(row.open); entry=entry_base+spread_price if signal.direction=='buy' else entry_base
                    entry+=slippage*point if signal.direction=='buy' else -slippage*point
                    adjusted=replace(signal,entry_hint=entry)
                    volume,why=calc_volume(balance+floating_total(),self.settings.risk.risk_per_trade_pct,entry,signal.sl_price,spec)
                    if volume<=0: continue
                    tick_value_loss=float(spec.get('trade_tick_value_loss',spec.get('trade_tick_value',spec.get('tick_value',0))))
                    tick_value_profit=float(spec.get('trade_tick_value_profit',spec.get('trade_tick_value',tick_value_loss)))
                    tick_size=float(spec.get('trade_tick_size',spec.get('tick_size',0)))
                    if tick_value_loss<=0 or tick_value_profit<=0 or tick_size<=0: continue
                    target_money=abs(signal.tp_price-entry)/tick_size*tick_value_profit*volume
                    risk_money=abs(entry-signal.sl_price)/tick_size*tick_value_loss*volume
                    spread_cost=spread_price/tick_size*float(spec.get('trade_tick_value',tick_value_loss))*volume
                    cost_est={'cost':spread_cost+2*commission*volume,'commission_known':True}
                    open_dicts=[{**p,'profit':p.get('profit',0)} for p in positions.values()]
                    margin=float(spec.get('margin_per_lot',0))*volume
                    eq=balance+floating_total(); account=SimpleNamespace(balance=balance,equity=eq,margin=sum(float(p.get('margin',0)) for p in positions.values()))
                    now=bar_end
                    cooldown=int(getattr(self.settings.risk,'symbol_cooldown_minutes',0)); last_close=symbol_last_close.get(symbol)
                    cooldown_active=bool(cooldown and last_close and now-last_close<timedelta(minutes=cooldown))
                    trades_today=symbol_trade_counts.get((symbol,now.date()),0)
                    allowed,_=check_trade_allowed(adjusted,account,open_dicts,daily_pnl.get(now.date(),0),weekly_pnl.get((now-isoweekday_delta(now)).date(),0),self.settings,cost_est,queued['group'],now,margin,volume,spec,cooldown_active,trades_today)
                    if not allowed or target_money<=0 or expected_value_score(signal.confidence,target_money,risk_money,cost_est['cost'])<=0: continue
                    entry_commission=commission*volume; balance-=entry_commission
                    cost_tick_value=float(spec.get('trade_tick_value',tick_value_loss))
                    positions[symbol]={'entry_price':entry,'entry_base':entry_base,'open_time':open_time,'direction':signal.direction,'volume':volume,'sl':signal.sl_price,'tp':signal.tp_price,'strategy':signal.strategy_name,'asset_group':queued['group'],'entry_commission':entry_commission,'spread_cost':spread_cost,'slippage_cost':slippage*point/tick_size*cost_tick_value*volume,'margin':margin,'profit':0.0}
                    symbol_trade_counts[(symbol,now.date())]=trades_today+1
                # Intrabar exits use bid OHLC and ask OHLC. If stop and target both hit, stop wins.
                pos=positions.get(symbol)
                if pos:
                    low=float(row.low); high=float(row.high); close=float(row.close)
                    if pos['direction']=='buy': sl_hit=low<=pos['sl']; tp_hit=high>=pos['tp']
                    else: sl_hit=high+spread_price>=pos['sl']; tp_hit=low+spread_price<=pos['tp']
                    if sl_hit or tp_hit:
                        level=pos['sl'] if sl_hit else pos['tp']; reason='sl' if sl_hit else 'tp'
                        fill_reference=level if pos['direction']=='buy' else level-spread_price
                        net=close_position(symbol,pos,bar_end,fill_reference,reason,spread_price); daily_pnl[bar_end.date()]=daily_pnl.get(bar_end.date(),0)+net; monday=(bar_end-timedelta(days=bar_end.weekday())).date(); weekly_pnl[monday]=weekly_pnl.get(monday,0)+net; positions.pop(symbol)
                    else:
                        max_hold=self.settings.risk.max_hold_minutes
                        weekend=bar_end.weekday()==4 and bar_end.strftime('%H:%M')>=self.settings.risk.close_all_friday_utc
                        timed=(bar_end-pos['open_time']).total_seconds()>=max_hold*60
                        if weekend or timed:
                            reason='weekend' if weekend else 'time'; net=close_position(symbol,pos,bar_end,close,reason,spread_price)
                            daily_pnl[bar_end.date()]=daily_pnl.get(bar_end.date(),0)+net; monday=(bar_end-timedelta(days=bar_end.weekday())).date(); weekly_pnl[monday]=weekly_pnl.get(monday,0)+net; positions.pop(symbol)
                # Generate at the close. Each strategy runs only when its own trigger bar advances.
                for strategy in self.strategies:
                    group=self.specs.get(symbol,{}).get('asset_group','other')
                    if group not in getattr(strategy,'allowed_groups',[group]): continue
                    available=[value for value in strategy.required_timeframes if value in data[symbol]]
                    trigger=min(available,key=lambda value:TF_DELTA[value]) if available else (tf if not strategy.required_timeframes else None)
                    if trigger is None: continue
                    if trigger not in data[symbol]: continue
                    trigger_frame=data[symbol][trigger]; trigger_index=trigger_frame.index
                    complete_count=trigger_index.searchsorted(bar_end-TF_DELTA[trigger],side='right')
                    if complete_count<=0: continue
                    trigger_stamp=trigger_index[complete_count-1]
                    key=(symbol,strategy.name)
                    if last_signal_bar.get(key)==trigger_stamp: continue
                    last_signal_bar[key]=trigger_stamp
                    if trigger!=tf and bar_end!=trigger_stamp+TF_DELTA[trigger]: continue
                    supplied={}
                    for name,frame in data[symbol].items():
                        complete_count=frame.index.searchsorted(bar_end-TF_DELTA[name],side='right')
                        if complete_count>0:
                            supplied[name]=frame.iloc[max(0,complete_count-signal_lookback):complete_count]
                    sig=strategy.generate_signal(symbol,supplied)
                    if sig is None or symbol in positions: continue
                    indices=data[symbol][tf].index; next_pos=indices.searchsorted(open_time,side='right')
                    if next_pos>=len(indices): continue
                    next_idx=indices[next_pos]
                    spec0=self.specs.get(symbol,{})
                    pending.setdefault((symbol,next_idx),[]).append({'signal':sig,'group':spec0.get('asset_group','other'),'strategy':strategy.name})
            # Refresh floating profit and append one portfolio equity point for every event time.
            for symbol,pos in positions.items():
                if symbol not in last_prices: continue
                close,spread=last_prices[symbol]; spec=self.specs.get(symbol,{})
                mark=close if pos['direction']=='buy' else close+spread
                sign=1 if pos['direction']=='buy' else -1
                value=float(spec.get('trade_tick_value',spec.get('tick_value',spec.get('trade_tick_value_loss',0))))/float(spec.get('trade_tick_size',spec.get('tick_size',0)) or 1)
                pos['profit']=(mark-pos['entry_price'])*sign*pos['volume']*value
            curve.append({'time':open_time.isoformat(),'balance':balance,'equity':balance+floating_total(),'open_positions':len(positions)})
        # Force-close residual positions at the final observed quote so summaries are realized.
        if timeline:
            final_time=timeline[-1]+timedelta(minutes=1)
            for symbol,pos in list(positions.items()):
                close,spread=last_prices.get(symbol,(pos['entry_price'],0))
                net=close_position(symbol,pos,final_time,close,'end_of_data',spread)
                positions.pop(symbol)
            curve.append({'time':final_time.isoformat(),'balance':balance,'equity':balance,'open_positions':0})
        return BacktestResult(trades,curve)

def isoweekday_delta(value): return timedelta(days=value.weekday())
