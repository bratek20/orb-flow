"""Order sizing: pick a ratio that splits into small lots so partial fills can happen.

A partial fill must be whole units on BOTH sides at your exact ratio, so the smallest piece anyone can take
is the ratio reduced to lowest terms (lot). "23 div : 190 monsters" cannot be reduced -> all or nothing.
"22 div : 187 monsters" = 11 x (2:17) -> fills in pieces of 17 monsters.

Ratios are written like the player reports them: want : give.
    python -m orbflow.ratio div monsters 1:8.3 --have 190          # selling 190 monsters near 8.3 per div
    python -m orbflow.ratio monsters chaos 2:1 --have 100          # buying monsters with 100 chaos near 2 per chaos
    python -m orbflow.ratio div monsters 1:8 --have 190 --tol 0.08 --max-lot 30
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
    ap.add_argument("ratio", help="target want:give, e.g. 1:8.3")
    ap.add_argument("--have", type=float, required=True, help="units of the give item you put in")
    ap.add_argument("--tol", type=float, default=0.05)
    ap.add_argument("--max-lot", type=int, default=40)
    ap.add_argument("--show", type=int, default=12)
    a = ap.parse_args(argv)

    want, give = resolve(a.want), resolve(a.give)
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
