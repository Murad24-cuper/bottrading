import pytest
from src.config import validate_risk_ceilings, LOCKED_RISK_CEILINGS

def base_valid_config():
    return {
        'risk': {
            'risk_per_trade_pct': 0.25,
            'daily_loss_limit_pct': 3.0,
            'weekly_loss_limit_pct': 8.0,
            'max_open_positions': 20,
            'max_positions_per_group': 6,
            'max_margin_usage_pct': 50.0,
            'max_total_open_risk_pct': 5.0,
            'max_cost_to_target_ratio': 0.30,
            'min_risk_reward': 1.2
        }
    }

def test_demo_exploration_risk_per_trade_cannot_exceed_ceiling():
    cfg = base_valid_config()
    cfg['demo_exploration'] = {'risk_per_trade_pct': 0.50}
    with pytest.raises(ValueError, match="demo_exploration.risk_per_trade_pct exceeds locked ceiling"):
        validate_risk_ceilings(cfg)

def test_weekend_max_open_positions_cannot_exceed_ceiling():
    cfg = base_valid_config()
    cfg['weekend'] = {'max_open_positions': 25}
    with pytest.raises(ValueError, match="weekend.max_open_positions exceeds locked ceiling"):
        validate_risk_ceilings(cfg)

def test_valid_demo_and_weekend_pass_validation():
    cfg = base_valid_config()
    cfg['demo_exploration'] = {'risk_per_trade_pct': 0.10, 'max_open_positions': 5}
    cfg['weekend'] = {'risk_per_trade_pct': 0.15, 'max_open_positions': 3}
    validate_risk_ceilings(cfg)  # must not raise
