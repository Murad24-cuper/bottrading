import pytest

from scripts.run_six_families_research_v4_ultralow import spread_cost_per_lot, evaluate_live_gates, _read_v3_rows


def test_ultralow_cost_uses_live_spread_times_tick_value_and_margin():
    # 2.4 pips = 24 ticks; $1 per tick per lot; 1.25 cost factor.
    assert spread_cost_per_lot(.00024,.00001,1.0)==pytest.approx(30.0)


def test_ultralow_cost_rejects_incomplete_live_symbol_spec():
    with pytest.raises(ValueError):
        spread_cost_per_lot(.00024,0,1.0)


def test_live_min_lot_and_strict_cost_gates_use_stop_value_and_budget():
    result=evaluate_live_gates(stop_distance=.001,tick_size=.00001,tick_value_loss=1,
        volume_min=.01,cost_per_lot=5,risk_budget=10)
    assert result=={'min_lot_risk':1.0,'cost_stop_ratio':.05,'min_lot_pass':True,'cost_pass':True,'both_pass':True}
    blocked=evaluate_live_gates(stop_distance=.0002,tick_size=.00001,tick_value_loss=1,
        volume_min=.01,cost_per_lot=5,risk_budget=10)
    assert not blocked['cost_pass']


def test_v3_report_parser_reads_variant_baselines(tmp_path):
    report=tmp_path/'v3.md'
    report.write_text('\n'.join([
        '| Family | Variant | N (Tr/Val) | Win% | EV Train | EV Val | PF | Max DD | WF Share | Random 95% | Buy-and-Hold | DSR | Status |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---|',
        '| Time-Series Momentum | v1 (H4 12-bar, sl 2.0, tp 3.0) | 100/50 | 45% | +0.12 | +0.05 | 1.2 | 4R | 60% | PASS | n/a | 0.2 | PASS |',
        '',
    ]),encoding='utf-8')
    rows=_read_v3_rows(report)
    assert rows[('Time-Series Momentum','v1 (H4 12-bar, sl 2.0, tp 3.0)')]==('100/50','+0.12','+0.05','1.2')
