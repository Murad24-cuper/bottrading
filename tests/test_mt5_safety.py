import sys
from types import SimpleNamespace

import pytest

from src.mt5_client import MT5Client


def client_settings(mode,allow_real):
    return SimpleNamespace(mt5_path=None,mt5_login=123456,mt5_password='private-test-value',mt5_server='demo-server',allow_real=allow_real,config={'account':{'mode':mode}})

def fake_mt5(trade_mode):
    return SimpleNamespace(ACCOUNT_TRADE_MODE_DEMO=0,ACCOUNT_MARGIN_MODE_RETAIL_HEDGING=2,initialize=lambda *a:True,login=lambda *a,**k:True,account_info=lambda:SimpleNamespace(trade_mode=trade_mode,margin_mode=2,login=123456),terminal_info=lambda:SimpleNamespace(trade_allowed=True),shutdown=lambda:None,last_error=lambda:(0,'ok'))

def test_real_login_requires_both_real_mode_and_explicit_allow_real(monkeypatch):
    module=fake_mt5(1); monkeypatch.setitem(sys.modules,'MetaTrader5',module)
    with pytest.raises(RuntimeError,match='account.mode=real'):
        MT5Client(client_settings('demo',True)).connect()

def test_real_login_allowed_only_with_both_explicit_guards(monkeypatch,caplog):
    module=fake_mt5(1); monkeypatch.setitem(sys.modules,'MetaTrader5',module)
    client=MT5Client(client_settings('real',True)).connect()
    assert client.mt5 is module
    assert 'private-test-value' not in caplog.text
