# Live readiness — report only

**Status: FAIL — not READY.** Generated from the read-only local database at
2026-11-09 15:23 UTC. This score does not change account mode or trading
controls. DEMO remains the only selected account; real-money switching stays a
manual decision.

| Gate | Required | Observed | Result |
|---|---:|---:|---|
| DEMO duration on current strategy set | 8 weeks | Database starts 2026-11-05; about 4 days | FAIL |
| DEMO closed trades | 200 | 41 | FAIL |
| Real-cost expectancy | Positive | -0.79 account-currency units/trade (41 trades) | FAIL |
| DEMO/backtest tolerance | Within configured tolerance | Not comparable in units: prior backtest is R, persisted DEMO summary is account currency; prior strategy baseline was -0.32R | FAIL |
| Maximum drawdown | Within risk limit | 39.35 currency units / 3.83% peak-to-trough | FAIL |
| Monte Carlo ruin probability | Below threshold | 0.0% in 10,000 IID resamples; terminal equity p5/p50/p95: 942.18 / 967.88 / 993.14 from 1,000 | PASS (limited sample) |
| Unresolved incidents in last 2 weeks | None | 21 ERROR/CRITICAL event rows; no incident-resolution ledger proves closure | FAIL |

The underlying evidence contains only 41 closed main-mode trades over four
days. The IID Monte Carlo result is not a substitute for adequate sample size
or intrabar cost modeling. Do not promote the brain or activate ordinary
strategy trades from this report. The updated Part 7 setting keeps ordinary
trades disabled and permits only guarded DEMO exploration in calibrated cost
cells.

This file is currently a point-in-time report. The supervisor does not yet
regenerate and Telegram-send this report weekly; that automation remains open.
