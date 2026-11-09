# Provisional no-edge policy — v2 research pending

## Decision

Ordinary strategy entries remain disabled in `config.yaml` with
`live.normal_trading_disabled: true`. This is a fail-closed safety setting,
not a valid final Case B result: Part 6 edge research v2 was not run. The six
requested families have zero evaluated trades; see
`reports/edge_research_v2.md`. Until those experiments finish, neither Case A
nor Case B is established, and the 2026-11-08 brain holdout must remain
untouched.

DEMO exploration is configured at 0.1% risk, but cannot yet run because no
cost-map cell has verified broker commission and enough spread observations.
Hard risk, daily/weekly loss, margin, session, spread and 10%-of-stop cost
checks remain in effect.

The hourly cost gate requires five recent observations in the same UTC hour
and known round-trip commission. The database had 52 spread observations per
focus symbol across only one UTC hour at inspection, below the requested 500
samples across trading hours; no commission data is available. Exploration is
blocked. This is not evidence that a cell passes the cost rule.

## Prior evidence (not a v2 result)

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
not been completed. Native H4/D1 maximum-range completeness and verified cost
cells remain unknown. No strategy is enabled for normal DEMO orders. This is a
provisional posture pending the required v2 test, not a completed Case B.
