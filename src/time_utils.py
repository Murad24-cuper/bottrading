"""Convert broker-local MT5 timestamps to UTC using a live liquid-symbol tick."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import time

_OFFSET_CACHE: dict[int, tuple[float, timedelta]] = {}


def detect_server_utc_offset(mt5, now_utc: datetime | None = None,
                             symbols: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDJPY"),
                             tolerance_seconds: int = 600) -> timedelta:
    """Estimate server minus UTC offset, rounded to the nearest whole hour."""
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    for symbol in symbols:
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
            if abs(difference - hours * 3600) <= tolerance_seconds:
                return timedelta(hours=hours)
        except (AttributeError, TypeError, ValueError, OverflowError):
            continue
    return timedelta(0)


def server_utc_offset(mt5) -> timedelta:
    """Return a short-lived cached broker offset, detecting it from a liquid tick."""
    key = id(mt5)
    cached = _OFFSET_CACHE.get(key)
    now = time.monotonic()
    if cached and now - cached[0] < 60:
        return cached[1]
    offset = detect_server_utc_offset(mt5)
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
