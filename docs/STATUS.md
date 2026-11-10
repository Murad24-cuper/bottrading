# Current Runtime Status

**Updated:** 2026-11-10 20:37 Asia/Baku

## Current state

- Account: XM DEMO login `108765323`, server `XMGlobal-MT5 5`.
- Supervisor and bot are running from the project `.venv`; recent heartbeat is fresh, MT5 is connected, and algorithmic trading is allowed.
- `STOP` is clear, so entries are enabled subject to the configured DEMO exploration and risk gates.
- The guarded EURUSD# minimum-lot E2E completed: open, server SL/TP check, SL modification and close all succeeded. The test position closed; its realized result was about `-$0.10`.
- Two bot-owned positions opened after resuming. Their database rows contain SL and TP; the bot continues managing them.
- Dashboard is responding locally at **http://localhost:8501** (HTTP 200).
- No ERROR/CRITICAL event has been recorded since the current supervisor restart. Earlier startup/watchdog and rejection incidents remain in the event history.
- Full pytest: 433 passed. `pip check` reports no broken requirements.

## Open issues and monitoring

- Watch incremental history refresh timing: a few sequential MT5 requests took about 2.4 seconds against the 1.5-second target. The bot did not overlap cycles.
- `cost_model.default_commission_per_lot` remains an estimated `$0.00`; confirm actual commission from account deals if XM charges any.
- Older ERROR/CRITICAL events remain in SQLite for audit history; they predate the current healthy runtime.

## Start and stop

From PowerShell in the project folder:

```powershell
.\start_bot.bat
.\start_dashboard.bat
```

Open the dashboard at **http://localhost:8501**.

- **Pause entries:** use the dashboard Pause control or create a `STOP` file containing `PAUSE`. Existing positions continue to be managed.
- **Stop the bot:** use the dashboard **Stop bot** control. The bot exits cleanly and broker-side SL/TP remain in place.
- **Close bot positions and stop:** use **Close all & stop** only when you want bot-owned positions closed too.
- To resume entries, use the dashboard Resume control, which removes `STOP`. The bot must still report DEMO, MT5 connected and trading allowed.

Keep the MT5 terminal running and signed into the DEMO account during the test week. Do not change account mode or risk settings for this run.
