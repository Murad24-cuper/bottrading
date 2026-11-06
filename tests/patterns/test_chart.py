import numpy as np
import pandas as pd
from src.patterns.chart import detect_chart_patterns

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
