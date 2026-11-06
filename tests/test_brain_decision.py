from src.brain.decide import decide,expected_value_r
from src.brain.sizing import fractional_kelly_risk_pct

def test_brain_decision_missing_memory_never_accepts_and_ev_after_costs():
    assert abs(expected_value_r(.6,2,1,.2)-.6)<1e-12
    assert decide({'score':1,'blocking_failures':[]},{'probability':None},{})['accepted'] is False

def test_fractional_kelly_is_zero_for_nonpositive_edge_and_bounded():
    assert fractional_kelly_risk_pct(.4,1)==0
    assert fractional_kelly_risk_pct(.9,2)==.5
