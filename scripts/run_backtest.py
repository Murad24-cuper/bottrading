"""Run the Part 2 simulator against cached Parquet data; no MT5 connection needed."""
from pathlib import Path
from itertools import product
import argparse,csv,json,sys
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import load_settings
from src.backtest.engine import Backtester
from src.backtest.report import save_report,walk_forward
from src.strategies import REGISTRY,load_strategies
from src.history import history_path
from src.parquet_compat import read_parquet

def _settings(): return load_settings(require_credentials=False)

def _read_history(settings,mode,strategy_names,requested_timeframes=None):
    base=Path(settings.config['history']['data_dir']); base=base if base.is_absolute() else settings.root/base
    specfile=base/'symbol_specs.json'; specs=json.loads(specfile.read_text(encoding='utf-8')) if specfile.exists() else {}
    if mode=='liquid':
        symbols=[]; names=list(specs)
        for logical in settings.config['history']['liquid_aliases']:
            patterns=settings.config['universe']['symbol_aliases'].get(logical,[logical])
            found=next((name for pattern in patterns for name in names if pattern.lower() in name.lower()),None)
            if found: symbols.append(found)
            else: print(f'Skipping missing cached liquid symbol: {logical}')
    else:
        symbols=list(specs)
        if not symbols:
            frames=list(base.glob('*_M1.parquet'))
            symbols=[p.stem[:-3] for p in frames]
    symbols=list(dict.fromkeys(symbols)); history={}
    timeframes=set(tf for name,entry in settings.config['strategies'].items() if name in strategy_names and entry.get('enabled') for tf in entry.get('timeframes',[]))
    if requested_timeframes is not None: timeframes &= set(requested_timeframes)
    for symbol in symbols:
        history[symbol]={}
        for tf in sorted(timeframes):
            path=history_path(base,symbol,tf)
            if path.exists(): history[symbol][tf]=read_parquet(path)
        if not history[symbol]: print(f'No cached bars for {symbol}; skipped.')
    history={s:frames for s,frames in history.items() if frames}
    return history,specs

def _slice_history(history,start,end):
    result={}
    for symbol,frames in history.items():
        result[symbol]={tf:frame.loc[(frame.index>=start)&(frame.index<end)] for tf,frame in frames.items()}
        result[symbol]={tf:frame for tf,frame in result[symbol].items() if not frame.empty}
    return {s:f for s,f in result.items() if f}

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--strategies',default='all'); parser.add_argument('--symbols',choices=['liquid','universe'],default='liquid'); parser.add_argument('--only-symbols',help='comma-separated logical or broker symbol names'); parser.add_argument('--timeframes',help='comma-separated history timeframes to load'); parser.add_argument('--lookback-months',type=int,help='limit each selected series to its latest N months'); parser.add_argument('--equity',type=float,default=None); parser.add_argument('--walk-forward',action='store_true'); args=parser.parse_args()
    settings=_settings(); enabled=load_strategies(settings); names=[s.name for s in enabled]
    if args.strategies!='all':
        if args.strategies not in REGISTRY: raise SystemExit(f'Unknown strategy {args.strategies!r}; choose all or one of {", ".join(REGISTRY)}')
        names=[args.strategies] if args.strategies in names else []
    if not names: raise SystemExit('No selected enabled strategies in config.yaml')
    requested_timeframes=None
    if args.timeframes:
        requested_timeframes=[tf.strip().upper() for tf in args.timeframes.split(',') if tf.strip()]
        invalid=set(requested_timeframes)-{'M1','M5','M15','H1'}
        if invalid: raise SystemExit(f'Unsupported timeframe(s): {", ".join(sorted(invalid))}')
    history,specs=_read_history(settings,args.symbols,names,requested_timeframes)
    if args.only_symbols:
        available=list(specs); resolved=[]
        for logical in (value.strip() for value in args.only_symbols.split(',')):
            if not logical: continue
            aliases=settings.config['universe']['symbol_aliases'].get(logical,[logical])
            patterns=[logical,*aliases]
            actual=next((name for name in available if name.lower()==logical.lower()),None)
            if actual is None:
                actual=next((name for pattern in patterns for name in available if pattern.lower() in name.lower()),None)
            if actual: resolved.append(actual)
            else: print(f'Skipping missing selected symbol: {logical}')
        selected=list(dict.fromkeys(resolved)); history={symbol:frames for symbol,frames in history.items() if symbol in selected}
        print(f'Selected symbols: {", ".join(selected)}')
    if args.lookback_months is not None:
        if args.lookback_months<=0: raise SystemExit('--lookback-months must be positive')
        latest=max(frame.index.max() for frames in history.values() for frame in frames.values() if not frame.empty)
        cutoff=latest-pd.DateOffset(months=args.lookback_months)
        history={symbol:{tf:frame.loc[frame.index>=cutoff] for tf,frame in frames.items() if not frame.loc[frame.index>=cutoff].empty} for symbol,frames in history.items()}
        history={symbol:frames for symbol,frames in history.items() if frames}
        print(f'Limited history to {args.lookback_months} months from {cutoff.isoformat()}')
    if not history: raise SystemExit('No cached Parquet history found. Run scripts/download_history.py first on an MT5-connected Windows machine.')
    strategies=[strategy for strategy in enabled if strategy.name in names]
    equity=args.equity if args.equity is not None else settings.config['backtest']['start_equity']
    result=Backtester(settings,specs,equity,strategies).run(history)
    directory,metrics=save_report(result,settings.root/'reports',settings.config['backtest']['in_sample_pct'])
    print(f'Equity={equity:g}; trades={metrics["overall"]["trades"]}; win rate={metrics["overall"]["win_rate"]:.1%}; expectancy after costs={metrics["overall"]["expectancy"]:.4f}; profit factor={metrics["overall"]["profit_factor"]:.4f}; max DD={metrics["overall"]["max_drawdown_pct"]:.2f}%; report={directory}')
    if args.walk_forward:
        grids=settings.config['backtest'].get('parameter_grid',{}); subset={name:grids.get(name,{}) for name in names}
        dates=[]
        for frames in history.values():
            for frame in frames.values():
                if len(frame):
                    for value in (frame.index.min(),frame.index.max()):
                        stamp=pd.Timestamp(value); dates.append(stamp.tz_localize('UTC') if stamp.tzinfo is None else stamp.tz_convert('UTC'))
        start=min(dates); end=max(dates)
        def run_window(a,b,name,params):
            cls=REGISTRY[name]; entry=settings.config['strategies'][name]; instance=cls({**entry.get('params',{}),**params}); instance.allowed_groups=entry.get('groups',[]); instance.required_timeframes=entry.get('timeframes',instance.required_timeframes)
            sliced=_slice_history(history,pd.Timestamp(a),pd.Timestamp(b))
            return Backtester(settings,specs,equity,[instance]).run(sliced).trades
        windows=walk_forward(start,end,subset,run_window,settings.config['backtest']['walk_forward_optimize_months'],settings.config['backtest']['walk_forward_test_months'])
        pd.DataFrame(windows).to_csv(directory/'walk_forward.csv',index=False)
        print(f'Walk-forward windows: {len(windows)}; saved to {directory / "walk_forward.csv"}')
    print('Strategy summary:')
    print(pd.DataFrame(metrics['per_strategy'])[['strategy','trades','win_rate','expectancy','profit_factor','max_drawdown_pct','in_sample_expectancy','out_of_sample_expectancy','verdict']].to_string(index=False) if metrics['per_strategy'] else 'No closed trades.')
    return 0

if __name__=='__main__': raise SystemExit(main())
