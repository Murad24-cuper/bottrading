from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import pytest
from src.time_utils import detect_server_utc_offset, server_utc_offset

def test_detect_server_utc_offset_uses_fallback_or_cache_on_weekend():
    mock_mt5 = MagicMock()
    mock_mt5.symbols_get.return_value = []
    mock_mt5.symbol_select.return_value = True
    # All ticks are None or stale
    mock_mt5.symbol_info_tick.return_value = None

    # Should use fallback_offset instead of defaulting to timedelta(0)
    offset = detect_server_utc_offset(mock_mt5, fallback_offset=timedelta(hours=2))
    assert offset == timedelta(hours=2), f"Expected timedelta(hours=2), got {offset}"

def test_detect_server_utc_offset_remembers_last_known_offset():
    mock_mt5 = MagicMock()
    mock_mt5.symbols_get.return_value = []
    mock_mt5.symbol_select.return_value = True

    now = datetime(2026, 11, 6, 12, 0, 0, tzinfo=timezone.utc) # Friday noon
    # Server is UTC+2: server time is 14:00:00
    server_epoch = now.timestamp() + 7200
    tick = MagicMock()
    tick.time = server_epoch
    tick.time_msc = int(server_epoch * 1000)
    mock_mt5.symbol_info_tick.return_value = tick

    detected = detect_server_utc_offset(mock_mt5, now_utc=now)
    assert detected == timedelta(hours=2)

    # Now simulate weekend: ticks are stale (market closed)
    stale_tick = MagicMock()
    stale_tick.time = server_epoch # stale by > 24h
    stale_tick.time_msc = int(server_epoch * 1000)
    mock_mt5.symbol_info_tick.return_value = stale_tick

    weekend_now = datetime(2026, 11, 8, 12, 0, 0, tzinfo=timezone.utc) # Sunday
    weekend_offset = detect_server_utc_offset(mock_mt5, now_utc=weekend_now)

    # It must NOT fall back to timedelta(0); it must preserve last known offset (UTC+2)
    assert weekend_offset == timedelta(hours=2), f"Weekend offset fell back to {weekend_offset} instead of remembering last known offset"
