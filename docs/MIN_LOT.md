# Minimum-lot risk on the live XM Ultra Low DEMO account

Live snapshot: `2026-11-10T14:26:04.953179+00:00` UTC · account `108765323` · balance/equity `$10,000.00` / `$10,000.00` USD · server `XMGlobal-MT5 5`.
Spread statistics use enabled `#` broker symbols, sampled on M1 during London/New York overlap from `2026-11-10T13:45:41.751330+00:00` through `2026-11-10T14:25:38.000280+00:00` UTC. Each symbol has at least 30 minutes of samples; the current spread shown is the median with observed minimum and maximum.

## Live instrument specifications

| Logical instrument | Live MT5 symbol | Contract size | Min / step | Tick size | Tick value (loss/lot) | Spread median (min–max) | M1 samples |
|---|---|---:|---:|---:|---:|---:|---:|
| EURUSD | `EURUSD#` | 100,000 units | 0.01 / 0.01 | 1e-05 | $1.000000 | 1.10 pips (1.00–1.20) | 30 |
| GBPUSD | `GBPUSD#` | 100,000 units | 0.01 / 0.01 | 1e-05 | $1.000000 | 1.30 pips (1.10–1.50) | 30 |
| USDJPY | `USDJPY#` | 100,000 units | 0.01 / 0.01 | 0.001 | $0.630664 | 1.20 pips (1.00–1.50) | 30 |
| AUDUSD | `AUDUSD#` | 100,000 units | 0.01 / 0.01 | 1e-05 | $1.000000 | 1.40 pips (1.30–1.50) | 30 |
| USDCAD | `USDCAD#` | 100,000 units | 0.01 / 0.01 | 1e-05 | $0.705686 | 2.30 pips (2.10–2.50) | 30 |
| EURJPY | `EURJPY#` | 100,000 units | 0.01 / 0.01 | 0.001 | $0.632355 | 2.10 pips (1.80–2.50) | 38 |
| GBPJPY | `GBPJPY#` | 100,000 units | 0.01 / 0.01 | 0.001 | $0.632383 | 2.90 pips (2.40–3.20) | 39 |
| GOLD | `GOLD#` | 100 oz | 0.01 / 0.01 | 0.01 | $1.000000 | $0.31 ($0.26–$0.33) | 39 |

## Risk budgets

| Risk rate | Current $10,000 balance | $50 comparison balance |
|---:|---:|---:|
| 0.10% | $10.00 | $0.050 |
| 0.25% | $25.00 | $0.125 |
| 0.50% | $50.00 | $0.250 |
| 1.00% | $100.00 | $0.500 |

Minimum-lot stop risk is `abs(entry − stop) / tick_size × trade_tick_value_loss × volume_min`. JPY and CAD tick values are the live broker USD-converted values at snapshot time and can vary with conversion rates.

## Typical minimum-lot stop risk by family and timeframe

“Typical stop” is the unchanged research variant stop multiplier times median ATR(14) from closed history covering 2026-01-01 through 2026-09-30. Cells show `stop distance / risk at live volume_min`; FX distances are pips and GOLD distances are dollars.

### M15

| Family / variant | Stop multiple | EURUSD | GBPUSD | USDJPY | AUDUSD | USDCAD | EURJPY | GBPJPY | GOLD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Session Breakout · v1 M15 | 1.5×ATR | 7.7 pips / $0.77 | 10.3 pips / $1.03 | 12.4 pips / $0.78 | 7.3 pips / $0.73 | 7.6 pips / $0.53 | 13.1 pips / $0.83 | 17.0 pips / $1.08 | $14.02 / $14.02 |
| Session Breakout · v2 M15 | 1×ATR | 5.1 pips / $0.51 | 6.9 pips / $0.69 | 8.3 pips / $0.52 | 4.8 pips / $0.48 | 5.0 pips / $0.36 | 8.7 pips / $0.55 | 11.4 pips / $0.72 | $9.35 / $9.35 |
| Index Opening Range Breakout · v1 M15 | 1×ATR | 5.1 pips / $0.51 | 6.9 pips / $0.69 | 8.3 pips / $0.52 | 4.8 pips / $0.48 | 5.0 pips / $0.36 | 8.7 pips / $0.55 | 11.4 pips / $0.72 | $9.35 / $9.35 |
| Index Opening Range Breakout · v2 M15 | 1×ATR | 5.1 pips / $0.51 | 6.9 pips / $0.69 | 8.3 pips / $0.52 | 4.8 pips / $0.48 | 5.0 pips / $0.36 | 8.7 pips / $0.55 | 11.4 pips / $0.72 | $9.35 / $9.35 |
| VWAP Reversion · v1 M15 | 1.5×ATR | 7.7 pips / $0.77 | 10.3 pips / $1.03 | 12.4 pips / $0.78 | 7.3 pips / $0.73 | 7.6 pips / $0.53 | 13.1 pips / $0.83 | 17.0 pips / $1.08 | $14.02 / $14.02 |
| VWAP Reversion · v2 M15 | 1×ATR | 5.1 pips / $0.51 | 6.9 pips / $0.69 | 8.3 pips / $0.52 | 4.8 pips / $0.48 | 5.0 pips / $0.36 | 8.7 pips / $0.55 | 11.4 pips / $0.72 | $9.35 / $9.35 |

### H1

| Family / variant | Stop multiple | EURUSD | GBPUSD | USDJPY | AUDUSD | USDCAD | EURJPY | GBPJPY | GOLD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Session Breakout · v3 H1 | 1.5×ATR | 16.3 pips / $1.63 | 22.0 pips / $2.20 | 26.9 pips / $1.70 | 15.1 pips / $1.51 | 15.8 pips / $1.12 | 26.8 pips / $1.69 | 35.0 pips / $2.21 | $29.33 / $29.33 |
| Index Opening Range Breakout · v3 H1 | 1.2×ATR | 13.0 pips / $1.30 | 17.6 pips / $1.76 | 21.5 pips / $1.36 | 12.1 pips / $1.21 | 12.7 pips / $0.89 | 21.4 pips / $1.35 | 28.0 pips / $1.77 | $23.47 / $23.47 |
| VWAP Reversion · v3 H1 | 1.5×ATR | 16.3 pips / $1.63 | 22.0 pips / $2.20 | 26.9 pips / $1.70 | 15.1 pips / $1.51 | 15.8 pips / $1.12 | 26.8 pips / $1.69 | 35.0 pips / $2.21 | $29.33 / $29.33 |

### H4

| Family / variant | Stop multiple | EURUSD | GBPUSD | USDJPY | AUDUSD | USDCAD | EURJPY | GBPJPY | GOLD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Donchian Breakout · v1 H4 | 2×ATR | 45.8 pips / $4.58 | 60.7 pips / $6.07 | 76.9 pips / $4.85 | 41.4 pips / $4.14 | 43.7 pips / $3.09 | 76.9 pips / $4.86 | 97.6 pips / $6.17 | $79.72 / $79.72 |
| Donchian Breakout · v2 H4 | 2.5×ATR | 57.2 pips / $5.72 | 75.8 pips / $7.58 | 96.1 pips / $6.06 | 51.8 pips / $5.18 | 54.7 pips / $3.86 | 96.1 pips / $6.08 | 122.0 pips / $7.72 | $99.65 / $99.65 |
| Time-Series Momentum · v1 H4 | 2×ATR | 45.8 pips / $4.58 | 60.7 pips / $6.07 | 76.9 pips / $4.85 | 41.4 pips / $4.14 | 43.7 pips / $3.09 | 76.9 pips / $4.86 | 97.6 pips / $6.17 | $79.72 / $79.72 |
| Time-Series Momentum · v2 H4 | 2.5×ATR | 57.2 pips / $5.72 | 75.8 pips / $7.58 | 96.1 pips / $6.06 | 51.8 pips / $5.18 | 54.7 pips / $3.86 | 96.1 pips / $6.08 | 122.0 pips / $7.72 | $99.65 / $99.65 |
| Index Pullback in 200-Day Uptrend · v3 H4 | 1.5×ATR | 34.3 pips / $3.43 | 45.5 pips / $4.55 | 57.7 pips / $3.64 | 31.1 pips / $3.11 | 32.8 pips / $2.31 | 57.7 pips / $3.65 | 73.2 pips / $4.63 | $59.79 / $59.79 |

### D1

| Family / variant | Stop multiple | EURUSD | GBPUSD | USDJPY | AUDUSD | USDCAD | EURJPY | GBPJPY | GOLD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Donchian Breakout · v3 D1 | 2×ATR | 124.1 pips / $12.41 | 166.7 pips / $16.67 | 212.8 pips / $13.42 | 117.1 pips / $11.71 | 115.6 pips / $8.16 | 212.5 pips / $13.44 | 266.1 pips / $16.83 | $221.45 / $221.45 |
| Time-Series Momentum · v3 D1 | 2.5×ATR | 155.1 pips / $15.51 | 208.4 pips / $20.84 | 266.0 pips / $16.78 | 146.3 pips / $14.63 | 144.5 pips / $10.20 | 265.6 pips / $16.80 | 332.7 pips / $21.04 | $276.82 / $276.82 |
| Index Pullback in 200-Day Uptrend · v1 D1 | 1.5×ATR | 93.0 pips / $9.30 | 125.0 pips / $12.50 | 159.6 pips / $10.07 | 87.8 pips / $8.78 | 86.7 pips / $6.12 | 159.4 pips / $10.08 | 199.6 pips / $12.62 | $166.09 / $166.09 |
| Index Pullback in 200-Day Uptrend · v2 D1 | 2×ATR | 124.1 pips / $12.41 | 166.7 pips / $16.67 | 212.8 pips / $13.42 | 117.1 pips / $11.71 | 115.6 pips / $8.16 | 212.5 pips / $13.44 | 266.1 pips / $16.83 | $221.45 / $221.45 |

## Feasibility

Compare each displayed stop risk with the selected balance and risk rate above. Current broker specifications are used; no micro contract is assumed. Spread cost is reported separately and is not included in stop-risk figures.
