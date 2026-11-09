from abc import ABC, abstractmethod
import pandas as pd
from .models import Signal

class Strategy(ABC):
    name: str = ''
    required_timeframes: list[str] = []
    params: dict = {}
    def _skip(self,reason):
        self.last_skip_reason=reason
        counts=getattr(self,'diagnostic_counts',None)
        if counts is None: self.diagnostic_counts=counts={}
        counts[reason]=counts.get(reason,0)+1
        return None
    @abstractmethod
    def generate_signal(self, symbol: str, candles: dict[str,pd.DataFrame]) -> Signal | None: ...
