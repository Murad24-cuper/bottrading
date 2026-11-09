# No qualifying edge — DEMO policy

## Decision

**Case B applied conservatively.** Ordinary strategy entries are disabled in
`config.yaml` with `live.normal_trading_disabled: true`. DEMO-only exploration
is enabled at the existing 0.1% risk setting. Exploration must still pass the
same hard risk, daily/weekly loss, margin, session, spread and 10%-of-stop cost
checks as normal entries; it does not inherit lower reward/risk or looser cost
limits. Adaptive strategy/group pauses can be bypassed only for this explicitly
tagged DEMO exploration path, so its observations can continue without
reactivating ordinary strategy trades.

The hourly cost gate requires five recent observations in the same UTC hour
and known round-trip commission. Until cells are calibrated, exploration is
also blocked. This is intentional fail-closed behavior; it is not evidence that
there is a passing cost cell.

## Evidence used

The committed M1–H1 research report records the previous holdout baseline for
the current strategies: 557 trades, 30.3% wins, expectancy -0.3224R and profit
factor 0.3524. Trend pullback produced 511 trades at -0.3240R; mean reversion
14 at -0.3397R; volatility scalp 32 at -0.2898R. That report also found the
checklist at -0.63R versus -0.57R for random selection. These are prior
research results; the holdout was not re-opened or re-evaluated in this task.

## Untested directions

Session/opening-range breakout, VWAP reversion, native H4/D1 Donchian and
time-series momentum, index pullback, validation-only walk-forward robustness,
random-entry benchmarking and multiple-testing-corrected significance have
not been completed. Native H4/D1 history requires a maintenance operation
through the current bot-owned MT5 session; see `docs/BLOCKERS.md`. Therefore
no strategy has met the complete qualification standard, and none is enabled
for normal DEMO orders.
