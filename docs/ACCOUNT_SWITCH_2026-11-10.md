# Live account switch · 2026-11-10

Snapshot time (UTC): `2026-11-10T11:09:40.414107+00:00`
New account: XMGlobal-MT5 5 DEMO, login ending `323`, balance/equity `$10000.00 USD`.
Algorithmic trading enabled: `True`.
Previous database archived at `C:\Users\Murad\Desktop\tradingbot\data\account_archive\bot_346494979_before_switch_20261110.db` with old account id `346494979`; active account state was cleared. Forex/gold price history files were retained.

All specifications and spreads below were read from the newly connected MT5 terminal. `spread` is current ask minus bid at snapshot time.

| Logical | Live MT5 symbol | Contract size | Min / step | Tick size | Tick value (loss) | Current spread |
|---|---|---:|---:|---:|---:|---:|
| EURUSD | `EURUSD` | 100000 | 0.01 / 0.01 | 1e-05 | $1.000000 | 2.00 pips |
| GBPUSD | `GBPUSD` | 100000 | 0.01 / 0.01 | 1e-05 | $1.000000 | 2.40 pips |
| USDJPY | `USDJPY` | 100000 | 0.01 / 0.01 | 0.001 | $0.632447 | 2.60 pips |
| AUDUSD | `AUDUSD` | 100000 | 0.01 / 0.01 | 1e-05 | $1.000000 | 2.40 pips |
| USDCAD | `USDCAD` | 100000 | 0.01 / 0.01 | 1e-05 | $0.708110 | 3.10 pips |
| EURJPY | `EURJPY#` | 100000 | 0.01 / 0.01 | 0.001 | $0.632423 | 2.20 pips |
| GBPJPY | `GBPJPY#` | 100000 | 0.01 / 0.01 | 0.001 | $0.632423 | 3.30 pips |
| GOLD | `GOLD#` | 100 | 0.01 / 0.01 | 0.01 | $1.000000 | $0.29 (29 points) |

The prior `docs/MIN_LOT.md` micro-account estimates were not taken from a live terminal. The current terminal exposes standard contract sizes for all eight instruments.
