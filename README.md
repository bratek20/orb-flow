# OrbFlow

A market radar for the Path of Exile 2 Currency Exchange. It collects public exchange data, finds
trades worth making (spread flips, cross-currency chains), logs every piece of advice, and grades
that advice later against what actually happened. The goal is advice that is measurably right more
often than not.

**Analysis only.** OrbFlow never touches the game client. Automating in-game actions breaks GGG's
ToS, so you always place orders by hand.

## Quick start

```bash
python -m orbflow.collect --backfill-hours 336   # snapshot all pairs + 2 weeks of hourly item prices
python -m orbflow.scan                            # cross-pair price gaps (leads to verify in-game)
python -m orbflow.journal advise                  # log current leads as advice
python -m orbflow.journal grade                   # later: grade old advice against the newest snapshot
python -m orbflow.journal stats
python -m orbflow.backtest [--grid]               # walk-forward backtest of the spread strategy (v0)
```

The code uses only the Python 3.11+ standard library. Data goes to `data/orbflow.db` (SQLite, git-ignored).

## Data sources

| Source | What it gives | Notes |
|---|---|---|
| `api.poe2scout.com/poe2/...` (OpenAPI at `/openapi/v1.json`) | Latest hourly snapshot of every exchange pair (units traded on each side, stock); hourly price and quantity history per item | No key needed. History per *item* blends all pairs together, see `docs/PLAN.md` |
| `poe.ninja/poe2/api/economy/...` | Price per item and its most-traded pair | No key needed |
| GGG `pathofexile.com/api/currency-exchange/poe2/{ts}` | Official hourly digests per pair with **lowest/highest ratio** and stock | Needs an OAuth app (`service:cxapi`) registered with GGG. This is the best source |

See [`docs/PLAN.md`](docs/PLAN.md) for the roadmap and [`docs/FINDINGS.md`](docs/FINDINGS.md) for what the data has shown so far.
