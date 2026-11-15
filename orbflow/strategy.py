"""Strategies. Each strategy maps (price series up to as_of) -> optional Advice.

The price series is poe2scout's hourly average exchange price (in ex). It is NOT a live
order book: hourly averages swing between "sellers dumping" and "buyers sweeping" hours,
so the size of the swing is a proxy for the bid/ask spread we can harvest with limit orders.
"""
from __future__ import annotations

import math
import statistics as st
from dataclasses import dataclass, field


@dataclass
class Advice:
    api_id: str
    strategy: str
    buy_at: float          # limit buy price (ex)
    sell_at: float         # limit sell price (ex)
    horizon_h: int
    score: float           # expected % edge per round trip, after haircut
    rationale: str
    meta: dict = field(default_factory=dict)


@dataclass
class BandParams:
    lookback_h: int = 48       # window to estimate fair price and band
    horizon_h: int = 24        # how long the advice stays valid
    buy_q: float = 0.25        # buy at this quantile of recent prices
    sell_q: float = 0.75       # sell at this quantile
    min_qty_h: int = 100       # min median units traded per hour (liquidity)
    max_price_ex: float = 100  # must be affordable within budget
    min_edge: float = 0.06     # required spread after haircut
    haircut: float = 0.03      # assumed slippage / undercut cost per round trip
    max_trend: float = 0.25    # skip items moving > this (abs log) over lookback - falling knives


def band_mm(api_id: str, series: list[tuple[str, float, int]], p: BandParams) -> Advice | None:
    """Spread-harvest ("market making") on the recent hourly price band.

    series: [(ts, price_ex, qty)] oldest->newest, ending at as_of.
    """
    if len(series) < p.lookback_h:
        return None
    w = series[-p.lookback_h:]
    prices = [x[1] for x in w if x[1] > 0]
    qtys = [x[2] for x in w]
    if len(prices) < p.lookback_h * 0.8:
        return None
    med_q = st.median(qtys)
    fair = st.median(prices)
    if med_q < p.min_qty_h or fair > p.max_price_ex:
        return None
    k = max(3, p.lookback_h // 4)
    trend = math.log(st.median(prices[-k:]) / st.median(prices[:k]))
    if abs(trend) > p.max_trend:
        return None
    qs = st.quantiles(prices, n=100)
    buy = qs[int(p.buy_q * 100) - 1]
    sell = qs[int(p.sell_q * 100) - 1]
    edge = sell / buy - 1 - p.haircut
    if edge < p.min_edge:
        return None
    score = edge * min(1.0, math.log10(med_q) / 3)  # reward liquidity (fill probability)
    return Advice(api_id, "band_mm", round(buy, 4), round(sell, 4), p.horizon_h, round(score, 4),
                  f"fair~{fair:.2f}ex band {buy:.2f}->{sell:.2f} ({edge*100:.0f}% net), "
                  f"{med_q:.0f} units/h, trend {trend*100:+.0f}%",
                  {"fair": fair, "edge": edge, "qty_h": med_q, "trend": trend})


def simulate(adv: Advice, future: list[tuple[str, float, int]], dump_cost: float = 0.03) -> dict:
    """Grade an advice against what happened next (hourly proxy).

    Buy fills in the first hour whose avg price <= buy_at; sell fills at a later hour whose
    avg price >= sell_at. If never sold, mark-to-market at last price minus dump_cost.
    """
    fut = future[: adv.horizon_h]
    if not fut:
        return {"filled": False, "realized_pct": 0.0, "hit": None, "exit": None}
    bought_i = next((i for i, x in enumerate(fut) if x[1] <= adv.buy_at), None)
    if bought_i is None:
        return {"filled": False, "realized_pct": 0.0, "hit": None, "exit": None}
    sold_i = next((i for i, x in enumerate(fut) if i > bought_i and x[1] >= adv.sell_at), None)
    exit_p = adv.sell_at if sold_i is not None else fut[-1][1] * (1 - dump_cost)
    r = exit_p / adv.buy_at - 1
    return {"filled": True, "sold": sold_i is not None, "realized_pct": r, "hit": int(r > 0), "exit": exit_p}
