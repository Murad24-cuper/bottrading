from datetime import datetime, timedelta, timezone

from src.news import CalendarEvent, entry_block_reason, event_matches_symbol, parse_calendar


def test_high_impact_event_blocks_mapped_instrument_only_inside_window():
    now=datetime(2026,11,9,13,45,tzinfo=timezone.utc)
    event=CalendarEvent(now+timedelta(minutes=10),'USD','HIGH','Inflation')
    assert 'Inflation' in entry_block_reason('EURUSD',now,[event],now)
    assert entry_block_reason('GER40Cash',now,[event],now)==''


def test_stale_calendar_uses_conservative_currency_time_window():
    now=datetime(2026,11,9,13,0,tzinfo=timezone.utc)
    assert entry_block_reason('US30Cash',now,[],now-timedelta(hours=3))
    assert entry_block_reason('BTCUSD',now,[],now-timedelta(hours=3))==''


def test_calendar_parser_normalizes_utc_and_skips_invalid_rows(tmp_path):
    path=tmp_path/'calendar.csv'
    path.write_text('time_utc,currency,importance,name,actual,forecast,previous\n2026-11-09T13:00:00+00:00,USD,HIGH,CPI,1,2,3\nbad,USD,HIGH,broken,,,\n',encoding='utf-8')
    events,updated=parse_calendar(path)
    assert len(events)==1 and events[0].time.tzinfo==timezone.utc
    assert event_matches_symbol(events[0],'US500Cash')
