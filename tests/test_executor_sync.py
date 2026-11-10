from pathlib import Path
from types import SimpleNamespace

import pytest

from src.db import Database
from src.executor import Executor


def test_sync_separates_partial_and_final_realized_pnl(tmp_path):
    import json
    db=Database(tmp_path/'sync.db')
    db.insert_trade(ticket=17,symbol='EURUSD',asset_group='forex',direction='buy',volume=.5,initial_volume=1.0,open_time='2026-11-05T10:00:00+00:00',open_price=1.1,sl=1.09,tp=1.12,profit=0,commission=0,swap=0,magic=7,status='open',initial_risk=.01,features=json.dumps({'sizing':{'stressed_risk_money':2},'process_review':{'good_process':True,'outcome_r':None,'outcome_grade':'pending'}}))
    deals=[
        SimpleNamespace(ticket=1,position_id=17,entry=0,time=1793872800,volume=1.0,price=1.1,profit=0,commission=-.1,swap=0,reason=0,comment=''),
        SimpleNamespace(ticket=2,position_id=17,entry=1,time=1793872860,volume=.5,price=1.11,profit=1,commission=-.05,swap=.01,reason=0,comment='partial_tp'),
        SimpleNamespace(ticket=3,position_id=17,entry=1,time=1793872920,volume=.5,price=1.12,profit=2,commission=-.05,swap=.02,reason=5,comment=''),
    ]
    class MT5:
        DEAL_ENTRY_OUT=1; DEAL_ENTRY_OUT_BY=3; DEAL_ENTRY_INOUT=2; DEAL_ENTRY_TP=5; DEAL_REASON_TP=5; DEAL_REASON_SL=4
        def positions_get(self): return []
        def history_deals_get(self,*args,**kwargs): return deals
        def last_error(self): return (0,'ok')
    settings=SimpleNamespace(magic_number=7)
    executor=Executor(MT5(),settings,db)
    assert executor.sync_positions()==[17]
    row=db.get_trade(17); partial=db.get_partial_closes(17)
    assert row['close_reason']=='tp' and row['profit']==2
    assert row['commission']==pytest.approx(-.15) and row['swap']==pytest.approx(.02)
    assert len(partial)==1 and partial[0]['deal_ticket']==2 and partial[0]['profit']==1
    assert db.get_pnl_since('2026-11-05T00:00:00+00:00')==pytest.approx(2.83)
    review=json.loads(row['features'])['process_review']
    assert review['outcome_grade']=='win' and review['outcome_r']==pytest.approx(2.83/2)


@pytest.mark.parametrize(('stop','deal_profit','expected'),[
    (1.099,0.0,'trail'),   # stop moved from the original 1.0900 level
    (1.09,0.25,'trail'),   # profitable stop execution even if row history is old
    (1.09,-0.5,'sl'),      # original stop with a loss remains an SL
])
def test_sync_classifies_profitable_or_moved_sl_as_trailing_stop(tmp_path,stop,deal_profit,expected):
    db=Database(tmp_path/'trail.db')
    db.insert_trade(ticket=18,symbol='EURUSD',asset_group='forex',direction='buy',volume=.1,initial_volume=.1,open_time='2026-11-05T10:00:00+00:00',open_price=1.1,sl=stop,tp=1.12,profit=0,commission=0,swap=0,magic=7,status='open',initial_risk=.01)
    deal=SimpleNamespace(ticket=4,position_id=18,entry=1,time=1793872860,volume=.1,price=stop,profit=deal_profit,commission=0,swap=0,reason=4,comment='')
    class MT5:
        DEAL_ENTRY_OUT=1; DEAL_ENTRY_OUT_BY=3; DEAL_ENTRY_INOUT=2; DEAL_REASON_TP=5; DEAL_REASON_SL=4
        def positions_get(self): return []
        def history_deals_get(self,*args,**kwargs): return [deal]
        def last_error(self): return (0,'ok')
    executor=Executor(MT5(),SimpleNamespace(magic_number=7),db)
    assert executor.sync_positions()==[18]
    assert db.get_trade(18)['close_reason']==expected


def test_sync_mirrors_external_position_for_dashboard_without_treating_it_as_bot_trade(tmp_path):
    db=Database(tmp_path/'external.db')
    db.set_active_account_id('108765323')
    external=SimpleNamespace(ticket=77,identifier=77,magic=9001,symbol='GBPUSD#',type=0,volume=.03,
        price_open=1.3,sl=1.31,tp=1.28,profit=-.2,swap=0,time=0,comment='manual')
    class MT5:
        POSITION_TYPE_BUY=0; DEAL_ENTRY_OUT=1; DEAL_ENTRY_OUT_BY=3; DEAL_ENTRY_INOUT=2; DEAL_REASON_TP=5; DEAL_REASON_SL=4
        def positions_get(self): return [external]
        def history_deals_get(self,*args,**kwargs): return []
        def last_error(self): return (0,'ok')
    executor=Executor(MT5(),SimpleNamespace(magic_number=7),db)
    assert executor.sync_positions()==[]
    with db.connect() as connection:
        row=connection.execute('SELECT account_id,ticket,symbol,magic,volume,sl,tp,status,comment FROM external_positions').fetchone()
        assert dict(row)=={'account_id':'108765323','ticket':77,'symbol':'GBPUSD#','magic':9001,'volume':.03,'sl':1.31,'tp':1.28,'status':'open','comment':'manual'}
        assert connection.execute('SELECT COUNT(*) FROM trades').fetchone()[0]==0
