# Shared cost model and live cost gate

`src/costs.py` is the shared account-currency arithmetic for one spread,
round-trip commission, both-side slippage and stop risk. It reports
`commission_known`; unknown broker commission cannot produce a passing cell.
`hourly_cost_cells` builds median cells without inventing missing symbol specs.

The live scanner records a spread sample per symbol/timeframe at the configured
cadence into SQLite. Entry candidates look up the same UTC hour over the
trailing 24 hours. With at least five observations it uses the cell median;
until then it uses the enabled symbol's current `symbol_info.spread * point`
with a 1.25 multiplier. Both paths include configured round-trip commission
and two-sided slippage and are checked against the proposed stop. The hard cap
is 10%. Unknown commission, unavailable spread/contract data or an enabled but
uncalibrated one-bar delay model rejects the entry. The fallback allows a new
account or broker alias to be evaluated while live spread sampling continues.

The numeric helper, hourly pass/fail handling, and SQLite cell lookup are
covered by unit tests. Existing backtest output in `reports/edge_research.md`
is a prior research artifact; it is not treated as an account-verified or
hourly live cost map. Spread sampling begins after the updated scanner is
restarted.
