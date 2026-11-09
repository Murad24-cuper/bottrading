# Entry protection gates

In addition to the existing strategy/group adaptive expectancy gate, the bot
now checks config-driven protections for three consecutive symbol losses, a
symbol daily loss threshold in R, and rolling equity drawdown. A protection
pause is persisted to the same `adaptive_gates` table as existing gates, so
the scanner, bot and dashboard see one pause source. Symbol and global pauses
are hard gates and DEMO exploration cannot bypass them. Strategy/group gates
may be bypassed only for risk-limited DEMO exploration; all loss, margin,
session and cost checks still apply. A trigger is logged once and sent to
Telegram once per active gate.

The daily R-loss gate requires closed-trade `process_review.outcome_r`; old
unreviewed rows do not have a reliable money-per-risk denominator and are not
fabricated. Existing fixed cooldown and 20-trade strategy/group expectancy
gates remain. Tests cover each new trigger, expiry, symbol isolation and shared
gate event deduplication.
