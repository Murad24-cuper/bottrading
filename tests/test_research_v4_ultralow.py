import pytest

from scripts.run_six_families_research_v4_ultralow import (
    spread_cost_per_lot,evaluate_live_gates,_read_v3_rows,read_live_spread_snapshot,
)


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


def test_spread_snapshot_uses_enabled_suffix_and_30_minute_london_ny_median(tmp_path):
    import json,sqlite3
    from datetime import datetime,timezone,timedelta
    db=tmp_path/'bot.db'; specs_path=tmp_path/'symbol_specs.json'
    names=['EURUSD#','GBPUSD#','USDJPY#','AUDUSD#','USDCAD#','EURJPY#','GBPJPY#','GOLD#']
    specs={}
    with sqlite3.connect(db) as c:
        c.executescript('''
            create table account_context(account_id text,updated_at text);
            create table bot_status(account_type text,mt5_connected integer,trade_allowed integer);
            create table equity_snapshots(time text,balance real,equity real);
            create table spread_samples(time text,symbol text,timeframe text,hour_utc integer,spread_price real);
        ''')
        c.execute("insert into account_context values('108765323','2026-11-10T14:31:00+00:00')")
        c.execute("insert into bot_status values('DEMO',1,1)")
        c.execute("insert into equity_snapshots values('2026-11-10T14:31:00+00:00',10000,10000)")
        start=datetime(2026,11,10,14,0,tzinfo=timezone.utc)
        for symbol in names:
            point=.01 if symbol=='GOLD#' else .001 if symbol.endswith('JPY#') else .00001
            specs[symbol]={'digits':2 if symbol=='GOLD#' else 3 if symbol.endswith('JPY#') else 5,
                'point':point,'trade_contract_size':100 if symbol=='GOLD#' else 100000,
                'trade_tick_size':point,'trade_tick_value_loss':1.0,'volume_min':.01,'volume_step':.01}
            for minute in range(31):
                stamp=start+timedelta(minutes=minute)
                spread=point*(10+(minute%3))
                c.execute('insert into spread_samples values(?,?,?,?,?)',
                    (stamp.isoformat(),symbol,'M1',stamp.hour,spread))
    specs_path.write_text(json.dumps(specs),encoding='utf-8')

    live,costs,live_specs,account=read_live_spread_snapshot(
        db,specs_path,now=datetime(2026,11,10,14,31,tzinfo=timezone.utc))

    assert {row['symbol'] for row in live}==set(names)
    assert all(row['sample_count']==31 for row in live)
    assert all(row['sample_end']>row['sample_start'] for row in live)
    assert live[0]['spread_min_price']<live[0]['spread_price']<live[0]['spread_max_price']
    assert account['login_suffix']=='323' and account['balance']==10000
    expected={'EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','EURJPY','GBPJPY','GOLD'}
    assert set(costs)==set(live_specs)==expected
