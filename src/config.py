"""Typed configuration loading and validation."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os
import math
import yaml
from dotenv import load_dotenv

@dataclass(frozen=True)
class RiskSettings:
    risk_per_trade_pct: float
    daily_loss_limit_pct: float
    weekly_loss_limit_pct: float
    max_open_positions: int
    max_positions_per_group: int
    max_margin_usage_pct: float
    max_hold_minutes: int
    min_risk_reward: float
    max_cost_to_target_ratio: float
    max_spread_points: dict[str, float]
    no_new_trades_friday_after_utc: str
    close_all_friday_utc: str

@dataclass(frozen=True)
class Settings:
    config: dict[str, Any]
    mt5_login: int | None
    mt5_password: str
    mt5_server: str
    mt5_path: str | None
    allow_real: bool
    root: Path
    risk: RiskSettings
    @property
    def magic_number(self) -> int: return int(self.config['magic_number'])
    @property
    def db_path(self) -> Path:
        path=Path(self.config['db_path'])
        return path if path.is_absolute() else self.root/path

def _clock(value: object, key: str) -> str:
    import re
    if not isinstance(value,str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',value):
        raise ValueError(f'risk.{key} must be a UTC time in HH:MM format')
    return value

def load_settings(config_path: str | Path='config.yaml', env_path: str | Path='.env', require_credentials: bool=True) -> Settings:
    path=Path(config_path).resolve()
    if not path.is_file(): raise ValueError(f'Configuration file not found: {path}')
    load_dotenv(path.parent/Path(env_path),override=False)
    try: config=yaml.safe_load(path.read_text(encoding='utf-8'))
    except (OSError,yaml.YAMLError) as exc: raise ValueError(f'Cannot load config.yaml: {exc}') from exc
    if not isinstance(config,dict): raise ValueError('config.yaml must contain a YAML mapping')
    required={'account','risk','universe','timeframes','magic_number','executor','strategies','loop','scanner','history','backtest','db_path'}
    missing=required-config.keys()
    if missing: raise ValueError(f'config.yaml is missing keys: {", ".join(sorted(missing))}')
    for section in ('account','risk','universe','loop','scanner','history','backtest'):
        if not isinstance(config[section],dict): raise ValueError(f'{section} must be a mapping')
    if config['account'].get('mode') not in {'demo','real'}: raise ValueError('account.mode must be demo or real')
    raw=config['risk']
    numeric={'risk_per_trade_pct':(0,100),'daily_loss_limit_pct':(0,100),'weekly_loss_limit_pct':(0,100),'max_margin_usage_pct':(0,100),'min_risk_reward':(0,None),'max_cost_to_target_ratio':(0,None)}
    for key,(low,high) in numeric.items():
        value=raw.get(key)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=low or (high is not None and value>high):
            raise ValueError(f'risk.{key} must be > {low}' + (f' and <= {high}' if high else ''))
    for key in ('max_open_positions','max_positions_per_group','max_hold_minutes'):
        if type(raw.get(key)) is not int or raw[key]<=0: raise ValueError(f'risk.{key} must be a positive integer')
    spreads=raw.get('max_spread_points')
    if not isinstance(spreads,dict) or any(not isinstance(v,(int,float)) or v<0 for v in spreads.values()): raise ValueError('risk.max_spread_points must map symbols to non-negative numbers')
    risk=RiskSettings(float(raw['risk_per_trade_pct']),float(raw['daily_loss_limit_pct']),float(raw['weekly_loss_limit_pct']),raw['max_open_positions'],raw['max_positions_per_group'],float(raw['max_margin_usage_pct']),raw['max_hold_minutes'],float(raw['min_risk_reward']),float(raw['max_cost_to_target_ratio']),spreads,_clock(raw.get('no_new_trades_friday_after_utc'),'no_new_trades_friday_after_utc'),_clock(raw.get('close_all_friday_utc'),'close_all_friday_utc'))
    credentials={key:os.getenv(key,'').strip() for key in ('MT5_LOGIN','MT5_PASSWORD','MT5_SERVER')}
    if require_credentials:
        for key,value in credentials.items():
            if not value: raise ValueError(f'Missing {key}; set it in .env before connecting to MT5')
    login=credentials['MT5_LOGIN']
    if login and not login.isdigit(): raise ValueError('MT5_LOGIN must be a numeric account number')
    if not isinstance(config['universe'].get('include_groups'),list) or not isinstance(config['universe'].get('exclude_symbols'),list) or not isinstance(config['universe'].get('symbol_aliases'),dict): raise ValueError('universe include_groups, exclude_symbols and symbol_aliases must be configured')
    if not isinstance(config['timeframes'],list) or not config['timeframes']: raise ValueError('timeframes must be a non-empty list')
    if any(tf not in {'M1','M5','M15','H1'} for tf in config['timeframes']): raise ValueError('timeframes may contain only M1, M5, M15 and H1')
    if type(config['magic_number']) is not int or config['magic_number']<=0: raise ValueError('magic_number must be a positive integer')
    if not isinstance(config['executor'],dict) or type(config['executor'].get('deviation_points')) is not int or config['executor']['deviation_points']<0: raise ValueError('executor.deviation_points must be a non-negative integer')
    scanner=config['scanner']
    for key in ('max_seconds_per_cycle','max_candidates','candle_count'):
        if not isinstance(scanner.get(key),(int,float)) or scanner[key]<=0: raise ValueError(f'scanner.{key} must be > 0')
    if not isinstance(scanner.get('min_score'),(int,float)): raise ValueError('scanner.min_score must be numeric')
    point_sizes=scanner.get('timeframe_point_sizes',{})
    if not isinstance(point_sizes,dict) or any(not isinstance(value,(int,float)) or value<=0 for value in point_sizes.values()): raise ValueError('scanner.timeframe_point_sizes must map symbols to positive point sizes')
    if not isinstance(config['loop'].get('interval_seconds'),(int,float)) or config['loop']['interval_seconds']<=0: raise ValueError('loop.interval_seconds must be > 0')
    history=config['history']
    if not isinstance(history.get('ranges_months'),dict) or any(type(v) is not int or v<=0 for v in history['ranges_months'].values()): raise ValueError('history.ranges_months must map timeframes to positive month counts')
    if not isinstance(history.get('liquid_aliases'),list) or not history['liquid_aliases']: raise ValueError('history.liquid_aliases must be a non-empty list')
    backtest=config['backtest']
    for key in ('start_equity','in_sample_pct','walk_forward_optimize_months','walk_forward_test_months'):
        if not isinstance(backtest.get(key),(int,float)) or backtest[key]<=0: raise ValueError(f'backtest.{key} must be > 0')
    if backtest['in_sample_pct']>=1: raise ValueError('backtest.in_sample_pct must be < 1')
    for key in ('commission_per_lot_per_side','slippage_points','fallback_spread_points'):
        if not isinstance(backtest.get(key),(int,float)) or backtest[key]<0: raise ValueError(f'backtest.{key} must be >= 0')
    if not isinstance(config['strategies'],dict): raise ValueError('strategies must be a mapping')
    for name,entry in config['strategies'].items():
        if not isinstance(entry,dict) or type(entry.get('enabled')) is not bool or not isinstance(entry.get('groups'),list) or not isinstance(entry.get('timeframes'),list) or not isinstance(entry.get('params'),dict): raise ValueError(f'strategies.{name} must define enabled, groups, timeframes and params')
    return Settings(config,int(login) if login else None,credentials['MT5_PASSWORD'],credentials['MT5_SERVER'],os.getenv('MT5_PATH') or None,os.getenv('ALLOW_REAL','false').lower()=='true',path.parent,risk)
