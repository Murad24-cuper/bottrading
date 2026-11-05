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
class TradeRequest:
    symbol: str
    direction: str
    volume: float
    sl: float
    tp: float
    magic: int
    comment: str = ''
    deviation: int = 20

@dataclass
class TradeResult:
    success: bool
    ticket: int | None
    price: float | None
    volume: float
    retcode: int | None
    message: str

@dataclass
class Position:
    ticket: int
    symbol: str
    direction: str
    volume: float
    open_time: object
    open_price: float
    sl: float | None
    tp: float | None
    profit: float = 0
    magic: int = 0
    swap: float = 0

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
