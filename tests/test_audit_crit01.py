from types import SimpleNamespace
from unittest.mock import Mock, patch
from src.executor import Executor
from src.bot import TradingBot

class FakeDB:
    def __init__(self):
        self.events = []
        self.open = []
    def log_event(self, level, source, message):
        self.events.append((level, source, message))
    def get_open_trades(self):
        return self.open
    def get_trade(self, ticket):
        return next((r for r in self.open if r.get('ticket') == ticket), None)
    def update_open_trade(self, ticket, **kw):
        return 1

class FakeMT5:
    POSITION_TYPE_BUY = 0
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    TRADE_ACTION_SLTP = 6
    TRADE_ACTION_DEAL = 1
    TRADE_RETCODE_DONE = 10009
    ORDER_TIME_GTC = 0
    ORDER_FILLING_FOK = 0
    SYMBOL_FILLING_FOK = 1
    SYMBOL_TRADE_MODE_FULL = 4

    def __init__(self):
        self.orders = []
        self.modify_fail_count = 0
        self.modify_attempts = 0
        self.pos = SimpleNamespace(
            ticket=101, identifier=101, magic=7, symbol='EURUSD', type=0,
            price_open=1.1000, sl=0.0, tp=1.1200, volume=0.1, profit=0.0, swap=0.0
        )
        self.info = SimpleNamespace(
            point=0.00001, trade_stops_level=10, trade_mode=4,
            trade_tick_size=0.0001, trade_tick_value=1.0, trade_tick_value_loss=1.0,
            volume_min=0.01, volume_step=0.01, volume_max=10.0, filling_mode=1
        )
        self.info._asdict = lambda: {'trade_tick_size': 0.0001, 'trade_tick_value': 1.0, 'trade_tick_value_loss': 1.0, 'volume_min': 0.01, 'volume_step': 0.01, 'volume_max': 10.0}
        self.tick = SimpleNamespace(bid=1.1020, ask=1.1022)

    def positions_get(self, *a, **k):
        return [self.pos] if self.pos else []

    def symbol_info(self, symbol):
        return self.info

    def symbol_info_tick(self, symbol):
        return self.tick

    def symbol_select(self, symbol, state):
        return True

    def last_error(self):
        return (0, 'ok')

    def order_send(self, **request):
        self.orders.append(request)
        if request.get('action') == self.TRADE_ACTION_SLTP:
            self.modify_attempts += 1
            if self.modify_attempts <= self.modify_fail_count:
                return SimpleNamespace(retcode=10013, comment='Invalid request')
            self.pos.sl = request.get('sl', 0)
            return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, comment='done', price=1.1020)
        elif request.get('action') == self.TRADE_ACTION_DEAL:
            # closing position
            self.pos = None
            return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, comment='done', price=1.1020)
        return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, comment='done', price=1.1020)

def test_remediate_missing_sl_sets_planned_sl_and_retries(tmp_path):
    settings = SimpleNamespace(
        root=tmp_path, magic_number=7,
        risk=SimpleNamespace(risk_per_trade_pct=0.25),
        allow_real=False,
        config={'account': {'mode': 'demo'}, 'executor': {'deviation_points': 20}}
    )
    mt5 = FakeMT5()
    db = FakeDB()
    executor = Executor(mt5, settings, db)

    # Make modify fail 2 times, then succeed on 3rd attempt
    mt5.modify_fail_count = 2
    success = executor.remediate_missing_sl(mt5.pos, planned_sl=1.0950)
    assert success is True
    assert mt5.modify_attempts == 3
    assert mt5.pos.sl == 1.0950
    assert any('Recovered' in msg or 'missing SL' in msg for _, _, msg in db.events)

def test_remediate_missing_sl_closes_at_market_if_all_retries_fail(tmp_path):
    settings = SimpleNamespace(
        root=tmp_path, magic_number=7,
        risk=SimpleNamespace(risk_per_trade_pct=0.25),
        allow_real=False,
        config={'account': {'mode': 'demo'}, 'executor': {'deviation_points': 20}}
    )
    mt5 = FakeMT5()
    db = FakeDB()
    executor = Executor(mt5, settings, db)

    # Fail all retries
    mt5.modify_fail_count = 99
    success = executor.remediate_missing_sl(mt5.pos, planned_sl=1.0950)
    assert success is False
    assert mt5.modify_attempts >= 3
    # Position must be closed at market (mt5.pos becomes None)
    assert mt5.pos is None
    assert any(lvl == 'CRITICAL' for lvl, _, _ in db.events)
