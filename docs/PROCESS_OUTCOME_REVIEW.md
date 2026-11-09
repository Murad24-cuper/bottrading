# Trade process and outcome review

Every accepted bot entry stores a process review in the existing trade feature
JSON. The review records that a protective stop/target existed, stressed size
was computed, risk checks passed and the cost-cell gate passed. On close,
executor reconciliation calculates net outcome R including partial closes and
stores the result separately from process grade. Weekly Telegram/event summaries
report process-compliant count and mean outcome R. The dashboard's detailed
closed-trade table shows both values.

Brain drift and bandit observations now use only closed main-mode trades marked
`good_process`; older rows without that review are excluded from learning.
Adaptive risk gates continue to observe all closed trades for safety. Existing
historical rows are not retroactively graded as good process.
