"""Order sizing: pick a ratio that splits into small lots so partial fills can happen.

A partial fill must be whole units on BOTH sides at your exact ratio, so the smallest piece anyone can take
is the ratio reduced to lowest terms (lot). "23 div : 190 monsters" cannot be reduced -> all or nothing.
"22 div : 187 monsters" = 11 x (2:17) -> fills in pieces of 17 monsters.

Ratios are written like the player reports them: want : give.
    python -m orbflow.ratio div monsters 1:8.3 --have 190          # selling 190 monsters near 8.3 per div
    python -m orbflow.ratio monsters chaos 2:1 --have 100          # buying monsters with 100 chaos near 2 per chaos
    python -m orbflow.ratio div monsters 1:8 --have 190 --tol 0.08 --max-lot 30
    python -m orbflow.ratio div monsters --ahead-of 1:8 --have 190   # cheapest ways to jump the best competing offer

How the book behaves (from GGG hourly low/high ratios, 2026-11-20; no official doc found):
- PRICE priority beats time: in hours when someone listed 2:17 monsters per div, nothing traded at 1:8, even though
  1:8 sellers were in the book. Being first in line at 1:8 does not help once anyone posts a better ratio.
- 93% of all best/worst traded ratios are 1:N, ~4% 2:N. Competitors almost never use finer ratios, so a 3:25 or 2:17
  slot between 1:8 and 1:9 is rarely undercut by a small step; they jump to the next simple ratio instead.
Options: --tol (relative window around the target, default 5%), --max-lot (largest lot on either side, default 40),
--show N rows. Gold = units WANTED x fee of the wanted item (logged fees from the trades table win).
"""
from __future__ import annotations

import argparse
import math

from .chains import DEFAULT_GOLD_PER_UNIT, gold_table
from .db import connect
from .names import resolve, short


def parse_ratio(s: str) -> float:
    """'1:8.3' (want:give) -> give units per 1 want."""
    w, g = (float(x) for x in s.split(":"))
    return g / w


def candidates(target: float, have: float, tol: float = 0.05, max_lot: int = 40, max_want_lot: int = 20):
    """Reduced ratios a:b (want:give) with b/a within tol of target, sized to use `have` units of give.

    target = give per 1 want. Returns dicts sorted by: closest to target, then smaller lot.
    """
    out = []
    for a in range(1, max_want_lot + 1):
        for b in range(1, max_lot + 1):
            if math.gcd(a, b) != 1:
                continue
            price = b / a
            dev = price / target - 1
            if abs(dev) > tol:
                continue
            lots = int(have // b)
            if lots < 1:
                continue
            out.append({"a": a, "b": b, "price": price, "dev": dev, "lots": lots,
                        "want": lots * a, "give": lots * b, "left": have - lots * b})
    out.sort(key=lambda c: (round(abs(c["dev"]), 3), c["b"]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("want")
    ap.add_argument("give")
    ap.add_argument("ratio", nargs="?", help="target want:give, e.g. 1:8.3")
    ap.add_argument("--ahead-of", help="best competing want:give; list ratios just better for the other side")
    ap.add_argument("--have", type=float, required=True, help="units of the give item you put in")
    ap.add_argument("--tol", type=float, default=0.05)
    ap.add_argument("--max-lot", type=int, default=40)
    ap.add_argument("--show", type=int, default=12)
    a = ap.parse_args(argv)

    want, give = resolve(a.want), resolve(a.give)
    if a.ahead_of:
        comp = parse_ratio(a.ahead_of)
        rows = [c for c in candidates(comp * (1 + a.tol / 2), a.have, a.tol / 2 + 1e-9, a.max_lot, a.max_lot)
                if c["price"] > comp + 1e-9]
        rows.sort(key=lambda c: (round(c["price"] / comp - 1, 3), c["b"] if c["b"] >= c["a"] else c["a"]))
        print(f"ahead of {a.ahead_of} ({comp:g} {short(give)} per {short(want)}): cheapest steps, have {a.have:g} {short(give)}")
        print(f"  {'lot':>9}  {'per want':>8}  {'you concede':>11}  {'order (want : give)':>26}  {'left':>5}  {'1:N?':>4}")
        for c in rows[:a.show]:
            order = f"{c['want']:g} {short(want)} : {c['give']:g} {short(give)}"
            simple = "yes" if 1 in (c["a"], c["b"]) else "no"
            print(f"  {c['a']:>4}:{c['b']:<4}  {c['price']:8.3f}  {c['price'] / comp - 1:+10.1%}  {order:>26}  {c['left']:5g}  {simple:>4}")
        print("  1:N? no = a slot competitors rarely use (93% of trades are 1:N), so it is less likely to be undercut")
        return
    if not a.ratio:
        ap.error("give a target ratio or --ahead-of")
    target = parse_ratio(a.ratio)
    gpu = gold_table(connect()).get(want)
    fee_note = "" if gpu is not None else " (fee unknown, default used)"
    gpu = gpu if gpu is not None else DEFAULT_GOLD_PER_UNIT

    rows = candidates(target, a.have, a.tol, a.max_lot, a.max_lot)
    print(f"target {short(give)} per {short(want)}: {target:g}   have {a.have:g} {short(give)}   "
          f"gold {gpu:g}/{short(want)}{fee_note}")
    print("  your price vs target: + = you give MORE per unit wanted (fills sooner), - = you give less (waits)")
    if not rows:
        print("  no small-lot ratio in the window; widen --tol or raise --max-lot")
        return
    print(f"  {'lot':>9}  {'per want':>8}  {'vs target':>9}  {'order (want : give)':>26}  {'left':>5}  {'gold':>7}")
    for c in rows[:a.show]:
        order = f"{c['want']:g} {short(want)} : {c['give']:g} {short(give)}"
        print(f"  {c['a']:>4}:{c['b']:<4}  {c['price']:8.3f}  {c['dev']:+8.1%}  {order:>26}  {c['left']:5g}  {c['want'] * gpu:7.0f}")


if __name__ == "__main__":
    main()
