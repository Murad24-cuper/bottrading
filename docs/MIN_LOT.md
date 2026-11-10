# Minimum-lot risk on the live XM Ultra Low DEMO account

Live snapshot: `2026-11-10T11:16:33.485795+00:00` · account ending `323` · balance/equity `$10,000.00 USD` · server `XMGlobal-MT5 5`.

This replaces the prior estimates. The earlier Micro-account figures were **not taken from a live MT5 account**; they assumed micro contracts that the current terminal does not offer. MT5 currently resolves these seven forex pairs and GOLD to the standard-contract names below.

## Live instrument specifications

| Logical instrument | Live MT5 symbol | Contract size | Min / step | Tick size | Tick value (loss/lot) | Current spread |
|---|---|---:|---:|---:|---:|---:|
| EURUSD | `EURUSD` | 100,000 units | 0.01 / 0.01 | 1e-05 | $1.000000 | 2.00 pips |
| GBPUSD | `GBPUSD` | 100,000 units | 0.01 / 0.01 | 1e-05 | $1.000000 | 2.30 pips |
| USDJPY | `USDJPY` | 100,000 units | 0.01 / 0.01 | 0.001 | $0.632371 | 2.50 pips |
| AUDUSD | `AUDUSD` | 100,000 units | 0.01 / 0.01 | 1e-05 | $1.000000 | 2.40 pips |
| USDCAD | `USDCAD` | 100,000 units | 0.01 / 0.01 | 1e-05 | $0.707980 | 3.00 pips |
| EURJPY | `EURJPY#` | 100,000 units | 0.01 / 0.01 | 0.001 | $0.632347 | 2.00 pips |
| GBPJPY | `GBPJPY#` | 100,000 units | 0.01 / 0.01 | 0.001 | $0.632347 | 2.70 pips |
| GOLD | `GOLD#` | 100 oz | 0.01 / 0.01 | 0.01 | $1.000000 | $0.32 (32 points) |

## Risk budgets

| Risk rate | $10,000 live balance | $50 comparison balance |
|---:|---:|---:|
| 0.1% | $10.00 | $0.050 |
| 0.25% | $25.00 | $0.125 |
| 0.5% | $50.00 | $0.250 |
| 1% | $100.00 | $0.500 |

Minimum-lot stop risk is `abs(entry − stop) / tick_size × trade_tick_value_loss × volume_min`. JPY and CAD tick values are the live MT5 USD-converted values at snapshot time and can vary with conversion rates.

## Typical minimum-lot stop risk by family and timeframe

“Typical stop” is the unchanged research variant stop multiplier times the median ATR(14) for that instrument and timeframe, computed from closed MT5 history for 2026-01-01 through 2026-09-30. FX distances are pips; GOLD distances are dollars. Cells show `stop distance / risk at live volume_min`. The 18 research variants are listed.

### M15

| Family / variant | Stop multiple | EURUSD | GBPUSD | USDJPY | AUDUSD | USDCAD | EURJPY | GBPJPY | GOLD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Session Breakout · v1 M15 | 1.5×ATR | 7.7 / $0.77 | 10.3 / $1.03 | 12.4 / $0.78 | 7.3 / $0.73 | 7.6 / $0.54 | 13.1 / $0.83 | 17.0 / $1.08 | $14.02 / $14.02 |
| Session Breakout · v2 M15 | 1×ATR | 5.1 / $0.51 | 6.9 / $0.69 | 8.3 / $0.52 | 4.8 / $0.48 | 5.0 / $0.36 | 8.7 / $0.55 | 11.4 / $0.72 | $9.35 / $9.35 |
| Opening Range Breakout · v1 M15 | 1×ATR | 5.1 / $0.51 | 6.9 / $0.69 | 8.3 / $0.52 | 4.8 / $0.48 | 5.0 / $0.36 | 8.7 / $0.55 | 11.4 / $0.72 | $9.35 / $9.35 |
| Opening Range Breakout · v2 M15 | 1×ATR | 5.1 / $0.51 | 6.9 / $0.69 | 8.3 / $0.52 | 4.8 / $0.48 | 5.0 / $0.36 | 8.7 / $0.55 | 11.4 / $0.72 | $9.35 / $9.35 |
| VWAP Reversion · v1 M15 | 1.5×ATR | 7.7 / $0.77 | 10.3 / $1.03 | 12.4 / $0.78 | 7.3 / $0.73 | 7.6 / $0.54 | 13.1 / $0.83 | 17.0 / $1.08 | $14.02 / $14.02 |
| VWAP Reversion · v2 M15 | 1×ATR | 5.1 / $0.51 | 6.9 / $0.69 | 8.3 / $0.52 | 4.8 / $0.48 | 5.0 / $0.36 | 8.7 / $0.55 | 11.4 / $0.72 | $9.35 / $9.35 |
### H1

| Family / variant | Stop multiple | EURUSD | GBPUSD | USDJPY | AUDUSD | USDCAD | EURJPY | GBPJPY | GOLD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Session Breakout · v3 H1 | 1.5×ATR | 16.3 / $1.63 | 22.0 / $2.20 | 26.9 / $1.70 | 15.1 / $1.51 | 15.8 / $1.12 | 26.8 / $1.69 | 35.0 / $2.21 | $29.33 / $29.33 |
| Opening Range Breakout · v3 H1 | 1.2×ATR | 13.0 / $1.30 | 17.6 / $1.76 | 21.5 / $1.36 | 12.1 / $1.21 | 12.7 / $0.90 | 21.4 / $1.35 | 28.0 / $1.77 | $23.47 / $23.47 |
| VWAP Reversion · v3 H1 | 1.5×ATR | 16.3 / $1.63 | 22.0 / $2.20 | 26.9 / $1.70 | 15.1 / $1.51 | 15.8 / $1.12 | 26.8 / $1.69 | 35.0 / $2.21 | $29.33 / $29.33 |
### H4

| Family / variant | Stop multiple | EURUSD | GBPUSD | USDJPY | AUDUSD | USDCAD | EURJPY | GBPJPY | GOLD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Donchian Breakout · v1 H4 | 2×ATR | 45.8 / $4.58 | 60.7 / $6.07 | 76.9 / $4.86 | 41.4 / $4.14 | 43.7 / $3.10 | 76.9 / $4.86 | 97.6 / $6.17 | $79.72 / $79.72 |
| Donchian Breakout · v2 H4 | 2.5×ATR | 57.2 / $5.72 | 75.8 / $7.58 | 96.1 / $6.08 | 51.8 / $5.18 | 54.7 / $3.87 | 96.1 / $6.08 | 122.0 / $7.72 | $99.65 / $99.65 |
| Time-Series Momentum · v1 H4 | 2×ATR | 45.8 / $4.58 | 60.7 / $6.07 | 76.9 / $4.86 | 41.4 / $4.14 | 43.7 / $3.10 | 76.9 / $4.86 | 97.6 / $6.17 | $79.72 / $79.72 |
| Time-Series Momentum · v2 H4 | 2.5×ATR | 57.2 / $5.72 | 75.8 / $7.58 | 96.1 / $6.08 | 51.8 / $5.18 | 54.7 / $3.87 | 96.1 / $6.08 | 122.0 / $7.72 | $99.65 / $99.65 |
| Index Pullback 200-Day · v3 H4 | 1.5×ATR | 34.3 / $3.43 | 45.5 / $4.55 | 57.7 / $3.65 | 31.1 / $3.11 | 32.8 / $2.32 | 57.7 / $3.65 | 73.2 / $4.63 | $59.79 / $59.79 |
### D1

| Family / variant | Stop multiple | EURUSD | GBPUSD | USDJPY | AUDUSD | USDCAD | EURJPY | GBPJPY | GOLD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Donchian Breakout · v3 D1 | 2×ATR | 124.1 / $12.41 | 166.7 / $16.67 | 212.8 / $13.46 | 117.1 / $11.71 | 115.6 / $8.18 | 212.5 / $13.44 | 266.1 / $16.83 | $221.45 / $221.45 |
| Time-Series Momentum · v3 D1 | 2.5×ATR | 155.1 / $15.51 | 208.4 / $20.84 | 266.0 / $16.82 | 146.3 / $14.63 | 144.5 / $10.23 | 265.6 / $16.80 | 332.7 / $21.04 | $276.82 / $276.82 |
| Index Pullback 200-Day · v1 D1 | 1.5×ATR | 93.0 / $9.30 | 125.0 / $12.50 | 159.6 / $10.09 | 87.8 / $8.78 | 86.7 / $6.14 | 159.4 / $10.08 | 199.6 / $12.62 | $166.09 / $166.09 |
| Index Pullback 200-Day · v2 D1 | 2×ATR | 124.1 / $12.41 | 166.7 / $16.67 | 212.8 / $13.46 | 117.1 / $11.71 | 115.6 / $8.18 | 212.5 / $13.44 | 266.1 / $16.83 | $221.45 / $221.45 |

## Feasibility

Compare each displayed stop risk with the budget at the chosen balance and rate. These are current broker specifications; no micro contract is assumed. Current spread cost is reported separately and is not included in stop-risk figures.
