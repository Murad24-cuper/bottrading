# History dataset provenance

Each history download now writes `data/history/manifests/<symbol>_<tf>.json`
with source, symbol, timeframe, exact UTC start/end, row count, all detected
missing-bar intervals, and SHA-256 of the stored parquet file. Gaps are recorded
as gaps; no rows are synthesized or filled. Hashing streams the parquet file
in bounded blocks. Unit tests cover manifest creation, gap counts and the
stored-file hash. Existing historical datasets will receive manifests when
their next incremental download occurs; this commit does not rewrite them.
