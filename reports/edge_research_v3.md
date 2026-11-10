# Systematic Edge Research v3: Six Strategy Families (Correct Research Split)

**Date:** 2026-11-10 10:21:54 UTC
**Splits Applied:**
- **M15/H1 Intraday:** Train `<= 2025-12-31`, Validation `2026-01-01` .. `2026-09-30` (9 months).
- **H4/D1 Swing:** Train `<= 2024-06-30`, Validation `2024-07-01` .. `2026-09-30` (27 months).
- **Protected holdout:** observations from `2026-10-20` onward are excluded from feature and outcome scoring.
- Trades whose full holding horizon would cross a train/validation cutoff are purged; holdout entries are not simulated.
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
| Index Opening Range Breakout | v3 (H1 60m ORB, sl 1.2, tp 2.0) | 4286/899 | 41.9% | -0.0204 | -0.0629 | 0.95 | 178.87R | 33% | FAIL (p95=+0.119) | Tr:+55.1%, Val:+10.0% | 0.00 | FAIL (EV not pos on both (tr:-0.020, val:-0.063); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v1 (M15 dev 2.0 ATR, sl 1.5, tp VWAP) | 3661/2313 | 41.2% | -0.0458 | -0.0529 | 0.92 | 368.56R | 17% | FAIL (p95=+0.113) | Tr:+68.7%, Val:+7.3% | 0.00 | FAIL (EV not pos on both (tr:-0.046, val:-0.053); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v2 (M15 dev 2.5 ATR + RSI, sl 1.0, tp VWAP) | 499/465 | 28.6% | -0.1009 | +0.0519 | 0.96 | 56.01R | 33% | FAIL (p95=+0.754) | Tr:+68.7%, Val:+7.3% | 0.00 | FAIL (EV not pos on both (tr:-0.101, val:0.052); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v3 (H1 dev 2.0 ATR, sl 1.5, tp VWAP) | 4374/700 | 42.1% | -0.0818 | -0.0725 | 0.83 | 411.85R | 0% | FAIL (p95=+0.025) | Tr:+68.7%, Val:+7.3% | 0.00 | FAIL (EV not pos on both (tr:-0.082, val:-0.073); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v1 (H4 20-period, sl 2.0, tp 4.0) | 4412/1281 | 34.6% | -0.0500 | +0.0132 | 0.95 | 257.10R | 33% | FAIL (p95=+0.395) | Tr:+63.0%, Val:+47.6% | 0.00 | FAIL (EV not pos on both (tr:-0.050, val:0.013); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v2 (H4 55-period, sl 2.5, tp 5.0) | 2333/681 | 34.9% | -0.0204 | -0.0212 | 0.97 | 114.36R | 50% | FAIL (p95=+0.423) | Tr:+63.0%, Val:+47.6% | 0.00 | FAIL (EV not pos on both (tr:-0.020, val:-0.021); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v3 (D1 20-period, sl 2.0, tp 4.0) | 1643/225 | 37.7% | +0.0074 | +0.1150 | 1.03 | 39.08R | 50% | FAIL (p95=+0.378) | Tr:+63.0%, Val:+47.6% | 0.00 | FAIL (WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v1 (H4 12-bar, sl 2.0, tp 3.0) | 7516/2218 | 41.3% | -0.0342 | -0.0148 | 0.95 | 317.24R | 17% | FAIL (p95=+0.156) | Tr:+63.0%, Val:+47.6% | 0.00 | FAIL (EV not pos on both (tr:-0.034, val:-0.015); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v2 (H4 30-bar, sl 2.5, tp 4.0) | 4185/1164 | 40.4% | -0.0318 | +0.0605 | 0.98 | 151.28R | 50% | FAIL (p95=+0.218) | Tr:+63.0%, Val:+47.6% | 0.00 | FAIL (EV not pos on both (tr:-0.032, val:0.060); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v3 (D1 20-bar, sl 2.5, tp 4.0) | 1935/267 | 44.0% | -0.0143 | +0.0462 | 0.99 | 53.30R | 50% | FAIL (p95=+0.139) | Tr:+63.0%, Val:+47.6% | 0.00 | FAIL (EV not pos on both (tr:-0.014, val:0.046); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v1 (D1 SMA200 + RSI<40, sl 1.5, tp 2.5) | 172/33 | 47.3% | +0.1750 | +0.4803 | 1.42 | 9.85R | 83% | FAIL (p95=+0.409) | Tr:+65.6%, Val:+39.7% | 0.00 | FAIL (N < 100 (tr:172, val:33); fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v2 (D1 SMA200 + 3 down days, sl 2.0, tp 3.0) | 316/64 | 44.5% | -0.0126 | +0.3985 | 1.10 | 12.02R | 50% | FAIL (p95=+0.252) | Tr:+65.6%, Val:+39.7% | 0.00 | FAIL (EV not pos on both (tr:-0.013, val:0.398); N < 100 (tr:316, val:64); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v3 (H4 SMA1200 + RSI<30, sl 1.5, tp 2.5) | 223/116 | 36.9% | -0.0659 | -0.0102 | 0.93 | 30.50R | 33% | FAIL (p95=+0.380) | Tr:+65.6%, Val:+39.7% | 0.00 | FAIL (EV not pos on both (tr:-0.066, val:-0.010); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |

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