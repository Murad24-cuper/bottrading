# Edge research v2 status

The history pipeline supports native MT5 H4/D1 bars and writes provenance
manifests. At inspection, 10 H4 and 9 D1 manifests existed. Six v2 families
were not implemented or executed. The train/validation report therefore lists
0 evaluated trades per family with expectancy, walk-forward share, random
benchmark and corrected Sharpe as n/a/not run; this is not evidence of a
negative edge. There is no claim that requested maximum native history or
<10%-of-stop cost cells are complete. See `reports/edge_research_v2.md` and
`docs/BLOCKERS.md`. The 2026-11-08 holdout was not accessed.
