# Audit Findings Response & Resolution Log

Tracking responses and fixes for findings in `docs/AUDIT.md`.

| Finding ID | Title | Status | Fix Summary | Test Name |
|---|---|---|---|---|
| **CRIT-01** | Position without server-side SL | Confirmed & Fixed | Added `remediate_missing_sl()` in `Executor` to retry setting planned or emergency ATR SL up to 3 times, closing at market if impossible; integrated into `open_trade()`, `_health()`, and `_startup()`. | `tests/test_audit_crit01.py` |
| **CRIT-02** | MT5 threading IPC hangs | Confirmed & Fixed | Replaced per-call thread spawning in `MT5CallProxy` with a single dedicated worker thread and queue; timed-out calls mark session unhealthy and reject subsequent calls fast; linked 6 unresolved hangs in `docs/ERROR_LEDGER.md`. | `tests/test_audit_crit02.py` |
| **CRIT-03** | Cost gate commission deadlock | Confirmed & Fixed | Added fallback hierarchy (deals -> symbol/account -> 0.0 default); recognized 0.0 deals; marked estimated commissions so fresh/zero-commission accounts pass cost gate without blocking. | `tests/test_audit_crit03.py` |
| **CRIT-04** | Requote sizing and stop validation | Confirmed & Fixed | On requote, re-validate SL/TP side and distance, recompute volume via stressed-stop sizing to ensure risk cap is never exceeded, and cancel if safe volume falls below min lot. | `tests/test_audit_crit04.py` |

