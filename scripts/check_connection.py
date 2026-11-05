from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import load_settings
from src.mt5_client import MT5Client
from src.symbols import SymbolService
from src.market_data import get_account_state,get_spread_points,get_candles

def main():
    s=load_settings()
    with MT5Client(s) as client:
        m=client.mt5; a=get_account_state(m); print(f'Account ***{str(m.account_info().login)[-3:]} balance={a.balance} equity={a.equity} margin_mode={a.margin_mode}')
        ti=m.terminal_info(); print(f'Algorithmic trading enabled: {bool(ti and ti.trade_allowed)}')
        svc=SymbolService(m,s); groups={}
        for item in svc.list_all_symbols(): groups.setdefault(svc.get_asset_group(item.name),[]).append(item.name)
        for group,names in groups.items():
            print(f'{group}: {len(names)} symbols')
            for name in names[:10]:
                ok,why=svc.is_tradable(name)
                try: spread=get_spread_points(m,name)
                except Exception: spread='n/a'
                print(f'  {name}: spread={spread} tradable={ok} ({why})')
        for logical in s.config['universe']['symbol_aliases']: print(f'Alias {logical}: {svc.resolve_alias(logical)}')
        tradable=svc.get_universe()[:2]
        for name in tradable:
            print(f'M5 candles {name}:\n{get_candles(m,name,"M5",20).tail(20)}')
if __name__=='__main__': main()
