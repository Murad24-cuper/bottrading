import sqlite3

from src.dashboard import queries
from src.db import Database


def test_pipeline_funnel_aggregates_stage_counts_and_reasons_since_cutoff(tmp_path):
    path = tmp_path / 'pipeline.db'
    db = Database(path)
    db.record_scan_funnel(
        time='2026-11-09T15:30:00+00:00', symbols_scanned=10,
        filters_passed=6, signals=2, passed_risk=1, orders=1,
        filter_rejections={'stale tick': 3},
        signal_rejections={'conditions_not_met': 4},
        risk_rejections={'cost too high': 1}, order_rejections={},
    )
    db.record_scan_funnel(
        time='2026-11-09T15:55:00+00:00', symbols_scanned=8,
        filters_passed=5, signals=3, passed_risk=0, orders=0,
        filter_rejections={'stale tick': 2, 'spread too high': 1},
        signal_rejections={'conditions_not_met': 6},
        risk_rejections={'normal entries disabled': 3},
        order_rejections={'broker rejected': 1},
    )
    db.record_scan_funnel(
        time='2026-11-09T14:00:00+00:00', symbols_scanned=100,
        filters_passed=80, signals=40, passed_risk=20, orders=15,
    )

    funnel = queries.get_pipeline_funnel('2026-11-09T15:00:00+00:00', path)

    assert funnel['available'] is True
    assert funnel['cycles'] == 2
    assert funnel['counts'] == {
        'symbols_scanned': 18, 'filters_passed': 11, 'signals': 5,
        'passed_risk': 1, 'orders': 1,
    }
    assert funnel['rejections']['filters'] == {'stale tick': 5, 'spread too high': 1}
    assert funnel['rejections']['signals'] == {'conditions_not_met': 10}
    assert funnel['rejections']['risk'] == {
        'cost too high': 1, 'normal entries disabled': 3,
    }
    assert funnel['rejections']['orders'] == {'broker rejected': 1}


def test_pipeline_funnel_reports_unavailable_before_bot_creates_table(tmp_path):
    path = tmp_path / 'empty.db'
    with sqlite3.connect(path):
        pass

    assert queries.get_pipeline_funnel('2026-11-09T15:00:00+00:00', path) == {
        'available': False, 'cycles': 0, 'counts': {}, 'rejections': {},
    }
