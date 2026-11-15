"""Chain finder: buy an item cheaply in one "money" market, sell it in another.

Confirmed in game (2026-11-15):
  * Regal: bought 245 @ 0.41 ex (bid in the ex market), sold 80 regal -> 1 div (~7.4 ex each)
  * Gemcutter's Prism: bought @ 20 ex, sold 1:1 for chaos (~58 ex)
Pattern: many items trade far cheaper against Exalted than against Chaos / Divine.

For each item we take every collected hourly snapshot, compute the volume-weighted implied price
(in ex) inside each money pair, and the median units traded per hour. Then for every ordered
pair of money markets (cheap -> expensive) we estimate:

  gap        = sell_price / buy_price
  lot        = smallest sell order that makes sense (1 div or 1 chaos worth of items)
  fill hours = how long a maker order of that size waits, ~ qty / (FILL_SHARE * units_per_hour)
  ex/hour    = profit per lot / (buy hours + sell hours)

FILL_SHARE is the part of a pair's hourly volume that would hit *our* order. It starts as a guess
and should be calibrated from the trades table (python -m orbflow.trades calib).
"""
from __future__ import annotations

import argparse
import collections
import math
import statistics as st

from .db import connect

MONEY = ("exalted", "chaos", "divine")
FILL_SHARE = 0.5   # calibrate! first data point (regal ex bid) suggested ~0.7-1.0
HAIRCUT = 0.15     # we will not get the average price on both legs; leave room
DEFAULT_GOLD_PER_EX = 120.0  # gold fee per ex of order value; 1st observation: 57k gold for a 478-ex order


def gold_per_ex(con, rates):
    """Calibrate the gold fee from logged trades that have a gold cost and a money-currency side.
    Model: fee = k * (order value in ex). Returns (k, n_observations)."""
    obs = []
    try:
        rows = con.execute("SELECT * FROM trades WHERE gold IS NOT NULL AND gold > 0").fetchall()
    except Exception:
        rows = []
    for r in rows:
        for cur, qty in ((r["want"], r["want_qty"]), (r["give"], r["give_qty"])):
            if cur in rates and qty:
                obs.append(r["gold"] / (qty * rates[cur]))
                break
    return (st.median(obs), len(obs)) if obs else (DEFAULT_GOLD_PER_EX, 0)


def load(con, league, last_n=24):
    sids = [r[0] for r in con.execute(
        "SELECT DISTINCT snapshot_id FROM pair_snapshots WHERE league=? ORDER BY snapshot_id DESC LIMIT ?",
        (league, last_n))]
    marks = ",".join("?" * len(sids))
    rows = con.execute(f"SELECT * FROM pair_snapshots WHERE league=? AND snapshot_id IN ({marks})",
                       (league, *sids)).fetchall()
    # money rates in ex per snapshot (from direct pairs with exalted)
    rates = collections.defaultdict(lambda: {"exalted": 1.0})
    for r in rows:
        for m in ("chaos", "divine"):
            if {r["one_api"], r["two_api"]} == {"exalted", m} and r["one_volume"] and r["two_volume"]:
                ex_u, m_u = ((r["one_volume"], r["two_volume"]) if r["one_api"] == "exalted"
                             else (r["two_volume"], r["one_volume"]))
                rates[r["snapshot_id"]][m] = ex_u / m_u
    # per (item, money): list of (item_units, money_units_in_ex)
    legs = collections.defaultdict(list)
    for r in rows:
        sr = rates[r["snapshot_id"]]
        for item, iu, money, mu in ((r["one_api"], r["one_volume"], r["two_api"], r["two_volume"]),
                                    (r["two_api"], r["two_volume"], r["one_api"], r["one_volume"])):
            if money in MONEY and item not in MONEY and money in sr:
                legs[(item, money)].append((iu or 0, (mu or 0) * sr[money]))
    latest = rates[sids[0]] if sids else {}
    return legs, latest, len(sids)


def market_stats(samples, n_snaps):
    units = sum(s[0] for s in samples)
    value = sum(s[1] for s in samples)
    if units <= 0:
        return None
    per_hour = [s[0] for s in samples] + [0] * (n_snaps - len(samples))  # missing hour = no trades
    return {"price": value / units, "units_h": st.median(per_hour), "hours_seen": len(samples)}


def find_chains(con, league, budget_ex=100.0, min_gap=1.3, min_units_h=20, max_hours=24, gold_k=None):
    legs, rates, n = load(con, league)
    if gold_k is None:
        gold_k, _ = gold_per_ex(con, rates)
    by_item = collections.defaultdict(dict)
    for (item, money), s in legs.items():
        ms = market_stats(s, n)
        if ms and ms["units_h"] >= min_units_h:
            by_item[item][money] = ms
    out = []
    for item, mk in by_item.items():
        for buy_m in mk:
            for sell_m in mk:
                if buy_m == sell_m:
                    continue
                b, s = mk[buy_m], mk[sell_m]
                gap = s["price"] / b["price"]
                if gap < min_gap:
                    continue
                # smallest sensible sell order: 1 unit of the sell currency
                lot = max(1, math.ceil(rates.get(sell_m, 1.0) / s["price"])) if sell_m != "exalted" else 1
                lot_cost = lot * b["price"]
                if lot_cost > budget_ex:
                    continue
                lots = max(1, int(budget_ex // lot_cost))
                qty = lots * lot
                buy_h = qty / (FILL_SHARE * b["units_h"])
                sell_h = qty / (FILL_SHARE * s["units_h"])
                net = qty * (s["price"] - b["price"]) * (1 - HAIRCUT) - qty * b["price"] * HAIRCUT
                hours = buy_h + sell_h
                gold_buy = qty * b["price"] * gold_k          # buy order: value of what we pay
                gold_sell = qty * s["price"] * gold_k         # sell order: value of what we receive
                gold = gold_buy + gold_sell
                if hours > max_hours or net <= 0:
                    continue
                out.append({
                    "item": item, "buy_with": buy_m, "buy_ex": b["price"], "sell_for": sell_m, "sell_ex": s["price"],
                    "gap": gap, "lot": lot, "qty": qty, "cost_ex": qty * b["price"], "net_ex": net,
                    "buy_h": buy_h, "sell_h": sell_h, "ex_per_h": net / max(hours, 0.25),
                    "buy_units_h": b["units_h"], "sell_units_h": s["units_h"],
                    "seen": min(b["hours_seen"], s["hours_seen"]), "snaps": n,
                    "gold": gold, "gold_buy": gold_buy, "gold_sell": gold_sell,
                    "ex_per_kgold": net / max(gold / 1000, 1e-9),
                })
    out.sort(key=lambda r: -r["ex_per_h"])
    return out, rates, gold_k


def main(argv=None):
    ap = argparse.ArgumentParser(description="Find buy-in-one-market / sell-in-another chains")
    ap.add_argument("--league", default="Forbidden Rites")
    ap.add_argument("--budget", type=float, default=100.0, help="ex available for one chain")
    ap.add_argument("--min-gap", type=float, default=1.3)
    ap.add_argument("--max-hours", type=float, default=24)
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--sort", choices=["ex_per_h", "ex_per_kgold", "net_ex"], default="ex_per_h",
                    help="ex_per_kgold when gold is the bottleneck")
    ap.add_argument("--gold-per-ex", type=float, default=None, help="override the calibrated gold fee")
    a = ap.parse_args(argv)
    con = connect()
    rows, rates, gk = find_chains(con, a.league, a.budget, a.min_gap, max_hours=a.max_hours, gold_k=a.gold_per_ex)
    _, nobs = gold_per_ex(con, rates)
    rows.sort(key=lambda r: -r[a.sort])
    print(f"rates: chaos={rates.get('chaos', 0):.1f} ex, divine={rates.get('divine', 0):.0f} ex | budget {a.budget:.0f} ex | "
          f"gold fee {gk:.0f}/ex of order value ({nobs} logged obs) | FILL_SHARE={FILL_SHARE} HAIRCUT={HAIRCUT}")
    print(f"{'item':28s} {'buy':>7s} {'@ex':>7s} {'sell':>7s} {'@ex':>7s} {'gap':>5s} {'qty':>5s} {'cost':>5s} "
          f"{'net':>6s} {'buyH':>5s} {'sellH':>5s} {'ex/h':>6s} {'goldBuy':>8s} {'goldSell':>8s} {'ex/kG':>6s}")
    for r in rows[:a.top]:
        print(f"{r['item'][:28]:28s} {r['buy_with'][:7]:>7s} {r['buy_ex']:7.2f} {r['sell_for'][:7]:>7s} "
              f"{r['sell_ex']:7.2f} {r['gap']:5.1f} {r['qty']:5d} {r['cost_ex']:5.0f} {r['net_ex']:6.0f} "
              f"{r['buy_h']:5.1f} {r['sell_h']:5.1f} {r['ex_per_h']:6.0f} {r['gold_buy']:8.0f} {r['gold_sell']:8.0f} "
              f"{r['ex_per_kgold']:6.2f}")


if __name__ == "__main__":
    main()
