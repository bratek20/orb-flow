"""Data collection: snapshot of all exchange pairs + hourly price history backfill."""
from __future__ import annotations

import datetime as dt

from .client import Scout
from .db import connect


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def collect_pairs(scout: Scout, con) -> list[dict]:
    pairs = scout.snapshot_pairs()
    fetched = _now()
    rows, items = [], {}
    for p in pairs:
        a, b = p["CurrencyOne"], p["CurrencyTwo"]
        for c in (a, b):
            items[c["ItemId"]] = (c["ItemId"], c["ApiId"], c["Text"], c.get("CategoryApiId"))
        ad, bd = p["CurrencyOneData"], p["CurrencyTwoData"]
        rows.append((scout.league, p["CurrencyExchangeSnapshotId"], fetched, a["ApiId"], b["ApiId"], p["Volume"],
                     ad["RelativePrice"], ad["ValueTraded"], ad["VolumeTraded"], ad["StockValue"], ad["HighestStock"],
                     bd["RelativePrice"], bd["ValueTraded"], bd["VolumeTraded"], bd["StockValue"], bd["HighestStock"]))
    con.executemany("INSERT OR IGNORE INTO items VALUES (?,?,?,?)", items.values())
    con.executemany("INSERT OR IGNORE INTO pair_snapshots VALUES (" + ",".join("?" * 16) + ")", rows)
    con.commit()
    return pairs


def backfill_history(scout: Scout, con, item_ids, hours=168, verbose=True):
    """Pull last `hours` of hourly prices (in ex) for each item."""
    n = 0
    for i, iid in enumerate(item_ids):
        try:
            h = scout.item_history(iid, log_count=hours)
        except Exception as e:  # keep going, some items have no history
            if verbose:
                print(f"  ! item {iid}: {e}")
            continue
        rows = [(scout.league, iid, r["Time"][:13] + ":00:00Z", r["Price"], r["Quantity"])
                for r in h.get("PriceHistory", []) if r.get("Price")]
        con.executemany("INSERT OR REPLACE INTO price_history VALUES (?,?,?,?,?)", rows)
        n += len(rows)
        if verbose and i % 20 == 0:
            print(f"  {i+1}/{len(item_ids)} items, {n} rows")
        con.commit()
    return n


def liquid_item_ids(con, league, min_volume_ex=2000, top=None):
    """Items whose summed pair volume in the latest snapshot exceeds a threshold."""
    sid = con.execute("SELECT MAX(snapshot_id) FROM pair_snapshots WHERE league=?", (league,)).fetchone()[0]
    sql = """
      SELECT i.item_id, i.api_id, SUM(v) vol FROM (
        SELECT one_api api, one_value_traded v FROM pair_snapshots WHERE league=? AND snapshot_id=?
        UNION ALL
        SELECT two_api, two_value_traded FROM pair_snapshots WHERE league=? AND snapshot_id=?
      ) JOIN items i ON i.api_id = api GROUP BY i.item_id HAVING vol >= ? ORDER BY vol DESC"""
    rows = con.execute(sql, (league, sid, league, sid, min_volume_ex)).fetchall()
    return [r["item_id"] for r in rows[:top] if True] if top else [r["item_id"] for r in rows]


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Collect PoE2 exchange data")
    ap.add_argument("--league")
    ap.add_argument("--backfill-hours", type=int, default=0, help="also pull N hours of item history")
    ap.add_argument("--min-volume", type=float, default=2000, help="min ex traded/hour to backfill an item")
    a = ap.parse_args(argv)
    scout = Scout(a.league)
    con = connect()
    pairs = collect_pairs(scout, con)
    print(f"[{scout.league}] stored {len(pairs)} pairs")
    if a.backfill_hours:
        ids = liquid_item_ids(con, scout.league, a.min_volume)
        print(f"backfilling {len(ids)} liquid items x {a.backfill_hours}h")
        print("rows:", backfill_history(scout, con, ids, a.backfill_hours))


if __name__ == "__main__":
    main()
