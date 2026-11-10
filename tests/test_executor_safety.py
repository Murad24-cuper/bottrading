from pathlib import Path
from types import SimpleNamespace

from src.executor import Executor
from src.models import Signal


class FakeDB:
    def __init__(self): self.events=[]; self.open=[]; self.inserted=[]
    def log_event(self,*args): self.events.append(args)
    def get_open_trades(self): return self.open
    def insert_trade(self,**kwargs): self.inserted.append(kwargs)
    def update_open_trade(self,*args,**kwargs): return 1
    def get_trade(self,*args,**kwargs): return None

class FakeMT5:
    POSITION_TYPE_BUY=0; ORDER_TYPE_BUY=0; ORDER_TYPE_SELL=1
    SYMBOL_TRADE_MODE_FULL=4; SYMBOL_FILLING_FOK=1; ORDER_FILLING_FOK=0
    SYMBOL_TRADE_EXECUTION_MARKET=2; ACCOUNT_MARGIN_MODE_RETAIL_NETTING=0
    ACCOUNT_TRADE_MODE_DEMO=0
    TRADE_ACTION_SLTP=6; TRADE_RETCODE_DONE=10009; TRADE_RETCODE_REQUOTE=10004; TRADE_RETCODE_PRICE_CHANGED=10020
    TRADE_ACTION_DEAL=1; ORDER_TIME_GTC=0
    def __init__(self):
        self.orders=[]; self.position=SimpleNamespace(ticket=9,identifier=9,magic=7,symbol='EURUSD',type=0,price_open=1.1,sl=1.099,tp=1.103,volume=.1,profit=0,swap=0,time=1735689600)
        self.info=SimpleNamespace(trade_mode=4,trade_stops_level=0,point=.00001,volume_min=.01,volume_step=.01,volume_max=10,trade_tick_size=.0001,trade_tick_value=1,trade_tick_value_loss=1,filling_mode=1,trade_exemode=1)
        self.info._asdict=lambda:{'trade_tick_size':.0001,'trade_tick_value':1,'trade_tick_value_loss':1,'volume_min':.01,'volume_step':.01,'volume_max':10}
        self.tick=SimpleNamespace(bid=1.101,ask=1.1011)
    def positions_get(self,*args,**kwargs): return [self.position]
    def symbol_info(self,*args): return self.info
    def symbol_info_tick(self,*args): return self.tick
    def account_info(self): return SimpleNamespace(equity=1000,balance=1000,margin_mode=2,trade_mode=0)
    def order_send(self,**request): self.orders.append(request); return SimpleNamespace(retcode=10009,price=request.get('price',0),comment='done',position=9,order=9,deal=9)
    def last_error(self): return (0,'ok')

def make_executor(tmp_path):
    settings=SimpleNamespace(root=Path(tmp_path),magic_number=7,risk=SimpleNamespace(risk_per_trade_pct=.5),allow_real=False,config={'account':{'mode':'demo'},'executor':{'deviation_points':20}})
    class Service:
        def is_tradable(self,symbol): return True,'tradable'
        def get_asset_group(self,symbol): return 'forex'
    mt5=FakeMT5(); db=FakeDB(); return Executor(mt5,settings,db,Service()),mt5,db

def test_modify_sl_tp_refuses_widen_or_remove_stop(tmp_path):
    executor,mt5,_=make_executor(tmp_path)
    assert not executor.modify_sl_tp(9,1.098,1.103)
    assert not executor.modify_sl_tp(9,0,1.103)
    assert mt5.orders==[]
    assert executor.modify_sl_tp(9,1.1005,1.103)
    assert mt5.orders[-1]['sl']==1.1005

def test_partial_close_rejects_over_open_and_rounds_off_step_down(tmp_path):
    executor,mt5,_=make_executor(tmp_path)
    assert not executor._close_partial(mt5.position,.11).success
    assert executor._close_partial(mt5.position,.015).success
    assert mt5.orders[-1]['volume']==.01

def test_executor_refuses_direct_order_larger_than_stop_risk_volume(tmp_path):
    executor,mt5,_=make_executor(tmp_path)
    signal=Signal('EURUSD','buy','M5',1.101,1.1,1.103,.8,'test')
    result=executor.open_trade(signal,.6)
    assert not result.success and 'exceeds stop-risk size' in result.message
    assert mt5.orders==[]

def test_executor_real_account_needs_both_real_guards(tmp_path):
    executor,mt5,_=make_executor(tmp_path)
    mt5.account_info=lambda:SimpleNamespace(equity=1000,balance=1000,margin_mode=2,trade_mode=1)
    signal=Signal('EURUSD','buy','M5',1.101,1.1,1.103,.8,'test')
    result=executor.open_trade(signal,.05)
    assert not result.success and 'real account requires' in result.message
    assert mt5.orders==[]
