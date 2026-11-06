from datetime import datetime, timezone
from types import SimpleNamespace

from src.symbols import SymbolService, is_dated_future, underlying_group, underlying_key


class FakeMT5:
    SYMBOL_TRADE_MODE_FULL = 4

    def __init__(self, names):
        now = datetime.now(timezone.utc).timestamp()
        self.rows = [SimpleNamespace(name=name) for name in names]
        self.ticks = {name: SimpleNamespace(time=int(now), time_msc=int(now * 1000), bid=1.0, ask=1.001) for name in names}

    def symbols_get(self):
        return self.rows

    def symbol_info(self, name):
        return SimpleNamespace(name=name, path='Indices\\US', trade_mode=4, point=0.001, select=False)

    def symbol_select(self, name, enable):
        return True

    def symbol_info_tick(self, name):
        return self.ticks.get(name, next(iter(self.ticks.values())))

    def last_error(self):
        return (0, 'ok')


def make_service(names, exclude_dated=True):
    mt5 = FakeMT5(names)
    config = {'universe': {'include_groups': ['indices'], 'exclude_symbols': [], 'exclude_dated_futures': exclude_dated, 'symbol_aliases': {}}, 'history': {'liquid_aliases': []}}
    settings = SimpleNamespace(config=config, risk=SimpleNamespace(max_spread_points={}))
    return SymbolService(mt5, settings)


def test_underlying_normalizes_cash_and_expiry_suffixes():
    assert underlying_key('US500Cash') == 'US500'
    assert underlying_key('US500-DEC26') == 'US500'
    assert underlying_key('EURUSDm') == 'EURUSD'


def test_dated_futures_are_excluded_from_universe_by_default():
    service = make_service(['US500Cash', 'US500-DEC26', 'US400Cash'])
    assert service.get_universe() == ['US500Cash', 'US400Cash']
    assert is_dated_future('US500-DEC26')
    assert underlying_group('US400Cash', 'indices') == 'us_indices'


def test_dated_futures_can_be_included_when_explicitly_configured():
    service = make_service(['US500-DEC26'], exclude_dated=False)
    assert service.get_universe() == ['US500-DEC26']
