# Findings log

## 2026-11-15: first look (league: Forbidden Rites, about 10 weeks old)

**Reference rates:** 1 div ≈ 590–610 ex and 1 chaos ≈ 59 ex. A 100 ex budget is about 0.17 div or 1.7 chaos.

1. **Hourly prices mean-revert strongly.** Lag-1 autocorrelation of hourly returns is about −0.3 to −0.5
   on nearly every liquid item. That is the signature of bid/ask bounce, which is the spread a flipper
   can harvest. Some of it is an artifact of blending pairs (finding 2).
2. **The same item implies very different prices in different pairs.** From the latest snapshot, using
   units actually traded in the hour:

   | item | in the ex pair | in the div/chaos pair | units/h (ex leg / other leg) |
   |---|---|---|---|
   | Regal Orb | 1.06 ex | 10.7 ex (div) | 507 / 5082 |
   | Orb of Alchemy | 3.4 ex | 15.3 ex (chaos) | 1100 / 5446 |
   | Armourer's Scrap | 1.3 ex | 9.6 ex (chaos) | 888 / 6760 |
   | Greater Exalted Orb | 15.9 ex | 48 ex (div) | 592 / 1197 |

   Nearly every cheap item looks 4–10× cheaper in its ex pair. A gap this large and this systematic is
   more likely a quirk in how the data is aggregated, or how I read it, than free money. **It has to be
   checked in game before any real budget goes in.**
3. **v0 band backtest is invalid** (+73%/trade, 98% hit) because of finding 2. Kept only as a harness.

### Open questions for the player
- In game, what are the live ratios for Regal↔Exalted and Regal↔Divine (and Alchemy↔Exalted and Alchemy↔Chaos)?
- How much gold is available? It caps how many orders can be placed.

## 2026-11-15 (later): first in-game ground truth (Regal Orb)
- Player saw **Regal<->Exalted at 2.47 (available) vs 2.48 (competing)**: practically no spread.
  That book is efficient, so there is nothing to flip there. (The direction of the 2.47 still needs confirming.)
- Player saw **50 Regal -> 1 Divine** as the best competing offer, and it is not filling.
- API, last 2 hourly snapshots, Regal vs Divine: 5082 regal / 92 div, then 4382 / 64,
  i.e. **55-68 regals per div actually traded**, about 4-5k regals/hour. So it is NOT a dead
  market. The 50:1 order asks for more than the market pays, and sellers offering 55-70 per div fill first.
- poe.ninja says regal = 7.45 ex (81 regal/div). The API-implied prices still disagree with each other
  (ex pair: ~0.6-1.06 ex/regal, chaos pair: ~5.8 ex/regal), so they can't be trusted without the live book.
- Next check: the *available* trades in the Regal->Divine market (someone handing over a div for
  N regals). If N regals cost far less than 1 div through the ex market, the chain is real.

## 2026-11-15: live Regal books (player reading)
- Book where you give ex and get Regal: **available 1:2 (stock 1782)**, **competing 2.47:1 (stock 15)**.
  A book can't be crossed, so the only consistent reading is that sellers give 2 regal per ex (ask = 0.50 ex)
  and buyers bid 2.47 regal per ex (bid = 0.405 ex). **Regal ≈ 0.40-0.50 ex, spread ≈ 23%.**
  -> The ex-pair API numbers (~0.6-1 ex) were roughly right. The div-pair numbers (55-68 regal/div ≈ 9-11 ex/regal) are not.
- Book where you give Regal and get Div: only **1:500, stock 3** available. Fair value at 0.45 ex/regal
  is ~1300 regal per div, so a 1:50 or 1:70 bid will never fill.
- Lesson: the per-pair "units traded" from poe2scout can't be read as a price for the div legs of cheap items.
  Don't trust the cross_pair scanner until it is validated against the GGG ratio data.

## Live experiments
| # | placed (local) | order | status | notes |
|---|---|---|---|---|
| 1 | 2026-11-15 09:45 | buy Regal with ~100 ex at ~2.45 regal/ex (bid) | FILLED ~20-25 min after placing | buy side filled fast with a thin bid book (15 stock ahead) |
| 2 | 2026-11-15 ~10:00 | give 80 Regal for 1 Div | open | based on bad API div-leg data; fair value is ~1300 regal/div, so a fill is very unlikely |
| 3 | 2026-11-15 (after #1 filled) | sell ~245 Regal at ~2.05 regal/ex (ask) | to place | target ~119 ex back, about +19% |
