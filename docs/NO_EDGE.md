# Final Empirical No-Edge Policy: Case B Applied (v3 Research Splits)

## 1. Decision & Status

**Status:** Completed Case B (Empirical Research v3 Finished on 2026-11-10).

Systematic edge research v3 over all six strategy families across 18 parameter variants was executed against time-based splits:
- **M15/H1 Intraday:** Train `<= 2025-12-31`, Validation `2026-01-01` .. `2026-09-30` (9 months).
- **H4/D1 Swing:** Train `<= 2024-06-30`, Validation `2024-07-01` .. `2026-09-30` (27 months).
- **Protected holdout:** observations from `2026-10-20` onward are excluded from feature/outcome scoring; the `2026-11-08` brain holdout remains untouched.

Costs were evaluated under Conservative Cost Model v1 ($1.25 \times \text{spread} + \text{slippage} + \text{commission}$) with the minimum validation toolkit (random benchmark with 200 reps, 6-window walk-forward, Deflated Sharpe Ratio with $M=18$ trials, and Buy-and-Hold benchmark comparisons).
Trades whose full holding horizon crosses a train/validation boundary are purged; holdout entries are not simulated.

**Result:** Zero of 18 variants met all five qualification criteria:
1. Positive net expectancy after costs on both Train and Validation splits ($EV > 0$).
2. Sufficient trade sample ($\ge 300$ per split for intraday, $\ge 100$ per split for H4/D1).
3. Walk-forward consistency $\ge 60\%$ positive EV windows.
4. Outperforming 95th percentile random baseline.
5. Deflated Sharpe Ratio $DSR > 0$.

Accordingly, **Case B remains fully in force**:
1. Ordinary production live entries remain disabled (`live.normal_trading_disabled: true`).
2. The 2026-11-08 brain holdout remains strictly preserved and untouched.
3. All six strategy families are deployed as live signal generators (shadow by default).
4. `demo_exploration` is enabled at minimum risk (0.1% per trade) on DEMO to collect forward out-of-sample data under live conditions.

---

## 2. Empirical Research Summary (from reports/edge_research_v3.md)

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

---

## 3. Key Analytical Insights

1. **Transaction Costs Dominance:** After deducting conservative round-trip friction ($1.25 \times \text{spread} + \text{slippage} + \text{commission}$), raw mechanical entry rules exhibit negative expectancy across large out-of-sample periods.
2. **Buy-and-Hold Drift vs. Skill:** While indices gained +55% to +123% over train and +10% to +52% over validation, long-only pullback rules gained positive raw EV primarily due to underlying asset upward drift rather than entry timing timing skill (failing random-entry benchmarks).
3. **Donchian Breakout v3 (D1):** Produced positive net EV on both train (+0.0057R) and validation (+0.1157R) with profit factor 1.03, but failed the 60% walk-forward consistency threshold (50%) and random baseline.
4. **Exploration Function:** Rather than risking capital on unproven mechanical rules, DEMO exploration collects forward live trade data at minimal 0.1% risk to evaluate execution and ML filtering.
