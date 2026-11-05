import numpy as np
import pandas as pd
import pytest
from src.strategies import REGISTRY,load_strategies
from src.models import Signal

def make_candles(n=160):
    x=np.arange(n); close=100+0.03*x+np.sin(x/3)*.5
    return pd.DataFrame({'open':close-.04,'high':close+.2,'low':close-.2,'close':close,'tick_volume':100+(x%9)*4,'spread':1,'spread_points':1,'spread_price':.001},index=pd.date_range('2026-01-01',periods=n,freq='min',tz='UTC'))

@pytest.mark.parametrize('name',list(REGISTRY))
def test_strategy_returns_none_or_valid_closed_bar_signal(name):
    cls=REGISTRY[name]; strategy=cls({}); candles=make_candles()
    values={tf:candles.copy() for tf in strategy.required_timeframes}
    result=strategy.generate_signal('EURUSD',values)
    assert result is None or isinstance(result,Signal)
    if result:
        assert 0<=result.confidence<=1
        assert result.sl_price is not None and result.tp_price is not None
        assert result.sl_price<result.entry_hint<result.tp_price if result.direction=='buy' else result.tp_price<result.entry_hint<result.sl_price

def test_registry_loads_only_enabled_and_group_eligible_strategies():
    config={'strategies':{'breakout':{'enabled':True,'groups':['forex'],'params':{}},'mean_reversion':{'enabled':True,'groups':['metals'],'params':{}},'trend_pullback':{'enabled':False}}}
    assert [s.name for s in load_strategies(config,'forex')]==['breakout']
