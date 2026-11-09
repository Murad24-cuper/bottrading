# Locked risk ceilings

The immutable ceilings live in `src/config.py`; `load_settings` rejects a
configuration that exceeds them before bot startup. Strategies, learning
artifacts and Telegram commands cannot alter the loaded risk settings. Config
may tighten each bound, including reducing risk, position count, margin use or
cost allowance. The minimum reward/risk floor cannot be reduced. Tests cover
both tighter settings and attempted increases.

The ceilings currently lock risk per trade at 0.25%, daily loss at 3%, weekly
loss at 8%, 20 positions total, 6 per group, margin use at 50%, total open
stop risk at 5%, maximum cost/target at 30%, and reward/risk at no less than
1.2. Any future authorized adjustment requires a reviewed code change.
