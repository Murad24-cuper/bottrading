from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
import pytest
from src.db import Database
from src.bot import TradingBot

def test_get_pnl_since_filters_by_magic(tmp_path):
    db = Database(tmp_path / "test.db")
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Trade 1: Bot trade (magic=999) with profit +50
    db.insert_trade(
        ticket=1001, symbol="EURUSD", asset_group="forex", direction="buy",
        volume=0.1, open_time=day_start.isoformat(), open_price=1.1000,
        sl=1.0900, tp=1.1200, profit=0, commission=0, swap=0,
        magic=999, status="open"
    )
    db.update_trade_close(1001, close_time=now.isoformat(), close_price=1.1050, profit=50.0, commission=-2.0, swap=0.0, close_reason="tp")

    # Trade 2: Manual / external trade (magic=0) with loss -300
    db.insert_trade(
        ticket=1002, symbol="EURUSD", asset_group="forex", direction="sell",
        volume=1.0, open_time=day_start.isoformat(), open_price=1.1000,
        sl=1.1200, tp=1.0800, profit=0, commission=0, swap=0,
        magic=0, status="open"
    )
    db.update_trade_close(1002, close_time=now.isoformat(), close_price=1.1030, profit=-300.0, commission=0.0, swap=0.0, close_reason="manual")

    # With magic=999 filter: should only see Trade 1 (+48 net: 50 - 2)
    pnl_bot = db.get_pnl_since(day_start, magic=999)
    assert pnl_bot == 48.0

    # Without magic filter (legacy / overall): sees both (48 - 300 = -252)
    pnl_all = db.get_pnl_since(day_start)
    assert pnl_all == -252.0

def test_bot_pnl_periods_uses_magic_number(tmp_path):
    db = Database(tmp_path / "test.db")
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Trade with foreign magic
    db.insert_trade(
        ticket=2001, symbol="EURUSD", asset_group="forex", direction="buy",
        volume=0.5, open_time=day_start.isoformat(), open_price=1.1000,
        sl=1.0900, tp=1.1200, profit=0, commission=0, swap=0,
        magic=12345, status="open"
    )
    db.update_trade_close(2001, close_time=now.isoformat(), close_price=1.0950, profit=-500.0, commission=0.0, swap=0.0, close_reason="sl")

    settings = SimpleNamespace(
        root=tmp_path,
        data_dir=tmp_path,
        magic_number=999,
        db_path=tmp_path / "test.db",
        config={"notify": {}, "live": {}}
    )
    bot = TradingBot(settings, db=db)
    pnl_day, pnl_week = bot._pnl_periods(now)
    # Foreign -500 trade must not contaminate bot's PnL
    assert pnl_day == 0.0
    assert pnl_week == 0.0
