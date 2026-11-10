"""Re-run the unchanged v3 18-variant protocol on live Ultra Low DEMO costs.

The market-data windows, variant parameters, trade simulator, splits, protected
holdout, and qualification tests come from run_six_families_research_v3.py.
Only the symbol universe and live-spread cost inputs are replaced here.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys
import json
import sqlite3
import statistics
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_settings
from src.symbols import underlying_key
from src.parquet_compat import read_parquet
from scripts import run_six_families_research_v3 as engine

FOREX_SYMBOLS = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'EURJPY', 'GBPJPY']
FOCUS_SYMBOLS = [*FOREX_SYMBOLS, 'GOLD']
SPREAD_MULTIPLIER = 1.25
VARIANT_STOPS=[
    ('Session Breakout','v1 M15','M15',1.5),('Session Breakout','v2 M15','M15',1.0),('Session Breakout','v3 H1','H1',1.5),
    ('Index Opening Range Breakout','v1 M15','M15',1.0),('Index Opening Range Breakout','v2 M15','M15',1.0),('Index Opening Range Breakout','v3 H1','H1',1.2),
    ('VWAP Reversion','v1 M15','M15',1.5),('VWAP Reversion','v2 M15','M15',1.0),('VWAP Reversion','v3 H1','H1',1.5),
    ('Donchian Breakout','v1 H4','H4',2.0),('Donchian Breakout','v2 H4','H4',2.5),('Donchian Breakout','v3 D1','D1',2.0),
    ('Time-Series Momentum','v1 H4','H4',2.0),('Time-Series Momentum','v2 H4','H4',2.5),('Time-Series Momentum','v3 D1','D1',2.5),
    ('Index Pullback in 200-Day Uptrend','v1 D1','D1',1.5),('Index Pullback in 200-Day Uptrend','v2 D1','D1',2.0),('Index Pullback in 200-Day Uptrend','v3 H4','H4',1.5),
]


def spread_cost_per_lot(spread_price: float, tick_size: float,
                        tick_value_loss: float, multiplier: float = SPREAD_MULTIPLIER) -> float:
    """Convert the live quote spread into conservative round-trip USD/lot cost."""
    values=(float(spread_price),float(tick_size),float(tick_value_loss),float(multiplier))
    if any(value<0 for value in values) or values[1]<=0 or values[2]<=0 or values[3]<=0:
        raise ValueError('spread, tick size/value, and multiplier must be valid')
    return values[0]/values[1]*values[2]*values[3]


def evaluate_live_gates(stop_distance: float, volume_min: float, tick_size: float,
                        tick_value_loss: float, cost_per_lot: float,
                        risk_budget: float, cost_ratio_limit: float=.10) -> dict:
    """Return the two independent exploration gates for a typical family stop."""
    stop_distance=float(stop_distance); volume_min=float(volume_min)
    tick_size=float(tick_size); tick_value_loss=float(tick_value_loss)
    cost_per_lot=float(cost_per_lot); risk_budget=float(risk_budget)
    if stop_distance<=0 or volume_min<=0 or tick_size<=0 or tick_value_loss<=0 or cost_per_lot<0 or risk_budget<=0:
        raise ValueError('stop/spec/cost/budget inputs must be valid')
    stop_risk=stop_distance/tick_size*tick_value_loss*volume_min
    stop_value_per_lot=stop_distance/tick_size*tick_value_loss
    ratio=cost_per_lot/stop_value_per_lot
    return {'min_lot_risk':stop_risk,'cost_stop_ratio':ratio,
        'min_lot_pass':stop_risk<=risk_budget+1e-12,'cost_pass':ratio<cost_ratio_limit,
        'both_pass':stop_risk<=risk_budget+1e-12 and ratio<cost_ratio_limit}


def _london_ny_overlap(stamp: datetime) -> bool:
    """True during the joint 08:00–17:00 London/New York weekday session."""
    stamp=stamp.astimezone(timezone.utc)
    if stamp.weekday()>=5: return False
    london=stamp.astimezone(ZoneInfo('Europe/London'))
    new_york=stamp.astimezone(ZoneInfo('America/New_York'))
    return 8<=london.hour<17 and 8<=new_york.hour<17


def read_live_spread_snapshot(db_path: Path, specs_path: Path, *, now=None) -> tuple[list[dict],dict,dict,dict]:
    """Build the v4 quote snapshot from the bot-owned DEMO sampling database."""
    now=now or datetime.now(timezone.utc)
    now=now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    start=now-timedelta(hours=1)
    specs=json.loads(Path(specs_path).read_text(encoding='utf-8'))
    with sqlite3.connect(db_path) as connection:
        connection.row_factory=sqlite3.Row
        account=connection.execute('SELECT account_id FROM account_context ORDER BY updated_at DESC LIMIT 1').fetchone()
        status=connection.execute('SELECT account_type,mt5_connected,trade_allowed FROM bot_status LIMIT 1').fetchone()
        equity=connection.execute('SELECT balance,equity FROM equity_snapshots ORDER BY time DESC LIMIT 1').fetchone()
        rows=connection.execute(
            'SELECT symbol,time,spread_price FROM spread_samples WHERE timeframe=? AND time>=? AND time<=? ORDER BY time',
            ('M1',start.isoformat(),now.isoformat())).fetchall()
    if not account or not status or status['account_type']!='DEMO' or not status['mt5_connected']:
        raise RuntimeError('Cost snapshot requires the bot-owned connected DEMO account')
    if not equity: raise RuntimeError('No live DEMO equity snapshot is available')
    samples_by_symbol={}
    for row in rows:
        stamp=datetime.fromisoformat(str(row['time']).replace('Z','+00:00'))
        if stamp.tzinfo is None: stamp=stamp.replace(tzinfo=timezone.utc)
        stamp=stamp.astimezone(timezone.utc)
        if _london_ny_overlap(stamp):
            samples_by_symbol.setdefault(str(row['symbol']),[]).append((stamp,float(row['spread_price'])))
    live=[]; costs={}; live_specs={}
    for logical in FOCUS_SYMBOLS:
        possible=[symbol for symbol,values in samples_by_symbol.items()
            if underlying_key(symbol).upper()==logical.upper() and symbol.endswith('#') and symbol in specs and values]
        if not possible: raise RuntimeError(f'No enabled # symbol spread samples in London/New York hours: {logical}')
        symbol=max(possible,key=lambda name:len(samples_by_symbol[name]))
        values=samples_by_symbol[symbol]
        first,last=values[0][0],values[-1][0]
        if (last-first)<timedelta(minutes=30) or len(values)<30:
            raise RuntimeError(f'{logical} needs at least 30 minutes and 30 M1 spread samples; got {len(values)} from {first.isoformat()} to {last.isoformat()}')
        spread_values=[value for _,value in values]
        median_spread=statistics.median(spread_values)
        spec=specs[symbol]
        tick_size=float(spec.get('trade_tick_size') or 0)
        tick_value=float(spec.get('trade_tick_value_loss') or spec.get('trade_tick_value') or 0)
        point=float(spec.get('point') or spec.get('point_size') or 0)
        digits=int(spec.get('digits') or 0)
        if tick_size<=0 or tick_value<=0 or point<=0: raise RuntimeError(f'Incomplete live symbol specs for {symbol}')
        cost=spread_cost_per_lot(median_spread,tick_size,tick_value)
        costs[logical]={'cost_per_lot':cost,'point':point,'tick_size':tick_size,'tick_value':tick_value}
        live_specs[logical]={'tick_size':tick_size,'tick_value_loss':tick_value,'volume_min':float(spec['volume_min']),
            'volume_step':float(spec['volume_step']),'contract_size':float(spec['trade_contract_size']),
            'point':point,'digits':digits}
        pip_size=point*(10 if digits in (3,5) else 1)
        live.append({'logical':logical,'symbol':symbol,'contract_size':float(spec['trade_contract_size']),
            'volume_min':float(spec['volume_min']),'volume_step':float(spec['volume_step']),
            'tick_size':tick_size,'tick_value_loss':tick_value,'spread_price':median_spread,
            'spread_min_price':min(spread_values),'spread_max_price':max(spread_values),
            'spread_pips':median_spread/pip_size if logical!='GOLD' else None,
            'spread_min_pips':min(spread_values)/pip_size if logical!='GOLD' else None,
            'spread_max_pips':max(spread_values)/pip_size if logical!='GOLD' else None,
            'cost_per_lot':cost,'sample_count':len(values),'sample_start':first.isoformat(),'sample_end':last.isoformat()})
    account_snapshot={'account_id':str(account['account_id']),
        'login_suffix':str(account['account_id'])[-3:],
        'balance':float(equity['balance']),'equity':float(equity['equity']),
        'currency':'USD','server':'XMGlobal-MT5 5','trade_mode':'DEMO',
        'snapshot_utc':now.isoformat(),
        'sample_start_utc':min(row['sample_start'] for row in live),
        'sample_end_utc':max(row['sample_end'] for row in live)}
    return live,costs,live_specs,account_snapshot


def write_live_cost_docs(live: list[dict], live_specs: dict, account: dict,
                         typical_atr: dict, *, root: Path=ROOT) -> None:
    """Regenerate account cost and minimum-lot docs from the same live sample."""
    logical_order=FOCUS_SYMBOLS
    spread_rows=[]
    for row in live:
        if row['logical']=='GOLD':
            spread_text=f"${row['spread_price']:.2f} (${row['spread_min_price']:.2f}–${row['spread_max_price']:.2f})"
        else:
            spread_text=f"{row['spread_pips']:.2f} pips ({row['spread_min_pips']:.2f}–{row['spread_max_pips']:.2f})"
        spread_rows.append((row,spread_text))
    risk_lines=[]
    for timeframe in ('M15','H1','H4','D1'):
        rows=[item for item in VARIANT_STOPS if item[2]==timeframe]
        risk_lines.extend([f'### {timeframe}','',f"| Family / variant | Stop multiple | {' | '.join(logical_order)} |",
            f"|---|---:|{'|'.join(['---:']*len(logical_order))}|"])
        for family,variant,tf,multiplier in rows:
            cells=[]
            for logical in logical_order:
                spec=live_specs[logical]; stop=float(typical_atr[logical,tf])*multiplier
                risk=stop/spec['tick_size']*spec['tick_value_loss']*spec['volume_min']
                if logical=='GOLD': cell=f"${stop:.2f} / ${risk:.2f}"
                else:
                    pip=spec['point']*(10 if spec['digits'] in (3,5) else 1)
                    cell=f"{stop/pip:.1f} pips / ${risk:.2f}"
                cells.append(cell)
            risk_lines.append(f"| {family} · {variant} | {multiplier:g}×ATR | {' | '.join(cells)} |")
        risk_lines.append('')
    budgets=['| Risk rate | Current $10,000 balance | $50 comparison balance |','|---:|---:|---:|']
    for rate in (.001,.0025,.005,.01): budgets.append(f'| {rate:.2%} | ${account["balance"]*rate:.2f} | ${50*rate:.3f} |')
    min_lot=['# Minimum-lot risk on the live XM Ultra Low DEMO account','',
        f"Live snapshot: `{account['snapshot_utc']}` UTC · account `{account['account_id']}` · balance/equity `${account['balance']:,.2f}` / `${account['equity']:,.2f}` USD · server `{account['server']}`.",
        f"Spread statistics use enabled `#` broker symbols, sampled on M1 during London/New York overlap from `{account['sample_start_utc']}` through `{account['sample_end_utc']}` UTC. Each symbol has at least 30 minutes of samples; the current spread shown is the median with observed minimum and maximum.",'',
        '## Live instrument specifications','',
        '| Logical instrument | Live MT5 symbol | Contract size | Min / step | Tick size | Tick value (loss/lot) | Spread median (min–max) | M1 samples |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for row,spread_text in spread_rows:
        spec=live_specs[row['logical']]
        contract=f"{spec['contract_size']:,.0f} oz" if row['logical']=='GOLD' else f"{spec['contract_size']:,.0f} units"
        min_lot.append(f"| {row['logical']} | `{row['symbol']}` | {contract} | {spec['volume_min']:g} / {spec['volume_step']:g} | {spec['tick_size']:g} | ${spec['tick_value_loss']:.6f} | {spread_text} | {row['sample_count']} |")
    min_lot.extend(['','## Risk budgets','',*budgets,'',
        'Minimum-lot stop risk is `abs(entry − stop) / tick_size × trade_tick_value_loss × volume_min`. JPY and CAD tick values are the live broker USD-converted values at snapshot time and can vary with conversion rates.','',
        '## Typical minimum-lot stop risk by family and timeframe','',
        '“Typical stop” is the unchanged research variant stop multiplier times median ATR(14) from closed history covering 2026-01-01 through 2026-09-30. Cells show `stop distance / risk at live volume_min`; FX distances are pips and GOLD distances are dollars.','',*risk_lines,
        '## Feasibility','',
        'Compare each displayed stop risk with the selected balance and risk rate above. Current broker specifications are used; no micro contract is assumed. Spread cost is reported separately and is not included in stop-risk figures.',''])
    (root/'docs'/'MIN_LOT.md').write_text('\n'.join(min_lot),encoding='utf-8')

    acc=['# Account and Symbol Facts & Cost Model v1','',
        f"Generated: {account['snapshot_utc']} UTC",'',
        '## 1. Account facts','',
        f"- **Account login:** `{account['account_id']}`",
        '- **Trade mode:** `DEMO` (verified from the running bot status)',
        f"- **Balance / equity:** `${account['balance']:.2f} / ${account['equity']:.2f} USD`",
        f"- **Server:** `{account['server']}`",'',
        '## 2. Enabled symbol specifications and observed spreads','',
        f"M1 spread samples cover London/New York overlap from `{account['sample_start_utc']}` through `{account['sample_end_utc']}` UTC. `Spread pts` is median (minimum–maximum); at least 30 minutes of observations are included for every symbol.",'',
        '| Symbol | Logical | Group | Digits | Point | Spread pts (min–max) | Median pips / $ | Min Vol | Step | Contract | Tick Size | Tick Value Loss | Samples |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for row,_ in spread_rows:
        spec=live_specs[row['logical']]; point=spec['point']; digits=spec['digits']
        minimum=row['spread_min_price']/point; median=row['spread_price']/point; maximum=row['spread_max_price']/point
        med_display=f"${row['spread_price']:.2f}" if row['logical']=='GOLD' else f"{row['spread_pips']:.2f} pips"
        acc.append(f"| `{row['symbol']}` | {row['logical']} | {'metals' if row['logical']=='GOLD' else 'forex'} | {digits} | {point:g} | {median:.1f} ({minimum:.1f}–{maximum:.1f}) | {med_display} | {spec['volume_min']:g} | {spec['volume_step']:g} | {spec['contract_size']:g} | {spec['tick_size']:g} | ${spec['tick_value_loss']:.6f} | {row['sample_count']} |")
    acc.extend(['','## 3. Conservative cost model v1','',
        'For live entry fallback, spread is current `symbol_info.spread × point × 1.25`; observed cells use their sample median. Both include two-sided slippage and estimated round-trip commission in the live gate. This research cost summary uses the frozen v4 assumption: median sampled spread × 1.25, without added slippage or commission.','',
        'Per-lot cost = `((median spread × 1.25) + (slippage points × point)) / tick size × loss tick value + round-trip commission`. Commission is not confirmed by closed deals on the new account; configured default is `$0.00/lot/side` and is labeled estimated.','',
        '| Symbol | Group | Median spread ×1.25 | Slippage | Commission source | Cost / 1 lot |','|---|---|---:|---:|---|---:|'])
    for row,_ in spread_rows:
        spec=live_specs[row['logical']]; slip_points=2.0 if row['logical']=='GOLD' else 1.0
        total=((row['spread_price']*SPREAD_MULTIPLIER+slip_points*spec['point'])/spec['tick_size']*spec['tick_value_loss'])
        effective=row['spread_price']*SPREAD_MULTIPLIER
        cost_spread=f"${effective:.2f}" if row['logical']=='GOLD' else f"{effective/(spec['point']*10):.2f} pips"
        slip=f"{slip_points:g} pts"
        acc.append(f"| `{row['symbol']}` | {'metals' if row['logical']=='GOLD' else 'forex'} | {cost_spread} | {slip} | estimated default $0.00/side | ${total:.2f} |")
    acc.extend(['','## 4. Sources','',
        '1. Account mode and connection: live `bot_status` maintained by the supervisor-owned MT5 session.',
        '2. Account balance/equity: latest live equity snapshot in `data/bot.db`.',
        '3. Broker specs: `data/history/symbol_specs.json`, refreshed through the bot-owned MT5 session.',
        '4. Spread min/median/max: `spread_samples` M1 records in `data/bot.db` from the enabled `#` symbol aliases during London/New York overlap.',''])
    (root/'docs'/'ACCOUNT_COSTS.md').write_text('\n'.join(acc),encoding='utf-8')


def _read_v3_rows(path: Path) -> dict[tuple[str,str],tuple[str,str,str,str]]:
    rows={}
    if not path.is_file(): return rows
    in_table=False
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('| Family | Variant |'):
            in_table=True; continue
        if not in_table: continue
        if not line.startswith('|'):
            if rows: break
            continue
        parts=[cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(parts)<13 or parts[0]=='---' or parts[0].startswith('---'): continue
        if parts[0]=='Family' or set(parts[0])<=set('-:'): continue
        rows[(parts[0],parts[1])]=(parts[2],parts[4],parts[5],parts[6])
    return rows


def run() -> tuple[bool,list[dict]]:
    settings=load_settings()
    live,costs,live_specs,account_snapshot=read_live_spread_snapshot(
        settings.db_path,Path(settings.data_dir)/'history'/'symbol_specs.json')

    if account_snapshot['login_suffix']!='323' or account_snapshot['balance']!=10000.0:
        raise RuntimeError(f"Unexpected live account for this report: {account_snapshot}")

    engine.FOCUS_SYMBOLS=FOCUS_SYMBOLS
    engine.FOREX_SYMBOLS=FOREX_SYMBOLS
    # The two historically index-labelled families are evaluated on the same
    # requested forex+gold universe, with their original 3 variants/parameters.
    engine.INDEX_SYMBOLS=FOCUS_SYMBOLS
    engine.load_costs_model=lambda: costs
    engine.REPORT_FILENAME='edge_research_v4_ultralow.md'
    engine.REPORT_TITLE='Systematic Edge Research v4 Ultra Low: Six Families, Forex + Gold'
    engine.COST_MODEL_LABEL='Enabled # symbol M1 median spread × 1.25; no added slippage or commission assumption.'
    engine.BENCHMARK_LABEL='Buy-and-hold returns for the same forex + gold research universe.'

    v3_path=ROOT/'reports'/'edge_research_v3.md'
    v3_rows=_read_v3_rows(v3_path)
    prior_v4_path=ROOT/'reports'/'edge_research_v4_ultralow.md'
    prior_v4_rows=_read_v3_rows(prior_v4_path)
    prior_v4_text=prior_v4_path.read_text(encoding='utf-8') if prior_v4_path.exists() else ''
    prior_v4_decision='Case A' if '**Research decision:** `Case A`' in prior_v4_text else 'Case B'
    qualified,rows=engine.run_research()
    if len(rows)!=18: raise RuntimeError(f'Expected 18 unchanged variants, got {len(rows)}')
    report=ROOT/'reports'/'edge_research_v4_ultralow.md'
    lines=report.read_text(encoding='utf-8').rstrip().splitlines()
    lines.extend(['','## Live DEMO cost snapshot','',
        f"Account: DEMO `{account_snapshot['server']}`, login ending `{account_snapshot['login_suffix']}`, balance `${account_snapshot['balance']:,.2f}`; sampled `{account_snapshot['sample_start_utc']}` through `{account_snapshot['sample_end_utc']}` UTC during London/New York overlap.",
        'Spreads are M1 live samples from enabled `#` symbols; each median spans at least 30 minutes. Offline research retains the v4 spread-cost formula: median live spread × loss tick value × 1.25, with no added slippage or commission.','',
        '| Symbol | Live name | Median spread (min–max) | Samples | Cost/lot after ×1.25 |','|---|---|---:|---:|---:|'])
    for row in live:
        if row['logical']!='GOLD':
            spread=f"{row['spread_pips']:.2f} pips ({row['spread_min_pips']:.2f}–{row['spread_max_pips']:.2f})"
        else:
            spread=f"${row['spread_price']:.2f} (${row['spread_min_price']:.2f}–${row['spread_max_price']:.2f})"
        lines.append(f"| {row['logical']} | `{row['symbol']}` | {spread} | {row['sample_count']} | ${row['cost_per_lot']:.2f} |")
    typical_atr={}
    history_dir=ROOT/'data'/'history'
    for logical in FOCUS_SYMBOLS:
        for timeframe in ('M15','H1','H4','D1'):
            frame=read_parquet(history_dir/f'{logical}_{timeframe}.parquet')
            series=engine.atr(frame,period=14)
            window=series[(series.index>='2026-01-01T00:00:00Z') & (series.index<='2026-09-30T23:59:59Z')].dropna()
            if window.empty: raise RuntimeError(f'No typical ATR data for {logical} {timeframe}')
            typical_atr[logical,timeframe]=float(window.median())
    write_live_cost_docs(live,live_specs,account_snapshot,typical_atr)
    lines.extend(['','## Typical 0.1% exploration sizing and cost gates','',
        'For each family stop, the reference distance is median ATR(14) from 2026-01-01 through 2026-09-30 times its unchanged variant stop multiple. Minimum-lot risk is tested against the live DEMO 0.1% budget ($10); cost gate is strict `<10%` of stop value. This matrix isolates these two gates; news, MTF, sessions, broker stops, margin, and other hard protections remain separately enforced.','',
        '| Family / variant | TF | Both pass | Min-lot fails | Cost gate fails |','|---|---|---|---|---|'])
    for family,variant,timeframe,multiplier in VARIANT_STOPS:
        passing=[]; min_fails=[]; cost_fails=[]
        symbols=FOREX_SYMBOLS if family=='Session Breakout' else FOCUS_SYMBOLS
        for logical in symbols:
            stop=typical_atr[logical,timeframe]*multiplier; spec=live_specs[logical]
            verdict=evaluate_live_gates(stop,spec['volume_min'],spec['tick_size'],spec['tick_value_loss'],costs[logical]['cost_per_lot'],account_snapshot['equity']*.001)
            if verdict['both_pass']: passing.append(logical)
            if not verdict['min_lot_pass']: min_fails.append(f"{logical} (${verdict['min_lot_risk']:.2f})")
            if not verdict['cost_pass']: cost_fails.append(f"{logical} ({verdict['cost_stop_ratio']:.1%})")
        lines.append(f"| {family} · {variant} | {timeframe} | {', '.join(passing) or 'none'} | {', '.join(min_fails) or 'none'} | {', '.join(cost_fails) or 'none'} |")
    lines.extend(['','## Side-by-side: v3 baseline vs v4 Ultra Low','',
        'Variant parameters, split boundaries, holdout protection, simulator, and 18-trial qualification tests are unchanged. V3 used its earlier 5-FX + 4-index + GOLD universe/costs; v4 evaluates 7 forex pairs + GOLD, so this is an operational comparison across the requested universe rather than a controlled same-universe cost-only ablation.','',
        '| Family | Variant | V3 N | V3 EV train | V3 EV val | V3 PF | V4 N | V4 EV train | V4 EV val | V4 PF | V4 status |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|'])
    for row in rows:
        old=v3_rows.get((row['family'],row['variant']),('n/a','n/a','n/a','n/a'))
        lines.append(f"| {row['family']} | {row['variant']} | {old[0]} | {old[1]} | {old[2]} | {old[3]} | {row['n_train']}/{row['n_val']} | {row['ev_train']} | {row['ev_val']} | {row['pf']} | {row['status']} |")
    lines.extend(['','## Corrected enabled-symbol spreads vs previous v4','',
        f"Previous v4 decision: `{prior_v4_decision}`. Corrected enabled-`#`-symbol decision: `{'Case A' if qualified else 'Case B'}`.",'',
        '| Family | Variant | Prior v4 N | Prior EV train | Prior EV val | Prior PF | Corrected N | Corrected EV train | Corrected EV val | Corrected PF | Corrected status |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|'])
    for row in rows:
        old=prior_v4_rows.get((row['family'],row['variant']),('n/a','n/a','n/a','n/a'))
        lines.append(f"| {row['family']} | {row['variant']} | {old[0]} | {old[1]} | {old[2]} | {old[3]} | {row['n_train']}/{row['n_val']} | {row['ev_train']} | {row['ev_val']} | {row['pf']} | {row['status']} |")
    lines.extend(['',f"**Research decision:** `{'Case A' if qualified else 'Case B'}`.",
        'No automatic transition from research qualification to normal trading is made by this script. DEMO exploration and the existing safety gates remain separate from this report.',''])
    report.write_text('\n'.join(lines),encoding='utf-8')
    print(f'Wrote {report}; {len(rows)} variants; decision={"Case A" if qualified else "Case B"}')
    return qualified,rows


if __name__=='__main__':
    run()
