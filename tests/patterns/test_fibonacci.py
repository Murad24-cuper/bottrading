import numpy as np
import pandas as pd
from src.patterns.fibonacci import fibonacci_retracement

def test_fibonacci_returns_all_levels_and_atr_distance():
    close=np.linspace(100,120,101)
    d=pd.DataFrame({'open':close-.1,'high':close+.5,'low':close-.5,'close':close,'tick_volume':1})
    result=fibonacci_retracement(d,'M15')
    assert len(result['levels'])==5 and result['nearest']['distance_atr']>=0
    assert result['swing_direction']=='up'

def test_fibonacci_ignores_forming_bar():
    close=np.linspace(100,120,101)
    d=pd.DataFrame({'open':close-.1,'high':close+.5,'low':close-.5,'close':close,'tick_volume':1})
    expected=fibonacci_retracement(d,'H1'); d.loc[100,['high','low','close']]=[1e9,0,1e9]
    assert fibonacci_retracement(d,'H1')==expected
