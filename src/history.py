"""Incremental UTC OHLCV history download to Parquet through local MT5."""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from pathlib import Path
import re
import json
import pandas as pd
from .symbols import SymbolService
from .time_utils import server_utc_offset

TF_MINUTES={'M1':1,'M5':5,'M15':15,'H1':60}

def _safe_name(symbol): return re.sub(r'[^A-Za-z0-9_.-]','_',symbol)
def history_path(directory,symbol,timeframe): return Path(directory)/f'{_safe_name(symbol)}_{timeframe}.parquet'

def _rates(mt5,symbol,timeframe,start,end,chunk_days=7):
    """Read a range, falling back to bounded chunks when MT5 rejects a long request."""
    tf=getattr(mt5,'TIMEFRAME_'+timeframe)
    def fetch(a,b):
        rows=mt5.copy_rates_range(symbol,tf,a,b)
        return None if rows is None else pd.DataFrame(rows)
    rows=fetch(start,end)
    if rows is None:
        print(f'{symbol} {timeframe}: full-range request failed ({mt5.last_error()}); retrying in {chunk_days}-day chunks')
        frames=[]; cursor=start; step=timedelta(days=chunk_days)
        while cursor<end:
            chunk_end=min(cursor+step,end)
            try: part=fetch(cursor,chunk_end)
            except Exception as exc:
                print(f'{symbol} {timeframe}: chunk {cursor.isoformat()}..{chunk_end.isoformat()} failed: {exc}')
                part=None
            if part is None:
                print(f'{symbol} {timeframe}: chunk {cursor.isoformat()}..{chunk_end.isoformat()} unavailable ({mt5.last_error()})')
            elif not part.empty: frames.append(part)
            cursor=chunk_end
        rows=pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()
    if rows.empty: return pd.DataFrame(columns=['open','high','low','close','tick_volume','spread'],index=pd.DatetimeIndex([],tz='UTC',name='time'))
    rows['time']=pd.to_datetime(rows['time'],unit='s',utc=True)-server_utc_offset(mt5)
    return rows.set_index('time')[['open','high','low','close','tick_volume','spread']].sort_index()

def download_history(mt5,symbols,timeframes,date_from=None,date_to=None,settings=None):
    """Fetch only ranges outside cached files and return a symbol/timeframe map."""
    end=date_to or datetime.now(timezone.utc)
    if end.tzinfo is None: end=end.replace(tzinfo=timezone.utc)
    end=end.astimezone(timezone.utc)
    history_cfg=(settings.config if hasattr(settings,'config') else settings or {}).get('history',{})
    base=Path(history_cfg.get('data_dir','data/history'))
    if not base.is_absolute(): base=Path(getattr(settings,'root',Path.cwd()))/base
    months_cfg=history_cfg.get('ranges_months',{'M1':3,'M5':12,'M15':36,'H1':36})
    max_bytes=int(float(history_cfg.get('max_storage_gb',5))*1024**3)
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
            temporary=path.with_suffix(path.suffix+'.tmp')
            combined.to_parquet(temporary)
            existing_bytes=sum(file.stat().st_size for file in base.glob('*.parquet') if file!=path)
            projected=existing_bytes+temporary.stat().st_size
            if projected>max_bytes:
                temporary.unlink(missing_ok=True)
                raise RuntimeError(f'History storage cap {max_bytes/1024**3:.1f} GB exceeded while saving {symbol} {tf}; stop before writing more data.')
            temporary.replace(path)
            result[symbol][tf]=combined.loc[(combined.index>=start)&(combined.index<=end)]
            actual=result[symbol][tf]
            if actual.empty: print(f'{symbol} {tf}: received 0 bars; no actual range available in {start.isoformat()}..{end.isoformat()}')
            else: print(f'{symbol} {tf}: received {len(actual)} bars; actual range {actual.index.min().isoformat()}..{actual.index.max().isoformat()}')
    if metadata:
        specs_path.parent.mkdir(parents=True,exist_ok=True)
        specs_path.write_text(json.dumps(metadata,indent=2,default=str),encoding='utf-8')
    return result
