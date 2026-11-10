# Systematic Edge Research v4 Ultra Low: Six Families, Forex + Gold

**Date:** 2026-11-10 14:26:13 UTC
**Splits Applied:**
- **M15/H1 Intraday:** Train `<= 2025-12-31`, Validation `2026-01-01` .. `2026-09-30` (9 months).
- **H4/D1 Swing:** Train `<= 2024-06-30`, Validation `2024-07-01` .. `2026-09-30` (27 months).
- **Protected holdout:** observations from `2026-10-20` onward are excluded from feature and outcome scoring.
- Trades whose full holding horizon would cross a train/validation cutoff are purged; holdout entries are not simulated.
**Cost Model:** Enabled # symbol M1 median spread × 1.25; no added slippage or commission assumption.
**Benchmark Included:** Buy-and-hold returns for the same forex + gold research universe.
**Multiple Testing Control:** Deflated Sharpe Ratio with $M=18$ trials (threshold $DSR > 0$).

## 1. Summary of Results

| Family | Variant | N (Tr/Val) | Win% | EV Train | EV Val | PF | Max DD | WF Share | Random 95% | Buy-and-Hold | DSR | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Session Breakout | v1 (M15 buf 0.1, sl 1.5, tp 2.0) | 1169/237 | 43.7% | -0.0418 | -0.1668 | 0.89 | 90.05R | 33% | FAIL (p95=+0.048) | n/a (FX neutral) | 0.00 | FAIL (EV not pos on both (tr:-0.042, val:-0.167); N < 300 (tr:1169, val:237); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Session Breakout | v2 (M15 buf 0.2, sl 1.0, tp 2.0) | 356/52 | 33.3% | -0.0384 | -0.5355 | 0.86 | 60.28R | 50% | FAIL (p95=+0.402) | n/a (FX neutral) | 0.00 | FAIL (EV not pos on both (tr:-0.038, val:-0.535); N < 300 (tr:356, val:52); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Session Breakout | v3 (H1 buf 0.0, sl 1.5, tp 2.5) | 6362/819 | 41.9% | -0.0604 | -0.0059 | 0.90 | 393.73R | 0% | FAIL (p95=+0.072) | n/a (FX neutral) | 0.00 | FAIL (EV not pos on both (tr:-0.060, val:-0.006); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Opening Range Breakout | v1 (M15 30m ORB, sl 1.0, tp 1.5) | 733/324 | 39.7% | -0.0968 | -0.0592 | 0.86 | 96.74R | 0% | FAIL (p95=+0.148) | Tr:+22.3%, Val:-0.8% | 0.00 | FAIL (EV not pos on both (tr:-0.097, val:-0.059); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Opening Range Breakout | v2 (M15 30m ORB + SMA50, sl 1.0, tp 2.0) | 521/221 | 34.2% | -0.0768 | -0.1050 | 0.87 | 66.87R | 33% | FAIL (p95=+0.345) | Tr:+22.3%, Val:-0.8% | 0.00 | FAIL (EV not pos on both (tr:-0.077, val:-0.105); N < 300 (tr:521, val:221); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Opening Range Breakout | v3 (H1 60m ORB, sl 1.2, tp 2.0) | 5252/764 | 43.6% | -0.0603 | -0.1014 | 0.86 | 406.79R | 0% | FAIL (p95=-0.002) | Tr:+22.3%, Val:-0.8% | 0.00 | FAIL (EV not pos on both (tr:-0.060, val:-0.101); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v1 (M15 dev 2.0 ATR, sl 1.5, tp VWAP) | 3438/1002 | 41.6% | -0.0592 | -0.0104 | 0.92 | 249.41R | 33% | FAIL (p95=+0.099) | Tr:+33.5%, Val:-1.1% | 0.00 | FAIL (EV not pos on both (tr:-0.059, val:-0.010); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v2 (M15 dev 2.5 ATR + RSI, sl 1.0, tp VWAP) | 466/211 | 30.0% | -0.0263 | +0.0187 | 0.98 | 57.40R | 50% | FAIL (p95=+0.697) | Tr:+33.5%, Val:-1.1% | 0.00 | FAIL (EV not pos on both (tr:-0.026, val:0.019); N < 300 (tr:466, val:211); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v3 (H1 dev 2.0 ATR, sl 1.5, tp VWAP) | 4673/631 | 44.5% | -0.0595 | -0.0556 | 0.87 | 316.86R | 0% | FAIL (p95=-0.005) | Tr:+33.5%, Val:-1.1% | 0.00 | FAIL (EV not pos on both (tr:-0.060, val:-0.056); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v1 (H4 20-period, sl 2.0, tp 4.0) | 3544/1008 | 35.0% | -0.0380 | +0.0514 | 0.97 | 189.19R | 17% | FAIL (p95=+0.414) | Tr:+18.3%, Val:+19.7% | 0.00 | FAIL (EV not pos on both (tr:-0.038, val:0.051); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v2 (H4 55-period, sl 2.5, tp 5.0) | 1831/529 | 34.9% | -0.0237 | +0.0256 | 0.98 | 110.26R | 50% | FAIL (p95=+0.448) | Tr:+18.3%, Val:+19.7% | 0.00 | FAIL (EV not pos on both (tr:-0.024, val:0.026); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v3 (D1 20-period, sl 2.0, tp 4.0) | 1094/185 | 36.7% | +0.0073 | -0.0063 | 1.01 | 40.06R | 33% | FAIL (p95=+0.404) | Tr:+18.3%, Val:+19.7% | 0.00 | FAIL (EV not pos on both (tr:0.007, val:-0.006); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v1 (H4 12-bar, sl 2.0, tp 3.0) | 6083/1758 | 41.8% | -0.0163 | -0.0117 | 0.97 | 144.64R | 17% | FAIL (p95=+0.170) | Tr:+18.3%, Val:+19.7% | 0.00 | FAIL (EV not pos on both (tr:-0.016, val:-0.012); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v2 (H4 30-bar, sl 2.5, tp 4.0) | 3344/919 | 40.4% | -0.0230 | +0.0417 | 0.98 | 96.59R | 33% | FAIL (p95=+0.228) | Tr:+18.3%, Val:+19.7% | 0.00 | FAIL (EV not pos on both (tr:-0.023, val:0.042); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v3 (D1 20-bar, sl 2.5, tp 4.0) | 1278/226 | 45.0% | +0.0120 | -0.0057 | 1.02 | 26.36R | 33% | FAIL (p95=+0.142) | Tr:+18.3%, Val:+19.7% | 0.00 | FAIL (EV not pos on both (tr:0.012, val:-0.006); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v1 (D1 SMA200 + RSI<40, sl 1.5, tp 2.5) | 186/42 | 45.2% | +0.1282 | +0.1611 | 1.25 | 9.52R | 67% | FAIL (p95=+0.362) | Tr:+14.1%, Val:+12.3% | 0.00 | FAIL (N < 100 (tr:186, val:42); fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v2 (D1 SMA200 + 3 down days, sl 2.0, tp 3.0) | 427/95 | 46.6% | +0.0736 | +0.3187 | 1.24 | 15.68R | 67% | FAIL (p95=+0.247) | Tr:+14.1%, Val:+12.3% | 0.00 | FAIL (N < 100 (tr:427, val:95); fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v3 (H4 SMA1200 + RSI<30, sl 1.5, tp 2.5) | 329/150 | 40.9% | +0.0283 | +0.1008 | 1.08 | 16.74R | 67% | FAIL (p95=+0.347) | Tr:+14.1%, Val:+12.3% | 0.00 | FAIL (fails p95 benchmark; DSR 0.00 <= 0) |

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
- Research findings are report-only; they do not change normal-entry settings.
- DEMO exploration continues running for all families at 0.1% minimum risk.

## 3. Buy-and-Hold Drift vs. Strategy Skill Analysis

Buy-and-hold returns for the symbols in this report's benchmark scope:
- **EURUSD:** Intraday M15/H1: Train +9.8%, Val -4.1% | H4/D1: Train -3.9%, Val +4.6%.
- **GBPUSD:** Intraday M15/H1: Train +10.0%, Val -2.0% | H4/D1: Train -3.7%, Val +4.0%.
- **USDJPY:** Intraday M15/H1: Train +3.5%, Val +0.8% | H4/D1: Train +48.7%, Val -2.1%.
- **AUDUSD:** Intraday M15/H1: Train +4.9%, Val +3.5% | H4/D1: Train -4.7%, Val +3.9%.
- **USDCAD:** Intraday M15/H1: Train -0.6%, Val +3.6% | H4/D1: Train +5.8%, Val +4.0%.
- **EURJPY:** Intraday M15/H1: Train +13.7%, Val -3.3% | H4/D1: Train +7.4%, Val +2.5%.
- **GBPJPY:** Intraday M15/H1: Train +13.9%, Val -1.2% | H4/D1: Train +10.4%, Val +1.9%.
- **GOLD:** Intraday M15/H1: Train +123.0%, Val -3.6% | H4/D1: Train +52.5%, Val +79.3%.

Strategy results are evaluated after the configured execution-cost model; benchmark returns are contextual and do not change qualification.

## Live DEMO cost snapshot

Account: DEMO `XMGlobal-MT5 5`, login ending `323`, balance `$10,000.00`; sampled `2026-11-10T13:45:41.751330+00:00` through `2026-11-10T14:25:38.000280+00:00` UTC during London/New York overlap.
Spreads are M1 live samples from enabled `#` symbols; each median spans at least 30 minutes. Offline research retains the v4 spread-cost formula: median live spread × loss tick value × 1.25, with no added slippage or commission.

| Symbol | Live name | Median spread (min–max) | Samples | Cost/lot after ×1.25 |
|---|---|---:|---:|---:|
| EURUSD | `EURUSD#` | 1.10 pips (1.00–1.20) | 30 | $13.75 |
| GBPUSD | `GBPUSD#` | 1.30 pips (1.10–1.50) | 30 | $16.25 |
| USDJPY | `USDJPY#` | 1.20 pips (1.00–1.50) | 30 | $9.46 |
| AUDUSD | `AUDUSD#` | 1.40 pips (1.30–1.50) | 30 | $17.50 |
| USDCAD | `USDCAD#` | 2.30 pips (2.10–2.50) | 30 | $20.29 |
| EURJPY | `EURJPY#` | 2.10 pips (1.80–2.50) | 38 | $16.60 |
| GBPJPY | `GBPJPY#` | 2.90 pips (2.40–3.20) | 39 | $22.92 |
| GOLD | `GOLD#` | $0.31 ($0.26–$0.33) | 39 | $38.75 |

## Typical 0.1% exploration sizing and cost gates

For each family stop, the reference distance is median ATR(14) from 2026-01-01 through 2026-09-30 times its unchanged variant stop multiple. Minimum-lot risk is tested against the live DEMO 0.1% budget ($10); cost gate is strict `<10%` of stop value. This matrix isolates these two gates; news, MTF, sessions, broker stops, margin, and other hard protections remain separately enforced.

| Family / variant | TF | Both pass | Min-lot fails | Cost gate fails |
|---|---|---|---|---|
| Session Breakout · v1 M15 | M15 | none | none | EURUSD (17.8%), GBPUSD (15.8%), USDJPY (12.1%), AUDUSD (24.1%), USDCAD (38.0%), EURJPY (20.0%), GBPJPY (21.3%) |
| Session Breakout · v2 M15 | M15 | none | none | EURUSD (26.7%), GBPUSD (23.7%), USDJPY (18.2%), AUDUSD (36.2%), USDCAD (57.0%), EURJPY (30.0%), GBPJPY (31.9%) |
| Session Breakout · v3 H1 | H1 | EURUSD, GBPUSD, USDJPY, EURJPY | none | AUDUSD (11.6%), USDCAD (18.2%), GBPJPY (10.4%) |
| Index Opening Range Breakout · v1 M15 | M15 | GOLD | none | EURUSD (26.7%), GBPUSD (23.7%), USDJPY (18.2%), AUDUSD (36.2%), USDCAD (57.0%), EURJPY (30.0%), GBPJPY (31.9%) |
| Index Opening Range Breakout · v2 M15 | M15 | GOLD | none | EURUSD (26.7%), GBPUSD (23.7%), USDJPY (18.2%), AUDUSD (36.2%), USDCAD (57.0%), EURJPY (30.0%), GBPJPY (31.9%) |
| Index Opening Range Breakout · v3 H1 | H1 | GBPUSD, USDJPY | GOLD ($23.47) | EURUSD (10.6%), AUDUSD (14.5%), USDCAD (22.7%), EURJPY (12.3%), GBPJPY (12.9%) |
| VWAP Reversion · v1 M15 | M15 | none | GOLD ($14.02) | EURUSD (17.8%), GBPUSD (15.8%), USDJPY (12.1%), AUDUSD (24.1%), USDCAD (38.0%), EURJPY (20.0%), GBPJPY (21.3%) |
| VWAP Reversion · v2 M15 | M15 | GOLD | none | EURUSD (26.7%), GBPUSD (23.7%), USDJPY (18.2%), AUDUSD (36.2%), USDCAD (57.0%), EURJPY (30.0%), GBPJPY (31.9%) |
| VWAP Reversion · v3 H1 | H1 | EURUSD, GBPUSD, USDJPY, EURJPY | GOLD ($29.33) | AUDUSD (11.6%), USDCAD (18.2%), GBPJPY (10.4%) |
| Donchian Breakout · v1 H4 | H4 | EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURJPY, GBPJPY | GOLD ($79.72) | none |
| Donchian Breakout · v2 H4 | H4 | EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURJPY, GBPJPY | GOLD ($99.65) | none |
| Donchian Breakout · v3 D1 | D1 | USDCAD | EURUSD ($12.41), GBPUSD ($16.67), USDJPY ($13.42), AUDUSD ($11.71), EURJPY ($13.44), GBPJPY ($16.83), GOLD ($221.45) | none |
| Time-Series Momentum · v1 H4 | H4 | EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURJPY, GBPJPY | GOLD ($79.72) | none |
| Time-Series Momentum · v2 H4 | H4 | EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURJPY, GBPJPY | GOLD ($99.65) | none |
| Time-Series Momentum · v3 D1 | D1 | none | EURUSD ($15.51), GBPUSD ($20.84), USDJPY ($16.78), AUDUSD ($14.63), USDCAD ($10.20), EURJPY ($16.80), GBPJPY ($21.04), GOLD ($276.82) | none |
| Index Pullback in 200-Day Uptrend · v1 D1 | D1 | EURUSD, AUDUSD, USDCAD | GBPUSD ($12.50), USDJPY ($10.07), EURJPY ($10.08), GBPJPY ($12.62), GOLD ($166.09) | none |
| Index Pullback in 200-Day Uptrend · v2 D1 | D1 | USDCAD | EURUSD ($12.41), GBPUSD ($16.67), USDJPY ($13.42), AUDUSD ($11.71), EURJPY ($13.44), GBPJPY ($16.83), GOLD ($221.45) | none |
| Index Pullback in 200-Day Uptrend · v3 H4 | H4 | EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURJPY, GBPJPY | GOLD ($59.79) | none |

## Side-by-side: v3 baseline vs v4 Ultra Low

Variant parameters, split boundaries, holdout protection, simulator, and 18-trial qualification tests are unchanged. V3 used its earlier 5-FX + 4-index + GOLD universe/costs; v4 evaluates 7 forex pairs + GOLD, so this is an operational comparison across the requested universe rather than a controlled same-universe cost-only ablation.

| Family | Variant | V3 N | V3 EV train | V3 EV val | V3 PF | V4 N | V4 EV train | V4 EV val | V4 PF | V4 status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Session Breakout | v1 (M15 buf 0.1, sl 1.5, tp 2.0) | 86/9 | -0.2836 | -0.2488 | 0.59 | 1169/237 | -0.0418 | -0.1668 | 0.89 | FAIL (EV not pos on both (tr:-0.042, val:-0.167); N < 300 (tr:1169, val:237); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Session Breakout | v2 (M15 buf 0.2, sl 1.0, tp 2.0) | 29/1 | -0.3345 | -1.0992 | 0.56 | 356/52 | -0.0384 | -0.5355 | 0.86 | FAIL (EV not pos on both (tr:-0.038, val:-0.535); N < 300 (tr:356, val:52); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Session Breakout | v3 (H1 buf 0.0, sl 1.5, tp 2.5) | 1446/123 | -0.0826 | -0.1815 | 0.83 | 6362/819 | -0.0604 | -0.0059 | 0.90 | FAIL (EV not pos on both (tr:-0.060, val:-0.006); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Opening Range Breakout | v1 (M15 30m ORB, sl 1.0, tp 1.5) | 944/813 | -0.0658 | -0.1375 | 0.85 | 733/324 | -0.0968 | -0.0592 | 0.86 | FAIL (EV not pos on both (tr:-0.097, val:-0.059); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Opening Range Breakout | v2 (M15 30m ORB + SMA50, sl 1.0, tp 2.0) | 763/652 | -0.0744 | -0.1181 | 0.87 | 521/221 | -0.0768 | -0.1050 | 0.87 | FAIL (EV not pos on both (tr:-0.077, val:-0.105); N < 300 (tr:521, val:221); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Opening Range Breakout | v3 (H1 60m ORB, sl 1.2, tp 2.0) | 4286/899 | -0.0204 | -0.0629 | 0.95 | 5252/764 | -0.0603 | -0.1014 | 0.86 | FAIL (EV not pos on both (tr:-0.060, val:-0.101); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v1 (M15 dev 2.0 ATR, sl 1.5, tp VWAP) | 3661/2313 | -0.0458 | -0.0529 | 0.92 | 3438/1002 | -0.0592 | -0.0104 | 0.92 | FAIL (EV not pos on both (tr:-0.059, val:-0.010); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v2 (M15 dev 2.5 ATR + RSI, sl 1.0, tp VWAP) | 499/465 | -0.1009 | +0.0519 | 0.96 | 466/211 | -0.0263 | +0.0187 | 0.98 | FAIL (EV not pos on both (tr:-0.026, val:0.019); N < 300 (tr:466, val:211); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v3 (H1 dev 2.0 ATR, sl 1.5, tp VWAP) | 4374/700 | -0.0818 | -0.0725 | 0.83 | 4673/631 | -0.0595 | -0.0556 | 0.87 | FAIL (EV not pos on both (tr:-0.060, val:-0.056); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v1 (H4 20-period, sl 2.0, tp 4.0) | 4412/1281 | -0.0500 | +0.0132 | 0.95 | 3544/1008 | -0.0380 | +0.0514 | 0.97 | FAIL (EV not pos on both (tr:-0.038, val:0.051); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v2 (H4 55-period, sl 2.5, tp 5.0) | 2333/681 | -0.0204 | -0.0212 | 0.97 | 1831/529 | -0.0237 | +0.0256 | 0.98 | FAIL (EV not pos on both (tr:-0.024, val:0.026); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v3 (D1 20-period, sl 2.0, tp 4.0) | 1643/225 | +0.0074 | +0.1150 | 1.03 | 1094/185 | +0.0073 | -0.0063 | 1.01 | FAIL (EV not pos on both (tr:0.007, val:-0.006); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v1 (H4 12-bar, sl 2.0, tp 3.0) | 7516/2218 | -0.0342 | -0.0148 | 0.95 | 6083/1758 | -0.0163 | -0.0117 | 0.97 | FAIL (EV not pos on both (tr:-0.016, val:-0.012); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v2 (H4 30-bar, sl 2.5, tp 4.0) | 4185/1164 | -0.0318 | +0.0605 | 0.98 | 3344/919 | -0.0230 | +0.0417 | 0.98 | FAIL (EV not pos on both (tr:-0.023, val:0.042); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v3 (D1 20-bar, sl 2.5, tp 4.0) | 1935/267 | -0.0143 | +0.0462 | 0.99 | 1278/226 | +0.0120 | -0.0057 | 1.02 | FAIL (EV not pos on both (tr:0.012, val:-0.006); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v1 (D1 SMA200 + RSI<40, sl 1.5, tp 2.5) | 172/33 | +0.1750 | +0.4803 | 1.42 | 186/42 | +0.1282 | +0.1611 | 1.25 | FAIL (N < 100 (tr:186, val:42); fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v2 (D1 SMA200 + 3 down days, sl 2.0, tp 3.0) | 316/64 | -0.0126 | +0.3985 | 1.10 | 427/95 | +0.0736 | +0.3187 | 1.24 | FAIL (N < 100 (tr:427, val:95); fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v3 (H4 SMA1200 + RSI<30, sl 1.5, tp 2.5) | 223/116 | -0.0659 | -0.0102 | 0.93 | 329/150 | +0.0283 | +0.1008 | 1.08 | FAIL (fails p95 benchmark; DSR 0.00 <= 0) |

## Corrected enabled-symbol spreads vs previous v4

Previous v4 decision: `Case B`. Corrected enabled-`#`-symbol decision: `Case B`.

| Family | Variant | Prior v4 N | Prior EV train | Prior EV val | Prior PF | Corrected N | Corrected EV train | Corrected EV val | Corrected PF | Corrected status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Session Breakout | v1 (M15 buf 0.1, sl 1.5, tp 2.0) | 379/49 | -0.0749 | -0.4546 | 0.81 | 1169/237 | -0.0418 | -0.1668 | 0.89 | FAIL (EV not pos on both (tr:-0.042, val:-0.167); N < 300 (tr:1169, val:237); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Session Breakout | v2 (M15 buf 0.2, sl 1.0, tp 2.0) | 97/11 | -0.0987 | +0.4061 | 0.93 | 356/52 | -0.0384 | -0.5355 | 0.86 | FAIL (EV not pos on both (tr:-0.038, val:-0.535); N < 300 (tr:356, val:52); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Session Breakout | v3 (H1 buf 0.0, sl 1.5, tp 2.5) | 3931/392 | -0.0608 | -0.0723 | 0.88 | 6362/819 | -0.0604 | -0.0059 | 0.90 | FAIL (EV not pos on both (tr:-0.060, val:-0.006); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Opening Range Breakout | v1 (M15 30m ORB, sl 1.0, tp 1.5) | 456/266 | -0.0955 | -0.0176 | 0.89 | 733/324 | -0.0968 | -0.0592 | 0.86 | FAIL (EV not pos on both (tr:-0.097, val:-0.059); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Opening Range Breakout | v2 (M15 30m ORB + SMA50, sl 1.0, tp 2.0) | 326/172 | -0.0749 | -0.0158 | 0.92 | 521/221 | -0.0768 | -0.1050 | 0.87 | FAIL (EV not pos on both (tr:-0.077, val:-0.105); N < 300 (tr:521, val:221); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Opening Range Breakout | v3 (H1 60m ORB, sl 1.2, tp 2.0) | 3385/405 | -0.0705 | -0.1129 | 0.84 | 5252/764 | -0.0603 | -0.1014 | 0.86 | FAIL (EV not pos on both (tr:-0.060, val:-0.101); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v1 (M15 dev 2.0 ATR, sl 1.5, tp VWAP) | 2002/627 | -0.0495 | -0.0067 | 0.93 | 3438/1002 | -0.0592 | -0.0104 | 0.92 | FAIL (EV not pos on both (tr:-0.059, val:-0.010); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v2 (M15 dev 2.5 ATR + RSI, sl 1.0, tp VWAP) | 332/186 | -0.0529 | -0.0242 | 0.94 | 466/211 | -0.0263 | +0.0187 | 0.98 | FAIL (EV not pos on both (tr:-0.026, val:0.019); N < 300 (tr:466, val:211); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v3 (H1 dev 2.0 ATR, sl 1.5, tp VWAP) | 3330/376 | -0.0794 | -0.1379 | 0.82 | 4673/631 | -0.0595 | -0.0556 | 0.87 | FAIL (EV not pos on both (tr:-0.060, val:-0.056); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v1 (H4 20-period, sl 2.0, tp 4.0) | 3528/1001 | -0.0521 | +0.0413 | 0.95 | 3544/1008 | -0.0380 | +0.0514 | 0.97 | FAIL (EV not pos on both (tr:-0.038, val:0.051); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v2 (H4 55-period, sl 2.5, tp 5.0) | 1831/529 | -0.0331 | +0.0160 | 0.97 | 1831/529 | -0.0237 | +0.0256 | 0.98 | FAIL (EV not pos on both (tr:-0.024, val:0.026); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v3 (D1 20-period, sl 2.0, tp 4.0) | 1094/185 | +0.0021 | -0.0108 | 1.00 | 1094/185 | +0.0073 | -0.0063 | 1.01 | FAIL (EV not pos on both (tr:0.007, val:-0.006); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v1 (H4 12-bar, sl 2.0, tp 3.0) | 6042/1728 | -0.0266 | -0.0258 | 0.96 | 6083/1758 | -0.0163 | -0.0117 | 0.97 | FAIL (EV not pos on both (tr:-0.016, val:-0.012); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v2 (H4 30-bar, sl 2.5, tp 4.0) | 3341/918 | -0.0329 | +0.0333 | 0.97 | 3344/919 | -0.0230 | +0.0417 | 0.98 | FAIL (EV not pos on both (tr:-0.023, val:0.042); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v3 (D1 20-bar, sl 2.5, tp 4.0) | 1278/226 | +0.0078 | -0.0094 | 1.01 | 1278/226 | +0.0120 | -0.0057 | 1.02 | FAIL (EV not pos on both (tr:0.012, val:-0.006); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v1 (D1 SMA200 + RSI<40, sl 1.5, tp 2.5) | 186/42 | +0.1217 | +0.1544 | 1.23 | 186/42 | +0.1282 | +0.1611 | 1.25 | FAIL (N < 100 (tr:186, val:42); fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v2 (D1 SMA200 + 3 down days, sl 2.0, tp 3.0) | 427/95 | +0.0686 | +0.3140 | 1.22 | 427/95 | +0.0736 | +0.3187 | 1.24 | FAIL (N < 100 (tr:427, val:95); fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v3 (H4 SMA1200 + RSI<30, sl 1.5, tp 2.5) | 322/131 | +0.0412 | +0.1359 | 1.11 | 329/150 | +0.0283 | +0.1008 | 1.08 | FAIL (fails p95 benchmark; DSR 0.00 <= 0) |

**Research decision:** `Case B`.
No automatic transition from research qualification to normal trading is made by this script. DEMO exploration and the existing safety gates remain separate from this report.
