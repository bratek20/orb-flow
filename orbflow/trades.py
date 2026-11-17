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


CSV_PATH = __import__("pathlib").Path(__file__).resolve().parent.parent / "data" / "trades.csv"
COLS = ["id", "placed_at", "filled_at", "status", "want", "want_qty", "give", "give_qty", "gold", "note"]


def import_csv(con, replace=False):
    """Load data/trades.csv into the trades table (only if empty, unless replace)."""
    import csv
    con.executescript(SCHEMA)
    if not CSV_PATH.exists():
        return 0
    if con.execute("SELECT COUNT(*) FROM trades").fetchone()[0] and not replace:
        return 0
    rows = [[(r[c] if r[c] != "" else None) for c in COLS] for r in csv.DictReader(open(CSV_PATH, encoding="utf-8"))]
    con.execute("DELETE FROM trades")
    con.executemany(f"INSERT INTO trades VALUES ({','.join('?' * len(COLS))})", rows)
    con.commit()
    return len(rows)


def export_csv(con):
    import csv
    cur = con.execute("SELECT * FROM trades ORDER BY id")
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([d[0] for d in cur.description])
        w.writerows(cur)


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
    a_gold = sub.add_parser("gold", help="set gold cost of an existing trade")
    a_gold.add_argument("id", type=int)
    a_gold.add_argument("gold", type=int)
    for c in ("fill", "cancel"):
        p = sub.add_parser(c)
        p.add_argument("id", type=int)
        p.add_argument("--at", default=None)
    sub.add_parser("list")
    sub.add_parser("calib")
    sub.add_parser("import", help="replace the trades table with data/trades.csv")
    a = ap.parse_args(argv)
    con = connect()
    con.executescript(SCHEMA)
    if a.cmd == "add":
        from .names import resolve
        a.want, a.give = resolve(a.want), resolve(a.give)
        cur = con.execute("INSERT INTO trades (placed_at, want, want_qty, give, give_qty, gold, note) VALUES (?,?,?,?,?,?,?)",
                          (a.at or _now(), a.want, a.want_qty, a.give, a.give_qty, a.gold, a.note))
        print("trade id", cur.lastrowid)
    elif a.cmd in ("fill", "cancel"):
        con.execute("UPDATE trades SET status=?, filled_at=? WHERE id=?",
                    ("filled" if a.cmd == "fill" else "cancelled", a.at or _now(), a.id))
    elif a.cmd == "gold":
        con.execute("UPDATE trades SET gold=? WHERE id=?", (a.gold, a.id))
    elif a.cmd == "import":
        print("imported", import_csv(con, replace=True), "trades")
    elif a.cmd == "list":
        for r in con.execute("SELECT * FROM trades ORDER BY id"):
            print(dict(r))
    elif a.cmd == "calib":
        for r in con.execute("SELECT * FROM trades WHERE status='filled'"):
            mins = (dt.datetime.fromisoformat(r["filled_at"]) - dt.datetime.fromisoformat(r["placed_at"])).total_seconds() / 60
            print(f"#{r['id']} want {r['want_qty']:g} {r['want']} for {r['give_qty']:g} {r['give']}: filled in {mins:.0f} min")
        from .chains import gold_table
        print("gold per unit WANTED:", gold_table(con))
        for r in con.execute("SELECT * FROM trades WHERE gold IS NOT NULL"):
            print(f"  #{r['id']} want {r['want_qty']:g} {r['want']} (give {r['give_qty']:g} {r['give']}): "
                  f"{r['gold']} gold = {r['gold'] / r['want_qty']:.0f}/unit")
    con.commit()
    if a.cmd in ("add", "fill", "cancel", "gold"):
        export_csv(con)   # keep the committed CSV in sync


if __name__ == "__main__":
    main()
