# Shared cost model and live cost gate

`src/costs.py` is the shared account-currency arithmetic for one spread,
round-trip commission, both-side slippage and stop risk. It reports
`commission_known`; unknown broker commission cannot produce a passing cell.
`hourly_cost_cells` builds median cells without inventing missing symbol specs.

The live scanner records a spread sample per symbol/timeframe at the configured
cadence into SQLite. Entry candidates look up the same UTC hour over the
trailing 24 hours, require at least five observations and known commission,
then estimate median cell cost against the proposed stop. The hard cap is 10%.
Missing samples, unknown commission, unavailable contract data or an enabled
but uncalibrated one-bar delay model rejects the entry. No account-specific
commission schedule is currently persisted, so a new symbol/hour cell will
remain blocked until both sample and commission evidence are available.

The numeric helper, hourly pass/fail handling, and SQLite cell lookup are
covered by unit tests. Existing backtest output in `reports/edge_research.md`
is a prior research artifact; it is not treated as an account-verified or
hourly live cost map. Spread sampling begins after the updated scanner is
restarted.
