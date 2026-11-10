"""Acceptance-gated brain scoring; it cannot override the risk manager."""
from __future__ import annotations

def expected_value_r(probability: float, avg_win_r: float, avg_loss_r: float, cost_r: float) -> float:
    p=float(probability)
    return p*float(avg_win_r)-(1-p)*float(avg_loss_r)-float(cost_r)

def decide(checklist: dict, memory: dict, config: dict, cost_r: float=0.0) -> dict:
    """Evaluate brain entry rules while remaining descriptive when memory is absent."""
    reasons=[]; p=memory.get('probability'); win=float(memory.get('avg_win_r',0)); loss=float(memory.get('avg_loss_r',0))
    if memory.get('out_of_distribution') is True: reasons.append('out of distribution; brain abstains')
    ev=expected_value_r(float(p),win,loss,cost_r) if p is not None else None
    if float(checklist.get('score',0))<float(config.get('min_checklist',.55)): reasons.append('checklist below floor')
    if checklist.get('blocking_failures'): reasons.extend(checklist['blocking_failures'])
    if p is None: reasons.append('past-situation memory is unavailable')
    elif float(p)<float(config.get('min_probability',.55)): reasons.append('probability below floor')
    if ev is not None and ev<=float(config.get('min_ev_r',.05)): reasons.append('expected value below floor')
    return {'accepted':not reasons,'probability':p,'avg_win_r':win,'avg_loss_r':loss,'expected_value_r':ev,'reasons':reasons}
