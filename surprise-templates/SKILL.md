---
name: surprise-templates
version: 1.1.0
description: |
  Pre-built, high-quality HTML/CSS/JS templates for the Surprise Me feature.
  Agent selects a template based on user research signals, copies it to the output directory,
  applies a color theme, replaces placeholders with personalized data, and serves a preview.
tags: [surprise-me, templates, dashboard, tools, personalization]
tools: [read_file, write_file, bash, preview_serve]
triggers:
  - "[SURPRISE_ME]"
---

# Surprise Me — Template System

> This skill provides 119 pre-built templates and 20 color themes.
> The agent MUST use an existing template. Never write HTML/CSS/JS from scratch.

---

## 1. Template Selection Flow

### Step 1 — Collect User Signals

From the user research phase you will have signals such as:
- Connected data sources: `wallet`, `twitter`, `github`, `email`
- Interests: `defi`, `nft`, `trading`, `developer`, `productivity`, etc.
- Mentioned tokens, tools, or topics
- User's display language (zh-CN, en, ja, ko, etc.)
- User's avatar URL or brand color (if available)
- Previously delivered template IDs (from conversation history or user profile)

### Step 2 — Match & Randomly Select Template

Compare user signals against each template's `matchSignals` array (see §4 Template Catalog).

**Step 2a — Build candidate list:**
1. Score every template by counting how many of the user's signals appear in its `matchSignals`.
2. Keep all templates with score ≥ 2 (or ≥ 1 if fewer than 3 templates reach 2).
3. Remove any template the user has already received (see §1.1 Anti-Repeat).

**Step 2b — Randomly select from candidates:**
- Do NOT pick the first match or the highest-scored match deterministically.
- From the candidate list, **randomly select one template**. Use a mental coin-flip, current-second parity, or any non-deterministic method available to you.
- If multiple templates share the same top score, they are equally valid — pick one at random.
- The goal is: **two users with identical signals should usually get different templates**.

**Step 2c — Data source preference (tie-breaking only):**
- If you must narrow candidates further: `wallet` → prefer Category A/E; `twitter` → prefer Category C/E; `github` → prefer Category B/E.
- This is a soft preference, not a hard filter. Randomness takes priority over category preference.

**Step 2d — No-signal fallback (no wallet, no GitHub, no Twitter):**
- When the user has NO connected data sources and NO specific interest signals:
  1. Use the full Category D list (28 standalone tools) as the candidate pool.
  2. **Randomly select one** from Category D. Do not default to the same template.
  3. Additionally consider universally appealing templates: `morning-briefing`, `pomodoro`, `kanban`, `quick-notes`, `fear-greed`, `market-overview`, `crypto-quiz`.
  4. If the user has mentioned any topic at all (even casually), use it to filter Category D by `matchSignals` before random selection.

### Step 3 — Copy Template to Output

```bash
cp -r skills/surprise-templates/templates/{template-id}/ output/surprise-me/
```

### Step 4 — Randomly Select Theme & Apply

**Step 4a — Theme randomization:**
1. Consult the Theme Selection Guidelines (§5) to identify 3–5 themes that fit the template's category.
2. **Randomly pick one** from those fitting themes. Do NOT always use the first suggested theme.
3. If no category guideline applies, randomly pick from all 20 themes.
4. Vary between dark/light themes across sessions for the same user.

**Step 4b — Apply theme + placeholders:**
1. In `output/surprise-me/style.css`, replace CSS variable values with the chosen theme's `colors`
2. In `output/surprise-me/index.html`, replace `{{PLACEHOLDER}}` tokens with personalized content (see §3 Placeholder Rules)
3. Add Google Fonts `<link>` for the theme's `fonts.heading`, `fonts.body`, and `fonts.mono`
4. Update `chartColors` in `script.js` if the template uses Chart.js

### Step 5 — Personalize Beyond Placeholders

After basic placeholder replacement, apply these additional personalizations:

1. **Creative APP_TITLE** — Don't just use the template's default name. Craft a title that reflects the user's identity. Examples:
   - `"DeFi Yield Optimizer"` → `"Alex 的 DeFi 收益雷达"` or `"Alex's Alpha Farm"`
   - `"Tech Radar"` → `"Alex 的技术风向标"` or `"Alex's Stack Compass"`
   - Incorporate the user's name, interests, or style into the title.

2. **Realistic mock data** — Templates contain placeholder data (chart values, table rows, etc.). Adjust these to feel authentic:
   - If user tracks ETH/SOL, use realistic price ranges for those tokens (not $999 or $123).
   - If user is a developer, populate code snippets with languages from their tech stack.
   - Match numerical ranges to real-world values (gas fees in gwei, APY in reasonable %, etc.).

3. **Language localization** — Translate ALL visible UI text (headings, labels, buttons, tooltips, empty states) to the user's display language. This includes:
   - Navigation items, card titles, chart labels, footer text
   - Placeholder text in search bars and inputs
   - Error messages and empty state descriptions

4. **Avatar & brand color injection** (if available):
   - If user has an avatar URL, inject it as a profile image in the header/sidebar.
   - If user has a brand color, use it as `--accent-1` override on top of the selected theme.

### Step 6 — Preview Serve

```bash
cd output/surprise-me && python3 -m http.server 8080
```

Open `http://localhost:8080` to verify, then deliver to user.

---

### 1.1 Anti-Repeat Mechanism

To prevent the same user from seeing the same template on repeated "Surprise Me" requests:

1. **Check history** — Before selecting, review the conversation history for any previously delivered template IDs. Also check if the user profile stores a `surprise_history` array.
2. **Exclude seen templates** — Remove all previously delivered template IDs from the candidate list.
3. **Cycle through categories** — If the user has exhausted all templates in their best-matching category, move to the next category (e.g., A → E → D).
4. **Theme rotation** — Even if forced to reuse a template (all candidates exhausted), apply a different theme than last time.
5. **Full reset** — If all 119 templates have been shown (unlikely), reset the history and start fresh.

---

## 2. Prohibited Actions

| Rule | Detail |
|------|--------|
| **No from-scratch HTML/CSS/JS** | You MUST use an existing template. Do not create new pages from zero. |
| **No placeholder guessing** | Only replace placeholders defined in the template's `manifest.json`. |
| **No theme color hardcoding** | All colors must come from the selected theme JSON file. |
| **No API-key endpoints** | Templates only call public, CORS-enabled, key-free APIs. |
| **No emoji icons** | Templates use Lucide inline SVGs, never emoji for structural UI elements. |

---

## 3. Placeholder Replacement Rules

Each template's `manifest.json` lists its `placeholders` object. Common placeholders:

| Placeholder | Source | Example Value |
|-------------|--------|---------------|
| `{{APP_TITLE}}` | Template name or personalized title | `"Alex's Trading Dashboard"` |
| `{{USER_NAME}}` | User's display name | `"Alex"` |
| `{{WALLET_ADDRESS}}` | User's connected wallet | `"0x1234...abcd"` |
| `{{TWITTER_HANDLE}}` | User's Twitter username | `"@alexcrypto"` |
| `{{GITHUB_USERNAME}}` | User's GitHub username | `"alexdev"` |
| `{{TRACKED_TOKENS}}` | User's tokens of interest (JSON array) | `["ETH","SOL","ARB"]` |
| `{{HERO_IMAGE_URL}}` | AI-generated hero image URL or local path | `"./hero-bg.png"` |
| `{{INTERESTS}}` | User's interest keywords | `"DeFi, NFT, Layer2"` |
| `{{CITY}}` | User's city for weather/time | `"Tokyo"` |
| `{{TECH_STACK}}` | User's tech stack | `"React, TypeScript, Solidity"` |
| `{{RESEARCH_AREAS}}` | User's research interests | `"LLM, Diffusion Models"` |
| `{{COMPETITORS}}` | Competitor accounts to track | `"@competitor1, @competitor2"` |

**Rules:**
- Replace `{{PLACEHOLDER}}` literally in `index.html` (and `script.js` if referenced)
- If a placeholder value is unavailable, use a sensible default (e.g., `"Explorer"` for `USER_NAME`)
- `TRACKED_TOKENS` should be a JS array in `script.js` context, a comma-separated string in HTML context

---

## 4. Template Catalog (119 templates)

Templates are in `skills/surprise-templates/templates/{id}/`.

Each template directory contains: `index.html`, `style.css`, `script.js`, `manifest.json`, and optionally `hero-bg.png`.

### Category A — Wallet & On-Chain Analytics (32 templates)

Require `wallet` signal. Dashboards for portfolio, trading, DeFi, NFT, and on-chain data.

| ID | Name | matchSignals | Placeholders |
|----|------|-------------|--------------|
| `airdrop-checker` | Airdrop Eligibility Checker | wallet, airdrop, eligibility, claim | APP_TITLE, USER_NAME, WALLET_ADDRESS, HERO_IMAGE_URL |
| `competitor-analysis` | Competitor Token Analysis | wallet, competitor, analysis, comparison, token | APP_TITLE, USER_NAME, WALLET_ADDRESS, TRACKED_TOKENS, HERO_IMAGE_URL |
| `correlation-matrix` | Portfolio Correlation Matrix | wallet, portfolio, correlation, risk, diversification | APP_TITLE, USER_NAME, TRACKED_TOKENS, HERO_IMAGE_URL |
| `crosschain-advisor` | Cross-Chain Migration Advisor | wallet, bridge, crosschain, migration, advisor | APP_TITLE, USER_NAME, WALLET_ADDRESS, TRACKED_TOKENS, HERO_IMAGE_URL |
| `crypto-events` | Crypto Events Calendar | wallet, events, calendar, conference, upgrade | APP_TITLE, USER_NAME, WALLET_ADDRESS, TRACKED_TOKENS, HERO_IMAGE_URL |
| `defi-yield` | DeFi Yield Optimizer | wallet, defi, yield, farming, staking | APP_TITLE, USER_NAME, TRACKED_TOKENS, HERO_IMAGE_URL |
| `dex-arb` | DEX vs CEX Arbitrage | wallet, dex, cex, arbitrage, price-spread | APP_TITLE, USER_NAME, TRACKED_TOKENS, HERO_IMAGE_URL |
| `ecosystem-dashboard` | Ecosystem Dashboard | wallet, ecosystem, chain, base, arbitrum | APP_TITLE, USER_NAME, WALLET_ADDRESS, TRACKED_TOKENS, HERO_IMAGE_URL |
| `funding-rate` | Funding Rate Dashboard | wallet, funding-rate, perpetual, futures, arbitrage | APP_TITLE, USER_NAME, TRACKED_TOKENS, HERO_IMAGE_URL |
| `gas-tracker` | Gas Fee Tracker | wallet, gas, ethereum, transaction | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `impermanent-loss` | Impermanent Loss Calculator | wallet, defi, impermanent-loss, liquidity, calculator | APP_TITLE, USER_NAME, TRACKED_TOKENS, HERO_IMAGE_URL |
| `liquidation-heatmap` | Liquidation Heatmap | wallet, liquidation, leverage, risk, futures | APP_TITLE, USER_NAME, TRACKED_TOKENS, HERO_IMAGE_URL |
| `market-cycle` | Market Cycle Indicators | wallet, market-cycle, macro, indicator, phase | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `meme-radar` | Meme Coin Radar | wallet, meme, degen, trending, social | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `nft-gallery` | NFT Collection Gallery | wallet, nft, collection, gallery, art | APP_TITLE, USER_NAME, WALLET_ADDRESS, HERO_IMAGE_URL |
| `nft-market-trends` | NFT Market Trends | wallet, nft, market, trends, analytics | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `nft-rarity` | NFT Rarity Explorer | wallet, nft, rarity, collection, traits | APP_TITLE, USER_NAME, WALLET_ADDRESS, HERO_IMAGE_URL |
| `onchain-timeline` | On-Chain Activity Timeline | wallet, onchain, history, timeline, activity | APP_TITLE, USER_NAME, WALLET_ADDRESS, HERO_IMAGE_URL |
| `personalized-news` | Personalized Crypto News Feed | wallet, news, personalized, crypto, feed | APP_TITLE, USER_NAME, WALLET_ADDRESS, TRACKED_TOKENS, HERO_IMAGE_URL |
| `portfolio-radar` | Portfolio Risk Radar | wallet, portfolio, investment, risk, allocation, diversification | APP_TITLE, USER_NAME, TRACKED_TOKENS, HERO_IMAGE_URL |
| `portfolio-timemachine` | Portfolio Time Machine | wallet, portfolio, investment, historical | APP_TITLE, USER_NAME, TRACKED_TOKENS, PORTFOLIO_VALUE, HERO_IMAGE_URL |
| `protocol-risk` | Protocol Risk Exposure Map | wallet, defi, protocol, risk, exposure | APP_TITLE, USER_NAME, WALLET_ADDRESS, HERO_IMAGE_URL |
| `regulation-tracker` | Crypto Regulation Tracker | wallet, regulation, compliance, legal, news | APP_TITLE, USER_NAME, WALLET_ADDRESS, TRACKED_TOKENS, HERO_IMAGE_URL |
| `smart-money` | Smart Money Tracker | wallet, smart-money, whale, institutional, tracking | APP_TITLE, USER_NAME, TRACKED_TOKENS, WALLET_ADDRESS, HERO_IMAGE_URL |
| `stablecoin-yield` | Stablecoin Yield Comparison | wallet, stablecoin, yield, apy, comparison | APP_TITLE, USER_NAME, WALLET_ADDRESS, TRACKED_TOKENS, HERO_IMAGE_URL |
| `token-momentum` | Token Momentum Scanner | wallet, momentum, rsi, macd, technical-analysis | APP_TITLE, USER_NAME, TRACKED_TOKENS, HERO_IMAGE_URL |
| `token-sentiment` | Token Sentiment Indicators | wallet, sentiment, fear-greed, token, mood | APP_TITLE, USER_NAME, WALLET_ADDRESS, TRACKED_TOKENS, HERO_IMAGE_URL |
| `token-unlock` | Token Unlock Calendar | wallet, token, unlock, vesting, calendar | APP_TITLE, USER_NAME, TRACKED_TOKENS, HERO_IMAGE_URL |
| `trading-intel` | Trading Intelligence Dashboard | wallet, defi, trading, crypto, token | APP_TITLE, USER_NAME, WALLET_ADDRESS, TRACKED_TOKENS, HERO_IMAGE_URL |
| `whale-alert` | Whale Alert Monitor | wallet, whale, alert, large-transfer, monitoring | APP_TITLE, USER_NAME, TRACKED_TOKENS, HERO_IMAGE_URL |
| `whale-comparison` | Whale Comparison Dashboard | wallet, whale, defi, portfolio | APP_TITLE, USER_NAME, WALLET_ADDRESS, HERO_IMAGE_URL |

### Category B — Developer & GitHub Tools (23 templates)

Require `github` signal. Tools for developers, code references, and tech exploration.

| ID | Name | matchSignals | Placeholders |
|----|------|-------------|--------------|
| `api-playground` | API Playground | github, api, testing, playground, http | APP_TITLE, BASE_URL, DEFAULT_HEADERS |
| `blockchain-toolkit` | Blockchain Dev Toolkit | github, blockchain, tools, development, reference | APP_TITLE, PREFERRED_CHAIN, DEV_LEVEL |
| `code-snippets` | Code Snippet Library | github, code, snippets, patterns, reference | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `color-scheme` | Color Scheme Generator | github, design, color, palette, css | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `css-playground` | CSS Animation Playground | github, css, animation, frontend, playground | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `dapp-ideas` | DApp Idea Generator | github, dapp, ideas, web3, creative | APP_TITLE, PREFERRED_CHAIN, INTEREST_AREA |
| `dependency-monitor` | Dependency Update Monitor | github, dependencies, security, updates, npm | APP_TITLE, USER_NAME, GITHUB_USERNAME, HERO_IMAGE_URL |
| `framework-migration` | Framework Migration Guide | github, framework, migration, upgrade, guide | APP_TITLE, SOURCE_FRAMEWORK, TARGET_FRAMEWORK, PROJECT_NAME |
| `gas-optimization` | Gas Optimization Cheatsheet | github, solidity, gas, optimization, reference | APP_TITLE, SOLIDITY_VERSION, TARGET_CHAIN |
| `github-stars` | GitHub Stars Explorer | github, stars, repositories, analysis, interests | APP_TITLE, USER_NAME, GITHUB_USERNAME, HERO_IMAGE_URL |
| `hackathon-matcher` | Hackathon Matcher | github, hackathon, competition, team, events | APP_TITLE, USER_NAME, TECH_STACK, HERO_IMAGE_URL |
| `indie-dev` | Indie Developer Dashboard | github, indie, startup, saas, solo-developer | APP_TITLE, USER_NAME, TECH_STACK, HERO_IMAGE_URL |
| `interview-prep` | Technical Interview Prep | github, interview, preparation, coding, algorithms | APP_TITLE, USER_NAME, TECH_STACK, HERO_IMAGE_URL |
| `learning-path` | Learning Path Generator | github, learning, path, skills, education | APP_TITLE, TECH_STACK, USER_LEVEL |
| `opensource-finder` | Open Source Opportunity Finder | github, opensource, contribution, good-first-issue, community | APP_TITLE, USER_NAME, GITHUB_USERNAME, TECH_STACK, HERO_IMAGE_URL |
| `opensource-monetize` | Open Source Monetization Guide | github, opensource, monetization, revenue, business | APP_TITLE, PROJECT_NAME, GITHUB_STARS |
| `producthunt-tracker` | Product Hunt Tracker | github, producthunt, launches, products, trending | APP_TITLE, FOCUS_CATEGORIES, USER_NAME |
| `regex-tester` | Regex Pattern Tester | github, regex, pattern, testing, developer | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `side-project-ideas` | Side Project Idea Generator | github, ideas, project, creative, generator | APP_TITLE, TECH_PREFERENCES, DIFFICULTY |
| `smart-contract-scanner` | Smart Contract Security Scanner | github, solidity, smart-contract, security, audit | APP_TITLE, USER_NAME, CONTRACT_ADDRESS, HERO_IMAGE_URL |
| `tech-blogs` | Tech Blog Aggregator | github, blog, articles, reading, tech | APP_TITLE, FEED_TOPICS, USER_NAME |
| `tech-conferences` | Tech Conference Finder | github, conference, events, tech, meetup | APP_TITLE, FOCUS_TOPICS, REGION |
| `tech-radar` | Tech Stack Trend Radar | github, developer, programming, code, tech, stack, framework | APP_TITLE, USER_NAME, TECH_STACK, GITHUB_USERNAME, HERO_IMAGE_URL |
| `web3-jobs` | Web3 Job Board | github, web3, jobs, remote, hiring | APP_TITLE, PREFERRED_CHAINS, USER_SKILLS |

### Category C — Twitter & Social Intelligence (18 templates)

Require `twitter` signal. Social analytics, content strategy, and trend tracking.

| ID | Name | matchSignals | Placeholders |
|----|------|-------------|--------------|
| `ai-research` | AI Research Digest | twitter, ai, research, papers, models | APP_TITLE, USER_NAME, RESEARCH_AREAS |
| `airdrop-intel` | Airdrop Intel Feed | twitter, airdrop, intel, alpha, opportunities | APP_TITLE, USER_NAME |
| `competitor-monitor` | Competitor Monitor | twitter, competitor, monitoring, social, tracking | APP_TITLE, USER_NAME, COMPETITORS |
| `content-calendar` | Content Calendar — Posting Strategy | twitter, content, calendar, schedule, posting | APP_TITLE, USER_NAME, TWITTER_HANDLE, HERO_IMAGE_URL |
| `ct-alpha` | CT Alpha Feed | twitter, crypto-twitter, alpha, signals, defi | APP_TITLE, USER_NAME, TWITTER_HANDLE, TRACKED_TOKENS, HERO_IMAGE_URL |
| `devtools-radar` | Developer Tools Radar | twitter, devtools, releases, updates, radar | APP_TITLE, USER_NAME |
| `event-tracker` | Event Tracker | twitter, events, tracking, upcoming, calendar | APP_TITLE, USER_NAME, EVENT_TYPES |
| `industry-news` | Industry News Radar | twitter, news, industry, realtime, feed | APP_TITLE, USER_NAME, INDUSTRIES |
| `interest-radar` | Interest Radar — Topic Analysis | twitter, interests, topics, content, radar | APP_TITLE, USER_NAME, TWITTER_HANDLE, HERO_IMAGE_URL |
| `kol-tracker` | KOL Tracker | twitter, kol, influencer, opinion-leader, tracking | APP_TITLE, USER_NAME, TWITTER_HANDLE, HERO_IMAGE_URL |
| `narrative-tracker` | Narrative Tracker | twitter, narrative, trend, crypto, macro | APP_TITLE, USER_NAME, TWITTER_HANDLE, HERO_IMAGE_URL |
| `remote-jobs` | Remote Job Board | twitter, remote, jobs, work, hiring | APP_TITLE, USER_NAME, SKILLS |
| `social-graph` | Social Graph — Network Analysis | twitter, social, network, connections, graph | APP_TITLE, USER_NAME, TWITTER_HANDLE, HERO_IMAGE_URL |
| `startup-funding` | Startup Funding Tracker | twitter, startup, funding, investment, venture | APP_TITLE, USER_NAME |
| `tech-launches` | Tech Product Launch Feed | twitter, producthunt, hackernews, launches, tech | APP_TITLE, USER_NAME |
| `thread-ideas` | Thread Ideas Generator | twitter, thread, ideas, content, writing | APP_TITLE, USER_NAME, NICHE |
| `token-launches` | Token Launch Tracker | twitter, launch, ido, token-sale, upcoming | APP_TITLE, USER_NAME |
| `token-mentions` | Token Mentions Tracker | twitter, token, mentions, kol, tracking | APP_TITLE, USER_NAME, TRACKED_TOKENS |
| `topic-dashboard` | Trending Topics Dashboard | twitter, trending, topics, news, dashboard | APP_TITLE, USER_NAME, TWITTER_HANDLE, HERO_IMAGE_URL |
| `viral-analyzer` | Viral Tweet Analyzer | twitter, viral, engagement, analytics, growth | APP_TITLE, USER_NAME, TWITTER_HANDLE, HERO_IMAGE_URL |

### Category D — Standalone Tools & Utilities (28 templates)

No specific data source required. General-purpose tools, calculators, and utilities.

| ID | Name | matchSignals | Placeholders |
|----|------|-------------|--------------|
| `ascii-art` | ASCII Art Generator | tool, ascii, art, text, generator | APP_TITLE, HERO_IMAGE_URL |
| `block-explorer-lite` | Block Explorer Lite | blockchain, explorer, address, transaction, search | APP_TITLE, DEFAULT_CHAIN, HERO_IMAGE_URL |
| `bookmark-manager` | Bookmark Manager | productivity, bookmarks, organize, links, reading | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `contract-reader` | Smart Contract Reader | blockchain, contract, abi, reader, tool | APP_TITLE, HERO_IMAGE_URL |
| `cron-builder` | Cron Expression Builder | developer, cron, scheduler, expression, tool | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `crypto-quiz` | Crypto Knowledge Quiz | education, quiz, crypto, knowledge, game | APP_TITLE, HERO_IMAGE_URL |
| `dca-calculator` | DCA Calculator | calculator, dca, investment, strategy, crypto | APP_TITLE, USER_NAME, TRACKED_TOKENS, HERO_IMAGE_URL |
| `defi-compare` | DeFi Protocol Comparison | defi, compare, protocol, tvl, apy | APP_TITLE, HERO_IMAGE_URL |
| `fear-greed` | Crypto Fear & Greed Index | crypto, market, sentiment, fear, greed, bitcoin | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `habit-tracker` | Habit Tracker | productivity, habits, tracking, streak, daily | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `ico-calendar` | ICO/IDO Calendar | calendar, ico, ido, token-sale, upcoming | APP_TITLE, HERO_IMAGE_URL |
| `json-formatter` | JSON Formatter & Validator | productivity, json, formatter, validator, developer | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `kanban` | Kanban Board | productivity, kanban, tasks, project, board | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `markdown-editor` | Markdown Editor | productivity, markdown, editor, writing, documentation | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `market-overview` | Market Overview Dashboard | market, overview, crypto, stocks, forex | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `meme-generator` | Meme Generator | tool, meme, generator, image, fun | APP_TITLE, HERO_IMAGE_URL |
| `morning-briefing` | Morning Intelligence Briefing | news, briefing, morning, daily, summary, update, digest | APP_TITLE, USER_NAME, INTERESTS, CITY, HERO_IMAGE_URL |
| `password-gen` | Password Generator | productivity, password, security, generator, tool | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `pixel-editor` | Pixel Art Editor | tool, pixel, art, editor, creative | APP_TITLE, HERO_IMAGE_URL |
| `pnl-calculator` | P&L Calculator | calculator, pnl, profit-loss, trading, crypto | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `pomodoro` | Pomodoro Timer | productivity, timer, pomodoro, focus, task | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `qrcode-gen` | QR Code Generator | productivity, qrcode, generator, tool, share | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `quick-notes` | Quick Notes | productivity, notes, markdown, quick, writing | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `staking-yield` | Staking Yield Calculator | calculator, staking, yield, apy, comparison | APP_TITLE, DEFAULT_TOKEN, HERO_IMAGE_URL |
| `tax-estimator` | Crypto Tax Estimator | calculator, tax, crypto, estimation, tool | APP_TITLE, DEFAULT_COUNTRY, HERO_IMAGE_URL |
| `timezone-converter` | Timezone Converter | productivity, timezone, converter, remote, global | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `token-compare` | Token Compare Tool | compare, token, analysis, market-cap, tvl | APP_TITLE, USER_NAME, TRACKED_TOKENS, HERO_IMAGE_URL |
| `typing-test` | Typing Speed Test | productivity, typing, speed, test, keyboard | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `unit-converter` | Unit Converter | productivity, converter, units, currency, tool | APP_TITLE, DEFAULT_CATEGORY, HERO_IMAGE_URL |
| `web3-glossary` | Web3 Glossary | web3, glossary, terms, education, reference | APP_TITLE, USER_NAME, HERO_IMAGE_URL |

### Category E — Multi-Source & Cross-Platform (16 templates)

Require 2+ data sources (e.g., `wallet` + `twitter`, `github` + `twitter`). Rich, multi-dimensional dashboards.

| ID | Name | matchSignals | Placeholders |
|----|------|-------------|--------------|
| `ai-builder` | AI Builder Toolkit | twitter, github, ai, machine-learning, developer | APP_TITLE, USER_NAME, GITHUB_USERNAME, HERO_IMAGE_URL |
| `alpha-signal` | Alpha Signal Board | twitter, wallet, alpha, signal, trading | APP_TITLE, USER_NAME, TWITTER_HANDLE, WALLET_ADDRESS, HERO_IMAGE_URL |
| `creator-analytics` | Creator Analytics Dashboard | twitter, github, creator, analytics, content | APP_TITLE, USER_NAME, TWITTER_HANDLE, GITHUB_USERNAME, HERO_IMAGE_URL |
| `crosschain-bridge` | Cross-Chain Bridge Optimizer | wallet, bridge, crosschain, multichain, transfer | APP_TITLE, USER_NAME, WALLET_ADDRESS, HERO_IMAGE_URL |
| `defi-dev-console` | DeFi Developer Console | github, wallet, defi, solidity, developer | APP_TITLE, USER_NAME, GITHUB_USERNAME, WALLET_ADDRESS, HERO_IMAGE_URL |
| `dev-brand` | Developer Brand Page | github, twitter, brand, portfolio, developer | APP_TITLE, USER_NAME, GITHUB_USERNAME, TWITTER_HANDLE, HERO_IMAGE_URL |
| `efficiency-hub` | Efficiency & Finance Hub | wallet, email, calendar, portfolio, productivity | APP_TITLE, USER_NAME, WALLET_ADDRESS, TRACKED_TOKENS, HERO_IMAGE_URL |
| `enterprise-intel` | Enterprise Intelligence Dashboard | email, twitter, enterprise, competitor, intelligence | APP_TITLE, USER_NAME, COMPANY_NAME, HERO_IMAGE_URL |
| `ml-tracker` | ML Experiment Tracker | github, twitter, ml, experiment, python | APP_TITLE, USER_NAME, GITHUB_USERNAME, HERO_IMAGE_URL |
| `nft-community` | NFT Community Radar | wallet, twitter, nft, community, social | APP_TITLE, USER_NAME, WALLET_ADDRESS, TWITTER_HANDLE, HERO_IMAGE_URL |
| `solana-radar` | Solana Ecosystem Radar | wallet, twitter, solana, ecosystem, defi | APP_TITLE, USER_NAME, WALLET_ADDRESS, HERO_IMAGE_URL |
| `starchild-demo` | Starchild Capabilities Showcase | starchild, demo, showcase, capabilities, features | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `ui-components` | UI Components Gallery | github, frontend, ui, components, design | APP_TITLE, USER_NAME, HERO_IMAGE_URL |
| `web3-builder` | Web3 Builder Dashboard | github, wallet, web3, builder, developer | APP_TITLE, USER_NAME, GITHUB_USERNAME, WALLET_ADDRESS, HERO_IMAGE_URL |

---

## 5. Theme Catalog (20 themes)

Theme files are in `skills/surprise-templates/themes/{id}.json`.

Each theme JSON contains:
- `colors` — CSS variable values (`--bg-primary`, `--bg-secondary`, `--bg-card`, `--text-primary`, `--text-secondary`, `--accent-1`, `--accent-2`, `--accent-3`, `--border`, `--glow`, `--gradient-hero`)
- `fonts` — `heading`, `body`, `mono` font families
- `chartColors` — array of 6 hex colors for Chart.js

### Dark Themes (13)

| ID | Name | Vibe |
|----|------|------|
| `cyber-neon` | Cyber Neon | Cyberpunk — deep black + neon green/purple |
| `ocean-depth` | Ocean Depth | Deep sea — dark blue + cyan/coral |
| `midnight-gold` | Midnight Gold | Luxury finance — midnight blue + gold/amber |
| `aurora-borealis` | Aurora Borealis | Northern lights — deep purple + aurora green/pink |
| `forest-canopy` | Forest Canopy | Forest — dark green + moss/amber |
| `volcanic-ember` | Volcanic Ember | Volcanic — dark gray + lava red/orange |
| `neon-tokyo` | Neon Tokyo | Tokyo neon — pure black + neon pink/cyan |
| `deep-space` | Deep Space | Space — space black + nebula purple/blue |
| `coral-reef` | Coral Reef | Coral reef — dark teal + coral/gold |
| `industrial-steel` | Industrial Steel | Industrial — steel gray + orange/white |
| `electric-blue` | Electric Blue | Electric — dark blue + electric blue/white |
| `rose-gold` | Rose Gold | Rose gold — dark rose + rose gold/white |
| `matrix-green` | Matrix Green | Matrix — pure black + matrix green/dark green |

### Light Themes (5)

| ID | Name | Vibe |
|----|------|------|
| `arctic-frost` | Arctic Frost | Arctic — ice white + ice blue/silver |
| `lavender-dream` | Lavender Dream | Lavender — light purple + lavender/rose |
| `desert-sand` | Desert Sand | Desert — sand + ochre/sky blue |
| `paper-ink` | Paper & Ink | Paper — paper white + ink black/red |
| `candy-pop` | Candy Pop | Candy — pink white + candy colors/bright |

### Monochrome (2)

| ID | Name | Vibe |
|----|------|------|
| `monochrome-noir` | Monochrome Noir | Black & white + single accent color |
| `sunset-gradient` | Sunset Gradient | Warm orange + pink-purple/gold |

### Theme Selection Guidelines

- **Crypto/trading dashboards** → `cyber-neon`, `neon-tokyo`, `midnight-gold`, `deep-space`
- **Developer tools** → `matrix-green`, `industrial-steel`, `paper-ink`
- **Productivity/utilities** → `arctic-frost`, `lavender-dream`, `desert-sand`
- **NFT/creative** → `aurora-borealis`, `coral-reef`, `sunset-gradient`
- **Finance/enterprise** → `midnight-gold`, `monochrome-noir`, `rose-gold`
- **Fun/casual** → `candy-pop`, `volcanic-ember`, `ocean-depth`

---

## 6. How to Apply a Theme

Read the theme JSON file and replace CSS variables in `style.css`:

```bash
# Example: applying cyber-neon theme
THEME=$(cat skills/surprise-templates/themes/cyber-neon.json)
```

In `style.css`, find the `:root { ... }` block and replace each CSS variable value:

```css
:root {
  --bg-primary: #0a0a0f;       /* from theme.colors.--bg-primary */
  --bg-secondary: #12121a;     /* from theme.colors.--bg-secondary */
  --bg-card: rgba(18,18,26,0.85);
  --text-primary: #e0e0e8;
  --text-secondary: #8888a0;
  --accent-1: #39ff14;
  --accent-2: #bf00ff;
  --accent-3: #00e5ff;
  --border: rgba(57,255,20,0.15);
  --glow: 0 0 20px rgba(57,255,20,0.3), 0 0 60px rgba(57,255,20,0.1);
  --gradient-hero: linear-gradient(135deg, #0a0a0f 0%, #1a0a2e 50%, #0a0a0f 100%);
}
```

Also update the font `<link>` in `index.html`:

```html
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

And update `chartColors` in `script.js` where Chart.js datasets reference colors.

---

## 7. Quick Reference — End-to-End Example

### Example A — User with signals

```
User signals: wallet connected, interests = ["defi", "yield"], tokens = ["ETH", "AAVE"]
Language: zh-CN, Avatar: https://example.com/alex.png
History: previously received "trading-intel"

1. Build candidates → score all templates against ["wallet", "defi", "yield"]
   Candidates (score ≥ 2): defi-yield(3), stablecoin-yield(2), impermanent-loss(2),
   funding-rate(2), dex-arb(2), portfolio-radar(2)
   Exclude history: trading-intel (already seen)
2. Random select → impermanent-loss (randomly picked from 6 candidates)
3. Copy  → cp -r templates/impermanent-loss/ output/surprise-me/
4. Random theme → from [midnight-gold, cyber-neon, deep-space, neon-tokyo],
   randomly pick → deep-space
5. Replace placeholders:
   - {{APP_TITLE}} → "Alex 的无常损失计算器" (creative, localized title)
   - {{USER_NAME}} → "Alex"
   - {{TRACKED_TOKENS}} → ["ETH", "AAVE"]
   - {{HERO_IMAGE_URL}} → "./hero-bg.png"
6. Personalize beyond placeholders:
   - Translate all UI labels to zh-CN (按钮、标题、图表标签)
   - Inject avatar as profile image in header
   - Adjust mock data: use realistic ETH/AAVE price ranges
7. Apply theme colors to style.css :root block
8. Add Google Fonts link for theme fonts
9. Serve → cd output/surprise-me && python3 -m http.server 8080
```

### Example B — User with no signals (fallback)

```
User signals: none (no wallet, no GitHub, no Twitter, no specific interests)
Language: en

1. No matching signals → use Category D (28 standalone tools) as candidate pool
2. Random select → pomodoro (randomly picked from 28 candidates)
3. Copy  → cp -r templates/pomodoro/ output/surprise-me/
4. Random theme → from all 20 themes, randomly pick → lavender-dream
5. Replace placeholders:
   - {{APP_TITLE}} → "Your Focus Timer" (creative title)
   - {{USER_NAME}} → "Explorer"
   - {{HERO_IMAGE_URL}} → "./hero-bg.png"
6. Personalize: adjust default session durations, translate if needed
7. Apply theme + fonts
8. Serve → cd output/surprise-me && python3 -m http.server 8080
```
