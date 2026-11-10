import pytest

from src.brain.ood import fit_ood_guard,is_out_of_distribution
from src.brain.decide import decide


def test_ood_threshold_uses_validation_distance_and_abstains_on_far_query():
    train=[[0.0,0.0],[1.0,1.0]]
    validation=[[0.1,0.0],[1.1,1.0],[0.0,0.2]]
    guard=fit_ood_guard(train,validation,percentile=100)
    assert guard['validation_count']==3 and guard['training_count']==2
    assert not is_out_of_distribution([0.1,0.1],train,guard)
    assert is_out_of_distribution([10.0,10.0],train,guard)


def test_brain_decision_abstains_for_out_of_distribution_market():
    result=decide({'score':1.0,'blocking_failures':[]},
                  {'probability':0.9,'avg_win_r':1.0,'avg_loss_r':1.0,'out_of_distribution':True},
                  {'min_checklist':0.5,'min_probability':0.5,'min_ev_r':0.0})
    assert not result['accepted']
    assert 'out of distribution; brain abstains' in result['reasons']


def test_ood_guard_rejects_empty_or_dimension_mismatched_inputs():
    with pytest.raises(ValueError):
        fit_ood_guard([],[[0.0]])
    guard=fit_ood_guard([[0.0]],[[0.1]])
    assert is_out_of_distribution([0.0,1.0],[[0.0,1.0]],guard)
