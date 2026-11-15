# OrbFlow: working notes for Claude

PoE2 Currency Exchange analysis tool. Claude is the "analyst" in the loop for now; the code is
the toolbox. Read `docs/PLAN.md` (roadmap) and `docs/FINDINGS.md` (what we learned so far) first.

## Before answering any market question
1. Check how fresh the data is:
   `python -c "import sqlite3;print(sqlite3.connect('data/orbflow.db').execute('select max(fetched_at) from pair_snapshots').fetchone())"`
2. If the latest snapshot is older than ~1 hour, refresh: `python -m orbflow.collect`
   (one call, ~1.5 MB). Each refresh also grows our own per-pair history, which poe2scout does not keep.
3. If price history is older than ~1 day, also run `python -m orbflow.collect --backfill-hours 48`.
4. Run `python -m orbflow.journal grade` so old advice gets scored before giving new advice.
5. After analysis, journal new advice (`python -m orbflow.journal advise`) and add notable
   learnings to `docs/FINDINGS.md`. When the player reports in-game ratios or fills, write them
   down there too. They are ground truth and beat the API numbers.

No scheduled tasks. Data is only downloaded while we work.

## Player context
- Starting budget: 100 ex for experiments (holds ~50 chaos total). Gold: ~1.4M, so not a constraint yet.
- Wants to start small, verify each strategy in game, then scale up.
- Analysis only: never automate in-game actions (GGG ToS).

## Data caveats (important)
- poe2scout per-item hourly price blends all pairs, so it is noisy and causes fake mean reversion.
- Pair "units traded per hour" ratios often disagree with the live in-game book (see FINDINGS).
  Treat API numbers as leads and ask the player for live ratios before recommending real trades.
- Python stdlib only; run modules as `python -m orbflow.<module>` from the repo root.
