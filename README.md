# XM MT5 Trading Bot — Part 1 Foundation

This is a single-owner foundation for an XM account. It connects through the locally running MetaTrader 5 terminal using the official Python package. It does not withdraw money. Strategy scanning, a live loop and a dashboard belong to later parts.

## Install and connect

1. On Windows, install Python 3.11 or later and MetaTrader 5. Sign in to the XM **demo** account and enable **Allow algorithmic trading** in the terminal.
2. From this project folder, create and activate a virtual environment, then install the packages:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and set `MT5_LOGIN`, `MT5_PASSWORD` and `MT5_SERVER`. `MT5_PATH` is optional when MT5 is installed in a standard location. Keep `.env` private; it is ignored by Git. Real accounts are refused unless the account mode is `real` in `config.yaml` and `ALLOW_REAL=true` is set in `.env`.
4. Run `pytest`, then `python scripts/check_connection.py`. Review the account type, margin mode, symbols and spreads.
5. `python scripts/test_order_demo.py` is a read-only dry run. Only on a DEMO account, run `python scripts/test_order_demo.py --confirm` to open a small test position, wait five seconds and close it.

## Emergency stop and ownership

Create an empty file named `STOP` in this project folder to block new orders. The executor checks it before every entry. Remove the file when you intend to re-enable entries. Closing existing positions on a kill switch is the responsibility of the live loop. Every order this code submits uses `magic_number`; close and modify operations first verify that magic number. On netting accounts, the executor must not merge a new trade with an existing position on the same symbol.

## Risk settings in `config.yaml`

- `risk_per_trade_pct`: maximum equity budget at the stop for one trade. Volume rounds down to the broker step; if minimum volume exceeds the budget, the trade is refused.
- `daily_loss_limit_pct` and `weekly_loss_limit_pct`: stop new entries at the configured loss, including floating P/L from open positions.
- `max_open_positions`: total position limit. `max_positions_per_group`: correlation limit for each asset group.
- `max_margin_usage_pct`: maximum projected used margin as a share of equity. Leverage is only a margin constraint; it never sets position size.
- `max_hold_minutes`: close our positions when they exceed the time limit.
- `min_risk_reward`: minimum take-profit distance divided by stop distance.
- `max_cost_to_target_ratio`: reject a setup when estimated round-trip spread and commission are too large relative to target value.
- `max_spread_points`: optional per-symbol spread ceilings. An empty mapping means no configured spread ceiling.
- `no_new_trades_friday_after_utc` and `close_all_friday_utc`: Friday entry cutoff and close time, in UTC.
- `executor.deviation_points`: maximum price deviation sent with an order.

`universe.symbol_aliases` contains search patterns, not fixed XM names. The terminal symbol list is always discovered at runtime. XM symbols and symbol suffixes vary by server/account; margin mode is read from `account_info()` and supports hedging and netting safeguards.
