"""Run one read-only scan and show candidates plus risk-manager decisions."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import sys,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import load_settings
from src.mt5_client import MT5Client
from src.db import Database
from src.market_data import get_account_state
from src.risk import check_trade_allowed
from src.scanner import MarketScanner
from src.symbols import SymbolService

def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    try: settings=load_settings()
    except ValueError as exc: raise SystemExit(f'Configuration error: {exc}')
    with MT5Client(settings) as client:
        mt5=client.mt5; account_info=mt5.account_info()
        if account_info.trade_mode!=getattr(mt5,'ACCOUNT_TRADE_MODE_DEMO',0): raise SystemExit('Read-only scan requires a DEMO account')
        if not mt5.terminal_info().trade_allowed: print('WARNING: terminal algorithmic trading is disabled; scan is still read-only.')
        service=SymbolService(mt5,settings); db=Database(settings.db_path); scanner=MarketScanner(mt5,settings,db,service)
        candidates=scanner.scan_once(); state=get_account_state(mt5); now=datetime.now(timezone.utc)
        day=now.replace(hour=0,minute=0,second=0,microsecond=0); week=(now-timedelta(days=now.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)
        pnl_today=db.get_pnl_since(day); pnl_week=db.get_pnl_since(week)
        positions=[p for p in (mt5.positions_get() or []) if int(p.magic)==settings.magic_number]
        print('rank symbol strategy direction confidence volume SL TP cost score risk_decision')
        for rank,candidate in enumerate(candidates,1):
            margin=mt5.order_calc_margin(mt5.ORDER_TYPE_BUY if candidate.signal.direction=='buy' else mt5.ORDER_TYPE_SELL,candidate.symbol,candidate.volume,candidate.signal.entry_hint)
            if margin is None: ok,why=False,f'order_calc_margin error {mt5.last_error()}'
            else:
                opens=[{'symbol':p.symbol,'asset_group':service.get_asset_group(p.symbol),'profit':p.profit} for p in positions]
                ok,why=check_trade_allowed(candidate.signal,state,opens,pnl_today,pnl_week,settings,candidate.cost,candidate.asset_group,now,margin,candidate.volume,candidate.symbol_spec)
            print(f'{rank:>2} {candidate.symbol:<12} {candidate.strategy:<18} {candidate.signal.direction:<5} {candidate.confidence:.2f} {candidate.volume:g} {candidate.signal.sl_price:g} {candidate.signal.tp_price:g} {candidate.cost["cost"]:.2f} {candidate.score:.4f} {"ALLOW" if ok else "BLOCK"}: {why}')
        if not candidates: print('No positive-score candidates in this scan cycle.')
    return 0

if __name__=='__main__': raise SystemExit(main())
