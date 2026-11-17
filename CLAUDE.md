# OrbFlow: working notes for Claude

PoE2 Currency Exchange analysis tool. Claude is the "analyst" in the loop for now; the code is
the toolbox. Read `docs/PLAN.md` (roadmap) and `docs/FINDINGS.md` (what we learned so far) first.

## Before answering any market question
1. Refresh: `python -m orbflow.ggg` (fetches only the missing GGG hours, ~1.4 MB each; newest hour is ~1-1.5 h late)
   and `python -m orbflow.collect` (one poe2scout snapshot; needed so new items get mapped to names).
2. GGG's public feed (web.poecdn.com/api/currency-exchange/poe2/<unix hour>) is THE source: no login, full history,
   lowest/highest ratio per pair per hour. `python -m orbflow.ggg --show <item>` shows hourly avg/low/high per money market.
   No OAuth application is needed (decided 2026-11-17).
3. If price history is older than ~1 day, also run `python -m orbflow.collect --backfill-hours 48`.
4. Run `python -m orbflow.journal grade` so old advice gets scored before giving new advice.
5. After analysis, journal new advice (`python -m orbflow.journal advise`) and add notable
   learnings to `docs/FINDINGS.md`. When the player reports in-game ratios or fills, write them
   down there too. They are ground truth and beat the API numbers.

No scheduled tasks. Data is only downloaded while we work.

## Main tools
- `python -m orbflow.ggg [--hours N] [--show <item>]`: GGG public hourly feed (the main data source), avg/low/high per hour
- `python -m orbflow.board [--collect|--serve]`: robust round finder on GGG hours (per-hour gap check, gold on every leg,
  low/high prices) -> reports/board.html. `--serve` refreshes hourly and serves it at http://<pc-ip>:8765/board.html
  (phone on the same Wi-Fi). This is the no-Claude view. Hosted: https://bratek20.github.io/orb-flow/ (GitHub Actions
  `.github/workflows/board.yml` rebuilds it hourly at :25; repo https://github.com/bratek20/orb-flow, public).
- `python -m orbflow.cycles --legs "div>chaos@10.4" "chaos>monsters@1.67" "monsters>div@/7"`: one full round with gold per leg
  (use the player's live ratios). `--scan` is the older poe2scout-based version of the board.
- `python -m orbflow.liquidity <item> --qty N`: units/h per market, queue size, time-to-fill estimate
- `python -m orbflow.trades add|fill|cancel|gold|list|calib`: log of real orders (ground truth for fills AND gold fees;
  `chains.gold_table` reads fees from here). After each change re-export data/trades.csv (it's committed; the DB is not).
- `python -m orbflow.names [short]`: short-name table. Older/less used: `chains`, `scan`, `journal`, `backtest`.

## Item names
The player writes full names; gently remind them of the short name (they want to learn them).
Use short names when talking to the player (rarity, echoes, necro-cat, gex, div, ex...). `python -m orbflow.names`
prints the table (docs/NAMES.txt), and every CLI accepts short names.

## Player context
- Started with a 100 ex budget (~50 chaos total). Gold: ~1.4M at start. The gold fee is per unit WANTED (see FINDINGS).
- Wants to start small, verify each strategy in game, then scale up.
- Analysis only: never automate in-game actions (GGG ToS).

## Data caveats (important)
- poe2scout per-item hourly price blends all pairs, so it is noisy and causes fake mean reversion.
- Pair "units traded per hour" ratios often disagree with the live in-game book (see FINDINGS).
  Treat API numbers as leads and ask the player for live ratios before recommending real trades.
- Python stdlib only; run modules as `python -m orbflow.<module>` from the repo root.

## Strategy playbook (what we learned, details in docs/FINDINGS.md)
- Core edge: many items trade far cheaper vs ex (or chaos) than vs div. Buy in the cheap market, sell for div.
- GOLD is the binding constraint, not currency. Fee = units WANTED x per-unit fee of the wanted item
  (ex 120, regal 120, chaos 160, div 800, infuser 250, rarity/monsters 450, echoes/gcp 1000; table in FINDINGS).
  Rank routes by gold per div of profit. Fund with chaos (div->chaos ~1.7k gold/div), not ex (~72k gold/div).
- Proven rounds: ex->regal->div (+30 div, ~13-15k gold/div profit); chaos->echoes->div (5-8/div, 7.5-13k);
  chaos->monsters->div (1.67/chaos -> 7/div, ~7k gold/div, best now); armour-infuser worked once at 6 chaos but
  the normal price is 12-16 chaos (one dump hour) -> no edge.
- Before calling a gap real, check it hour by hour (`ggg --show`), not as an average. Then ask the player for the live book.
- The player reports trades as "want_qty want - give_qty give (gold)", e.g. "10 monsters - 6 chaos (4500)".
  Log every one with `trades add` (gold included) and note fills.

## Where we left off (2026-11-17, morning)
- Holdings (approx): ~45 div, ~180 chaos, 58 ex; gold ~0.75M (estimate, ask). Open orders (see `trades list`):
  #18 140 echoes -> 28 div (5/div, ambitious; fallback 6, never below 8), #22 7 monsters left -> 1 div,
  #23 buy 30 monsters for 18 chaos. Player also wanted a p-charging-rune (~6-8 div) for personal use.
- Next: scale monsters if #23 fills and sells hold 7/div (bids of 50-100); test sin-necromancy (ex 1-2.5 -> div 0.05-0.08,
  gold fee unknown); fill in unknown gold fees ("gold?" on the board) for catalysts/omens.
- Ideas not done: alerts when a proven route crosses a threshold, calibrate FILL_SHARE from fill times, `trades import` from CSV.
- Trade #9 in the trades table is an aggregate summary row, not a single order.
