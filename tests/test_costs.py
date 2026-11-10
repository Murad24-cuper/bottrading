import pandas as pd
import pytest

from src.costs import estimate_round_trip_cost,evaluate_live_cost_gate,hourly_cost_cells


def test_shared_cost_estimate_converts_ticks_commission_and_unknown_flag():
    cost=estimate_round_trip_cost(spread_price=.0002,stop_distance=.002,tick_size=.0001,
        tick_value=1,volume=.1,commission_per_lot_round_trip=7,slippage_points=1,point_size=.00001)
    assert cost['commission_known'] is True
    assert cost['commission']==pytest.approx(.7)
    assert cost['cost']==pytest.approx(.00022/.0001*.1+.7)
    assert cost['cost_stop_ratio']==pytest.approx(cost['cost']/2)
    unknown=estimate_round_trip_cost(spread_price=.1,stop_distance=1,tick_size=.1,
        tick_value=1,volume=1,commission_per_lot_round_trip=None)
    assert not unknown['commission_known']


def test_hourly_cost_map_requires_known_commission_to_pass():
    index=pd.date_range('2026-01-01',periods=40,freq='h',tz='UTC')
    frame=pd.DataFrame({'open':100.,'high':101.,'low':99.,'close':100.,'spread':1.},index=index)
    spec={'point_size':.01,'trade_tick_size':.01,'trade_tick_value':1.,'stop_mult':2.}
    incomplete=hourly_cost_cells({('X','H1'):frame},{'X':spec})
    assert incomplete and all(not row['commission_known'] and not row['passes_10pct'] for row in incomplete)
    known=hourly_cost_cells({('X','H1'):frame},{'X':spec},{'X':1.})
    assert all(row['commission_known'] for row in known)


def test_new_account_zero_samples_uses_live_symbol_info_cost_fallback():
    result,reason=evaluate_live_cost_gate(samples=0,min_samples=5,
        median_spread_price=None,symbol_info_spread_points=13,point_size=.001,
        fallback_spread_multiplier=1.25,stop_distance=.754,tick_size=.001,
        tick_value=.92,volume=.01,commission_per_lot_round_trip=7,
        slippage_points=1,max_stop_ratio=.10)

    assert reason==''
    assert result['spread_source']=='symbol_info_fallback'
    assert result['spread_price']==pytest.approx(.01625)
    assert result['commission']==pytest.approx(.07)
    assert result['cost']>result['spread_slippage']
    assert result['cost_stop_ratio']<.10
