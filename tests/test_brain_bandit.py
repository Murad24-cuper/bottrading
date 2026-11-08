import random

from src.brain.bandit import arm_key, sample_arm_priorities


def test_bandit_shares_are_bounded_and_sum_to_one():
    arms=[arm_key(f's{i}','forex','London') for i in range(4)]
    shares=sample_arm_priorities([],arms,random.Random(7))
    assert set(shares)==set(arms)
    assert all(.05<=value<=.40 for value in shares.values())
    assert sum(shares.values())<=1.0


def test_recent_winners_raise_expected_priority_without_touching_risk():
    good=arm_key('trend','forex','London'); bad=arm_key('breakout','forex','London')
    history=[{'arm':good,'win':True} for _ in range(30)]+[{'arm':bad,'win':False} for _ in range(30)]
    shares=sample_arm_priorities(history,[good,bad],random.Random(2))
    assert shares[good]>shares[bad]
