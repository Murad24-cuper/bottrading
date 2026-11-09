"""Convert broker-local MT5 timestamps to UTC using a live liquid-symbol tick."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import time

_OFFSET_CACHE: dict[int, tuple[float, timedelta]] = {}
_LAST_KNOWN_OFFSETS: dict[int, timedelta] = {}
_GLOBAL_LAST_OFFSET: timedelta | None = None


def detect_server_utc_offset(mt5, now_utc: datetime | None = None,
                             symbols: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDJPY"),
                             tolerance_seconds: int = 600, max_tick_age_seconds: int=900,
                             fallback_offset: timedelta | None = None) -> timedelta:
    """Estimate server minus UTC offset using a fresh FX tick or an open-market fallback."""
    global _GLOBAL_LAST_OFFSET
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    candidates=list(symbols)
    # At weekends the major FX references are stale. Discover an actively
    # quoted crypto/24-7 symbol instead of deriving an offset from Friday's tick.
    try:
        rows=mt5.symbols_get() or ()
        fallback=[]
        for row in rows:
            name=str(getattr(row,'name','')); path=str(getattr(row,'path','')).lower()
            upper=name.upper()
            if 'crypto' in path or any(token in upper for token in ('BTC','ETH','24-7','24/7')):
                priority=0 if upper.startswith(('BTCUSD','ETHUSD')) else 1 if '24-7' in upper or '24/7' in upper else 2
                fallback.append((priority,name))
        candidates.extend(name for _,name in sorted(fallback)[:12])
    except (AttributeError,TypeError,RuntimeError):
        pass
    for symbol in dict.fromkeys(candidates):
        try:
            if not mt5.symbol_select(symbol, True):
                continue
            tick = mt5.symbol_info_tick(symbol)
            stamp = (float(getattr(tick, "time_msc", 0) or 0) / 1000
                     if tick and getattr(tick, "time_msc", 0)
                     else float(getattr(tick, "time", 0) or 0) if tick else 0)
            if stamp <= 0:
                continue
            difference = stamp - now.timestamp()
            hours = round(difference / 3600)
            age=now.timestamp()-(stamp-hours*3600)
            # A closed-market tick can be many hours behind UTC. Rounding that
            # gap as an offset (for example -44h on Sunday) shifts every quote
            # into the future. Real broker UTC offsets fit within this bound.
            if (-14 <= hours <= 14 and
                    abs(difference - hours * 3600) <= tolerance_seconds and
                    -tolerance_seconds <= age <= max_tick_age_seconds):
                res = timedelta(hours=hours)
                key = id(mt5) if mt5 is not None else None
                if key is not None:
                    _LAST_KNOWN_OFFSETS[key] = res
                _GLOBAL_LAST_OFFSET = res
                try:
                    from pathlib import Path
                    cache_file = Path("data/.server_offset")
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    cache_file.write_text(str(hours), encoding="utf-8")
                except Exception:
                    pass
                return res
        except (AttributeError, TypeError, ValueError, OverflowError):
            continue

    # Weekend / closed market fallback:
    key = id(mt5) if mt5 is not None else None
    if key is not None and key in _LAST_KNOWN_OFFSETS:
        return _LAST_KNOWN_OFFSETS[key]
    if _GLOBAL_LAST_OFFSET is not None:
        return _GLOBAL_LAST_OFFSET
    if fallback_offset is not None:
        return fallback_offset
    try:
        from pathlib import Path
        cache_file = Path("data/.server_offset")
        if cache_file.exists():
            val = int(cache_file.read_text(encoding="utf-8").strip())
            if -14 <= val <= 14:
                return timedelta(hours=val)
    except Exception:
        pass
    try:
        import yaml
        from pathlib import Path
        cfg_file = Path("config.yaml")
        if cfg_file.exists():
            data = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
            cfg_h = data.get("time", {}).get("default_server_utc_offset_hours")
            if cfg_h is not None and -14 <= int(cfg_h) <= 14:
                return timedelta(hours=int(cfg_h))
    except Exception:
        pass
    return timedelta(0)


def server_utc_offset(mt5, fallback_offset: timedelta | None = None) -> timedelta:
    """Return a short-lived cached broker offset, detecting it from a liquid tick."""
    key = id(mt5)
    cached = _OFFSET_CACHE.get(key)
    now = time.monotonic()
    if cached and now - cached[0] < 60:
        return cached[1]
    offset = detect_server_utc_offset(mt5, fallback_offset=fallback_offset)
    _OFFSET_CACHE[key] = (now, offset)
    return offset


def mt5_epoch_to_utc(value: float | int, mt5=None, offset: timedelta | None = None) -> datetime:
    """Convert an MT5 broker-time epoch to an aware UTC datetime."""
    server_offset = offset if offset is not None else server_utc_offset(mt5) if mt5 is not None else timedelta(0)
    return datetime.fromtimestamp(float(value), timezone.utc) - server_offset


def server_clock_drift_seconds(mt5, symbol: str, now_utc: datetime | None = None) -> float | None:
    """Estimate PC UTC drift from a fresh broker tick and whole-hour server offset."""
    now=now_utc or datetime.now(timezone.utc)
    now=now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    if not mt5.symbol_select(symbol,True): return None
    tick=mt5.symbol_info_tick(symbol)
    stamp=float(getattr(tick,'time_msc',0) or 0)/1000 if tick and getattr(tick,'time_msc',0) else float(getattr(tick,'time',0) or 0) if tick else 0
    if stamp<=0: return None
    delta=stamp-now.timestamp()
    return abs(delta-round(delta/3600)*3600)
