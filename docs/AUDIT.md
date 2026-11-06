# Codebase audit

Reviewed 2026-11-06 before the requested DEMO run. This review covers the order path, risk gates, scanner, persistence, dashboard controls, and live loop. Source line references below refer to the audit-fix commit.

## Critical

No remaining critical findings.

## High

| Finding | File:line | Problem | Fix |
|---|---|---|---|
| Oversized direct order could bypass the strategy sizing path | `src/executor.py:34-72` | A caller could invoke the executor with a volume larger than the configured stop risk. | Executor independently recalculates volume from account equity, live price, SL, tick value/size, and broker volume grid; it refuses larger volumes. `tests/test_executor_safety.py` covers it. |
| Direct executor call could bypass MT5Client's real-account guard | `src/executor.py:45-53` | The bot normally connects through `MT5Client`, but the order boundary itself did not verify a DEMO account or both explicit REAL flags. | `open_trade()` now independently requires DEMO, or both `account.mode: real` and `ALLOW_REAL=true`. Covered by `tests/test_executor_safety.py`. |
| A real account could pass the gate with only `ALLOW_REAL=true` | `src/mt5_client.py:24-27` | The config's account mode was not an independent guard. | A real account now requires both `account.mode: real` and `ALLOW_REAL=true`. `tests/test_mt5_safety.py` covers the combinations. |
| Same-cycle orders could bypass portfolio limits while MT5 state lagged | `src/bot.py:150-180` | Position count, currency/group exposure, and margin checks could see stale broker positions after an accepted order. | Successful entries reserve a position and margin for the remainder of that cycle. `tests/test_bot.py` covers delayed visibility. |
| Partial closes could be double-counted or disappear from realized P/L | `src/executor.py:224-306`, `src/db.py:14-18, 50-54, 128-141, 199-204` | Position history can contain multiple outbound deals; retries/reconciliation risked duplicates and the final close row alone did not represent scale-out profit. | Partial deals are keyed uniquely by broker deal ticket, reconciled separately from the final close, and included in P/L queries and dashboard summaries. Covered by `tests/test_executor_sync.py`, `tests/test_db.py`, and `tests/test_dashboard_queries.py`. |
| Non-FX symbols could crash risk evaluation | `src/risk.py:78-87` | Currency pair detection could return no pair and then be unpacked for stocks/other assets. | Pair exposure checks now run only when a pair is known. Covered by `tests/test_risk.py`. |
| Session inference could fail open with too little history | `src/symbols.py:29-50, 85-98` | Insufficient H1 history could be mistaken for no upcoming close, allowing an entry without a known session boundary. | Tradeability checks fail closed until at least seven days of H1 history are available; the scanner delays this more expensive check until after movement ranking. Covered by `tests/test_symbols.py`. |
| Scanner movement filter excluded too many otherwise tradable symbols | `config.yaml:76`, `src/scanner.py:75-124` | The `.35 ATR` spread ratio rejected most stage-1 symbols; only 7 of 40 configured movers reached analysis. | Ratio raised to `1.0`, session checks moved to selected movers, and selected versus analysed counts are reported separately. Recent live read-only scan: 1,612 visited, 143 stage-1, 26 analysed, 3 signals in 7.507 seconds. |

## Medium

| Finding | File:line | Problem | Fix / reason left |
|---|---|---|---|
| Broker sessions are inferred from H1 gaps | `src/sessions.py:10-52`, `src/symbols.py:29-50` | MT5 Python does not expose the broker's full per-symbol session schedule here; irregular holidays or newly listed symbols may be represented imperfectly. | Fail-closed on less than seven days of H1 data, cache observations, and apply per-symbol UTC times. Residual limitation is documented because the broker API does not provide a more authoritative schedule through this connection. |
| Daily/weekly loss baseline uses current balance | `src/risk.py:66-72` | A manual deposit during a period raises the monetary threshold; withdrawals are explicitly outside bot control. | Limits still include realized P/L and floating position P/L and immediately block once the configured percentage is crossed. A period-start balance ledger would be stricter; left unchanged in this audit to avoid silently changing the configured risk semantics mid-run. |
| A single slow MT5 call can overrun the scan budget | `src/scanner.py:75-82, 117-125` | Python cannot interrupt an in-flight terminal history request. | Stage 1 and analysis have deadlines, the loop subtracts work from its target period and never overlaps cycles. A single blocked MT5 call remains dependent on terminal responsiveness. |
| Dashboard password is optional | `src/dashboard/app.py:64-71`, `scripts/run_dashboard.py:8` | Without `DASHBOARD_PASSWORD`, the dashboard has no app-level authentication. | It binds to `127.0.0.1`; the password remains configurable for a locally shared machine. Keep it off public interfaces. |
| Process lock file can remain after an abnormal termination | `src/bot.py:20-33` | A crash can leave a stale lock file. | Dashboard Start checks the PID and removes a stale lock before starting; manual startup may require checking the PID and removing `data/bot.lock`. The lock still prevents normal concurrent starts. |

## Low

| Finding | File:line | Problem | Fix / reason left |
|---|---|---|---|
| Unused account-state refresh after an entry | `src/bot.py:179-180` | A refresh call's return value is not used; current account state is fetched again before the next candidate. | No safety effect; retained as a harmless explicit refresh. |
| Old strategy parameter defaults can yield sparse signals | `config.yaml:49-74` | Strategy conditions intentionally filter weak setups. | No relaxation made during an audit; the observed scan produced three signals and all were blocked by the still-present STOP file. |

## Checks performed

- Position sizing converts stop distance using `trade_tick_value_loss`/tick value and `trade_tick_size`/tick size, rounds down on the broker volume grid, caps at `volume_max`, and returns zero when the minimum lot exceeds risk (`src/risk.py:8-26`; `tests/test_risk.py`).
- Opens require positive SL and TP, validate their side against the current quote and broker stop distance, and attach both on the market request (`src/executor.py:34-72`). Direct execution also rechecks sizing and tradability.
- Stop modifications require a positive SL/TP and refuse loosening; the manager's breakeven and ATR trail only tighten. Partial-close validation checks ownership, step, minimum, and open volume (`src/executor.py:109-143, 161-198`).
- Close, modify, time-stop, session-close, sync, and close-all paths filter the configured magic number (`src/executor.py:87-111, 128-150, 200-215, 238-306`).
- Daily and weekly gates receive closed P/L plus partial realized P/L; open positions add floating profit, swap, and recorded commission (`src/bot.py:127-129, 150-180`; `src/risk.py:66-72`).
- Cycle reservations cover max-open, group, currency, underlying, and margin constraints while broker positions update (`src/bot.py:150-180`; `src/risk.py:73-87`).
- Session times are normalized to UTC; new entries are blocked inside the close buffer and owned positions are closed before inferred long gaps. No blanket Friday cutoff remains (`src/symbols.py:85-104`, `src/executor.py:200-215`).
- Dashboard commands have UTC expiry, duplicate active-command rejection, and pre-start expiry handling (`src/db.py:168-198`). Dashboard Start and the bot lock serialize normal startup (`src/dashboard/app.py:20-54`, `src/bot.py:20-33`).
- Reconnect is checked every cycle; backoff is bounded; consecutive cycle errors disable new entries while position management continues (`src/bot.py:222-263`).
- SQLite uses WAL; partial-deal uniqueness and close reconciliation protect persistence consistency (`src/db.py:39-55`, `src/executor.py:238-306`).
- `.env` is ignored, login logs show only the last three digits, credentials are not logged, and dashboard binds to localhost (`.gitignore:1`, `src/mt5_client.py:31`, `scripts/run_dashboard.py:8`).

## Tests

The audit-fix commit is gated on the complete `pytest` suite. This file records the review and outstanding limitations; live execution is a separate authorized step after the audit commit.
