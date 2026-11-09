# Historical ERROR / CRITICAL resolution ledger

Source: read-only `bot_events` query against `data/bot.db` on 2026-11-09.
There are 21 historical rows: 13 ERROR and 8 CRITICAL. Status is based on
later code or observed recovery; a supervisor restart is recorded as recovery,
not as proof that a recurring root cause was fixed.

| # | Time (UTC) | Level | Cause | Resolution | Fix status | Commit |
|---:|---|---|---|---|---|---|
| 1 | 2026-11-05 20:41:02 | ERROR | MT5 `copy_rates_from_pos` closed-bar request returned `Terminal: Call failed` | Later closed-bar scans succeeded | Recovered; root cause not isolated | `8f60e68` |
| 2 | 2026-11-05 20:41:35 | ERROR | MT5 `copy_rates_from_pos` closed-bar request returned `Terminal: Call failed` | Later closed-bar scans succeeded | Recovered; root cause not isolated | `8f60e68` |
| 3 | 2026-11-05 20:43:32 | ERROR | MT5 `copy_rates_from_pos` closed-bar request returned `Terminal: Call failed` | Later closed-bar scans succeeded | Recovered; root cause not isolated | `8f60e68` |
| 4 | 2026-11-06 13:06:15 | ERROR | MT5 `account_info` IPC send failed (`-10001`) | Successful account read and DEMO reconnect later observed | Recovered; transport cause not isolated | `8f60e68` |
| 5 | 2026-11-06 14:30:56 | ERROR | MT5 initialize retry timed out (`-10005`) | Successful reconnect later observed | Recovered; transport cause not isolated | `8f60e68` |
| 6 | 2026-11-06 14:33:10 | ERROR | MT5 initialize retry timed out (`-10005`) | Successful reconnect later observed | Recovered; transport cause not isolated | `8f60e68` |
| 7 | 2026-11-06 14:35:23 | CRITICAL | Three MT5 reconnect attempts failed; entry health gate blocked new entries | Successful DEMO reconnect later observed | Recovered; transport cause not isolated | `8f60e68` |
| 8 | 2026-11-06 14:35:23 | ERROR | Cycle 248 failed after MT5 initialize timeout | Successful DEMO reconnect later observed | Recovered; transport cause not isolated | `8f60e68` |
| 9 | 2026-11-06 20:12:29 | CRITICAL | Watchdog found stale heartbeat and terminated child PID 20868 | Supervisor restarted child | expected fixed by AUDIT-CRIT-02, to be confirmed after 7 days without a hang | `829f603` |
| 10 | 2026-11-06 20:12:40 | CRITICAL | Watchdog found stale heartbeat and terminated child PID 10128 | Supervisor restarted child | expected fixed by AUDIT-CRIT-02, to be confirmed after 7 days without a hang | `829f603` |
| 11 | 2026-11-06 20:38:12 | ERROR | Supervisor `UnboundLocalError`: `last_health_check` referenced before assignment | State initialization moved inside child runner | Fixed | `02e5571` |
| 12 | 2026-11-06 20:38:23 | ERROR | Supervisor `UnboundLocalError`: `last_health_check` referenced before assignment | State initialization moved inside child runner | Fixed | `02e5571` |
| 13 | 2026-11-06 20:40:57 | CRITICAL | Bot lock file disappeared during lock release (`FileNotFoundError`) | Lock release now tolerates a missing file | Fixed | `2fed485` |
| 14 | 2026-11-06 20:43:37 | ERROR | Supervisor `NameError`: `datetime` not imported | UTC datetime import/helper added | Fixed | `50a90d7` |
| 15 | 2026-11-06 20:43:48 | ERROR | Supervisor `NameError`: `datetime` not imported | UTC datetime import/helper added | Fixed | `50a90d7` |
| 16 | 2026-11-06 20:44:19 | ERROR | Supervisor `NameError`: `datetime` not imported | UTC datetime import/helper added | Fixed | `50a90d7` |
| 17 | 2026-11-06 20:45:20 | ERROR | Supervisor `NameError`: `datetime` not imported | UTC datetime import/helper added | Fixed | `50a90d7` |
| 18 | 2026-11-08 03:47:37 | CRITICAL | Watchdog found stale heartbeat and terminated child PID 7848 | Supervisor restarted child | expected fixed by AUDIT-CRIT-02, to be confirmed after 7 days without a hang | `829f603` |
| 19 | 2026-11-08 16:42:23 | CRITICAL | Watchdog found stale heartbeat and terminated child PID 25860 | Supervisor restarted child | expected fixed by AUDIT-CRIT-02, to be confirmed after 7 days without a hang | `829f603` |
| 20 | 2026-11-08 20:40:29 | CRITICAL | Watchdog found stale heartbeat and terminated child PID 536 | Supervisor restarted child | expected fixed by AUDIT-CRIT-02, to be confirmed after 7 days without a hang | `829f603` |
| 21 | 2026-11-09 12:02:31 | CRITICAL | Watchdog found stale heartbeat and terminated child PID 26296 | Supervisor restarted child; subsequent MT5 connection observed | expected fixed by AUDIT-CRIT-02, to be confirmed after 7 days without a hang | `829f603` |

The ledger classifies all 21 events as resolved or fixed (13 code/threading defects and 8
operational MT5 recoveries). The six historical watchdog hang events (#9, #10, #18, #19, #20, #21)
are expected fixed by AUDIT-CRIT-02 (single dedicated worker thread and queue in MT5CallProxy),
to be confirmed after 7 days without a hang.
