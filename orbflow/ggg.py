"""GGG's official public Currency Exchange feed: hourly digests, no login.

    python -m orbflow.ggg                 # fetch every hour we are missing (default: last 48 h)
    python -m orbflow.ggg --hours 336     # backfill two weeks
    python -m orbflow.ggg --map           # (re)build metadata-path -> item name mapping
    python -m orbflow.ggg --show regal    # hourly low/high/volume of one item vs ex/chaos/div

Endpoint: https://web.poecdn.com/api/currency-exchange/poe2/<unix hour>
  -> {"next_change_id": <next hour>, "markets": [ {league, market_pair:[a,b], volume_traded{a,b},
      lowest_ratio{a,b}, highest_ratio{a,b}, lowest_stock{a,b}, highest_stock{a,b}} ]}
One call = every pair of every league for that hour (~1.4 MB). The newest hour shows up ~1-1.5 h late.
This is the same data poe2scout serves (its snapshot = one GGG hour, volumes match exactly), but here we
get the whole history plus the lowest/highest ratio inside each hour.

Items are identified by game metadata paths (Metadata/Items/Currency/CurrencyModValues = divine).
We learn the mapping to our api ids by matching volumes with the poe2scout snapshots we collected.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import time
from pathlib import Path

from .client import get_json
from .db import connect

MAP_CSV = Path(__file__).resolve().parent.parent / "data" / "meta_map.csv"   # committed: lets a fresh DB name items
URL = "https://web.poecdn.com/api/currency-exchange/poe2/{ts}"
LEAGUE = "Forbidden Rites"
SEED = {  # sure anchors; the rest is learned
    "Metadata/Items/Currency/CurrencyModValues": "divine",
    "Metadata/Items/Currency/CurrencyAddModToRare": "exalted",
    "Metadata/Items/Currency/CurrencyRerollRare": "chaos",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS cx_hours (
    league TEXT, ts INTEGER, a TEXT, b TEXT,
    a_vol INTEGER, b_vol INTEGER,
    a_low INTEGER, b_low INTEGER, a_high INTEGER, b_high INTEGER,
    a_low_stock INTEGER, b_low_stock INTEGER, a_high_stock INTEGER, b_high_stock INTEGER,
    PRIMARY KEY (league, ts, a, b)
);
CREATE TABLE IF NOT EXISTS cx_fetched (ts INTEGER PRIMARY KEY, n_markets INTEGER, fetched_at TEXT);
CREATE TABLE IF NOT EXISTS meta_map (meta TEXT PRIMARY KEY, api_id TEXT, votes INTEGER);
"""


def init(con):
    con.executescript(SCHEMA)


def fetch_hour(con, ts, league=LEAGUE):
    """Download one hour and store the league's markets. Returns number of markets, or None if not published yet."""
    try:
        d = get_json(URL.format(ts=ts), min_interval=1.0, retries=1)
    except Exception as e:
        if "404" in str(e):
            return None  # hour not published yet
        raise
    ms = d.get("markets") or []
    if not ms:
        return None
    rows = []
    for m in ms:
        if m["league"] != league:
            continue
        a, b = m["market_pair"]
        g = lambda k, x: (m.get(k) or {}).get(x)
        rows.append((league, ts, a, b, g("volume_traded", a), g("volume_traded", b),
                     g("lowest_ratio", a), g("lowest_ratio", b), g("highest_ratio", a), g("highest_ratio", b),
                     g("lowest_stock", a), g("lowest_stock", b), g("highest_stock", a), g("highest_stock", b)))
    con.executemany("INSERT OR REPLACE INTO cx_hours VALUES (" + ",".join("?" * 14) + ")", rows)
    con.execute("INSERT OR REPLACE INTO cx_fetched VALUES (?,?,?)",
                (ts, len(rows), dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))
    con.commit()
    return len(rows)


def sync(con, hours=48, league=LEAGUE, verbose=True):
    """Fetch every missing hour in the last `hours` hours (newest first, stops at unpublished hours)."""
    init(con)
    now_h = int(time.time()) // 3600 * 3600
    have = {r[0] for r in con.execute("SELECT ts FROM cx_fetched")}
    got = 0
    for ts in range(now_h, now_h - hours * 3600, -3600):
        if ts in have:
            continue
        n = fetch_hour(con, ts, league)
        if n is None:
            continue  # not published yet
        got += 1
        if verbose:
            print(f"  {dt.datetime.fromtimestamp(ts, dt.timezone.utc):%Y-%m-%d %H:%M}Z  {n} markets", flush=True)
    return got


def build_map(con, verbose=True):
    """Learn metadata path -> api id by matching pair volumes with poe2scout snapshots of the same hour."""
    init(con)
    votes = collections.defaultdict(collections.Counter)
    for meta, api in SEED.items():
        votes[meta][api] += 1000
    if MAP_CSV.exists():  # what earlier runs learned
        for row in csv.DictReader(open(MAP_CSV, encoding="utf-8")):
            votes[row["meta"]][row["api_id"]] += int(row["votes"])
    # find which GGG hour each scout snapshot is: the div/ex pair volumes are unique enough
    div, ex = "Metadata/Items/Currency/CurrencyModValues", "Metadata/Items/Currency/CurrencyAddModToRare"
    ggg_key = {}
    for r in con.execute("SELECT ts, a, a_vol, b_vol FROM cx_hours WHERE ? IN (a,b) AND ? IN (a,b)", (div, ex)):
        dv, xv = (r[2], r[3]) if r[1] == div else (r[3], r[2])
        ggg_key[(dv, xv)] = r[0]
    snap_ts = {}
    for r in con.execute("""SELECT snapshot_id, one_api, one_volume, two_volume FROM pair_snapshots
                            WHERE one_api IN ('divine','exalted') AND two_api IN ('divine','exalted')"""):
        dv, xv = (r[2], r[3]) if r[1] == "divine" else (r[3], r[2])
        if (dv, xv) in ggg_key:
            snap_ts[r[0]] = ggg_key[(dv, xv)]
    for sid, ts in snap_ts.items():
        scout = collections.defaultdict(list)
        for r in con.execute("SELECT one_api, two_api, one_volume, two_volume FROM pair_snapshots WHERE snapshot_id=?", (sid,)):
            scout[tuple(sorted((r[2] or 0, r[3] or 0)))].append(r)
        for r in con.execute("SELECT a, b, a_vol, b_vol FROM cx_hours WHERE ts=?", (ts,)):
            a, b, av, bv = r
            cands = scout.get(tuple(sorted((av or 0, bv or 0))), [])
            if len(cands) != 1 or av == bv:
                continue
            s = cands[0]
            (sa, sb) = (s[0], s[1]) if s[2] == av else (s[1], s[0])
            votes[a][sa] += 1
            votes[b][sb] += 1
    con.execute("DELETE FROM meta_map")
    n = 0
    for meta, c in votes.items():
        api, v = c.most_common(1)[0]
        if v >= 2 and v >= 0.8 * sum(c.values()):
            con.execute("INSERT INTO meta_map VALUES (?,?,?)", (meta, api, v))
            n += 1
    con.commit()
    with open(MAP_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["meta", "api_id", "votes"])
        w.writerows(sorted(tuple(r) for r in con.execute("SELECT meta, api_id, MIN(votes, 1000) FROM meta_map")))
    total = con.execute("SELECT COUNT(DISTINCT a) FROM cx_hours").fetchone()[0]
    if verbose:
        print(f"matched {len(snap_ts)} scout snapshots to GGG hours; mapped {n} metadata ids (of ~{total})")
    return n


def meta_map(con):
    init(con)
    if not con.execute("SELECT 1 FROM meta_map LIMIT 1").fetchone() and MAP_CSV.exists():
        rows = [(r["meta"], r["api_id"], int(r["votes"])) for r in csv.DictReader(open(MAP_CSV, encoding="utf-8"))]
        con.executemany("INSERT OR REPLACE INTO meta_map VALUES (?,?,?)", rows)
        con.commit()
    return dict(con.execute("SELECT meta, api_id FROM meta_map"))


def pair_rows(con, league=LEAGUE, last_n=24):
    """GGG hours in the same shape as pair_snapshots rows (dicts), mapped to api ids.
    Adds low/high ratios: one_low/two_low (units of each side in the lowest-ratio trade) etc."""
    init(con)
    mp = meta_map(con)
    hours = [r[0] for r in con.execute(
        "SELECT DISTINCT ts FROM cx_hours WHERE league=? ORDER BY ts DESC LIMIT ?", (league, last_n))]
    out = []
    if not hours:
        return out
    marks = ",".join("?" * len(hours))
    for r in con.execute(f"SELECT * FROM cx_hours WHERE league=? AND ts IN ({marks})", (league, *hours)):
        a, b = mp.get(r[2]), mp.get(r[3])
        if not a or not b:
            continue
        out.append({"snapshot_id": r[1], "one_api": a, "two_api": b, "one_volume": r[4], "two_volume": r[5],
                    "one_low": r[6], "two_low": r[7], "one_high": r[8], "two_high": r[9],
                    "one_highest_stock": r[12], "two_highest_stock": r[13]})
    return out


def show(con, item, league=LEAGUE, last_n=24):
    from .names import resolve, short
    item = resolve(item)
    rows = [r for r in pair_rows(con, league, last_n) if item in (r["one_api"], r["two_api"])
            and ({r["one_api"], r["two_api"]} & {"exalted", "chaos", "divine"})]
    print(f"{short(item)} = {item}   (money per item; low/high = cheapest/dearest trade that hour)")
    for r in sorted(rows, key=lambda r: (r["one_api"] if r["two_api"] == item else r["two_api"], r["snapshot_id"])):
        if r["one_api"] == item:
            money, iv, mv, il, ml, ih, mh = r["two_api"], r["one_volume"], r["two_volume"], r["one_low"], r["two_low"], r["one_high"], r["two_high"]
        else:
            money, iv, mv, il, ml, ih, mh = r["one_api"], r["two_volume"], r["one_volume"], r["two_low"], r["one_low"], r["two_high"], r["one_high"]
        p = lambda m, i: (m / i) if (m and i) else float("nan")
        lo, hi = sorted((p(ml, il), p(mh, ih)))
        print(f"  {short(money):6s} {dt.datetime.fromtimestamp(r['snapshot_id'], dt.timezone.utc):%m-%d %H}h "
              f"units {iv:6} avg {p(mv, iv):9.3f}  low {lo:9.3f}  high {hi:9.3f}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=48)
    ap.add_argument("--map", action="store_true")
    ap.add_argument("--show")
    ap.add_argument("--league", default=LEAGUE)
    a = ap.parse_args(argv)
    con = connect()
    init(con)
    if a.show:
        show(con, a.show, a.league, a.hours)
        return
    if not a.map:
        n = sync(con, a.hours, a.league)
        print(f"fetched {n} new hours")
    build_map(con)


if __name__ == "__main__":
    main()
