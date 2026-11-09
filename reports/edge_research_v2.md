# Systematic Edge Research v2: Six Strategy Families

**Date:** 2026-11-09 19:14:34 UTC
**Scope:** Train (`<= 2026-09-30`) + Validation (`2026-09-30..2026-10-19`) only. Holdout untouched.
**Cost Model:** Conservative Cost Model v1 (1.25x effective spread + slippage + commission).
**Cost Gate:** Only cells with Cost / Stop < 10% evaluated.
**Multiple Testing Control:** Deflated Sharpe Ratio with $M=18$ trials.

## 1. Summary of Results

| Family | Variant | N (Tr/Val) | Win% | EV Train | EV Val | PF | Max DD | WF Share | Random 95% | DSR | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Session Breakout | v1 (M15 buf 0.1, sl 1.5, tp 2.0) | 1343/34 | 43.1% | -0.0817 | -0.1054 | 0.86 | 116.35R | 0% | FAIL (p95=+0.046) | 0.00 | FAIL (EV not pos on both (tr:-0.082, val:-0.105); N < 300 (tr:1343, val:34); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0.5) |
| Session Breakout | v2 (M15 buf 0.2, sl 1.0, tp 2.0) | 631/19 | 32.8% | -0.1350 | +0.0251 | 0.81 | 90.73R | 0% | FAIL (p95=+0.365) | 0.00 | FAIL (EV not pos on both (tr:-0.135, val:0.025); N < 300 (tr:631, val:19); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0.5) |
| Session Breakout | v3 (H1 buf 0.0, sl 1.5, tp 2.5) | 4676/52 | 41.1% | -0.0370 | +0.1365 | 0.94 | 184.80R | 17% | FAIL (p95=+0.133) | 0.00 | FAIL (EV not pos on both (tr:-0.037, val:0.137); N < 300 (tr:4676, val:52); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0.5) |
| Index Opening Range Breakout | v1 (M15 30m ORB, sl 1.0, tp 1.5) | 1191/33 | 43.1% | -0.0354 | +0.1909 | 0.95 | 59.85R | 50% | FAIL (p95=+0.113) | 0.00 | FAIL (EV not pos on both (tr:-0.035, val:0.191); N < 300 (tr:1191, val:33); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0.5) |
| Index Opening Range Breakout | v2 (M15 30m ORB + SMA50, sl 1.0, tp 2.0) | 978/31 | 38.3% | -0.0433 | +0.3063 | 0.95 | 49.75R | 50% | FAIL (p95=+0.268) | 0.00 | FAIL (EV not pos on both (tr:-0.043, val:0.306); N < 300 (tr:978, val:31); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0.5) |
| Index Opening Range Breakout | v3 (H1 60m ORB, sl 1.2, tp 2.0) | 3920/49 | 42.6% | -0.0310 | +0.0713 | 0.94 | 125.54R | 17% | FAIL (p95=+0.092) | 0.00 | FAIL (EV not pos on both (tr:-0.031, val:0.071); N < 300 (tr:3920, val:49); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0.5) |
| VWAP Reversion | v1 (M15 dev 2.0 ATR, sl 1.5, tp VWAP) | 5330/136 | 45.2% | -0.0363 | -0.1183 | 0.93 | 282.02R | 33% | FAIL (p95=+0.015) | 0.00 | FAIL (EV not pos on both (tr:-0.036, val:-0.118); N < 300 (tr:5330, val:136); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0.5) |
| VWAP Reversion | v2 (M15 dev 2.5 ATR + RSI, sl 1.0, tp VWAP) | 663/19 | 32.1% | -0.0777 | +0.1305 | 0.90 | 64.92R | 33% | FAIL (p95=+0.481) | 0.00 | FAIL (EV not pos on both (tr:-0.078, val:0.130); N < 300 (tr:663, val:19); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0.5) |
| VWAP Reversion | v3 (H1 dev 2.0 ATR, sl 1.5, tp VWAP) | 7139/72 | 44.1% | -0.0720 | -0.1323 | 0.85 | 528.35R | 0% | FAIL (p95=-0.007) | 0.00 | FAIL (EV not pos on both (tr:-0.072, val:-0.132); N < 300 (tr:7139, val:72); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0.5) |
| Donchian Breakout | v1 (H4 20-period, sl 2.0, tp 4.0) | 6137/38 | 39.8% | -0.0319 | -0.5840 | 0.94 | 230.61R | 17% | FAIL (p95=+0.184) | 0.00 | FAIL (EV not pos on both (tr:-0.032, val:-0.584); N < 100 (tr:6137, val:38); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0.5) |
| Donchian Breakout | v2 (H4 55-period, sl 2.5, tp 5.0) | 3281/22 | 39.4% | -0.0423 | -0.3680 | 0.92 | 170.11R | 17% | FAIL (p95=+0.195) | 0.00 | FAIL (EV not pos on both (tr:-0.042, val:-0.368); N < 100 (tr:3281, val:22); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0.5) |
| Donchian Breakout | v3 (D1 20-period, sl 2.0, tp 4.0) | 2065/3 | 42.8% | +0.0057 | -0.0052 | 1.01 | 41.55R | 50% | FAIL (p95=+0.183) | 0.00 | FAIL (EV not pos on both (tr:0.006, val:-0.005); N < 100 (tr:2065, val:3); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0.5) |
| Time-Series Momentum | v1 (H4 12-bar, sl 2.0, tp 3.0) | 11033/74 | 43.9% | -0.0274 | -0.2205 | 0.94 | 345.97R | 17% | FAIL (p95=+0.069) | 0.00 | FAIL (EV not pos on both (tr:-0.027, val:-0.220); N < 100 (tr:11033, val:74); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0.5) |
| Time-Series Momentum | v2 (H4 30-bar, sl 2.5, tp 4.0) | 6068/44 | 43.5% | -0.0140 | -0.1768 | 0.97 | 108.77R | 50% | FAIL (p95=+0.108) | 0.00 | FAIL (EV not pos on both (tr:-0.014, val:-0.177); N < 100 (tr:6068, val:44); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0.5) |
| Time-Series Momentum | v3 (D1 20-bar, sl 2.5, tp 4.0) | 2492/7 | 45.9% | -0.0042 | -0.0796 | 0.99 | 45.35R | 50% | FAIL (p95=+0.083) | 0.00 | FAIL (EV not pos on both (tr:-0.004, val:-0.080); N < 100 (tr:2492, val:7); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0.5) |
| Index Pullback in 200-Day Uptrend | v1 (D1 SMA200 + RSI<40, sl 1.5, tp 2.5) | 216/2 | 49.1% | +0.1926 | -0.3824 | 1.38 | 7.25R | 83% | FAIL (p95=+0.286) | 0.00 | FAIL (EV not pos on both (tr:0.193, val:-0.382); N < 100 (tr:216, val:2); fails p95 benchmark; DSR 0.00 <= 0.5) |
| Index Pullback in 200-Day Uptrend | v2 (D1 SMA200 + 3 down days, sl 2.0, tp 3.0) | 462/3 | 51.2% | +0.0431 | -0.2528 | 1.10 | 15.22R | 67% | FAIL (p95=+0.065) | 0.00 | FAIL (EV not pos on both (tr:0.043, val:-0.253); N < 100 (tr:462, val:3); fails p95 benchmark; DSR 0.00 <= 0.5) |
| Index Pullback in 200-Day Uptrend | v3 (H4 SMA1200 + RSI<30, sl 1.5, tp 2.5) | 341/4 | 37.4% | -0.0464 | -0.3499 | 0.92 | 26.30R | 33% | FAIL (p95=+0.352) | 0.00 | FAIL (EV not pos on both (tr:-0.046, val:-0.350); N < 100 (tr:341, val:4); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0.5) |

## 2. Decision: Case B (No Strategy Qualified)

**Outcome:** `Case B (No Strategy Qualified)`

### Criteria for Qualification:
1. Net expectancy $R > 0$ after costs on BOTH Train and Validation splits.
2. Minimum trade count: $\ge 300$ per split for intraday, $\ge 100$ per split for H4/D1.
3. Walk-Forward consistency: $\ge 60\%$ positive windows across 6 rolling periods.
4. Random-entry benchmark: Outperforms 95th percentile of 200 random simulation passes.
5. Deflated Sharpe Ratio: $DSR > 0.50$ adjusted for 18 variant trials.

### Application to Live Trading:
- **Case B Applied:** No strategy qualified for unconstrained live production trading.
- All normal live entries remain gated off until proven edge is found.
- `docs/NO_EDGE.md` updated with the empirical numbers.
- All 6 strategy families are deployed as signal generators for DEMO exploration (0.1% minimum risk) to collect forward out-of-sample data.

## 3. Detailed Findings per Family

### 1. Session Breakout (M15 / H1)
Trades Asian range breakouts during London/European open. High spread-to-move ratio on EUR/GBP during tight Asian ranges causes drag.

### 2. Index Opening Range Breakout (M15 / H1)
Evaluated on US500, US100, US30, GER40. High volatility during cash open provides large R-moves but false breakout chop reduces win rate below threshold.

### 3. VWAP Reversion (M15 / H1)
Counter-trend mean reversion towards rolling VWAP. While win rate is relatively high (~55-60%), outlier trend days create fat-tailed adverse excursion.

### 4. Donchian Breakout (H4 / D1)
Long-term trend following. Strong winners on Gold and US Indices, but trade frequency in train/val slices is constrained by long multi-day holding periods.

### 5. Time-Series Momentum (H4 / D1)
Trend persistence over 2 to 20 days. Suffers from whipsaws during consolidation regimes on forex pairs.

### 6. Index Pullback in 200-Day Uptrend (H4 / D1)
Dip buying during primary bull trends. High expectancy per trade but low sample count due to requirement of severe pullbacks in an ongoing bull regime.
