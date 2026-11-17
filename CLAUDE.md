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
- `python -m orbflow.chains --budget N`: ranked buy-in-one-market / sell-in-another chains, with fill-time estimates
- `python -m orbflow.board [--collect|--serve]`: robust round finder (per-hour gap check, gold per leg) -> reports/board.html;
  `--serve` refreshes hourly and serves it on the LAN (phone). This is the no-Claude view.
- `python -m orbflow.trades add|fill|cancel|list|calib`: log of real orders (ground truth for fill times and gold)
- `python -m orbflow.scan`: raw cross-pair gaps. `journal`: advice log and grading. `backtest`: v0 harness

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

## Where we left off (2026-11-16)
- 2026-11-17: echoes (140) and regal->13 div filled overnight; 3 armour-infusers bought at 6 chaos, ask 1.67 div did not fill (reprice to 1.5).
- Player made +30 div with the ex -> regal -> div loop. Holdings 2026-11-16 evening: 242 ex, 40 chaos, 33 div
  (+ open orders: 140 echoes for 50 chaos, 828 regal -> 12 div). Gold ~1.0M (spent ~400k for the +30 div, ~13.3k gold per div).
- Proposed next: test Omen of Chaotic Rarity (buy with ex ~60, sell for chaos/div ~300-390) and chaos-funded
  Omen of Abyssal Echoes (buy with chaos ~24 ex, sell for div ~52). Need per-unit gold fee for omens.
- Trade #9 in the trades table is an aggregate summary row, not a single order.
- Backlog: calibrate FILL_SHARE from fills, `trades import` from data/trades.csv,
  use poe.ninja as a second price source inside chains (snapshot prices are noisy with only a few snapshots).
- `python -m orbflow.liquidity <item> --qty N` answers "how long will it take to sell".
- `python -m orbflow.cycles --legs ...` / `--scan`: full rounds div->...->div with gold on EVERY leg, plus a poe.ninja check.
  Gold is now the player's main constraint: rank by ex per 1k gold. Collect per-unit gold fees for catalysts/omens/infusers.
