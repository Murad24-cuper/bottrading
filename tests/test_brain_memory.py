from datetime import datetime,timezone,timedelta
import numpy as np
import pandas as pd
from src.brain.memory import apply_pca,fit_pca,query_memory,situation_vector

def test_memory_purges_future_rows_and_near_same_symbol():
    now=datetime(2026,1,10,tzinfo=timezone.utc); vector=np.array([1.,2.])
    rows=[{'time':(now-timedelta(days=3)).isoformat(),'symbol':'EURUSD','vector':[1,2],'win':1,'net_r':2},
          {'time':(now-timedelta(hours=12)).isoformat(),'symbol':'EURUSD','vector':[1,2],'win':0,'net_r':-1},
          {'time':(now+timedelta(days=1)).isoformat(),'symbol':'GBPUSD','vector':[1,2],'win':1,'net_r':1}]
    result=query_memory(vector,rows,now,'EURUSD',k=10,exclude_same_symbol_days=1)
    assert result['count']==1 and result['probability']==1 and result['cases'][0]['symbol']=='EURUSD'

def test_pca_uses_training_rows_and_transforms_vectors():
    train=np.arange(40,dtype=float).reshape(10,4); model=fit_pca(train,2)
    transformed=apply_pca(train,model)
    assert transformed.shape==(10,2) and np.allclose(transformed.mean(axis=0),0,atol=1e-5)

def test_situation_vector_has_stable_size_from_closed_bar_history():
    index=pd.date_range('2026-01-01',periods=100,freq='5min',tz='UTC')
    frame=pd.DataFrame({'close':np.linspace(100,110,100),'high':np.linspace(100.1,110.1,100),'low':np.linspace(99.9,109.9,100)},index=index)
    vector=situation_vector({'M5':frame,'M15':frame})
    assert vector.shape==(88,) and np.isfinite(vector).all()
