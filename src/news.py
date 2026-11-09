"""Read-only economic calendar filtering for entry decisions."""
from __future__ import annotations

import csv
import json
import urllib.request
import xml.etree.ElementTree as ET
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


def _utc_stamp(value: str) -> datetime | None:
    try:
        stamp = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        return None
    return stamp.astimezone(timezone.utc)


def parse_ff_json(payload: str | bytes) -> list[CalendarEvent]:
    """Parse the public ForexFactory-format JSON feed; feed ISO offsets are honored."""
    rows = json.loads(payload)
    if not isinstance(rows, list):
        raise ValueError("calendar JSON must be a list")
    events = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        stamp = _utc_stamp(str(row.get("date", "")))
        if not stamp:
            continue
        events.append(CalendarEvent(stamp, str(row.get("country", "")).upper(),
                                   str(row.get("impact", "")).upper(),
                                   str(row.get("title", "")), "",
                                   str(row.get("forecast", "")), str(row.get("previous", ""))))
    return events


def parse_ff_xml(payload: str | bytes) -> list[CalendarEvent]:
    """Parse recorded ForexFactory XML; naive calendar wall times are US/Eastern."""
    from zoneinfo import ZoneInfo
    try:
        import defusedxml.ElementTree as safe_ET
        root = safe_ET.fromstring(payload)
    except ImportError:
        root = ET.fromstring(payload)
    eastern = ZoneInfo("America/New_York")
    events = []
    for row in root.findall(".//event"):
        fields = {child.tag.lower(): (child.text or "").strip() for child in row}
        date_text, time_text = fields.get("date", ""), fields.get("time", "")
        stamp = _utc_stamp(date_text)
        if stamp is None:
            for fmt in ("%m-%d-%Y", "%Y-%m-%d"):
                try:
                    date = datetime.strptime(date_text, fmt).date()
                    break
                except ValueError:
                    date = None
            if date is None or not time_text or time_text.lower() in {"all day", "tentative"}:
                continue
            wall_time = None
            for t_fmt in ("%I:%M%p", "%H:%M"):
                try:
                    wall_time = datetime.strptime(time_text.upper(), t_fmt).time()
                    break
                except ValueError:
                    pass
            if wall_time is None:
                continue
            wall = datetime.combine(date, wall_time, tzinfo=eastern)
            stamp = wall.astimezone(timezone.utc)
        events.append(CalendarEvent(stamp, fields.get("country", "").upper(),
                                   fields.get("impact", "").upper(), fields.get("title", ""),
                                   fields.get("actual", ""), fields.get("forecast", ""),
                                   fields.get("previous", "")))
    return events


def load_calendar(csv_path: str | Path | None, cache_path: str | Path,
                  now: datetime | None = None, refresh_hours: float = 6,
                  stale_hours: float = 24, fetch=None):
    """Prefer a fresh terminal CSV, otherwise refresh/read the public cached feed.

    Returns ``(events, updated_at, source, age_hours)``. A failed refresh keeps a
    previously downloaded feed if it is no older than ``stale_hours``.
    """
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    events, updated = parse_calendar(csv_path) if csv_path else ([], None)
    if updated and 0 <= (now - updated).total_seconds() <= stale_hours * 3600:
        return events, updated, "MT5 CSV", max(0.0, (now-updated).total_seconds()/3600)
    cache = Path(cache_path)
    cached_events, cached_updated = [], None
    if cache.is_file():
        cached_updated = datetime.fromtimestamp(cache.stat().st_mtime, timezone.utc)
        try:
            cached_events = parse_ff_json(cache.read_bytes())
        except (ValueError, OSError, TypeError):
            try:
                cached_events = parse_ff_xml(cache.read_bytes())
            except (ValueError, ET.ParseError, OSError, TypeError):
                cached_events = []
    age = (now-cached_updated).total_seconds()/3600 if cached_updated else float("inf")
    if age >= refresh_hours:
        try:
            payload = (fetch or _download_calendar)()
            parsed = parse_ff_json(payload)
            if not parsed:
                raise ValueError("calendar feed contained no parseable events")
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(payload if isinstance(payload, bytes) else payload.encode("utf-8"))
            cached_events = parsed
            cached_updated = now
            age = 0.0
        except Exception:
            pass
    if cached_updated and age <= stale_hours and cached_events:
        return cached_events, cached_updated, "ForexFactory cache", max(0.0, age)
    return [], None, "fallback window", float("inf")


def _download_calendar(url: str = "https://nfs.faireconomy.media/ff_calendar_thisweek.json") -> bytes:
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ValueError(f"Insecure or unsupported calendar URL scheme: {url!r}")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "tradingbot-calendar/1.0"})
    with urllib.request.urlopen(request, timeout=12) as response:
        if response.status != 200:
            raise OSError(f"calendar HTTP {response.status}")
        return response.read(2_000_000)


def event_matches_symbol(event: CalendarEvent, symbol: str) -> bool:
    name = symbol.upper()
    return any(alias in name or name in alias for alias in CURRENCY_SYMBOLS.get(event.currency, ()))


def minutes_to_next_high_impact(symbol: str, now_utc: datetime, events: list[CalendarEvent]) -> float | None:
    """Return minutes to the next mapped high-impact event, or None when unavailable."""
    now=now_utc.replace(tzinfo=timezone.utc) if now_utc.tzinfo is None else now_utc.astimezone(timezone.utc)
    upcoming=[event for event in events if event.importance=='HIGH' and event.time>=now and event_matches_symbol(event,symbol)]
    return (min(event.time for event in upcoming)-now).total_seconds()/60 if upcoming else None


def entry_block_reason(symbol: str, now_utc: datetime, events: list[CalendarEvent], updated_at: datetime | None, stale_after_hours: float = 24.0) -> str:
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
