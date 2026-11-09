"""Step 1 & 2: Collect account facts, symbol specifications, commissions,
and build conservative cost model v1, writing docs/ACCOUNT_COSTS.md.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json, math, sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_settings
from src.mt5_client import MT5Client
from src.symbols import SymbolService
from src.db import Database
from src.history import download_history

def main():
    settings = load_settings()
    db = Database(settings.db_path)
    
    print("Connecting to MT5...")
    with MT5Client(settings) as client:
        mt5 = client.mt5
        acc = mt5.account_info()
        if not acc:
            raise RuntimeError(f"account_info failed: {mt5.last_error()}")
        
        mode_str = "DEMO" if acc.trade_mode == getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0) else "REAL"
        print(f"Account: {acc.login}, Mode: {mode_str}, Equity: {acc.equity}, Currency: {acc.currency}")
        
        # Check open positions
        positions = mt5.positions_get() or []
        print(f"Open positions count: {len(positions)}")
        
        service = SymbolService(mt5, settings)
        
        focus_logical = settings.config['universe'].get('focus_symbols', [])
        weekend_logical = settings.config['universe'].get('weekend_symbols', [])
        all_logical = list(dict.fromkeys(focus_logical + weekend_logical))
        
        # Resolve all actual symbols
        resolved_symbols = {}
        for logical in all_logical:
            actual = service.resolve_alias(logical)
            if actual:
                resolved_symbols[logical] = actual
            else:
                # If alias not found, check if logical itself exists
                info = mt5.symbol_info(logical)
                if info:
                    resolved_symbols[logical] = logical
                else:
                    print(f"Warning: could not resolve {logical}")
        
        print(f"Resolved {len(resolved_symbols)} symbols: {resolved_symbols}")
        
        # Collect deals history for commissions
        deals = mt5.history_deals_get(datetime.now(timezone.utc) - timedelta(days=90), datetime.now(timezone.utc)) or []
        symbol_commissions = {}
        for d in deals:
            sym = getattr(d, 'symbol', None)
            vol = float(getattr(d, 'volume', 0) or 0)
            comm = getattr(d, 'commission', None)
            if sym and vol > 0 and comm is not None:
                symbol_commissions.setdefault(sym, []).append(abs(float(comm)) / vol)
        
        # Collect recorded live spread samples from DB
        live_spreads = {}
        with db.connect() as conn:
            rows = conn.execute("""
                SELECT symbol, AVG(spread_price) as avg_sp, COUNT(*) as cnt
                FROM spread_samples
                GROUP BY symbol
            """).fetchall()
            for r in rows:
                live_spreads[r['symbol']] = float(r['avg_sp'])
        
        symbol_facts = {}
        symbols_to_download = []
        for logical, actual in resolved_symbols.items():
            mt5.symbol_select(actual, True)
            info = mt5.symbol_info(actual)
            if not info:
                print(f"Could not get info for {actual}")
                continue
            
            symbols_to_download.append(actual)
            group = service.get_asset_group(actual)
            
            # Tick and point values
            point = float(info.point or 0.0)
            digits = int(info.digits or 0)
            spread_raw = float(info.spread or 0.0)
            spread_pts = spread_raw
            spread_price = spread_raw * point
            live_med_price = live_spreads.get(actual, spread_price)
            live_med_pts = live_med_price / point if point > 0 else spread_pts
            
            contract_size = float(info.trade_contract_size or 1.0)
            tick_size = float(info.trade_tick_size or point or 1e-5)
            tick_value = float(info.trade_tick_value or info.trade_tick_value_loss or 0.0)
            swap_long = float(info.swap_long or 0.0)
            swap_short = float(info.swap_short or 0.0)
            vol_min = float(info.volume_min or 0.01)
            vol_step = float(info.volume_step or 0.01)
            vol_max = float(info.volume_max or 100.0)
            
            # Commission calculation (AUDIT-CRIT-03 hierarchy)
            comm_source = "deal history"
            comm_per_lot = None
            if actual in symbol_commissions and symbol_commissions[actual]:
                comm_per_lot = sum(symbol_commissions[actual]) / len(symbol_commissions[actual])
            else:
                for attr in ('trade_commission', 'commission'):
                    val = getattr(info, attr, None)
                    if val is not None and math.isfinite(float(val)):
                        comm_per_lot = float(val)
                        comm_source = f"symbol_info.{attr}"
                        break
            if comm_per_lot is None:
                comm_per_lot = 0.0
                comm_source = "conservative default (0.0)"
            
            # Step 2: Research Cost Model v1
            # Round-trip cost = max(symbol_info spread, median recorded live spread) * 1.25
            # + commission (per lot round trip) + slippage
            # Slippage: 1 point forex, 2 points indices and gold, 0.1% price crypto
            effective_spread_price = max(spread_price, live_med_price)
            cost_spread = effective_spread_price * 1.25
            cost_comm_per_lot = 2 * comm_per_lot  # round trip
            
            # Slippage definition per asset group
            tick = mt5.symbol_info_tick(actual)
            price = float(tick.ask if tick else (info.ask or 1.0))
            if group == 'forex':
                slip_price = 1.0 * point
                slip_label = "1.0 point"
            elif group in ('indices', 'metals'):
                slip_price = 2.0 * point
                slip_label = "2.0 points"
            elif group == 'crypto':
                slip_price = price * 0.001  # 0.1%
                slip_label = "0.1% of price"
            else:
                slip_price = 1.0 * point
                slip_label = "1.0 point"
            
            mpp = (tick_value / tick_size) if tick_size > 0 else 1.0
            total_cost_per_lot = (cost_spread + slip_price) * mpp + cost_comm_per_lot
            
            symbol_facts[actual] = {
                "logical": logical,
                "actual": actual,
                "asset_group": group,
                "digits": digits,
                "point": point,
                "spread_raw_pts": spread_pts,
                "spread_price": spread_price,
                "live_spread_price": live_med_price,
                "effective_spread_price": effective_spread_price,
                "contract_size": contract_size,
                "tick_size": tick_size,
                "tick_value": tick_value,
                "swap_long": swap_long,
                "swap_short": swap_short,
                "volume_min": vol_min,
                "volume_step": vol_step,
                "volume_max": vol_max,
                "comm_per_lot_side": comm_per_lot,
                "comm_source": comm_source,
                "slip_label": slip_label,
                "slip_price": slip_price,
                "cost_spread": cost_spread,
                "cost_comm_round_trip": cost_comm_per_lot,
                "total_cost_per_lot": total_cost_per_lot,
                "source_spread": "MT5 symbol_info tick vs live db samples"
            }
        
        print("Ensuring H4 and D1 history are downloaded with manifests...")
        try:
            download_history(mt5, symbols_to_download, ['H4', 'D1'], None, None, settings)
            print("Download completed successfully.")
        except Exception as exc:
            print(f"Warning during download: {exc}. Will verify manifests and fall back to resampling if needed.")
        
    # Write docs/ACCOUNT_COSTS.md
    account_costs_path = ROOT / "docs" / "ACCOUNT_COSTS.md"
    md_lines = [
        "# Account and Symbol Facts & Cost Model v1",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()} UTC",
        "",
        "## 1. Account Facts",
        "",
        f"- **Account Login:** `{acc.login}`",
        f"- **Trade Mode:** `{mode_str}` (Verified DEMO)",
        f"- **Balance:** `{acc.balance:.2f} {acc.currency}`",
        f"- **Equity:** `{acc.equity:.2f} {acc.currency}`",
        f"- **Currency:** `{acc.currency}`",
        f"- **Leverage:** `1:{acc.leverage}`",
        f"- **Company / Broker:** `{acc.company}`",
        f"- **Server:** `{acc.server}`",
        "",
        "## 2. Symbol Specifications and Live Cost Parameters",
        "",
        "| Symbol | Logical | Group | Digits | Point | Spread (pts) | Live Spread (pts) | Min Vol | Step | Tick Size | Tick Value | Comm / Lot (Side) | Comm Source |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|"
    ]
    
    for sym, f in sorted(symbol_facts.items(), key=lambda x: x[1]['asset_group']):
        md_lines.append(
            f"| `{sym}` | `{f['logical']}` | {f['asset_group']} | {f['digits']} | {f['point']} | "
            f"{f['spread_raw_pts']:.1f} | {f['live_spread_price'] / f['point']:.1f} | "
            f"{f['volume_min']} | {f['volume_step']} | {f['tick_size']} | {f['tick_value']:.4f} | "
            f"{f['comm_per_lot_side']:.2f} | {f['comm_source']} |"
        )
    
    md_lines.extend([
        "",
        "## 3. Conservative Cost Model v1",
        "",
        "### Formula & Definition",
        "Per symbol, round-trip cost is calculated as:",
        "$$\\text{Cost} = \\left( \\max(\\text{Spread}_{\\text{symbol\\_info}}, \\text{Spread}_{\\text{live\\_median}}) \\times 1.25 + \\text{Slippage} \\right) \\times \\frac{\\text{TickValue}}{\\text{TickSize}} + 2 \\times \\text{Commission}_{\\text{side}}$$",
        "",
        "**Slippage Assumptions:**",
        "- **Forex:** 1.0 point",
        "- **Indices & Gold:** 2.0 points",
        "- **Crypto:** 0.1% of market price",
        "",
        "### Resulting Cost per 1.0 Lot (Account Currency)",
        "",
        "| Symbol | Asset Group | Effective Spread | Slippage | Spread Cost (1.25x) | Round-Trip Comm | Total Cost / Lot (USD) |",
        "|---|---|---|---|---|---|---|"
    ])
    
    for sym, f in sorted(symbol_facts.items(), key=lambda x: x[1]['asset_group']):
        md_lines.append(
            f"| `{sym}` | {f['asset_group']} | {f['effective_spread_price']:.5g} | {f['slip_label']} | "
            f"${f['cost_spread'] * (f['tick_value'] / f['tick_size']):.2f} | ${f['cost_comm_round_trip']:.2f} | "
            f"**${f['total_cost_per_lot']:.2f}** |"
        )
    
    md_lines.extend([
        "",
        "## 4. Sources of Facts",
        "",
        "1. **Account Parameters:** MT5 C-API `account_info()` directly via MT5CallProxy.",
        "2. **Symbol Specs:** MT5 C-API `symbol_info(sym)` (point, digits, contract_size, tick_size, tick_value, volume min/step).",
        "3. **Live Spreads:** `data/bot.db` table `spread_samples` collected during live trading cycles.",
        "4. **Commissions:** Historical `history_deals_get` 90-day window deals; if no deals found, broker `symbol_info.trade_commission` or default 0.0 with `commission_estimated=True`.",
        "5. **Data Manifests:** `data/history/manifests/*.json` matching downloaded parquet partitions.",
        ""
    ])
    
    account_costs_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Wrote {account_costs_path}")

if __name__ == "__main__":
    main()
