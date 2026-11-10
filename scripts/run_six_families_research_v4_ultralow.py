"""Re-run the unchanged v3 18-variant protocol on live Ultra Low DEMO costs.

The market-data windows, variant parameters, trade simulator, splits, protected
holdout, and qualification tests come from run_six_families_research_v3.py.
Only the symbol universe and live-spread cost inputs are replaced here.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_settings
from src.mt5_client import MT5Client
from src.symbols import SymbolService
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
    live=[]; costs={}; live_specs={}
    with MT5Client(settings) as client:
        mt5=client.mt5; account=mt5.account_info()
        if account is None or account.trade_mode!=getattr(mt5,'ACCOUNT_TRADE_MODE_DEMO',0):
            raise RuntimeError('Research cost capture requires a connected DEMO account')
        service=SymbolService(mt5,settings)
        for logical in FOCUS_SYMBOLS:
            symbol=service.resolve_alias(logical)
            info=mt5.symbol_info(symbol) if symbol else None
            tick=mt5.symbol_info_tick(symbol) if symbol else None
            if info is None or tick is None: raise RuntimeError(f'Live symbol quote/spec unavailable: {logical}')
            tick_size=float(info.trade_tick_size or 0)
            tick_value=float(info.trade_tick_value_loss or info.trade_tick_value or 0)
            spread=float(tick.ask)-float(tick.bid)
            cost=spread_cost_per_lot(spread,tick_size,tick_value)
            costs[logical]={'cost_per_lot':cost,'point':float(info.point),'tick_size':tick_size,'tick_value':tick_value}
            live_specs[logical]={'tick_size':tick_size,'tick_value_loss':tick_value,'volume_min':float(info.volume_min)}
            live.append({'logical':logical,'symbol':symbol,'contract_size':float(info.trade_contract_size),
                'volume_min':float(info.volume_min),'volume_step':float(info.volume_step),'tick_size':tick_size,
                'tick_value_loss':tick_value,'spread_price':spread,
                'spread_pips':spread/(float(info.point)*(10 if int(info.digits) in (3,5) else 1)) if logical!='GOLD' else None,
                'cost_per_lot':cost})
        account_snapshot={'login_suffix':str(account.login)[-3:],'balance':float(account.balance),
            'equity':float(account.equity),'currency':str(account.currency),'server':str(account.server),
            'trade_mode':'DEMO','snapshot_utc':datetime.now(timezone.utc).isoformat()}

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
    engine.COST_MODEL_LABEL='Live DEMO bid/ask spread × 1.25; no added slippage or commission assumption.'
    engine.BENCHMARK_LABEL='Buy-and-hold returns for the same forex + gold research universe.'

    v3_path=ROOT/'reports'/'edge_research_v3.md'
    v3_rows=_read_v3_rows(v3_path)
    qualified,rows=engine.run_research()
    if len(rows)!=18: raise RuntimeError(f'Expected 18 unchanged variants, got {len(rows)}')
    report=ROOT/'reports'/'edge_research_v4_ultralow.md'
    lines=report.read_text(encoding='utf-8').rstrip().splitlines()
    lines.extend(['','## Live DEMO cost snapshot','',
        f"Account: DEMO `{account_snapshot['server']}`, login ending `{account_snapshot['login_suffix']}`, balance `${account_snapshot['balance']:,.2f}`; captured `{account_snapshot['snapshot_utc']}`.",
        'Per-lot modeled cost is live `(ask − bid) / tick_size × loss_tick_value × 1.25`; the research uses the same sizing-independent stop-cost gate as v3. No slippage or commission is added.','',
        '| Symbol | Live name | Spread | Cost/lot after ×1.25 |','|---|---|---:|---:|'])
    for row in live:
        spread=f"{row['spread_pips']:.2f} pips" if row['logical']!='GOLD' else f"${row['spread_price']:.2f}"
        lines.append(f"| {row['logical']} | `{row['symbol']}` | {spread} | ${row['cost_per_lot']:.2f} |")
    typical_atr={}
    history_dir=ROOT/'data'/'history'
    for logical in FOCUS_SYMBOLS:
        for timeframe in ('M15','H1','H4','D1'):
            frame=engine.pd.read_parquet(history_dir/f'{logical}_{timeframe}.parquet')
            series=engine.atr(frame,period=14)
            window=series[(series.index>='2026-01-01T00:00:00Z') & (series.index<='2026-09-30T23:59:59Z')].dropna()
            if window.empty: raise RuntimeError(f'No typical ATR data for {logical} {timeframe}')
            typical_atr[logical,timeframe]=float(window.median())
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
    lines.extend(['',f"**Research decision:** `{'Case A' if qualified else 'Case B'}`.",
        'No automatic transition from research qualification to normal trading is made by this script. DEMO exploration and the existing safety gates remain separate from this report.',''])
    report.write_text('\n'.join(lines),encoding='utf-8')
    print(f'Wrote {report}; {len(rows)} variants; decision={"Case A" if qualified else "Case B"}')
    return qualified,rows


if __name__=='__main__':
    run()
