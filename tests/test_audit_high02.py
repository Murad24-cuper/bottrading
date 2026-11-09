from types import SimpleNamespace
from datetime import datetime, timezone
import pytest
from src.bot import TradingBot
from src.scanner import Candidate
from src.models import Signal

def test_trailed_stop_in_profit_does_not_count_as_open_risk(tmp_path):
    class FakeInfo:
        trade_mode = 4
        point = 0.01
        trade_tick_size = 0.01
        trade_tick_value = 1.0
        trade_tick_value_loss = 1.0
        volume_min = 0.01
        volume_step = 0.01
        volume_max = 100.0
        currency_base = "EUR"
        currency_profit = "USD"
        def _asdict(self):
            return {
                "trade_mode": 4, "point": 0.01, "trade_tick_size": 0.01,
                "trade_tick_value": 1.0, "trade_tick_value_loss": 1.0,
                "volume_min": 0.01, "volume_step": 0.01, "volume_max": 100.0,
                "currency_base": "EUR", "currency_profit": "USD"
            }

    class FakeAccount:
        equity = 10000.0
        balance = 10000.0
        margin = 100.0
        margin_free = 9900.0
        margin_level = 10000.0
        trade_mode = 0
        margin_mode = 2
        currency = "USD"
        leverage = 100

    class FakePosition:
        def __init__(self, ticket, symbol, p_type, price_open, sl, volume, magic=999):
            self.ticket = ticket
            self.identifier = ticket
            self.symbol = symbol
            self.type = p_type  # 0 = BUY, 1 = SELL
            self.price_open = price_open
            self.sl = sl
            self.volume = volume
            self.magic = magic
            self.profit = 50.0
            self.swap = 0.0
            self.price_current = price_open + 10.0

    class FakeMT5:
        POSITION_TYPE_BUY = 0
        POSITION_TYPE_SELL = 1
        ORDER_TYPE_BUY = 0
        ORDER_TYPE_SELL = 1
        ACCOUNT_TRADE_MODE_DEMO = 0
        ACCOUNT_MARGIN_MODE_RETAIL_HEDGING = 2

        def __init__(self):
            # A BUY position with price_open=100.0, but stop trailed into profit at 105.0!
            # Risk is $0 (locked profit of $500).
            self.pos = [
                FakePosition(101, "EURUSD", 0, price_open=100.0, sl=105.0, volume=1.0)
            ]
        def symbol_info(self, symbol): return FakeInfo()
        def account_info(self): return FakeAccount()
        def symbol_info_tick(self, symbol):
            return SimpleNamespace(ask=100.00, bid=99.98, time_msc=int(datetime.now(timezone.utc).timestamp()*1000))
        def positions_get(self, **kwargs): return self.pos
        def order_calc_margin(self, *a, **k): return 100.0
        def last_error(self): return (0, "ok")

    settings = SimpleNamespace(
        root=tmp_path,
        data_dir=tmp_path,
        risk=SimpleNamespace(
            risk_per_trade_pct=0.25,
            max_open_positions=10,
            max_positions_per_group=5,
            max_positions_per_currency=5,
            max_positions_per_underlying_group=5,
            max_total_open_risk_pct=0.25,  # Cap at $25!
            max_margin_usage_pct=50.0,
            daily_loss_limit_pct=3.0,
            weekly_loss_limit_pct=8.0,
            symbol_cooldown_minutes=60,
            no_entry_before_close_minutes=15,
            max_spread_points={},
        ),
        magic_number=999,
        allow_real=False,
        config={
            "account": {"mode": "demo"},
            "executor": {"deviation_points": 10},
            "risk": {
                "risk_per_trade_pct": 0.25,
                "max_open_positions": 10,
                "max_positions_per_group": 5,
                "max_positions_per_currency": 5,
                "max_positions_per_underlying_group": 5,
                "max_total_open_risk_pct": 0.25,  # Cap at 0.25% ($25)
                "max_margin_usage_pct": 50.0,
                "daily_loss_limit_pct": 3.0,
                "weekly_loss_limit_pct": 8.0,
                "min_risk_reward": 1.2,
                "max_cost_to_target_ratio": 0.30,
                "max_trades_per_symbol_per_day": 10,
            },
            "demo_exploration": {"enabled": False},
            "weekend": {"enabled": False},
            "protections": {"enabled": False},
            "live": {"mode": "trade", "strategies": ["test_strat"], "max_cycle_errors": 3},
        }
    )

    class FakeDB:
        def __init__(self):
            self.last_skip_reason = None
        def get_open_trades(self): return []
        def count_underlying_trades_since(self, *a): return 0
        def count_trades_since(self, *a, **k): return 0
        def underlying_closed_since(self, *a): return False
        def get_pnl_since(self, *a, **k): return 0.0
        def log_event(self, *a): pass
        def insert_signal(self, **kwargs):
            self.last_skip_reason = kwargs.get("skip_reason")

    bot = TradingBot(settings, db=FakeDB())
    bot.client = SimpleNamespace(mt5=FakeMT5())
    bot.executor = SimpleNamespace(open_trade=lambda *a, **k: SimpleNamespace(success=True))
    bot._last_account_type = "DEMO"
    bot._trade_allowed = True

    signal = Signal(
        symbol="GBPUSD", direction="buy", strategy_name="test_strat", timeframe="M15",
        entry_hint=1.2500, sl_price=1.2480, tp_price=1.3000, confidence=0.8, reason="test"
    )
    candidate = Candidate(
        symbol="GBPUSD", asset_group="forex", strategy="test_strat", signal=signal,
        confidence=0.8, volume=0.1, risk_money=20.0, reward_money=100.0,
        cost={"cost": 1.0}, score=10.0, features={}, symbol_spec=FakeInfo()._asdict(), skip_reason=""
    )

    # State equity = $10,000. Risk limit = 0.25% ($25).
    # New trade risk = $20.
    # Existing trade has price_open=100, sl=105 (BUY).
    # If buggy abs(100 - 105) is used: open risk = $500, total = $520 > $25 -> rejected!
    # If correct direction-aware risk is used: open risk = $0, total = $20 <= $25 -> accepted!
    now = datetime.now(timezone.utc)
    accepted = bot._candidate(candidate, now, allow_entries=True)
    assert accepted is True, f"Candidate was wrongly rejected: {bot.db.last_skip_reason}"
