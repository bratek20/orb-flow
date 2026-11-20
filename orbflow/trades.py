"""Log of real in-game orders. This is ground truth for fill times and prices.

    python -m orbflow.trades add regal exalted 245 100 --side buy --gold 0 --note "bid 2.45"
        (I want 245 regal, paying 100 exalted)
    python -m orbflow.trades fill 3 [--at 2026-11-15T10:40]
    python -m orbflow.trades cancel 3
    python -m orbflow.trades list
    python -m orbflow.trades calib     # fill speed vs. API volume -> FILL_SHARE estimate
    python -m orbflow.trades inbox [--apply]   # reports sent from the board page (GitHub issues, label "trade")
"""
from __future__ import annotations

import argparse
import datetime as dt
import math

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


# ---- inbox: trade reports sent from the board page as GitHub issues (label "trade") ----
REPO = "bratek20/orb-flow"


def _gh(*args):
    import subprocess
    return subprocess.run(["gh", *args, "-R", REPO], capture_output=True, text=True, encoding="utf-8", check=True).stdout


def parse_report(body):
    """'key: value' lines of an orbflow-report issue -> dict (None if it isn't one)."""
    if "orbflow-report" not in (body or ""):
        return None
    d = {}
    for line in body.splitlines():
        if ":" in line and not line.startswith("<!--"):
            k, v = line.split(":", 1)
            d[k.strip().lower()] = v.strip()
    return d


def _qty_item(s):
    q, _, item = s.strip().partition(" ")
    return float(q), item.strip()


def apply_report(con, d, issue_no):
    """Apply one parsed report to the trades table. Returns a short description of what happened."""
    from .names import resolve
    k, at, note = d.get("kind"), d.get("at") or _now(), d.get("note", "")
    tag = f"[gh#{issue_no}]"
    ref = int(d["ref"]) if d.get("ref") else None
    if ref is not None and not con.execute("SELECT 1 FROM trades WHERE id=?", (ref,)).fetchone():
        raise ValueError(f"order #{ref} does not exist")

    def add_note(text):
        con.execute("UPDATE trades SET note = TRIM(COALESCE(note,'') || ' | ' || ?, ' |') WHERE id=?", (text, ref))

    if k == "new":
        wq, w = _qty_item(d["want"])
        gq, g = _qty_item(d["give"])
        gold = int(float(d["gold"])) if d.get("gold") else None
        cur = con.execute("INSERT INTO trades (placed_at, want, want_qty, give, give_qty, gold, note) VALUES (?,?,?,?,?,?,?)",
                          (at, resolve(w), wq, resolve(g), gq, gold, f"{note} {tag}".strip()))
        return f"logged as #{cur.lastrowid}"
    if k in ("filled", "cancel"):
        con.execute("UPDATE trades SET status=?, filled_at=? WHERE id=?", ("filled" if k == "filled" else "cancelled", at, ref))
        add_note(f"{at[11:16]} {k} {tag} {note}".strip())
        return f"#{ref} marked {'filled' if k == 'filled' else 'cancelled'}"
    if k == "partial":
        paid = f" for {d['paid']}" if d.get("paid") else ""
        con.execute("UPDATE trades SET status='partial' WHERE id=?", (ref,))
        add_note(f"{at[11:16]} got {d.get('got')}{paid} {tag} {note}".strip())
        return f"#{ref} partial: got {d.get('got')}{paid}"
    if k == "note":
        if ref is None:
            raise ValueError("free note without an order; read it and act by hand")
        add_note(f"{at[11:16]} {note} {tag}")
        return f"note added to #{ref}"
    raise ValueError(f"unknown kind {k!r}")


def inbox(con, apply=False):
    import json
    issues = json.loads(_gh("issue", "list", "--label", "trade", "--state", "open", "--limit", "100",
                            "--json", "number,title,body,createdAt"))
    if not issues:
        print("inbox empty")
        return
    for i in sorted(issues, key=lambda x: x["number"]):
        d = parse_report(i["body"])
        print(f"gh#{i['number']} {i['createdAt']}  {i['title']}")
        if d is None:
            print("    not a form report; read it and handle by hand:\n    " + (i["body"] or "").replace("\n", "\n    "))
            continue
        if not apply:
            print("    " + ", ".join(f"{k}={v}" for k, v in d.items() if v))
            continue
        try:
            msg = apply_report(con, d, i["number"])
        except Exception as e:  # leave the issue open for a human look
            print(f"    NOT applied: {e}")
            continue
        con.commit()
        export_csv(con)
        _gh("issue", "close", str(i["number"]), "--comment", f"Logged by orbflow: {msg}")
        print(f"    applied: {msg} (issue closed)")


def _min_lot(want_qty, give_qty):
    """Smallest whole-unit piece of an order (want, give), or None for fractional quantities."""
    if want_qty != int(want_qty) or give_qty != int(give_qty) or want_qty <= 0 or give_qty <= 0:
        return None
    g = math.gcd(int(want_qty), int(give_qty))
    return want_qty / g, give_qty / g


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
    a_in = sub.add_parser("inbox", help="trade reports sent from the board (GitHub issues with label 'trade')")
    a_in.add_argument("--apply", action="store_true", help="log them in the trades table and close the issues")
    a = ap.parse_args(argv)
    con = connect()
    con.executescript(SCHEMA)
    if a.cmd == "add":
        from .names import resolve
        a.want, a.give = resolve(a.want), resolve(a.give)
        cur = con.execute("INSERT INTO trades (placed_at, want, want_qty, give, give_qty, gold, note) VALUES (?,?,?,?,?,?,?)",
                          (a.at or _now(), a.want, a.want_qty, a.give, a.give_qty, a.gold, a.note))
        print("trade id", cur.lastrowid)
        lot = _min_lot(a.want_qty, a.give_qty)
        if lot and lot[1] > 40 and lot[1] >= a.give_qty / 2:
            print(f"  warning: smallest partial fill is {lot[0]:g} : {lot[1]:g} (ratio does not split); "
                  f"next time pick one with `python -m orbflow.ratio`")
    elif a.cmd in ("fill", "cancel"):
        con.execute("UPDATE trades SET status=?, filled_at=? WHERE id=?",
                    ("filled" if a.cmd == "fill" else "cancelled", a.at or _now(), a.id))
    elif a.cmd == "gold":
        con.execute("UPDATE trades SET gold=? WHERE id=?", (a.gold, a.id))
    elif a.cmd == "inbox":
        inbox(con, apply=a.apply)
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
