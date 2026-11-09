from types import SimpleNamespace
from datetime import datetime, timezone
import pytest
from src.market_data import get_cost_estimate

def test_fresh_account_zero_commission_passes_cost_gate():
    class FakeMT5:
        def symbol_select(self, symbol, enable):
            return True
        def symbol_info(self, symbol):
            return SimpleNamespace(
                trade_tick_size=0.01,
                trade_tick_value=1.0,
                trade_tick_value_loss=1.0,
                point=0.01,
                point_size=0.01,
            )
        def symbol_info_tick(self, symbol):
            return SimpleNamespace(ask=100.05, bid=100.00)
        def history_deals_get(self, date_from, date_to):
            # Fresh account: zero deals in history
            return []
        def last_error(self):
            return (0, "ok")

    mt5 = FakeMT5()
    cost = get_cost_estimate(mt5, "EURUSD", volume=0.1)

    # Must not be unknown or block
    assert cost["commission_known"] is True
    assert cost.get("commission_estimated") is True
    assert cost["commission"] == 0.0
    assert cost["cost"] > 0  # spread cost is positive

def test_zero_commission_in_deal_history_is_recognized():
    class FakeMT5:
        def symbol_select(self, symbol, enable):
            return True
        def symbol_info(self, symbol):
            return SimpleNamespace(
                trade_tick_size=0.01,
                trade_tick_value=1.0,
                trade_tick_value_loss=1.0,
                point=0.01,
                point_size=0.01,
            )
        def symbol_info_tick(self, symbol):
            return SimpleNamespace(ask=100.05, bid=100.00)
        def history_deals_get(self, date_from, date_to):
            # Account with deals that have 0.0 commission (standard zero-commission broker)
            return [
                SimpleNamespace(symbol="EURUSD", volume=0.5, commission=0.0),
                SimpleNamespace(symbol="EURUSD", volume=1.0, commission=0.0),
            ]
        def last_error(self):
            return (0, "ok")

    mt5 = FakeMT5()
    cost = get_cost_estimate(mt5, "EURUSD", volume=0.1)

    assert cost["commission_known"] is True
    assert cost["commission"] == 0.0
    assert cost.get("commission_estimated") is False  # observed from actual deals

def test_scanner_passes_cost_gate_on_fresh_account():
    from src.costs import estimate_round_trip_cost
    cost = {"cost": 5.0, "spread_cost": 5.0, "commission": 0.0, "commission_known": True, "commission_estimated": True}
    cell = {"samples": 10, "median_spread_price": 0.05}
    cost_cfg = {"enabled": True, "min_samples_per_cell": 5, "max_stop_ratio": 0.10, "slippage_points": 0.0}
    
    cost_gate_reason = ""
    if int(cell["samples"]) < int(cost_cfg.get("min_samples_per_cell", 5)):
        cost_gate_reason = "cost map cell not calibrated"
    elif not cost.get("commission_known", False):
        cost_gate_reason = "cost map commission unknown"
    else:
        mapped = estimate_round_trip_cost(
            spread_price=float(cell["median_spread_price"]),
            stop_distance=1.0,
            tick_size=0.01,
            tick_value=1.0,
            volume=0.1,
            commission_per_lot_round_trip=float(cost.get("commission", 0)) / 0.1,
            slippage_points=0.0,
            point_size=0.01,
        )
        if mapped["cost_stop_ratio"] >= float(cost_cfg.get("max_stop_ratio", 0.1)):
            cost_gate_reason = "median hourly costs exceed 10% of stop risk"

    assert cost_gate_reason == ""
