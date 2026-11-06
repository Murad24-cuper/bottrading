import json
from src.analysis.feature_impact import analyze_feature_impact

def test_feature_report_requires_30_trades_and_ci_excluding_zero():
    rows=[]
    for i in range(40):
        rows.append({'profit':1 if i<35 else -1,'commission':0,'swap':0,'features':json.dumps({'observations':{'with_usd_context':i<35}})})
    result=analyze_feature_impact(rows,bootstrap_samples=300,seed=3)
    positive=next(x for x in result if x['feature']=='observations.with_usd_context=true')
    assert positive['trades']==35 and positive['meaningful'] is True
    assert positive['ci90_low']>0

def test_small_feature_group_is_never_marked_proven():
    rows=[{'profit':1,'features':json.dumps({'pattern':'x'})} for _ in range(29)]
    result=analyze_feature_impact(rows,bootstrap_samples=50)
    assert all(x['meaningful'] is False and x['ci90_low'] is None for x in result)
