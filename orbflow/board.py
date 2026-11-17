"""Trade board: robust round finder + a self-refreshing HTML page. Works without Claude.

    python -m orbflow.board                 # build reports/board.html from the data we have
    python -m orbflow.board --collect       # download a fresh snapshot first
    python -m orbflow.board --serve         # collect + rebuild every hour, serve on http://<pc-ip>:8765
                                            #   (open that address on your phone on the same Wi-Fi)

Why it is more accurate than `cycles --scan`:
  * Prices are checked PER SNAPSHOT, not as one blended average. A route is only shown when the
    sell/buy gap is there in most hours (`stable` = share of hours with gap >= --min-gap).
    The armour-infuser lesson: one cheap hour (6 chaos) looked like the market, normal was 12-16.
  * Each hour is priced with that hour's own chaos/div rates.
  * Gold on every leg, from the real fees we logged (trades table), ranked by gold per div of profit.
  * Trades the player logged with `orbflow.trades` show up as "proven".
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import html
import http.server
import socket
import statistics as st
import threading
import time
from pathlib import Path

from .chains import DEFAULT_GOLD_PER_UNIT, FILL_SHARE, MONEY, gold_table
from .db import connect
from .names import short

OUT = Path(__file__).resolve().parent.parent / "reports" / "board.html"
HAIRCUT = 0.10  # per item leg


def snapshot_prices(con, league, last_n):
    """-> (prices, rates, units, sids)
    prices[item][money][sid] = price of 1 item in div, in that market, that hour
    units[item][money][sid]  = item units traded that hour
    rates[sid] = {money: ex per unit}"""
    from .ggg import pair_rows
    rows = pair_rows(con, league, last_n)          # GGG hourly digests (preferred: more hours, low/high)
    if not rows:                                   # fallback: poe2scout snapshots
        sids = [r[0] for r in con.execute(
            "SELECT DISTINCT snapshot_id FROM pair_snapshots WHERE league=? ORDER BY snapshot_id DESC LIMIT ?",
            (league, last_n))]
        marks = ",".join("?" * len(sids))
        rows = [dict(r) for r in con.execute(
            f"SELECT * FROM pair_snapshots WHERE league=? AND snapshot_id IN ({marks})", (league, *sids))]
    sids = sorted({r["snapshot_id"] for r in rows})
    if not sids:
        return {}, {}, {}, [], {}
    rates = collections.defaultdict(lambda: {"exalted": 1.0})
    for r in rows:
        for m in ("chaos", "divine"):
            if {r["one_api"], r["two_api"]} == {"exalted", m} and r["one_volume"] and r["two_volume"]:
                ex_u, m_u = ((r["one_volume"], r["two_volume"]) if r["one_api"] == "exalted"
                             else (r["two_volume"], r["one_volume"]))
                rates[r["snapshot_id"]][m] = ex_u / m_u
    prices = collections.defaultdict(lambda: collections.defaultdict(dict))
    units = collections.defaultdict(lambda: collections.defaultdict(dict))
    rng = collections.defaultdict(lambda: collections.defaultdict(dict))   # (low, high) price in div
    for r in rows:
        sr = rates[r["snapshot_id"]]
        if "divine" not in sr:
            continue
        for item, iu, money, mu in ((r["one_api"], r["one_volume"], r["two_api"], r["two_volume"]),
                                    (r["two_api"], r["two_volume"], r["one_api"], r["one_volume"])):
            if money in MONEY and item not in MONEY and money in sr and iu and mu:
                prices[item][money][r["snapshot_id"]] = mu * sr[money] / sr["divine"] / iu
                units[item][money][r["snapshot_id"]] = iu
                k1, k2 = ("one", "two") if item == r["one_api"] else ("two", "one")
                lo_i, lo_m, hi_i, hi_m = (r.get(f"{k1}_low"), r.get(f"{k2}_low"), r.get(f"{k1}_high"), r.get(f"{k2}_high"))
                if lo_i and lo_m and hi_i and hi_m:
                    f = sr[money] / sr["divine"]
                    rng[item][money][r["snapshot_id"]] = tuple(sorted((lo_m / lo_i * f, hi_m / hi_i * f)))
    return prices, rates, units, sids, rng


def find_rounds(con, league, last_n=12, min_gap=1.3, min_units_h=10, min_stable=0.6):
    prices, rates, units, sids, rng = snapshot_prices(con, league, last_n)
    if not sids:
        return [], {}, sids
    gtbl = gold_table(con)
    latest = rates[sids[-1]]
    div_ex = latest.get("divine", 1)
    # money conversion rates in div (median over hours)
    mdiv = {m: st.median([rates[s][m] / rates[s]["divine"] for s in sids if m in rates[s] and "divine" in rates[s]])
            for m in MONEY}
    proven = set()
    try:
        for r in con.execute("SELECT want, give FROM trades WHERE status IN ('filled','partial')"):
            proven.add(r["want"]); proven.add(r["give"])
    except Exception:
        pass
    out = []
    for item, mk in prices.items():
        for fund in mk:
            for sell in mk:
                if fund == sell:
                    continue
                common = [s for s in sids if s in mk[fund] and s in mk[sell]]
                if len(common) < max(2, len(sids) // 3):
                    continue
                gaps = [mk[sell][s] / mk[fund][s] for s in common]
                stable = sum(g >= min_gap for g in gaps) / len(sids)   # missing hour counts as "no"
                if stable < min_stable:
                    continue
                u_f = st.median([units[item][fund].get(s, 0) for s in sids])
                u_s = st.median([units[item][sell].get(s, 0) for s in sids])
                if min(u_f, u_s) < min_units_h:
                    continue
                buy = st.median(mk[fund][s] for s in common)     # div per item
                sel = st.median(mk[sell][s] for s in common)
                # round, 1 div in: div -> fund -> item -> sell -> div
                legs, q = [], 1.0
                if fund != "divine":
                    q2 = q / mdiv[fund]; legs.append(("divine", fund, q2)); q = q2
                q2 = q * mdiv[fund] / buy * (1 - HAIRCUT); legs.append((fund, item, q2)); n_items = q2; q = q2
                q2 = q * sel / mdiv[sell] * (1 - HAIRCUT); legs.append((item, sell, q2)); q = q2
                if sell != "divine":
                    q2 = q * mdiv[sell]; legs.append((sell, "divine", q2)); q = q2
                profit = q - 1
                if profit <= 0:
                    continue
                gold = sum(n * gtbl.get(w, DEFAULT_GOLD_PER_UNIT) for _, w, n in legs)
                gold_first = legs[0][2] * gtbl.get(fund, DEFAULT_GOLD_PER_UNIT) if fund != "divine" else 0.0
                hours = n_items / (FILL_SHARE * u_f) + n_items / (FILL_SHARE * u_s)
                out.append({
                    "item": item, "fund": fund, "sell": sell, "profit_div": profit, "gold": gold,
                    "gold_per_div": gold / profit, "hours": hours, "stable": stable,
                    "gap_med": st.median(gaps), "gap_min": min(gaps), "gap_last": gaps[-1] if common[-1] == sids[-1] else None,
                    "buy_ex": buy * div_ex, "sell_ex": sel * div_ex,
                    "buy_unit": buy / mdiv[fund], "sell_per": mdiv[sell] / sel,
                    "units_f": u_f, "units_s": u_s, "gold_known": item in gtbl, "proven": item in proven,
                    "hours_seen": len(common), "n_items": n_items, "gold_first": gold_first,
                    "hist": {k: [(round(m[x], 6) if x in m else None) for x in sids] for k, m in (("buy", mk[fund]), ("sell", mk[sell]))}
                            | {k: [(round(rng[item][mm][x][i], 6) if x in rng[item][mm] else None) for x in sids]
                               for k, mm, i in (("buy_lo", fund, 0), ("buy_hi", fund, 1), ("sell_lo", sell, 0), ("sell_hi", sell, 1))},
                    # typical cheapest buy / dearest sell seen inside an hour (maker prices), in money units
                    "buy_low": (st.median([rng[item][fund][x][0] for x in common if x in rng[item][fund]]) / mdiv[fund])
                               if any(x in rng[item][fund] for x in common) else None,
                    "sell_high": (st.median([rng[item][sell][x][1] for x in common if x in rng[item][sell]]) / mdiv[sell])
                                 if any(x in rng[item][sell] for x in common) else None,
                })
    out.sort(key=lambda r: r["gold_per_div"])
    return out, {"hours": sids, "min_gap": min_gap, "fill_share": FILL_SHARE, "div_ex": div_ex, "chaos_per_div": 1 / mdiv["chaos"], "ex_per_div": 1 / mdiv["exalted"],
                 "snaps": len(sids), "last": sids[-1]}, sids


MONEY_SHORT = {"exalted": "ex", "chaos": "chaos", "divine": "div"}


TEMPLATE = Path(__file__).resolve().parent / "board_template.html"


def render(rows, info, league, refresh_s):
    import json
    last = info.get("last", "-")
    if isinstance(last, int) and last > 1_000_000_000:   # GGG hour = unix time
        last = dt.datetime.fromtimestamp(last, dt.timezone.utc).strftime("%Y-%m-%d %H:00 UTC")
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    meta = (f"Built {now} · data hour {html.escape(str(last))} · {info.get('snaps', 0)} hours of data · "
            f"1 div = {info.get('div_ex', 0):.0f} ex = {info.get('chaos_per_div', 0):.1f} chaos · page refreshes every {refresh_s // 60} min")
    keys = ["item", "fund", "sell", "profit_div", "gold", "gold_per_div", "hours", "stable", "gap_med", "gap_min", "gap_last",
            "buy_ex", "sell_ex", "buy_unit", "sell_per", "units_f", "units_s", "gold_known", "proven", "n_items", "gold_first",
            "buy_low", "sell_high", "hist"]
    data = {"rows": [{**{k: r.get(k) for k in keys}, "short": short(r["item"])} for r in rows],
            "info": {k: info.get(k) for k in ("hours", "min_gap", "fill_share", "div_ex", "chaos_per_div", "ex_per_div")}}
    js = json.dumps(data, separators=(",", ":"), default=float).replace("</", "<\\/")
    return (TEMPLATE.read_text(encoding="utf-8")
            .replace("%%REFRESH%%", str(refresh_s)).replace("%%LEAGUE%%", html.escape(league))
            .replace("%%META%%", meta).replace("%%DEFAULT_GOLD%%", str(DEFAULT_GOLD_PER_UNIT)).replace("%%DATA%%", js))


def build(league, collect=False, last_n=24, min_gap=1.3, refresh_s=600):
    if collect:
        from .client import Scout
        from .collect import collect_pairs
        from .ggg import build_map, sync
        con = connect()
        collect_pairs(Scout(league), con)      # poe2scout snapshot: keeps the name mapping learning
        if sync(con, hours=last_n + 2, league=league, verbose=False):
            build_map(con, verbose=False)
    from .trades import import_csv
    import_csv(connect())   # no-op unless the trades table is empty (fresh DB on GitHub)
    rows, info, _ = find_rounds(connect(), league, last_n=last_n, min_gap=min_gap)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render(rows, info, league, refresh_s), encoding="utf-8")
    return rows, info


def _lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--league", default="Forbidden Rites")
    ap.add_argument("--collect", action="store_true", help="download a fresh snapshot first")
    ap.add_argument("--serve", action="store_true", help="collect + rebuild every --every minutes and serve the page")
    ap.add_argument("--every", type=int, default=60, help="minutes between refreshes in --serve mode")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--hours", type=int, default=24, help="how many recent hourly snapshots to use")
    ap.add_argument("--min-gap", type=float, default=1.3)
    a = ap.parse_args(argv)
    if not a.serve:
        rows, info = build(a.league, a.collect, a.hours, a.min_gap)
        print(f"wrote {OUT} ({len(rows)} routes, {info.get('snaps', 0)} snapshots)")
        for r in rows[:15]:
            print(f"  {short(r['item']):22s} {MONEY_SHORT[r['fund']]:>5s}->{MONEY_SHORT[r['sell']]:5s} "
                  f"gold/div {r['gold_per_div']:7.0f}  +{r['profit_div']:.2f} div/div  stable {r['stable']:.0%}  "
                  f"gap {r['gap_med']:.2f}x{'' if r['gold_known'] else '  gold?'}{'  proven' if r['proven'] else ''}")
        return

    def loop():
        while True:
            try:
                rows, _ = build(a.league, True, a.hours, a.min_gap, refresh_s=a.every * 60 // 2)
                print(f"{dt.datetime.now():%H:%M} rebuilt board: {len(rows)} routes", flush=True)
            except Exception as e:  # keep serving the last page if a download fails
                print("refresh failed:", e, flush=True)
            time.sleep(a.every * 60)

    threading.Thread(target=loop, daemon=True).start()
    handler = lambda *x, **k: http.server.SimpleHTTPRequestHandler(*x, directory=str(OUT.parent), **k)
    print(f"serving http://{_lan_ip()}:{a.port}/board.html  (Ctrl+C to stop)")
    http.server.ThreadingHTTPServer(("0.0.0.0", a.port), handler).serve_forever()


if __name__ == "__main__":
    main()
