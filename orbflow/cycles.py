"""Full trading ROUNDS (cycles) with gold accounting on every leg, starting and ending in divines.

A round = a list of legs. Each leg converts `give` into `want` at a rate (units of want per unit
of give) and costs gold = units WANTED x gold-per-unit(want). Rounds start with 1 div, so results
read as "per divine of capital put through the loop".

Evaluate an explicit round (live in-game numbers beat API numbers):
    python -m orbflow.cycles --legs "divine>exalted@597" "exalted>regal@2.45" "regal>divine@/82"
      (@x = you get x want per 1 give;  @/x = you give x per 1 want)

Scan all 2-3 leg rounds  div -> [fund currency] -> item -> [sell currency] -> div  from market data:
    python -m orbflow.cycles --scan [--sort ex_per_kgold|profit_ex|ex_per_h] [--rate divine=597]
"""
from __future__ import annotations

import argparse
import collections

from .chains import DEFAULT_GOLD_PER_UNIT, FILL_SHARE, MONEY, gold_table, load, market_stats
from .db import connect
from .names import short

HAIRCUT = 0.10  # per trading leg (item buy and item sell): we rarely get the average price


def run_round(legs, gtbl, start_qty=1.0):
    """legs: [(give, want, rate)] -> per-leg breakdown and totals."""
    qty, cur, out, gold, unknown = start_qty, legs[0][0], [], 0.0, []
    for give, want, rate in legs:
        assert give == cur, f"leg {give}>{want} does not continue from {cur}"
        got = qty * rate
        gpu = gtbl.get(want)
        if gpu is None:
            gpu = DEFAULT_GOLD_PER_UNIT
            unknown.append(want)
        g = got * gpu
        out.append({"give": give, "give_qty": qty, "want": want, "want_qty": got, "gold": g, "gpu": gpu})
        gold += g
        qty, cur = got, want
    return {"legs": out, "end_qty": qty, "end": cur, "gold": gold, "unknown_gold": unknown}


def print_round(res, div_ex):
    print(f"{'leg':32s} {'give':>12s} {'get':>12s} {'gold/unit':>9s} {'gold':>9s}")
    for l in res["legs"]:
        mark = " (guess)" if l["want"] in res["unknown_gold"] else ""
        print(f"{short(l['give']) + ' -> ' + short(l['want']):32s} {l['give_qty']:12.2f} {l['want_qty']:12.2f} "
              f"{l['gpu']:9.0f} {l['gold']:9.0f}{mark}")
    if res["end"] == "divine":
        profit_div = res["end_qty"] - res["legs"][0]["give_qty"]
        print(f"\nstart 1 div -> end {res['end_qty']:.2f} div | profit {profit_div:.2f} div "
              f"(~{profit_div * div_ex:.0f} ex) | gold {res['gold']:.0f}")
        if profit_div > 0:
            print(f"gold per div of profit: {res['gold'] / profit_div:.0f} | ex per 1k gold: "
                  f"{profit_div * div_ex / (res['gold'] / 1000):.1f}")
            for l in res["legs"]:
                print(f"   {short(l['give'])}->{short(l['want'])}: {l['gold'] / profit_div:8.0f} gold per div profit")


def parse_leg(s):
    pair, r = s.split("@")
    give, want = pair.split(">")
    rate = 1 / float(r[1:]) if r.startswith("/") else float(r)
    from .names import resolve
    return resolve(give.strip()), resolve(want.strip()), rate


def scan(con, league, rates_override, min_units_h=20, haircut=HAIRCUT):
    legs_data, rates, n = load(con, league)
    rates.update(rates_override)
    gtbl = gold_table(con)
    mk = collections.defaultdict(dict)
    for (item, money), s in legs_data.items():
        ms = market_stats(s, n)
        if ms and ms["units_h"] >= min_units_h:
            mk[item][money] = ms
    div_ex = rates["divine"]
    rows = []
    for item, m in mk.items():
        for fund in m:
            for sell in m:
                if fund == sell or fund not in rates or sell not in rates:
                    continue
                legs = []
                if fund != "divine":
                    legs.append(("divine", fund, div_ex / rates[fund]))
                legs.append((fund, item, rates[fund] / m[fund]["price"] * (1 - haircut)))
                legs.append((item, sell, m[sell]["price"] / rates[sell] * (1 - haircut)))
                if sell != "divine":
                    legs.append((sell, "divine", rates[sell] / div_ex))
                res = run_round(legs, gtbl)
                profit = res["end_qty"] - 1
                if profit <= 0:
                    continue
                item_units = [l for l in res["legs"] if l["want"] == item][0]["want_qty"]
                hours = item_units / (FILL_SHARE * m[fund]["units_h"]) + item_units / (FILL_SHARE * m[sell]["units_h"])
                rows.append({
                    "route": " > ".join(short(x) for x in ["divine"] + [l[1] for l in legs]), "item": item,
                    "profit_ex": profit * div_ex, "gold": res["gold"],
                    "ex_per_kgold": profit * div_ex / (res["gold"] / 1000),
                    "gold_per_div": res["gold"] / profit, "hours_per_div_in": hours,
                    "ex_per_h": profit * div_ex / max(hours, 0.25),
                    "item_units": item_units, "item_gpu_known": item in gtbl,
                    "fund_units_h": m[fund]["units_h"], "sell_units_h": m[sell]["units_h"],
                    "buy_ex": m[fund]["price"], "sell_ex": m[sell]["price"], "sell_m": sell,
                })
    return rows, rates, gtbl


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--legs", nargs="+", help='e.g. "divine>exalted@597" "exalted>regal@2.45" "regal>divine@/82"')
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--sort", default="ex_per_kgold", choices=["ex_per_kgold", "profit_ex", "ex_per_h"])
    ap.add_argument("--rate", action="append", default=[], help="override ex value, e.g. divine=597 chaos=60")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--no-ninja", action="store_true", help="skip poe.ninja cross-check")
    ap.add_argument("--league", default="Forbidden Rites")
    a = ap.parse_args(argv)
    con = connect()
    over = {k: float(v) for k, v in (r.split("=") for r in a.rate)}
    if a.legs:
        _, rates, _ = load(con, a.league)
        rates.update(over)
        print_round(run_round([parse_leg(s) for s in a.legs], gold_table(con)), rates["divine"])
    if a.scan:
        rows, rates, gtbl = scan(con, a.league, over)
        rows.sort(key=lambda r: -r[a.sort])
        nin = {}
        if not a.no_ninja:
            from .client import ninja_prices
            nin = ninja_prices(a.league)
        print(f"rates (ex): { {k: round(v, 1) for k, v in rates.items()} } | haircut {HAIRCUT:.0%}/trade leg | "
              f"* = item gold/unit unknown, guessed {DEFAULT_GOLD_PER_UNIT}")
        print("buy/sell = implied ex price in the fund/sell market; ninja = poe.ninja price (its main market).")
        print("check: OK if ninja agrees within 35% with whichever of our two prices is from ninja's main market")
        print(f"{'route (1 div in)':56s} {'profit':>7s} {'gold':>7s} {'ex/kG':>6s} {'gold/div':>8s} {'hrs':>5s} "
              f"{'units':>5s} {'buy':>7s} {'sell':>7s} {'ninja':>7s} check")
        for r in rows[:a.top]:
            nj = nin.get(r["item"])
            if nj:
                ref = r["buy_ex"] if (nj[1] != r["sell_m"] and short(nj[1]) in r["route"].split(" > ")[:2]) else r["sell_ex"]
                chk = "OK" if abs(nj[0] / ref - 1) < 0.35 else "DIFF"
                nj_s = f"{nj[0]:7.1f}"
            else:
                chk, nj_s = "?", f"{'-':>7s}"
            print(f"{r['route'][:56]:56s} {r['profit_ex']:7.0f} {r['gold']:7.0f} {r['ex_per_kgold']:6.1f} "
                  f"{r['gold_per_div']:8.0f} {r['hours_per_div_in']:5.1f} {r['item_units']:5.0f} {r['buy_ex']:7.1f} "
                  f"{r['sell_ex']:7.1f} {nj_s} {chk}{'' if r['item_gpu_known'] else ' *'}")


if __name__ == "__main__":
    main()
