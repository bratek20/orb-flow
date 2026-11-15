"""Log of real in-game orders. This is ground truth for fill times and prices.

    python -m orbflow.trades add regal exalted 245 100 --side buy --gold 0 --note "bid 2.45"
        (I want 245 regal, paying 100 exalted)
    python -m orbflow.trades fill 3 [--at 2026-11-15T10:40]
    python -m orbflow.trades cancel 3
    python -m orbflow.trades list
    python -m orbflow.trades calib     # fill speed vs. API volume -> FILL_SHARE estimate
"""
from __future__ import annotations

import argparse
import datetime as dt

from .db import connect

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    placed_at TEXT, filled_at TEXT, status TEXT DEFAULT 'open',   -- open/filled/partial/cancelled
    want TEXT, want_qty REAL, give TEXT, give_qty REAL,
    gold INTEGER, note TEXT
);
"""


def _now():
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M")


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a_add = sub.add_parser("add")
    a_add.add_argument("want")
    a_add.add_argument("give")
    a_add.add_argument("want_qty", type=float)
    a_add.add_argument("give_qty", type=float)
    a_add.add_argument("--at", default=None)
    a_add.add_argument("--gold", type=int, default=None)
    a_add.add_argument("--note", default="")
    for c in ("fill", "cancel"):
        p = sub.add_parser(c)
        p.add_argument("id", type=int)
        p.add_argument("--at", default=None)
    sub.add_parser("list")
    sub.add_parser("calib")
    a = ap.parse_args(argv)
    con = connect()
    con.executescript(SCHEMA)
    if a.cmd == "add":
        cur = con.execute("INSERT INTO trades (placed_at, want, want_qty, give, give_qty, gold, note) VALUES (?,?,?,?,?,?,?)",
                          (a.at or _now(), a.want, a.want_qty, a.give, a.give_qty, a.gold, a.note))
        print("trade id", cur.lastrowid)
    elif a.cmd in ("fill", "cancel"):
        con.execute("UPDATE trades SET status=?, filled_at=? WHERE id=?",
                    ("filled" if a.cmd == "fill" else "cancelled", a.at or _now(), a.id))
    elif a.cmd == "list":
        for r in con.execute("SELECT * FROM trades ORDER BY id"):
            print(dict(r))
    elif a.cmd == "calib":
        for r in con.execute("SELECT * FROM trades WHERE status='filled'"):
            mins = (dt.datetime.fromisoformat(r["filled_at"]) - dt.datetime.fromisoformat(r["placed_at"])).total_seconds() / 60
            print(f"#{r['id']} want {r['want_qty']:g} {r['want']} for {r['give_qty']:g} {r['give']}: filled in {mins:.0f} min")
    con.commit()


if __name__ == "__main__":
    main()
