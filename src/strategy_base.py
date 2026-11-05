from abc import ABC, abstractmethod
import pandas as pd
from .models import Signal

class Strategy(ABC):
    name: str = ''
    required_timeframes: list[str] = []
    params: dict = {}
    @abstractmethod
    def generate_signal(self, symbol: str, candles: dict[str,pd.DataFrame]) -> Signal | None: ...

class DummyStrategy(Strategy):
    name='dummy'; required_timeframes=[]; params={}
    def generate_signal(self, symbol, candles): return None
