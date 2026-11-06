"""Infer recurring per-symbol sessions from broker-supplied hourly bars."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import statistics

import pandas as pd


def session_closures(frame: pd.DataFrame) -> list[tuple[int, int, float]]:
    """Return weekday, minute-of-day, and duration for observed bar gaps."""
    if frame is None or frame.empty or len(frame.index) < 3:
        return []
    index = pd.DatetimeIndex(frame.index)
    if index.tz is None:
        index = index.tz_localize(timezone.utc)
    else:
        index = index.tz_convert(timezone.utc)
    gaps = []
    for previous, following in zip(index[:-1], index[1:]):
        elapsed = (following - previous).total_seconds() / 3600
        # A normal hourly bar sequence advances by one hour. A larger gap is
        # treated as a session boundary; median repeats filter one-off misses.
        if elapsed >= 1.5:
            close = previous.to_pydatetime() + timedelta(hours=1)
            gaps.append((close.weekday(), close.hour * 60 + close.minute, elapsed - 1.0))
    return gaps


def next_session_close(frame: pd.DataFrame, now_utc: datetime,
                       min_session_gap_hours: float = 0.0) -> tuple[datetime, float] | None:
    """Predict the next recurring session close with a gap at least this long."""
    now = now_utc.replace(tzinfo=timezone.utc) if now_utc.tzinfo is None else now_utc.astimezone(timezone.utc)
    samples = session_closures(frame)
    by_weekday: dict[int, list[tuple[int, float]]] = {}
    for weekday, minute, gap_hours in samples:
        if gap_hours > min_session_gap_hours:
            by_weekday.setdefault(weekday, []).append((minute, gap_hours))
    upcoming = []
    for weekday, values in by_weekday.items():
        minute = int(statistics.median(item[0] for item in values))
        gap_hours = statistics.median(item[1] for item in values)
        days_ahead = (weekday - now.weekday()) % 7
        candidate_date = (now + timedelta(days=days_ahead)).date()
        candidate = datetime(candidate_date.year, candidate_date.month, candidate_date.day,
                             minute // 60, minute % 60, tzinfo=timezone.utc)
        if candidate <= now:
            candidate += timedelta(days=7)
        upcoming.append((candidate, float(gap_hours)))
    return min(upcoming, key=lambda item: item[0]) if upcoming else None

def session_context(frame: pd.DataFrame, now_utc: datetime|None=None) -> dict:
    """Summarize UTC trading session and range versus recent same-session days."""
    now=now_utc or datetime.now(timezone.utc)
    now=now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    hour=now.hour
    if 12<=hour<16: name='London-NY overlap'; opened=12
    elif 7<=hour<12: name='London'; opened=7
    elif 16<=hour<21: name='New York'; opened=16
    elif 0<=hour<7: name='Asia'; opened=0
    else: name='off-hours'; opened=21
    if frame is None or frame.empty or not isinstance(frame.index,pd.DatetimeIndex):
        return {'session':name,'minutes_since_open':int((now.hour-opened)*60+now.minute),'range':None,'average_range':None,'range_vs_average':None}
    data=frame.iloc[:-1].copy(); ix=data.index
    if ix.tz is None: ix=ix.tz_localize(timezone.utc)
    else: ix=ix.tz_convert(timezone.utc)
    data.index=ix
    tod=(data.index.hour>=opened)&(data.index.date==now.date())&(data.index<=now)
    current=data.loc[tod]
    current_range=float(current.high.max()-current.low.min()) if not current.empty else 0.0
    ranges=[]
    for day in sorted(set(data.index.date)):
        if day>=now.date(): continue
        selected=data.loc[(data.index.date==day)&(data.index.hour>=opened)&(data.index.hour<now.hour+1)]
        if not selected.empty: ranges.append(float(selected.high.max()-selected.low.min()))
    avg=sum(ranges[-20:])/len(ranges[-20:]) if ranges else None
    return {'session':name,'minutes_since_open':int((now.hour-opened)*60+now.minute),'range':current_range,'average_range':avg,'range_vs_average':current_range/avg if avg else None}
