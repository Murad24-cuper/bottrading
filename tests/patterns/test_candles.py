import pandas as pd
from src.patterns.candles import detect_candlestick_patterns

def _frame(rows):
    # Last row is a forming bar and must not affect the result.
    return pd.DataFrame([dict(open=o,high=h,low=l,close=c,tick_volume=10) for o,h,l,c in rows])

def test_candle_detector_emits_names_direction_and_timeframe():
    rows=[(11,12,9,10),(11,12,8,9),(8.5,12,8.2,11.5),(10,11,9,10)]
    found=detect_candlestick_patterns(_frame(rows),'M5')
    assert {'name':'bullish_engulfing','direction':'bullish','timeframe':'M5'} in found
    doji=_frame([(10,11,9,10),(10,11,9,10),(10,11,9,10),(10,11,9,10)])
    assert any(item['name']=='doji' for item in detect_candlestick_patterns(doji,'M5'))

def test_candle_detector_ignores_forming_bar():
    rows=[(11,12,9,10),(11,12,8,9),(8.5,12,8.2,11.5),(10,11,9,10)]
    baseline=detect_candlestick_patterns(_frame(rows),'M1')
    rows[-1]=(1e9,1e9,1e9,1e9)
    assert detect_candlestick_patterns(_frame(rows),'M1')==baseline

def test_candle_detector_finds_inside_outside_and_star_patterns():
    inside=_frame([(10,12,8,11),(9,11,8,10),(9.5,10,9,9.8),(10,11,9,10)])
    assert any(x['name']=='inside_bar' for x in detect_candlestick_patterns(inside,'M15'))
    outside=_frame([(10,12,8,11),(9,13,7,12),(10,14,6,12),(10,11,9,10)])
    assert any(x['name']=='outside_bar' for x in detect_candlestick_patterns(outside,'M5'))
    morning=_frame([(12,12.2,7.8,8),(8.4,8.8,8.2,8.5),(8.6,11.2,8.5,11),(10,11,9,10)])
    assert any(x['name']=='morning_star' for x in detect_candlestick_patterns(morning,'M5'))
