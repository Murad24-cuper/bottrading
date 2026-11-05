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

## Part 2: analysis, data and backtests

Pure pandas/numpy indicators live in `src/indicators.py`; `src/features.py` builds causal latest-bar values and a coarse regime. The four configured strategies are `trend_pullback`, `mean_reversion`, `breakout` and `volatility_scalp`. Strategy parameters and allowed asset groups are in `config.yaml`.

Download candles from the logged-in local MT5 terminal (read-only):

```powershell
python scripts/download_history.py --symbols liquid
python scripts/download_history.py --symbols universe --from 2024-01-01 --to 2026-11-05
```

MT5 history availability is constrained by **Max bars in chart**. In MT5, open **Tools > Options > Charts** and set **Max bars in chart** to **Unlimited** before downloading long ranges. Cached candles are written as Parquet under `data/history/`; `symbol_specs.json` captures the broker tick and volume specifications used by the simulator.

Run the read-only live scanner or a cached-data backtest:

```powershell
python scripts/run_scan_once.py
python scripts/run_backtest.py --strategies all --symbols liquid --equity 1000 --walk-forward
python scripts/run_backtest.py --strategies all --symbols liquid --equity 10
```

The scanner ranks signals and prints the risk-manager decision; it never submits orders. The backtester enters at the next bar open, applies spread, slippage and configured per-side commission, assumes the stop is hit first when both stop and target fall inside one bar, and reuses the live position sizing and risk gates. Reports are saved under `reports/<UTC timestamp>/` with summary, trade, equity and grouped metric files. Historical and simulated results do not guarantee future performance.

## Part 3: live loop and dashboard

Install the latest dependencies with `python -m pip install -r requirements.txt`. Start the bot and dashboard in separate terminals:

```powershell
.\start_bot.bat
.\start_dashboard.bat
```

The dashboard binds to `127.0.0.1:8501` and reads bot state only from SQLite; it does not open an MT5 connection. `DASHBOARD_PASSWORD` is optional. Set it in `.env` or the Windows environment used to launch the dashboard to require a password. Keep the service on localhost or behind a separately secured tunnel.

The default `live.mode: shadow` records candidates and risk decisions without sending orders. To enable demo trading, set `live.mode: trade` and list only the strategies you want in `live.strategies`; an empty list authorizes no strategy to place orders. For a real account, the existing MT5 guard also requires `account.mode: real` and `ALLOW_REAL=true` in `.env`. Review the risk controls and validate with demo/backtests before switching modes.

Create `STOP` in the project root to pause new entries while the bot continues managing owned positions. Put the standalone word `HALT` in `STOP` to exit the bot cleanly without closing positions. Remove `STOP` to resume. Dashboard pause/resume controls queue commands for the bot; **Close all positions** requires a confirmation checkbox and is also handled by the bot, which only closes positions with its configured magic number.

The bot uses `data/bot.lock` to refuse a second instance. If it was force-terminated, confirm that it is no longer running before removing a leftover lock file. After `live.max_cycle_errors` consecutive cycle errors, new entries are disabled while position management continues. Ctrl+C stops the loop cleanly and shuts down MT5.

For a VPS, use Windows Task Scheduler to start `start_bot.bat` at system startup, with **Start in** set to this project directory and the same Windows account/environment that can access MT5 and the credentials. Create a separate startup task for `start_dashboard.bat` only if the local dashboard is needed. Keep the dashboard bound to localhost; do not expose its port directly to the internet.
