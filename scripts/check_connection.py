"""Read-only MT5 account and universe diagnostic."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import load_settings
from src.mt5_client import MT5Client
from src.symbols import SymbolService
from src.market_data import get_account_state,get_spread_points,get_candles

def main():
    try: settings=load_settings()
    except ValueError as exc:
        print(f'Configuration error: {exc}'); return 2
    try:
        with MT5Client(settings) as client:
            mt5=client.mt5; account=get_account_state(mt5); info=mt5.account_info()
            margin_mode='hedging' if account.margin_mode==getattr(mt5,'ACCOUNT_MARGIN_MODE_RETAIL_HEDGING',2) else 'netting'
            print(f'Connected to account ***{str(info.login)[-3:]} ({"DEMO" if account.trade_mode==getattr(mt5,"ACCOUNT_TRADE_MODE_DEMO",0) else "REAL"})')
            print(f'Balance={account.balance} {account.currency}; equity={account.equity}; margin={account.margin}; margin mode={margin_mode}')
            terminal=mt5.terminal_info(); allowed=bool(terminal and terminal.trade_allowed)
            print(f'Algorithmic trading enabled: {allowed}')
            if not allowed: print('WARNING: Enable "Allow algorithmic trading" in the MT5 terminal before trading.')
            service=SymbolService(mt5,settings); symbols=service.list_all_symbols()
            grouped={}
            for item in symbols: grouped.setdefault(service.get_asset_group(item.name),[]).append(item.name)
            for group in ('forex','metals','indices','energy','crypto','stocks','other'):
                names=grouped.get(group,[]); print(f'[{group}] {len(names)} symbols')
                for name in names[:10]:
                    tradable,reason=service.is_tradable(name)
                    try: spread=f'{get_spread_points(mt5,name):.2f} points'
                    except Exception as exc: spread=f'unavailable ({exc})'
                    print(f'  {name}: spread={spread}; tradable={tradable} ({reason})')
            for logical in settings.config['universe']['symbol_aliases']:
                print(f'Alias {logical} -> {service.resolve_alias(logical) or "not found"}')
            candles_symbols=service.get_universe()[:2]
            for symbol in candles_symbols:
                print(f'Last 20 M5 candles for {symbol} (UTC):')
                print(get_candles(mt5,symbol,'M5',20).to_string())
            if not candles_symbols: print('No currently tradable symbols; candle samples skipped.')
        return 0
    except RuntimeError as exc:
        message=str(exc)
        if 'initialize failed' in message.lower(): print(f'MT5 terminal unavailable or closed. {message}')
        elif 'login failed' in message.lower(): print(f'MT5 login failed; check account number, password and XM server. {message}')
        else: print(f'MT5 connection error: {message}')
        return 1

if __name__=='__main__': raise SystemExit(main())
