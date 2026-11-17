# OrbFlow

A market radar for the Path of Exile 2 Currency Exchange. It collects public exchange data, finds
trades worth making (spread flips, cross-currency chains), logs every piece of advice, and grades
that advice later against what actually happened. The goal is advice that is measurably right more
often than not.

**Analysis only.** OrbFlow never touches the game client. Automating in-game actions breaks GGG's
ToS, so you always place orders by hand.

## Quick start

```bash
python -m orbflow.ggg --hours 48        # GGG public exchange feed: last 48 hourly digests
python -m orbflow.collect               # one poe2scout snapshot (used to map game ids to item names)
python -m orbflow.board --serve         # trade board, refreshed hourly: http://localhost:8765/board.html
python -m orbflow.cycles --legs "div>chaos@10.4" "chaos>monsters@1.67" "monsters>div@/7"   # one round, gold per leg
python -m orbflow.trades list           # your logged orders (fills and gold fees)
```

The code uses only the Python 3.11+ standard library. Data goes to `data/orbflow.db` (SQLite, git-ignored);
the trade log is also exported to `data/trades.csv`.

## Data sources

| Source | What it gives | Notes |
|---|---|---|
| GGG `web.poecdn.com/api/currency-exchange/poe2/{unix hour}` | Official hourly digest of every pair: volume, **lowest/highest ratio**, stock. Full history | Public, no login. Items are game metadata paths, mapped to names by `orbflow.ggg` |
| `api.poe2scout.com/poe2/...` | Latest hour of every pair (same data as GGG), item names | Used for name mapping |
| `poe.ninja/poe2/api/economy/...` | Price per item and its most-traded pair | Cross-check |

See [`docs/PLAN.md`](docs/PLAN.md) for the roadmap and [`docs/FINDINGS.md`](docs/FINDINGS.md) for what the data has shown so far.
