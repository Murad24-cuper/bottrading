# Audit Findings Response & Resolution Log

Tracking responses and fixes for findings in `docs/AUDIT.md`.

| Finding ID | Title | Status | Fix Summary | Test Name |
|---|---|---|---|---|
| **CRIT-01** | Position without server-side SL | Confirmed & Fixed | Added `remediate_missing_sl()` in `Executor` to retry setting planned or emergency ATR SL up to 3 times, closing at market if impossible; integrated into `open_trade()`, `_health()`, and `_startup()`. | `tests/test_audit_crit01.py` |
| **CRIT-02** | MT5 threading IPC hangs | Confirmed & Fixed | Replaced per-call thread spawning in `MT5CallProxy` with a single dedicated worker thread and queue; timed-out calls mark session unhealthy and reject subsequent calls fast; linked 6 unresolved hangs in `docs/ERROR_LEDGER.md`. | `tests/test_audit_crit02.py` |
| **CRIT-03** | Cost gate commission deadlock | Confirmed & Fixed | Added fallback hierarchy (deals -> symbol/account -> 0.0 default); recognized 0.0 deals; marked estimated commissions so fresh/zero-commission accounts pass cost gate without blocking. | `tests/test_audit_crit03.py` |
| **CRIT-04** | Requote sizing and stop validation | Confirmed & Fixed | On requote, re-validate SL/TP side and distance, recompute volume via stressed-stop sizing to ensure risk cap is never exceeded, and cancel if safe volume falls below min lot. | `tests/test_audit_crit04.py` |
| **CRIT-05** | Partial fill and DB reconciliation | Confirmed & Fixed | Recorded actual filled volume in `open_trade`; updated `sync_positions` and bot `_startup` to reconcile DB open trades against MT5 and close stale DB records. | `tests/test_audit_crit05.py` |
| **HIGH-01** | Exploration & weekend locked ceiling bypass | Confirmed & Fixed | Extended `validate_risk_ceilings()` to enforce locked ceilings on `demo_exploration` and `weekend` config sections (`risk_per_trade_pct` and `max_open_positions`). | `tests/test_audit_high01.py` |
| **HIGH-02** | Trailed profit counted as open risk | Confirmed & Fixed | Made open risk distance direction-aware (`max(0, open-stop)` for BUY, `max(0, stop-open)` for SELL) so trailed profits are not counted as portfolio risk. | `tests/test_audit_high02.py` |
| **HIGH-03** | Chronological purge window data leakage | Confirmed & Fixed | Increased default `purge_minutes` in `chronological_splits()` from 20 to 120 minutes to match `max_hold_extended_minutes` and prevent lookahead data leakage between splits. | `tests/test_audit_high03.py` |
| **HIGH-04** | Windows WDAC blocked Parquet engine | Confirmed & Fixed | Added `src/parquet_compat.py` with transparent fallback for DataFrame parquet read/write when native `_parquet.pyd` DLL is blocked by Windows AppLocker; fixed 4 failing tests. | `tests/test_audit_high04.py` |
| **HIGH-05** | Missing magic filter in `get_pnl_since` | Confirmed & Fixed | Added optional `magic` filter to `Database.get_pnl_since()` and passed `settings.magic_number` in `bot._pnl_periods()` so foreign manual trades do not halt the bot. | `tests/test_audit_high05.py` |
| **MED-02** | News XML / URL security (XXE & scheme) | Confirmed & Fixed | Switched XML parsing to `defusedxml` to block entity expansions (XXE); restricted `_download_calendar` to `https://` URLs; standardized DST zone combining. | `tests/test_audit_med02.py` |

