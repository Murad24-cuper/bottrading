"""Refresh the configured focus and weekend Parquet history over the local MT5 session.

Run only while the supervised bot is stopped. This utility is read-only and never places orders.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import load_settings
from src.history import download_history
from src.mt5_client import MT5Client
from src.symbols import SymbolService


def _resolve(service,logical):
    symbol=service.resolve_alias(str(logical))
    if symbol: return symbol
    names=[item.name for item in service.list_all_symbols()]
    return next((name for name in names if name.casefold()==str(logical).casefold()),None)


def main():
    settings=load_settings()
    if settings.config['account']['mode']!='demo' or settings.allow_real:
        raise SystemExit('History refresh requires account.mode=demo and ALLOW_REAL=false.')
    for name in ('bot.lock','supervisor.pid'):
        if (settings.data_dir/name).exists():
            raise SystemExit(f'{name} exists. Stop the supervised bot before taking the MT5 data session.')
    root=settings.root; history_dir=root/settings.config['history']['data_dir']
    ranges=[]; now=datetime.now(timezone.utc)
    with MT5Client(settings) as client:
        account=client.mt5.account_info()
        if account is None or account.trade_mode!=getattr(client.mt5,'ACCOUNT_TRADE_MODE_DEMO',0):
            raise SystemExit('Refusing history refresh: MT5 is not on a DEMO account.')
        service=SymbolService(client.mt5,settings); universe=settings.config['universe']
        focus=[]; weekend=[]
        for logical in universe.get('focus_symbols',[]):
            actual=_resolve(service,logical)
            if actual: focus.append(actual)
            else: print(f'Unavailable broker symbol for focus alias {logical}')
        for logical in universe.get('weekend_symbols',[]):
            actual=_resolve(service,logical)
            if actual: weekend.append(actual)
            else: print(f'Unavailable broker symbol for weekend alias {logical}')
        if not focus: raise SystemExit('No focus symbols resolved from the connected MT5 terminal.')
        timeframe_cfg=settings.config['history']
        if focus:
            download_history(client.mt5,focus,['M1','M5','M15','H1'],date_to=now,settings=settings)
        if weekend:
            download_history(client.mt5,weekend,['M1','M5','M15'],date_to=now,settings=settings)
        for symbol in [*focus,*weekend]:
            for timeframe in (['M1','M5','M15','H1'] if symbol in focus else ['M1','M5','M15']):
                path=history_dir/f'{symbol}_{timeframe}.parquet'
                if not path.exists(): continue
                import pandas as pd
                frame=pd.read_parquet(path); index=pd.to_datetime(frame.index,utc=True)
                ranges.append((symbol,timeframe,len(frame),index.min().isoformat(),index.max().isoformat()))
    target=root/'docs'/'HISTORY_RANGES.md'; target.parent.mkdir(parents=True,exist_ok=True)
    lines=['# History ranges','',f'Refreshed at {now.isoformat()} via the local DEMO terminal. Missing broker history is recorded as provided; no order functions are called.','','| Symbol | Timeframe | Bars | First UTC bar | Last UTC bar |','|---|---|---:|---|---|']
    lines += [f'| {symbol} | {tf} | {count} | {first} | {last} |' for symbol,tf,count,first,last in ranges]
    target.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Wrote {len(ranges)} real ranges to {target}')
    return 0


if __name__=='__main__': raise SystemExit(main())
