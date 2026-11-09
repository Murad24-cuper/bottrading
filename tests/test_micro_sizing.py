"""Tests verifying position sizing on Micro accounts without standard-lot assumptions."""
from __future__ import annotations
import pytest
from src.risk import calc_volume, calc_volume_stressed
from src.symbols import underlying_key


def test_micro_eurusd_sizing_at_small_balance():
    """On XM Micro EURUSD, 1 lot = 1,000 units, tick_value = $0.01 per tick.
    With $50 balance and 0.5% risk ($0.25), a 50-pip stop should size cleanly to 0.05 lots."""
    micro_spec = {
        'trade_contract_size': 1000.0,
        'trade_tick_size': 0.00001,
        'trade_tick_value': 0.01,
        'trade_tick_value_loss': 0.01,
        'volume_min': 0.01,
        'volume_step': 0.01,
        'volume_max': 100.0,
    }
    # 50 pips stop = 0.0050 = 500 ticks.
    # Risk per 1 micro lot = 500 * $0.01 = $5.00.
    # Budget for $50 equity at 0.5% risk = $0.25.
    # Expected volume = 0.25 / 5.00 = 0.05 lot.
    vol, reason = calc_volume(50.0, 0.5, 1.1000, 1.0950, micro_spec)
    assert reason == 'ok'
    assert vol == 0.05


def test_micro_gold_sizing_at_minimum_risk():
    """On Micro Gold (1 lot = 1 oz), a $10 stop on a $1000 account at 0.1% risk ($1.00)
    sizes cleanly to 0.10 lots, unlike standard gold which exceeds the risk cap."""
    micro_gold_spec = {
        'trade_contract_size': 1.0,
        'trade_tick_size': 0.01,
        'trade_tick_value': 0.01,
        'trade_tick_value_loss': 0.01,
        'volume_min': 0.1,
        'volume_step': 0.01,
        'volume_max': 100.0,
    }
    # Stop distance $10 = 1000 ticks.
    # Risk per lot = 1000 * 0.01 = $10.00.
    # Allowed at 0.1% of $1000 = $1.00.
    # Volume = $1.00 / $10.00 = 0.10 lot.
    vol, reason = calc_volume(1000.0, 0.1, 2700.0, 2690.0, micro_gold_spec)
    assert reason == 'ok'
    assert vol == 0.1


def test_contract_size_fallback_when_tick_value_missing():
    """When broker returns 0 or missing tick_value, fallback derives tick_value = contract_size * tick_size."""
    spec_missing_tv = {
        'trade_contract_size': 1000.0,
        'trade_tick_size': 0.00001,
        'trade_tick_value': 0.0,
        'trade_tick_value_loss': 0.0,
        'volume_min': 0.01,
        'volume_step': 0.01,
        'volume_max': 100.0,
    }
    vol, reason = calc_volume(50.0, 1.0, 1.1000, 1.0950, spec_missing_tv)
    # Budget = $50 * 1.0% = $0.50.
    # Derived tick_value = 1000 * 0.00001 = $0.01.
    # Stop = 500 ticks * $0.01 = $5.00 / lot -> 0.10 lot.
    assert reason == 'ok'
    assert vol == 0.10


def test_underlying_key_strips_micro_suffix():
    """Verify underlying_key correctly cleans micro symbols for group exposure checks."""
    assert underlying_key('EURUSDmicro') == 'EURUSD'
    assert underlying_key('GOLDmicro') == 'GOLD'
    assert underlying_key('US500micro') == 'US500'
    assert underlying_key('GBPUSD.m') == 'GBPUSD'
