# OrbFlow plan

## The loop we are building

```
collect (hourly) ──> analyse ──> advise (journaled, with data cut-off) ──> you trade by hand
     ^                                                                        │
     └──── grade advice vs. later data  <── log actual fills (optional) <─────┘
                    │
                    └──> per-strategy hit-rate / EV ──> tune parameters, drop bad strategies
```

Every piece of advice is stored with its `as_of` cut-off. Grading uses only data from after that
cut-off, so the "based on data till Monday 12:00 I'd do X; Monday 13:00 shows whether X was good"
check is built into the design. The backtester replays the same idea over history (walk-forward:
tune on the first half, test on the second).

## Phases

### Phase 0: foundations (done in this commit)
- [x] git repo, package layout, SQLite schema
- [x] poe2scout and poe.ninja clients; pair-snapshot collector; 2-week hourly history backfill
- [x] `scan`: cross-pair implied price gaps
- [x] `journal`: advise, grade, stats
- [x] `backtest`: walk-forward harness plus a spread-band strategy (v0, see the known flaw below)

### Phase 1: trustworthy data (next)
1. **Hourly collector on a schedule** (Windows Task Scheduler runs `python -m orbflow.collect`).
   poe2scout only serves the *latest* pair snapshot, so per-pair history exists only if we record it.
2. **GGG official cxapi**: register an OAuth app, then backfill the whole league per pair with
   lowest and highest ratios. That is real bid/ask information instead of a hourly average.
3. **Ground-truth log**: a tiny CLI where you type what you actually saw or filled in game
   (`orbflow log regal ex 1:1.05 div 52:1`). This calibrates how far API numbers sit from the live book.

### Phase 2: strategies, each graded separately
- `band_mm`: buy at the low quantile of the recent band and sell at the high quantile, rebuilt on **per-pair** series.
- `cross_pair`: buy with currency A and sell for currency B, when the gap persists across hours.
- `cycle`: hour-of-day and weekday seasonality (EU evening vs. NA evening demand).
- `trend`: league-age drift. Items crafters need later in the league go up, loot that is dumped goes down.
- Costs model: gold fee per order, undercut haircut, how long capital is tied up.

### Phase 3: less me in the loop
- `orbflow report` produces a ranked plan for a given budget (what, buy price, sell price, size).
- Recommendation thresholds auto-tuned from journal stats; strategies with poor live EV are auto-disabled.
- Optional notifications (Discord or Telegram webhook) when a strong lead appears.
- Later, possibly: a small dashboard.

## Known flaw in v0 backtest
poe2scout's per-item hourly price mixes pairs (vs ex, vs chaos, vs divine) that imply very different
prices, so the hourly series jumps whenever the pair mix changes. `band_mm` on that series
shows a ~98% hit rate, which is an **artifact**, not an edge. Fix: rebuild the backtest on per-pair
series (Phase 1, steps 1 and 2).
