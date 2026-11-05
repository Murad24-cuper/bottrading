"""Download incremental candle history through the read-only MT5 interface."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import load_settings
from src.mt5_client import MT5Client
from src.symbols import SymbolService
from src.history import download_history

def parse_time(value):
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--symbols',choices=['liquid','universe'],default='liquid'); parser.add_argument('--from',dest='date_from'); parser.add_argument('--to',dest='date_to'); args=parser.parse_args()
    try: settings=load_settings()
    except ValueError as exc: raise SystemExit(f'Configuration error: {exc}')
    with MT5Client(settings) as client:
        service=SymbolService(client.mt5,settings)
        if args.symbols=='universe': symbols=service.get_universe()
        else:
            symbols=[]
            for alias in settings.config['history']['liquid_aliases']:
                actual=service.resolve_alias(alias)
                if actual: symbols.append(actual)
                else: print(f'Skipping unavailable liquid alias: {alias}')
        symbols=list(dict.fromkeys(symbols))
        if not symbols: raise SystemExit('No symbols resolved; check the connected XM terminal universe and aliases.')
        download_history(client.mt5,symbols,settings.config['timeframes'],parse_time(args.date_from) if args.date_from else None,parse_time(args.date_to) if args.date_to else None,settings)
    return 0

if __name__=='__main__': raise SystemExit(main())
