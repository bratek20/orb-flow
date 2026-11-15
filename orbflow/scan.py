"""Cross-pair scanner on the latest hourly exchange snapshot.

For every item we compute the *implied* price in ex from each "money" pair it trades in
(item<->exalted, item<->chaos, item<->divine) using units actually traded in that hour:

    implied_ex = (money_units * money_value_ex) / item_units

If the same item is cheap vs one money currency and expensive vs another, that is a
candidate chain:  money_A -> item -> money_B -> (convert back) money_A.

These are LEADS, not facts: an hourly aggregate hides the live order book. Verify in game.
"""
from __future__ import annotations

import argparse
import collections

from .db import connect

MONEY = ("exalted", "chaos", "divine")


def money_rates(con, league, sid):
    """Value of chaos/divine in ex from their direct pairs with exalted (units ratio)."""
    rates = {"exalted": 1.0}
    for m in ("chaos", "divine"):
        r = con.execute("""SELECT one_api, one_volume, two_volume FROM pair_snapshots
                           WHERE league=? AND snapshot_id=? AND
                           ((one_api='exalted' AND two_api=?) OR (one_api=? AND two_api='exalted'))""",
                        (league, sid, m, m)).fetchone()
        if r and r["one_volume"] and r["two_volume"]:
            ex_units, m_units = ((r["one_volume"], r["two_volume"]) if r["one_api"] == "exalted"
                                 else (r["two_volume"], r["one_volume"]))
            rates[m] = ex_units / m_units
    # fallback for divine via chaos if needed
    return rates


def implied_prices(con, league, sid=None, min_units=20):
    if sid is None:
        sid = con.execute("SELECT MAX(snapshot_id) FROM pair_snapshots WHERE league=?", (league,)).fetchone()[0]
    rates = money_rates(con, league, sid)
    out = collections.defaultdict(dict)
    for r in con.execute("SELECT * FROM pair_snapshots WHERE league=? AND snapshot_id=?", (league, sid)):
        for item, iu, money, mu in ((r["one_api"], r["one_volume"], r["two_api"], r["two_volume"]),
                                    (r["two_api"], r["two_volume"], r["one_api"], r["one_volume"])):
            if money in MONEY and item not in MONEY and iu and mu and money in rates:
                if iu < min_units and mu < min_units:
                    continue
                out[item][money] = {"ex": mu * rates[money] / iu, "item_units": iu, "money_units": mu}
    return rates, out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--league", default="Forbidden Rites")
    ap.add_argument("--min-units", type=int, default=20)
    ap.add_argument("--min-gap", type=float, default=1.25)
    ap.add_argument("--max-buy-ex", type=float, default=100.0, help="budget: unit price we can afford")
    a = ap.parse_args(argv)
    con = connect()
    rates, imp = implied_prices(con, a.league, min_units=a.min_units)
    print("money rates (ex):", {k: round(v, 2) for k, v in rates.items()})
    rows = []
    for item, d in imp.items():
        if len(d) < 2:
            continue
        lo_m = min(d, key=lambda m: d[m]["ex"])
        hi_m = max(d, key=lambda m: d[m]["ex"])
        gap = d[hi_m]["ex"] / d[lo_m]["ex"]
        if gap >= a.min_gap and d[lo_m]["ex"] <= a.max_buy_ex:
            rows.append((gap, item, lo_m, d[lo_m], hi_m, d[hi_m]))
    rows.sort(key=lambda r: -r[0])
    print(f"\n{'item':34s} {'buy with':>8s} {'@ex':>9s} {'units/h':>7s}  {'sell for':>8s} {'@ex':>9s} {'units/h':>7s}  gap")
    for gap, item, lm, l, hm, h in rows[:40]:
        print(f"{item:34s} {lm:>8s} {l['ex']:9.2f} {l['item_units']:7d}  {hm:>8s} {h['ex']:9.2f} {h['item_units']:7d}  x{gap:.2f}")


if __name__ == "__main__":
    main()
