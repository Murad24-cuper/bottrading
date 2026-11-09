# Validation toolkit status

Backtest metric output now includes per-trade Sharpe, Sortino and Calmar in
addition to expectancy, profit factor, drawdown, holding time and losing
streak. A deterministic 10,000-resample bootstrap helper reports 5/50/95%
terminal equity and maximum drawdown plus ruin probability. It resamples
observed net trade outcomes IID; it does not simulate intrabar SL/TP ordering,
serial dependence, changing spreads or slippage paths.

The full requested validation suite is not complete: there is no matched
random-entry execution benchmark, no completed rolling walk-forward report for
the new strategy families, and no deflated-Sharpe/White reality correction.
Do not interpret the bootstrap as proof of an edge. These omissions are listed
as open work in `docs/FINAL_PROMPT_STATUS.md`.
