# Final prompt implementation status

Repository status refreshed on 2026-11-10. DEMO remains selected and
`ALLOW_REAL` was not read or changed. The 2026-11-08 brain-gate holdout was
not reopened.

| Part | Status | Result / limitation |
|---|---|---|
| 1 | Blocked | DEMO was confirmed from persisted bot status; server, leverage, commission schedule, contract/swap and tick-spread facts are unavailable without a safe request to the MT5-owning process. See `ACCOUNT_COSTS.md`. |
| 2 | Done | MT5 CSV plus HTTPS weekly calendar fallback, UTC normalization, 6-hour refresh, 24-hour cache validity, dashboard source/age, recorded-sample tests. Five upcoming events were verified from the feed. |
| 3 | Partial | Future-perturbation tests cover indicators/features; full strategy and history-start audit remains incomplete, and the old holdout was not touched. |
| 4 | Partial | Shared cost utility and hourly sample collection run; six of eight focus symbols have 650+ samples; EURJPY/GBPJPY have 57/58 across one UTC hour. Coverage is only 8 UTC hours; verified broker commission is unavailable and legacy backtest costs are not fully unified. |
| 5 | Partial | The v3 report runs 200-repetition random-entry benchmarking, six-window walk-forward checks, buy-and-hold comparisons and DSR. Full validation and broker-calibrated costs remain incomplete. |
| 6 | Done (v3 research) | Six families and 18 variants were evaluated with time-based train/validation splits. Boundary-crossing trades are purged; holdout entries are not simulated. Zero variants qualified; see `reports/edge_research_v3.md`. |
| 7 | Done (Case B) | No tested edge qualifies. Normal strategy entries remain disabled; guarded DEMO exploration remains subject to the cost gate and all hard risk protections. Brain remains shadow-only. |
| 8 | Done | Exploration is DEMO-only, capped at 0.1% risk, 3 open positions and 1 per symbol. Family stops/timeframes, MTF, news, cost and protection gates remain active. No exploration trade has opened in the current run. |
| 9 | Done | Config-driven symbol cooldown, symbol daily R loss, rolling drawdown and adaptive gates; events/notifications and tests are present. |
| 10 | Not done | No validated train-memory dissimilarity score/threshold; brain remains shadow-only. |
| 11 | Not done | Verified fill-cost evidence is insufficient for weekly live/backtest reconciliation. |
| 12 | Done | Entry sizing includes stressed spread, commission and doubled slippage; planned and stressed risks are recorded; minimum-lot oversizing still refuses. |
| 13 | Done | Code-enforced risk ceilings reject loosened config; tested. |
| 14 | Done | Dataset manifests include source, ranges, rows, gaps and SHA-256; no synthetic gap fill. |
| 15 | Done | Closed trades store separate process grade and outcome R; learning consumes only good-process rows; dashboard/report exposes both. |
| 16 | Done | SL absence, MT5 disconnect, repeated order rejects, low margin, stale heartbeat, low disk and dual calendar failure have detection, logging and Telegram alerts; entry blocks apply where appropriate. See `INCIDENT_PLAYBOOKS.md`. |
| 17 | Not done | Telegram approval tickets and expiry are not implemented; approval remains off. See blocker. |
| 18 | Not done | Weekly learning stays deferred until walk-forward and rolling holdout promotion gates exist; risk ceilings remain locked. |
| 19 | Partial | Supervisor, restart cap, watchdog, logon scheduled task, awake request, daily backup retention and log pruning exist. Weekly retraining/readiness and fresh MT5 reconnect behavior are not end-to-end verified in this run. |
| 20 | Partial | Point-in-time report is FAIL; no weekly regeneration or Telegram delivery, and incidents lack resolution ledger. |
| 21 | Done (audit) | Cleanup manifest was reviewed. It records prior data cleanup and states no safe unused source/config candidates were found; protected assets remain. No risky code deletion was made. |
| 22 | Partial | Azerbaijani user instructions are documented. One Telegram test returned HTTP 400 `Bad Request: chat not found`; no token/chat ID was exposed. The owner must start a bot conversation, obtain the chat ID from getUpdates and update `.env` manually. Optional exporter and Windows power steps are documented. |

## Evidence snapshot

Read-only SQLite checkpoint at 2026-11-10 10:27 UTC: DEMO, equity 1,000.00,
mode `trade`, bot status `running`, MT5 connected and `trade_allowed`; 8 symbols
scanned (7 forex and GOLD). One `ts_momentum` signal on USDJPY/H4 was recorded
since the latest supervisor restart and rejected by the M1/M5/M15 agreement
gate. There are 0 exploration trades and 0 open bot trades; the 41 closed
main-mode trades remain unchanged. No new order was submitted by this task.

Full test suite after all code changes: **408 passed**. Current blockers and
their safe next actions are in `docs/BLOCKERS.md`.
