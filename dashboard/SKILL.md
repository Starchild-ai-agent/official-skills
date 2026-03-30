---
name: dashboard
version: 1.0.0
description: Create HTML/CSS/JS dashboards with data visualization and real-time updates
metadata:
  starchild:
    emoji: 📊
    requires:
      bins: []
    install: []
---

# Dashboard Creation Skill

Create professional HTML/CSS/JavaScript dashboards with data visualization, real-time updates, and free data source integration.

## Quick Reference

```
1. Check Star Child's built-in data sources FIRST (coingecko, twelvedata, taapi, coinglass, etc.)
2. Choose approach: Template (Tabler — fast) or Custom (full control)
3. Default chart lib: Chart.js (covers 90% of cases)
4. Real-time: SSE > WebSocket for most dashboards
5. Always mobile-first, accessible, performant
```

## Data Sources

**Check Star Child's built-in sources first** — they route through the proxy and need no extra setup:
- coingecko (crypto), twelvedata (stocks/forex), taapi (indicators), coinglass (derivatives)
- lunarcrush (social), birdeye (wallet analytics), twitter (social), 1inch (DEX)

To discover what's available: check `core/http_client.py` for `DEFAULT_PROXIED_APIS` and env vars for `*_API_KEY`.

**External free APIs** (when built-in sources don't cover it):
- Weather: OpenMeteo (no key), WeatherAPI (free tier)
- Finance: Alpha Vantage, Yahoo Finance
- General: REST Countries, Open Library, GitHub API

## Dashboard Approaches

### Tabler Template (recommended for speed)
```html
<!-- CDN: https://cdn.jsdelivr.net/npm/@tabler/core@latest -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/core@1.2.0/dist/css/tabler.min.css">
```
Pre-built components: cards, stats, grids, nav. Best when layout speed matters.

### Custom Build
Use CSS Grid/Flexbox + Chart.js. Start with `display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr))`.

## Chart Libraries

| Library | Best For | Size |
|---------|----------|------|
| **Chart.js** (default) | Bar, line, pie, doughnut — 90% of cases | 65KB |
| Lightweight Charts | Financial/candlestick | 45KB |
| ECharts | Complex/interactive | 800KB |
| D3.js | Custom/advanced viz | 90KB |

**Chart.js CDN**: `https://cdn.jsdelivr.net/npm/chart.js`

## Real-time Data

**SSE (recommended)** — simpler, auto-reconnect, sufficient for dashboards:
```javascript
const es = new EventSource('api/stream');
es.onmessage = e => updateChart(JSON.parse(e.data));
```

**Polling** — simplest, fine for <30s intervals:
```javascript
setInterval(async () => {
  const data = await fetch('api/data').then(r => r.json());
  updateDashboard(data);
}, 30000);
```

**WebSocket** — only when bidirectional communication needed.

## Design Best Practices

- **Mobile-first**: `min-width` breakpoints, touch targets ≥44px
- **Dark mode**: `prefers-color-scheme` media query, CSS variables for theming
- **Accessibility**: ARIA labels, 4.5:1 contrast ratio, keyboard navigation
- **Color-blind safe**: Don't rely on color alone — use patterns/labels. Tools: coolors.co/contrast-checker
- **Performance**: Cache API responses, debounce resize events, lazy-load below-fold content

## Workflow

```
1. Requirements → data sources, target devices, update frequency
2. Data source check → Star Child built-in first, then external APIs
3. Build structure → HTML skeleton with CSS Grid
4. Add charts → Chart.js default, alternatives if needed  
5. Connect data → Fetch API with error handling
6. Add real-time → SSE or polling
7. Polish → responsive, dark mode, loading states
8. Deploy → preview_serve for testing
```

## Common Patterns

### Fetch with Error Handling
```javascript
async function fetchData(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`${res.status}`);
    return await res.json();
  } catch (e) {
    console.error('Fetch failed:', e);
    return null;
  }
}
```

### Auto-Refresh Timer
```javascript
function startAutoRefresh(fn, interval = 60000) {
  fn(); // immediate
  return setInterval(fn, interval);
}
```

### Responsive Grid
```css
.dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; padding: 1rem; }
.card { background: var(--bg-card); border-radius: 8px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| CORS errors | Use backend proxy endpoint (preview_serve), not direct API calls |
| Chart not rendering | Ensure canvas has explicit width/height or container dimensions |
| Stale data | Add cache-busting: `url + '?t=' + Date.now()` |
| Mobile overflow | Add `overflow-x: auto` to table/chart containers |
| Dark mode flash | Set initial theme in `<head>` before CSS loads |

## Resources

- Tabler UI: https://tabler.io/
- Chart.js: https://www.chartjs.org/docs/
- Color Palettes: https://coolors.co/
- MDN Web Docs: https://developer.mozilla.org/
