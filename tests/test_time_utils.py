from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from src.time_utils import detect_server_utc_offset, mt5_epoch_to_utc
from src.market_data import get_candles
import numpy as np
import pandas as pd


class FakeMT5:
    def __init__(self, tick):
        self.tick = tick
        self.selected = []

    def symbol_select(self, symbol, enable):
        self.selected.append((symbol, enable))
        return True

    def symbol_info_tick(self, symbol):
        return self.tick


def test_detects_server_offset_from_selected_liquid_symbol():
    now = datetime(2026, 11, 5, 19, 0, tzinfo=timezone.utc)
    server_time = now + timedelta(hours=2)
    mt5 = FakeMT5(SimpleNamespace(time=int(server_time.timestamp()), time_msc=int(server_time.timestamp() * 1000)))

    assert detect_server_utc_offset(mt5, now, ("EURUSD",)) == timedelta(hours=2)
    assert mt5.selected == [("EURUSD", True)]


def test_converts_mt5_server_epoch_to_utc():
    now = datetime(2026, 11, 5, 19, 0, tzinfo=timezone.utc)
    server_time = now + timedelta(hours=2)

    assert mt5_epoch_to_utc(server_time.timestamp(), offset=timedelta(hours=2)) == now

def test_bot_normalizes_local_saturday_clock_to_utc_friday(tmp_path):
    from src.bot import TradingBot
    local=datetime(2026,11,7,0,30,tzinfo=timezone(timedelta(hours=4)))
    bot=object.__new__(TradingBot); bot.clock=lambda:local
    assert bot._now()==datetime(2026,11,6,20,30,tzinfo=timezone.utc)


def test_candle_index_is_converted_to_utc_and_symbol_is_selected(monkeypatch):
    import src.market_data as market_data

    broker_stamp = datetime(2026, 11, 5, 21, 0, tzinfo=timezone.utc).timestamp()
    class FakeRatesMT5(FakeMT5):
        TIMEFRAME_M5 = 5
        def copy_rates_from_pos(self, symbol, timeframe, shift, count):
            return np.array([(broker_stamp,1.0,1.1,0.9,1.05,10,3)], dtype=[
                ('time','i8'),('open','f8'),('high','f8'),('low','f8'),('close','f8'),('tick_volume','i8'),('spread','i8')
            ])

    mt5 = FakeRatesMT5(SimpleNamespace(time=int(broker_stamp), time_msc=int(broker_stamp*1000)))
    monkeypatch.setattr(market_data, 'server_utc_offset', lambda _mt5: timedelta(hours=2))
    frame = get_candles(mt5, 'EURUSD', 'M5', 1)

    assert frame.index[0] == pd.Timestamp('2026-11-05 19:00:00', tz='UTC')
    assert ('EURUSD', True) in mt5.selected


def test_closed_candles_retries_transient_mt5_failure(monkeypatch):
    import src.market_data as market_data

    broker_stamp = datetime(2026, 11, 5, 21, 0, tzinfo=timezone.utc).timestamp()
    rates = np.array([(broker_stamp,1.0,1.1,0.9,1.05,10,3)], dtype=[
        ('time','i8'),('open','f8'),('high','f8'),('low','f8'),('close','f8'),('tick_volume','i8'),('spread','i8')
    ])

    class TransientRatesMT5(FakeMT5):
        TIMEFRAME_M5 = 5
        def __init__(self):
            super().__init__(SimpleNamespace(time=int(broker_stamp), time_msc=int(broker_stamp*1000)))
            self.calls = 0
        def copy_rates_from_pos(self, symbol, timeframe, shift, count):
            self.calls += 1
            return None if self.calls == 1 else rates
        def last_error(self):
            return (-1, 'Terminal: Call failed')

    monkeypatch.setattr(market_data, 'server_utc_offset', lambda _mt5: timedelta(hours=2))
    mt5 = TransientRatesMT5()
    frame = market_data.get_closed_candles(mt5, 'EURUSD', 'M5', 1)

    assert mt5.calls == 2
    assert frame.index[0] == pd.Timestamp('2026-11-05 19:00:00', tz='UTC')

