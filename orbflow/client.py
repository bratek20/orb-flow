"""Thin HTTP clients for public PoE2 economy APIs (poe2scout, poe.ninja). Stdlib only."""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

UA = "orb-flow/0.1 (personal market research tool)"
SCOUT = "https://api.poe2scout.com/poe2"
NINJA = "https://poe.ninja/poe2/api"

_last_call = 0.0


def get_json(url: str, min_interval: float = 1.0, retries: int = 3):
    """GET JSON with polite rate limiting and simple retry."""
    global _last_call
    for attempt in range(retries):
        wait = min_interval - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(3 * (attempt + 1))


def q(league: str) -> str:
    return urllib.parse.quote(league)


class Scout:
    def __init__(self, league: str | None = None):
        self.league = league or self.current_league()

    @staticmethod
    def leagues():
        return get_json(f"{SCOUT}/Leagues")

    @classmethod
    def current_league(cls) -> str:
        for lg in cls.leagues():
            if lg.get("IsCurrent"):
                return lg["Value"]
        raise RuntimeError("no current league")

    def base(self) -> str:
        return f"{SCOUT}/Leagues/{q(self.league)}"

    def snapshot_pairs(self):
        """All exchange pairs from the latest hourly snapshot (GGG cxapi-derived)."""
        return get_json(f"{self.base()}/SnapshotPairs")

    def snapshot_history(self, limit=24, end_epoch=None):
        url = f"{self.base()}/SnapshotHistory?limit={limit}"
        if end_epoch:
            url += f"&endEpoch={end_epoch}"
        return get_json(url)

    def item_history(self, item_id: int, log_count=168, end_time: str | None = None, ref="exalted"):
        """Hourly price (in `ref`) + quantity log for one item. Newest first."""
        url = f"{self.base()}/Items/{item_id}/History?logCount={log_count}&referenceCurrency={ref}"
        if end_time:
            url += f"&endTime={urllib.parse.quote(end_time)}"
        return get_json(url)


class Ninja:
    def __init__(self, league: str):
        self.league = league

    def overview(self, type_: str = "Currency"):
        return get_json(f"{NINJA}/economy/exchange/current/overview?league={q(self.league)}&type={type_}")


NINJA_TYPES = ["Currency", "Fragments", "Essences", "Ritual", "Delirium", "Breach", "Abyss", "UncutGems",
               "Expedition", "Runes", "SoulCores", "Idols", "LineageSupportGems", "Ultimatum"]


def ninja_prices(league: str) -> dict:
    """{api_id: (price_ex, main_market_currency, volume)} across poe.ninja exchange categories."""
    out = {}
    nj = Ninja(league)
    for t in NINJA_TYPES:
        try:
            d = nj.overview(t)
        except Exception:
            continue
        rate = d.get("core", {}).get("rates", {}).get("exalted")
        if not rate:
            continue
        for l in d.get("lines", []):
            out[l["id"]] = (l["primaryValue"] * rate, l.get("maxVolumeCurrency"), l.get("volumePrimaryValue"))
    return out
