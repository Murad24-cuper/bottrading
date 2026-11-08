"""Test-period acceptance gate and ablation summaries."""
from __future__ import annotations
import math
import pandas as pd

def _summary(rows: pd.DataFrame) -> dict:
    if rows.empty: return {'trades':0,'win_rate':0.0,'expectancy_r':None,'profit_factor':None,'symbols':0,'groups_positive':0,'subperiods_positive':0,'dominant_group_share':1.0}
    net=rows['net_r'].astype(float); gains=net[net>0].sum(); losses=-net[net<0].sum()
    group_ev=rows.groupby('asset_group').net_r.mean() if 'asset_group' in rows else pd.Series(dtype=float)
    group_counts=rows.groupby('asset_group').size() if 'asset_group' in rows else pd.Series(dtype=int)
    sub=rows.groupby('subperiod').net_r.mean() if 'subperiod' in rows else pd.Series(dtype=float)
    return {'trades':len(rows),'win_rate':float((net>0).mean()),'expectancy_r':float(net.mean()),'profit_factor':float(gains/losses) if losses else (math.inf if gains else 0.0),'symbols':int(rows['symbol'].nunique()) if 'symbol' in rows else 0,'groups_positive':int((group_ev>0).sum()),'subperiods_positive':int((sub>0).sum()),'dominant_group_share':float(group_counts.max()/group_counts.sum()) if len(group_counts) else 1.0}

def evaluate_test_period(rows: pd.DataFrame, config: dict) -> dict:
    """Evaluate the full-rule test predictions; empty or insufficient data fails closed."""
    required={'probability','actual_win','net_r','symbol','asset_group','subperiod','checklist_only','memory_only','both','current_rule'}
    missing=required-set(rows.columns)
    if missing: return {'passed':False,'reasons':[f'missing columns: {", ".join(sorted(missing))}'],'calibration':[],'selected':{},'ablation':{},'current_rule':{}}
    data=rows.copy(); data=data[pd.to_numeric(data.probability,errors='coerce').between(0,1)&pd.to_numeric(data.net_r,errors='coerce').notna()]
    buckets=[]
    edges=[i/10 for i in range(11)]
    data['bucket']=pd.cut(data.probability,edges,include_lowest=True)
    for name,group in data.groupby('bucket',observed=True):
        if len(group)>=200:
            buckets.append({'bucket':str(name),'samples':len(group),'predicted':float(group.probability.mean()),'actual':float(group.actual_win.mean()),'error':abs(float(group.probability.mean())-float(group.actual_win.mean()))})
    selected=data[data['both'].astype(bool)]
    summary=_summary(selected); reasons=[]
    max_error=max((row['error'] for row in buckets),default=1.0)
    acceptance=config.get('acceptance',{})
    if not buckets: reasons.append('no calibration bucket has 200+ test samples')
    elif max_error>=float(acceptance.get('calibration_error',.05)): reasons.append(f'calibration error {max_error:.3f} is not below limit')
    if summary['trades']<int(acceptance.get('min_trades',500)): reasons.append('fewer than required selected test trades')
    if summary['expectancy_r'] is None or summary['expectancy_r']<=0: reasons.append('selected test expectancy is not positive')
    if summary['profit_factor'] is None or summary['profit_factor']<=float(acceptance.get('min_profit_factor',1.1)): reasons.append('selected test profit factor is not above the limit')
    if summary['subperiods_positive']<2: reasons.append('fewer than two of three subperiods are profitable')
    if summary['symbols']<int(acceptance.get('min_symbols',30)): reasons.append('fewer than required distinct symbols')
    if summary['groups_positive']<2 or summary['dominant_group_share']>.8: reasons.append('results depend too heavily on one asset group')
    ablation={name:_summary(data[data[name].astype(bool)]) for name in ('checklist_only','memory_only','both')}
    current=_summary(data[data['current_rule'].astype(bool)])
    if not data['current_rule'].astype(bool).any():
        reasons.append('no current rule-based strategy baseline was supplied for the same test period')
    return {'passed':not reasons,'reasons':reasons,'calibration':buckets,'max_calibration_error':max_error,'selected':summary,'ablation':ablation,'current_rule':current}

def render_report(result: dict) -> str:
    """Render a concise Markdown acceptance report."""
    status='PASS' if result['passed'] else 'FAIL'
    lines=[f'# Brain acceptance gate: {status}','', 'Only the final held-out test period is used here.','', '## Gate reasons']
    lines += [f'- {reason}' for reason in result['reasons']] or ['- All configured thresholds passed.']
    lines += ['', '## Calibration','', '| Bucket | N | Predicted | Actual | Error |','|---|---:|---:|---:|---:|']
    lines += [f"| {row['bucket']} | {row['samples']} | {row['predicted']:.1%} | {row['actual']:.1%} | {row['error']:.1%} |" for row in result['calibration']]
    for title,key in (('Selected both layers','selected'),('Ablation','ablation'),('Current rule','current_rule')):
        lines += ['',f'## {title}','']
        rows=result[key] if isinstance(result[key],dict) and key=='ablation' else {key:result[key]}
        lines += ['| Model | Trades | Win rate | Expectancy R | Profit factor | Symbols |', '|---|---:|---:|---:|---:|---:|']
        lines += [f"| {name} | {item['trades']} | {item['win_rate']:.1%} | {item['expectancy_r'] if item['expectancy_r'] is not None else 'N/A'} | {item['profit_factor']} | {item['symbols']} |" for name,item in rows.items()]
    return '\n'.join(lines)+'\n'
