# Aesthetic Direction Reference

## Color Strategy: Choose a Level First

Before picking any colors, decide your strategy level. This determines how much color your design uses.

| Level | Description | When to Use | Example |
|-------|-------------|-------------|---------|
| **Restrained** | Near-monochrome. One accent used sparingly (links, active states, one CTA). Surface does the work. | Data tools, documentation, professional dashboards | Notion, Linear, Stripe Docs |
| **Committed** | One accent color used boldly — in headers, illustrations, key UI elements. Still disciplined. | SaaS products, portfolios, marketing pages | Vercel, Figma, Raycast |
| **Full palette** | 3-5 harmonious colors, each with a role. Requires careful balance. | Creative tools, consumer apps, editorial | Slack, Notion (with databases), Pitch |
| **Drenched** | Color IS the brand. Saturated backgrounds, colored surfaces, bold combinations. | Fashion, entertainment, gaming, art | Spotify, Discord, Gumroad |

The strategy level should match your Design Read. A clinical developer tool at "Drenched" will feel wrong. A gaming landing page at "Restrained" will feel lifeless.

---

## How to Build a Color Palette From Scratch

Do NOT copy a preset palette. Build one from your design direction.

### Step 1: Pick a Base Surface Color

Start with the background — the most impactful decision.

- **Light surfaces**: Pure white or a very subtle tint. To tint, add 1-3% of your accent hue to white. Avoid warm neutrals (cream, beige, sand) unless the Design Read explicitly calls for warmth.
- **Dark surfaces**: Near-black, not pure `#000`. Add 2-5% of your accent hue for depth. Write a "scene sentence" first — what physical space does this dark mode evoke? See the **Dark Surface Tint Guide** below for scene-to-color mapping. NEVER use the default `#0a-#0f` blue-black range.
- **Colored surfaces**: A saturated or muted color AS the background (deep navy, forest green, dusty rose). This is bold — commit fully.

### Step 2: Derive Your Neutral Scale

From your base surface, create 3-5 shades for hierarchy. Name them by purpose, not appearance:

- **Primary surface** → your base background
- **Secondary surface** → slightly offset for sections, sidebars, alternating areas
- **Elevated surface** → cards, containers, floating elements
- **Interactive surface** → hover and active states

For dark themes: each step adds ~5-10% lightness. You need MORE levels than light themes (at least 4).
For light themes: each step subtracts ~2-5% lightness.

Choose your own CSS custom property names that make sense for your project. Don't use the same naming scheme every time.

### Step 3: Choose Your Accent Color

Pick a single accent color that:
- Has meaning for the content OR deliberately subverts expectations
- Contrasts well against your surface (test at 4.5:1 ratio)
- Is NOT the AI default (avoid generic blue and AI purple)
- Is NOT the "anti-AI-default" default (teal/emerald have become the new AI purple — vary further)
- Is NOT in the banned accent list (see **Banned Color Reference** below)

Derive a hover state by adjusting lightness ±10%.

**Subversion principle**: If the topic strongly implies a color (blue for finance, green for health, red for food), consider whether a less obvious choice would be more distinctive. A finance dashboard in warm amber or deep indigo can be more memorable than yet another blue one.

### Step 4: Set Text Colors

Create 3 levels of text hierarchy:
- **Primary text** → high contrast against surface (≥ 7:1 for body text)
- **Secondary text** → medium contrast (≥ 4.5:1) for supporting text
- **Muted text** → lower contrast (≥ 3:1) for captions, timestamps, labels

For dark themes: white → light gray → medium gray
For light themes: near-black → dark gray → medium gray

### Step 5: Define Semantic Colors

Always include functional colors regardless of aesthetic:
- A success green that works on your surface
- A warning amber that works on your surface
- An error red that works on your surface
- A subtle border/separator color

### Step 6: Assemble as CSS Custom Properties

Define all colors in `:root` using semantic names. Choose names that reflect your project's vocabulary — there is no single correct naming convention. The goal is clarity and consistency within the project, not conformity across projects.

For dark mode: use the same property names with different values under a theme selector (`[data-theme="dark"]`, `.dark`, or `prefers-color-scheme: dark`).

---

## How to Choose Typography

### Step 1: Match Font Character to Content

| Content Type | Font Character | Why |
|-------------|---------------|-----|
| Data/analytics dashboard | Geometric sans or monospace | Precision, clarity, tabular alignment |
| Creative portfolio | Distinctive display font | Personality, memorability |
| Professional tool | Clean humanist sans | Readability, trust |
| Editorial/content | Serif or humanist sans | Reading comfort, authority |
| Developer tool | Monospace | Code familiarity, alignment |
| Playful/social | Rounded sans | Friendliness, approachability |

### Step 2: Browse Google Fonts with Intent

Go to [fonts.google.com](https://fonts.google.com) and filter by:
- Category (sans-serif, serif, monospace, display)
- Number of styles (pick fonts with 4+ weights for flexibility)
- Trending / recently updated (for freshness)

**The anti-repetition rule**: If you've used a font in a recent generation, pick a different one. Also avoid converging on the same "safe alternative" fonts (Space Grotesk, DM Sans, Outfit, Plus Jakarta Sans, Manrope) — these have become AI anti-defaults. When a Style Preset is active, use the preset's specified font instead of choosing your own.

### Step 3: Set Up the Type Scale

Build a consistent type scale. Use `clamp()` for responsive heading sizes. Key constraints:

| Level | Size Range | Weight | Line Height | Letter Spacing |
|-------|-----------|--------|-------------|----------------|
| h1 | Responsive, max ~3rem | 600-800 | 1.05-1.15 | -0.02em to -0.03em |
| h2 | Responsive, max ~2rem | 600 | 1.15-1.25 | -0.01em |
| h3 | Responsive, max ~1.25rem | 500-600 | 1.25-1.35 | normal |
| Body | 16px minimum | 400 | 1.5-1.6 | normal |
| Small | 14px | 400-500 | 1.4 | normal |
| Caption | 12px | 400-500 | 1.3 | 0.01em |

Adjust the specific values to match your design direction — airy designs use larger sizes with more spacing, dense designs use tighter scales. Don't use the exact same values every time.

### Real-World Typography References (from 73 major brands)

These are actual values extracted from production websites. Use them as calibration points, not templates. Organized by aesthetic category.

#### Minimal / Developer Platform

| Brand | Display Size | Display Weight | Display Letter-Spacing | Body Size | Body LH | Body LS |
|-------|-------------|---------------|----------------------|-----------|---------|---------|
| **Apple** | 56px | 600 | -0.28px | 17px | 1.47 | 0 |
| **Vercel** | 48px | 600 | -2.4px | 16px | 1.5 | 0 |
| **Linear** | 56px | 500 | -3px | 16px | 1.5 | 0 |
| **Expo** | 64px | 600 | -1.92px | 16px | 1.5 | 0 |
| **Ollama** | 36px | 500 | 0 | 16px | 1.5 | 0 |

#### Editorial / Magazine

| Brand | Display Size | Display Weight | Display Letter-Spacing | Body Size | Body LH | Body LS |
|-------|-------------|---------------|----------------------|-----------|---------|---------|
| **ElevenLabs** | 64px | 300 | -1.92px | 16px | 1.5 | +0.16px |
| **Mistral** | 84px | 400 | -1.5px | 16px | 1.55 | 0 |
| **Resend** | 96px | 400 | -0.96px | 16px | 1.5 | -0.8px |
| **Wired** | 64px | 400 | -0.5px | 19px (serif) | 1.47 | +0.108px |
| **Replicate** | 72px | 700 | -1.8px | 16px | 1.5 | 0 |

#### Enterprise / Infrastructure

| Brand | Display Size | Display Weight | Display Letter-Spacing | Body Size | Body LH | Body LS |
|-------|-------------|---------------|----------------------|-----------|---------|---------|
| **IBM** | 76px | 300 | -0.5px | 16px | 1.5 | +0.16px |
| **HashiCorp** | 80px | 700 | -2.5px | 16px | 1.5 | 0 |
| **HP** | 72px | 500 | 0 | 16px | 1.38 | 0 |
| **NVIDIA** | 48px | 700 | 0 | 16px | 1.5 | 0 |
| **MongoDB** | 72px | 500 | -1.5px | 16px | 1.55 | 0 |

#### Consumer / Commerce

| Brand | Display Size | Display Weight | Display Letter-Spacing | Body Size | Body LH | Body LS |
|-------|-------------|---------------|----------------------|-----------|---------|---------|
| **Airbnb** | 28px | 700 | 0 | 16px | 1.5 | 0 |
| **Uber** | 52px | 700 | 0 | 16px | 1.5 | 0 |
| **Meta** | 64px | 500 | 0 | 16px | 1.5 | -0.16px |
| **Shopify** | 96px | 330 | +2.4px | 16px | 1.5 | 0 |
| **Pinterest** | 70px | 600 | -1.2px | 16px | 1.4 | 0 |
| **Mastercard** | 64px | 500 | -1.28px | 16px | 1.4 | 0 |
| **Revolut** | 136px | 500 | -2.72px | 16px | 1.5 | +0.24px |

#### Luxury / Automotive

| Brand | Display Size | Display Weight | Display Letter-Spacing | Body Size | Body LH | Body LS |
|-------|-------------|---------------|----------------------|-----------|---------|---------|
| **Ferrari** | 80px | 500 | -1.6px | 14px | 1.5 | 0 |
| **Lamborghini** | 120px | 400 | 0 | 16px | 1.5 | 0 |
| **SpaceX** | 80px | 700 | +1.6px | 16px | 1.5 | +0.32px |
| **Renault** | 56px | 700 | 0 | 16px | 1.4 | 0 |

#### AI / Developer Tools

| Brand | Display Size | Display Weight | Display Letter-Spacing | Body Size | Body LH | Body LS |
|-------|-------------|---------------|----------------------|-----------|---------|---------|
| **MiniMax** | 80px | 600 | -2px | 16px | 1.5 | 0 |
| **Mintlify** | 72px | 600 | -2px | 16px | 1.5 | 0 |
| **Miro** | 80px | 500 | -2px | 16px | 1.5 | 0 |
| **Intercom** | 72px | 500 | -2.0px | 16px | 1.5 | 0 |
| **Sanity** | 112px | 400 | -4.48px | 16px | 1.5 | 0 |

#### Entertainment / Gaming

| Brand | Display Size | Display Weight | Display Letter-Spacing | Body Size | Body LH | Body LS |
|-------|-------------|---------------|----------------------|-----------|---------|---------|
| **PlayStation** | 54px | 300 | -0.1px | 18px | 1.5 | +0.1px |
| **The Verge** | 107px | 900 | +1.07px | 16px | 1.6 | 0 |
| **Vodafone** | 144px | 800 | -1px | 18px | 1.56 | 0 |
| **Superhuman** | 64px | 540 | 0 | 16px | 1.5 | 0 |

**Key insights from 73 brands**:
1. **85% use negative letter-spacing on display** — the range is -0.28px to -4.48px. AI skips this entirely.
2. **Display weight 400-500 is the sweet spot** — 45% of brands use this range. Only 15% use 700+.
3. **Body line-height clusters at 1.5** — with 1.4-1.55 as the full range. 1.6+ is rare outside editorial.
4. **Positive body letter-spacing is a premium signal** — IBM +0.16px, ElevenLabs +0.16px, Revolut +0.24px, SpaceX +0.32px.
5. **Display sizes go much larger than AI defaults** — Vodafone 144px, Revolut 136px, Lamborghini 120px, Sanity 112px. AI rarely exceeds 64px.

### Real-World Border-Radius References (from 73 major brands)

#### Sharp / Angular (0-4px)

| Brand | Buttons | Cards | Pills/Tags | Input Fields | Signature |
|-------|---------|-------|-----------|-------------|-----------|
| **IBM** | 0px | 0px | 0px | 0px | Carbon: everything square |
| **Ferrari** | 0px | 0px | 9999px (badge) | 4px | Luxury precision |
| **Lamborghini** | 0px | 0px | 2px | 20px (switch) | Aggressive angular |
| **NVIDIA** | 2px | 2px | 2px | 2px | Engineering grade |
| **Warp** | 3px | 3px | 9999px | 3px | Terminal aesthetic |
| **OpenCode** | 4px | 4px | 4px | 4px | Monospace discipline |

#### Moderate (6-12px)

| Brand | Buttons | Cards | Pills/Tags | Input Fields | Signature |
|-------|---------|-------|-----------|-------------|-----------|
| **Vercel** | 6px | 12px | 999px | 6px | Developer standard |
| **Expo** | 8px | 12px | 9999px | 8px | React Native standard |
| **Intercom** | 8px | 12px | 9999px | 8px | SaaS standard |
| **Mistral** | 8px | 12px | 9999px | 8px | Editorial sober |
| **Sentry** | 8px | 12px | 4px | 8px | Developer playful |
| **Kraken** | 12px | 12px | 6px | 12px | Crypto standard |

#### Soft (16-32px)

| Brand | Buttons | Cards | Pills/Tags | Input Fields | Signature |
|-------|---------|-------|-----------|-------------|-----------|
| **Apple** | 980px (pill) | 18px | 980px | 12px | Pill buttons + soft cards |
| **Airbnb** | 8px | 14px | 999px | 8px | Warm marketplace |
| **Uber** | 999px (pill) | 16px | 36px | 8px | Pill + moderate cards |
| **HP** | 4px | 16px | 9999px | 4px | Sharp buttons + soft cards |
| **Pinterest** | 16px | 16px | 9999px | 16px | Unified 16px |
| **Meta** | 100px (pill) | 32px | 100px | 8px | Pill + large cards |
| **Miro** | 9999px (pill) | 28px | 9999px | 8px | Pill + pastel cards |

#### Extreme (40px+ / Full Pill)

| Brand | Buttons | Cards | Pills/Tags | Input Fields | Signature |
|-------|---------|-------|-----------|-------------|-----------|
| **Mastercard** | 20px | 40px | 999px | 999px | Stadium shapes |
| **MiniMax** | 9999px | 32px (hero) / 16px (std) | 9999px | 8px | Dual-radius system |
| **Revolut** | 9999px | 20px | 9999px | 8px | Fintech pill |
| **MongoDB** | 9999px | 12px | 6px | 8px | Green pill + moderate cards |

**Key insights from 73 brands**:
1. **Card radius: 12px is the mode** — 35% of brands use 12px for cards. 16px is second at 20%. 24px+ is rare (~10%).
2. **Button radius is bimodal** — either sharp (0-8px, ~30%) or full pill (9999px, ~40%). The 12-16px middle ground is uncommon.
3. **The "two-tier" pattern** — many brands use sharp/moderate buttons with softer cards (HP: 4px buttons + 16px cards) or pill buttons with moderate cards (MongoDB: pill + 12px cards).
4. **0px radius = luxury/enterprise signal** — IBM, Ferrari, Lamborghini all use 0px. It reads as precision and authority.
5. **AI over-rounds everything** — AI defaults to 24px+ cards and 8-12px buttons. Real brands are either sharper or more committed to pills.

---

## How to Design Layout

### Match Layout to Content Type

| Content | Layout | Why |
|---------|--------|-----|
| Dashboard with KPIs + charts | Sidebar + grid content | Navigation always visible, data organized |
| Single-purpose tool | Top nav + centered content | Focus on the task |
| Portfolio / showcase | Full-width sections | Each project gets full attention |
| Data-heavy table view | Top nav + full-width table | Maximum horizontal space |
| Multi-panel monitoring | Bento grid | Different data types, different sizes |
| Article / documentation | Single column, max-width 65ch | Optimal reading experience |
| Marketing / landing page | Full-width sections with varied layouts | Visual storytelling |

### Layout Variety Within a Page

A page with 5+ sections must NOT repeat the same layout pattern. Audit your sections top-to-bottom:

- If section 1 is centered text, section 2 should NOT also be centered text
- If sections 2-3 alternate image-left/image-right (zigzag), section 4 must break the pattern
- Vary content width: some sections full-bleed, some contained, some narrow

### Don't Default to the Same Layout

If your last generation used a sidebar layout, try top nav or bento grid next. If it was a card grid, try a table or split panel. Variety in layout is as important as variety in color.

---

## Surface Treatments (Optional Depth)

These are techniques to add visual depth. Use 0-2 per project, not all of them. Implement fresh each time — don't copy the same code.

| Technique | What It Does | When to Use | When NOT to Use |
|-----------|-------------|-------------|-----------------|
| **Noise/grain texture** | SVG feTurbulence overlay at very low opacity on a fixed pseudo-element | Editorial, analog, luxury aesthetics | Clean/minimal designs, data-dense dashboards |
| **Gradient orbs** | Radial gradients using accent color at low opacity, positioned as fixed background | Dark tech/AI themes that need atmospheric depth | Light themes, corporate/clean designs |
| **Glass/blur cards** | `backdrop-filter: blur` with semi-transparent background and hairline border | Dark themes with layered depth, floating nav bars | Scrolling content areas (kills mobile perf), light themes |
| **Nested card (double-bezel)** | Outer shell with subtle bg + inner content card with smaller border-radius | Premium/luxury feel, hero feature cards | Every card on the page (use sparingly, 1-2 max) |
| **Subtle gradient background** | Linear or radial gradient on body, very low saturation | Pastel/soft aesthetics, wellness/education | Data dashboards, professional tools |
| **Dot grid pattern** | Repeating radial-gradient dots at low opacity | Technical/engineering aesthetics | Organic/warm designs |

**Rules**:
- Pick 0-2 treatments per project. More than 2 is visual noise.
- A clean surface with no effects is always a valid choice — often the best one.
- `backdrop-filter: blur` only on fixed/sticky elements, never on scrolling containers.
- All overlays must be `pointer-events: none` and `position: fixed`.

---

## Dark Surface Tint Guide

When the Design Dials select a dark or tinted surface (indices 2, 3, or 4), use the Scene Sentence to determine the tint direction. **NEVER default to the `#0a-#0f` blue-black range** — this is the #1 cause of AI design sameness.

### Scene-to-Tint Mapping

| Scene Environment | Tint Direction | Example Base | Example Elevated | CSS Custom Property Hint |
|-------------------|---------------|-------------|-----------------|-------------------------|
| Studio with warm lighting | Warm charcoal | `#1a1816` | `#242220` | `--surface: hsl(30, 8%, 9%)` |
| Forest cabin at night | Deep green-black | `#0f1512` | `#1a201c` | `--surface: hsl(150, 15%, 7%)` |
| Wine cellar / luxury lounge | Deep wine/burgundy | `#1a1014` | `#24181c` | `--surface: hsl(340, 25%, 8%)` |
| Industrial workshop | Warm gray-brown | `#1c1a18` | `#26241f` | `--surface: hsl(40, 8%, 10%)` |
| Cinema / theater | Pure neutral black | `#111111` | `#1a1a1a` | `--surface: hsl(0, 0%, 7%)` |
| Underwater / aquatic | Deep teal-black | `#0f1614` | `#1a211e` | `--surface: hsl(160, 20%, 7%)` |
| Desert night | Warm sand-black | `#181614` | `#22201c` | `--surface: hsl(30, 10%, 8%)` |
| Arctic / ice | Cool blue-gray | `#14161a` | `#1e2024` | `--surface: hsl(220, 12%, 9%)` |

### How to Use This Table

1. Write your Scene Sentence (see SKILL.md Step 0.5)
2. Find the closest matching environment in the table above
3. Use the example colors as a starting point, then adjust to match your specific scene
4. Derive 4+ surface levels by incrementing lightness by 5-10% per step
5. Verify all text contrast ratios against your chosen surface

### Banned Dark Surface Colors

These specific hex values are **absolutely banned** as dark surface backgrounds — they are the AI default dark mode palette:

```css
/* BANNED — AI default blue-black surfaces */
#0a0e1a    /* Most common AI deep blue-black */
#0d1117    /* GitHub-style deep blue-black */
#0f172a    /* Tailwind slate-900 */
#111827    /* Tailwind gray-900 */
#1e1b4b    /* Tailwind indigo-950 */
```

Any background color in the `#07-#0f` range with a blue hue component is suspect. If your dark surface has more blue than any other hue channel, reconsider.

---

## Banned Color Reference

A comprehensive list of colors to avoid as defaults. These are the most common AI-generated color choices across thousands of outputs.

### AI Default Accents

```css
/* BANNED as default accent — AI's go-to colors */
#3b82f6    /* Tailwind blue-500 — the #1 AI accent */
#6366f1    /* Tailwind indigo-500 */
#8b5cf6    /* Tailwind violet-500 */
#a855f7    /* Tailwind purple-500 */
```

**Exemption**: Only if the Design Read explicitly demands blue/purple (e.g., a brand whose identity IS blue), document the justification in a code comment.

### AI Default Warm Neutral Backgrounds

```css
/* BANNED as default background — 2025-2026 AI warm neutral wave */
#f5f1ea
#f7f5f1
#fbf8f1
#efeae0
#ece6db
#faf7f1
#e8dfcb
```

Any warm neutral with OKLCH L 0.84-0.97, C < 0.06, hue 40-100 falls in this category.

### AI Default Premium Accents

```css
/* BANNED as default — AI "premium-consumer" palette */
#b08947    /* brass */
#b6553a    /* clay */
#9a2436    /* oxblood */
#9c6e2a    /* ochre */
#bc7c3a    /* amber-brown */
#7d5621    /* dark gold */

/* BANNED — AI "premium" text colors */
#1a1714    /* espresso */
#1a1814    /* espresso variant */
#1b1814    /* espresso variant */
```

### Anti-Default Defaults (the trap one tier deeper)

These aren't banned outright, but be aware they are becoming the new AI defaults:

- **Teal/emerald** — has become "the new AI purple" (the go-to when told to avoid blue/purple)
- **Warm amber/gold** — becoming the "sophisticated alternative" to blue
- **Sage green** — the "calming, natural" default

When you find yourself reaching for these, ask: "Am I choosing this because it's right for the content, or because it's my safe alternative?" If the latter, explore further.

---

## Curated Color Palettes by Aesthetic Family

These are **starting points**, not templates. Pick one as inspiration, then adjust to match your specific Design Read. Never copy a palette verbatim across projects.

### Swiss/International
| Role | Light Theme | Dark Theme | Notes |
|------|------------|------------|-------|
| Surface | `#fafafa` | `#141414` | Near-white / near-black, no tint |
| Elevated | `#ffffff` | `#1e1e1e` | Pure contrast |
| Accent | `#e63946` | `#ff6b6b` | Swiss red, bold and singular |
| Text | `#1d1d1f` | `#f0f0f0` | Maximum readability |
| Muted | `#86868b` | `#8e8e93` | Functional gray |

### Neo-brutalist
| Role | Light Theme | Dark Theme | Notes |
|------|------------|------------|-------|
| Surface | `#fffdf5` | `#1a1a1a` | Warm white / true black |
| Elevated | `#ffffff` | `#2a2a2a` | With thick black borders |
| Accent | `#ff5722` | `#ff7043` | Loud, unapologetic |
| Secondary | `#ffeb3b` | `#fdd835` | Yellow highlight |
| Text | `#000000` | `#ffffff` | Pure black/white |
| Border | `#000000` (3px) | `#ffffff` (3px) | Thick, visible |

### Editorial/Magazine
| Role | Light Theme | Dark Theme | Notes |
|------|------------|------------|-------|
| Surface | `#f8f6f3` | `#1c1917` | Warm paper / warm dark |
| Elevated | `#ffffff` | `#262220` | Subtle warmth |
| Accent | `#c2452d` | `#e05a3a` | Editorial red-orange |
| Text | `#2c2825` | `#e8e2da` | Warm, not pure black |
| Caption | `#8a8078` | `#9a9088` | Warm gray |

### Soft-tech
| Role | Light Theme | Dark Theme | Notes |
|------|------------|------------|-------|
| Surface | `#f0f4ff` | `#161a2e` | Soft blue tint |
| Elevated | `#ffffff` | `#1e2240` | Gentle lift |
| Accent | `#6c5ce7` | `#a29bfe` | Soft purple |
| Secondary | `#00cec9` | `#55efc4` | Mint complement |
| Text | `#2d3436` | `#dfe6e9` | Soft contrast |
| Shadow | `rgba(108,92,231,0.08)` | `rgba(162,155,254,0.12)` | Tinted shadows |

### Industrial/Utilitarian
| Role | Light Theme | Dark Theme | Notes |
|------|------------|------------|-------|
| Surface | `#e8e6e3` | `#141413` | Concrete / carbon |
| Elevated | `#f2f0ed` | `#1c1c1a` | Subtle lift |
| Accent | `#f59e0b` | `#fbbf24` | Warning amber |
| Status Green | `#22c55e` | `#4ade80` | System go |
| Status Red | `#ef4444` | `#f87171` | System alert |
| Text | `#1c1917` | `#d4d4d4` | Functional |
| Mono | `JetBrains Mono` | `JetBrains Mono` | Monospace throughout |

### Art Deco/Geometric
| Role | Light Theme | Dark Theme | Notes |
|------|------------|------------|-------|
| Surface | `#1a1a2e` | `#0d0d1a` | Deep midnight |
| Elevated | `#25254a` | `#16162e` | Rich depth |
| Accent | `#d4af37` | `#e8c547` | True gold |
| Secondary | `#c9a96e` | `#d4b87a` | Antique brass |
| Text | `#f0e6d3` | `#e8dcc8` | Warm cream on dark |
| Pattern | `rgba(212,175,55,0.1)` | `rgba(212,175,55,0.15)` | Geometric overlays |

### Organic/Natural
| Role | Light Theme | Dark Theme | Notes |
|------|------------|------------|-------|
| Surface | `#f5f2ed` | `#1a1c18` | Parchment / forest floor |
| Elevated | `#faf8f4` | `#242620` | Natural warmth |
| Accent | `#5a7247` | `#7d9a6a` | Moss green |
| Secondary | `#c17f59` | `#d4956e` | Terracotta |
| Text | `#2d2a26` | `#e0dcd6` | Earth tone |
| Muted | `#8a8279` | `#9a9289` | Stone gray |

### Retro-futuristic
| Role | Light Theme | Dark Theme | Notes |
|------|------------|------------|-------|
| Surface | `#1a0a2e` | `#0a0518` | Deep purple-black |
| Elevated | `#2a1548` | `#150d28` | Neon-ready dark |
| Accent | `#00ff88` | `#00ff88` | Neon green |
| Secondary | `#ff006e` | `#ff3388` | Hot pink |
| Tertiary | `#00b4d8` | `#48cae4` | Cyan |
| Text | `#e0ffe8` | `#d0ffd8` | Green-tinted white |
| Glow | `0 0 20px rgba(0,255,136,0.3)` | `0 0 30px rgba(0,255,136,0.4)` | Neon glow effect |

### Minimalist/Zen
| Role | Light Theme | Dark Theme | Notes |
|------|------------|------------|-------|
| Surface | `#ffffff` | `#111111` | Pure, no tint |
| Elevated | `#fafafa` | `#1a1a1a` | Barely there |
| Accent | `#9ca3af` | `#6b7280` | Muted gray as accent |
| Text | `#374151` | `#d1d5db` | Soft, not harsh |
| Muted | `#d1d5db` | `#4b5563` | Whisper |
| Border | `#f3f4f6` | `#1f2937` | Nearly invisible |

### Data-dense/Mission Control
| Role | Light Theme | Dark Theme | Notes |
|------|------------|------------|-------|
| Surface | `#f1f3f5` | `#0c0c0e` | Cool neutral |
| Elevated | `#ffffff` | `#161618` | Panel background |
| Accent | `#3b82f6` | `#60a5fa` | Functional blue (allowed here) |
| Success | `#10b981` | `#34d399` | System nominal |
| Warning | `#f59e0b` | `#fbbf24` | Attention needed |
| Critical | `#ef4444` | `#f87171` | Alert |
| Text | `#1e293b` | `#e2e8f0` | High contrast |
| Grid | `rgba(0,0,0,0.06)` | `rgba(255,255,255,0.06)` | Panel borders |

### Playful/Toy-like
| Role | Light Theme | Dark Theme | Notes |
|------|------------|------------|-------|
| Surface | `#fff8e1` | `#1a1520` | Warm yellow / playful dark |
| Elevated | `#ffffff` | `#252030` | Bouncy cards |
| Primary | `#ff6b6b` | `#ff8a8a` | Coral red |
| Secondary | `#4ecdc4` | `#6ee7de` | Turquoise |
| Tertiary | `#ffe66d` | `#fff08a` | Sunny yellow |
| Quaternary | `#a06cd5` | `#b88ae0` | Playful purple |
| Text | `#2d3436` | `#f0eef5` | Warm dark |

### Luxury/Refined
| Role | Light Theme | Dark Theme | Notes |
|------|------------|------------|-------|
| Surface | `#0a0a0a` | `#050505` | Deep black |
| Elevated | `#141414` | `#0f0f0f` | Subtle lift |
| Accent | `#c9a55c` | `#d4b06a` | Matte gold (not shiny brass) |
| Secondary | `#8a7e6b` | `#9a8e7b` | Warm stone |
| Text | `#e8e4de` | `#f0ece6` | Warm white |
| Muted | `#6b6560` | `#7a746e` | Understated |
| Border | `rgba(201,165,92,0.15)` | `rgba(201,165,92,0.2)` | Gold whisper |

### Usage Notes

- **Light-first families** (Swiss, Editorial, Organic, Minimalist, Playful): The light theme is the "hero" — design it first, then derive the dark variant.
- **Dark-first families** (Art Deco, Retro-futuristic, Luxury, Industrial): The dark theme is the "hero" — design it first, then derive the light variant.
- **Neutral families** (Neo-brutalist, Soft-tech, Data-dense): Both themes are equally important.
- **Never use these palettes as-is** — they are starting points. Adjust hue, saturation, and lightness to match your specific Design Read and Scene Sentence.

---

## The Creativity Rule

The examples and techniques in this file are **starting points for thinking**, not templates to copy. The best designs come from:

1. Understanding the content and audience first (Design Read)
2. Choosing a color strategy level that matches the atmosphere
3. Making intentional choices for each dimension
4. Combining familiar techniques in unfamiliar ways
5. Knowing the rules well enough to break them purposefully

If you find yourself reaching for the same combination you used before, stop and explore a different direction. The goal is that every project feels like it was designed specifically for its content — not generated from a template.
