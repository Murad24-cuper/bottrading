"""Offline edge diagnostics over cached XM history; never connects to MT5."""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import json, math, sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from src.brain.training import label_trade, split_name
from src.config import load_settings
from src.indicators import atr
from src.strategies import load_strategies
from src.trade_rules import strategy_mtf_allowed

TFS={'M1':1,'M5':5,'M15':15,'H1':60}; RRS=(1.,1.5,2.,3.)
NAMES={'trend_pullback','mean_reversion','volatility_scalp'}
def metric(rows):
    if not rows:return {'n':0,'win':None,'ev':None,'pf':None}
    x=np.asarray([r['net_r'] for r in rows],float); wins=x[x>0].sum(); losses=-x[x<0].sum()
    return {'n':len(x),'win':float((x>0).mean()),'ev':float(x.mean()),'pf':float(wins/losses) if losses else (math.inf if wins else 0.)}
def show(x): return 'n/a' if x is None else f'{x:.4f}'
def winshow(x): return 'n/a' if x is None else f'{x:.1%}'
def main():
    s=load_settings(require_credentials=False)
    if s.config['account']['mode']!='demo' or s.allow_real: raise SystemExit('Requires DEMO config and ALLOW_REAL=false')
    data_dir=s.data_dir/'history'; brain=s.data_dir/'brain'
    split=json.loads((brain/'splits.json').read_text()); specs=json.loads((data_dir/'symbol_specs.json').read_text())
    start=pd.Timestamp(split['train_end'],tz='UTC')-pd.Timedelta(days=8)
    finish=pd.Timestamp(max(x['end_utc'] for x in split['symbols'].values()))
    frames={}
    for symbol in split['symbols']:
        fs={}
        for tf,mins in TFS.items():
            p=data_dir/f'{symbol}_{tf}.parquet'
            if p.exists():
                f=pd.read_parquet(p).sort_index(); f.index=pd.DatetimeIndex(f.index)
                f.index=f.index.tz_localize('UTC') if f.index.tz is None else f.index.tz_convert('UTC')
                f=f.loc[(f.index>=start)&(f.index<=finish)].copy()
                if len(f): fs[tf]=f
        if fs: frames[symbol]=fs
    cfg=s.config; bt=cfg['backtest']; costs=[]
    for symbol,fs in frames.items():
        spec=specs.get(symbol,{}); point=float(spec.get('point_size',spec.get('point',spec.get('trade_tick_size',1e-5))) or 1e-5)
        tick=float(spec.get('trade_tick_size',spec.get('tick_size',point)) or point); value=float(spec.get('trade_tick_value',spec.get('trade_tick_value_loss',spec.get('tick_value',0))) or 0)
        mpp=value/tick if tick else 0
        for tf,f in fs.items():
            spr=pd.to_numeric(f.get('spread',pd.Series(dtype=float)),errors='coerce').clip(lower=0).dropna()
            med_sp=float(spr.median()) if len(spr) else 0.; med_atr=float(atr(f,14).dropna().median())
            cost=med_sp*point+2*float(bt.get('slippage_points',0))*point+(2*float(bt.get('commission_per_lot_per_side',0))/mpp if mpp else 0)
            stop=med_atr*float(cfg['risk']['sl_move_mult'])
            costs.append((symbol,spec.get('asset_group','other'),tf,med_sp,med_atr,cost,stop,cost/stop if stop>0 else None))
    strategies=[x for x in load_strategies(s) if x.name in NAMES]
    weekend_names=cfg['universe'].get('weekend_symbols',[]); aliases=cfg['universe'].get('symbol_aliases',{})
    pats=[str(a).upper() for n in weekend_names for a in aliases.get(n,[n])]
    weekend={sym for sym in frames if any(p in sym.upper() for p in pats)}
    fx=frames.get('EURUSD',{}).get('M1'); fxidx=fx.index if fx is not None else pd.DatetimeIndex([])
    outrows=[]; grid=defaultdict(list); holdout=defaultdict(list); last_close={}
    check=cfg['scanner']; risk=cfg['risk']; hld=int(risk['max_hold_minutes'])
    for symbol,base in frames.items():
        spec=specs.get(symbol,{}); group=str(spec.get('asset_group','other'))
        prepared={k:v.copy() for k,v in base.items()}; point=float(spec.get('point_size',spec.get('point',1e-5)) or 1e-5)
        if 'M1' in prepared:
            m1=prepared['M1']; m1['__scalp_atr']=atr(m1,14); scalp=next((x for x in strategies if x.name=='volatility_scalp'),None)
            look=int(scalp.params.get('percentile_lookback_bars',7200)) if scalp else 7200
            q=float(scalp.params.get('atr_percentile',.70)) if scalp else .70
            m1['__scalp_percentile_threshold']=m1['__scalp_atr'].shift(1).rolling(look,min_periods=max(100,look//2)).quantile(q)
            m1['spread_points']=pd.to_numeric(m1.get('spread',0),errors='coerce').fillna(0); m1['point_size']=point; m1['spread_price']=m1.spread_points*point
            if 'spread' in m1: m1['__spread_median24']=m1.spread.rolling(1440,min_periods=60).median().shift(1)
        for tf in TFS:
            entry=prepared.get(tf)
            if entry is None or len(entry)<80: continue
            delta=pd.Timedelta(minutes=TFS[tf]); # closed candle at idx, entry on idx+1
            # M1 is the baseline; M15/H1 are diagnostic grid entries.
            for idx in range(60,len(entry)-1):
                now=entry.index[idx]+delta; part=split_name(now.to_pydatetime(),split)
                if part not in ('train','validation','test'): continue
                pos=int(fxidx.searchsorted(now,side='right'))-1; forex_open=pos>=0 and now-fxidx[pos]<=pd.Timedelta(minutes=2)
                if (symbol in weekend and (now.weekday()<5 or forex_open)) or (symbol not in weekend and now.weekday()>=5 and not forex_open): continue
                candles={}
                for source,f in prepared.items():
                    end=f.index.searchsorted(now-pd.Timedelta(minutes=TFS[source]),side='right')
                    if end: candles[source]=f.iloc[max(0,end-(7201 if source=='M1' else 300)):end]
                if tf not in candles: continue
                atrvals=atr(entry.iloc[max(0,idx-100):idx+1],14); atrv=float(atrvals.iloc[-1])
                if not np.isfinite(atrv) or atrv<=0: continue
                for strategy in strategies:
                    if group not in getattr(strategy,'allowed_groups',[]): continue
                    # Current rule baseline: run all three strategies at M1 entries.
                    # Grid only uses M15/H1 entries and train/validation timestamps.
                    if tf!='M1' and part=='test': continue
                    try: signal=strategy.generate_signal(symbol,candles)
                    except (KeyError,ValueError,IndexError,TypeError): continue
                    if signal is None or signal.direction not in ('buy','sell'): continue
                    if float(signal.confidence)<float(check.get('min_confidence',0)): continue
                    if not strategy_mtf_allowed(strategy.name,candles,signal.direction,enabled=bool(check.get('require_mtf_agreement',False)),fast=int(check.get('mtf_ema_fast',5)),slow=int(check.get('mtf_ema_slow',13)),min_agree=int(check.get('mtf_min_agree',3))): continue
                    stop=abs(float(signal.entry_hint)-float(signal.sl_price))
                    if stop<=0 or not np.isfinite(stop): continue
                    # Single-symbol max-hold spacing keeps overlapping labels out.
                    if tf=='M1' and now<last_close.get((symbol,strategy.name),pd.Timestamp.min.tz_localize('UTC')): continue
                    horizon=hld; proxy=stop/math.sqrt(max(1,horizon))
                    targets=RRS if tf in ('M15','H1') else (abs(float(signal.tp_price)-float(signal.entry_hint))/stop,)
                    for rr in targets:
                        result=label_trade(entry,idx,signal.direction,proxy,spec,horizon_minutes=horizon,sl_mult=1,tp_mult=rr,
                            slippage_points=float(bt.get('slippage_points',0)),timeout_minutes=horizon,
                            commission_per_lot_per_side=float(bt.get('commission_per_lot_per_side',0)))
                        if not result: continue
                        row={'net_r':result['net_r'],'symbol':symbol,'asset_group':group,'strategy':strategy.name,'time':now.isoformat()}
                        if tf=='M1' and part=='test':
                            holdout[(strategy.name,group)].append(row); last_close[(symbol,strategy.name)]=now+pd.Timedelta(minutes=horizon)
                        elif tf in ('M15','H1') and part in ('train','validation'):
                            grid[(strategy.name,group,tf,rr,part)].append(row)
    baseline=[x for vals in holdout.values() for x in vals]
    bys=defaultdict(list); byg=defaultdict(list)
    for x in baseline: bys[x['strategy']].append(x); byg[x['asset_group']].append(x)
    g_rows=[]
    for key,vals in sorted(grid.items()): g_rows.append((*key,metric(vals)))
    viable=[]
    for key in sorted({r[:4] for r in g_rows}):
        tr=metric(grid.get((*key,'train'),[])); va=metric(grid.get((*key,'validation'),[]))
        if tr['n']>=300 and va['n']>=300 and tr['ev']>0 and va['ev']>0: viable.append((key,tr,va))
    pred=pd.read_parquet(brain/'test_predictions.parquet'); pool=pred.net_r.to_numpy(float); chosen=pred.loc[pred.checklist_only.astype(bool),'net_r'].to_numpy(float)
    rng=np.random.default_rng(20261109); rand=np.asarray([rng.choice(pool,len(chosen),replace=False).mean() for _ in range(1000)])
    bmet=metric(baseline); lines=['# Edge research','','Offline-only diagnostic. No MT5 connection, live code path, or trading/risk configuration changes.',
      f"Frozen periods: train ends {split['train_end']}; validation {split['validation_start']} to {split['validation_end']}; holdout begins {split['test_start']}.",
      'Holdout is used only for the requested baseline and checklist comparison. Grid code processes train/validation only.','',
      '## 1. Transaction costs vs ATR stop distance','','Round trip = median spread + two-sided configured commission + two-sided slippage, converted to price units. Stop = median ATR(14) × configured stop multiplier.','',
      '| Symbol | Group | TF | Median spread pts | Median ATR | Cost price | Stop distance | Cost/stop |','|---|---|---:|---:|---:|---:|---:|---:|']
    for a in costs: lines.append(f'| {a[0]} | {a[1]} | {a[2]} | {a[3]:.3f} | {a[4]:.8g} | {a[5]:.8g} | {a[6]:.8g} | {a[7]:.1%} |' if a[7] is not None else f'| {a[0]} | {a[1]} | {a[2]} | {a[3]:.3f} | {a[4]:.8g} | {a[5]:.8g} | {a[6]:.8g} | n/a |')
    lines+=['','## 2. Current strategies on holdout','',f"Signal-level M1 baseline, current confidence/MTF gates, one max-hold slot per symbol/strategy: {bmet['n']} trades, win {winshow(bmet['win'])}, expectancy {show(bmet['ev'])} R, PF {show(bmet['pf'])}.",'','### By strategy','','| Strategy | Trades | Win rate | Expectancy R | PF |','|---|---:|---:|---:|---:|']
    for k,v in sorted(bys.items()):
        m=metric(v); lines.append(f'| {k} | {m["n"]} | {winshow(m["win"])} | {show(m["ev"])} | {show(m["pf"])} |')
    lines+=['','### By group','','| Group | Trades | Win rate | Expectancy R | PF |','|---|---:|---:|---:|---:|']
    for k,v in sorted(byg.items()):
        m=metric(v); lines.append(f'| {k} | {m["n"]} | {winshow(m["win"])} | {show(m["ev"])} | {show(m["pf"])} |')
    lines+=['','## 3. M15/H1 timeframe and R:R grid (train/validation only)','','Causal signals use closed bars; entry is the next bar open. The strategy stop distance is preserved; target is varied. Costs and configured time barrier are applied; stop takes precedence if both barriers hit.','',
      '| Strategy | Group | TF | R:R | Split | Trades | Win | Expectancy net R | PF |','|---|---|---:|---:|---|---:|---:|---:|---:|']
    for st,g,tf,rr,part,m in g_rows: lines.append(f'| {st} | {g} | {tf} | 1:{rr:g} | {part} | {m["n"]} | {winshow(m["win"])} | {show(m["ev"])} | {show(m["pf"])} |')
    lines+=['','## 4. Positive on both train and validation with 300+ trades in each','']
    if viable:
        lines+=['| Strategy | Group | TF | R:R | Train N / EV | Validation N / EV |','|---|---|---:|---:|---:|---:|']
        for k,t,v in viable: lines.append(f'| {k[0]} | {k[1]} | {k[2]} | 1:{k[3]:g} | {t["n"]} / {t["ev"]:.4f} | {v["n"]} / {v["ev"]:.4f} |')
    else: lines.append('None. The 300-trade minimum is required separately in each split.')
    lines+=['','## 5. Why checklist-only is worse than random','',
      f'The holdout candidate pool: {len(pool)} samples, win rate {pred.actual_win.mean():.2%}, expectancy {pool.mean():.4f} R. Checklist-only: {len(chosen)} samples, win rate {(chosen>0).mean():.2%}, expectancy {chosen.mean():.4f} R.',
      f'1,000 uniformly random equal-size subsets average {rand.mean():.4f} R, central 90% {np.quantile(rand,.05):.4f} to {np.quantile(rand,.95):.4f} R. Checklist is {chosen.mean()-pool.mean():.4f} R below the whole candidate pool. This establishes worse selection on this sample, not which checklist item caused it; item-level randomized ablations were not run.',
      '','## Method limits','','The current-strategy section is a causal signal-level replay with bot confidence/MTF gates, configured spread/costs, and a non-overlap max-hold spacing. It does not apply full portfolio margin/daily-loss allocation. The grid is a fixed-barrier diagnostic, not a portfolio backtest. No holdout tuning was done.']
    target=s.root/'reports'/'edge_research.md'; target.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Wrote {target}; baseline={bmet["n"]}; grid rows={len(g_rows)}; positive combinations={len(viable)}')
if __name__=='__main__': main()
