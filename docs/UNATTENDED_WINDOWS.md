# Unattended local Windows operation

`start_bot.bat` starts `scripts/run_forever.py`; the supervisor owns the child,
logs crashes, reconnects the MT5 client through the bot loop, and prevents
duplicates with the PID and bot lock files. The supervisor now requests
Windows `ES_SYSTEM_REQUIRED` while running and clears that request on exit.
The daily maintenance job keeps seven SQLite backups and prunes project log
files older than 14 days. Existing disk-space checks, stale-heartbeat watchdog,
backoff and Telegram daily/weekly notifications remain active.

Run `scripts/install_autostart.ps1` once to register the current-user
`XMTradingBotSupervisor` logon task. Verify it in Task Scheduler Library by
that task name. Task registration is separate from bot startup; its start
action is `start_bot.bat`. A stopped/locked bot is not started twice.

The weekly pipeline still defers retraining because the current strategy set
has no qualified edge and no rolling holdout promotion pipeline is complete.
See `docs/NO_EDGE.md` and `docs/BLOCKERS.md`.
