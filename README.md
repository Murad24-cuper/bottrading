# XM MT5 Trading Bot

This is a single-owner XM trading bot. Python connects to the locally running MetaTrader 5 terminal through the official `MetaTrader5` package. It scans the broker's discovered symbols, records decisions and trades in SQLite, and provides a localhost dashboard. It never withdraws money. Validate on DEMO before considering any real account.

## Install and connect

1. On Windows, install Python 3.11 or later and the XM MetaTrader 5 terminal. Sign in to the XM **demo** account, enable **Allow algorithmic trading**, and set **Tools > Options > Charts > Max bars in chart** to **Unlimited** for history downloads.
2. From this project folder, create and activate a virtual environment, then install the packages:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and set `MT5_LOGIN`, `MT5_PASSWORD` and `MT5_SERVER`. `MT5_PATH` is optional when MT5 is installed in a standard location. Keep `.env` private; it is ignored by Git. Real accounts are refused unless the account mode is `real` in `config.yaml` and `ALLOW_REAL=true` is set in `.env`.
4. Run `pytest`, then `python scripts/check_connection.py`. Review the account type, margin mode, symbols and spreads.
5. Run `python scripts/test_order_demo.py` for a read-only dry run. The `--confirm` option places a DEMO test order, waits five seconds and closes it; never use it on a real account.

## Emergency stop and ownership

Create an empty file named `STOP` in this project folder to block new entries while the bot continues managing its positions. The dashboard Pause button creates this file through an expiring command; Resume removes it. The dashboard Stop bot command exits cleanly and leaves broker SL/TP in place. Close all & stop requires confirmation and closes only positions with this bot's `magic_number`. Every close or stop modification checks ownership. Netting accounts are detected and a new order is refused if that symbol already has a position.

## Risk settings in `config.yaml`

- `risk_per_trade_pct`: maximum equity budget at the stop for one trade. Volume rounds down to the broker step; if minimum volume exceeds the budget, the trade is refused.
- `daily_loss_limit_pct` and `weekly_loss_limit_pct`: stop new entries at the configured loss, including floating P/L from open positions.
- `max_open_positions`: total position limit. `max_positions_per_group`: correlation limit for each asset group. `max_positions_per_currency` limits net FX/metals exposure per currency. `max_positions_per_underlying_group` limits correlated index exposure.
- `max_margin_usage_pct`: maximum projected used margin as a share of equity. Leverage is only a margin constraint; it never sets position size.
- `first_target_r` and `scale_out_pct`: close part of a position at the first favorable R target. If the broker's minimum volume prevents a split, close the full position there.
- `breakeven_cost_multiplier`: after scale-out, move the stop to breakeven plus estimated round-trip costs.
- `trail_atr_mult`: trail the remaining volume by ATR on its entry timeframe. Stops only move in the protective direction.
- `momentum_lookback_bars`: closed-bar lookback for detecting momentum reversal. `stagnation_minutes` and `stagnation_min_r` close positions that have not progressed enough. `max_hold_minutes` is the high safety ceiling (720 minutes by default).
- `no_entry_before_close_minutes` and `max_session_gap_hours`: infer recurring symbol session closes from the broker's H1 history; avoid new entries shortly before a close and exit owned positions before longer breaks. All comparisons use UTC. The MT5 Python package does not provide the session schedule table, so the bot infers recurring closes from observed broker bars; gaps without a repeating history pattern cannot be forecast.
- `symbol_cooldown_minutes` and `max_trades_per_symbol_per_day`: limit repeated entries per instrument.
- `min_risk_reward`: minimum take-profit distance divided by stop distance.
- `max_cost_to_target_ratio`: reject a setup when estimated round-trip spread and commission are too large relative to target value.
- `max_spread_points`: optional per-symbol spread ceilings. An empty mapping means no configured spread ceiling.
- `executor.deviation_points`: maximum price deviation sent with an order.

The scanner considers the configured asset groups across the broker's discovered symbol list. It first checks ticks and session/spread conditions, then ranks recent movement and fully analyzes at most `scanner.top_movers` symbols. `scanner.max_seconds_per_cycle` bounds the rotating universe scan; open positions remain included for management. The dashboard's scan panel shows totals, movers, signals, duration and rejection/strategy diagnostics.

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

`live.mode: shadow` records decisions without sending orders. `live.mode: trade` submits DEMO trades that pass every risk gate. The checked-in configuration selects `trade` and lists all four strategies; change it to `shadow` when you want observation only. Real trading also requires `account.mode: real` and `ALLOW_REAL=true` in `.env`; `ALLOW_REAL=false` refuses it. Keep `.env` private and never commit it.

Open the dashboard at **http://127.0.0.1:8501**. Its sidebar has Start bot, Pause, Resume, Stop bot and Close all & stop. Start launches the `.venv` bot in the background and is guarded by a process lock. Pause and Resume only change entry permission; Stop bot exits after the current management step and leaves open positions protected by broker SL/TP. Close all & stop needs the confirmation checkbox. Commands expire after `live.command_ttl_seconds` (60 seconds by default), and duplicate pending commands are rejected. The dashboard shows each command result and the heartbeat/process/MT5 state. If `DASHBOARD_PASSWORD` is non-empty, enter it before controls appear. The server binds to localhost only.

The bot uses `data/bot.lock` to refuse a second instance. If it was force-terminated, confirm it is no longer running before removing a stale lock. After `live.max_cycle_errors` consecutive cycle errors, new entries are disabled while position management continues. Ctrl+C stops the loop cleanly and shuts down MT5.

Close reasons in the trades table are `tp`, `partial_tp`, `trail`, `momentum_lost`, `stagnant`, `sl`, `time`, `session_close`, `manual`, and `kill`. Each scale-out is separately recorded in `partial_closes` and shown in the dashboard.

For a VPS, use Windows Task Scheduler to start `start_bot.bat` at system startup, with **Start in** set to this project directory and the same Windows account/environment that can access MT5 and the credentials. Create a separate startup task for `start_dashboard.bat` only if the local dashboard is needed. Keep the dashboard bound to localhost; do not expose its port directly to the internet.
