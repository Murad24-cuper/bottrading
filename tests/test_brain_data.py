from src.brain.data import select_universe

def test_universe_selection_applies_group_quotas_and_cost_score():
    rows=[{'symbol':'EURUSD','asset_group':'forex','spread_price':.1,'atr_price':1,'activity':10},
          {'symbol':'GBPUSD','asset_group':'forex','spread_price':.2,'atr_price':1,'activity':100},
          {'symbol':'US30Cash','asset_group':'indices','spread_price':.1,'atr_price':1,'activity':1},
          {'symbol':'X','asset_group':'stocks','spread_price':3,'atr_price':1,'activity':1}]
    picked=select_universe(rows,{'forex':1,'indices':1,'stocks':1},3)
    assert {row['asset_group'] for row in picked}=={'forex','indices','stocks'}
    assert picked[0]['symbol']=='EURUSD'
