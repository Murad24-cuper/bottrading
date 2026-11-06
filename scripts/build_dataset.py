"""Create a cost-aware brain universe and update its historical bars on Windows."""
from __future__ import annotations
from pathlib import Path
import shutil,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import load_settings
from src.mt5_client import MT5Client
from src.symbols import SymbolService
from src import indicators as ind
from src.market_data import get_closed_candles
from src.brain.data import select_universe,save_universe
from src.history import download_history

def main():
    settings=load_settings(); free=shutil.disk_usage(settings.root).free
    if free<15*1024**3: raise SystemExit(f'Not enough free disk space for brain history: {free/1024**3:.1f} GB; need 15 GB.')
    base=settings.data_dir/'brain'; base.mkdir(parents=True,exist_ok=True)
    selected=[]
    with MT5Client(settings) as client:
        service=SymbolService(client.mt5,settings); rows=[]
        for symbol in service.get_candidates():
            if not client.mt5.symbol_select(symbol,True): continue
            tick=client.mt5.symbol_info_tick(symbol); frame=get_closed_candles(client.mt5,symbol,'M1',160)
            if tick is None or frame is None or len(frame)<30: continue
            atr=float(ind.atr(frame).iloc[-1]); info=client.mt5.symbol_info(symbol)
            if atr<=0 or not info: continue
            rows.append({'symbol':symbol,'asset_group':service.get_asset_group(symbol),'spread_price':max(0.0,float(tick.ask)-float(tick.bid)),'atr_price':atr,'activity':float(frame.tick_volume.tail(60).sum()),'horizon_minutes':20,'volume_min':float(info.volume_min),'volume_step':float(info.volume_step),'contract_size':float(info.trade_contract_size)})
        brain=settings.config.get('brain',{}); selected=select_universe(rows,brain.get('universe_quotas',{}),int(brain.get('max_symbols',400)))
        if len(selected)<200: raise SystemExit(f'Only {len(selected)} usable symbols found; need at least 200. Check Market Watch and open sessions.')
        save_universe(selected,base/'universe.json')
        print(f'Brain universe: {len(selected)} symbols; free disk {free/1024**3:.1f} GB')
        by_group={}
        for row in selected: by_group[row['asset_group']]=by_group.get(row['asset_group'],0)+1
        print(f'Group counts: {by_group}')
        download_history(client.mt5,[row['symbol'] for row in selected],['M1','M5','M15','H1'],settings=settings)
    return 0

if __name__=='__main__': raise SystemExit(main())
