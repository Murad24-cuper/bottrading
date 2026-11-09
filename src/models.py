from dataclasses import dataclass
from typing import Literal

@dataclass
class Signal:
    symbol: str
    direction: Literal['buy', 'sell']
    timeframe: str
    entry_hint: float | None
    sl_price: float | None
    tp_price: float | None
    confidence: float
    strategy_name: str
    reason: str = ''

@dataclass
class TradeResult:
    success: bool
    ticket: int | None
    price: float | None
    volume: float
    retcode: int | None
    message: str

@dataclass
class AccountState:
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float | None
    currency: str
    leverage: int
    trade_mode: object
    margin_mode: object
