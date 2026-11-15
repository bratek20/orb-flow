# Path of Exile 2: Currency Flipping & Project Naming Chat

**User:**
Poe2 Trading currencies, I realized I can buy some stuff cheap and sell stuff with higher price, is it known tactic in game? Basically there are some buy offers and sell offers and sometimes there is big difference, so I can put lowest buy offer and then when buy happens I can put lowest sell offer and earn money based on cost difference

**Model:**
**Currency flipping** (also known as **market making** or **straddling** the bid-ask spread) is one of the most well-known and lucrative wealth-building tactics in *Path of Exile 2*. You essentially figured out how real-world financial market makers operate on your own.

**Why it works so reliably**
You are profiting off other players' impatience. When a player finishes a map and wants quick currency to upgrade their gear, they dump their loot directly into existing buy orders for instant cash. Conversely, when a wealthy crafter is mass-producing items, they don't want to wait—they buy out existing sell orders immediately. By placing passive orders on both sides, you act as the middleman providing instant liquidity and pocketing the difference.

**The catches that keep it balanced**
While it feels like an infinite money printer at first, Grinding Gear Games built a few friction points into the Currency Exchange to keep flippers from taking over the economy:
* **Gold is your real bottleneck:** Every order costs Gold, which cannot be traded with other players and has to be farmed by killing monsters and running maps/waystones. Gold fees scale with the quantity of items you request, so flipping huge stacks of low-tier currency burns through Gold rapidly. Worse, if you manually cancel an active order, your Gold fee is not refunded.
* **Undercutting wars:** On popular items, other flippers will constantly outbid your buy orders or undercut your sell orders by 1 unit. If you keep canceling and relisting to stay at the front of the line, you'll bleed Gold.
* **Price volatility:** Markets shift noticeably between peak evening hours, weekdays, and weekends. If you buy an item right before its price dips, you can get stuck holding inventory that won't sell at your target price.

**Tips to get more out of it**
* **Inspect the full order book:** Hold `Alt` while hovering over the market ratio in the exchange window to see the list of competing trades. Sometimes the "best" price is a tiny bait order of 1 or 2 items—you don't always need to outbid those, just price yourself ahead of the big bulk stacks.
* **Try cross-currency arbitrage:** Instead of buying with Exalted Orbs and selling for Exalted Orbs, look for items (like high-tier Omens, Greater Essences, or Boss Fragments) that you can buy cheap with Exalts and sell for Divine Orbs—or vice versa.
* **Focus on high-turnover consumables:** Items that crafters burn through in bulk (Essences, Catalysts, Omens, Distilled Emotions) fill orders much faster than niche items.

Which currencies or crafting materials have you been flipping so far, and are you running into any Gold bottlenecks yet?

---

**User:**
Is there a way to know what is the most liquid currencies meaning a lot of instant sell and buy?

**Model:**
You can measure liquidity both **inside the Currency Exchange UI** by inspecting order-book depth and **outside the game** using live API trackers that log trade volume.

**1. Check Order-Book Depth In-Game**
Hover over the **Market Ratio** in the Currency Exchange and hold **`Alt`** (or press **R3 / Right Stick** on console) to open the **Available Trades** and **Competing Trades** breakdown. Look at two numbers:
* **Stack Depth (Volume on the Book):** High-liquidity items have hundreds or thousands of units queued across multiple consecutive price ratios on *both* sides. If an item only has a few dozen units listed total, orders will sit unfilled for a long time.
* **The Spread vs. Turnover Balance:** The highest-volume currencies (like Exalted, Chaos, and Divine Orbs) move almost instantaneously, which keeps their buy/sell spreads razor-thin. A massive spread usually indicates low liquidity. The flipping "sweet spot" is an item with **hundreds of units stacked on both sides** that still maintains a noticeable gap between the top bulk buy stack and top bulk sell stack.

**2. Use External Volume Trackers**
Because the in-game UI doesn't display a "24-hour volume" stat, community tools pull data directly from the Currency Exchange API:
* **poe2scout (`poe2scout.com`):** Tracks live exchange rates alongside **trade volume/quantity** and price history. Sorting by high volume lets you immediately spot which items are actively turning over hundreds or thousands of units rather than sitting stagnant.
* **poe.ninja:** Useful for checking multi-day price graphs to make sure a high-volume item isn't crashing before you buy into it.

**3. Stick to Consistently Liquid Categories**
If you want fast fills without clicking through every tab in the exchange, focus on items with constant sink/demand:
* **Core Orbs (Fastest velocity, lowest margin):** Exalted Orbs, Chaos Orbs, Divine Orbs, Orbs of Annulment, Vaal Orbs, and Fracturing Orbs.
* **Endgame Crafting Materials (Best balance of speed + margin):** High-demand **Omens** (such as Sinistral/Dextral Erasure or Annulment), **Greater/Perfect Jeweller's Orbs**, and top-tier **Essences**. Mappers dump these immediately for quick currency, while crafters buy them out in bulk.
* **Pinnacle Keys & Fragments:** Items like Breachstones or *An Audience with the King* turn over quickly because boss-runners buy them continuously in bulk.

What size bankroll are you working with right now—are you mostly flipping in Exalted/Chaos Orbs, or have you moved up to Divine-tier items yet?

---

**User:**
Would it be possible to implement some sort of program to gather all this information and output what is the best to trade on? Can trading inside poe be somehow automated? Mostly question about API that can be used but if there is non other options

**Model:**
Yes—you can absolutely build a program to pull market data, calculate spreads, detect triangular arbitrage loops, and rank the most profitable trades. However, there is a strict line between **automating market analysis** (allowed) and **automating in-game actions** (bannable).

### 1. Building a Market Scanner (Allowed & Supported)
Grinding Gear Games (GGG) and community sites provide public JSON endpoints you can query using Python, Node.js, or any scripting language without needing to log in or risk your account:

* **Official GGG Currency Exchange Endpoint:** GGG exposes an official public CDN endpoint (`https://web.poecdn.com/api/currency-exchange/poe2`) that returns aggregate Currency Exchange trade history grouped into hourly digests. Each market pair includes the traded items (`market_pair`) and volume/rate data, allowing you to compute real-time liquidity and historical movement directly from the source.
* **`poe.ninja` Public Economy API:** If you want clean, pre-aggregated JSON without parsing raw hourly chunks, you can query `poe.ninja` directly (no API key required):
  * **Leagues:** `GET https://poe.ninja/poe2/api/economy/leagues`
  * **Exchange Data:** `GET https://poe.ninja/poe2/api/economy/exchange/current/overview?league={league}&type={type}` (where `type` can be `Currency`, `Fragments`, `Essences`, `Ritual` for Omens, `Delirium`, `Breach`, `Runes`, `SoulCores`, etc.).
  * This returns `primaryValue`, `volumePrimaryValue` (liquidity), `maxVolumeCurrency`, and `maxVolumeRate`.
* **`poe2scout` API:** Also provides public JSON snapshots (`https://api.poe2scout.com`) specifically tailored around PoE 2 exchange pairs and reference currencies.

**What your script can calculate:**
* **Liquidity-weighted spreads:** Filter out low-volume traps by requiring a minimum `volumePrimaryValue` before ranking items by bid-ask spread.
* **Triangular Arbitrage:** Build a directed graph of exchange rates (e.g., *Divine Orb → Omen → Exalted Orb → Divine Orb*) and use a pathfinding algorithm (like Bellman-Ford on negative log weights) to find multi-step conversion loops that net more currency than you started with.
* **Important Caveat:** Because public endpoints aggregate data roughly every hour (rather than streaming the live in-game order book tick-by-tick), your script acts as a **radar** to tell you *which* items to check. You still have to verify the live buy/sell spread in-game before placing your orders.

### 2. Automating In-Game Trading (Strictly Against ToS)
**You cannot automate placing orders, clicking the UI, or executing trades inside the game.**
* **Third-Party Policy & Automation Rules:** GGG’s Terms of Service strictly prohibit any macro, script, or bot that performs automated in-game actions or sends multiple server-side actions per user hardware input. Using OCR/screen-scraping bots or mouse-click macros to auto-list and undercut on the Currency Exchange will result in a permanent account ban.
* **What *is* allowed in-game:**
  * **Built-in Asynchronous Trading:** You don't need a bot to trade while mapping or offline. The Currency Exchange fills your buy/sell orders asynchronously in the background, and for regular gear/items, recruiting **Ange** (via the *Hostile Takeover* quest) unlocks Merchant Tabs that automatically sell your listed items to visiting buyers without you needing to stop mapping or respond to whispers.
  * **Log Parsing & Overlays:** Tools that read your local `Client.txt` log file (for example, to send a Discord/Telegram ping to your phone when a trade completes) or display price-check overlays triggered by manual hotkeys are completely fine.

If you'd like to build a quick scanner, what programming language do you prefer (e.g., Python or JavaScript)? I can write a starter script that pulls live PoE 2 exchange data and ranks the highest-volume arbitrage opportunities.

---

**User:**
Suggest name for such project, flipper word is nice

**Model:**
**PoE 2 Lore & Currency Flavored**
* **FaustusFlipper:** Named after Faustus, the NPC who actually runs the Currency Exchange in-game.
* **ExileFlipper:** Classic, instantly recognizable, and clean for a GitHub repository or Discord bot.
* **DivFlipper:** Short, punchy, and centered on the endgame Divine Orb economy.
* **VaalFlipper:** A nod to Vaal Orbs—fitting if you ever add high-risk, volatile market alerts.

**Clean & Tech-Focused**
* **FlipperPulse:** Sounds like a real-time market monitor and liquidity tracker.
* **FlipperRadar:** Emphasizes that it scans the exchange for spreads without crossing into automation.
* **FlipFlow:** Highlights high-liquidity, fast-turnover currencies rather than stagnant items.
* **poe2-flipper:** Simple, lowercase, and standard if you're building a CLI tool or Python package.

**Trading & Market Wordplay**
* **CoinFlipper:** Works on two levels—literally flipping currency and playing the odds on market spreads.
* **SpreadFlipper:** Direct nod to profiting off the bid-ask spread.
* **LiquidFlipper:** Calls out the exact strategy of targeting high-volume, fast-moving markets.

Which vibe fits what you're building—something lore-heavy like **FaustusFlipper**, or a clean utility name like **FlipperRadar**?

---

**User:**
Exile flipper wins for now, suggest better name, does not need to include flipper word

**Model:**
**Wall Street & Finance Wordplay**
* **Vaal Street:** A play on Wall Street and Vaal Orbs—clever, memorable, and instantly communicates high-volume trading.
* **Wraeclast Terminal:** Inspired by the Bloomberg Terminal; fits well if you are building a data-heavy scanner or CLI tool.
* **SpreadCraft:** Combines bid-ask spreads with PoE’s "theorycrafting" culture.

**Upgraded "Exile" Variants**
* **ExileArb:** Keeps the *Exile* identity you liked while swapping "flipper" for *Arbitrage*—shorter and cleaner for a repo or command prefix.
* **ExileDesk:** Sounds like an institutional trading desk rather than a basic script.
* **ExilePulse:** Emphasizes tracking real-time market liquidity and volume spikes.

**Lore & Currency Flavored**
* **Faustus Ledger:** Named after Faustus, the Currency Exchange NPC, paired with a financial ledger theme.
* **OrbFlow:** Short, modern, and directly highlights liquid, fast-moving currencies.
* **DivTicker:** Gives the project the feel of a live stock market ticker centered on Divine Orbs.

Which direction fits your vision best—a sharp pun like **Vaal Street**, or a clean utility name like **ExileArb**?

---

**User:**
Orb flow or exile flipper, what you recommend, or maybe some other names?

**Model:**
Go with **OrbFlow** if you want the project to look like a sleek, modern web app or public tool, and **ExileFlipper** if you are building a straightforward personal CLI script or GitHub utility.

* **Why OrbFlow wins on polish:** "Flow" directly reflects what you are actually tracking—market liquidity and volume velocity. It sounds like a legitimate fintech product and ages well if you later expand the tool beyond simple flipping (like tracking price history or crafting costs).
* **Why ExileFlipper wins on clarity:** Anyone browsing GitHub or Discord immediately knows what it does and what game it is for without needing an explanation. It has a classic, utilitarian developer vibe.

If neither feels quite 100% right, here are three middle-ground names that bridge both styles:

* **ExileFlow:** The exact mashup of your two finalists—keeps the clear *Path of Exile* anchor while sounding cleaner and more analytical than "flipper."
* **Trade of Exile:** A simple, memorable play on the game's title that sounds like a full-fledged community trade site.
* **VaalPulse:** Short, punchy, and captures the idea of monitoring the live heartbeat of volatile currency markets.

Are you planning to keep this as a personal terminal script, or do you want to turn it into a web dashboard or Discord bot eventually?

---

**User:**
dump all conversation to file