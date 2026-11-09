"""Incremental UTC OHLCV history download to Parquet through local MT5."""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from pathlib import Path
import re
import json
import hashlib
import pandas as pd
from .symbols import SymbolService
from .time_utils import server_utc_offset

TF_MINUTES={'M1':1,'M5':5,'M15':15,'H1':60}

def _safe_name(symbol): return re.sub(r'[^A-Za-z0-9_.-]','_',symbol)
def history_path(directory,symbol,timeframe): return Path(directory)/f'{_safe_name(symbol)}_{timeframe}.parquet'

def build_history_manifest(frame,path,symbol,timeframe,source='MT5 terminal'):
    """Describe exact stored range, missing-bar intervals and file digest."""
    path=Path(path); index=pd.to_datetime(frame.index,utc=True).sort_values()
    delta=timedelta(minutes=TF_MINUTES[timeframe]); gaps=[]
    for before,after in zip(index[:-1],index[1:]):
        missing=max(0,int((after-before).total_seconds()//delta.total_seconds())-1)
        if missing:
            gaps.append({'after_utc':before.isoformat(),'before_utc':after.isoformat(),'missing_bars':missing})
    digest=None
    if path.is_file():
        hasher=hashlib.sha256()
        with path.open('rb') as source_file:
            for block in iter(lambda:source_file.read(1024*1024),b''): hasher.update(block)
        digest=hasher.hexdigest()
    return {'source':source,'symbol':str(symbol),'timeframe':str(timeframe),
            'start_utc':index.min().isoformat() if len(index) else None,
            'end_utc':index.max().isoformat() if len(index) else None,
            'rows':int(len(index)),'gap_count':len(gaps),'gaps':gaps,
            'sha256':digest,'file':path.name}

def _write_history_manifest(base,manifest):
    folder=Path(base)/'manifests'; folder.mkdir(parents=True,exist_ok=True)
    target=folder/f"{_safe_name(manifest['symbol'])}_{manifest['timeframe']}.json"
    temporary=target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(manifest,indent=2),encoding='utf-8'); temporary.replace(target)
    return target

def _rates(mt5,symbol,timeframe,start,end,chunk_days=7,max_bars=80000):
    """Read bounded chunks, keep available bars, and log unavailable intervals."""
    tf=getattr(mt5,'TIMEFRAME_'+timeframe)
    def fetch(a,b):
        rows=mt5.copy_rates_range(symbol,tf,a,b)
        return None if rows is None else pd.DataFrame(rows)
    max_days=max(1,int(int(max_bars)*TF_MINUTES[timeframe]/1440))
    step_days=max(1,min(int(chunk_days),max_days))
    def fetch_chunk(a,b):
        try: part=fetch(a,b)
        except Exception as exc:
            part=None; failure=f'{type(exc).__name__}: {exc}'
        else: failure=str(mt5.last_error()) if part is None else ''
        if part is not None: return [part] if not part.empty else []
        if (b-a).total_seconds()<=7*86400:
            print(f'{symbol} {timeframe}: unavailable chunk {a.isoformat()}..{b.isoformat()} ({failure})')
            return []
        midpoint=a+(b-a)/2
        return fetch_chunk(a,midpoint)+fetch_chunk(midpoint,b)
    frames=[]; cursor=start; step=timedelta(days=step_days)
    while cursor<end:
        chunk_end=min(cursor+step,end)
        frames.extend(fetch_chunk(cursor,chunk_end))
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
    full_config=settings.config if hasattr(settings,'config') else settings or {}
    history_cfg=full_config.get('history',{})
    base=Path(history_cfg.get('data_dir','data/history'))
    if not base.is_absolute(): base=Path(getattr(settings,'root',Path.cwd()))/base
    base.mkdir(parents=True,exist_ok=True)
    months_cfg=history_cfg.get('ranges_months',{'M1':3,'M5':12,'M15':36,'H1':36})
    max_bytes=int(float(history_cfg.get('max_storage_gb',5))*1024**3)
    import shutil
    min_free=int(float((settings.config if hasattr(settings,'config') else settings or {}).get('health',{}).get('stop_downloads_free_gb',2))*1024**3)
    result={}; specs_path=base/'symbol_specs.json'
    if specs_path.exists():
        try: metadata=json.loads(specs_path.read_text(encoding='utf-8'))
        except (OSError,json.JSONDecodeError): metadata={}
    else: metadata={}
    symbol_service=SymbolService(mt5,settings) if settings is not None else None
    for symbol in symbols:
        free=shutil.disk_usage(base if base.exists() else base.parent).free
        if free<min_free: raise RuntimeError(f'History download stopped: only {free/1024**3:.2f} GB disk space remains; configured minimum is {min_free/1024**3:.1f} GB.')
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
            path=base/f'{_safe_name(symbol)}_{tf}.parquet'; path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists():
                existing=pd.read_parquet(path)
                if not isinstance(existing.index,pd.DatetimeIndex):
                    if 'time' not in existing: raise ValueError(f'Invalid history file: {path}')
                    existing['time']=pd.to_datetime(existing.time,utc=True); existing=existing.set_index('time')
                existing.index=pd.to_datetime(existing.index,utc=True); existing=existing.sort_index()
            else: existing=pd.DataFrame()
            weekend_names={str(name) for name in full_config.get('universe',{}).get('weekend_symbols',[])}
            range_source=history_cfg.get('weekend_ranges_months',months_cfg) if symbol in weekend_names else months_cfg
            start=date_from
            if start is None: start=end-timedelta(days=30.4375*int(range_source.get(tf,12)))
            if start.tzinfo is None: start=start.replace(tzinfo=timezone.utc)
            start=start.astimezone(timezone.utc)
            if existing.empty: ranges=[(start,end)]
            else:
                first=existing.index.min().to_pydatetime(); last=existing.index.max().to_pydatetime(); step=timedelta(minutes=TF_MINUTES[tf])
                ranges=[]
                if start<first: ranges.append((start,min(end,first)))
                if last+step<end: ranges.append((max(start,last+step),end))
            chunk_days=int(history_cfg.get('download_chunk_days',{}).get(tf,7))
            new=[_rates(mt5,symbol,tf,a,b,chunk_days=chunk_days,max_bars=int(history_cfg.get('max_bars_per_request',80000))) for a,b in ranges if a<b]
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
            _write_history_manifest(base,build_history_manifest(combined,path,symbol,tf))
            if actual.empty: print(f'{symbol} {tf}: received 0 bars; no actual range available in {start.isoformat()}..{end.isoformat()}')
            else: print(f'{symbol} {tf}: received {len(actual)} bars; actual range {actual.index.min().isoformat()}..{actual.index.max().isoformat()}')
    if metadata:
        specs_path.parent.mkdir(parents=True,exist_ok=True)
        specs_path.write_text(json.dumps(metadata,indent=2,default=str),encoding='utf-8')
    return result

def refresh_incremental_batch(mt5,settings,now=None):
    """Fetch one bounded update or historical backfill chunk through the bot's MT5 session."""
    cfg=settings.config.get('history',{})
    if not cfg.get('incremental_refresh_enabled',False): return None
    universe_path=Path(settings.data_dir)/'brain'/'universe.json'
    if not universe_path.is_file(): return None
    payload=json.loads(universe_path.read_text(encoding='utf-8'))
    symbols=[str(row['symbol']) for row in payload.get('symbols',[]) if isinstance(row,dict) and row.get('symbol')]
    timeframes=[str(tf) for tf in cfg.get('incremental_timeframes',['M1','M5','M15','H1']) if tf in TF_MINUTES]
    if not symbols or not timeframes: return None
    cursor_path=Path(settings.data_dir)/'history_refresh_cursor.json'
    try: cursor=max(0,int(json.loads(cursor_path.read_text(encoding='utf-8')).get('cursor',0)))
    except (OSError,ValueError,TypeError,json.JSONDecodeError): cursor=0
    weekend_names={str(name) for name in settings.config.get('universe',{}).get('weekend_symbols',[])}
    weekend_timeframes=cfg.get('weekend_timeframes',['M1','M5','M15'])
    pairs=[(symbol,tf) for symbol in symbols for tf in timeframes if symbol not in weekend_names or tf in weekend_timeframes]
    cursor%=len(pairs); symbol,timeframe=pairs[cursor]
    end=now or datetime.now(timezone.utc)
    end=end.replace(tzinfo=timezone.utc) if end.tzinfo is None else end.astimezone(timezone.utc)
    days=max(1,int(cfg.get('incremental_batch_days',{}).get(timeframe,7)))
    if symbol in weekend_names:
        months=max(1,int(cfg.get('weekend_ranges_months',{}).get(timeframe,6 if timeframe=='M1' else 24)))
    else:
        months=max(1,int(cfg.get('ranges_months',{}).get(timeframe,12)))
    target_start=end-timedelta(days=30.4375*months)
    base=Path(cfg.get('data_dir','data/history'))
    if not base.is_absolute(): base=Path(getattr(settings,'root',Path.cwd()))/base
    cached=history_path(base,symbol,timeframe)
    request_end=end
    if cached.is_file():
        try:
            frame=pd.read_parquet(cached)
            index=frame.index if isinstance(frame.index,pd.DatetimeIndex) else pd.to_datetime(frame['time'],utc=True)
            oldest=pd.Timestamp(index.min()).to_pydatetime()
            if oldest.tzinfo is None: oldest=oldest.replace(tzinfo=timezone.utc)
            else: oldest=oldest.astimezone(timezone.utc)
            if oldest>target_start:
                request_end=oldest
        except (OSError,ValueError,KeyError,TypeError):
            pass
    request_start=max(target_start,request_end-timedelta(days=days))
    result=download_history(mt5,[symbol],[timeframe],request_start,request_end,settings)
    cursor_path.parent.mkdir(parents=True,exist_ok=True)
    temp=cursor_path.with_suffix('.tmp')
    temp.write_text(json.dumps({'cursor':(cursor+1)%len(pairs),'updated_at':end.isoformat()}),encoding='utf-8')
    temp.replace(cursor_path)
    return {'symbol':symbol,'timeframe':timeframe,'bars':len(result.get(symbol,{}).get(timeframe,[])),'cursor':(cursor+1)%len(pairs)}
