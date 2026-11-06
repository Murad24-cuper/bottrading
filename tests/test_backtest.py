from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
import pandas as pd
from src.backtest.engine import Backtester
from src.models import Signal

class OneBuy:
    name='one_buy'; required_timeframes=['M1']; allowed_groups=['forex']
    def __init__(self,entry=100,sl=99,tp=102): self.sent=False; self.entry=entry; self.sl=sl; self.tp=tp
    def generate_signal(self,symbol,candles):
        if self.sent: return None
        self.sent=True
        return Signal(symbol,'buy','M1',self.entry,self.sl,self.tp,.8,self.name,'test')

def settings(max_hold=120,commission=1):
    risk={'risk_per_trade_pct':.5,'daily_loss_limit_pct':3,'weekly_loss_limit_pct':8,'max_open_positions':10,'max_positions_per_group':4,'max_positions_per_currency':2,'max_positions_per_underlying_group':2,'symbol_cooldown_minutes':30,'max_trades_per_symbol_per_day':5,'max_margin_usage_pct':40,'max_hold_minutes':max_hold,'first_target_r':.7,'scale_out_pct':50,'trail_atr_mult':1.5,'stagnation_minutes':45,'stagnation_min_r':.3,'momentum_lookback_bars':5,'breakeven_cost_multiplier':1.0,'no_entry_before_close_minutes':60,'max_session_gap_hours':6,'min_risk_reward':1,'max_cost_to_target_ratio':.3}
    return SimpleNamespace(config={'risk':risk,'backtest':{'start_equity':1000,'commission_per_lot_per_side':commission,'slippage_points':1,'fallback_spread_points':2}},risk=SimpleNamespace(**risk),root=Path(__file__).parent)

def bars(highs=None,lows=None):
    idx=pd.date_range('2026-01-05T00:00:00Z',periods=4,freq='min')
    highs=highs or [100.5,100.8,103,101]
    lows=lows or [99.5,99.5,98,99.5]
    return pd.DataFrame({'open':[100,100,100,100],'high':highs,'low':lows,'close':[100,100,100,100],'tick_volume':[100]*4,'spread':[2]*4},index=idx)

def specs(): return {'EURUSD':{'asset_group':'forex','point_size':.01,'trade_tick_size':.01,'trade_tick_value':1,'volume_min':.01,'volume_step':.01,'volume_max':10}}

def test_next_bar_buy_fills_at_ask_and_both_hits_use_sl_first():
    result=Backtester(settings(),specs(),1000,[OneBuy()]).run({'EURUSD':{'M1':bars()}})
    assert len(result.trades)==2
    trade=next(item for item in result.trades if item['close_reason']=='sl')
    assert trade['open_price']==100.03
    assert trade['close_price']<trade['tp']
    assert trade['net_profit']==trade['profit']+trade['commission']
    assert trade['commission']<0 and trade['costs']>0
    assert any(item['close_reason']=='partial_tp' for item in result.trades)

def test_time_stop_closes_at_max_hold():
    result=Backtester(settings(max_hold=1),specs(),1000,[OneBuy()]).run({'EURUSD':{'M1':bars([100.5,100.6,100.6,100.6],[99.5,99.5,99.5,99.5])}})
    assert len(result.trades)==1 and result.trades[0]['close_reason']=='time'

def test_default_twenty_minute_horizon_closes_unprotected_trade():
    risk_settings=settings(max_hold=20)
    idx=pd.date_range('2026-01-05T00:00:00Z',periods=25,freq='min')
    frame=pd.DataFrame({'open':[100]*25,'high':[100.5]*25,'low':[99.5]*25,'close':[100]*25,
                        'tick_volume':[100]*25,'spread':[2]*25},index=idx)
    result=Backtester(risk_settings,specs(),1000,[OneBuy()]).run({'EURUSD':{'M1':frame}})
    assert len(result.trades)==1 and result.trades[0]['close_reason']=='time'
    assert result.trades[0]['holding_minutes']==20

def test_ten_dollar_equity_skips_trade_when_min_lot_exceeds_risk():
    result=Backtester(settings(),specs(),10,[OneBuy(entry=100,sl=90,tp=120)]).run({'EURUSD':{'M1':bars([100.5]*4,[99.5]*4)}})
    assert result.trades==[]

def test_scale_out_records_partial_take_profit():
    frame=bars([100.5,100.8,101,101],[99.5,99.5,99.5,99.5])
    result=Backtester(settings(),specs(),1000,[OneBuy()]).run({'EURUSD':{'M1':frame}})
    partials=[trade for trade in result.trades if trade['close_reason']=='partial_tp']
    assert len(partials)==1
    assert 0<partials[0]['volume']<sum(trade['volume'] for trade in result.trades)

def test_future_bar_changes_cannot_change_earlier_signal_fill():
    original=bars(); changed=original.copy(); changed.loc[changed.index[2]:,'close']=10000; changed.loc[changed.index[2]:,'high']=10001
    first=Backtester(settings(),specs(),1000,[OneBuy()]).run({'EURUSD':{'M1':original}})
    second=Backtester(settings(),specs(),1000,[OneBuy()]).run({'EURUSD':{'M1':changed}})
    assert first.trades[0]['open_time']==second.trades[0]['open_time']
    assert first.trades[0]['open_price']==second.trades[0]['open_price']
