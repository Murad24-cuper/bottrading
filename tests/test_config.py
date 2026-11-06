from pathlib import Path
from src import config as config_module

def test_default_config_loads_for_offline_work(monkeypatch):
    monkeypatch.setattr(config_module,'load_dotenv',lambda *args,**kwargs:False)
    root=Path(__file__).resolve().parents[1]
    settings=config_module.load_settings(root/'config.yaml',env_path='deliberately-not-loaded.env',require_credentials=False)
    assert settings.config['account']['mode']=='demo'
    assert settings.risk.max_hold_minutes==10
    assert settings.risk.first_target_r==0.8
    assert settings.risk.scale_out_pct==50
    assert settings.risk.risk_per_trade_pct==0.25
    assert settings.config['scanner']['min_confidence']==0.6
    assert settings.config['scanner']['require_mtf_agreement'] is True
    assert settings.config['risk']['min_risk_reward']==1.3
    assert settings.risk.no_entry_before_close_minutes==60
    assert settings.risk.max_session_gap_hours==6
    assert settings.config['scanner']['top_movers']==40
    assert settings.config['scanner']['max_seconds_per_cycle']>0
    assert settings.config['history']['ranges_months']['M1']==3

def test_config_rejects_zero_risk_percentage(tmp_path,monkeypatch):
    import yaml
    monkeypatch.setattr(config_module,'load_dotenv',lambda *args,**kwargs:False)
    root=Path(__file__).resolve().parents[1]
    data=yaml.safe_load((root/'config.yaml').read_text(encoding='utf-8'))
    data['risk']['risk_per_trade_pct']=0
    path=tmp_path/'config.yaml'; path.write_text(yaml.safe_dump(data),encoding='utf-8')
    try: config_module.load_settings(path,env_path='absent.env',require_credentials=False)
    except ValueError as exc: assert 'risk.risk_per_trade_pct' in str(exc)
    else: raise AssertionError('zero risk percentage was accepted')
