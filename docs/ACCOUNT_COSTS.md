# Account and Symbol Facts & Cost Model v1

Generated: 2026-11-10T14:26:04.953179+00:00 UTC

## 1. Account facts

- **Account login:** `108765323`
- **Trade mode:** `DEMO` (verified from the running bot status)
- **Balance / equity:** `$10000.00 / $10000.00 USD`
- **Server:** `XMGlobal-MT5 5`

## 2. Enabled symbol specifications and observed spreads

M1 spread samples cover London/New York overlap from `2026-11-10T13:45:41.751330+00:00` through `2026-11-10T14:25:38.000280+00:00` UTC. `Spread pts` is median (minimum–maximum); at least 30 minutes of observations are included for every symbol.

| Symbol | Logical | Group | Digits | Point | Spread pts (min–max) | Median pips / $ | Min Vol | Step | Contract | Tick Size | Tick Value Loss | Samples |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `EURUSD#` | EURUSD | forex | 5 | 1e-05 | 11.0 (10.0–12.0) | 1.10 pips | 0.01 | 0.01 | 100000 | 1e-05 | $1.000000 | 30 |
| `GBPUSD#` | GBPUSD | forex | 5 | 1e-05 | 13.0 (11.0–15.0) | 1.30 pips | 0.01 | 0.01 | 100000 | 1e-05 | $1.000000 | 30 |
| `USDJPY#` | USDJPY | forex | 3 | 0.001 | 12.0 (10.0–15.0) | 1.20 pips | 0.01 | 0.01 | 100000 | 0.001 | $0.630664 | 30 |
| `AUDUSD#` | AUDUSD | forex | 5 | 1e-05 | 14.0 (13.0–15.0) | 1.40 pips | 0.01 | 0.01 | 100000 | 1e-05 | $1.000000 | 30 |
| `USDCAD#` | USDCAD | forex | 5 | 1e-05 | 23.0 (21.0–25.0) | 2.30 pips | 0.01 | 0.01 | 100000 | 1e-05 | $0.705686 | 30 |
| `EURJPY#` | EURJPY | forex | 3 | 0.001 | 21.0 (18.0–25.0) | 2.10 pips | 0.01 | 0.01 | 100000 | 0.001 | $0.632355 | 38 |
| `GBPJPY#` | GBPJPY | forex | 3 | 0.001 | 29.0 (24.0–32.0) | 2.90 pips | 0.01 | 0.01 | 100000 | 0.001 | $0.632383 | 39 |
| `GOLD#` | GOLD | metals | 2 | 0.01 | 31.0 (26.0–33.0) | $0.31 | 0.01 | 0.01 | 100 | 0.01 | $1.000000 | 39 |

## 3. Conservative cost model v1

For live entry fallback, spread is current `symbol_info.spread × point × 1.25`; observed cells use their sample median. Both include two-sided slippage and estimated round-trip commission in the live gate. This research cost summary uses the frozen v4 assumption: median sampled spread × 1.25, without added slippage or commission.

Per-lot cost = `((median spread × 1.25) + (slippage points × point)) / tick size × loss tick value + round-trip commission`. Commission is not confirmed by closed deals on the new account; configured default is `$0.00/lot/side` and is labeled estimated.

| Symbol | Group | Median spread ×1.25 | Slippage | Commission source | Cost / 1 lot |
|---|---|---:|---:|---|---:|
| `EURUSD#` | forex | 1.37 pips | 1 pts | estimated default $0.00/side | $14.75 |
| `GBPUSD#` | forex | 1.62 pips | 1 pts | estimated default $0.00/side | $17.25 |
| `USDJPY#` | forex | 1.50 pips | 1 pts | estimated default $0.00/side | $10.09 |
| `AUDUSD#` | forex | 1.75 pips | 1 pts | estimated default $0.00/side | $18.50 |
| `USDCAD#` | forex | 2.87 pips | 1 pts | estimated default $0.00/side | $20.99 |
| `EURJPY#` | forex | 2.63 pips | 1 pts | estimated default $0.00/side | $17.23 |
| `GBPJPY#` | forex | 3.62 pips | 1 pts | estimated default $0.00/side | $23.56 |
| `GOLD#` | metals | $0.39 | 2 pts | estimated default $0.00/side | $40.75 |

## 4. Sources

1. Account mode and connection: live `bot_status` maintained by the supervisor-owned MT5 session.
2. Account balance/equity: latest live equity snapshot in `data/bot.db`.
3. Broker specs: `data/history/symbol_specs.json`, refreshed through the bot-owned MT5 session.
4. Spread min/median/max: `spread_samples` M1 records in `data/bot.db` from the enabled `#` symbol aliases during London/New York overlap.
