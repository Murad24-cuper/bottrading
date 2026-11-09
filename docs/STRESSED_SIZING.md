# Stressed-stop sizing

Before any entry, the live bot starts with its planned stop-based volume, then
recomputes volume using stop loss plus estimated round-trip spread/commission
per lot and two-sided slippage at the configured points. The rounded volume
still uses the broker minimum/step/maximum rules. If the minimum lot breaches
the combined risk budget, the entry is refused. Each candidate stores planned
volume, stressed volume, planned stop risk, stressed risk and estimated cost
per lot in its trade feature snapshot. This remains a conservative estimate;
unknown commission cells fail the cost gate before execution.
