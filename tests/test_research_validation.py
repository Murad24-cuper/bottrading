"""Tests for research validation toolkit: random benchmark, walk-forward, deflated Sharpe."""
import pytest
from src.research.validation import random_entry_benchmark, walk_forward_share, deflated_sharpe_ratio

def test_random_entry_benchmark():
    trades = [{'net_r': 1.5, 'cost_r': 0.05} for _ in range(50)] + [{'net_r': -1.0, 'cost_r': 0.05} for _ in range(50)]
    res = random_entry_benchmark(trades, n_reps=50)
    assert 'mean_r' in res
    assert 'p95_r' in res
    assert isinstance(res['beats_p95'], bool)

def test_walk_forward_share():
    # 60 trades across 6 windows
    trades = [{'entry_time': f'2026-08-{i:02d}T00:00:00Z', 'net_r': 0.5} for i in range(1, 31)] + \
             [{'entry_time': f'2026-09-{i:02d}T00:00:00Z', 'net_r': -0.2} for i in range(1, 31)]
    res = walk_forward_share(trades, n_windows=6)
    assert res['total_windows'] == 6
    assert 0.0 <= res['share'] <= 1.0

def test_deflated_sharpe_ratio():
    # Positive edge trades
    trades = [{'net_r': 1.0} for _ in range(70)] + [{'net_r': -0.8} for _ in range(30)]
    res = deflated_sharpe_ratio(trades, n_trials=18)
    assert 'sharpe' in res
    assert 'dsr' in res
    assert res['sharpe'] > 0
