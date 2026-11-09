# Lookahead and warm-up review

## Evidence from this pass

Added a future-perturbation test over EMA, ATR, ADX, RSI, ROC, MACD, Bollinger
bands, swing/support/resistance, breakout levels, candle structure, relative
volume and the brain's `build_features` snapshot. It tests three internal
timestamps and replaces every later candle with extreme OHLC and volume
values. The result is unchanged (`tests/test_causality.py`: pass).

The indicator implementations are backward-looking: rolling/ewm calculations,
shifted breakout windows, and swing pivots are emitted on the confirmation bar.
The four strategy implementations read only the supplied candle frames and
their trailing bars. This source review is not equivalent to a complete replay
of every strategy and trained brain vector over all historical train and
validation timestamps.

## Not established

History-start sensitivity has not been quantified, and the full truncated vs.
full-data run across every strategy/brain feature on persisted train and
validation history was not run. The current brain training artifacts include a
holdout split; this pass deliberately did not load or inspect holdout rows.
Consequently the full-history verification remains **incomplete**. A safe
complete run must select train/validation timestamps only from `splits.json`,
then compare outputs at each sampled as-of timestamp and separately vary the
warm-up start while keeping the evaluated timestamp fixed.
