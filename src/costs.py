"""Shared, account-currency round-trip cost arithmetic for offline diagnostics."""
from __future__ import annotations

from collections import defaultdict
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


def estimate_round_trip_cost(*, spread_price: float, stop_distance: float,
                             tick_size: float, tick_value: float, volume: float,
                             commission_per_lot_round_trip: float | None,
                             slippage_points: float = 0.0, point_size: float = 0.0,
                             delay_price: float = 0.0) -> dict:
    """Return estimated account-currency cost and cost/stop risk.

    Commission is explicitly marked unknown when no broker evidence is supplied;
    consumers must not treat an unknown estimate as a complete cost model.
    """
    values=(spread_price,stop_distance,tick_size,tick_value,volume,slippage_points,point_size,delay_price)
    if any(not math.isfinite(float(v)) or float(v)<0 for v in values):
        raise ValueError("cost model inputs must be finite and non-negative")
    if tick_size<=0 or tick_value<=0 or volume<=0 or stop_distance<=0:
        raise ValueError("tick size/value, volume and stop distance must be positive")
    money_per_price=tick_value/tick_size
    commission_known=commission_per_lot_round_trip is not None
    commission=float(commission_per_lot_round_trip or 0.0)*volume
    if commission<0 or not math.isfinite(commission):
        raise ValueError("round-trip commission must be finite and non-negative")
    slip_price=2*slippage_points*point_size
    price_cost=spread_price+slip_price+delay_price
    spread_slippage=price_cost*money_per_price*volume
    total=spread_slippage+commission
    risk=stop_distance*money_per_price*volume
    return {"cost":total,"spread_slippage":spread_slippage,"commission":commission,
            "commission_known":commission_known,"cost_stop_ratio":total/risk,
            "risk_money":risk}


def evaluate_live_cost_gate(*, samples: int, min_samples: int,
                            median_spread_price: float | None,
                            symbol_info_spread_points: float,
                            point_size: float, fallback_spread_multiplier: float,
                            stop_distance: float, tick_size: float,
                            tick_value: float, volume: float,
                            commission_per_lot_round_trip: float | None,
                            slippage_points: float, max_stop_ratio: float,
                            one_bar_delay: bool = False) -> tuple[dict, str]:
    """Evaluate a live entry using a sampled spread or conservative live fallback.

    New broker symbols/accounts cannot have enough historical spread samples.
    For those cells, use the current MT5 symbol_info spread with the configured
    conservative multiplier instead of failing calibration. Commission and
    two-sided slippage still enter the same stop-risk calculation.
    """
    if int(samples) >= int(min_samples):
        if median_spread_price is None:
            return {"spread_source": "sample_median"}, "cost map spread unavailable"
        spread_price=float(median_spread_price)
        spread_source="sample_median"
    else:
        if not math.isfinite(float(symbol_info_spread_points)) or float(symbol_info_spread_points)<=0:
            return {"spread_source": "symbol_info_fallback"}, "live symbol_info spread unavailable"
        if not math.isfinite(float(point_size)) or float(point_size)<=0:
            return {"spread_source": "symbol_info_fallback"}, "cost map contract data unavailable"
        multiplier=float(fallback_spread_multiplier)
        if not math.isfinite(multiplier) or multiplier<1.25:
            raise ValueError("fallback spread multiplier cannot be below 1.25")
        spread_price=float(symbol_info_spread_points)*float(point_size)*multiplier
        spread_source="symbol_info_fallback"
    if commission_per_lot_round_trip is None:
        return {"spread_source": spread_source, "spread_price": spread_price}, "cost map commission unknown"
    if one_bar_delay:
        return {"spread_source": spread_source, "spread_price": spread_price}, "one-bar delay cost unavailable"
    try:
        estimate=estimate_round_trip_cost(spread_price=spread_price,
            stop_distance=stop_distance,tick_size=tick_size,tick_value=tick_value,
            volume=volume,commission_per_lot_round_trip=commission_per_lot_round_trip,
            slippage_points=slippage_points,point_size=point_size)
    except (TypeError,ValueError,ZeroDivisionError):
        return {"spread_source": spread_source, "spread_price": spread_price}, "cost map contract data unavailable"
    result={**estimate,"spread_source":spread_source,"spread_price":spread_price}
    reason="median hourly costs exceed 10% of stop risk" if estimate["cost_stop_ratio"]>=float(max_stop_ratio) else ""
    return result,reason


def hourly_cost_cells(frames: dict[tuple[str,str],'pd.DataFrame'], specs: dict[str,dict],
                      commission_per_lot_round_trip: dict[str,float] | None = None,
                      slippage_points: float = 0.0) -> list[dict]:
    """Build symbol/timeframe/UTC-hour median cost cells from OHLC spread bars.

    Each frame needs a UTC DatetimeIndex and `spread`; specs need point/tick
    sizing and an ATR stop multiplier can be supplied as ``stop_mult``.
    Missing contract data is omitted, never imputed.
    """
    commission_per_lot_round_trip=commission_per_lot_round_trip or {}
    cells=[]
    for (symbol,timeframe),frame in frames.items():
        spec=specs.get(symbol,{})
        point=float(spec.get("point_size",spec.get("point",0)) or 0)
        tick_size=float(spec.get("trade_tick_size",spec.get("tick_size",0)) or 0)
        tick_value=float(spec.get("trade_tick_value",spec.get("tick_value",0)) or 0)
        if not point or not tick_size or not tick_value or "spread" not in frame or frame.empty:
            continue
        import pandas as pd
        index=pd.to_datetime(frame.index,utc=True)
        spread=pd.to_numeric(frame["spread"],errors="coerce")*point
        from .indicators import atr
        atr_values=atr(frame)
        stop_distance=atr_values*float(spec.get("stop_mult",2.0))
        rows=defaultdict(list)
        for i,hour in enumerate(index.hour):
            if not math.isfinite(float(spread.iloc[i])) or not math.isfinite(float(stop_distance.iloc[i])) or stop_distance.iloc[i]<=0:
                continue
            estimate=estimate_round_trip_cost(spread_price=float(spread.iloc[i]),
                stop_distance=float(stop_distance.iloc[i]),tick_size=tick_size,tick_value=tick_value,
                volume=1.0,commission_per_lot_round_trip=commission_per_lot_round_trip.get(symbol),
                slippage_points=slippage_points,point_size=point)
            rows[int(hour)].append(estimate["cost_stop_ratio"])
        for hour,ratios in sorted(rows.items()):
            cells.append({"symbol":symbol,"timeframe":timeframe,"hour_utc":hour,
                          "samples":len(ratios),"median_cost_stop_ratio":float(pd.Series(ratios).median()),
                          "commission_known":symbol in commission_per_lot_round_trip,
                          "passes_10pct":symbol in commission_per_lot_round_trip and float(pd.Series(ratios).median())<.10})
    return cells
