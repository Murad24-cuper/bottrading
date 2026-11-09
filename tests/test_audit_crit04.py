from types import SimpleNamespace
from datetime import datetime, timezone
import pytest
from src.executor import Executor
from src.models import Signal

class FakeDB:
    def __init__(self):
        self.trades = []
        self.events = []
    def log_event(self, level, source, message):
        self.events.append((level, source, message))
    def insert_trade(self, **kwargs):
        self.trades.append(kwargs)

def test_requote_recalculates_volume_to_stay_under_risk_cap(tmp_path):
    class FakeInfo:
        trade_mode = 4
        trade_stops_level = 0
        point = 0.01
        filling_mode = 1
        volume_min = 0.01
        volume_step = 0.01
        volume_max = 100.0
        trade_tick_size = 0.01
        trade_tick_value = 1.0
        trade_tick_value_loss = 1.0
        def _asdict(self):
            return {
                "trade_stops_level": 0, "point": 0.01, "filling_mode": 1,
                "volume_min": 0.01, "volume_step": 0.01, "volume_max": 100.0,
                "trade_tick_size": 0.01, "trade_tick_value": 1.0, "trade_tick_value_loss": 1.0
            }

    class FakeAccount:
        equity = 10000.0  # risk 0.25% = $25
        trade_mode = 0
        margin_mode = 2

    sent_requests = []

    class FakeMT5:
        TRADE_ACTION_DEAL = 1
        ORDER_TYPE_BUY = 0
        ORDER_TYPE_SELL = 1
        ORDER_TIME_GTC = 0
        ORDER_FILLING_IOC = 1
        ORDER_FILLING_FOK = 0
        TRADE_RETCODE_REQUOTE = 10004
        TRADE_RETCODE_DONE = 10009

        def __init__(self):
            self.call_count = 0

        def symbol_select(self, symbol, enable):
            return True

        def symbol_info(self, symbol):
            return FakeInfo()

        def account_info(self):
            return FakeAccount()

        def symbol_info_tick(self, symbol):
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            # First tick: ask = 100.00, sl = 99.00 -> distance = 1.00 -> per lot risk = $100 -> max volume = 0.25
            if self.call_count == 0:
                return SimpleNamespace(ask=100.00, bid=99.98, time_msc=now_ms)
            # Second tick (requote): ask jumps to 100.50 -> sl = 99.00 -> distance = 1.50 -> per lot risk = $150 -> max volume = 0.16
            return SimpleNamespace(ask=100.50, bid=100.48, time_msc=now_ms)

        def copy_rates_from_pos(self, symbol, tf, start, count):
            return [{"time": 1234567890}]

        def order_send(self, req):
            sent_requests.append(dict(req))
            self.call_count += 1
            if self.call_count == 1:
                # First attempt gets REQUOTE
                return SimpleNamespace(retcode=10004, comment="Requote", price=100.00)
            return SimpleNamespace(retcode=10009, comment="Done", price=100.50, position=123)

        def positions_get(self, **kwargs):
            return [SimpleNamespace(ticket=123, sl=99.0, magic=999)]

        def last_error(self):
            return (0, "ok")

    settings = SimpleNamespace(
        root=tmp_path,
        risk=SimpleNamespace(risk_per_trade_pct=0.25),
        magic_number=999,
        allow_real=False,
        config={
            "account": {"mode": "demo"},
            "executor": {"deviation_points": 10},
            "universe": {"tick_freshness_seconds_by_group": {"forex": 1000}}
        }
    )
    db = FakeDB()
    mt5 = FakeMT5()
    symbol_service = SimpleNamespace(
        is_tradable=lambda s: (True, "tradable"),
        get_asset_group=lambda s: "forex"
    )
    executor = Executor(mt5, settings, db, symbol_service=symbol_service)

    signal = Signal(
        symbol="EURUSD",
        direction="buy",
        strategy_name="test_strat",
        timeframe="M15",
        entry_hint=100.00,
        sl_price=99.00,
        tp_price=102.00,
        confidence=0.8,
        reason="test"
    )

    # Initial volume 0.25 fits 100.00 entry ($25 risk)
    res = executor.open_trade(signal, volume=0.25)
    assert res.success is True
    assert len(sent_requests) == 2
    # The first request had volume 0.25 at price 100.0
    assert sent_requests[0]["price"] == 100.00
    assert sent_requests[0]["volume"] == 0.25
    # The retry request on requote MUST have recalculated volume to stay within $25 risk!
    # At 100.50 with sl 99.00, distance is 1.50, max safe volume is 0.16
    assert sent_requests[1]["price"] == 100.50
    assert sent_requests[1]["volume"] <= 0.16

def test_requote_cancels_if_safe_volume_below_min_lot(tmp_path):
    class FakeInfo:
        trade_mode = 4
        trade_stops_level = 0
        point = 0.01
        filling_mode = 1
        volume_min = 0.10
        volume_step = 0.01
        volume_max = 100.0
        trade_tick_size = 0.01
        trade_tick_value = 1.0
        trade_tick_value_loss = 1.0
        def _asdict(self):
            return {
                "trade_stops_level": 0, "point": 0.01, "filling_mode": 1,
                "volume_min": 0.10, "volume_step": 0.01, "volume_max": 100.0,
                "trade_tick_size": 0.01, "trade_tick_value": 1.0, "trade_tick_value_loss": 1.0
            }

    class FakeAccount:
        equity = 10000.0  # risk 0.25% = $25
        trade_mode = 0
        margin_mode = 2

    sent_requests = []

    class FakeMT5:
        TRADE_ACTION_DEAL = 1
        ORDER_TYPE_BUY = 0
        ORDER_TYPE_SELL = 1
        ORDER_TIME_GTC = 0
        ORDER_FILLING_IOC = 1
        ORDER_FILLING_FOK = 0
        TRADE_RETCODE_REQUOTE = 10004
        TRADE_RETCODE_DONE = 10009

        def __init__(self):
            self.call_count = 0
        def symbol_select(self, symbol, enable): return True
        def symbol_info(self, symbol): return FakeInfo()
        def account_info(self): return FakeAccount()
        def symbol_info_tick(self, symbol):
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            if self.call_count == 0:
                return SimpleNamespace(ask=100.00, bid=99.98, time_msc=now_ms)
            # Requote jumps to 103.00 -> SL is 99.00 -> distance = 4.00 -> per lot risk = $400 -> safe volume = 0.06 < min_lot 0.10!
            return SimpleNamespace(ask=103.00, bid=102.98, time_msc=now_ms)
        def copy_rates_from_pos(self, symbol, tf, start, count): return [{"time": 1234567890}]
        def order_send(self, req):
            sent_requests.append(dict(req))
            self.call_count += 1
            return SimpleNamespace(retcode=10004, comment="Requote", price=100.00)
        def positions_get(self, **kwargs): return []
        def last_error(self): return (0, "ok")

    settings = SimpleNamespace(
        root=tmp_path,
        risk=SimpleNamespace(risk_per_trade_pct=0.25),
        magic_number=999,
        allow_real=False,
        config={
            "account": {"mode": "demo"},
            "executor": {"deviation_points": 10},
            "universe": {"tick_freshness_seconds_by_group": {"forex": 1000}}
        }
    )
    db = FakeDB()
    mt5 = FakeMT5()
    symbol_service = SimpleNamespace(is_tradable=lambda s: (True, "tradable"), get_asset_group=lambda s: "forex")
    executor = Executor(mt5, settings, db, symbol_service=symbol_service)

    signal = Signal(
        symbol="EURUSD", direction="buy", strategy_name="test_strat", timeframe="M15",
        entry_hint=100.00, sl_price=99.00, tp_price=105.00, confidence=0.8, reason="test"
    )

    res = executor.open_trade(signal, volume=0.20)
    # Must cancel the trade instead of sending an illegal or undersized / oversized order
    assert res.success is False
    assert "safe volume" in res.message or "minimum lot" in res.message or "min lot" in res.message
    assert len(sent_requests) == 1  # No second request sent!
