import numpy as np
import pandas as pd

from scripts.run_six_families_research_v3 import simulate_trades


def test_research_purges_trades_crossing_split_boundaries_and_skips_holdout():
    index = pd.to_datetime([
        '2025-12-29T00:00:00Z', '2025-12-30T00:00:00Z', '2025-12-31T00:00:00Z',
        '2026-01-01T00:00:00Z', '2026-01-02T00:00:00Z', '2026-01-03T00:00:00Z',
        '2026-09-28T00:00:00Z', '2026-09-29T00:00:00Z', '2026-09-30T00:00:00Z',
        '2026-10-20T00:00:00Z', '2026-10-21T00:00:00Z',
    ])
    frame = pd.DataFrame({
        'open': np.full(len(index), 100.0),
        'high': np.full(len(index), 100.5),
        'low': np.full(len(index), 99.5),
        'close': np.full(len(index), 100.0),
    }, index=index)
    signals = pd.Series(False, index=index)
    signals.iloc[[1, 3, 7, 9]] = True
    stop = pd.Series(1.0, index=index)
    target = pd.Series(2.0, index=index)

    trades = simulate_trades(
        frame, signals, stop, target, 'buy', max_hold_bars=2,
        symbol='EURUSD',
        cost_info={'point': 1.0, 'tick_size': 1.0, 'tick_value': 1.0, 'cost_per_lot': 0.0},
        is_h4_d1=False,
    )

    assert len(trades) == 1
    assert trades[0]['split'] == 'val'
    assert trades[0]['entry_time'].startswith('2026-01-02')
