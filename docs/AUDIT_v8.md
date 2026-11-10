# v8 Project Audit

**Date:** 2026-11-10 (Asia/Baku)  
**Scope:** order safety, retries and rejections, STOP/kill switch, SL/TP, risk and sizing, broker symbol aliases, costs, data refresh, SQLite, dashboard, self-test and pytest.  
**Account boundary:** XM DEMO only; login `108765323`; `.env` was not modified.

## Findings

| Severity | Finding | Status and evidence |
|---|---|---|
| **CRITICAL** | Three consecutive broker order rejections emitted an alert but left the entry loop enabled. | **Fixed** in `5a3ccbf`: the configured threshold now writes `STOP=PAUSE`, emits one CRITICAL event and blocks subsequent entries. Regression coverage: `test_three_consecutive_order_rejections_auto_pause_new_entries`. |
| **HIGH** | Streamlit imports `pyarrow`, while the previous compatibility guard rejected any process that loaded it. With the required Streamlit dependency installed, dashboard startup could fail even though project Parquet reads and writes explicitly use `fastparquet`. | **Fixed** in `c15541f`: startup verifies `fastparquet` availability; Parquet wrappers continue to pass `engine='fastparquet'`. Pinned `pyarrow==19.0.1` imports successfully after Smart App Control was turned off. Covered by `test_fastparquet_roundtrip_works_when_pyarrow_is_loaded`. |
| **HIGH** | Runtime dependencies were not consistently pinned, leaving native package versions subject to index changes. | **Fixed** in `b455c3e`: direct Windows/Python 3.12 dependencies are pinned in `requirements.txt`. `pip check` reported no broken requirements; every direct dependency imported. |
| **MEDIUM** | The Windows console encoding caused `scripts/health_check.py` to fail while printing Azerbaijani status text. | **Fixed** in `596f552`: console output is reconfigured to UTF-8 with replacement handling. Three focused tests pass and the script prints its complete report. |
| **MEDIUM** | Incremental history refresh can exceed its 1.5-second configured budget for an individual MT5 request. | **Observed, bounded:** live log messages show requests around 2.4 seconds. Requests are serialized through the bot-owned MT5 session; the bot records that cycles do not overlap. Continue monitoring the refresh latency during the DEMO week. |
| **LOW** | The event table retains historical ERROR/CRITICAL events from earlier startup/watchdog and order-rejection incidents. | **Historical only:** the latest supervised runtime began at 20:35 Baku. No ERROR/CRITICAL event has been recorded since that restart; older records remain available for diagnosis. |

## Safety review

- Order entry checks DEMO mode, terminal permissions, supported symbol specs, existing positions and risk gates. The guarded E2E path additionally requires `STOP=PAUSE`, checks DEMO and terminal trading permission, targets only `EURUSD#`, submits `order_check`, confirms server SL/TP, tightens the SL, closes the position and restores PAUSE in a `finally` block.
- The session UI showed login `108765323`, server `XMGlobal-MT5 5`, and Demo Account before the E2E order. The order used the broker minimum `0.01` lot. It closed successfully; realized test P/L was approximately `-$0.10`.
- The normal STOP file blocks new entries while position management continues. `HALT` requests a clean supervisor exit. The executor enforces ownership by `magic_number`; hedging/netting checks and protective-stop reconciliation are covered by the existing executor and bot tests.
- Sizing rounds down to broker volume steps and refuses a minimum lot that exceeds the risk budget. Stop and target are built and validated before submission. Strategy parameters and research outputs were not changed in v8.
- Broker suffix resolution is discovered from the terminal symbol list; the live test used `EURUSD#`. Spread-based costs, slippage and configured commission estimates remain part of the live cost gate. The configured commission default is estimated at `$0.00` per lot per side, not confirmed from new-account deal history.
- SQLite maintenance, retention, backup and retry code is present. The dashboard reads SQLite and binds to localhost; its HTTP endpoint returned 200 at `http://localhost:8501`.
- The self-test passed all checks after PAUSE was cleared: DEMO mode, real-account guard, `.env` ignore rule, disk, SQLite schema, recent heartbeat, MT5 connection/permission, STOP state, brain safe mode and dashboard socket.

## Verification

- All direct pinned dependencies imported under `.venv` on CPython 3.12.10 / Windows x64.
- `pip check`: no broken requirements.
- Full pytest: 433 passed (169 dependency/deprecation warnings).
- Local dashboard: HTTP 200 at `http://localhost:8501`.
- Current run: supervisor and bot healthy on DEMO; the current heartbeat reports MT5 connected and trading allowed. Two bot-owned trades opened after STOP was cleared; both database records include SL and TP. Their broker-side state continues to be managed by the bot.
