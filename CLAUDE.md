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

## Main tools
- `python -m orbflow.chains --budget N`: ranked buy-in-one-market / sell-in-another chains, with fill-time estimates
- `python -m orbflow.trades add|fill|cancel|list|calib`: log of real orders (ground truth for fill times and gold)
- `python -m orbflow.scan`: raw cross-pair gaps. `journal`: advice log and grading. `backtest`: v0 harness

## Player context
- Started with a 100 ex budget (~50 chaos total). Gold: ~1.4M at start. The gold fee is per unit WANTED (see FINDINGS).
- Wants to start small, verify each strategy in game, then scale up.
- Analysis only: never automate in-game actions (GGG ToS).

## Data caveats (important)
- poe2scout per-item hourly price blends all pairs, so it is noisy and causes fake mean reversion.
- Pair "units traded per hour" ratios often disagree with the live in-game book (see FINDINGS).
  Treat API numbers as leads and ask the player for live ratios before recommending real trades.
- Python stdlib only; run modules as `python -m orbflow.<module>` from the repo root.

## Where we left off (2026-11-15)
- Confirmed edge: cheap items trade far below value vs Exalted and well above it vs Chaos/Divine.
  Regal loop (ex bid ~2.45 regal/ex, then sell ~80-82 regal/div) and GCP (buy ~15-20 ex, sell 1:1 chaos) both worked live.
- Open order: trade #8, 492 regal -> 6 div (4800 gold). Ask how it went and log the fill (`trades fill 8 --at ...`).
- Fill times for trades #1/#2 were logged with guessed clock times.
- Suggested next test: Omen of the Ancients (buy with ex ~4-4.5, sell for div ~112). Need its per-unit gold fee.
- Backlog: GGG cxapi OAuth application (player is open to it; draft the email), calibrate FILL_SHARE
  from the trades table, persistence check of chains across many snapshots, cut sell prices for div sales
  to market (55-82 regal/div range seen).
