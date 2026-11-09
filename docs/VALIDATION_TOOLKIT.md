# Validation toolkit status

Backtest metric output now includes per-trade Sharpe, Sortino and Calmar in
addition to expectancy, profit factor, drawdown, holding time and losing
streak. A deterministic 10,000-resample bootstrap helper reports 5/50/95%
terminal equity and maximum drawdown plus ruin probability. It resamples
observed net trade outcomes IID; it does not simulate intrabar SL/TP ordering,
serial dependence, changing spreads or slippage paths.

The full requested validation suite is not complete. `walk_forward()` can
produce parameterized rolling windows, but the existing report does not
summarize the share with positive out-of-sample expectancy. There is no
matched random-entry simulator using the same trade count, duration and SL/TP,
no full breakdown by strategy/symbol/exit reason/session, and no
deflated-Sharpe correction. The backtest and replay also retain separate cost
arithmetic; account commission evidence and verified live spread samples are
not available to calibrate the shared cost model. Do not interpret the IID
bootstrap as proof of an edge.
