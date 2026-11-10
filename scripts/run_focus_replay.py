"""Replay a UTC weekday session on the configured focus universe from Parquet only."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json, sys, argparse

import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import load_settings
from src.history import history_path
from src.strategies import load_strategies
from src.backtest.engine import Backtester
from src.parquet_compat import read_parquet


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date',default='2026-11-06',help='UTC date to replay (Friday by default)')
    args=parser.parse_args(); settings=load_settings(require_credentials=False)
    base=Path(settings.config['history']['data_dir']); base=base if base.is_absolute() else settings.root/base
    specs_path=base/'symbol_specs.json'; specs=json.loads(specs_path.read_text(encoding='utf-8')) if specs_path.exists() else {}
    symbols=[]
    for logical in settings.config['universe'].get('focus_symbols',[]):
        patterns=settings.config['universe']['symbol_aliases'].get(logical,[logical])
        actual=next((name for name in specs if name.lower()==logical.lower()),None)
        if actual is None: actual=next((name for pattern in patterns for name in specs if pattern.lower() in name.lower()),None)
        if actual and actual not in symbols: symbols.append(actual)
    if not symbols: raise SystemExit('No focus symbol specifications are cached.')
    day=datetime.fromisoformat(args.date).replace(tzinfo=timezone.utc)
    start=day.replace(hour=7); end=day.replace(hour=21)
    context_start=start-timedelta(days=7); history={}; available={}
    for symbol in symbols:
        frames={}
        for tf in ('M1','M5','M15','H1'):
            path=history_path(base,symbol,tf)
            if not path.is_file(): continue
            frame=read_parquet(path); frame.index=pd.to_datetime(frame.index,utc=True)
            frame=frame.loc[(frame.index>=context_start)&(frame.index<end)]
            if not frame.empty: frames[tf]=frame
        if frames: history[symbol]=frames; available[symbol]=specs[symbol]
    strategies=load_strategies(settings)
    result=Backtester(settings,available,1000,strategies,entry_window=(start,end)).run(history)
    trades=pd.DataFrame(result.trades)
    counts=trades.groupby('strategy').size().to_dict() if not trades.empty else {}
    groups=trades.groupby('asset_group').size().to_dict() if not trades.empty else {}
    report={'date':args.date,'window_utc':[start.isoformat(),end.isoformat()],'symbols_requested':symbols,'symbols_with_history':sorted(history),'trades':len(result.trades),'trades_by_strategy':counts,'trades_by_group':groups,'traded_symbols':sorted(set(trades.symbol)) if not trades.empty else [],'closed_trades':result.trades}
    target=settings.root/'reports'/f"focus_replay_{args.date}.json"; target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='closed_trades'},indent=2,ensure_ascii=False))
    print(f'Replay details: {target}')
    return 0

if __name__=='__main__': raise SystemExit(main())
