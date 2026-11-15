"""Walk-forward backtest: at every as_of hour, produce advice using only past data,
then grade it with the following hours. This is the "was my advice good?" loop."""
from __future__ import annotations

import argparse
import collections
import statistics as st
from dataclasses import asdict

from .db import connect
from .strategy import BandParams, band_mm, simulate


def load_series(con, league):
    ser = collections.defaultdict(list)
    names = {r["item_id"]: r["api_id"] for r in con.execute("SELECT item_id, api_id FROM items")}
    for r in con.execute("SELECT item_id, ts, price_ex, quantity FROM price_history WHERE league=? ORDER BY ts",
                         (league,)):
        ser[names.get(r["item_id"], str(r["item_id"]))].append((r["ts"], r["price_ex"], r["quantity"]))
    return ser


def run(ser, p: BandParams, step_h=6, top_n=5, start_frac=0.0, end_frac=1.0):
    """Every `step_h` hours, take the top_n advices (only past data) and grade them on the future."""
    all_ts = sorted({t for s in ser.values() for t, _, _ in s})
    idx = {k: {t: i for i, (t, _, _) in enumerate(s)} for k, s in ser.items()}
    lo = max(p.lookback_h, int(len(all_ts) * start_frac))
    hi = min(len(all_ts) - p.horizon_h, int(len(all_ts) * end_frac))
    results = []
    for ti in range(lo, hi, step_h):
        as_of = all_ts[ti]
        cands = []
        for api, s in ser.items():
            i = idx[api].get(as_of)
            if i is None:
                continue
            a = band_mm(api, s[: i + 1], p)
            if a:
                cands.append((a, s[i + 1:]))
        cands.sort(key=lambda x: -x[0].score)
        for a, fut in cands[:top_n]:
            results.append({"as_of": as_of, **asdict(a), **simulate(a, fut)})
    return results


def summarize(results):
    if not results:
        return {"advices": 0}
    filled = [r for r in results if r["filled"]]
    rets = [r["realized_pct"] for r in filled]
    return {
        "advices": len(results),
        "fill_rate": round(len(filled) / len(results), 3),
        "round_trip_rate": round(sum(1 for r in filled if r.get("sold")) / max(1, len(filled)), 3),
        "hit_rate": round(sum(r["hit"] for r in filled) / max(1, len(filled)), 3),
        "avg_ret_filled": round(st.mean(rets), 4) if rets else 0,
        "median_ret_filled": round(st.median(rets), 4) if rets else 0,
        "worst": round(min(rets), 3) if rets else 0,
        "ev_per_advice": round(sum(rets) / len(results), 4),  # unfilled advice = 0 return
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--league", default="Forbidden Rites")
    ap.add_argument("--grid", action="store_true", help="parameter sweep: tune on first half, test on second")
    a = ap.parse_args(argv)
    con = connect()
    ser = load_series(con, a.league)
    if not a.grid:
        res = run(ser, BandParams())
        print(summarize(res))
        by_item = collections.defaultdict(list)
        for r in res:
            if r["filled"]:
                by_item[r["api_id"]].append(r["realized_pct"])
        print("\nper item (n, hit, avg):")
        for k, v in sorted(by_item.items(), key=lambda kv: -st.mean(kv[1])):
            print(f"  {k:35s} {len(v):3d} {sum(x > 0 for x in v) / len(v):.2f} {st.mean(v) * 100:+.1f}%")
        return
    rows = []
    for lb in (24, 48, 96):
        for hz in (12, 24, 48):
            for bq, sq in ((0.2, 0.8), (0.25, 0.75), (0.35, 0.65)):
                for mt in (0.15, 0.3):
                    p = BandParams(lookback_h=lb, horizon_h=hz, buy_q=bq, sell_q=sq, max_trend=mt)
                    tr = summarize(run(ser, p, end_frac=0.5))
                    te = summarize(run(ser, p, start_frac=0.5))
                    rows.append((tr.get("ev_per_advice", 0), te.get("ev_per_advice", 0), lb, hz, bq, sq, mt, te))
    rows.sort(key=lambda r: -r[0])
    print("train_ev  test_ev  lookback horizon buy_q sell_q max_trend | test summary")
    for r in rows[:12]:
        print(f"{r[0]*100:+6.2f}% {r[1]*100:+6.2f}%  {r[2]:4d} {r[3]:4d} {r[4]:.2f} {r[5]:.2f} {r[6]:.2f} | {r[7]}")


if __name__ == "__main__":
    main()
