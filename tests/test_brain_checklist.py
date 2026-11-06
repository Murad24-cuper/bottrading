from src.brain.checklist import evaluate

def test_checklist_is_weighted_and_blocks_confirmed_opposing_pattern():
    features={'M15':{'ema_slope':1,'support_distance_atr':.5,'rsi':55,'roc':1,'atr_pct':.01,'atr_pct_baseline':.01},
              'H1':{'ema_slope':.5},'M5':{'rsi':55,'roc':1}}
    obs={'chart_patterns':{'M5':[{'name':'double_top','direction':'bearish','state':'confirmed'}]},'session':{'range':1}}
    result=evaluate(features,'buy',{'trend':2},obs)
    assert result['items']['trend'] and result['score']>0
    assert result['blocking_failures']==['confirmed opposing chart pattern']
