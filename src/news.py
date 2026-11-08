"""Read-only economic calendar filtering for entry decisions."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True)
class CalendarEvent:
    time: datetime
    currency: str
    importance: str
    name: str
    actual: str = ""
    forecast: str = ""
    previous: str = ""


CURRENCY_SYMBOLS = {
    "USD": ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "US500", "NAS100", "US30", "GOLD"),
    "EUR": ("EURUSD", "GER40"),
    "GBP": ("GBPUSD",),
    "JPY": ("USDJPY",),
    "AUD": ("AUDUSD",),
    "CAD": ("USDCAD",),
}


def parse_calendar(path: str | Path) -> tuple[list[CalendarEvent], datetime | None]:
    """Parse calendar CSV and return rows plus newest file timestamp."""
    file = Path(path)
    if not file.is_file():
        return [], None
    events = []
    for row in csv.DictReader(file.open("r", encoding="utf-8-sig", newline="")):
        try:
            stamp = datetime.fromisoformat(row["time_utc"].replace("Z", "+00:00"))
            stamp = stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)
            events.append(CalendarEvent(stamp, row.get("currency", "").upper(), row.get("importance", "").upper(), row.get("name", ""), row.get("actual", ""), row.get("forecast", ""), row.get("previous", "")))
        except (KeyError, ValueError):
            continue
    try:
        modified = datetime.fromtimestamp(file.stat().st_mtime, timezone.utc)
    except OSError:
        modified = None
    return events, modified


def event_matches_symbol(event: CalendarEvent, symbol: str) -> bool:
    name = symbol.upper()
    return any(alias in name or name in alias for alias in CURRENCY_SYMBOLS.get(event.currency, ()))


def minutes_to_next_high_impact(symbol: str, now_utc: datetime, events: list[CalendarEvent]) -> float | None:
    """Return minutes to the next mapped high-impact event, or None when unavailable."""
    now=now_utc.replace(tzinfo=timezone.utc) if now_utc.tzinfo is None else now_utc.astimezone(timezone.utc)
    upcoming=[event for event in events if event.importance=='HIGH' and event.time>=now and event_matches_symbol(event,symbol)]
    return (min(event.time for event in upcoming)-now).total_seconds()/60 if upcoming else None


def entry_block_reason(symbol: str, now_utc: datetime, events: list[CalendarEvent], updated_at: datetime | None, stale_after_hours: float = 2.0) -> str:
    """Block around high-impact events, with a conservative stale-feed window."""
    now = now_utc.replace(tzinfo=timezone.utc) if now_utc.tzinfo is None else now_utc.astimezone(timezone.utc)
    if updated_at is None or now - updated_at > timedelta(hours=stale_after_hours):
        currencies = ("USD", "EUR", "GBP", "JPY")
        if now.hour in (12, 13) or (now.hour == 14 and now.minute < 30):
            if any(event_matches_symbol(CalendarEvent(now, cur, "HIGH", ""), symbol) for cur in currencies):
                return "calendar missing/stale; conservative USD/EUR/GBP/JPY time window"
    for event in events:
        if event.importance != "HIGH" or not event_matches_symbol(event, symbol):
            continue
        if event.time - timedelta(minutes=15) <= now <= event.time + timedelta(minutes=15):
            return f"high-impact {event.currency} event: {event.name}"
    return ""


def terminal_calendar_path(mt5) -> Path | None:
    """Find the exporter file under this bot's already connected MT5 terminal."""
    info = mt5.terminal_info()
    data_path = getattr(info, "data_path", "") if info else ""
    return Path(data_path) / "MQL5" / "Files" / "calendar_events.csv" if data_path else None
