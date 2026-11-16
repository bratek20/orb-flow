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
| 2 | 2026-11-15 ~10:00 | give 80 Regal for 1 Div | **FILLED** (~10:40) | 80 regal bought at 0.41 ex (~33 ex) became 1 div (~600 ex) |
| 3 | 2026-11-15 (after #1 filled) | sell 245 Regal for 478 ex (1.95 ex/regal), first in the sell queue ahead of a 2:1 wall of 5200 | placing, 57k gold fee | bought for 100 ex, so +378 ex if filled |

### CORRECTION 2026-11-15: UI ratio direction
The exchange UI shows ratios as **want : have**. In the sell window (want ex, have regal) the wall is
2:1 = **2 ex per regal**. So in the buy window, "available 1:2" meant 1 regal for 2 ex (ask ~2 ex), not
2 regals per ex. The real Regal/ex book is **bid ~0.41 ex vs ask ~2 ex**, a ~5x spread. My earlier
"regal ≈ 0.45 ex" was wrong. Experiment 1 bought 245 regal for 100 ex: a seller dumped into the bid.
- That would put a regal at 2 ex in the ex market vs ~7.5 ex in the div market (ninja 81 regal/div), so the
  ex<->div cross-pair gap may be partly real after all. Experiment 2 (80 regal -> 1 div) is not hopeless.
- Gold fee seen: ~57k gold for an order worth ~478 ex.

## 2026-11-15: the cross-currency pattern is REAL (two live confirmations)
- Regal: ex market bid 0.41 ex, sold 80 regal for 1 div (7.5 ex each), about 18x.
- Gemcutter's Prism (player's own trade): bought at 20 ex, sold 1:1 for chaos (~58 ex), about 2.9x.
- API for GCP agrees: ex pair ~20 ex, chaos pair ~29-38 ex, div pair ~41-46 ex.
- So the original cross_pair scanner was right and my "it's an artifact" call was wrong. The new
  `orbflow.chains` ranks these chains by ex/hour, with fill-time estimates.
- Working hypothesis: Exalted is the "small change" currency. Mappers dump cheap currency into ex bids, while
  crafters buy the same items in bulk with chaos/div at much higher prices. The gap survives because
  both legs are maker orders (patience) and each order costs gold.
- Gold could become the binding constraint: ~57k gold for a 478-ex order (~120 gold per ex of value?).
  Gold cost of every order needs logging.

## 2026-11-15: gold fee model (6 logged orders)
**fee = units you WANT x per-unit gold of the wanted item.** The item you give and the order's value don't matter.
| wanted item | gold per unit | gold per ex of value |
|---|---|---|
| Exalted | 120 | 120 (expensive: avoid *wanting* ex) |
| Regal | 120 | ~290 at 0.41 ex |
| Chaos | 160 | ~2.7 |
| Gemcutter's Prism | 1000 | ~20-50 |
| Divine | 800 | ~1.3 (cheapest way to sell) |
| Omen of Abyssal Echoes | 1000 | ~45 at ~22 ex |
| Omen of Chaotic Rarity | 450 | ~5.6 at ~81 ex |
| Vaal Armourer's Infuser | 250 | ~0.7 at ~350 ex |
- The gold goes into the BUY leg (many cheap units). Selling into chaos/div costs almost nothing.
- Selling for exalts is the gold-worst move. Prefer chaos/div as the sell currency, then convert only if needed.
- Player's GCP flip: bought 14 for 208 ex (14.9 each), sold 20 for 21 chaos (~58 ex each).

## 2026-11-16: scaling results and next strategies
- Player cycled ex -> regal -> div for a few hours: **+30 div**, waits of ~30 min per leg.
  Holdings now: 34 div, 1239 regal, 454 ex. ninja still shows regal at ~83/div (6.6 ex); div = ~546 ex.
- Gold per div of regal profit: 82 regal x 120 + 800 = ~10.6k gold (+~4k if the ex has to be bought, since 33 ex x 120).
- Regal liquidity (3 snapshots): div market 850-5000 regal/h, seller queue up to ~24k regal.
  Ex market 150-1000 regal/h. The ex buy side is the bottleneck.
- Journal: 9 of 20 cross_pair leads from 2026-11-15 still showed a >15% gap a day later (45%). Leads are noisy,
  so always verify live.
- Candidates for more throughput:
  - Omen of Chaotic Rarity: ex pair ~39-78 ex, chaos pair ~320-440 ex, div ~300-325 ex (ninja 325; div vol 734).
    Ex-side flow ~35-60/h. About 6x the profit-flow of regal, but the same ex-funding gold cost.
  - Chaos-funded (gold-cheap funding: chaos costs 160 gold per ~52 ex): Omen of Abyssal Echoes chaos ~24 ex,
    div ~52 ex, 350-1300 units/h. Needs the per-unit omen gold fee.
- New tool: `python -m orbflow.liquidity <item> --qty N` (units/h, queue, front/back fill hours).

## 2026-11-16: full-round gold accounting (`orbflow.cycles`)
Live numbers (div->ex 597, regal bid 2.45/ex, sell 82 regal/div), per 1 div put through the loop:
| leg | gold | gold per div of profit |
|---|---|---|
| div -> 597 ex | 71.6k | 4.3k (27%) |
| 597 ex -> 1463 regal | 175.5k | 10.4k (67%) |
| 1463 regal -> 17.8 div | 14.3k | 0.85k (6%) |
| **total** | **261k for +16.8 div** | **15.5k per div (38 ex per 1k gold)** |
- The gold sink is wanting 120-gold regals that are worth 0.41 ex, not the exalts.
- Funding with chaos instead of exalts: div -> ~9.5 chaos costs ~1.5k gold vs 71.6k for div -> 597 ex.
- Chaos-funded rounds where poe.ninja confirms the div-side price: Refined Necrotic Catalyst (chaos ~620 -> div ~1200-1375),
  Vaal Armourer's Infuser (~515 -> ~930-950), Omen of Abyssal Echoes (~25 -> ~54-56), Twilight Reliquary Key (~19 -> ~36-39).
  Their gold per div of profit is 3-12k IF the item fee is ~300/unit (unknown). That's the next thing to measure.
- Regal stays far ahead on profit per div of capital (+16.8 div per div in). Chaos rounds are about +0.2-1.3 div per div in.
  With 34 div of capital and gold now the scarce input, the per-gold ranking matters most.

## 2026-11-16: gold check against reality
- Player gold: ~1.4M -> ~1.0M over the +30 div session: **~400k gold for ~30 div = ~13.3k gold per div of profit**.
  The model predicts 10.6k (with ex on hand) to 15.5k (ex bought with div), so it is consistent.
- Runway at the regal loop: ~1.0M / 13-15.5k ≈ **65-75 more div** before gold runs out.

## 2026-11-16: Omen of Abyssal Echoes test
- Buy order: 28 echoes for 10 chaos (2.8 per chaos, ~22 ex each). Gold fee **1000 per omen** (28k).
- Round at 11 echoes/div: +1.42 div per div in, **21.2k gold per div of profit**, worse than regal (13-15.5k).
  At 9 per div: 15.6k, about equal to regal. Gold-wise it is not an upgrade at this unit price.
- Pattern: GCP and echoes are both 1000/unit. If catalysts/infusers are also ~1000, items worth 500-1300 ex
  would cost only ~1-2 gold per ex. That's the real gold-saver to test next.

## 2026-11-16: Omen of Chaotic Rarity, done live
- Bought 10 for 810 ex (81 ex each, 4.5k gold, **450 gold/unit**). Sold 10 for 58 chaos (5.8 chaos each, 9.3k gold).
  About 810 ex -> 58 chaos (~3,400 ex): **~+2,600 ex**, 13.8k gold for the two trading legs.
- If the 810 ex had to be bought with div (120 gold/ex = 97k), the full round is ~24k gold per div of profit,
  worse than regal (15.5k), because only 4.5x per ex vs 18x for regal.
- Rule: **spend exalts on the route with the highest multiplier per ex** (regal). Ex costs 120 gold whatever it's used for.
  Spend chaos and div on the lower-multiplier routes.
- Short names: `python -m orbflow.names` (full list in docs/NAMES.txt). All CLIs accept them.

## 2026-11-16: echoes scaling
- Sold 16 echoes for 2 div (**8 per div ≈ 75 ex each**, above ninja's ~54). Bought at 2.8 per chaos (~21 ex).
- Round at 8/div: +2.32 div per div in, **13.2k gold per div of profit** (regal: 15.5k). Slightly better on gold,
  and it needs no exalts. At 11/div it falls to 21k, so the sell price decides it.
- Scaling: buying 140 echoes for 50 chaos (140k gold). Div market trades ~1000 echoes/h with a ~10k seller queue.

## 2026-11-16: armour-infuser
- Best bid is ~6 chaos (~350 ex). The player bids 3 for 18 chaos, first in line. **Gold fee 250 per unit** (750 for 3).
- Sells for div at ~1.5-1.6 div (ninja ~955 ex). Round: ~2.8k gold per div of profit, about 5x better than regal.
