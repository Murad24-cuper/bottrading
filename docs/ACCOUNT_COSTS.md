# Account and trading cost facts

## Collection status

**Not collected in this run.** The local read-only `bot_status` table stores
`account_type`, equity, MT5 connection and trade permission, but it does not
store the broker server name, leverage, symbol contract size, swap rates,
commission schedule, or tick-level spread history. Existing history metadata
does not contain a complete per-hour spread sample or swap fields either.

The supervised child restarted successfully and reconnected to the existing
MT5 terminal, but the bot has no authenticated read-only request channel or
snapshot export for `account_info`, `symbol_info`, or deal history. Reading
these via a separate Python MT5 connection is prohibited because this is the
single live terminal session. The prompt also forbids reading `.env`; this
report does not read it and does not infer or echo credentials. For those
reasons the requested account and instrument facts cannot be obtained safely
from the available persisted data in this run.

| Fact requested | Persisted source available | Result |
|---|---|---|
| Account type | `bot_status.account_type` | DEMO at 2026-11-09 15:32 UTC; equity 1,000.00 account currency |
| Margin mode | MT5 connection log | Hedging, confirmed after the supervised restart at 2026-11-09 15:39 UTC (19:39 Baku time) |
| Server name | none | unavailable |
| Leverage | none | unavailable |
| Commission model | estimated trade fields only; not broker schedule | unavailable |
| Contract size | partial symbol spec cache may exist, not complete/unverified | unavailable |
| Swap long/short | none | unavailable |
| Typical and by-hour spread | no tick archive; bar spread alone is insufficient | unavailable |

No account type or broker pricing change is recommended from missing data.
The cost map remains conservative and treats unknown commission/slippage as
unknown rather than zero where a verified quote sample is required.

## Required safe follow-up

Add a bounded read-only account-cost snapshot to the already running bot's
own MT5 cycle. Persist account server/leverage and each discovered symbol's
contract size, swap long/short, commission evidence and timestamped hourly
spread quantiles. Then export the snapshot to this document without exposing
the account login. Do not start a second MT5 terminal session to collect it.
