"""Advice journal: every recommendation is stored with its data cut-off, then graded later
against newer snapshots. Over time this gives a hit-rate per strategy / item / condition,
which is how OrbFlow learns which advice is actually good.

    python -m orbflow.journal advise   # log current cross-pair leads
    python -m orbflow.journal grade    # grade old leads against the latest snapshot
    python -m orbflow.journal stats    # hit rate per strategy
"""
from __future__ import annotations

import argparse
import datetime as dt
import json

from .db import connect
from .scan import implied_prices


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def latest_sid(con, league):
    return con.execute("SELECT MAX(snapshot_id), MAX(fetched_at) FROM pair_snapshots WHERE league=?",
                       (league,)).fetchone()


def advise(con, league, min_gap=1.25, max_buy_ex=100, horizon_h=6, top=20):
    sid, as_of = latest_sid(con, league)
    _, imp = implied_prices(con, league, sid)
    recs = []
    for item, d in imp.items():
        if len(d) < 2:
            continue
        lo = min(d, key=lambda m: d[m]["ex"])
        hi = max(d, key=lambda m: d[m]["ex"])
        gap = d[hi]["ex"] / d[lo]["ex"]
        if gap >= min_gap and d[lo]["ex"] <= max_buy_ex:
            recs.append((gap, item, lo, hi, d))
    recs.sort(key=lambda r: -r[0])
    for gap, item, lo, hi, d in recs[:top]:
        con.execute("""INSERT INTO recommendations (created_at, as_of, league, strategy, api_id, action,
                       entry_price, target_price, horizon_h, score, rationale) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (_now(), as_of, league, "cross_pair", item, f"BUY_WITH_{lo}_SELL_FOR_{hi}",
                     d[lo]["ex"], d[hi]["ex"], horizon_h, gap,
                     json.dumps({"snapshot_id": sid, "legs": d})))
    con.commit()
    return len(recs[:top])


def grade(con, league):
    """A cross-pair lead is a 'hit' if, `horizon_h` later, the same direction still shows a gap
    big enough to profit after a 15% haircut (i.e. it was persistent, not a one-hour artifact)."""
    sid, now_ts = latest_sid(con, league)
    _, imp = implied_prices(con, league, sid)
    n = 0
    for r in con.execute("SELECT * FROM recommendations WHERE league=? AND evaluated_at IS NULL", (league,)).fetchall():
        made = dt.datetime.fromisoformat(r["as_of"].replace("Z", "+00:00"))
        now = dt.datetime.fromisoformat(now_ts.replace("Z", "+00:00"))
        if (now - made).total_seconds() < r["horizon_h"] * 3600:
            continue
        lo, hi = r["action"].replace("BUY_WITH_", "").split("_SELL_FOR_")
        d = imp.get(r["api_id"], {})
        if lo in d and hi in d:
            later_gap = d[hi]["ex"] / d[lo]["ex"]
            hit = int(later_gap > 1.15)
            realized = later_gap - 1
        else:
            later_gap, hit, realized = None, 0, 0.0
        con.execute("UPDATE recommendations SET evaluated_at=?, exit_price=?, realized_pct=?, hit=? WHERE id=?",
                    (now_ts, later_gap, realized, hit, r["id"]))
        n += 1
    con.commit()
    return n


def stats(con, league):
    for row in con.execute("""SELECT strategy, COUNT(*) n, AVG(hit) hit_rate, AVG(realized_pct) avg_ret
                              FROM recommendations WHERE league=? AND evaluated_at IS NOT NULL
                              GROUP BY strategy""", (league,)):
        print(dict(row))
    pending = con.execute("SELECT COUNT(*) FROM recommendations WHERE evaluated_at IS NULL").fetchone()[0]
    print("pending:", pending)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["advise", "grade", "stats"])
    ap.add_argument("--league", default="Forbidden Rites")
    a = ap.parse_args(argv)
    con = connect()
    if a.cmd == "advise":
        print("logged", advise(con, a.league))
    elif a.cmd == "grade":
        print("graded", grade(con, a.league))
    else:
        stats(con, a.league)


if __name__ == "__main__":
    main()
