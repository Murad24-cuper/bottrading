"""Dry-run by default; --confirm places and then closes one DEMO test trade."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import sys,argparse,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import load_settings
from src.mt5_client import MT5Client
from src.models import Signal
from src.market_data import get_account_state,get_cost_estimate,price_distance_to_money
from src.risk import calc_volume,check_trade_allowed
from src.db import Database
from src.executor import Executor
from src.symbols import SymbolService

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--confirm',action='store_true'); args=parser.parse_args()
    try: settings=load_settings()
    except ValueError as exc: raise SystemExit(f'Configuration error: {exc}')
    if settings.config['account']['mode']!='demo': raise SystemExit('This test script requires account.mode: demo')
    with MT5Client(settings) as client:
        mt5=client.mt5; account_info=mt5.account_info()
        if account_info.trade_mode!=getattr(mt5,'ACCOUNT_TRADE_MODE_DEMO',0): raise SystemExit('Test order refused: connected account is not DEMO')
        terminal=mt5.terminal_info()
        if not terminal or not terminal.trade_allowed: raise SystemExit('Test order refused: enable Allow algorithmic trading in MT5')
        symbols=SymbolService(mt5,settings); symbol=symbols.resolve_alias('EURUSD')
        if symbol is None: raise SystemExit('Could not resolve EURUSD alias against broker symbols')
        tradable,reason=symbols.is_tradable(symbol)
        if not tradable: raise SystemExit(f'Test order refused: {symbol} is not tradable: {reason}')
        info=mt5.symbol_info(symbol); tick=mt5.symbol_info_tick(symbol)
        entry=float(tick.ask); sl=entry-100*info.point; tp=entry+120*info.point
        volume,size_reason=calc_volume(account_info.equity,settings.risk.risk_per_trade_pct,entry,sl,info._asdict())
        risk_money=price_distance_to_money(mt5,symbol,entry-sl,volume) if volume>0 else 0.0
        allowed_money=account_info.equity*settings.risk.risk_per_trade_pct/100
        print(f'{"WOULD BUY" if not args.confirm else "DEMO TEST BUY"} {symbol}; volume={volume}; entry≈{entry}; SL={sl}; TP={tp}')
        print(f'Risk at SL={risk_money:.2f} {account_info.currency} (budget={allowed_money:.2f}); sizing={size_reason}')
        if volume<=0: raise SystemExit(f'Trade refused: {size_reason}')
        cost=get_cost_estimate(mt5,symbol,volume)
        target_value=price_distance_to_money(mt5,symbol,tp-entry,volume)
        cost['target_value']=target_value
        print(f'Estimated round-trip cost={cost["cost"]:.2f} {account_info.currency}; commission known={cost["commission_known"]}; cost/target={cost["cost"]/target_value:.3f}')
        if not args.confirm: print('Dry run only; no order was sent.'); return 0
        signal=Signal(symbol,'buy','M5',entry,sl,tp,0.5,'demo-test','manual demo order test')
        state=get_account_state(mt5); db=Database(settings.db_path); executor=Executor(mt5,settings,db,symbols)
        owned=[p for p in (mt5.positions_get() or []) if int(p.magic)==settings.magic_number]
        positions=[{'ticket':p.ticket,'symbol':p.symbol,'asset_group':symbols.get_asset_group(p.symbol),'profit':p.profit} for p in owned]
        now=datetime.now(timezone.utc); day_start=now.replace(hour=0,minute=0,second=0,microsecond=0); week_start=(now-timedelta(days=now.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)
        today_pnl=db.get_pnl_since(day_start); week_pnl=db.get_pnl_since(week_start)
        required_margin=mt5.order_calc_margin(mt5.ORDER_TYPE_BUY,symbol,volume,entry)
        if required_margin is None: raise SystemExit(f'Trade refused: order_calc_margin failed: {mt5.last_error()}')
        allowed,why=check_trade_allowed(signal,state,positions,today_pnl,week_pnl,settings,cost,symbols.get_asset_group(symbol),now,required_margin)
        if not allowed: raise SystemExit(f'Trade refused by risk manager: {why}')
        db.insert_signal(time=now.isoformat(),symbol=symbol,strategy=signal.strategy_name,direction=signal.direction,timeframe=signal.timeframe,confidence=signal.confidence,entry=entry,sl=sl,tp=tp,expected_cost=cost['cost'],taken=1,skip_reason='')
        opened=executor.open_trade(signal,volume); print(f'Open result: {opened}')
        if not opened.success: raise SystemExit(opened.message)
        time.sleep(5)
        closed=executor.close_position(opened.ticket,'manual')
        if not closed.success: raise SystemExit(f'Close failed; owned position may remain open: {closed.message}')
        executor.sync_positions()
        with db.connect() as connection:
            row=connection.execute('SELECT * FROM trades WHERE ticket=?',(opened.ticket,)).fetchone()
            if row is None or row['status']!='closed' or not row['close_reason']: raise SystemExit('Broker reported close but DB reconciliation is incomplete')
            print('Closed DB trade row:'); print(dict(row))
        return 0

if __name__=='__main__': raise SystemExit(main())
