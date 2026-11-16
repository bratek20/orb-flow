"""Liquidity and time-to-fill for one item in each money market, from global data.

    python -m orbflow.liquidity regal --qty 1239
    python -m orbflow.liquidity omen-of-chaotic-rarity sibilant-catalyst --qty 20

For each market (item vs exalted/chaos/divine) it shows, across all collected hourly snapshots:
  units/h  : item units actually traded per hour (median, min-max)
  price    : implied price in ex (volume weighted)
  stock    : the largest stock seen on the item side, a rough size of the queue of sellers
  fill est : hours to fill `qty` units
               front = you are first in line and get FILL_SHARE of the flow
               back  = you wait behind the whole visible stock
Real fills logged with `orbflow.trades` should be used to calibrate FILL_SHARE.
"""
from __future__ import annotations

import argparse
import statistics as st

from .chains import FILL_SHARE, MONEY
from .db import connect


def market_rows(con, league, item):
    rows = con.execute("""SELECT * FROM pair_snapshots WHERE league=? AND ? IN (one_api, two_api)
                          ORDER BY snapshot_id""", (league, item)).fetchall()
    n_snaps = con.execute("SELECT COUNT(DISTINCT snapshot_id) FROM pair_snapshots WHERE league=?",
                          (league,)).fetchone()[0]
    out = {}
    for r in rows:
        if r["one_api"] == item:
            money, iu, mu, stock = r["two_api"], r["one_volume"], r["two_volume"], r["one_highest_stock"]
        else:
            money, iu, mu, stock = r["one_api"], r["two_volume"], r["one_volume"], r["two_highest_stock"]
        if money not in MONEY:
            continue
        out.setdefault(money, []).append((r["snapshot_id"], iu or 0, mu or 0, stock or 0))
    return out, n_snaps


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("items", nargs="+")
    ap.add_argument("--qty", type=float, default=100, help="units you want to buy or sell")
    ap.add_argument("--league", default="Forbidden Rites")
    a = ap.parse_args(argv)
    con = connect()
    from .chains import load
    _, rates, _ = load(con, a.league)
    from .names import resolve
    for item in map(resolve, a.items):
        mk, n = market_rows(con, a.league, item)
        from .names import short
        print(f"\n{short(item)} = {item}  ({n} hourly snapshots collected, qty={a.qty:g})")
        print(f"  {'market':8s} {'units/h med (min-max)':>24s} {'price ex':>9s} {'stock':>7s} {'front h':>8s} {'back h':>7s}")
        for money, xs in sorted(mk.items()):
            per_h = [x[1] for x in xs] + [0] * (n - len(xs))
            med = st.median(per_h)
            units = sum(x[1] for x in xs)
            price = sum(x[2] for x in xs) * rates.get(money, 1) / units if units else float("nan")
            stock = max(x[3] for x in xs)
            front = a.qty / (FILL_SHARE * med) if med else float("inf")
            back = (stock + a.qty) / med if med else float("inf")
            print(f"  {money:8s} {med:10.0f} ({min(per_h):5.0f}-{max(per_h):6.0f}) {price:9.2f} {stock:7d} "
                  f"{front:8.1f} {back:7.1f}")


if __name__ == "__main__":
    main()
