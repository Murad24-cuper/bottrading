from src.confluence import apply_confluence

def test_disabled_confluence_is_a_noop_even_with_rules_configured():
    features={'observations':{'key_levels':{'tp_blocked':True},'session':{'session':'off-hours'}}}
    assert apply_confluence(features,'buy',.7,{'enabled':False,'rules':['skip_tp_blocked_by_level','skip_off_hours']})==(True,'',.7)

def test_optional_confluence_rules():
    base={'observations':{'signal_context':{'with_usd_context':False,'with_group_direction':False},'key_levels':{'tp_blocked':True},'chart_patterns':{'M5':[{'state':'confirmed breakout','direction':'bearish'}]},'candlestick_patterns':[],'session':{'session':'off-hours'},'fibonacci':{'M15':{'reacting':True}}}}
    for rule in ('require_with_usd_context','require_with_group_direction','skip_tp_blocked_by_level','skip_against_confirmed_chart_pattern','require_candle_confirmation','skip_off_hours'):
        allowed,reason,confidence=apply_confluence(base,'buy',.7,{'enabled':True,'rules':[rule]})
        assert not allowed and reason.startswith('confluence:') and confidence==.7
    allowed,reason,confidence=apply_confluence(base,'buy',.97,{'enabled':True,'rules':['prefer_fib_reaction']})
    assert allowed and reason=='' and confidence==1.0
