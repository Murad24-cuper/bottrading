# Systematic Edge Research v3: Six Strategy Families (Correct Research Split)

**Date:** 2026-11-09 20:13:48 UTC
**Splits Applied:**
- **M15/H1 Intraday:** Train `<= 2025-12-31`, Validation `2026-01-01` .. `2026-09-30` (9 months).
- **H4/D1 Swing:** Train `<= 2024-06-30`, Validation `2024-07-01` .. `2026-09-30` (27 months).
- **Brain Holdout:** `2026-10-20` onwards strictly untouched.
**Cost Model:** Conservative Cost Model v1 (1.25x spread + slippage + commission).
**Benchmark Included:** Buy-and-hold returns for indices and gold to isolate strategy skill from secular drift.
**Multiple Testing Control:** Deflated Sharpe Ratio with $M=18$ trials (threshold $DSR > 0$).

## 1. Summary of Results

| Family | Variant | N (Tr/Val) | Win% | EV Train | EV Val | PF | Max DD | WF Share | Random 95% | Buy-and-Hold | DSR | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Session Breakout | v1 (M15 buf 0.1, sl 1.5, tp 2.0) | 86/9 | 33.7% | -0.2836 | -0.2488 | 0.59 | 27.04R | 0% | FAIL (p95=+0.195) | n/a (FX neutral) | 0.00 | FAIL (EV not pos on both (tr:-0.284, val:-0.249); N < 300 (tr:86, val:9); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Session Breakout | v2 (M15 buf 0.2, sl 1.0, tp 2.0) | 29/1 | 23.3% | -0.3345 | -1.0992 | 0.56 | 9.91R | 33% | FAIL (p95=+0.869) | n/a (FX neutral) | 0.00 | FAIL (EV not pos on both (tr:-0.335, val:-1.099); N < 300 (tr:29, val:1); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Session Breakout | v3 (H1 buf 0.0, sl 1.5, tp 2.5) | 1446/123 | 42.2% | -0.0826 | -0.1815 | 0.83 | 140.92R | 0% | FAIL (p95=+0.028) | n/a (FX neutral) | 0.00 | FAIL (EV not pos on both (tr:-0.083, val:-0.182); N < 300 (tr:1446, val:123); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Opening Range Breakout | v1 (M15 30m ORB, sl 1.0, tp 1.5) | 944/813 | 39.2% | -0.0658 | -0.1375 | 0.85 | 183.61R | 17% | FAIL (p95=+0.145) | Tr:+55.1%, Val:+10.0% | 0.00 | FAIL (EV not pos on both (tr:-0.066, val:-0.138); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Opening Range Breakout | v2 (M15 30m ORB + SMA50, sl 1.0, tp 2.0) | 763/652 | 33.7% | -0.0744 | -0.1181 | 0.87 | 143.06R | 17% | FAIL (p95=+0.362) | Tr:+55.1%, Val:+10.0% | 0.00 | FAIL (EV not pos on both (tr:-0.074, val:-0.118); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Opening Range Breakout | v3 (H1 60m ORB, sl 1.2, tp 2.0) | 4288/901 | 41.9% | -0.0207 | -0.0621 | 0.95 | 179.95R | 33% | FAIL (p95=+0.120) | Tr:+55.1%, Val:+10.0% | 0.00 | FAIL (EV not pos on both (tr:-0.021, val:-0.062); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v1 (M15 dev 2.0 ATR, sl 1.5, tp VWAP) | 3663/2317 | 41.2% | -0.0463 | -0.0523 | 0.92 | 368.53R | 0% | FAIL (p95=+0.115) | Tr:+68.7%, Val:+7.3% | 0.00 | FAIL (EV not pos on both (tr:-0.046, val:-0.052); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v2 (M15 dev 2.5 ATR + RSI, sl 1.0, tp VWAP) | 499/466 | 28.7% | -0.1009 | +0.0569 | 0.97 | 55.45R | 33% | FAIL (p95=+0.752) | Tr:+68.7%, Val:+7.3% | 0.00 | FAIL (EV not pos on both (tr:-0.101, val:0.057); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v3 (H1 dev 2.0 ATR, sl 1.5, tp VWAP) | 4378/704 | 42.2% | -0.0804 | -0.0710 | 0.84 | 405.59R | 0% | FAIL (p95=+0.025) | Tr:+68.7%, Val:+7.3% | 0.00 | FAIL (EV not pos on both (tr:-0.080, val:-0.071); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v1 (H4 20-period, sl 2.0, tp 4.0) | 4430/1300 | 34.6% | -0.0518 | +0.0202 | 0.95 | 255.31R | 33% | FAIL (p95=+0.398) | Tr:+63.0%, Val:+47.6% | 0.00 | FAIL (EV not pos on both (tr:-0.052, val:0.020); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v2 (H4 55-period, sl 2.5, tp 5.0) | 2346/702 | 34.9% | -0.0233 | -0.0111 | 0.97 | 118.70R | 50% | FAIL (p95=+0.424) | Tr:+63.0%, Val:+47.6% | 0.00 | FAIL (EV not pos on both (tr:-0.023, val:-0.011); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v3 (D1 20-period, sl 2.0, tp 4.0) | 1661/235 | 37.8% | +0.0057 | +0.1157 | 1.03 | 40.11R | 50% | FAIL (p95=+0.379) | Tr:+63.0%, Val:+47.6% | 0.00 | FAIL (WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v1 (H4 12-bar, sl 2.0, tp 3.0) | 7538/2238 | 41.3% | -0.0340 | -0.0161 | 0.95 | 321.72R | 17% | FAIL (p95=+0.159) | Tr:+63.0%, Val:+47.6% | 0.00 | FAIL (EV not pos on both (tr:-0.034, val:-0.016); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v2 (H4 30-bar, sl 2.5, tp 4.0) | 4207/1177 | 40.4% | -0.0324 | +0.0588 | 0.98 | 154.15R | 50% | FAIL (p95=+0.220) | Tr:+63.0%, Val:+47.6% | 0.00 | FAIL (EV not pos on both (tr:-0.032, val:0.059); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v3 (D1 20-bar, sl 2.5, tp 4.0) | 1947/275 | 44.1% | -0.0158 | +0.0854 | 0.99 | 56.30R | 50% | FAIL (p95=+0.140) | Tr:+63.0%, Val:+47.6% | 0.00 | FAIL (EV not pos on both (tr:-0.016, val:0.085); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v1 (D1 SMA200 + RSI<40, sl 1.5, tp 2.5) | 174/36 | 47.1% | +0.1921 | +0.3562 | 1.41 | 9.85R | 83% | FAIL (p95=+0.400) | Tr:+65.6%, Val:+39.7% | 0.00 | FAIL (N < 100 (tr:174, val:36); fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v2 (D1 SMA200 + 3 down days, sl 2.0, tp 3.0) | 322/67 | 44.7% | +0.0077 | +0.3356 | 1.12 | 11.54R | 50% | FAIL (p95=+0.255) | Tr:+65.6%, Val:+39.7% | 0.00 | FAIL (N < 100 (tr:322, val:67); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v3 (H4 SMA1200 + RSI<30, sl 1.5, tp 2.5) | 224/116 | 37.1% | -0.0583 | -0.0102 | 0.94 | 28.86R | 33% | FAIL (p95=+0.376) | Tr:+65.6%, Val:+39.7% | 0.00 | FAIL (EV not pos on both (tr:-0.058, val:-0.010); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |

## 2. Decision: Case B (No Strategy Qualified)

**Outcome:** `Case B`

### Criteria for Qualification:
1. Net expectancy $R > 0$ after conservative costs on BOTH Train and Validation splits.
2. Minimum trade count: $\ge 300$ per split for intraday (M15/H1), $\ge 100$ per split for H4/D1.
3. Walk-Forward consistency: $\ge 60\%$ positive EV windows across 6 rolling periods.
4. Random-entry benchmark: Outperforms 95th percentile of 200 random simulation passes.
5. Deflated Sharpe Ratio: $DSR > 0$ adjusted for 18 variant trials.

### Application to Live Trading:
- **Case B Applied:** No strategy qualified for unconstrained live production trading.
- Normal entries stay off (capital protected from negative expectancy).
- `docs/NO_EDGE.md` updated with empirical v3 numbers.
- DEMO exploration continues running for all families at 0.1% minimum risk.

## 3. Buy-and-Hold Drift vs. Strategy Skill Analysis

Over the examined periods, secular asset appreciation was extraordinarily strong:
- **US500Cash:** Intraday M15/H1: Train +56.0%, Val +11.8% | H4/D1: Train +67.8%, Val +39.3%.
- **US100Cash:** Intraday M15/H1: Train +63.6%, Val +21.0% | H4/D1: Train +123.0%, Val +52.5%.
- **GOLD:** Intraday M15/H1: Train +123.0%, Val -3.6% | H4/D1: Train +52.5%, Val +79.3%.

Despite large macro market drifts, mechanical breakout and trend rules suffer from transaction drag, execution costs, and whipsaws during chop regimes, resulting in negative net expectancy after conservative execution costs.