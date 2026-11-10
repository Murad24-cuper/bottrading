"""Comprehensive executor tests to raise coverage above 80%."""
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timezone, timedelta
import json
import pytest

from src.executor import Executor
from src.models import Signal


class FakeDB:
    def __init__(self):
        self.events = []; self.open = []; self.inserted = []; self.closed = {}
        self.partial_closes = []; self.partial_deal_tickets = set()
        self.features_updates = {}
    def log_event(self, *args): self.events.append(args)
    def get_open_trades(self): return list(self.open)
    def insert_trade(self, **kwargs): self.inserted.append(kwargs)
    def update_open_trade(self, ticket, **kwargs):
        for r in self.open:
            if int(r.get('ticket', -1)) == int(ticket):
                r.update(kwargs)
        return 1
    def update_trade_close(self, ticket, **kwargs):
        self.closed[ticket] = kwargs
    def get_trade(self, ticket):
        for r in self.open:
            if int(r.get('ticket', -1)) == int(ticket):
                return dict(r)
        return self.closed.get(ticket)
    def get_partial_closes(self, ticket): return self.partial_closes
    def get_partial_deal_tickets(self, ticket): return set(self.partial_deal_tickets)
    def insert_partial_close(self, **kwargs): self.partial_closes.append(kwargs); return 1
    def update_trade_features(self, ticket, features): self.features_updates[ticket] = features


def _info_dict():
    return {'trade_tick_size': .0001, 'trade_tick_value': 1, 'trade_tick_value_loss': 1,
            'volume_min': .01, 'volume_step': .01, 'volume_max': 10}


class FakeMT5:
    POSITION_TYPE_BUY = 0; POSITION_TYPE_SELL = 1
    ORDER_TYPE_BUY = 0; ORDER_TYPE_SELL = 1
    SYMBOL_TRADE_MODE_FULL = 4; SYMBOL_FILLING_FOK = 1; ORDER_FILLING_FOK = 0
    SYMBOL_FILLING_IOC = 2; ORDER_FILLING_IOC = 1; ORDER_FILLING_RETURN = 2
    SYMBOL_TRADE_EXECUTION_MARKET = 2; ACCOUNT_MARGIN_MODE_RETAIL_NETTING = 0
    ACCOUNT_TRADE_MODE_DEMO = 0
    TRADE_ACTION_SLTP = 6; TRADE_ACTION_DEAL = 1; TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_REQUOTE = 10004; TRADE_RETCODE_PRICE_CHANGED = 10020
    ORDER_TIME_GTC = 0
    DEAL_REASON_TP = 5; DEAL_REASON_SL = 4
    DEAL_ENTRY_OUT = 1; DEAL_ENTRY_OUT_BY = 3; DEAL_ENTRY_INOUT = 2; DEAL_ENTRY_IN = 0

    def __init__(self):
        self.orders = []
        self._positions = []
        self._info = self._make_info()
        self._tick = SimpleNamespace(bid=1.101, ask=1.1011)
        self._deals = []

    @staticmethod
    def _make_info():
        info = SimpleNamespace(trade_mode=4, trade_stops_level=0, point=.00001,
                               volume_min=.01, volume_step=.01, volume_max=10,
                               trade_tick_size=.0001, trade_tick_value=1,
                               trade_tick_value_loss=1, trade_tick_value_profit=1,
                               filling_mode=1, trade_exemode=1,
                               trade_commission=None, commission=None)
        info._asdict = lambda: _info_dict()
        return info

    def positions_get(self, *a, **kw): return list(self._positions)
    def symbol_info(self, *a): return self._info
    def symbol_info_tick(self, *a): return self._tick
    def account_info(self):
        return SimpleNamespace(equity=10000, balance=10000, margin=0,
                               margin_free=10000, margin_mode=2, trade_mode=0,
                               margin_level=0, currency='USD', leverage=100)
    def symbols_get(self): return []
    def order_send(self, **request):
        self.orders.append(request)
        return SimpleNamespace(retcode=10009, price=request.get('price', 0),
                               comment='done', position=request.get('position', 100),
                               order=100, deal=100, volume=request.get('volume', 0))
    def last_error(self): return (0, 'ok')
    def order_calc_margin(self, *a): return 50.0
    def history_deals_get(self, *a, **kw): return list(self._deals)
    def copy_rates_from_pos(self, *a): return None


def _make_executor(tmp_path):
    settings = SimpleNamespace(
        root=Path(tmp_path), magic_number=7,
        risk=SimpleNamespace(
            risk_per_trade_pct=1.0, max_hold_minutes=60,
            first_target_r=1.0, scale_out_pct=0.5,
            breakeven_cost_multiplier=1.5,
            momentum_lookback_bars=10, trail_atr_mult=1.5,
            stagnation_minutes=120, stagnation_min_r=0.3,
            max_session_gap_hours=4, no_entry_before_close_minutes=15,
        ),
        allow_real=False, db_path='data/test.db',
        config={
            'account': {'mode': 'demo'},
            'executor': {'deviation_points': 20},
            'risk': {
                'max_hold_extended_minutes': 180,
                'extend_step_minutes': 30,
                'extend_min_score': 0.7,
                'early_exit_enabled': True,
                'early_exit_volume_lookback': 20,
            },
            'scanner': {},
        },
        magic_number_value=7
    )

    class Service:
        def is_tradable(self, symbol): return True, 'tradable'
        def get_asset_group(self, symbol): return 'forex'
        def next_session_close(self, symbol, now, gap):
            return None

    mt5 = FakeMT5(); db = FakeDB()
    return Executor(mt5, settings, db, Service()), mt5, db, settings


def _buy_position(ticket=9, sl=1.099, tp=1.103, volume=0.1, magic=7, price_open=1.1):
    return SimpleNamespace(
        ticket=ticket, identifier=ticket, magic=magic, symbol='EURUSD',
        type=0, price_open=price_open, price_current=1.101,
        sl=sl, tp=tp, volume=volume, profit=10, swap=-0.5, time=1700000000)


def _sell_position(ticket=10, sl=1.103, tp=1.097, volume=0.1, magic=7, price_open=1.1):
    return SimpleNamespace(
        ticket=ticket, identifier=ticket, magic=magic, symbol='EURUSD',
        type=1, price_open=price_open, price_current=1.099,
        sl=sl, tp=tp, volume=volume, profit=10, swap=-0.5, time=1700000000)


# ---- close_position ----

def test_close_position_success(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    pos = _buy_position()
    mt5._positions = [pos]
    db.open = [{'ticket': 9, 'symbol': 'EURUSD', 'direction': 'buy',
                'magic': 7, 'status': 'open', 'initial_volume': 0.1,
                'volume': 0.1, 'open_price': 1.1, 'sl': 1.099, 'tp': 1.103,
                'initial_risk': 0.001, 'scale_out_done': 0, 'features': '{}',
                'peak_favorable_r': 0}]
    res = exe.close_position(9, 'manual')
    assert res.success

def test_close_position_unsupported_reason(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    res = exe.close_position(9, 'badReason')
    assert not res.success and 'unsupported reason' in res.message

def test_close_position_not_found(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    mt5._positions = []
    res = exe.close_position(9, 'manual')
    assert not res.success and 'not found' in res.message

def test_close_position_tick_unavailable(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    mt5._positions = [_buy_position()]
    mt5.symbol_info_tick = lambda *a: None
    res = exe.close_position(9, 'manual')
    assert not res.success and 'tick failed' in res.message.lower()

def test_close_position_order_rejected(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    mt5._positions = [_buy_position()]
    mt5.order_send = lambda **request: SimpleNamespace(retcode=10006, comment='reject')
    res = exe.close_position(9, 'manual')
    assert not res.success


# ---- close_all ----

def test_close_all(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    pos1 = _buy_position(ticket=9)
    pos2 = _sell_position(ticket=10)
    mt5._positions = [pos1, pos2]
    db.open = [
        {'ticket': 9, 'symbol': 'EURUSD', 'direction': 'buy', 'magic': 7,
         'status': 'open', 'initial_volume': 0.1, 'volume': 0.1, 'open_price': 1.1,
         'sl': 1.099, 'tp': 1.103, 'initial_risk': 0.001, 'scale_out_done': 0,
         'features': '{}', 'peak_favorable_r': 0},
        {'ticket': 10, 'symbol': 'EURUSD', 'direction': 'sell', 'magic': 7,
         'status': 'open', 'initial_volume': 0.1, 'volume': 0.1, 'open_price': 1.1,
         'sl': 1.103, 'tp': 1.097, 'initial_risk': 0.003, 'scale_out_done': 0,
         'features': '{}', 'peak_favorable_r': 0},
    ]
    results = exe.close_all('manual')
    assert len(results) == 2


# ---- _close_partial ----

def test_close_partial_success(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    pos = _buy_position(volume=0.10)
    mt5._positions = [pos]
    db.open = [{'ticket': 9, 'symbol': 'EURUSD', 'direction': 'buy', 'magic': 7,
                'status': 'open', 'initial_volume': 0.1, 'volume': 0.1, 'open_price': 1.1,
                'sl': 1.099, 'tp': 1.103, 'initial_risk': 0.001, 'scale_out_done': 0,
                'features': '{}', 'peak_favorable_r': 0}]
    res = exe._close_partial(pos, 0.05)
    assert res.success

def test_close_partial_not_owned(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    pos = _buy_position(magic=999)
    res = exe._close_partial(pos, 0.05)
    assert not res.success

def test_close_partial_bad_volume(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    pos = _buy_position(volume=0.10)
    res = exe._close_partial(pos, 0.20)  # more than open
    assert not res.success

def test_close_partial_no_filling(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    pos = _buy_position(volume=0.10)
    info = mt5._make_info()
    info.filling_mode = 0; info.trade_exemode = 2  # SYMBOL_TRADE_EXECUTION_MARKET => None
    mt5._info = info
    res = exe._close_partial(pos, 0.05)
    assert not res.success and 'filling mode' in res.message.lower()


# ---- modify_sl_tp ----

def test_modify_sl_tp_ticket_not_owned(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    mt5._positions = []
    assert not exe.modify_sl_tp(9, 1.1005, 1.103)

def test_modify_sl_tp_zero_sl_rejected(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    mt5._positions = [_buy_position()]
    assert not exe.modify_sl_tp(9, 0, 1.103)

def test_modify_sl_tp_stop_wrong_side(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    mt5._positions = [_buy_position()]
    # SL above current bid => wrong side for buy
    assert not exe.modify_sl_tp(9, 1.102, 1.103)

def test_modify_sl_tp_broker_rejects(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    mt5._positions = [_buy_position()]
    mt5.order_send = lambda **request: SimpleNamespace(retcode=10006, comment='reject')
    assert not exe.modify_sl_tp(9, 1.1005, 1.103)

def test_modify_sl_tp_db_persist_failure_logged(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    mt5._positions = [_buy_position()]
    db.update_open_trade = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("db down"))
    # Should still succeed (modify was accepted) but log the error
    ok = exe.modify_sl_tp(9, 1.1005, 1.103)
    assert ok
    assert any('persist' in str(e).lower() for e in db.events)


# ---- _asset_group ----

def test_asset_group_detection(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    exe.symbol_service = None
    assert exe._asset_group('XAUUSD') == 'metals'
    assert exe._asset_group('US30') == 'indices'
    assert exe._asset_group('BTCUSD') == 'crypto'
    assert exe._asset_group('WTIUSD') == 'energy'
    assert exe._asset_group('EURUSD') == 'forex'
    assert exe._asset_group('AB') == 'other'


# ---- _filling_mode ----

def test_filling_mode_ioc(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    info = mt5._make_info(); info.filling_mode = 2
    assert exe._filling_mode(info) == mt5.ORDER_FILLING_IOC

def test_filling_mode_return(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    info = mt5._make_info(); info.filling_mode = 0; info.trade_exemode = 99
    assert exe._filling_mode(info) == mt5.ORDER_FILLING_RETURN

def test_filling_mode_market_execution_no_fill(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    info = mt5._make_info(); info.filling_mode = 0; info.trade_exemode = 2
    assert exe._filling_mode(info) is None


# ---- open_trade edge cases ----

def test_open_trade_kill_switch(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    (Path(tmp_path) / 'STOP').write_text('x')
    sig = Signal('EURUSD', 'buy', 'M5', 1.101, 1.1, 1.103, .8, 'test')
    res = exe.open_trade(sig, 0.05)
    assert not res.success and 'kill switch' in res.message.lower()

def test_open_trade_no_sl(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    sig = Signal('EURUSD', 'buy', 'M5', 1.101, None, 1.103, .8, 'test')
    res = exe.open_trade(sig, 0.05)
    assert not res.success

def test_open_trade_no_tp(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    sig = Signal('EURUSD', 'buy', 'M5', 1.101, 1.1, None, .8, 'test')
    res = exe.open_trade(sig, 0.05)
    assert not res.success

def test_open_trade_netting_duplicate(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    mt5.account_info = lambda: SimpleNamespace(
        equity=10000, balance=10000, margin=0, margin_free=10000,
        margin_mode=0, trade_mode=0, margin_level=0, currency='USD', leverage=100)
    mt5._positions = [_buy_position()]
    sig = Signal('EURUSD', 'buy', 'M5', 1.101, 1.1, 1.103, .8, 'test')
    res = exe.open_trade(sig, 0.05)
    assert not res.success and 'netting' in res.message.lower()

def test_open_trade_wrong_direction(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    sig = Signal('EURUSD', 'INVALID', 'M5', 1.101, 1.1, 1.103, .8, 'test')
    res = exe.open_trade(sig, 0.05)
    assert not res.success

def test_open_trade_sell_invalid_stops(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    mt5._tick = SimpleNamespace(bid=1.101, ask=1.1011)
    sig = Signal('EURUSD', 'sell', 'M5', 1.101, 1.1, 1.103, .8, 'test')
    # For sell: need tp < bid < sl, but tp=1.103 > bid => invalid
    res = exe.open_trade(sig, 0.05)
    assert not res.success

def test_open_trade_inside_stops_level(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    mt5._info.trade_stops_level = 1000  # huge stops level
    sig = Signal('EURUSD', 'buy', 'M5', 1.101, 1.1, 1.103, .8, 'test')
    res = exe.open_trade(sig, 0.05)
    assert not res.success and 'trade_stops_level' in res.message

def test_open_trade_db_write_failure_still_returns_success(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    mt5._positions = [_buy_position(sl=1.099)]
    db.insert_trade = lambda **kw: (_ for _ in ()).throw(RuntimeError("db fail"))
    sig = Signal('EURUSD', 'buy', 'M5', 1.101, 1.1, 1.103, .8, 'test')
    res = exe.open_trade(sig, 0.01)
    assert res.success  # position is open on broker


# ---- _close_reason / _sl_was_moved ----

def test_close_reason_tp(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    deal = SimpleNamespace(reason=5, profit=10)
    assert exe._close_reason([deal]) == 'tp'

def test_close_reason_sl_profit(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    deal = SimpleNamespace(reason=4, profit=5)
    assert exe._close_reason([deal]) == 'trail'

def test_close_reason_sl_loss(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    deal = SimpleNamespace(reason=4, profit=-5)
    assert exe._close_reason([deal]) == 'sl'

def test_close_reason_forced(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    deal = SimpleNamespace(reason=999, profit=0)
    assert exe._close_reason([deal], forced='manual') == 'manual'

def test_sl_was_moved():
    assert Executor._sl_was_moved(None) is False
    assert Executor._sl_was_moved({}) is False
    row = {'open_price': 1.1, 'initial_risk': 0.001, 'sl': 1.1005, 'direction': 'buy'}
    assert Executor._sl_was_moved(row) is True
    row2 = {'open_price': 1.1, 'initial_risk': 0.001, 'sl': 1.099, 'direction': 'buy'}
    assert Executor._sl_was_moved(row2) is False


# ---- sync_positions (deeper coverage) ----

def test_sync_recovers_missing_db_row(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    pos = _buy_position(ticket=99)
    mt5._positions = [pos]
    db.open = []
    exe.sync_positions()
    assert any(r['ticket'] == 99 for r in db.inserted)

def test_sync_closes_stale_db_record_no_deals(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    mt5._positions = []  # position gone from broker
    mt5._deals = []
    db.open = [{'ticket': 50, 'symbol': 'EURUSD', 'direction': 'buy', 'magic': 7,
                'status': 'open', 'initial_volume': 0.1, 'volume': 0.1,
                'open_price': 1.1, 'sl': 1.099, 'tp': 1.103, 'initial_risk': 0.001,
                'scale_out_done': 0, 'features': '{}', 'peak_favorable_r': 0}]
    reconciled = exe.sync_positions()
    assert 50 in reconciled
    assert 50 in db.closed

def test_sync_with_deal_history(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    mt5._positions = []
    deal = SimpleNamespace(
        ticket=200, position_id=50, entry=1, reason=5,
        price=1.103, time=1700000000, volume=0.1,
        profit=30, commission=-3.5, swap=-0.5, symbol='EURUSD', comment='tp')
    mt5._deals = [deal]
    db.open = [{'ticket': 50, 'symbol': 'EURUSD', 'direction': 'buy', 'magic': 7,
                'status': 'open', 'initial_volume': 0.1, 'volume': 0.1,
                'open_price': 1.1, 'sl': 1.099, 'tp': 1.103, 'initial_risk': 0.001,
                'scale_out_done': 0, 'features': '{}', 'peak_favorable_r': 0}]
    reconciled = exe.sync_positions()
    assert 50 in reconciled


# ---- enforce_session_close ----

def test_enforce_session_close_no_upcoming(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    mt5._positions = [_buy_position()]
    actions = exe.enforce_session_close()
    assert actions == []

def test_enforce_session_close_upcoming(tmp_path):
    exe, mt5, db, settings = _make_executor(tmp_path)
    now = datetime.now(timezone.utc)
    pos = _buy_position()
    mt5._positions = [pos]
    db.open = [{'ticket': 9, 'symbol': 'EURUSD', 'direction': 'buy', 'magic': 7,
                'status': 'open', 'initial_volume': 0.1, 'volume': 0.1,
                'open_price': 1.1, 'sl': 1.099, 'tp': 1.103, 'initial_risk': 0.001,
                'scale_out_done': 0, 'features': '{}', 'peak_favorable_r': 0}]

    class CloseService:
        def is_tradable(self, s): return True, 'ok'
        def get_asset_group(self, s): return 'forex'
        def next_session_close(self, symbol, n, gap):
            return (now + timedelta(minutes=5), now + timedelta(hours=2))

    exe.symbol_service = CloseService()
    actions = exe.enforce_session_close(now_utc=now)
    assert len(actions) == 1


# ---- _history fallback ----

def test_history_fallback_on_failure(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    call_count = [0]
    def failing_history(*a, **kw):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("not supported")
        return []
    mt5.history_deals_get = failing_history
    result = exe._history(123)
    assert result == []

def test_history_success(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    deal = SimpleNamespace(ticket=1, position_id=123, entry=1, reason=5,
                           price=1.1, time=1700000000, volume=0.1,
                           profit=10, commission=0, swap=0)
    mt5.history_deals_get = lambda *a, **kw: [deal]
    result = exe._history(123)
    assert len(result) == 1


# ---- _record_partial_deal ----

def test_record_partial_deal(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    row = {'ticket': 9, 'symbol': 'EURUSD'}
    deal = SimpleNamespace(ticket=100, entry=1, reason=5, price=1.103,
                           time=1700000000, volume=0.05, profit=15,
                           commission=-1.5, swap=0, comment='tp')
    exe._record_partial_deal(row, deal)
    assert len(db.partial_closes) == 1

def test_record_partial_deal_unknown_comment(tmp_path):
    exe, mt5, db, _ = _make_executor(tmp_path)
    row = {'ticket': 9, 'symbol': 'EURUSD'}
    deal = SimpleNamespace(ticket=100, entry=1, reason=5, price=1.103,
                           time=1700000000, volume=0.05, profit=15,
                           commission=-1.5, swap=0, comment='unknown_reason')
    exe._record_partial_deal(row, deal)
    assert len(db.partial_closes) == 1
