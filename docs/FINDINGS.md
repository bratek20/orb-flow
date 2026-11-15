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
