"""Live calibration and expectancy guard for accepted brain trades."""
from __future__ import annotations
import math

def assess_live_drift(rows: list[dict], window: int=100, max_calibration_error: float=.1,
                      min_expectancy_r: float=0.0) -> dict:
    """Return a shadow-mode trigger only after a complete recent brain-trade window."""
    recent=rows[:max(1,int(window))]
    if len(recent)<int(window): return {'ready':False,'trigger':False,'count':len(recent),'calibration_error':None,'expectancy_r':None,'reasons':[]}
    predicted=sum(float(row['probability']) for row in recent)/len(recent)
    actual=sum(bool(row['win']) for row in recent)/len(recent)
    calibration=abs(predicted-actual); expectancy=sum(float(row['net_r']) for row in recent)/len(recent)
    reasons=[]
    if calibration>float(max_calibration_error): reasons.append('live calibration error above limit')
    if expectancy<float(min_expectancy_r): reasons.append('live expectancy below zero')
    return {'ready':True,'trigger':bool(reasons),'count':len(recent),'calibration_error':calibration,'expectancy_r':expectancy,'reasons':reasons}
