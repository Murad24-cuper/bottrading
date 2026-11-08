# Next stage: focus 10 symbols, working signals, news calendar, weekend mode, trader brain, self-learning, Telegram

Context: existing MT5 trading bot (XM, Python) running locally on this
Windows PC on DEMO. Read README.md, config.yaml, src/ (incl. src/brain/),
docs/AUDIT.md, `git status`, `git log` first. This prompt is
SELF-CONTAINED. Do not redo finished work. The server move is cancelled;
everything runs on this PC. Do not connect to any server.

Do everything end to end without waiting for more prompts. Only stop and
ask me if a step is impossible or a safety rule would be violated. Today
is Sunday; markets mostly closed - use the time for code, data and
training; live weekday checks go to the Monday list (part L).

## Rules
- DEMO only. ALLOW_REAL=false. Never print or commit .env.
- Commit after each part; tests for every change; pytest must pass.
- Hard rules never change: SL/TP always set, SL never widened, daily and
  weekly loss limits, margin cap, exposure limits, max 1 open position per
  symbol, DEMO/REAL guard.
- No lookahead in any data, feature, label or model; time-based splits
  with a purge gap >= max hold time.
- Keep the local bot running on DEMO; restart only through the supervisor;
  positions stay.
- Report each part done / not done + reason. No part may be skipped.

---

## F. Focus universe (weekdays)
F1. Trade, scan and train ONLY: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD,
    US500, US100, US30, GER40, GOLD (resolve XM names via aliases, e.g.
    US500Cash, US100Cash, US30Cash, GER40Cash). Everything else excluded.
F2. Max 2 open positions across US500/US100/US30 together.
F3. Diversity rules adapted: min 5 different symbols and 2 groups per day
    (when open), max 4 trades per symbol per day, 20-min cooldown.
F4. History for these 10 symbols via the MT5 data service: M1 1 year, M5
    and M15 3 years, H1 5 years (as far as XM provides; log real ranges).
F5. Clean up: after F4 (and W5) are downloaded and verified, DELETE the
    history Parquet files, brain features/outcomes/memory files and any
    cached candles for all symbols that are NOT in the focus universe or
    the weekend set. Remove them from the universe files and config lists
    too. Keep data/bot.db (trade history) untouched. Report the disk space
    before/after and the list of symbols kept.

## W. Weekend mode (Saturday/Sunday)
W1. Automatic switch by UTC day and open sessions: universe = BTCUSD,
    ETHUSD, GOLD24-7 (resolve the XM name) and any index that is open on
    the weekend (discover and log names).
W2. Horizon 60 min (SL/TP from ATR(M1) * sqrt(60) with the configured
    multipliers), protected extension up to 120 min, risk 0.15% per trade,
    max 3 open positions, the SAME cost filter (no loosening).
W3. Weekend results tracked separately; auto-disable weekend mode for 7
    days if expectancy over its last 20 trades is negative.
W4. Switch back to the weekday focus universe automatically when forex
    opens; close weekend positions on symbols that close for the week per
    the session rules.
W5. History for weekend symbols (M1 6 months, M5/M15 2 years) and a
    separate weekend brain memory.

## N. Economic calendar filter (no AI)
N1. MQL5 script/EA (official MT5 Calendar functions, e.g.
    CalendarValueHistory) that every 15 minutes exports the next 7 days of
    events (time UTC, currency, importance, name, actual/forecast/previous)
    to a CSV/JSON file in the terminal's Files folder. It never trades.
    Install it on the DEMO terminal (attach to one chart, or as a service)
    and document how.
N2. src/news.py reads the file; currency -> symbol map (USD: USD pairs,
    US indices, GOLD; EUR: EURUSD, GER40; GBP: GBPUSD; JPY: USDJPY;
    AUD: AUDUSD; CAD: USDCAD).
N3. No new entries on affected symbols from 15 min before to 15 min after a
    HIGH-impact event. Open positions on affected symbols: move SL to
    breakeven + costs if in profit, otherwise close 5 min before the event
    (close_reason "news").
N4. Calendar file missing or older than 2 hours: WARNING, dashboard notice,
    safe default (no entries on USD/EUR/GBP/JPY symbols 12:30-14:30 UTC).
N5. Dashboard "Yaxın xəbərlər": next 24 h events and what the bot will do;
    translation news -> "Xəbərdən öncə bağlandı". Brain feature: minutes
    to next high-impact event for the symbol's currencies.

## A. Signals: fix strategy logic (not only thresholds)
Friday replay 07:00-21:00 UTC: trend_pullback 37 raw setups, rejects:
276 higher-timeframe alignment, 222 ADX, 119 pullback; mean_reversion
all 7 failed MTF agreement; volatility_scalp 672 rejected by the
volatility threshold. Only 14 signals, 6 symbols, forex only. Re-evaluate on the focus universe.
A1. mean_reversion trades AGAINST the short-term move by design, so the
    generic "M1/M5/M15 must agree" rule is wrong for it. Replace it, for
    this strategy only, with: higher timeframe regime = ranging (ADX low,
    flat EMA) and M1 showing a reversal sign (rejection candle or
    momentum turning). Keep all other filters.
A2. volatility_scalp: replace the fixed volatility threshold with a
    per-symbol relative one: current ATR(M1) percentile vs that symbol's
    last 5 days (enter when >= 70th percentile), so every asset type can
    qualify.
A3. trend_pullback: higher-timeframe alignment may use M15 OR H1 (either
    trending in the trade direction with slope above a small ATR-relative
    threshold); ADX minimum per asset group in config (default 18, not a
    single forex-tuned value); pullback depth defined in ATR units.
A4. All strategy thresholds in relative units (ATR, %, percentiles), never
    pips/points. Strategy parameters per asset group in config.
A5. Re-run the Friday replay on the focus universe. Target: >= 25 signals,
    all 3 groups (forex, indices, metal), >= 7 of the 10 symbols. Report the table before/after. If not met,
    show exactly which rule blocks each group and fix it within these
    floors: confidence 0.5, MTF 2 of 3 (trend strategies), net R:R 1.1,
    cost ratio 0.35.

## E. Demo exploration mode (must be implemented this time)
config demo_exploration.enabled: true; forced OFF on any non-demo account.
E1. A candidate that fails only soft filters (confidence >= 0.45, MTF 2 of
    3, net R:R >= 1.0, cost ratio <= 0.45) is opened as an exploration
    trade. All hard rules still apply.
E2. Risk 0.1% per exploration trade, max 5 open exploration trades,
    max 40 per day, diversity rules apply.
E3. Tag trades mode = "exploration". Exclude them from expectancy, gating,
    readiness checks and the main dashboard metrics; show them in a
    separate "Kəşf əməliyyatları" table with their own stats.
E4. Store their features and outcomes for the brain dataset.
E5. Tests; enable it on the running DEMO bot.

## M. MT5 data service (fix "no safe MT5 handoff")
M1. The bot process owns the MT5 connection. Add a data service inside the
    bot/supervisor that performs incremental history updates for the brain
    universe in small batches between trading cycles (time budget per
    cycle, e.g. 1-2 s), writing Parquet. No second MT5 connection.
M2. Hourly incremental update and the weekly retraining read data from
    these files only; retraining runs in a separate process that never
    touches MT5.
M3. Tests with a mocked MT5.

## B. Trader brain: build the full training pipeline, gate and live switch
The brain now uses ONLY the focus universe (part F) plus the weekend
symbols (part W), with the longer history from part F. What is missing is the outcome/label pipeline, the memory built on
real data, calibration, test predictions, the gate report and the switch.
Implement and RUN all of it:

### B0. Splits
Time-based: train (oldest ~60%), validation (~20%, all tuning), holdout
test (latest ~20%, used ONCE at the very end). Purge gap >= max hold.
Write data/brain/splits.json.

### B3. Layer 1 - book knowledge (src/brain/checklist.py)
A trader's checklist computed on closed bars for both directions, each
item with a weight in config (brain.checklist.weights) and a short
Azerbaijani reason text:
- trend direction on M15/H1 (EMA slope, higher highs/lows) agrees;
- price location: near support for buys / resistance for sells, not
  buying straight into strong resistance (or selling into support);
- chart pattern in trade direction (double bottom/top, head and
  shoulders, triangle/flag/wedge breakout) and no confirmed pattern
  against the trade;
- confirmation candle on M1/M5 (hammer, engulfing, morning/evening star,
  pin bar, etc.);
- Fibonacci reaction (38.2-61.8) of the last swing;
- key levels: TP not blocked by previous day/week high/low or pivot;
  SL not sitting just inside a level;
- momentum agrees (RSI/MACD/ROC) and is not exhausted (no extreme
  divergence against the trade);
- volatility suitable (ATR % within the symbol's normal range, spread
  small vs expected move);
- session/time: active session for that symbol;
- market context: USD strength, risk-on/off and the symbol's group
  direction agree.
Output: checklist score 0..1, list of passed/failed items, one sentence
"Niyə" summary (e.g. "Trend yuxarı, dəstəkdən qalxır, M5-də çəkic şamı,
dollar zəifdir"). Reuse existing indicator/pattern code; add what is
missing. All distances in ATR or %, never pips.

### B4. Layer 2 - similar-chart memory (src/brain/memory.py)
4.1 Situation vector for every sampled bar: normalized shape of recent
    price (e.g. last 48 M5 closes and last 32 M15 closes, returns scaled
    by ATR), plus context (checklist items, trend/momentum/volatility
    state, distance to key levels in ATR, session, USD strength,
    risk-on/off, asset group). Reduce with PCA to ~24-32 dims (fit on
    training data only).
4.2 Outcome per sampled bar and direction: simulate the bot's real trade
    (entry next bar open + spread + slippage; SL/TP from expected 20-min
    move; scale-out, breakeven, trailing, stagnation, max hold; SL first
    if both hit in one bar). Store win (net > 0 after costs) and net R.
    Vectorized.
4.3 Reference memory: per asset group nearest-neighbour index (sklearn
    NearestNeighbors / BallTree). Budget: at most 1.5 million reference
    situations total; sample evenly over time and symbols. Query time
    < 20 ms per symbol-direction.
4.4 For a live query: take k = brain.k_neighbors (default 300) most
    similar PAST situations (strictly earlier than now; for evaluation also
    exclude the same symbol within +-1 day). Probability = distance-weighted
    win rate, shrunk toward the group base rate when neighbours are few or
    far (Bayesian shrinkage), then calibrated (isotonic, fit on the
    validation period). Also average win R, average loss R of neighbours.
4.5 Explanation: "Oxşar vəziyyətlər: 312, onlardan 61%-i qazanıb" and the
    3 most similar past cases (symbol, date) for the dashboard.

### B5. Layer 3 - decision and sizing (src/brain/decide.py, src/brain/sizing.py)
5.1 Candidate passes only if: checklist score >= brain.min_checklist
    (default 0.55), no blocking item failed (buying into strong
    resistance, TP blocked by a key level, confirmed pattern against),
    calibrated p >= brain.min_probability (default 0.55),
    EV = p * avg_win_R - (1 - p) * avg_loss_R - cost_R > brain.min_ev_r
    (default 0.05).
5.2 Ranking by EV, then diversity rules (diversity rules already implemented), then risk checks.
5.3 Size: fractional Kelly f = brain.kelly_fraction (0.25) *
    (p * b - (1 - p)) / b (b = net reward/risk); risk_pct =
    clamp(f * 100, 0.1, 0.5). Before each trade read balance, equity, free
    margin and total open risk; keep total open risk <=
    risk.max_total_open_risk_pct (5); reduce or skip otherwise. calc_volume
    still enforces volume_min/step/max (skip if min lot too risky).
5.4 Coverage: every OPEN symbol of the active universe (focus or weekend) gets the full three-
    layer analysis at least every scanner.full_rotation_seconds (60);
    top movers every cycle. Cache candles, fetch only new bars; cycle
    stays under loop.interval_seconds.
5.5 scanner.target_open_positions: 10, risk.max_open_positions: 20.
    Never force.

### B6. Acceptance gate (scripts/evaluate_brain.py)
On the TEST period only:
- calibration: predicted buckets vs actual win rate, error < 5 points in
  buckets with >= 200 samples;
- trades selected by the full live rule (5.1-5.3 with diversity): at least
  500 trades, positive average net R after costs, profit factor > 1.1,
  positive in at least 2 of 3 sub-periods, results shown per asset group
  and not dependent on one group, at least 7 of the 10 focus symbols traded;
- ablation: checklist only, memory only, both - show which adds value;
- comparison with the current rule-based strategies on the same period.
Write reports/brain_eval_<date>.md. Result PASS or FAIL with reasons.
Only PASS allows live use (brain.enabled: true).

### B7. Shadow mode and live switch
If FAIL or brain.enabled is false: compute and store checklist, memory
probability, EV and suggested size for every candidate (signals.features
JSON), show them on the dashboard, but trade with the current rules.
If PASS: the brain makes the entry and sizing decisions; existing exit
logic and all risk limits stay.

### B8. Dashboard (Azerbaijani)
- Open positions and today's trades: "Niyə" sentence, "Qazanma ehtimalı"
  (%), "Oxşar vəziyyətlər" (count), "Gözlənilən nəticə" ($), "Risk" (%).
- New tab "Beyin": status (Aktiv / Müşahidə rejimində / Yoxlamadan
  keçməyib + reasons), calibration chart (predicted vs actual, test and
  live), ablation table, number of open symbols analysed and rotation
  time, 3 most similar past cases for a selected open position.

### B9. Retraining and drift guard
9.1 scripts/retrain_brain.py weekly (Sunday): download new data, rebuild
    memory and calibration, evaluate; switch only if it passes the gate and
    is not worse than the current one on the latest test period.
    Schedule it on the machine where the bot runs.
9.2 If live calibration error over the last 100 brain trades > 10 points,
    or live expectancy over the last 100 brain trades < 0, switch to shadow
    mode and notify.
9.3 All brain.* keys in config.yaml with comments.

### B11. Improvement loop (if the gate is FAIL)
Do not stop at FAIL. Split history into: train, validation (for all
tuning), and a final holdout test period that is used ONLY ONCE at the
very end. Gate checks during tuning use the validation period.
Up to 5 rounds: find which gate criteria failed and why (per asset group,
hour, session, probability bucket, checklist item, neighbour count and
distance), then improve within the rules, for example:
- trade only probability buckets that are profitable on validation;
- exclude asset groups / hours / sessions with negative expectancy
  (stored in config, visible on the dashboard);
- per-group memories, different k, window lengths and PCA dims;
- tune checklist weights and blocking items;
- adjust SL/TP multipliers within existing floors.
Never change the gate thresholds and never use the holdout for tuning.
After the last round run the gate once on the holdout. Report every round
(what changed, validation result) and the final holdout result. If it
still fails, keep shadow mode and write what would most likely fix it.


### B12. Run it
1. Build outcomes (labels) for sampled bars in both directions with the
   bot's real exit logic and costs (B4.2).
2. Build features/checklist (B3) and the similar-chart memory (B4) from
   TRAIN, calibrate on VALIDATION.
3. Produce data/brain/validation_predictions.parquet and evaluate with
   the gate criteria on validation; run the improvement loop (B11) on
   validation only.
4. Produce data/brain/test_predictions.parquet on the HOLDOUT and run
   scripts/evaluate_brain.py once. Write reports/brain_eval_<date>.md.
5. PASS -> brain.enabled: true on DEMO; FAIL -> shadow mode. Either way
   the live bot computes and stores brain p, EV and suggested size for
   every candidate, visible in the "Beyin" tab.
6. Memory budget for the live process: reference memory <= 800 MB RAM;
   report actual RAM use. Separate memories for weekday and weekend sets.


## S. Self-learning loop (risk rules locked)
S1. Every closed trade (incl. exploration) is added to the similar-chart
    memory with its outcome (no lookahead; size cap, oldest evicted).
S2. Daily adaptive allocation: Thompson-sampling bandit over arms
    (strategy x asset group x session); shift scan priority and the share
    of new trades toward better recent expectancy; each arm keeps >= 5%
    exploration share, max 40%.
S3. Weekly champion/challenger: retrain on all data up to last week,
    compare on the most recent unseen week with the gate criteria; promote
    only if better on expectancy and calibration. Keep 5 versions,
    one-command rollback.
S4. Weekly parameter self-tuning per group (SL/TP multipliers, first
    target, trailing, stagnation, strategy thresholds) with small steps on
    validation; apply only if validation improves without hurting holdout;
    never below floors.
S5. LOCKED: risk per trade limits, loss limits, margin cap, exposure
    limits, SL always set, SL never widened, DEMO/REAL guard. Enforced by
    code and tests.
S6. Weekly report in Azerbaijani ("Bu həftə öyrəndiklərim") on the
    dashboard and Telegram.

## T. Telegram control (optional, works without it)
T1. If TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set in .env: accept
    commands ONLY from that chat id: /status, /today, /positions, /pause,
    /resume, /stop, /closeall (asks for confirmation "/closeall YES"),
    /health. Commands go through the commands table with expiry.
T2. Notifications (Azerbaijani): bot started/stopped, crash/restart, MT5
    disconnected, loss limits hit, big loss, strategy/group disabled,
    news filter active for a major event, daily summary, weekly report.
T3. Never send secrets or the full login. Rate limits. Tests with a
    mocked Telegram API.
T4. TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are already in .env (do not
    print them). Create scripts/test_telegram.py, run it once, and confirm
    the test message was delivered (HTTP ok). If it fails, report the
    error code only (401 = token, 400 chat not found = chat id / Start).

## L. Leave it running and Monday list
L1. Restart through the supervisor; leave bot + dashboard running on DEMO,
    TRADE mode, exploration on, brain active (PASS) or shadow (FAIL),
    weekend mode active now if weekend symbols are open.
L2. scripts/self_test.py all green; live recovery test (kill the bot
    process once, supervisor restarts it and reports it).
L3. docs/MONDAY_CHECKS.md: checks for Monday after 07:00 UTC (signals per
    strategy and symbol, trades with SL/TP, diversity >= 5 symbols / 2
    groups in 2 hours, exploration trades, news filter around the first
    high-impact event, brain predictions stored, cycle time, no
    ERROR/CRITICAL) with the commands to run.

## X. Clean-up of everything old and unused (do this last, after part L)
X1. Delete only things that are not used anymore:
    - code: modules, strategies, scripts and tests that nothing imports or
      runs any more (check with grep/import graph and pytest); old
      experimental or replaced versions;
    - config: keys that no code reads;
    - data: history/brain files of symbols outside the focus and weekend
      sets (part F5), old reports, temporary and cache files, logs older
      than 14 days, DB backups beyond the last 7;
    - old prompt files (codex-prompt-*.md) except this one, which moves to
      docs/prompts/.
X2. NEVER delete: .env, data/bot.db, the current brain model and memory,
    the current history for the focus/weekend symbols, the last 7 backups,
    deploy/linux and the packaging scripts (needed later for the server).
X3. Before deleting, write the list of files to delete with sizes into
    docs/CLEANUP.md. Then delete, run pytest (must pass), restart the bot
    through the supervisor and confirm it runs (heartbeat, DEMO, MT5
    connected, no ERROR/CRITICAL).
X4. Commit as "cleanup unused files". Report disk space before/after and
    the number of files removed.

## FINAL REPORT
1. Each part F, W, N, A, E, M, B0-B12, S, T, L, X: done / not done + reason.
2. Real history ranges per symbol.
3. Friday replay table before/after for the focus universe.
4. Weekend: symbols found, any weekend trades so far.
5. Calendar export working (sample of next events).
6. Brain: dataset size, outcomes, RAM, validation rounds, final holdout
   gate tables, PASS/FAIL, active or shadow.
7. self_test and recovery results. Telegram test result.
8. Clean-up: files removed, disk before/after.
9. pytest result, commits.