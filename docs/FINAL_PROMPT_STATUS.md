# Final prompt implementation status

Repository work completed on 2026-11-09. DEMO remains selected and
`ALLOW_REAL` was not read or changed. The 2026-11-08 brain-gate holdout was
not reopened.

| Part | Status | Result / limitation |
|---|---|---|
| 1 | Blocked | DEMO was confirmed from persisted bot status; server, leverage, commission schedule, contract/swap and tick-spread facts are unavailable without a safe request to the MT5-owning process. See `ACCOUNT_COSTS.md`. |
| 2 | Done | MT5 CSV plus HTTPS weekly calendar fallback, UTC normalization, 6-hour refresh, 24-hour cache validity, dashboard source/age, recorded-sample tests. Five upcoming events were verified from the feed. |
| 3 | Partial | Future-perturbation tests cover indicators/features; full strategy and history-start audit remains incomplete, and the old holdout was not touched. |
| 4 | Partial | Shared cost utility, hourly sample schema/collection and fail-closed `<10%` entry rule added; no live samples/known commission in DB yet, and legacy backtest costs are not fully unified. |
| 5 | Partial | Sharpe/Sortino/Calmar and 10,000-draw IID bootstrap implemented; random-entry benchmark, rolling walk-forward, full breakdown and multiple-testing correction remain absent. |
| 6 | Not done | No v2 strategy family has been implemented or researched. Native H4/D1 pipeline support exists; MT5-owned download and research RPC are missing. |
| 7 | Done (Case B) | No tested edge qualifies. Normal strategy entries are disabled; guarded DEMO exploration remains subject to calibrated cost and all hard risk gates. Brain remains shadow-only. |
| 8 | Done | Rejected-signal rows are deduplicated; eligible DEMO exploration is isolated from normal strategies and cannot bypass hard protections. It is currently fail-closed until cost cells are calibrated. |
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

Last read-only SQLite checkpoint after the restart was 2026-11-09 15:30 UTC:
DEMO, equity 1,000.00, mode `trade`, bot status `running`, MT5 connected and
`trade_allowed`, hedging margin mode; 10 symbols scanned, 10 movers selected,
zero signals. The 41
closed main-mode trades in the database were unchanged from the existing
readiness report. No new orders were submitted by this task.

Full test suite after all code changes: **271 passed**. Current blockers and
their safe next actions are in `docs/BLOCKERS.md`.
