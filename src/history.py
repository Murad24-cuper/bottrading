"""Incremental UTC OHLCV history download to Parquet through local MT5."""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from pathlib import Path
import re
import json
import pandas as pd
from .symbols import SymbolService

TF_MINUTES={'M1':1,'M5':5,'M15':15,'H1':60}

def _safe_name(symbol): return re.sub(r'[^A-Za-z0-9_.-]','_',symbol)
def history_path(directory,symbol,timeframe): return Path(directory)/f'{_safe_name(symbol)}_{timeframe}.parquet'

def _rates(mt5,symbol,timeframe,start,end):
    tf=getattr(mt5,'TIMEFRAME_'+timeframe)
    rows=mt5.copy_rates_range(symbol,tf,start,end)
    if rows is None: raise RuntimeError(f'copy_rates_range failed for {symbol} {timeframe}: {mt5.last_error()}')
    frame=pd.DataFrame(rows)
    if frame.empty: return pd.DataFrame(columns=['open','high','low','close','tick_volume','spread'],index=pd.DatetimeIndex([],tz='UTC',name='time'))
    frame['time']=pd.to_datetime(frame['time'],unit='s',utc=True)
    return frame.set_index('time')[['open','high','low','close','tick_volume','spread']].sort_index()

def download_history(mt5,symbols,timeframes,date_from=None,date_to=None,settings=None):
    """Fetch only ranges outside cached files and return a symbol/timeframe map."""
    end=date_to or datetime.now(timezone.utc)
    if end.tzinfo is None: end=end.replace(tzinfo=timezone.utc)
    end=end.astimezone(timezone.utc)
    history_cfg=(settings.config if hasattr(settings,'config') else settings or {}).get('history',{})
    base=Path(history_cfg.get('data_dir','data/history'))
    if not base.is_absolute(): base=Path(getattr(settings,'root',Path.cwd()))/base
    months_cfg=history_cfg.get('ranges_months',{'M1':3,'M5':12,'M15':36,'H1':36})
    result={}; specs_path=base/'symbol_specs.json'
    if specs_path.exists():
        try: metadata=json.loads(specs_path.read_text(encoding='utf-8'))
        except (OSError,json.JSONDecodeError): metadata={}
    else: metadata={}
    symbol_service=SymbolService(mt5,settings) if settings is not None else None
    for symbol in symbols:
        result[symbol]={}
        if not mt5.symbol_select(symbol,True): raise RuntimeError(f'symbol_select {symbol} failed: {mt5.last_error()}')
        info=mt5.symbol_info(symbol)
        if info:
            raw=info._asdict()
            metadata[symbol]={key:raw.get(key) for key in ('digits','point','trade_tick_size','trade_tick_value','trade_tick_value_profit','trade_tick_value_loss','volume_min','volume_step','volume_max')}
            metadata[symbol]['point_size']=float(info.point)
            metadata[symbol]['asset_group']=symbol_service.get_asset_group(symbol) if symbol_service else 'other'
            tick=mt5.symbol_info_tick(symbol) if hasattr(mt5,'symbol_info_tick') else None
            if tick:
                margin=mt5.order_calc_margin(getattr(mt5,'ORDER_TYPE_BUY',0),symbol,1.0,float(tick.ask))
                if margin is not None: metadata[symbol]['margin_per_lot']=float(margin)
        for tf in timeframes:
            start=date_from
            if start is None: start=end-timedelta(days=30.4375*int(months_cfg.get(tf,12)))
            if start.tzinfo is None: start=start.replace(tzinfo=timezone.utc)
            start=start.astimezone(timezone.utc)
            path=base/f'{_safe_name(symbol)}_{tf}.parquet'; path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists():
                existing=pd.read_parquet(path)
                if not isinstance(existing.index,pd.DatetimeIndex):
                    if 'time' not in existing: raise ValueError(f'Invalid history file: {path}')
                    existing['time']=pd.to_datetime(existing.time,utc=True); existing=existing.set_index('time')
                existing.index=pd.to_datetime(existing.index,utc=True); existing=existing.sort_index()
            else: existing=pd.DataFrame()
            ranges=[]
            if existing.empty: ranges=[(start,end)]
            else:
                first=existing.index.min().to_pydatetime(); last=existing.index.max().to_pydatetime()
                step=timedelta(minutes=TF_MINUTES[tf])
                if start<first: ranges.append((start,min(end,first)))
                after=last+step
                if after<end: ranges.append((max(start,after),end))
            new=[_rates(mt5,symbol,tf,a,b) for a,b in ranges if a<b]
            parts=[frame for frame in (existing,*new) if not frame.empty]
            combined=pd.concat(parts).sort_index() if parts else pd.DataFrame(columns=['open','high','low','close','tick_volume','spread'],index=pd.DatetimeIndex([],tz='UTC',name='time'))
            if not combined.empty: combined=combined[~combined.index.duplicated(keep='last')]
            completed_before=datetime.now(timezone.utc)
            combined=combined[[stamp+timedelta(minutes=TF_MINUTES[tf])<=completed_before for stamp in combined.index]]
            combined.to_parquet(path)
            result[symbol][tf]=combined.loc[(combined.index>=start)&(combined.index<=end)]
            print(f'{symbol} {tf}: received {len(result[symbol][tf])} bars ({start.isoformat()} to {end.isoformat()})')
    if metadata:
        specs_path.parent.mkdir(parents=True,exist_ok=True)
        specs_path.write_text(json.dumps(metadata,indent=2,default=str),encoding='utf-8')
    return result
