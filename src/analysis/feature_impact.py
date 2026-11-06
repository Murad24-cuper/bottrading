"""Descriptive feature outcome analysis with bootstrap uncertainty."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd

def _feature_values(payload):
    try: data=json.loads(payload) if isinstance(payload,str) else payload or {}
    except (ValueError,TypeError): return []
    found=[]
    def walk(value,path=''):
        if isinstance(value,dict):
            for key,item in value.items(): walk(item,f'{path}.{key}' if path else str(key))
        elif isinstance(value,list):
            for item in value:
                if isinstance(item,dict) and item.get('name'):
                    name=str(item['name']); direction=str(item.get('direction',''))
                    found.append((f'{path} contains {name}',True))
                    if direction: found.append((f'{path} direction {direction}',True))
                else: walk(item,path)
        elif isinstance(value,(str,bool,int,float)) or value is None:
            found.append((path,str(value).lower() if isinstance(value,bool) else value))
    walk(data)
    return [(key,value) for key,value in found if key and value is not None]

def analyze_feature_impact(trades,bootstrap_samples=2000,seed=7,min_trades=30):
    """Compare feature cohorts with all closed trades; small samples stay unproven."""
    rows=[dict(row) for row in trades]
    outcomes=[]; feature_rows=[]
    for row in rows:
        net=float(row.get('profit') or 0)+float(row.get('commission') or 0)+float(row.get('swap') or 0)
        outcomes.append((net>0,net)); feature_rows.append(set(_feature_values(row.get('features'))))
    if not rows: return []
    baseline_win=float(np.mean([win for win,_ in outcomes])); baseline_exp=float(np.mean([net for _,net in outcomes]))
    keys=sorted({item for values in feature_rows for item in values},key=lambda item:(item[0],str(item[1]))); rng=np.random.default_rng(seed); result=[]
    base=np.array([float(win) for win,_ in outcomes]); n=len(rows)
    for key,value in keys:
        indexes=[i for i,items in enumerate(feature_rows) if (key,value) in items]
        if not indexes: continue
        sample=np.array([float(outcomes[i][0]) for i in indexes]); nets=np.array([outcomes[i][1] for i in indexes])
        count=len(indexes); rate=float(sample.mean()); exp=float(nets.mean())
        if count>=min_trades:
            draws=np.empty(int(bootstrap_samples))
            for j in range(len(draws)):
                feature_win=float(rng.choice(sample,size=count,replace=True).mean())
                base_win=float(rng.choice(base,size=n,replace=True).mean())
                draws[j]=feature_win-base_win
            low,high=(float(x) for x in np.quantile(draws,[.05,.95]))
        else: low=high=None
        meaningful=count>=min_trades and (low>0 or high<0)
        result.append({'feature':f'{key}={value}','trades':count,'win_rate':rate,'expectancy':exp,'baseline_win_rate':baseline_win,'baseline_expectancy':baseline_exp,'win_rate_difference':rate-baseline_win,'ci90_low':low,'ci90_high':high,'meaningful':meaningful})
    return sorted(result,key=lambda row:(row['win_rate_difference'],row['expectancy']),reverse=True)

def closed_trade_features(connection):
    """Read closed trade outcomes from an existing SQLite connection."""
    return [dict(row) for row in connection.execute("SELECT profit,commission,swap,features FROM trades WHERE status='closed' ORDER BY close_time")]
