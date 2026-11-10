# Current execution blocker

Updated: 2026-11-10 19:38 Asia/Baku

Windows Application Control blocks loading
`.venv/Lib/site-packages/pandas/_libs/pandas_parser.cp312-win_amd64.pyd`
with `ImportError: DLL load failed ... An Application Control policy has
blocked this file.` The error occurs during pandas import, before pytest
collection or bot startup. Reinstalling pandas 3.1.1 from the configured
Python package index did not change the result. I did not modify policy,
unblock binaries, or disable Smart App Control.

Consequences for this run:

- The bot/supervisor process recorded in `data/bot.lock` and
  `data/supervisor.pid` is no longer running; the last heartbeat in
  `data/bot.db` is 2026-11-10 15:30:32 UTC (19:30:32 Baku). The database
  status at that time was DEMO, MT5 connected, trade allowed, with no
  recorded open trade. That is stale status, not confirmation of current
  connectivity.
- `start_bot.bat` did not produce a new supervisor process or heartbeat.
- Direct foreground supervisor startup reproduced the pandas import error
  before it could start the child. No listener was present on port 8501.
- Focused pytest collection failed at the blocked pandas extension.
- Full pytest stopped during collection with 43 import errors, all caused by
  the same pandas extension denial. Independent tests passed:
  `tests/test_db.py` (20 passed) and `tests/test_brain_ood.py` (3 passed).
- `scripts/self_test.py` reported DEMO heartbeat stale and STOP present;
  STOP=PAUSE is being preserved while supervised order execution is
  unavailable. Other static checks passed, but its green panel check did
  not match the direct socket check (no listener on port 8501).
- The last stored scan (15:30:32 UTC) had a USDCAD# Donchian H4 signal
  recorded as `kill switch active`; the database had no open trade rows.
  This is historical state, not a post-restart signal or live MT5 check.
- The guarded live DEMO order-check/open/modify/close command cannot be
  executed until this environment can import pandas under its current
  application-control policy.
- Brain dataset regeneration, holdout_v2 evaluation, dashboard startup,
  and final post-restart health checks are similarly blocked.

Safe continuation: restore a supported runtime whose installed pandas
extension is accepted by the existing Windows policy, then rerun the full
test suite and supervisor startup. Do not clear STOP or attempt the guarded
order while the bot cannot be supervised. STOP remains `PAUSE`.
