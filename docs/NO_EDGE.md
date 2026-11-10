# Final Empirical No-Edge Policy: Case B Applied (v3 Research Splits)

## 1. Decision & Status

**Status:** Completed Case B (Empirical Research v3 Finished on 2026-11-10).

Systematic edge research v3 over all six strategy families across 18 parameter variants was executed against time-based splits:
- **M15/H1 Intraday:** Train `<= 2025-12-31`, Validation `2026-01-01` .. `2026-09-30` (9 months).
- **H4/D1 Swing:** Train `<= 2024-06-30`, Validation `2024-07-01` .. `2026-09-30` (27 months).
- **Brain Holdout:** `2026-10-20` onwards strictly untouched.

Costs were evaluated under Conservative Cost Model v1 ($1.25 \times \text{spread} + \text{slippage} + \text{commission}$) with the minimum validation toolkit (random benchmark with 200 reps, 6-window walk-forward, Deflated Sharpe Ratio with $M=18$ trials, and Buy-and-Hold benchmark comparisons).

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
| Session Breakout | v1 (M15 buf 0.1, sl 1.5, tp 2.0) | 86/9 | 33.7% | -0.2836 | -0.2488 | 0.59 | 27.04R | 0% | FAIL | n/a (FX neutral) | 0.00 | FAIL |
| Session Breakout | v2 (M15 buf 0.2, sl 1.0, tp 2.0) | 29/1 | 23.3% | -0.3345 | -1.0992 | 0.56 | 9.91R | 33% | FAIL | n/a (FX neutral) | 0.00 | FAIL |
| Session Breakout | v3 (H1 buf 0.0, sl 1.5, tp 2.5) | 1446/123 | 42.2% | -0.0826 | -0.1815 | 0.83 | 140.92R | 0% | FAIL | n/a (FX neutral) | 0.00 | FAIL |
| Index Opening Range Breakout | v1 (M15 30m ORB, sl 1.0, tp 1.5) | 944/813 | 39.2% | -0.0658 | -0.1375 | 0.85 | 183.61R | 17% | FAIL | Tr:+55.1%, Val:+10.0% | 0.00 | FAIL |
| Index Opening Range Breakout | v2 (M15 30m ORB + SMA50, sl 1.0, tp 2.0) | 763/652 | 33.7% | -0.0744 | -0.1181 | 0.87 | 143.06R | 17% | FAIL | Tr:+55.1%, Val:+10.0% | 0.00 | FAIL |
| Index Opening Range Breakout | v3 (H1 60m ORB, sl 1.2, tp 2.0) | 4288/901 | 41.9% | -0.0207 | -0.0621 | 0.95 | 179.95R | 33% | FAIL | Tr:+55.1%, Val:+10.0% | 0.00 | FAIL |
| VWAP Reversion | v1 (M15 dev 2.0 ATR, sl 1.5, tp VWAP) | 3663/2317 | 41.2% | -0.0463 | -0.0523 | 0.92 | 368.53R | 0% | FAIL | Tr:+68.7%, Val:+7.3% | 0.00 | FAIL |
| VWAP Reversion | v2 (M15 dev 2.5 ATR + RSI, sl 1.0, tp VWAP) | 499/466 | 28.7% | -0.1009 | +0.0569 | 0.97 | 55.45R | 33% | FAIL | Tr:+68.7%, Val:+7.3% | 0.00 | FAIL |
| VWAP Reversion | v3 (H1 dev 2.0 ATR, sl 1.5, tp VWAP) | 4378/704 | 42.2% | -0.0804 | -0.0710 | 0.84 | 405.59R | 0% | FAIL | Tr:+68.7%, Val:+7.3% | 0.00 | FAIL |
| Donchian Breakout | v1 (H4 20-period, sl 2.0, tp 4.0) | 4430/1300 | 34.6% | -0.0518 | +0.0202 | 0.95 | 255.31R | 33% | FAIL | Tr:+63.0%, Val:+47.6% | 0.00 | FAIL |
| Donchian Breakout | v2 (H4 55-period, sl 2.5, tp 5.0) | 2346/702 | 34.9% | -0.0233 | -0.0111 | 0.97 | 118.70R | 50% | FAIL | Tr:+63.0%, Val:+47.6% | 0.00 | FAIL |
| Donchian Breakout | v3 (D1 20-period, sl 2.0, tp 4.0) | 1661/235 | 37.8% | +0.0057 | +0.1157 | 1.03 | 40.11R | 50% | FAIL | Tr:+63.0%, Val:+47.6% | 0.00 | FAIL |
| Time-Series Momentum | v1 (H4 12-bar, sl 2.0, tp 3.0) | 7538/2238 | 41.3% | -0.0340 | -0.0161 | 0.95 | 321.72R | 17% | FAIL | Tr:+63.0%, Val:+47.6% | 0.00 | FAIL |
| Time-Series Momentum | v2 (H4 30-bar, sl 2.5, tp 4.0) | 4207/1177 | 40.4% | -0.0324 | +0.0588 | 0.98 | 154.15R | 50% | FAIL | Tr:+63.0%, Val:+47.6% | 0.00 | FAIL |
| Time-Series Momentum | v3 (D1 20-bar, sl 2.5, tp 4.0) | 1947/275 | 44.1% | -0.0158 | +0.0854 | 0.99 | 56.30R | 50% | FAIL | Tr:+63.0%, Val:+47.6% | 0.00 | FAIL |
| Index Pullback in 200-Day Uptrend | v1 (D1 SMA200 + RSI<40, sl 1.5, tp 2.5) | 174/36 | 47.1% | +0.1921 | +0.3562 | 1.41 | 9.85R | 83% | FAIL | Tr:+65.6%, Val:+39.7% | 0.00 | FAIL |
| Index Pullback in 200-Day Uptrend | v2 (D1 SMA200 + 3 down days, sl 2.0, tp 3.0) | 322/67 | 44.7% | +0.0077 | +0.3356 | 1.12 | 11.54R | 50% | FAIL | Tr:+65.6%, Val:+39.7% | 0.00 | FAIL |
| Index Pullback in 200-Day Uptrend | v3 (H4 SMA1200 + RSI<30, sl 1.5, tp 2.5) | 224/116 | 37.1% | -0.0583 | -0.0102 | 0.94 | 28.86R | 33% | FAIL | Tr:+65.6%, Val:+39.7% | 0.00 | FAIL |

---

## 3. Key Analytical Insights

1. **Transaction Costs Dominance:** After deducting conservative round-trip friction ($1.25 \times \text{spread} + \text{slippage} + \text{commission}$), raw mechanical entry rules exhibit negative expectancy across large out-of-sample periods.
2. **Buy-and-Hold Drift vs. Skill:** While indices gained +55% to +123% over train and +10% to +52% over validation, long-only pullback rules gained positive raw EV primarily due to underlying asset upward drift rather than entry timing timing skill (failing random-entry benchmarks).
3. **Donchian Breakout v3 (D1):** Produced positive net EV on both train (+0.0057R) and validation (+0.1157R) with profit factor 1.03, but failed the 60% walk-forward consistency threshold (50%) and random baseline.
4. **Exploration Function:** Rather than risking capital on unproven mechanical rules, DEMO exploration collects forward live trade data at minimal 0.1% risk to evaluate execution and ML filtering.
