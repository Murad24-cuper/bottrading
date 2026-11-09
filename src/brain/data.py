"""Cost/activity universe selection and auditable dataset metadata helpers."""
from __future__ import annotations
from pathlib import Path
import json
import math
from datetime import datetime,timezone

def select_universe(rows: list[dict], quotas: dict, limit: int=400) -> list[dict]:
    """Rank symbols by spread-to-expected-move and activity, preserving group quotas."""
    eligible=[]
    for row in rows:
        try:
            spread=float(row['spread_price']); atr=float(row['atr_price']); horizon=max(1.0,float(row.get('horizon_minutes',20)))
            activity=float(row.get('activity',0)); group=str(row['asset_group']); symbol=str(row['symbol'])
        except (KeyError,TypeError,ValueError): continue
        if not all(math.isfinite(value) for value in (spread,atr,horizon,activity)) or atr<=0 or spread<0: continue
        ratio=spread/(atr*math.sqrt(horizon)); score=ratio-0.002*math.log1p(max(0.0,activity))
        eligible.append({**row,'cost_to_move_ratio':ratio,'universe_score':score,'reason':f'cost/expected-move={ratio:.4f}; activity={activity:g}'})
    by_group: dict[str, list] = {}
    for row in eligible: by_group.setdefault(row['asset_group'],[]).append(row)
    selected=[]; seen=set()
    for group,quota in quotas.items():
        ranked=sorted(by_group.get(group,[]),key=lambda row:(row['universe_score'],row['symbol']))
        for row in ranked[:max(0,int(quota))]:
            if row['symbol'] not in seen: selected.append(row); seen.add(row['symbol'])
    remainder=sorted((row for row in eligible if row['symbol'] not in seen),key=lambda row:(row['universe_score'],row['symbol']))
    for row in remainder[:max(0,int(limit)-len(selected))]: selected.append(row); seen.add(row['symbol'])
    return selected[:int(limit)]

def save_universe(rows: list[dict], path: str|Path) -> None:
    """Persist selected symbols with reasons and UTC build time."""
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    payload={'built_at':datetime.now(timezone.utc).isoformat(),'symbols':rows}
    target.write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
