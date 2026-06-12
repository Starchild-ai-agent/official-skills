---
name: market-structure-ta
version: 1.0.1
description: >-
  Market-structure TA — Wyckoff, SMC/ICT order blocks, Al Brooks price action → trade script with entry/stop/R:R.
metadata:
  starchild:
    emoji: "📐"
    skillKey: market-structure-ta

tags: [trading, technical-analysis, market-structure, smc, wyckoff, ict, price-action]

user-invocable: true
disable-model-invocation: false

---

## When to use

Market structure analysis with Wyckoff, SMC/ICT, Al Brooks, and classical price action — outputs structured trade scripts with levels, entry, stop, R:R.

Use when the user wants real technical analysis on a ticker (e.g. "market structure analysis on NVDA", "Wyckoff phase for BTC", "where's the order block on SOL", "SMC analysis").

## What This Skill Is For

Price action analysis = **read the chart itself, not derivatives of it**. Indicators (RSI, MACD, BB) are second-derivative noise; PA traders read the auction directly — where smart money entered, where stops are stacked, where the imbalance lives.

This skill teaches you (the AI) to produce **a trading thesis with conviction**, not a list of "RSI is overbought, MACD is bullish, mixed signals". Every output must have:
1. A narrative (what's the market doing and why)
2. Key levels (numerical, not vibes)
3. An entry plan (trigger, entry, stop, target, R:R)
4. An invalidation level (where the thesis dies)

If you can't produce all four, say so — don't fake it.

## Mental Model — Four Lenses

You combine four frameworks. Each lens answers a different question:

| Lens | Question it answers | When dominant |
|---|---|---|
| **Wyckoff** | What phase of the cycle? (accumulation / markup / distribution / markdown) | Higher timeframes (W/D) |
| **SMC / ICT** | Where is smart money hunting liquidity? Where are the order blocks and FVGs? | Mid timeframes (4H/1H), entry timing |
| **Al Brooks** | What is each bar saying? Who's winning right now? | Lower timeframes (15m/5m), bar-by-bar |
| **Classical PA** | Trend, channels, S/R, supply/demand | All timeframes, structural skeleton |

Use them as overlays, not silos. A high-conviction setup has alignment across multiple lenses (e.g. Wyckoff Phase C spring + SMC liquidity sweep + bullish CHoCH + Brooks reversal bar).

## The 7-Step Workflow

Always run top-down. Do NOT jump to lower timeframes first.

### Step 1 — HTF Context (Weekly + Daily)
- Pull weekly + daily OHLC (200+ bars daily, 100+ weekly)
- Identify: primary trend (HH/HL = up, LH/LL = down, mixed = range)
- Mark the **dominant Wyckoff phase**: are we accumulating, marking up, distributing, marking down?
- Locate the **last major BOS (Break of Structure)** and **CHoCH (Change of Character)** — these define the current order flow

### Step 2 — Structure Mapping (Daily / 4H)
On the active timeframe, mark:
- Swing highs / lows that matter (HH, HL, LH, LL)
- The current **internal structure** (mini swings inside the larger leg)
- Active **trendline / channel** if one exists

A clean structure = trade with it. A messy structure = wait or scalp ranges.

### Step 3 — Liquidity Mapping
**The most underrated step.** Smart money targets retail stops. Identify:
- **Buy-side liquidity (BSL)** — above equal highs, prior swing highs (where shorts have stops)
- **Sell-side liquidity (SSL)** — below equal lows, prior swing lows (where longs have stops)
- **Trendline liquidity** — stops sitting along an obvious trendline
- **Session highs/lows** — Asia/London/NY ranges (intraday)

These are the **price magnets**. The market routinely sweeps them before reversing.

### Step 4 — Mark POIs (Points of Interest)
Find areas where price is likely to react:
- **Order Blocks (OB)** — last opposite-color candle before a strong impulsive move that broke structure
- **Fair Value Gaps (FVG) / Imbalances** — 3-candle pattern where wick of candle 1 ≠ wick of candle 3, leaving an "unfilled" zone
- **Breaker Blocks** — failed order block that gets traded back through; now flips role
- **Mitigation Blocks** — area where a prior swing failed; price returns to "mitigate" trapped traders
- **Supply / Demand zones** (classical) — base of a strong move

Rank POIs by quality: **OB + FVG overlap + caused BOS + untested** = A+ setup (this is the "Unicorn" model — see `references/advanced-modules.md`).

### Step 5 — LTF Entry (15m / 5m / 1m)
Drop to lower timeframe **only after** HTF context is clear. Look for:
- **Liquidity sweep** of a recent LTF high/low (the "stop hunt")
- **CHoCH on LTF** confirming reversal
- **Entry from an LTF OB / FVG inside the HTF POI**
- **Al Brooks reversal bar**: strong opposite-color close, good follow-through

The setup: HTF POI + LTF sweep + LTF CHoCH + LTF OB entry. This is the SMC entry trifecta.

### Step 6 — Volume / Confluence Check
- Volume should expand on the move you want to trade with, contract on pullbacks
- Wyckoff "no demand / no supply" bars = pullback exhausted
- Confluence: prior HTF S/R, Fib OTE (62%–79%), session levels, moving averages (only as reference, never trigger)

### Step 7 — Build the Script
Output a structured trading thesis (see Output Format below). If you couldn't find a clean setup, say "no trade — waiting for X to happen first".

## Tone & Voice (MANDATORY DEFAULT)

**Default audience: beginner to intermediate traders** (already familiar with basic candles and support/resistance, but not yet systematically trained in PA/SMC/Wyckoff).

**Voice rules:**
- **Every judgment must include an evidence chain** — don't just say "this is support"; say "this is support because (1) it's an untested demand zone from the prior leg, (2) it overlaps the 0.62–0.79 Fibonacci zone, and (3) price still has buffer to the most recent valid swing low at $X."
- **Show explicit math** — always calculate and display R:R, drawdown %, and distance to key levels. Don't make the user do arithmetic. "R:R = 2.6" is 10x better than "risk-reward looks decent."
- **Explain technical terms in plain language on first use** — e.g., "imbalance (an unfilled price gap created by aggressive one-sided movement)." After first use, terms alone are fine.
- **Logic chain > storytelling** — analogies are welcome, but each analogy must be followed by hard "because... therefore..." logic.
- **Don't flex with acronym overload** — keep shorthand practical. In one analysis, avoid introducing more than six distinct abbreviations (OB/FVG/CHoCH/etc.).
- **Bold key conclusions** — users should grasp the core judgment at a glance.

**Tone adjustments (switch dynamically based on user feedback):**

| User signal | Adjustment |
|---|---|
| "I don't understand" / "too technical" / "I'm a beginner" | Downgrade to story mode: use analogies and visual explanations, reduce jargon and math density, keep core conclusions intact |
| "Be more professional" / "I'm advanced" / "Use technical language" | Upgrade to dense mode: use standard SMC/Wyckoff/Brooks terminology throughout, skip plain-language explanations, include advanced modules like OTE/PO3/Unicorn |
| No explicit preference | **Default to the intermediate mode defined in this section** |

**Strictly prohibited:**
- Vague hedging words: "maybe" / "perhaps" / "seems" — give a probability (60%/70%) or a direct call ("bias: X")
- Numberless conclusions: "good R:R" → replace with "R:R = 2.6"
- Unsupported judgments: "there is support here" → replace with "support is here because 1/2/3"
- Recycled internet one-liners: phrases like "patience is a position" should appear at most once per analysis

## Output Format (MANDATORY)

Always produce this structure. No exceptions.

```
## [TICKER] — Market Structure Analysis ([DATE])

### 1. Macro Narrative
[2–4 sentences. Where are we in the Wyckoff cycle? What's the dominant order flow?
What just happened that matters?]

### 2. Key Levels
| Type | Price | Notes |
|---|---|---|
| HTF Resistance | $X | Why it matters |
| HTF Support | $Y | ... |
| Buy-Side Liquidity | $Z | Equal highs at... |
| Sell-Side Liquidity | $W | ... |
| Daily OB (bullish) | $A–$B | Formed [date] before BOS |
| Daily FVG | $C–$D | Unfilled imbalance |

### 3. Structure & Phase
- HTF trend: [up / down / range]
- Last BOS: [up / down] at $X on [date]
- Last CHoCH: [up / down] at $Y on [date]
- Wyckoff phase: [A/B/C/D/E within accumulation/distribution, or markup/markdown]

### 4. Primary Scenario (highest probability path)
[Narrative of what you expect: e.g. "Price sweeps SSL at $X, then mitigates the
daily bullish OB at $Y, expect bullish CHoCH on 1H, target the FVG fill at $Z"]

**Trade plan:**
- Trigger: [what needs to happen before you enter]
- Entry: $X (or zone $X–$Y)
- Stop: $Z (just beyond invalidation)
- Target 1: $A (R:R = ?)
- Target 2: $B (R:R = ?)
- Invalidation: [the exact condition that kills this thesis]

### 5. Alternate Scenario
[What happens if primary fails. Don't be wishy-washy — say what would flip your bias
and what you'd do instead.]

### 6. What I'm NOT Trading
[Be honest about what's unclear or low-conviction. "Skipping the chop between $X and $Y."]
```

## Hard Rules

- **No indicator-only conclusions.** "RSI oversold = buy" is banned. Indicators are confluence, never trigger.
- **No "bullish but could also be bearish" hedging.** Pick a primary, define invalidation.
- **No setups without invalidation.** Every entry must have a level that says "I was wrong".
- **No price targets without R:R math.** Always show the ratio.
- **No analysis without HTF context.** Always start weekly/daily.
- **Round numbers are not levels.** Find the real ones (swing points, OB/FVG edges).
- **If structure is unclear → say "no trade, wait for X".** Patience is a position.

## Data Fetch Pattern

For stocks/forex/commodities → use the `twelvedata` skill.
For crypto → use the `coingecko` skill (`coin_ohlc` for K-line).
For US fundamentals overlay → use `us-stock` skill.

Minimum bars needed:
- Weekly: 100+ bars
- Daily: 200+ bars
- 4H: 200+ bars
- 1H: 200+ bars
- 15m: 100+ bars (only if doing intraday)

For chart visualization, use the `chart` skill with annotated levels.

## Decision Tree — Which Lens to Emphasize

```
User wants...                      → Lens emphasis
─────────────────────────────────────────────────────
"Should I swing trade X?"          → Wyckoff + SMC (D/4H focus)
"Day trade plan for X today?"      → SMC + Brooks (1H/15m/5m)
"Where's the next big move?"       → Wyckoff phase analysis
"Where do I enter / exit?"         → SMC POIs + LTF trigger
"Is this trend over?"              → Structure + CHoCH + Wyckoff distribution signs
"Why did X just dump?"             → Liquidity sweep retro + Brooks bar reading
```

## Advanced Modules
Loaded on demand. Read these only when the analysis needs them:

- **`references/advanced-modules.md`** — OTE (Optimal Trade Entry), Power of 3, Unicorn Model, Breaker Block, Mitigation Block, Silver Bullet, Judas Swing, ICT killzones
- **`references/wyckoff-schematics.md`** — The full accumulation / distribution phase maps (Phase A/B/C/D/E events: PS, SC, AR, ST, Spring, Test, SOS, LPS / PSY, BC, AR, ST, UT, UTAD, SOW, LPSY)
- **`references/brooks-bar-reading.md`** — Bar-by-bar reading: signal bars, entry bars, follow-through, pullback counting, reversal patterns (three pushes, wedges, double tops)
- **`references/glossary.md`** — Quick lookup for all SMC/ICT/Wyckoff/Brooks terminology

## What This Skill Is NOT
- Not a backtester (use the trading-strategy skill or write a script for that)
- Not financial advice (always include risk disclaimer in output)
- Not for predicting exact tops/bottoms (PA gives probabilities, not certainties)
- Not a substitute for risk management (always size based on stop distance, never on conviction)
