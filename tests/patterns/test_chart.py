import numpy as np
import pandas as pd
from src.patterns.chart import _boundary_pattern, _continuation_pattern, detect_chart_patterns

def _bars():
    x=np.arange(122,dtype=float); close=100+np.sin(x/4)*3+np.sin(x/11)*.2
    return pd.DataFrame({'open':close-.1,'high':close+.5,'low':close-.5,'close':close,'tick_volume':100})

def test_chart_patterns_report_atr_distance_and_state():
    result=detect_chart_patterns(_bars(),'M5')
    assert isinstance(result,list)
    assert all({'name','direction','timeframe','state','breakout_level','distance_atr'}<=item.keys() for item in result)
    assert all(item['timeframe']=='M5' and item['direction'] in {'bullish','bearish'} for item in result)

def test_chart_detector_ignores_forming_last_bar():
    bars=_bars(); baseline=detect_chart_patterns(bars,'M15')
    bars.iloc[-1,bars.columns.get_loc('close')]=1e9
    bars.iloc[-1,bars.columns.get_loc('high')]=1e9
    bars.iloc[-1,bars.columns.get_loc('low')]=1e9
    assert detect_chart_patterns(bars,'M15')==baseline

def test_each_converging_boundary_pattern_has_a_direction():
    assert _boundary_pattern(-1,1,True,.1)==('symmetrical_triangle','bullish')
    assert _boundary_pattern(0,1,False,.1)==('ascending_triangle','bullish')
    assert _boundary_pattern(-1,0,False,.1)==('descending_triangle','bearish')
    assert _boundary_pattern(1,2,True,.1)==('rising_wedge','bearish')
    assert _boundary_pattern(-2,-1,True,.1)==('falling_wedge','bullish')
    assert _boundary_pattern(0,0,False,.1)[0]=='rectangle'

def test_flag_and_pennant_continuation_classification():
    assert _continuation_pattern(10,4,True)=='flag'
    assert _continuation_pattern(-10,4,False)=='pennant'
    assert _continuation_pattern(10,8,True) is None
