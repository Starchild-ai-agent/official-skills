# Dashboards — data, real-time, layout, performance

Use this when the visual output is a **multi-panel monitoring view** (portfolio, price tracker, system health, multi-asset comparison). It is the use-case layer on top of the general design gate. Charts setup lives in `charts.md`; visual taste lives in `design-process.md`.

Golden rule: **build the simplest dashboard that meets the requirement.** Don't over-engineer.

---

## 1. Find the data first (before any UI)

### Check Starchild's own data sources before searching outside
Starchild proxies many paid APIs for free (credentials injected by sc-proxy). Prefer a **skill** over raw HTTP whenever one exists — it has the right endpoints, auth, and quirks:

- Crypto spot/markets → `coingecko` · derivatives (funding/OI/liq) → `coinglass` · unlocks → `tokenomist`
- Stocks/forex/commodities → `twelvedata` (prices/K-line), `us-stock` / `cn-stock` (fundamentals)
- TA indicators → `taapi` · DeFi TVL/yields → `defillama` · on-chain/wallets → `debank`, `birdeye`
- Options → `massive-options-data`

To see what HTTP APIs are proxied directly (for scripts), read `core/http_client.py` (`DEFAULT_PROXIED_APIS`, `DOMAIN_TO_API_TYPE`). Always route script calls through `from core.http_client import proxied_get, proxied_post` and add a `SC-CALLER-ID` header for cost tracking. **Never fabricate numbers — every figure on a dashboard must come from a real call.**

### Premium vs free — do the rate-limit math, don't guess
```
daily_calls = (60 / update_interval_minutes) * 24 * num_assets
```
Example: 5 assets, every 2 min → 30/hr × 24 × 5 = 3,600 calls/day. If that exceeds the quota, the dashboard breaks silently — switch to a lower frequency or a free no-auth source. Decision order of preference for browser dashboards: **no-auth > API key > OAuth**. Use premium/Starchild APIs for medium/low frequency and historical OHLC; research a free alternative for high-frequency or public-facing dashboards.

When researching free APIs: check `github.com/public-apis/public-apis` first, prefer 2025-2026-maintained sources, verify CORS works in-browser, and test an endpoint before trusting a blog post. Red flags: last commit 2+ years ago, unclear limits, "free tier" needing a credit card, region locks.

---

## 2. Architecture

- **Quick static preview (most common):** HTML + CSS + JS files (split for maintainability), Tailwind via CDN, Chart.js via CDN, fetch on a timer. Apply the full Track-A design gate. Served by the static `preview`.
- **Real app:** Vite/Next + a component library (`component-libraries.md`) for the shell (sidebar, cards, tables), Chart.js/ECharts/ApexCharts for viz. Needs a `preview` with `command` + `port`.
- **Backend needed only** when you require SSE/WebSocket or server-side aggregation — otherwise keep it client-side.

Whatever the stack, drive every panel from **one fetch cycle** that returns a single data object, then update cards/charts from it. One source of truth, one refresh path.

---

## 3. Real-time updates

| Mechanism | Use when | Notes |
|-----------|----------|-------|
| **Polling** (`setInterval` + fetch) | Default for client-only dashboards; low/medium frequency | Simplest, most compatible. Always do an initial fetch immediately, then interval. |
| **SSE** (`EventSource`) | Server-to-client streaming, you control a backend | Auto-reconnects, one-way, simpler than WebSocket for dashboards. Format: `event: name\ndata: {json}\n\n`. |
| **WebSocket** | True bidirectional or sub-second latency (trading) | More work (reconnect logic); only when polling/SSE genuinely aren't enough. |

For real-time chart updates, push the new point, cap history (e.g. keep last 20-30 points by `shift()`-ing), and call the chart's update with animation disabled (`chart.update('none')`) to avoid jank.

---

## 4. Layout & UX (dashboard-specific)

- **Visual hierarchy:** most-critical metric top-left (natural eye flow), secondary top-right, detail charts center/below, filters in a top bar or sidebar.
- **Responsive grid:** mobile-first — KPI cards stack to one column < 768px, 2-up tablet, 3-4-up desktop. Use CSS Grid; let a wide chart `grid-column: span 2`.
- **KPI cards:** label + big value (`font-variant-numeric: tabular-nums`) + signed delta with color **and** an arrow/word (never color alone). Don't fake precision — round sensibly and label mock data as mock.
- **States are mandatory:** every panel needs a loading state (skeleton, not just a spinner), an error state with a retry, and an empty state with a helpful message. A dashboard that shows `0` or blank on fetch failure is a bug.
- **Density:** dashboards earn the right to be denser than landing pages, but still respect spacing rhythm and contrast from `design-process.md`. Status colors must pass contrast and pair with icon/text.

---

## 5. Performance

- Debounce `resize` before calling `chart.resize()` (~250ms).
- Decimate large series to ~100-200 points before plotting.
- Lazy-init off-screen charts with `IntersectionObserver`.
- Cache fetched data with a short TTL (e.g. 5 min) so multiple panels reusing the same source don't multiply API calls.
- In a `preview` iframe, heavy real-time canvas work can freeze the tab — throttle update frequency and keep point counts bounded.

---

## 6. Deployment / sharing

- Local view → `preview` (static for single-file; `command`+`port` for built apps).
- Public URL on Telegram/WeChat or for sharing → use the `community-publish` skill (`publish_preview`), never hand-roll hosting.
- Use **relative asset paths** in preview HTML (`./static/app.js`, not `/static/app.js`) — the proxy serves under `/preview/{id}/`.
