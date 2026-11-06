from src.brain.drift import assess_live_drift

def test_drift_guard_waits_for_full_recent_window():
    result=assess_live_drift([{'probability':.9,'win':True,'net_r':1}],100)
    assert not result['ready'] and not result['trigger']

def test_drift_guard_triggers_on_calibration_error_or_negative_expectancy():
    rows=[{'probability':.9,'win':False,'net_r':-1} for _ in range(100)]
    result=assess_live_drift(rows,100,.1,0)
    assert result['trigger'] and len(result['reasons'])==2
