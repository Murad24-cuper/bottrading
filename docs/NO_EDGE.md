# Final Empirical No-Edge Policy: Case B Applied

## 1. Decision & Status

**Status:** Completed Case B (Empirical Research Finished on 2026-11-09).

Systematic edge research over all six strategy families across 18 parameter variants was executed against historical train (`<= 2026-09-30`) and validation (`2026-09-30..2026-10-19`) splits using the Conservative Cost Model v1 (1.25x effective spread + slippage + commission) and the minimum validation toolkit (random benchmark with 200 reps, 6-window walk-forward, and Deflated Sharpe Ratio with $M=18$ trials).

**Result:** Zero of 18 variants met all five qualification criteria (positive EV on both train and validation splits, sufficient trade sample, walk-forward consistency $\ge 60\%$, beating 95th percentile random baseline, and Deflated Sharpe Ratio $> 0.50$).

Accordingly, **Case B is fully established and applied**:
1. Ordinary production live entries remain disabled (`live.normal_trading_disabled: true`).
2. The 2026-11-08 brain holdout was strictly preserved and never touched.
3. All six strategy families are implemented as live signal generators (shadow by default).
4. `demo_exploration` is enabled at minimum risk (0.1% per trade) to collect forward out-of-sample data on DEMO while strictly obeying all locked risk ceilings, session filters, and cost gates.

---

## 2. Empirical Research Summary (from reports/edge_research_v2.md)

| Family | Variant | N (Tr/Val) | Win% | EV Train | EV Val | PF | Max DD | WF Share | Random 95% | DSR | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Session Breakout | v1 (M15 buf 0.1, sl 1.5, tp 2.0) | 1343/34 | 43.1% | -0.0817 | -0.1054 | 0.86 | 116.35R | 0% | FAIL | 0.00 | FAIL |
| Session Breakout | v2 (M15 buf 0.2, sl 1.0, tp 2.0) | 631/19 | 32.8% | -0.1350 | +0.0251 | 0.81 | 90.73R | 0% | FAIL | 0.00 | FAIL |
| Session Breakout | v3 (H1 buf 0.0, sl 1.5, tp 2.5) | 4676/52 | 41.1% | -0.0370 | +0.1365 | 0.94 | 184.80R | 17% | FAIL | 0.00 | FAIL |
| Index Opening Range Breakout | v1 (M15 30m ORB, sl 1.0, tp 1.5) | 1191/33 | 43.1% | -0.0354 | +0.1909 | 0.95 | 59.85R | 50% | FAIL | 0.00 | FAIL |
| Index Opening Range Breakout | v2 (M15 30m ORB + SMA50, sl 1.0, tp 2.0) | 978/31 | 38.3% | -0.0433 | +0.3063 | 0.95 | 49.75R | 50% | FAIL | 0.00 | FAIL |
| Index Opening Range Breakout | v3 (H1 60m ORB, sl 1.2, tp 2.0) | 3920/49 | 42.6% | -0.0310 | +0.0713 | 0.94 | 125.54R | 17% | FAIL | 0.00 | FAIL |
| VWAP Reversion | v1 (M15 dev 2.0 ATR, sl 1.5, tp VWAP) | 5330/136 | 45.2% | -0.0363 | -0.1183 | 0.93 | 282.02R | 33% | FAIL | 0.00 | FAIL |
| VWAP Reversion | v2 (M15 dev 2.5 ATR + RSI, sl 1.0, tp VWAP) | 663/19 | 32.1% | -0.0777 | +0.1305 | 0.90 | 64.92R | 33% | FAIL | 0.00 | FAIL |
| VWAP Reversion | v3 (H1 dev 2.0 ATR, sl 1.5, tp VWAP) | 7139/72 | 44.1% | -0.0720 | -0.1323 | 0.85 | 528.35R | 0% | FAIL | 0.00 | FAIL |
| Donchian Breakout | v1 (H4 20-period, sl 2.0, tp 4.0) | 6137/38 | 39.8% | -0.0319 | -0.5840 | 0.94 | 230.61R | 17% | FAIL | 0.00 | FAIL |
| Donchian Breakout | v2 (H4 55-period, sl 2.5, tp 5.0) | 3281/22 | 39.4% | -0.0423 | -0.3680 | 0.92 | 170.11R | 17% | FAIL | 0.00 | FAIL |
| Donchian Breakout | v3 (D1 20-period, sl 2.0, tp 4.0) | 2065/3 | 42.8% | +0.0057 | -0.0052 | 1.01 | 41.55R | 50% | FAIL | 0.00 | FAIL |
| Time-Series Momentum | v1 (H4 12-bar, sl 2.0, tp 3.0) | 11033/74 | 43.9% | -0.0274 | -0.2205 | 0.94 | 345.97R | 17% | FAIL | 0.00 | FAIL |
| Time-Series Momentum | v2 (H4 30-bar, sl 2.5, tp 4.0) | 6068/44 | 43.5% | -0.0140 | -0.1768 | 0.97 | 108.77R | 50% | FAIL | 0.00 | FAIL |
| Time-Series Momentum | v3 (D1 20-bar, sl 2.5, tp 4.0) | 2492/7 | 45.9% | -0.0042 | -0.0796 | 0.99 | 45.35R | 50% | FAIL | 0.00 | FAIL |
| Index Pullback in 200-Day Uptrend | v1 (D1 SMA200 + RSI<40, sl 1.5, tp 2.5) | 216/2 | 49.1% | +0.1926 | -0.3824 | 1.38 | 7.25R | 83% | FAIL | 0.00 | FAIL |
| Index Pullback in 200-Day Uptrend | v2 (D1 SMA200 + 3 down days, sl 2.0, tp 3.0) | 462/3 | 51.2% | +0.0431 | -0.2528 | 1.10 | 15.22R | 67% | FAIL | 0.00 | FAIL |
| Index Pullback in 200-Day Uptrend | v3 (H4 SMA1200 + RSI<30, sl 1.5, tp 2.5) | 341/4 | 37.4% | -0.0464 | -0.3499 | 0.92 | 26.30R | 33% | FAIL | 0.00 | FAIL |

---

## 3. Key Analytical Insights

1. **Transaction Costs Dominance:** After deducting the conservative round-trip friction (spread x 1.25 + slippage + commission), mechanical entry rules exhibit negative expectancy on raw uncurated signals.
2. **Subperiod Instability:** Strategies that appeared marginally profitable in the bull run up to September 2026 (such as Index Pullback v1 with +0.19R) suffered severe drawdowns in the subsequent chop of October 2026.
3. **Exploration Function:** Rather than forcing trades through unproven models in full sizing, DEMO exploration collects forward data at minimal risk (0.1%) to evaluate whether machine learning filters (Brain memory & checklist) can isolate positive subsets.
