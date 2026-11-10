# Systematic Edge Research v4 Ultra Low: Six Families, Forex + Gold

**Date:** 2026-11-10 11:22:24 UTC
**Splits Applied:**
- **M15/H1 Intraday:** Train `<= 2025-12-31`, Validation `2026-01-01` .. `2026-09-30` (9 months).
- **H4/D1 Swing:** Train `<= 2024-06-30`, Validation `2024-07-01` .. `2026-09-30` (27 months).
- **Protected holdout:** observations from `2026-10-20` onward are excluded from feature and outcome scoring.
- Trades whose full holding horizon would cross a train/validation cutoff are purged; holdout entries are not simulated.
**Cost Model:** Live DEMO bid/ask spread × 1.25; no added slippage or commission assumption.
**Benchmark Included:** Buy-and-hold returns for the same forex + gold research universe.
**Multiple Testing Control:** Deflated Sharpe Ratio with $M=18$ trials (threshold $DSR > 0$).

## 1. Summary of Results

| Family | Variant | N (Tr/Val) | Win% | EV Train | EV Val | PF | Max DD | WF Share | Random 95% | Buy-and-Hold | DSR | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Session Breakout | v1 (M15 buf 0.1, sl 1.5, tp 2.0) | 379/49 | 41.6% | -0.0749 | -0.4546 | 0.81 | 52.15R | 0% | FAIL (p95=+0.069) | n/a (FX neutral) | 0.00 | FAIL (EV not pos on both (tr:-0.075, val:-0.455); N < 300 (tr:379, val:49); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Session Breakout | v2 (M15 buf 0.2, sl 1.0, tp 2.0) | 97/11 | 36.1% | -0.0987 | +0.4061 | 0.93 | 18.19R | 50% | FAIL (p95=+0.456) | n/a (FX neutral) | 0.00 | FAIL (EV not pos on both (tr:-0.099, val:0.406); N < 300 (tr:97, val:11); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Session Breakout | v3 (H1 buf 0.0, sl 1.5, tp 2.5) | 3931/392 | 42.4% | -0.0608 | -0.0723 | 0.88 | 277.82R | 17% | FAIL (p95=+0.047) | n/a (FX neutral) | 0.00 | FAIL (EV not pos on both (tr:-0.061, val:-0.072); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Opening Range Breakout | v1 (M15 30m ORB, sl 1.0, tp 1.5) | 456/266 | 40.0% | -0.0955 | -0.0176 | 0.89 | 49.70R | 17% | FAIL (p95=+0.166) | Tr:+22.3%, Val:-0.8% | 0.00 | FAIL (EV not pos on both (tr:-0.096, val:-0.018); N < 300 (tr:456, val:266); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Opening Range Breakout | v2 (M15 30m ORB + SMA50, sl 1.0, tp 2.0) | 326/172 | 34.5% | -0.0749 | -0.0158 | 0.92 | 37.56R | 17% | FAIL (p95=+0.393) | Tr:+22.3%, Val:-0.8% | 0.00 | FAIL (EV not pos on both (tr:-0.075, val:-0.016); N < 300 (tr:326, val:172); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Opening Range Breakout | v3 (H1 60m ORB, sl 1.2, tp 2.0) | 3385/405 | 42.9% | -0.0705 | -0.1129 | 0.84 | 300.10R | 0% | FAIL (p95=-0.001) | Tr:+22.3%, Val:-0.8% | 0.00 | FAIL (EV not pos on both (tr:-0.071, val:-0.113); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v1 (M15 dev 2.0 ATR, sl 1.5, tp VWAP) | 2002/627 | 41.6% | -0.0495 | -0.0067 | 0.93 | 140.10R | 50% | FAIL (p95=+0.129) | Tr:+33.5%, Val:-1.1% | 0.00 | FAIL (EV not pos on both (tr:-0.050, val:-0.007); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v2 (M15 dev 2.5 ATR + RSI, sl 1.0, tp VWAP) | 332/186 | 29.3% | -0.0529 | -0.0242 | 0.94 | 70.46R | 33% | FAIL (p95=+0.692) | Tr:+33.5%, Val:-1.1% | 0.00 | FAIL (EV not pos on both (tr:-0.053, val:-0.024); N < 300 (tr:332, val:186); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v3 (H1 dev 2.0 ATR, sl 1.5, tp VWAP) | 3330/376 | 43.8% | -0.0794 | -0.1379 | 0.82 | 318.80R | 0% | FAIL (p95=-0.022) | Tr:+33.5%, Val:-1.1% | 0.00 | FAIL (EV not pos on both (tr:-0.079, val:-0.138); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v1 (H4 20-period, sl 2.0, tp 4.0) | 3528/1001 | 34.9% | -0.0521 | +0.0413 | 0.95 | 239.25R | 17% | FAIL (p95=+0.393) | Tr:+18.3%, Val:+19.7% | 0.00 | FAIL (EV not pos on both (tr:-0.052, val:0.041); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v2 (H4 55-period, sl 2.5, tp 5.0) | 1831/529 | 34.8% | -0.0331 | +0.0160 | 0.97 | 127.79R | 50% | FAIL (p95=+0.433) | Tr:+18.3%, Val:+19.7% | 0.00 | FAIL (EV not pos on both (tr:-0.033, val:0.016); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v3 (D1 20-period, sl 2.0, tp 4.0) | 1094/185 | 36.7% | +0.0021 | -0.0108 | 1.00 | 41.21R | 33% | FAIL (p95=+0.394) | Tr:+18.3%, Val:+19.7% | 0.00 | FAIL (EV not pos on both (tr:0.002, val:-0.011); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v1 (H4 12-bar, sl 2.0, tp 3.0) | 6042/1728 | 41.8% | -0.0266 | -0.0258 | 0.96 | 223.31R | 0% | FAIL (p95=+0.148) | Tr:+18.3%, Val:+19.7% | 0.00 | FAIL (EV not pos on both (tr:-0.027, val:-0.026); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v2 (H4 30-bar, sl 2.5, tp 4.0) | 3341/918 | 40.4% | -0.0329 | +0.0333 | 0.97 | 128.35R | 33% | FAIL (p95=+0.210) | Tr:+18.3%, Val:+19.7% | 0.00 | FAIL (EV not pos on both (tr:-0.033, val:0.033); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v3 (D1 20-bar, sl 2.5, tp 4.0) | 1278/226 | 45.0% | +0.0078 | -0.0094 | 1.01 | 27.70R | 33% | FAIL (p95=+0.134) | Tr:+18.3%, Val:+19.7% | 0.00 | FAIL (EV not pos on both (tr:0.008, val:-0.009); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v1 (D1 SMA200 + RSI<40, sl 1.5, tp 2.5) | 186/42 | 45.2% | +0.1217 | +0.1544 | 1.23 | 9.69R | 67% | FAIL (p95=+0.349) | Tr:+14.1%, Val:+12.3% | 0.00 | FAIL (N < 100 (tr:186, val:42); fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v2 (D1 SMA200 + 3 down days, sl 2.0, tp 3.0) | 427/95 | 46.6% | +0.0686 | +0.3140 | 1.22 | 15.84R | 67% | FAIL (p95=+0.237) | Tr:+14.1%, Val:+12.3% | 0.00 | FAIL (N < 100 (tr:427, val:95); fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v3 (H4 SMA1200 + RSI<30, sl 1.5, tp 2.5) | 322/131 | 41.9% | +0.0412 | +0.1359 | 1.11 | 15.05R | 67% | FAIL (p95=+0.321) | Tr:+14.1%, Val:+12.3% | 0.00 | FAIL (fails p95 benchmark; DSR 0.00 <= 0) |

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

Account: DEMO `XMGlobal-MT5 5`, login ending `323`, balance `$10,000.00`; captured `2026-11-10T11:22:16.333603+00:00`.
Per-lot modeled cost is live `(ask − bid) / tick_size × loss_tick_value × 1.25`; the research uses the same sizing-independent stop-cost gate as v3. No slippage or commission is added.

| Symbol | Live name | Spread | Cost/lot after ×1.25 |
|---|---|---:|---:|
| EURUSD | `EURUSD` | 1.90 pips | $23.75 |
| GBPUSD | `GBPUSD` | 2.20 pips | $27.50 |
| USDJPY | `USDJPY` | 2.30 pips | $18.18 |
| AUDUSD | `AUDUSD` | 2.40 pips | $30.00 |
| USDCAD | `USDCAD` | 3.10 pips | $27.43 |
| EURJPY | `EURJPY#` | 2.10 pips | $16.60 |
| GBPJPY | `GBPJPY#` | 2.70 pips | $21.34 |
| GOLD | `GOLD#` | $0.29 | $36.25 |

## Typical 0.1% exploration sizing and cost gates

For each family stop, the reference distance is median ATR(14) from 2026-01-01 through 2026-09-30 times its unchanged variant stop multiple. Minimum-lot risk is tested against the live DEMO 0.1% budget ($10); cost gate is strict `<10%` of stop value. This matrix isolates these two gates; news, MTF, sessions, broker stops, margin, and other hard protections remain separately enforced.

| Family / variant | TF | Both pass | Min-lot fails | Cost gate fails |
|---|---|---|---|---|
| Session Breakout · v1 M15 | M15 | none | none | EURUSD (30.8%), GBPUSD (26.7%), USDJPY (23.2%), AUDUSD (41.4%), USDCAD (51.2%), EURJPY (20.0%), GBPJPY (19.8%) |
| Session Breakout · v2 M15 | M15 | none | none | EURUSD (46.2%), GBPUSD (40.1%), USDJPY (34.8%), AUDUSD (62.0%), USDCAD (76.8%), EURJPY (30.0%), GBPJPY (29.7%) |
| Session Breakout · v3 H1 | H1 | EURJPY, GBPJPY | none | EURUSD (14.6%), GBPUSD (12.5%), USDJPY (10.7%), AUDUSD (19.8%), USDCAD (24.5%) |
| Index Opening Range Breakout · v1 M15 | M15 | GOLD | none | EURUSD (46.2%), GBPUSD (40.1%), USDJPY (34.8%), AUDUSD (62.0%), USDCAD (76.8%), EURJPY (30.0%), GBPJPY (29.7%) |
| Index Opening Range Breakout · v2 M15 | M15 | GOLD | none | EURUSD (46.2%), GBPUSD (40.1%), USDJPY (34.8%), AUDUSD (62.0%), USDCAD (76.8%), EURJPY (30.0%), GBPJPY (29.7%) |
| Index Opening Range Breakout · v3 H1 | H1 | none | GOLD ($23.47) | EURUSD (18.2%), GBPUSD (15.6%), USDJPY (13.4%), AUDUSD (24.8%), USDCAD (30.6%), EURJPY (12.3%), GBPJPY (12.1%) |
| VWAP Reversion · v1 M15 | M15 | none | GOLD ($14.02) | EURUSD (30.8%), GBPUSD (26.7%), USDJPY (23.2%), AUDUSD (41.4%), USDCAD (51.2%), EURJPY (20.0%), GBPJPY (19.8%) |
| VWAP Reversion · v2 M15 | M15 | GOLD | none | EURUSD (46.2%), GBPUSD (40.1%), USDJPY (34.8%), AUDUSD (62.0%), USDCAD (76.8%), EURJPY (30.0%), GBPJPY (29.7%) |
| VWAP Reversion · v3 H1 | H1 | EURJPY, GBPJPY | GOLD ($29.33) | EURUSD (14.6%), GBPUSD (12.5%), USDJPY (10.7%), AUDUSD (19.8%), USDCAD (24.5%) |
| Donchian Breakout · v1 H4 | H4 | EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURJPY, GBPJPY | GOLD ($79.72) | none |
| Donchian Breakout · v2 H4 | H4 | EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURJPY, GBPJPY | GOLD ($99.65) | none |
| Donchian Breakout · v3 D1 | D1 | USDCAD | EURUSD ($12.41), GBPUSD ($16.67), USDJPY ($13.46), AUDUSD ($11.71), EURJPY ($13.44), GBPJPY ($16.83), GOLD ($221.45) | none |
| Time-Series Momentum · v1 H4 | H4 | EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURJPY, GBPJPY | GOLD ($79.72) | none |
| Time-Series Momentum · v2 H4 | H4 | EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURJPY, GBPJPY | GOLD ($99.65) | none |
| Time-Series Momentum · v3 D1 | D1 | none | EURUSD ($15.51), GBPUSD ($20.84), USDJPY ($16.82), AUDUSD ($14.63), USDCAD ($10.23), EURJPY ($16.79), GBPJPY ($21.03), GOLD ($276.82) | none |
| Index Pullback in 200-Day Uptrend · v1 D1 | D1 | EURUSD, AUDUSD, USDCAD | GBPUSD ($12.50), USDJPY ($10.09), EURJPY ($10.08), GBPJPY ($12.62), GOLD ($166.09) | none |
| Index Pullback in 200-Day Uptrend · v2 D1 | D1 | USDCAD | EURUSD ($12.41), GBPUSD ($16.67), USDJPY ($13.46), AUDUSD ($11.71), EURJPY ($13.44), GBPJPY ($16.83), GOLD ($221.45) | none |
| Index Pullback in 200-Day Uptrend · v3 H4 | H4 | EURUSD, GBPUSD, USDJPY, AUDUSD, EURJPY, GBPJPY | GOLD ($59.79) | USDCAD (11.8%) |

## Side-by-side: v3 baseline vs v4 Ultra Low

Variant parameters, split boundaries, holdout protection, simulator, and 18-trial qualification tests are unchanged. V3 used its earlier 5-FX + 4-index + GOLD universe/costs; v4 evaluates 7 forex pairs + GOLD, so this is an operational comparison across the requested universe rather than a controlled same-universe cost-only ablation.

| Family | Variant | V3 N | V3 EV train | V3 EV val | V3 PF | V4 N | V4 EV train | V4 EV val | V4 PF | V4 status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Session Breakout | v1 (M15 buf 0.1, sl 1.5, tp 2.0) | 86/9 | -0.2836 | -0.2488 | 0.59 | 379/49 | -0.0749 | -0.4546 | 0.81 | FAIL (EV not pos on both (tr:-0.075, val:-0.455); N < 300 (tr:379, val:49); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Session Breakout | v2 (M15 buf 0.2, sl 1.0, tp 2.0) | 29/1 | -0.3345 | -1.0992 | 0.56 | 97/11 | -0.0987 | +0.4061 | 0.93 | FAIL (EV not pos on both (tr:-0.099, val:0.406); N < 300 (tr:97, val:11); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Session Breakout | v3 (H1 buf 0.0, sl 1.5, tp 2.5) | 1446/123 | -0.0826 | -0.1815 | 0.83 | 3931/392 | -0.0608 | -0.0723 | 0.88 | FAIL (EV not pos on both (tr:-0.061, val:-0.072); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Opening Range Breakout | v1 (M15 30m ORB, sl 1.0, tp 1.5) | 944/813 | -0.0658 | -0.1375 | 0.85 | 456/266 | -0.0955 | -0.0176 | 0.89 | FAIL (EV not pos on both (tr:-0.096, val:-0.018); N < 300 (tr:456, val:266); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Opening Range Breakout | v2 (M15 30m ORB + SMA50, sl 1.0, tp 2.0) | 763/652 | -0.0744 | -0.1181 | 0.87 | 326/172 | -0.0749 | -0.0158 | 0.92 | FAIL (EV not pos on both (tr:-0.075, val:-0.016); N < 300 (tr:326, val:172); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Opening Range Breakout | v3 (H1 60m ORB, sl 1.2, tp 2.0) | 4286/899 | -0.0204 | -0.0629 | 0.95 | 3385/405 | -0.0705 | -0.1129 | 0.84 | FAIL (EV not pos on both (tr:-0.071, val:-0.113); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v1 (M15 dev 2.0 ATR, sl 1.5, tp VWAP) | 3661/2313 | -0.0458 | -0.0529 | 0.92 | 2002/627 | -0.0495 | -0.0067 | 0.93 | FAIL (EV not pos on both (tr:-0.050, val:-0.007); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v2 (M15 dev 2.5 ATR + RSI, sl 1.0, tp VWAP) | 499/465 | -0.1009 | +0.0519 | 0.96 | 332/186 | -0.0529 | -0.0242 | 0.94 | FAIL (EV not pos on both (tr:-0.053, val:-0.024); N < 300 (tr:332, val:186); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| VWAP Reversion | v3 (H1 dev 2.0 ATR, sl 1.5, tp VWAP) | 4374/700 | -0.0818 | -0.0725 | 0.83 | 3330/376 | -0.0794 | -0.1379 | 0.82 | FAIL (EV not pos on both (tr:-0.079, val:-0.138); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v1 (H4 20-period, sl 2.0, tp 4.0) | 4412/1281 | -0.0500 | +0.0132 | 0.95 | 3528/1001 | -0.0521 | +0.0413 | 0.95 | FAIL (EV not pos on both (tr:-0.052, val:0.041); WF 17% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v2 (H4 55-period, sl 2.5, tp 5.0) | 2333/681 | -0.0204 | -0.0212 | 0.97 | 1831/529 | -0.0331 | +0.0160 | 0.97 | FAIL (EV not pos on both (tr:-0.033, val:0.016); WF 50% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Donchian Breakout | v3 (D1 20-period, sl 2.0, tp 4.0) | 1643/225 | +0.0074 | +0.1150 | 1.03 | 1094/185 | +0.0021 | -0.0108 | 1.00 | FAIL (EV not pos on both (tr:0.002, val:-0.011); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v1 (H4 12-bar, sl 2.0, tp 3.0) | 7516/2218 | -0.0342 | -0.0148 | 0.95 | 6042/1728 | -0.0266 | -0.0258 | 0.96 | FAIL (EV not pos on both (tr:-0.027, val:-0.026); WF 0% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v2 (H4 30-bar, sl 2.5, tp 4.0) | 4185/1164 | -0.0318 | +0.0605 | 0.98 | 3341/918 | -0.0329 | +0.0333 | 0.97 | FAIL (EV not pos on both (tr:-0.033, val:0.033); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Time-Series Momentum | v3 (D1 20-bar, sl 2.5, tp 4.0) | 1935/267 | -0.0143 | +0.0462 | 0.99 | 1278/226 | +0.0078 | -0.0094 | 1.01 | FAIL (EV not pos on both (tr:0.008, val:-0.009); WF 33% < 60%; fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v1 (D1 SMA200 + RSI<40, sl 1.5, tp 2.5) | 172/33 | +0.1750 | +0.4803 | 1.42 | 186/42 | +0.1217 | +0.1544 | 1.23 | FAIL (N < 100 (tr:186, val:42); fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v2 (D1 SMA200 + 3 down days, sl 2.0, tp 3.0) | 316/64 | -0.0126 | +0.3985 | 1.10 | 427/95 | +0.0686 | +0.3140 | 1.22 | FAIL (N < 100 (tr:427, val:95); fails p95 benchmark; DSR 0.00 <= 0) |
| Index Pullback in 200-Day Uptrend | v3 (H4 SMA1200 + RSI<30, sl 1.5, tp 2.5) | 223/116 | -0.0659 | -0.0102 | 0.93 | 322/131 | +0.0412 | +0.1359 | 1.11 | FAIL (fails p95 benchmark; DSR 0.00 <= 0) |

**Research decision:** `Case B`.
No automatic transition from research qualification to normal trading is made by this script. DEMO exploration and the existing safety gates remain separate from this report.
