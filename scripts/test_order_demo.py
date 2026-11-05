from pathlib import Path
import sys,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import load_settings
from src.mt5_client import MT5Client
from src.models import Signal
from src.market_data import get_account_state
from src.risk import calc_volume,check_trade_allowed
from src.db import Database
from src.executor import Executor
from src.symbols import SymbolService

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--confirm',action='store_true'); args=ap.parse_args(); s=load_settings()
    if s.config['account']['mode']!='demo': raise SystemExit('Set account.mode=demo for this script')
    with MT5Client(s) as client:
        m=client.mt5; svc=SymbolService(m,s); symbol=svc.resolve_alias('EURUSD')
        if not symbol: raise SystemExit('Could not resolve EURUSD alias from broker symbols')
        info=m.symbol_info(symbol); tick=m.symbol_info_tick(symbol); entry=tick.ask; sl=entry-100*info.point; tp=entry+120*info.point
        vol,reason=calc_volume(m.account_info().equity,s.risk['risk_per_trade_pct'],entry,sl,info._asdict())
        print(f'Would buy {symbol} volume={vol} SL={sl} TP={tp}; sizing={reason}')
        if not args.confirm: return
        if vol<=0: raise SystemExit(f'Trade refused: {reason}')
        sig=Signal(symbol,'buy','M5',entry,sl,tp,.5,'demo-test','demo order test')
        account=get_account_state(m); db=Database(s.db_path); exe=Executor(m,s,db)
        ok,why=check_trade_allowed(sig,account,[],0,0,s,{'cost':0},svc.get_asset_group(symbol),__import__('datetime').datetime.now(__import__('datetime').timezone.utc),0)
        if not ok: raise SystemExit(f'Trade refused: {why}')
        result=exe.open_trade(sig,vol); print(result)
        if not result.success: raise SystemExit(result.message)
        import time; time.sleep(5); closed=exe.close_position(result.ticket,'manual')
        if not closed.success: raise SystemExit(f'Close failed; position may still be open: {closed.message}')
        exe.sync_positions()
        with db.connect() as c: print(dict(c.execute('SELECT * FROM trades WHERE ticket=?',(result.ticket,)).fetchone()))
if __name__=='__main__': main()
