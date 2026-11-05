# XM MT5 Trading Bot Foundation

## Setup

1. Install Python 3.11+ and the MT5 desktop terminal. Log into an XM demo account and enable **Allow algorithmic trading**.
2. Install dependencies: `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env`. Fill in `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER` and optionally `MT5_PATH`. Keep `.env` private. Real accounts also require `ALLOW_REAL=true` and `account.mode: real` in `config.yaml`.
4. Run `pytest`, then `python scripts/check_connection.py`. Use `python scripts/test_order_demo.py --confirm` only for a demo order.

## Safety

Create a file named `STOP` in the project root to stop new order placement. The live loop should also halt when it sees this file. Delete the file to resume. The bot refuses real accounts unless `ALLOW_REAL=true`. Every managed order must use the configured `magic_number`; manually opened trades are not to be managed.

## Risk settings

Edit `config.yaml` only to change tunable numbers. `risk_per_trade_pct` sets the equity risk budget per trade. Daily and weekly loss limits halt new entries. `max_open_positions` caps all positions, while `max_positions_per_group` limits concentration. `max_margin_usage_pct` caps used margin as a share of equity. `max_hold_minutes` is the time stop. `min_risk_reward` and `max_cost_to_target_ratio` filter weak or expensive trades. Friday times are UTC. `max_spread_points` can set per-symbol spread ceilings.

MT5 symbol names are discovered at runtime; alias patterns in `universe.symbol_aliases` are hints for finding broker-specific names, not assumptions that a specific suffix exists. XM account symbol sets and margin modes vary by account.
