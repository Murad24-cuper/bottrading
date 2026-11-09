from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from collections import namedtuple
import pytest
import numpy as np
import pandas as pd
from src.market_data import (
    get_account_state,
    get_candles,
    get_closed_candles,
    get_candles_multi,
    get_tick,
    get_spread_points,
    price_distance_to_money,
    get_cost_estimate,
)

def test_get_account_state_success_and_failure():
    mock_mt5 = MagicMock()
    mock_acc = MagicMock()
    mock_acc.balance = 10000.0
    mock_acc.equity = 10500.0
    mock_acc.margin = 500.0
    mock_acc.margin_free = 10000.0
    mock_acc.margin_level = 2100.0
    mock_acc.currency = "USD"
    mock_acc.leverage = 100
    mock_acc.trade_mode = 0
    mock_acc.margin_mode = 2
    mock_mt5.account_info.return_value = mock_acc

    state = get_account_state(mock_mt5)
    assert state.balance == 10000.0
    assert state.equity == 10500.0

    mock_mt5.account_info.return_value = None
    mock_mt5.last_error.return_value = (1, "fail")
    with pytest.raises(RuntimeError, match="account_info failed"):
        get_account_state(mock_mt5)

def test_get_candles_branches():
    mock_mt5 = MagicMock()
    mock_mt5.symbol_select.return_value = False
    with pytest.raises(RuntimeError, match="symbol_select"):
        get_candles(mock_mt5, "EURUSD", "M1", 10)

    mock_mt5.symbol_select.return_value = True
    mock_mt5.TIMEFRAME_INVALID = None
    with pytest.raises(ValueError, match="Unsupported timeframe"):
        get_candles(mock_mt5, "EURUSD", "INVALID", 10)

    mock_mt5.TIMEFRAME_M1 = 1
    mock_mt5.copy_rates_from_pos.return_value = None
    with pytest.raises(RuntimeError, match="copy_rates_from_pos failed"):
        get_candles(mock_mt5, "EURUSD", "M1", 10)

    # Empty array
    mock_mt5.copy_rates_from_pos.return_value = np.array([])
    df_empty = get_candles(mock_mt5, "EURUSD", "M1", 10)
    assert df_empty.empty

    # Non-empty array
    rates = np.array([(1700000000, 1.1, 1.15, 1.05, 1.12, 100, 5, 0)],
                     dtype=[('time', 'i8'), ('open', 'f8'), ('high', 'f8'), ('low', 'f8'),
                            ('close', 'f8'), ('tick_volume', 'i8'), ('spread', 'i4'), ('real_volume', 'i8')])
    mock_mt5.copy_rates_from_pos.return_value = rates
    df = get_candles(mock_mt5, "EURUSD", "M1", 1)
    assert len(df) == 1
    assert 'open' in df.columns

def test_get_closed_candles_and_retry():
    mock_mt5 = MagicMock()
    mock_mt5.symbol_select.return_value = False
    with pytest.raises(RuntimeError, match="symbol_select"):
        get_closed_candles(mock_mt5, "EURUSD", "M1", 10)

    mock_mt5.symbol_select.return_value = True
    mock_mt5.TIMEFRAME_INVALID = None
    with pytest.raises(ValueError, match="Unsupported timeframe"):
        get_closed_candles(mock_mt5, "EURUSD", "INVALID", 10)

    mock_mt5.TIMEFRAME_M1 = 1
    # First call fails, second succeeds
    rates = np.array([(1700000000, 1.1, 1.15, 1.05, 1.12, 100, 5, 0)],
                     dtype=[('time', 'i8'), ('open', 'f8'), ('high', 'f8'), ('low', 'f8'),
                            ('close', 'f8'), ('tick_volume', 'i8'), ('spread', 'i4'), ('real_volume', 'i8')])
    mock_mt5.copy_rates_from_pos.side_effect = [None, rates]
    df = get_closed_candles(mock_mt5, "EURUSD", "M1", 1)
    assert len(df) == 1

    # Both fail
    mock_mt5.copy_rates_from_pos.side_effect = [None, None]
    with pytest.raises(RuntimeError, match="copy_rates_from_pos closed bars failed"):
        get_closed_candles(mock_mt5, "EURUSD", "M1", 1)

    # Empty
    mock_mt5.copy_rates_from_pos.side_effect = None
    mock_mt5.copy_rates_from_pos.return_value = np.array([])
    df_empty = get_closed_candles(mock_mt5, "EURUSD", "M1", 1)
    assert df_empty.empty

def test_get_candles_multi():
    mock_mt5 = MagicMock()
    mock_mt5.symbol_select.return_value = True
    mock_mt5.TIMEFRAME_M1 = 1
    mock_mt5.TIMEFRAME_M5 = 5
    mock_mt5.copy_rates_from_pos.return_value = np.array([])
    res = get_candles_multi(mock_mt5, "EURUSD", ["M1", "M5"], 10)
    assert "M1" in res and "M5" in res

def test_get_tick_branches():
    mock_mt5 = MagicMock()
    mock_mt5.symbol_select.return_value = False
    with pytest.raises(RuntimeError, match="symbol_select"):
        get_tick(mock_mt5, "EURUSD")

    mock_mt5.symbol_select.return_value = True
    mock_mt5.symbol_info_tick.return_value = None
    with pytest.raises(RuntimeError, match="symbol_info_tick failed"):
        get_tick(mock_mt5, "EURUSD")

    Tick = namedtuple("Tick", ["time", "time_msc", "ask", "bid"])
    tick_obj = Tick(1700000000, 1700000000000, 1.1005, 1.1000)
    mock_mt5.symbol_info_tick.return_value = tick_obj
    t = get_tick(mock_mt5, "EURUSD")
    assert t.ask == 1.1005

def test_get_spread_points():
    mock_mt5 = MagicMock()
    mock_mt5.symbol_select.return_value = True
    Tick = namedtuple("Tick", ["ask", "bid"])
    mock_mt5.symbol_info_tick.return_value = Tick(1.10020, 1.10000)
    
    mock_info = MagicMock()
    mock_info.point = 0.00001
    mock_mt5.symbol_info.return_value = mock_info
    
    pts = get_spread_points(mock_mt5, "EURUSD")
    assert pytest.approx(pts, 0.01) == 20.0

    mock_info.point = 0
    with pytest.raises(RuntimeError, match="symbol_info"):
        get_spread_points(mock_mt5, "EURUSD")

def test_price_distance_to_money():
    mock_mt5 = MagicMock()
    mock_info = MagicMock()
    mock_info.trade_tick_size = 0.00001
    mock_info.trade_tick_value = 1.0
    mock_mt5.symbol_info.return_value = mock_info

    val = price_distance_to_money(mock_mt5, "EURUSD", 0.00100, 1.0)
    assert pytest.approx(val) == 100.0

    mock_info.trade_tick_size = 0
    with pytest.raises(ValueError, match="Invalid tick value/size"):
        price_distance_to_money(mock_mt5, "EURUSD", 0.00100, 1.0)

    mock_mt5.symbol_info.return_value = None
    with pytest.raises(RuntimeError, match="symbol_info"):
        price_distance_to_money(mock_mt5, "EURUSD", 0.00100, 1.0)

def test_get_cost_estimate_all_sources():
    mock_mt5 = MagicMock()
    mock_mt5.symbol_select.return_value = True
    Tick = namedtuple("Tick", ["ask", "bid"])
    mock_mt5.symbol_info_tick.return_value = Tick(1.1002, 1.1000)
    
    mock_info = MagicMock()
    mock_info.trade_tick_size = 0.00001
    mock_info.trade_tick_value = 1.0
    mock_info.trade_commission = 3.5
    mock_mt5.symbol_info.return_value = mock_info

    # Case 1: deals history has commission
    Deal = namedtuple("Deal", ["symbol", "volume", "commission"])
    mock_mt5.history_deals_get.return_value = [
        Deal("EURUSD", 1.0, -3.0),
        Deal("EURUSD", 2.0, -6.0),
    ]
    est1 = get_cost_estimate(mock_mt5, "EURUSD", 1.0)
    assert not est1["commission_estimated"]
    assert pytest.approx(est1["commission"]) == 6.0 # 2 * 3.0 round trip

    # Case 2: deals history empty -> falls back to info.trade_commission
    mock_mt5.history_deals_get.return_value = []
    est2 = get_cost_estimate(mock_mt5, "EURUSD", 1.0)
    assert not est2["commission_estimated"]
    assert pytest.approx(est2["commission"]) == 7.0 # 2 * 3.5

    # Case 3: info has no commission -> defaults to 0.0 estimated
    mock_info.trade_commission = None
    mock_info.commission = None
    est3 = get_cost_estimate(mock_mt5, "EURUSD", 1.0)
    assert est3["commission_estimated"]
    assert est3["commission"] == 0.0

    # Case 4: info is None -> raises RuntimeError
    mock_mt5.symbol_info.return_value = None
    with pytest.raises(RuntimeError, match="symbol_info"):
        get_cost_estimate(mock_mt5, "EURUSD", 1.0)
