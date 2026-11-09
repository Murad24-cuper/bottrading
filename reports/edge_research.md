# Edge research

Offline-only diagnostic. No MT5 connection, live code path, or trading/risk configuration changes.
Frozen periods: train ends 2026-09-30T04:30:00.000000000; validation 2026-09-30T06:30:00.000000000 to 2026-10-19T23:00:00.000000000; holdout begins 2026-10-20T01:00:00.000000000.
Holdout is used only for the requested baseline and checklist comparison. Grid code processes train/validation only. Baseline is sampled every 120 minutes to match stored holdout predictions; the grid samples hourly on closed M15/H1 bars. H1 labels use a 60m minimum timeout because OHLC bars cannot safely represent a 20m intrabar path. Cost medians use the complete locally available history range.

## 1. Transaction costs vs ATR stop distance

Round trip = median spread + two-sided configured commission + two-sided slippage, converted to price units. Stop = median ATR(14) × configured stop multiplier. `Crypto_10` H1 history is absent locally, so that row is reported as unavailable.

| Symbol | Group | TF | Median spread pts | Median ATR | Cost price | Stop distance | Cost/stop |
|---|---|---:|---:|---:|---:|---:|---:|
| EURUSD | forex | M1 | 19.000 | 9.853531e-05 | 0.00021 | 7.8828248e-05 | 266.4% |
| EURUSD | forex | M5 | 19.000 | 0.00024744772 | 0.00021 | 0.00019795818 | 106.1% |
| EURUSD | forex | M15 | 19.000 | 0.00046054575 | 0.00021 | 0.0003684366 | 57.0% |
| EURUSD | forex | H1 | 18.000 | 0.00097991298 | 0.0002 | 0.00078393038 | 25.5% |
| GBPUSD | forex | M1 | 22.000 | 0.00012974577 | 0.00024 | 0.00010379662 | 231.2% |
| GBPUSD | forex | M5 | 22.000 | 0.00032463486 | 0.00024 | 0.00025970789 | 92.4% |
| GBPUSD | forex | M15 | 21.000 | 0.00058369152 | 0.00023 | 0.00046695322 | 49.3% |
| GBPUSD | forex | H1 | 17.000 | 0.0012129603 | 0.00019 | 0.00097036825 | 19.6% |
| USDJPY | forex | M1 | 22.000 | 0.018454248 | 0.024 | 0.014763399 | 162.6% |
| USDJPY | forex | M5 | 21.000 | 0.046484975 | 0.023 | 0.03718798 | 61.8% |
| USDJPY | forex | M15 | 20.000 | 0.087133902 | 0.022 | 0.069707121 | 31.6% |
| USDJPY | forex | H1 | 20.000 | 0.19294655 | 0.022 | 0.15435724 | 14.3% |
| AUDUSD | forex | M1 | 23.000 | 8.3965713e-05 | 0.00025 | 6.7172571e-05 | 372.2% |
| AUDUSD | forex | M5 | 23.000 | 0.0002148842 | 0.00025 | 0.00017190736 | 145.4% |
| AUDUSD | forex | M15 | 23.000 | 0.00039290795 | 0.00025 | 0.00031432636 | 79.5% |
| AUDUSD | forex | H1 | 23.000 | 0.00082046192 | 0.00025 | 0.00065636953 | 38.1% |
| USDCAD | forex | M1 | 29.000 | 9.8321595e-05 | 0.00031 | 7.8657276e-05 | 394.1% |
| USDCAD | forex | M5 | 28.000 | 0.00025300717 | 0.0003 | 0.00020240574 | 148.2% |
| USDCAD | forex | M15 | 28.000 | 0.0004706256 | 0.0003 | 0.00037650048 | 79.7% |
| USDCAD | forex | H1 | 27.000 | 0.0010014962 | 0.00029 | 0.00080119698 | 36.2% |
| US500Cash | indices | M1 | 80.000 | 1.4443855 | 0.82 | 1.1555084 | 71.0% |
| US500Cash | indices | M5 | 80.000 | 3.5120255 | 0.82 | 2.8096204 | 29.2% |
| US500Cash | indices | M15 | 80.000 | 6.5065664 | 0.82 | 5.2052531 | 15.8% |
| US500Cash | indices | H1 | 80.000 | 13.996979 | 0.82 | 11.197583 | 7.3% |
| US100Cash | indices | M1 | 290.000 | 9.6347684 | 2.92 | 7.7078148 | 37.9% |
| US100Cash | indices | M5 | 290.000 | 23.449703 | 2.92 | 18.759762 | 15.6% |
| US100Cash | indices | M15 | 290.000 | 42.99547 | 2.92 | 34.396376 | 8.5% |
| US100Cash | indices | H1 | 290.000 | 90.68874 | 2.92 | 72.550992 | 4.0% |
| US30Cash | indices | M1 | 600.000 | 10.028482 | 6.02 | 8.0227859 | 75.0% |
| US30Cash | indices | M5 | 600.000 | 24.5517 | 6.02 | 19.64136 | 30.6% |
| US30Cash | indices | M15 | 600.000 | 46.408184 | 6.02 | 37.126547 | 16.2% |
| US30Cash | indices | H1 | 600.000 | 101.79014 | 6.02 | 81.432115 | 7.4% |
| GER40Cash | indices | M1 | 260.000 | 6.3407553 | 2.62 | 5.0726043 | 51.6% |
| GER40Cash | indices | M5 | 260.000 | 15.72185 | 2.62 | 12.57748 | 20.8% |
| GER40Cash | indices | M15 | 260.000 | 28.471332 | 2.62 | 22.777065 | 11.5% |
| GER40Cash | indices | H1 | 260.000 | 59.158581 | 2.62 | 47.326865 | 5.5% |
| GOLD | metals | M1 | 52.000 | 1.7343705 | 0.54 | 1.3874964 | 38.9% |
| GOLD | metals | M5 | 49.000 | 4.177296 | 0.51 | 3.3418368 | 15.3% |
| GOLD | metals | M15 | 40.000 | 7.6542876 | 0.42 | 6.1234301 | 6.9% |
| GOLD | metals | H1 | 40.000 | 16.495104 | 0.42 | 13.196083 | 3.2% |
| BTCUSD | crypto | M1 | 4000.000 | 32.891573 | 40.02 | 26.313259 | 152.1% |
| BTCUSD | crypto | M5 | 4000.000 | 87.17057 | 40.02 | 69.736456 | 57.4% |
| BTCUSD | crypto | M15 | 4000.000 | 169.55124 | 40.02 | 135.64099 | 29.5% |
| BTCUSD | crypto | H1 | 4000.000 | 375.61347 | 40.02 | 300.49078 | 13.3% |
| ETHUSD | crypto | M1 | 300.000 | 1.5152594 | 3.02 | 1.2122075 | 249.1% |
| ETHUSD | crypto | M5 | 300.000 | 3.7457124 | 3.02 | 2.9965699 | 100.8% |
| ETHUSD | crypto | M15 | 300.000 | 7.1232691 | 3.02 | 5.6986153 | 53.0% |
| ETHUSD | crypto | H1 | 300.000 | 15.903879 | 3.02 | 12.723103 | 23.7% |
| GOLD24-7 | metals | M1 | 150.000 | 1.4301328 | 1.52 | 1.1441062 | 132.9% |
| GOLD24-7 | metals | M5 | 150.000 | 3.5886528 | 1.52 | 2.8709222 | 52.9% |
| GOLD24-7 | metals | M15 | 150.000 | 6.720333 | 1.52 | 5.3762664 | 28.3% |
| GOLD24-7 | metals | H1 | 150.000 | 13.818739 | 1.52 | 11.054991 | 13.7% |
| Altcoins_INDX | indices | M1 | 320.000 | 0.17366531 | 3.22 | 0.13893225 | 2317.7% |
| Altcoins_INDX | indices | M5 | 320.000 | 0.4491749 | 3.22 | 0.35933992 | 896.1% |
| Altcoins_INDX | indices | M15 | 320.000 | 0.90527273 | 3.22 | 0.72421818 | 444.6% |
| Altcoins_INDX | indices | H1 | 320.000 | 2.0817372 | 3.22 | 1.6653897 | 193.3% |
| Crypto_10 | indices | M1 | 11550.000 | 7.9230291 | 115.52 | 6.3384233 | 1822.5% |
| Crypto_10 | indices | M5 | 11550.000 | 20.754471 | 115.52 | 16.603577 | 695.8% |
| Crypto_10 | indices | M15 | 11550.000 | 40.657319 | 115.52 | 32.525855 | 355.2% |
| Crypto_10 | indices | H1 | n/a | n/a | n/a | n/a | n/a |

## 2. Current strategies on holdout

Signal-level M1 baseline, current confidence/MTF gates, one max-hold slot per symbol/strategy: 557 trades, win 30.3%, expectancy -0.3224 R, PF 0.3524.

### By strategy

| Strategy | Trades | Win rate | Expectancy R | PF |
|---|---:|---:|---:|---:|
| mean_reversion | 14 | 35.7% | -0.3397 | 0.2701 |
| trend_pullback | 511 | 29.5% | -0.3240 | 0.3424 |
| volatility_scalp | 32 | 40.6% | -0.2898 | 0.5127 |

### By group

| Group | Trades | Win rate | Expectancy R | PF |
|---|---:|---:|---:|---:|
| crypto | 2 | 50.0% | 0.1477 | 3.0253 |
| forex | 242 | 24.8% | -0.4321 | 0.2427 |
| indices | 241 | 35.3% | -0.2502 | 0.4302 |
| metals | 72 | 31.9% | -0.2083 | 0.5486 |

## 3. M15/H1 timeframe and R:R grid (train/validation only)

Causal signals use closed bars; entry is the next bar open. The strategy stop distance is preserved; target is varied. Costs and configured time barrier are applied; stop takes precedence if both barriers hit.

| Strategy | Group | TF | R:R | Split | Trades | Win | Expectancy net R | PF |
|---|---|---:|---:|---|---:|---:|---:|---:|
| mean_reversion | forex | H1 | 1:1 | train | 20 | 25.0% | -0.5206 | 0.3158 |
| mean_reversion | forex | H1 | 1:1 | validation | 8 | 25.0% | -0.4214 | 0.4150 |
| mean_reversion | forex | H1 | 1:1.5 | train | 20 | 25.0% | -0.5157 | 0.3223 |
| mean_reversion | forex | H1 | 1:1.5 | validation | 8 | 12.5% | -0.6314 | 0.2544 |
| mean_reversion | forex | H1 | 1:2 | train | 20 | 25.0% | -0.4907 | 0.3552 |
| mean_reversion | forex | H1 | 1:2 | validation | 8 | 12.5% | -0.5689 | 0.3282 |
| mean_reversion | forex | H1 | 1:3 | train | 20 | 25.0% | -0.5050 | 0.3364 |
| mean_reversion | forex | H1 | 1:3 | validation | 8 | 12.5% | -0.6423 | 0.2415 |
| mean_reversion | forex | M15 | 1:1 | train | 20 | 20.0% | -0.5518 | 0.1407 |
| mean_reversion | forex | M15 | 1:1 | validation | 8 | 75.0% | 0.3046 | 2.1912 |
| mean_reversion | forex | M15 | 1:1.5 | train | 20 | 20.0% | -0.5518 | 0.1407 |
| mean_reversion | forex | M15 | 1:1.5 | validation | 8 | 75.0% | 0.4072 | 2.5926 |
| mean_reversion | forex | M15 | 1:2 | train | 20 | 20.0% | -0.5518 | 0.1407 |
| mean_reversion | forex | M15 | 1:2 | validation | 8 | 75.0% | 0.0960 | 1.3753 |
| mean_reversion | forex | M15 | 1:3 | train | 20 | 20.0% | -0.5518 | 0.1407 |
| mean_reversion | forex | M15 | 1:3 | validation | 8 | 75.0% | 0.0960 | 1.3753 |
| mean_reversion | indices | H1 | 1:1 | train | 5 | 20.0% | -0.5867 | 0.2683 |
| mean_reversion | indices | H1 | 1:1 | validation | 7 | 28.6% | -0.4522 | 0.2739 |
| mean_reversion | indices | H1 | 1:1.5 | train | 5 | 20.0% | -0.4867 | 0.3930 |
| mean_reversion | indices | H1 | 1:1.5 | validation | 7 | 28.6% | -0.3807 | 0.3886 |
| mean_reversion | indices | H1 | 1:2 | train | 5 | 20.0% | -0.3867 | 0.5177 |
| mean_reversion | indices | H1 | 1:2 | validation | 7 | 28.6% | -0.3093 | 0.5033 |
| mean_reversion | indices | H1 | 1:3 | train | 5 | 20.0% | -0.1867 | 0.7672 |
| mean_reversion | indices | H1 | 1:3 | validation | 7 | 28.6% | -0.1915 | 0.6925 |
| mean_reversion | indices | M15 | 1:1 | train | 8 | 12.5% | -0.6107 | 0.1804 |
| mean_reversion | indices | M15 | 1:1 | validation | 10 | 20.0% | -0.5743 | 0.1933 |
| mean_reversion | indices | M15 | 1:1.5 | train | 8 | 12.5% | -0.6002 | 0.1945 |
| mean_reversion | indices | M15 | 1:1.5 | validation | 10 | 20.0% | -0.5243 | 0.2635 |
| mean_reversion | indices | M15 | 1:2 | train | 8 | 12.5% | -0.6002 | 0.1945 |
| mean_reversion | indices | M15 | 1:2 | validation | 10 | 20.0% | -0.4743 | 0.3337 |
| mean_reversion | indices | M15 | 1:3 | train | 8 | 12.5% | -0.6002 | 0.1945 |
| mean_reversion | indices | M15 | 1:3 | validation | 10 | 20.0% | -0.4774 | 0.3294 |
| mean_reversion | metals | H1 | 1:1 | train | 1 | 0.0% | -1.0012 | 0.0000 |
| mean_reversion | metals | H1 | 1:1 | validation | 5 | 40.0% | -0.2871 | 0.5256 |
| mean_reversion | metals | H1 | 1:1.5 | train | 1 | 0.0% | -1.0012 | 0.0000 |
| mean_reversion | metals | H1 | 1:1.5 | validation | 5 | 20.0% | -0.6953 | 0.1366 |
| mean_reversion | metals | H1 | 1:2 | train | 1 | 0.0% | -1.0012 | 0.0000 |
| mean_reversion | metals | H1 | 1:2 | validation | 5 | 20.0% | -0.6953 | 0.1366 |
| mean_reversion | metals | H1 | 1:3 | train | 1 | 0.0% | -1.0012 | 0.0000 |
| mean_reversion | metals | H1 | 1:3 | validation | 5 | 20.0% | -0.6953 | 0.1366 |
| mean_reversion | metals | M15 | 1:1 | train | 1 | 100.0% | 0.1371 | inf |
| mean_reversion | metals | M15 | 1:1 | validation | 5 | 80.0% | 0.3525 | 2.7229 |
| mean_reversion | metals | M15 | 1:1.5 | train | 1 | 100.0% | 0.1371 | inf |
| mean_reversion | metals | M15 | 1:1.5 | validation | 5 | 80.0% | 0.1801 | 1.8803 |
| mean_reversion | metals | M15 | 1:2 | train | 1 | 100.0% | 0.1371 | inf |
| mean_reversion | metals | M15 | 1:2 | validation | 5 | 80.0% | 0.1801 | 1.8803 |
| mean_reversion | metals | M15 | 1:3 | train | 1 | 100.0% | 0.1371 | inf |
| mean_reversion | metals | M15 | 1:3 | validation | 5 | 80.0% | 0.1801 | 1.8803 |
| trend_pullback | forex | H1 | 1:1 | train | 915 | 19.6% | -0.5728 | 0.2544 |
| trend_pullback | forex | H1 | 1:1 | validation | 294 | 21.8% | -0.5086 | 0.3057 |
| trend_pullback | forex | H1 | 1:1.5 | train | 915 | 18.4% | -0.5682 | 0.2670 |
| trend_pullback | forex | H1 | 1:1.5 | validation | 294 | 21.1% | -0.4796 | 0.3486 |
| trend_pullback | forex | H1 | 1:2 | train | 915 | 17.9% | -0.5617 | 0.2786 |
| trend_pullback | forex | H1 | 1:2 | validation | 294 | 20.4% | -0.4899 | 0.3409 |
| trend_pullback | forex | H1 | 1:3 | train | 915 | 17.8% | -0.5592 | 0.2829 |
| trend_pullback | forex | H1 | 1:3 | validation | 294 | 20.1% | -0.4775 | 0.3580 |
| trend_pullback | forex | M15 | 1:1 | train | 915 | 18.5% | -0.5427 | 0.1800 |
| trend_pullback | forex | M15 | 1:1 | validation | 294 | 23.5% | -0.4351 | 0.2572 |
| trend_pullback | forex | M15 | 1:1.5 | train | 915 | 18.4% | -0.5393 | 0.1852 |
| trend_pullback | forex | M15 | 1:1.5 | validation | 294 | 23.1% | -0.4383 | 0.2562 |
| trend_pullback | forex | M15 | 1:2 | train | 915 | 18.4% | -0.5394 | 0.1850 |
| trend_pullback | forex | M15 | 1:2 | validation | 294 | 22.8% | -0.4453 | 0.2453 |
| trend_pullback | forex | M15 | 1:3 | train | 915 | 18.3% | -0.5439 | 0.1784 |
| trend_pullback | forex | M15 | 1:3 | validation | 294 | 22.8% | -0.4438 | 0.2477 |
| trend_pullback | indices | H1 | 1:1 | train | 705 | 37.3% | -0.2339 | 0.5867 |
| trend_pullback | indices | H1 | 1:1 | validation | 220 | 40.5% | -0.2135 | 0.6132 |
| trend_pullback | indices | H1 | 1:1.5 | train | 705 | 34.2% | -0.2277 | 0.6157 |
| trend_pullback | indices | H1 | 1:1.5 | validation | 220 | 39.5% | -0.1719 | 0.6937 |
| trend_pullback | indices | H1 | 1:2 | train | 705 | 33.2% | -0.2077 | 0.6518 |
| trend_pullback | indices | H1 | 1:2 | validation | 220 | 38.2% | -0.1718 | 0.6989 |
| trend_pullback | indices | H1 | 1:3 | train | 705 | 32.6% | -0.1865 | 0.6893 |
| trend_pullback | indices | H1 | 1:3 | validation | 220 | 36.8% | -0.1531 | 0.7379 |
| trend_pullback | indices | M15 | 1:1 | train | 705 | 38.6% | -0.1925 | 0.5411 |
| trend_pullback | indices | M15 | 1:1 | validation | 220 | 36.8% | -0.2201 | 0.4857 |
| trend_pullback | indices | M15 | 1:1.5 | train | 705 | 37.2% | -0.1902 | 0.5530 |
| trend_pullback | indices | M15 | 1:1.5 | validation | 220 | 36.4% | -0.2029 | 0.5263 |
| trend_pullback | indices | M15 | 1:2 | train | 705 | 36.7% | -0.1918 | 0.5502 |
| trend_pullback | indices | M15 | 1:2 | validation | 220 | 36.4% | -0.1990 | 0.5354 |
| trend_pullback | indices | M15 | 1:3 | train | 705 | 36.7% | -0.1985 | 0.5344 |
| trend_pullback | indices | M15 | 1:3 | validation | 220 | 36.4% | -0.2128 | 0.5032 |
| trend_pullback | metals | H1 | 1:1 | train | 174 | 40.2% | -0.1844 | 0.6739 |
| trend_pullback | metals | H1 | 1:1 | validation | 53 | 34.0% | -0.3014 | 0.5285 |
| trend_pullback | metals | H1 | 1:1.5 | train | 174 | 37.4% | -0.1319 | 0.7713 |
| trend_pullback | metals | H1 | 1:1.5 | validation | 53 | 28.3% | -0.3178 | 0.5232 |
| trend_pullback | metals | H1 | 1:2 | train | 174 | 35.1% | -0.1061 | 0.8207 |
| trend_pullback | metals | H1 | 1:2 | validation | 53 | 28.3% | -0.2772 | 0.5840 |
| trend_pullback | metals | H1 | 1:3 | train | 174 | 33.9% | -0.0793 | 0.8684 |
| trend_pullback | metals | H1 | 1:3 | validation | 53 | 28.3% | -0.2064 | 0.6903 |
| trend_pullback | metals | M15 | 1:1 | train | 174 | 42.5% | -0.1198 | 0.7122 |
| trend_pullback | metals | M15 | 1:1 | validation | 53 | 35.8% | -0.2277 | 0.4565 |
| trend_pullback | metals | M15 | 1:1.5 | train | 174 | 42.0% | -0.1282 | 0.6961 |
| trend_pullback | metals | M15 | 1:1.5 | validation | 53 | 34.0% | -0.2271 | 0.4812 |
| trend_pullback | metals | M15 | 1:2 | train | 174 | 42.0% | -0.1250 | 0.7036 |
| trend_pullback | metals | M15 | 1:2 | validation | 53 | 34.0% | -0.2395 | 0.4529 |
| trend_pullback | metals | M15 | 1:3 | train | 174 | 42.0% | -0.1115 | 0.7358 |
| trend_pullback | metals | M15 | 1:3 | validation | 53 | 34.0% | -0.2206 | 0.4960 |
| volatility_scalp | indices | H1 | 1:1 | train | 28 | 3.6% | -0.9225 | 0.0440 |
| volatility_scalp | indices | H1 | 1:1 | validation | 11 | 9.1% | -0.8062 | 0.1138 |
| volatility_scalp | indices | H1 | 1:1.5 | train | 28 | 3.6% | -0.9047 | 0.0625 |
| volatility_scalp | indices | H1 | 1:1.5 | validation | 11 | 9.1% | -0.7607 | 0.1638 |
| volatility_scalp | indices | H1 | 1:2 | train | 28 | 3.6% | -0.8868 | 0.0810 |
| volatility_scalp | indices | H1 | 1:2 | validation | 11 | 9.1% | -0.7153 | 0.2138 |
| volatility_scalp | indices | H1 | 1:3 | train | 28 | 3.6% | -0.8511 | 0.1180 |
| volatility_scalp | indices | H1 | 1:3 | validation | 11 | 9.1% | -0.6243 | 0.3137 |
| volatility_scalp | indices | M15 | 1:1 | train | 28 | 17.9% | -0.6136 | 0.2536 |
| volatility_scalp | indices | M15 | 1:1 | validation | 11 | 9.1% | -0.8062 | 0.1138 |
| volatility_scalp | indices | M15 | 1:1.5 | train | 28 | 17.9% | -0.5243 | 0.3622 |
| volatility_scalp | indices | M15 | 1:1.5 | validation | 11 | 9.1% | -0.7607 | 0.1638 |
| volatility_scalp | indices | M15 | 1:2 | train | 28 | 17.9% | -0.4351 | 0.4708 |
| volatility_scalp | indices | M15 | 1:2 | validation | 11 | 9.1% | -0.7153 | 0.2138 |
| volatility_scalp | indices | M15 | 1:3 | train | 28 | 17.9% | -0.2565 | 0.6880 |
| volatility_scalp | indices | M15 | 1:3 | validation | 11 | 9.1% | -0.6243 | 0.3137 |
| volatility_scalp | metals | H1 | 1:1 | train | 17 | 5.9% | -0.8762 | 0.0726 |
| volatility_scalp | metals | H1 | 1:1 | validation | 2 | 0.0% | -1.0045 | 0.0000 |
| volatility_scalp | metals | H1 | 1:1.5 | train | 17 | 5.9% | -0.8467 | 0.1038 |
| volatility_scalp | metals | H1 | 1:1.5 | validation | 2 | 0.0% | -1.0045 | 0.0000 |
| volatility_scalp | metals | H1 | 1:2 | train | 17 | 5.9% | -0.8173 | 0.1349 |
| volatility_scalp | metals | H1 | 1:2 | validation | 2 | 0.0% | -1.0045 | 0.0000 |
| volatility_scalp | metals | H1 | 1:3 | train | 17 | 5.9% | -0.7585 | 0.1972 |
| volatility_scalp | metals | H1 | 1:3 | validation | 2 | 0.0% | -1.0045 | 0.0000 |
| volatility_scalp | metals | M15 | 1:1 | train | 17 | 11.8% | -0.7463 | 0.1573 |
| volatility_scalp | metals | M15 | 1:1 | validation | 2 | 0.0% | -1.0045 | 0.0000 |
| volatility_scalp | metals | M15 | 1:1.5 | train | 17 | 11.8% | -0.6875 | 0.2237 |
| volatility_scalp | metals | M15 | 1:1.5 | validation | 2 | 0.0% | -1.0045 | 0.0000 |
| volatility_scalp | metals | M15 | 1:2 | train | 17 | 11.8% | -0.6287 | 0.2901 |
| volatility_scalp | metals | M15 | 1:2 | validation | 2 | 0.0% | -1.0045 | 0.0000 |
| volatility_scalp | metals | M15 | 1:3 | train | 17 | 11.8% | -0.5111 | 0.4230 |
| volatility_scalp | metals | M15 | 1:3 | validation | 2 | 0.0% | -1.0045 | 0.0000 |

Rows with zero qualifying setups are omitted from the grid (zero trades; expectancy is undefined).

## 4. Positive on both train and validation with 300+ trades in each

None. The 300-trade minimum is required separately in each split.

## 5. Why checklist-only is worse than random

The holdout candidate pool: 4228 samples, win rate 17.55%, expectancy -0.5693 R. Checklist-only: 2524 samples, win rate 15.02%, expectancy -0.6334 R.
1,000 uniformly random equal-size subsets average -0.5688 R, central 90% -0.5887 to -0.5482 R. Checklist is -0.0641 R below the whole candidate pool. This establishes worse selection on this sample, not which checklist item caused it; item-level randomized ablations were not run.

## Method limits

The current-strategy section is a causal signal-level replay with bot confidence/MTF gates, configured spread/costs, and a non-overlap max-hold spacing. It does not apply full portfolio margin/daily-loss allocation. The grid is a fixed-barrier diagnostic, not a portfolio backtest. No holdout tuning was done.
