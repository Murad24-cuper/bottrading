# Edge research v2 — not run

Run date: 2026-11-09. Research is **not complete**. No family below was
implemented/executed on train and validation data; zero is the number of
trades actually evaluated, not a measured strategy outcome. No edge is
qualified or declared to have failed. The 2026-11-08 brain-gate holdout was
not read or modified.

| Family | Requested data | Train trades | Validation trades | Train net expectancy | Validation net expectancy | Positive walk-forward share | Random benchmark | Deflated Sharpe | Qualifies |
|---|---|---:|---:|---:|---:|---:|---|---|---|
| London / New York session breakout (M15/H1) | Train/validation cost-map cells with cost <10% stop | 0 evaluated | 0 evaluated | n/a | n/a | n/a | not run | not run | No — not evaluated |
| Index opening range breakout (30/60 min cash open) | Train/validation cost-map cells with cost <10% stop | 0 evaluated | 0 evaluated | n/a | n/a | n/a | not run | not run | No — not evaluated |
| VWAP reversion with non-trending higher timeframe | Train/validation cost-map cells with cost <10% stop | 0 evaluated | 0 evaluated | n/a | n/a | n/a | not run | not run | No — not evaluated |
| Donchian breakout trend following, H4/D1 | Maximum native history with manifests | 0 evaluated | 0 evaluated | n/a | n/a | n/a | not run | not run | No — not evaluated |
| Time-series momentum (1/3/6/12 months, vol-scaled) | Maximum native history with manifests | 0 evaluated | 0 evaluated | n/a | n/a | n/a | not run | not run | No — not evaluated |
| Index pullback in a 200-day uptrend | Maximum native history with manifests | 0 evaluated | 0 evaluated | n/a | n/a | n/a | not run | not run | No — not evaluated |

## Why execution was blocked

The repository has no implementations for these six families or a v2 runner.
The currently supervised bot owns the single MT5 session, and there is no
maintenance RPC for an offline process to request and await maximum-history
downloads. Native H4/D1 cache files and some manifests exist (10 H4 and 9 D1
manifests at inspection), but this does not establish complete maximum ranges
or provide the missing family implementations. Step 1 account/instrument
facts and verified commission were unavailable; therefore no calibrated
cost-map cells can be used to select the required <10%-of-stop universe.
The validation toolkit also lacks the matched random-entry run, positive
walk-forward share and multiple-testing correction required by the
qualification rule.

## Decision

Case A cannot be applied: no strategy qualifies. Case B also cannot be
claimed as a completed research conclusion because the specified research was
not run. Keep normal entries disabled as the existing fail-closed setting;
the prior Case B decision remains provisional until v2 is executed. No
holdout gate or brain retraining was run.
