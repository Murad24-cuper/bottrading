from src.risk import calc_volume

SPEC={'tick_value':1,'tick_size':.0001,'volume_min':.01,'volume_step':.01,'volume_max':10}
def test_volume_normal(): assert calc_volume(1000,.5,1.1,1.09,SPEC)[0] > 0
def test_tiny_account_refused(): assert calc_volume(10,.5,1.1,1.09,SPEC) == (0,'min lot exceeds risk')
def test_step_rounds_down(): assert calc_volume(150,.5,1.1,1.09,SPEC)[0] == .07
def test_volume_max_cap(): assert calc_volume(100000,50,1.1,1.09,{**SPEC,'volume_max':.2})[0] == .2
