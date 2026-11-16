"""Short, memorable, unique names for exchange items.

    python -m orbflow.names              # print the whole alias table (checks uniqueness)
    python -m orbflow.names rarity       # resolve a short name -> api id

Every CLI that takes an item accepts either the short name or the full api id.
Rules (applied in order), then hand-picked overrides win:
  omen-of-(the-)X         -> X               omen-of-chaotic-rarity     -> rarity
  sinistral- / dextral-   -> sin- / dex-     omen-of-dextral-erasure    -> dex-erasure
  X-catalyst              -> X-cat           refined-necrotic-catalyst  -> refined-necrotic-cat
  greater- / perfect- / lesser- -> g- / p- / l-
  orb-of-X / X-orb        -> X
  essence-of-X            -> ess-X
If a rule would create a duplicate, the full api id is kept for those items.
"""
from __future__ import annotations

import re
import sys

OVERRIDES = {
    "exalted": "ex",
    "divine": "div",
    "chaos": "chaos",
    "gcp": "gcp",
    "greater-exalted-orb": "gex",
    "perfect-exalted-orb": "pex",
    "greater-chaos-orb": "gchaos",
    "greater-regal-orb": "gregal",
    "greater-jewellers-orb": "gjew",
    "lesser-jewellers-orb": "ljew",
    "perfect-jewellers-orb": "pjew",
    "an-audience-with-the-king": "king",
    "call-of-the-shadows": "shadows",
    "vaal-armourers-infuser": "armour-infuser",
    "refined-necrotic-catalyst": "necro-cat",
    "omen-of-abyssal-echoes": "echoes",
    "omen-of-chaotic-rarity": "rarity",
    "omen-of-chaotic-quantity": "quantity",
    "omen-of-chaotic-monsters": "monsters",
    "omen-of-chaotic-effectiveness": "effectiveness",
    "twilight-reliquary-key": "twilight-key",
    "whetstone": "whet",
    "transmute": "trans",
    "fracturing-orb": "fracture",
    "architects-orb": "architect",
}

_RULES = [
    (r"^omen-of-(the-)?", ""),
    (r"sinistral-", "sin-"),
    (r"dextral-", "dex-"),
    (r"-catalyst$", "-cat"),
    (r"^greater-", "g-"),
    (r"^perfect-", "p-"),
    (r"^lesser-", "l-"),
    (r"^orb-of-", ""),
    (r"-orb$", ""),
    (r"(^|-)essence-of-(the-)?", lambda m: m.group(1) + "ess-"),
]


def _rule_alias(api_id: str) -> str:
    s = api_id
    for pat, rep in _RULES:
        s = re.sub(pat, rep, s)
    return s or api_id


def build(api_ids):
    """Returns {api_id: short} with guaranteed-unique shorts."""
    api_ids = set(api_ids) | set(OVERRIDES)
    cand = {a: OVERRIDES.get(a) or _rule_alias(a) for a in api_ids}
    counts = {}
    for v in cand.values():
        counts[v] = counts.get(v, 0) + 1
    # a short name must not collide with another short name or with another item's full id
    out = {}
    for a, v in cand.items():
        clash = counts[v] > 1 or (v in api_ids and v != a)
        out[a] = a if (clash and a not in OVERRIDES) else v
    return out


_cache = None


def _table():
    global _cache
    if _cache is None:
        try:
            from .db import connect
            ids = [r[0] for r in connect().execute("SELECT api_id FROM items")]
        except Exception:
            ids = []
        _cache = build(ids)
    return _cache


def short(api_id: str) -> str:
    return _table().get(api_id, api_id)


def resolve(name: str) -> str:
    """Short name or full id -> full api id (unknown names pass through)."""
    t = _table()
    if name in t:
        return name
    for a, s in t.items():
        if s == name:
            return a
    return name


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    t = _table()
    if argv:
        for n in argv:
            print(f"{n} -> {resolve(n)}")
        return
    shorts = list(t.values())
    assert len(shorts) == len(set(shorts)), "duplicate short names!"
    for a, s in sorted(t.items(), key=lambda kv: kv[1]):
        if a != s:
            print(f"{s:28s} {a}")
    print(f"\n{len(t)} items, {sum(1 for a, s in t.items() if a != s)} with a short name, all unique")


if __name__ == "__main__":
    main()
