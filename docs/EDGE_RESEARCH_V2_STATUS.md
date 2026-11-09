# Edge research v2 status

The history pipeline and bar simulator now recognize native MT5 H4 and D1
bars. Incremental history settings request up to 120 months of H4 and 240
months of D1 data in bounded batches and write the same provenance manifests
as other timeframes. No H1-to-H4/D1 synthetic resampling is used.

The currently running bot owns the MT5 connection. The repository has no
maintenance RPC for another process to request a native download and wait for
its completion. The updated configuration will let the bot backfill in small
batches after it is restarted, but this turn did not obtain complete ranges or
run a new train/validation experiment. The new session breakout, opening-range
breakout, VWAP reversion, Donchian, time-series momentum and 200-day pullback
strategies are also not implemented. Therefore this part is **incomplete**;
no edge or qualifying strategy is claimed. The previous M1–H1 report remains
separate and its holdout was not re-opened.
