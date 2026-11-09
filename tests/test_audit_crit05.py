from types import SimpleNamespace
from datetime import datetime, timezone
import pytest
from src.executor import Executor
from src.models import Signal

class FakeDB:
    def __init__(self):
        self.trades = []
        self.events = []
        self.partial_closes = []
        self.closed_trades = {}
    def log_event(self, level, source, message):
        self.events.append((level, source, message))
    def insert_trade(self, **kwargs):
        self.trades.append(kwargs)
    def get_open_trades(self):
        return [t for t in self.trades if t.get("ticket") not in self.closed_trades]
    def get_trade(self, ticket):
        for t in self.trades:
            if t.get("ticket") == ticket:
                res = dict(t)
                if ticket in self.closed_trades:
                    res.update(self.closed_trades[ticket])
                return res
        return None
    def get_partial_deal_tickets(self, ticket):
        return set()
    def get_partial_closes(self, ticket):
        return []
    def update_trade_close(self, ticket, **kwargs):
        self.closed_trades[ticket] = kwargs
    def update_trade_features(self, ticket, features):
        pass

def test_partial_fill_stores_actual_filled_volume(tmp_path):
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
        equity = 100000.0
        trade_mode = 0
        margin_mode = 2

    class FakeMT5:
        TRADE_ACTION_DEAL = 1
        ORDER_TYPE_BUY = 0
        ORDER_TYPE_SELL = 1
        ORDER_TIME_GTC = 0
        ORDER_FILLING_IOC = 1
        ORDER_FILLING_FOK = 0
        TRADE_RETCODE_DONE = 10009

        def symbol_select(self, symbol, enable): return True
        def symbol_info(self, symbol): return FakeInfo()
        def account_info(self): return FakeAccount()
        def symbol_info_tick(self, symbol):
            return SimpleNamespace(ask=100.00, bid=99.98, time_msc=int(datetime.now(timezone.utc).timestamp()*1000))
        def copy_rates_from_pos(self, symbol, tf, start, count): return [{"time": 1234567890}]
        def order_send(self, req):
            # Broker partial fill: requested 1.0, but filled 0.4
            return SimpleNamespace(retcode=10009, comment="Done", price=100.00, position=555, volume=0.4)
        def positions_get(self, **kwargs):
            return [SimpleNamespace(ticket=555, sl=99.0, volume=0.4, magic=999)]
        def last_error(self): return (0, "ok")

    settings = SimpleNamespace(
        root=tmp_path,
        risk=SimpleNamespace(risk_per_trade_pct=0.25),
        magic_number=999,
        allow_real=False,
        config={"account": {"mode": "demo"}, "executor": {"deviation_points": 10}}
    )
    db = FakeDB()
    mt5 = FakeMT5()
    symbol_service = SimpleNamespace(is_tradable=lambda s: (True, "tradable"), get_asset_group=lambda s: "forex")
    executor = Executor(mt5, settings, db, symbol_service=symbol_service)

    signal = Signal(
        symbol="EURUSD", direction="buy", strategy_name="test_strat", timeframe="M15",
        entry_hint=100.00, sl_price=99.00, tp_price=105.00, confidence=0.8, reason="test"
    )

    res = executor.open_trade(signal, volume=1.0)
    assert res.success is True
    # The returned TradeResult and DB trade row MUST reflect the actual filled volume (0.4), NOT requested (1.0)
    assert res.volume == 0.4
    trade_row = db.trades[-1]
    assert trade_row["volume"] == 0.4
    assert trade_row["initial_volume"] == 0.4

def test_sync_positions_closes_stale_db_records_when_mt5_has_no_position(tmp_path):
    class FakeMT5:
        def positions_get(self, **kwargs):
            # MT5 has no open positions
            return []
        def history_deals_get(self, **kwargs):
            # No deals available in broker history
            return []
        def last_error(self): return (0, "ok")

    settings = SimpleNamespace(
        root=tmp_path,
        risk=SimpleNamespace(risk_per_trade_pct=0.25),
        magic_number=999,
        allow_real=False,
        config={"account": {"mode": "demo"}, "executor": {"deviation_points": 10}}
    )
    db = FakeDB()
    # Insert an open trade in DB that is no longer on MT5
    db.insert_trade(
        ticket=777, symbol="EURUSD", asset_group="forex", direction="buy",
        volume=0.5, initial_volume=0.5, open_time="2026-11-09T10:00:00Z",
        open_price=100.0, sl=99.0, tp=105.0, profit=0, commission=0, swap=0,
        magic=999, status="open"
    )

    mt5 = FakeMT5()
    executor = Executor(mt5, settings, db)

    reconciled = executor.sync_positions()
    assert 777 in reconciled
    assert 777 in db.closed_trades
