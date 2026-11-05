from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os
import yaml
from dotenv import load_dotenv

@dataclass(frozen=True)
class Settings:
    config: dict[str, Any]
    mt5_login: int | None
    mt5_password: str
    mt5_server: str
    mt5_path: str | None
    allow_real: bool
    root: Path
    @property
    def risk(self): return self.config['risk']
    @property
    def magic_number(self): return int(self.config['magic_number'])
    @property
    def db_path(self):
        p = Path(self.config['db_path'])
        return p if p.is_absolute() else self.root / p

def load_settings(config_path='config.yaml', env_path='.env') -> Settings:
    path = Path(config_path).resolve()
    load_dotenv(path.parent / env_path)
    try: cfg = yaml.safe_load(path.read_text(encoding='utf-8'))
    except Exception as e: raise ValueError(f'Cannot load config {path}: {e}') from e
    required = {'account','risk','universe','timeframes','magic_number','loop','db_path'}
    if not isinstance(cfg, dict) or required - cfg.keys(): raise ValueError(f'Invalid config; missing keys: {sorted(required - (cfg or {}).keys())}')
    risk = cfg['risk']
    for key in ('risk_per_trade_pct','daily_loss_limit_pct','weekly_loss_limit_pct','max_margin_usage_pct','min_risk_reward','max_cost_to_target_ratio'):
        if not isinstance(risk.get(key),(int,float)) or risk[key] <= 0: raise ValueError(f'risk.{key} must be > 0')
    for key in ('max_open_positions','max_positions_per_group','max_hold_minutes'):
        if not isinstance(risk.get(key),int) or risk[key] <= 0: raise ValueError(f'risk.{key} must be a positive integer')
    if cfg['account'].get('mode') not in ('demo','real'): raise ValueError('account.mode must be demo or real')
    login = os.getenv('MT5_LOGIN','').strip()
    if login and not login.isdigit(): raise ValueError('MT5_LOGIN must be numeric')
    return Settings(cfg,int(login) if login else None,os.getenv('MT5_PASSWORD',''),os.getenv('MT5_SERVER',''),os.getenv('MT5_PATH') or None,os.getenv('ALLOW_REAL','false').lower()=='true',path.parent)
