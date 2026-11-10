# Current blockers

Updated: 2026-11-10 20:37 Asia/Baku

## Resolved: Windows native dependency loading

After Smart App Control was turned off and Windows restarted, the project's
CPython 3.12.10 virtual environment successfully imported pandas 2.2.3,
NumPy 2.5.4, MetaTrader5 5.0.6231, fastparquet 2026.9.0 and the remaining
pinned direct dependencies. The required Streamlit `pyarrow` dependency
imports as well; project Parquet operations explicitly use fastparquet.
`pip check` reports no broken requirements. The prior pandas `_libs` policy
denial did not recur, so no CodeIntegrity event capture was needed.

## Live state

The supervisor and bot are running on XM DEMO login `108765323`. The latest
health checks report DEMO, MT5 connected, trading allowed, no STOP file, and
the localhost dashboard responding at `http://localhost:8501`. The guarded
EURUSD# minimum-lot open / SL-check / SL-modify / close test succeeded.

See [STATUS.md](STATUS.md) for the current runtime, the remaining monitoring
items and start/stop instructions. See [AUDIT_v8.md](AUDIT_v8.md) for the
project findings and verification evidence.
