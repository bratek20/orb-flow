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
| Omen of Chaotic Monsters | 450 | ~16 at ~28 ex |
| Omen of the Blessed | 800 | ~11 at ~70 ex (trade #30) |
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
- 2026-11-16 later: the in-game price moved to 2.4 echoes per chaos (~26 ex each). Round at 8/div: 9.5 chaos -> 22.8 echoes -> 2.85 div,
  +1.85 div, gold 26.6k (echo leg 22.8k) = **14.4k gold per div of profit**, about the same as regal. At 9/div: ~17k (worse).
  Correction from the player: the book is competing (buyers) 2.9 echoes/chaos, available (instant) 2.5. Our 2.8 bid sits ahead
  of the 2.9 queue. Instant buy at 2.5 -> ~14.0k gold per div of profit (sell at 8/div).

## 2026-11-17: overnight results
- Filled overnight: 140 echoes for 50 chaos (2.8/chaos, 140k gold); 13 div for 936 regal (**72 regal/div**, 10.4k gold = 800/div);
  3 armour-infusers for 18 chaos (6 chaos each).
- NOT filled overnight: selling 3 armour-infusers for 5 div (1.67 div each). Market: div side ~847 ex in snapshots,
  poe.ninja 775 ex = ~1.58 div; ~235/h trade vs div but ~5.9k infusers stocked on the seller side. 1.67 is above the market.
  Next ask: 1.5 div each (3 div for 2).
- poe.ninja now: div 491 ex, echoes 60.8 ex (= 8.1 per div), so selling echoes at 8/div is right at the market.
- In-game echoes book (player, morning): best competing ask **5 echoes per div**, far above poe.ninja (8.1/div) and snapshots (~10/div).
  The API lags or the price spiked. Listed 140 echoes for 28 div (22.4k gold). If it fills: round = ~7.5k gold per div of profit.
- Sold 4 armour-infusers for 6 div (**1.5 div each**, 4.8k gold = 800/div). Bought at 6 chaos each (~0.63 div).
  Infuser round confirmed: ~2.4x per round, ~2.8k gold per div of profit. Still OK up to ~8-9 chaos buy price (~4k gold/div).
- Player (2026-11-17): armour-infuser now **15 chaos each** in game. Snapshot history of the infuser/chaos pair, chaos per infuser:
  16.0, 12.7, **6.1**, 9.4, 14.0. Our 6-chaos fill was a cheap hour (someone dumped). Normal is 12-16 chaos = ~1.3-1.6 div,
  the same as the div-side price, so there's no edge at 15. Lesson: check the pair ratio PER SNAPSHOT, not the median
  implied price, before calling a gap real. A low bid (6-8 chaos) left in the book can still catch dumps.

## 2026-11-17: per-snapshot check of leads (5 snapshots)
- Echoes are rising everywhere: div pair 0.085-0.108 div each, then **0.177 at 03:00** (~5.6/div, matches the player's 5/div ask);
  chaos pair 0.39-0.49 chaos each, then 0.67. The div-vs-chaos gap is still ~2.5-3x.
- Omen of Chaotic Monsters: stable in all 5 snapshots. Chaos 0.55-0.69 chaos each (~30 ex), div 0.13-0.17 div (~75 ex).
  Gold fee unknown (omens seen at 450 and 1000). Next test candidate.
- Regal still 67-77 regal/div vs 0.5-0.76 ex in the ex market.
- Rejected after the per-snapshot check: chayulas-cat, uncut-skill-gem-19, sin-necromancy. Their ratios jump 3-10x between hours (thin, noisy).
- Monsters test: bought 10 at 1.67/chaos (450 gold each), first 7 sold at **7 per div**. The round works: ~2x per round,
  ~7.4k gold per div of profit. Scaling with a 30-unit bid.

## 2026-11-17: GGG public exchange feed (no OAuth needed)
- `https://web.poecdn.com/api/currency-exchange/poe2/<unix hour>` is open: every pair of every league per hour with
  volume_traded, lowest/highest_ratio, lowest/highest_stock. Unpublished hours return 404; the newest is ~1-1.5 h late.
- poe2scout snapshots ARE these hours (div/ex volumes 214/109,721 match exactly). Mapping metadata path -> api id is
  learned by volume matching (`orbflow.ggg --map`): 338 ids mapped from 4 matched snapshots.
- Low/high confirm the player's fills: monsters chaos low 0.5 / high 0.6-1.0 chaos (bought at 0.6), div low 0.067 /
  high 0.167 div (sold at 0.143 = 7/div). Monsters also trade at ~19-22 ex in the ex market (cheaper than via chaos).
- Lead: sin-necromancy buys at 1-2.5 ex, sells 0.05-0.08 div (25-40 ex) in the div market, but only 20-50/h there.
  Gold fee unknown (omens are 450 or 1000).
- Gold formula check (21 logged orders, 0 exceptions): gold = units WANTED x fee(wanted item). The fee is a fixed
  per-item constant, independent of what you give, order size and market price. It does NOT follow value
  (infuser ~800 ex -> 250; gcp ~30 ex -> 1000), and no public formula exists. So fees must be learned per item
  (the game shows the fee before you place the order). Useful view: gold per ex of value received:
  ex 120, gcp ~33, echoes ~11-40, monsters ~6-16, chaos ~3.4, div ~1.6, infuser ~0.3.

## 2026-11-17 midday (player report)
- Sin-necromancy: bought 30 (price/gold not reported yet), listed 2 div : 30 (15/div, 1600 gold). Player: "not selling well".
  GGG: only ~15 units/h sell for div, all at exactly 0.067 (15/div) = same price as the ~2.7k queue -> back of the line.
  The ex->div gap on paper (35x) is real in price but the div side is too thin to scale.
- Monsters: listed 9 div : 63 (7/div). Cheaper sellers at 1:10 (50 in stock) are ahead in the book. GGG 11h: 204 monsters
  sold for div at avg 0.127 div (~7.9/div), range 6-15/div. So 7/div is above the average fill but inside the range; 8/div fills most hours.
- Player says ex->regal->div "no longer so good" (no live numbers yet).
- Echoes div price collapsed: 11h 1690 echoes sold for div at avg 0.06 (~16/div, low 0.017). Chaos side ~0.48. The chaos->echoes->div
  gap is ~1.25x now, so the route is dead for the moment. Old #18 (140 echoes at 5/div) is far off the market.
- Pattern: cheap items (sin-necromancy, chance, preserved-jawbone) show 5-30x ex->div gaps, but the div side has queues of
  2-11k units. The gap is real in price but you sit at the back of the queue. Check queue/volume before calling it an edge.
- uncut-skill-gem-19: div side steady at 0.333 (3/div) for 4 hours (27-87/h, queue ~760); ex side 4-70 ex (avg 12-23). Test candidate.
- sin-exaltation: chaos ~0.45-0.9, div ~0.09-0.10 (10-11/div), 280-940/h on div. Monsters-like route, gold fee unknown.
- **Cancelling an order does NOT refund the gold fee** (player, 2026-11-17, cancelled #25 9 div : 63 monsters = 7,200 gold lost).
  So every reprice pays the full fee again: choose the price once, and prefer fewer, bigger orders over many small edits.
  For sell orders into div the fee is 800/div, so a reprice costs ~0.1-0.2 div of gold per 20 div order; for buy orders of omens
  (450/unit) it is much more.
