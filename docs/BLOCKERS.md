# Blocked items

| Part | Technical reason | Workaround / next safe action |
|---|---|---|
| 1 — live MT5 account and full broker cost facts | The persistent DB does not contain server, leverage, symbol contract size, swap, broker commission schedule or timestamped hourly tick spreads. No in-process read-only MT5 query channel exists. Opening a second Python/MT5 connection could disturb the live bot session; `.env` is not accessed. | Add snapshot collection to the bot's existing MT5-owned loop and export only non-secret facts. `docs/ACCOUNT_COSTS.md` records field coverage. |
| 6B — native H4/D1 history download | History download requires the MT5 connection owned by the currently running bot. The scanner does not provide an authenticated data-export command, and creating another terminal connection is unsafe. Existing H1 must not be presented as native H4/D1. | Add an MT5-owner maintenance command/queue operation that downloads native H4/D1 bars and writes provenance manifests, then run it through the current bot process. |
| 17 — Telegram approval integration test | Approval mode must remain off by default, and a real `approve <ticket>` could place a DEMO order. The current task requires the bot to remain safe; no new trade ticket can be confirmed without a deliberately isolated approval test harness. | Test ticket lifecycle and no-order guarantees with a fake executor; only test an actual approval in a dedicated DEMO window with an explicit user action. |

Other incomplete sections and exact evidence are recorded per part in
`docs/FINAL_PROMPT_STATUS.md`; no unavailable metric is fabricated.
