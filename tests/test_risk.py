from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
import pytest
from src.models import Signal,AccountState
from src.risk import calc_volume,check_trade_allowed

SPEC={'trade_tick_value':1.0,'trade_tick_size':0.0001,'volume_min':0.01,'volume_step':0.01,'volume_max':10.0}

def test_calc_volume_normal_case():
    volume,reason=calc_volume(1000,0.5,1.1,1.099,SPEC)
    assert volume==0.5 and reason=='ok'
def test_calc_volume_ten_dollar_account_refused():
    assert calc_volume(10,0.5,1.1,1.099,SPEC)==(0,'min lot exceeds risk')
def test_calc_volume_rounds_down_to_step():
    assert calc_volume(150,0.5,1.1,1.099,SPEC)[0]==0.07
def test_calc_volume_caps_at_volume_max():
    assert calc_volume(100000,50,1.1,1.099,{**SPEC,'volume_max':0.2})[0]==0.2

@pytest.mark.parametrize('entry,sl,tick_size,tick_value',[(1.1,1.099,.00001,1.0),(2000,1999,.01,1.0),(5000,4990,1.0,.1),(50000,49900,.1,.01),(100,99,.01,.1)])
def test_volume_risk_uses_tick_money_for_major_asset_classes(entry,sl,tick_size,tick_value):
    spec={**SPEC,'trade_tick_size':tick_size,'trade_tick_value_loss':tick_value,'volume_max':100}
    volume,reason=calc_volume(1000,.5,entry,sl,spec)
    assert reason=='ok' and volume>0
    risk=abs(entry-sl)/tick_size*tick_value*volume
    assert risk<=5+1e-8

def make_context(tmp_path):
    risk={'risk_per_trade_pct':0.5,'daily_loss_limit_pct':3.0,'weekly_loss_limit_pct':8.0,'max_open_positions':10,'max_positions_per_group':4,'max_positions_per_currency':2,'max_positions_per_underlying_group':2,'symbol_cooldown_minutes':30,'max_trades_per_symbol_per_day':5,'max_margin_usage_pct':40.0,'max_hold_minutes':720,'min_risk_reward':1.0,'max_cost_to_target_ratio':0.3,'max_spread_points':{},'no_entry_before_close_minutes':60,'max_session_gap_hours':6}
    settings=SimpleNamespace(config={'risk':risk},root=tmp_path,risk=SimpleNamespace(**risk))
    account=AccountState(1000,1000,0,1000,None,'USD',100,0,2)
    signal=Signal('EURUSD','buy','M5',100,99,102,0.8,'test')
    now=datetime(2026,11,2,12,0,tzinfo=timezone.utc) # Monday
    costs={'cost':0.1,'commission_known':True}; target_spec={'tick_value':1.0,'tick_size':1.0}
    allowed=check_trade_allowed(signal,account,[],0,0,settings,costs,'forex',now,0,1.0,target_spec)
    def check(**kw):
        values=dict(signal=signal,account=account,open_positions=[],pnl_today=0,pnl_week=0,settings=settings,cost_estimate=costs,symbol_group='forex',now_utc=now,required_margin=0,volume=1.0,symbol_spec=target_spec)
        values.update(kw)
        return check_trade_allowed(**values)
    return settings,account,signal,now,allowed,check

def test_check_trade_allowed_allows_valid_trade(tmp_path):
    *_,allowed,_=make_context(tmp_path)
    assert allowed==(True,'allowed')
def test_check_trade_allowed_kill_switch_first(tmp_path):
    _,_,_,_,allowed,check=make_context(tmp_path); assert allowed[0]; (tmp_path/'STOP').touch()
    assert check()[1]=='kill switch active'
def test_check_trade_allowed_session_close_blocks_on_any_weekday(tmp_path):
    _,_,_,_,allowed,check=make_context(tmp_path); assert allowed[0]
    assert check(session_closing=True)[1]=='symbol session closes soon'
def test_session_close_gate_is_independent_of_local_weekday(tmp_path):
    _,_,_,_,_,check=make_context(tmp_path)
    baku=datetime(2026,11,7,0,30,tzinfo=timezone(timedelta(hours=4)))
    assert baku.weekday()==5 and baku.astimezone(timezone.utc)==datetime(2026,11,6,20,30,tzinfo=timezone.utc)
    assert check(now_utc=baku)[0] is True
def test_check_trade_allowed_daily_loss_includes_floating(tmp_path):
    _,_,_,_,allowed,check=make_context(tmp_path); assert allowed[0]
    assert check(pnl_today=-25,open_positions=[{'symbol':'GBPUSD','profit':-6}])[1]=='daily loss limit reached'
def test_check_trade_allowed_weekly_loss_includes_floating(tmp_path):
    _,_,_,_,allowed,check=make_context(tmp_path); assert allowed[0]
    assert check(pnl_week=-75,open_positions=[{'symbol':'GBPUSD','profit':-6}])[1]=='weekly loss limit reached'
def test_check_trade_allowed_max_positions(tmp_path):
    _,_,_,_,allowed,check=make_context(tmp_path); assert allowed[0]
    positions=[{'symbol':f'OTHER{i}','asset_group':'other'} for i in range(10)]
    assert check(open_positions=positions)[1]=='maximum open positions reached'
def test_check_trade_allowed_group_limit(tmp_path):
    _,_,_,_,allowed,check=make_context(tmp_path); assert allowed[0]
    positions=[{'symbol':f'EURUSD{i}','asset_group':'forex'} for i in range(4)]
    assert check(open_positions=positions)[1]=='maximum positions for asset group reached'
def test_check_trade_allowed_duplicate_symbol(tmp_path):
    _,_,_,_,allowed,check=make_context(tmp_path); assert allowed[0]
    assert check(open_positions=[{'symbol':'EURUSD','asset_group':'forex'}])[1]=='symbol already has open position'
def test_check_trade_allowed_symbol_cooldown(tmp_path):
    _,_,_,_,_,check=make_context(tmp_path)
    assert check(symbol_cooldown=True)[1]=='symbol cooldown active'
def test_check_trade_allowed_max_trades_per_symbol_per_day(tmp_path):
    _,_,_,_,_,check=make_context(tmp_path)
    assert check(symbol_trades_today=5)[1]=='maximum trades for symbol today reached'
def test_currency_exposure_blocks_net_direction_over_limit(tmp_path):
    _,_,signal,_,_,check=make_context(tmp_path)
    signal.symbol='GBPAUD'
    positions=[{'symbol':'AUDUSD','asset_group':'forex','direction':'sell','currency_base':'AUD','currency_profit':'USD'}, {'symbol':'EURAUD','asset_group':'forex','direction':'buy','currency_base':'EUR','currency_profit':'AUD'}]
    assert check(open_positions=positions,symbol_spec={'currency_base':'GBP','currency_profit':'AUD'})[1]=='maximum net exposure for AUD reached'
def test_same_underlying_with_broker_suffix_is_blocked(tmp_path):
    _,_,signal,_,_,check=make_context(tmp_path)
    signal.symbol='US500Cash'
    positions=[{'symbol':'US500-DEC26','asset_group':'indices','direction':'sell'}]
    assert check(open_positions=positions,symbol_group='indices')[1]=='underlying already has open position'

def test_non_fx_symbol_without_currency_metadata_does_not_crash(tmp_path):
    _,_,signal,_,_,check=make_context(tmp_path)
    signal.symbol='AAPL'
    assert check(symbol_group='stocks')[0] is True
def test_underlying_group_limit_blocks_correlated_indices(tmp_path):
    _,_,signal,_,_,check=make_context(tmp_path)
    signal.symbol='US500Cash'
    positions=[{'symbol':'US30Cash','asset_group':'indices'}, {'symbol':'US400Cash','asset_group':'indices'}]
    assert check(open_positions=positions,symbol_group='indices')[1]=='maximum positions for underlying group reached'
def test_check_trade_allowed_requires_sl(tmp_path):
    _,_,signal,_,allowed,check=make_context(tmp_path); assert allowed[0]
    signal.sl_price=None
    assert check()[1]=='stop-loss is required'
def test_check_trade_allowed_correct_sl_tp_side(tmp_path):
    _,_,signal,_,allowed,check=make_context(tmp_path); assert allowed[0]
    signal.sl_price=101
    assert check()[1]=='invalid SL/TP side for buy'
def test_check_trade_allowed_minimum_risk_reward(tmp_path):
    _,_,signal,_,allowed,check=make_context(tmp_path); assert allowed[0]
    signal.tp_price=99.5
    assert check()[1]=='invalid SL/TP side for buy'
    signal.tp_price=100.5; signal.sl_price=99
    assert check()[1]=='risk/reward below minimum'
def test_check_trade_allowed_cost_ratio(tmp_path):
    _,_,_,_,allowed,check=make_context(tmp_path); assert allowed[0]
    assert check(cost_estimate={'cost':1})[1]=='cost-to-target ratio too high'
def test_check_trade_allowed_margin_cap(tmp_path):
    _,account,_,_,allowed,check=make_context(tmp_path); assert allowed[0]; account.margin=350
    assert check(required_margin=100)[1]=='margin usage cap exceeded'
