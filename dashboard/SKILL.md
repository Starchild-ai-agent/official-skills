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

This skill teaches you how to create professional HTML/CSS/JavaScript dashboards with data visualization, real-time updates, and integration with free data sources. Based on 2025-2026 best practices and modern architecture patterns.

## Core Capabilities

1. **Data Source Discovery** - Research and recommend free APIs for dashboard data
2. **Dashboard Generation** - Create responsive HTML/CSS/JS dashboards
3. **Visualization Integration** - Implement charts using modern libraries
4. **Real-time Updates** - Add live data streaming with SSE or WebSocket
5. **Best Practices** - Follow 2026 UX/UI and accessibility standards

---

## 1. Data Source Discovery

When users need data sources for their dashboards, help them find appropriate free public APIs.

### Discover Star Child's Data Sources ⭐ CHECK THESE FIRST

Before searching for external APIs, discover what Star Child already has. Don't assume - check.

**How to discover available data sources:**

```bash
# 1. Check which APIs Star Child supports
read_file core/http_client.py | grep -A 15 "DEFAULT_PROXIED_APIS"

# 2. Check environment variables for configured keys
bash env | grep -i "api_key\|_key"
```

**What you're looking for in `core/http_client.py`:**
- `DEFAULT_PROXIED_APIS` - Shows which APIs have proxy support
- `DOMAIN_TO_API_TYPE` - Shows the actual domains/endpoints

**Common Star Child data sources** (as of this writing, but CHECK):
- **coingecko** - Crypto market data (Bitcoin, Ethereum, etc.)
- **twelvedata** - Stocks, forex, commodities (AAPL, EUR/USD, XAU/USD)
- **taapi** - Technical analysis indicators (RSI, MACD, etc.)
- **coinglass** - Derivatives/options data
- **lunarcrush** - Social sentiment data
- **twitterapi** - Twitter/X data
- **birdeye** - Smart money & wallet analytics
- **oneinch** - DEX aggregator

**Don't hardcode assumptions.** The list above may be outdated. Always check `core/http_client.py` to see what's actually configured.

**If an API is listed:**
1. Check if the corresponding `*_API_KEY` environment variable exists
2. Use `web_fetch` to check the API documentation (search for "{api_name} API documentation")
3. These APIs route through Star Child's proxy - you can use them directly without worrying about rate limits initially

**Example: Finding crypto data sources**
```bash
# Step 1: Check what's available
read_file core/http_client.py | grep -i "coingecko\|crypto"

# Step 2: Check if key is configured
bash env | grep COINGECKO_API_KEY

# Step 3: If found, fetch docs to understand endpoints
web_fetch "https://docs.coingecko.com/reference/endpoint-overview"
```

**Proxy Auto-Configuration Pattern:**
```javascript
// Add this at the top of your data fetching script
// (Only needed if running standalone outside the browser)
if (typeof process !== 'undefined' && process.env) {
  const proxyHost = process.env.PROXY_HOST;
  const proxyPort = process.env.PROXY_PORT || '8080';

  if (proxyHost && !process.env.HTTP_PROXY) {
    // Handle IPv6 addresses
    const host = proxyHost.includes(':') && !proxyHost.startsWith('[')
      ? `[${proxyHost}]`
      : proxyHost;
    const proxyUrl = `http://${host}:${proxyPort}`;

    process.env.HTTP_PROXY = proxyUrl;
    process.env.HTTPS_PROXY = proxyUrl;
  }
}
```

**Browser Usage (Fetch API):**
```javascript
// CoinGecko - Bitcoin price
async function fetchBitcoinPrice() {
  const response = await fetch(
    'https://pro-api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd',
    {
      headers: {
        'x-cg-pro-api-key': 'YOUR_API_KEY'  // Get from env in production
      }
    }
  );
  const data = await response.json();
  return data.bitcoin.usd;
}

// Twelve Data - Apple stock
async function fetchAppleStock() {
  const response = await fetch(
    'https://api.twelvedata.com/price?symbol=AAPL&apikey=YOUR_API_KEY'
  );
  const data = await response.json();
  return data.price;
}
```

### API Selection Decision Tree

**IMPORTANT:** Star Child's premium APIs (CoinGecko, Twelve Data) are rate-limited. Use this decision tree to determine whether to use premium or free alternatives:

```
Step 1: Identify data domain
├─ Crypto (BTC, ETH, etc.)
├─ Stocks (AAPL, MSFT, etc.)
├─ Forex (EUR/USD, etc.)
├─ Commodities (Gold, Oil)
└─ Other (Weather, News, etc.)

Step 2: Determine update frequency
├─ High-frequency (< 5 min intervals)    → Research FREE alternatives
├─ Medium-frequency (5-15 min)           → Star Child premium OK
└─ Low-frequency (> 15 min)              → Star Child premium preferred

Step 3: Assess data requirements
├─ Simple current prices                 → FREE alternatives often sufficient
├─ Historical OHLC data                  → Star Child premium if available
├─ Real-time streaming                   → Research specialized APIs
└─ Multiple data points per asset        → Consider rate limit impact

Step 4: Decision
├─ Use Star Child premium if:
│   - Update frequency is medium/low
│   - Need historical OHLC data
│   - Need reliable, clean data
│   - Total API calls < rate limit
│
└─ Research FREE alternative if:
    - High-frequency updates
    - Simple data needs (current price only)
    - Premium quota exhausted
    - Multiple assets × high frequency = too many calls
```

**Rate Limit Impact Calculator:**
```
Updates per hour = (60 / update_interval_minutes)
Assets to track = N
Daily API calls = Updates per hour × 24 × N

Example:
- 5 cryptocurrencies
- Update every 2 minutes
- Calls per hour: 60/2 = 30
- Daily calls: 30 × 24 × 5 = 3,600 calls/day

If Star Child premium limit is 1,000 calls/day → NEED FREE ALTERNATIVE
If Star Child premium limit is 10,000 calls/day → Premium OK
```

**When to Research Free Alternatives:**
1. **Calculated daily calls exceed premium API quota**
2. **User explicitly requests free/no-auth solutions**
3. **Dashboard is public-facing (many users = multiplied requests)**
4. **Prototyping/testing phase (conserve premium quota)**
5. **User doesn't have API keys configured**

### Research Philosophy for Free APIs

When premium APIs won't work (rate limits, high-frequency, user preference), your job is to find what WILL work. Not to follow a checklist, but to actually solve the problem.

**Think like this:**

The user needs data. You need to find where that data lives for free, figure out if it's reliable enough, and whether it'll actually work for their use case. Calculate the math first — if they need 3,600 calls/day and the "free" API allows 100, you haven't solved anything.

**What matters:**
- **Rate limits vs actual usage** - Don't just list the limit, calculate if it's sufficient
- **Maintenance** - A perfect API from 2022 with no updates is a timebomb
- **CORS** - Browser dashboards die without it
- **Data quality** - "Free" means nothing if the data is stale or wrong
- **Friction** - No-auth > API key > OAuth (for dashboard use cases)

**Research depth should match the stakes:**
- Quick prototype? One good option is enough.
- Production dashboard? Find 2-3 options, compare trade-offs.
- User said "find me the best"? Actually do the work.

**Where to look:**
- github.com/public-apis/public-apis (900+ APIs, check it first)
- Recent GitHub repos using similar integrations
- Developer articles from 2025-2026 (not 2022)
- API marketplace sites (rapidapi, publicapis.io)

**Red flags:**
- Last commit 2+ years ago
- Rate limits buried or unclear
- "Free tier" that requires credit card
- Only works in specific regions without mentioning it
- CORS issues mentioned in GitHub issues

**Test, don't trust:**
If you can fetch the docs or test an endpoint, do it. Don't recommend based on a blog post from 2023.
### Summary: Research-First Approach

The dashboard skill prioritizes:

1. **Calculate before choosing**: Always calculate total API calls needed based on update frequency and number of assets
2. **Premium when appropriate**: Use Star Child premium APIs for medium/low frequency and historical data
3. **Research when needed**: Deep research for high-frequency, no-auth, or specialized needs
4. **Present options**: Give users 2-4 researched options with clear trade-offs
5. **Verify freshness**: Prioritize 2025-2026 sources and active maintenance

**The agent should NEVER:**
- Recommend an API without calculating rate limit impact first
- Suggest premium APIs for high-frequency dashboards without checking quota
- Prescribe specific free APIs without researching current status
- Skip the research step when free alternatives are needed
- Recommend deprecated or unmaintained APIs

---

## 2. Dashboard Generation Approaches

### Approach A: Template-Based (RECOMMENDED for rapid development)

Use pre-built HTML dashboard templates as foundation:

**Tabler** (github.com/tabler/tabler) ⭐ RECOMMENDED
- Bootstrap 5.3 based, 40k+ GitHub stars
- 100+ responsive components, 200+ sample pages
- 5,400+ SVG icons included
- Built-in dark mode
- MIT licensed

**AdminKit** (github.com/adminkit/adminkit)
- Bootstrap 5 based, modern build pipeline
- No jQuery dependency
- Webpack, Sass, BrowserSync
- Responsive across all devices

**Implementation Steps:**
```bash
# Option 1: Download template
curl -L https://github.com/tabler/tabler/archive/refs/heads/main.zip -o tabler.zip
unzip tabler.zip
cd tabler-main/dist

# Option 2: Use via CDN (faster for prototyping)
# See code example below
```

**Tabler Quick Start:**
```html
<!DOCTYPE html>
<html>
<head>
  <title>Dashboard</title>
  <link href="https://cdn.jsdelivr.net/npm/@tabler/core@latest/dist/css/tabler.min.css" rel="stylesheet"/>
</head>
<body>
  <div class="page">
    <div class="page-wrapper">
      <div class="page-header">
        <div class="container-xl">
          <h1>My Dashboard</h1>
        </div>
      </div>
      <div class="page-body">
        <div class="container-xl">
          <div class="row row-cards">
            <!-- Cards go here -->
          </div>
        </div>
      </div>
    </div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/@tabler/core@latest/dist/js/tabler.min.js"></script>
</body>
</html>
```

### Approach B: Custom HTML/CSS/JS (worldmonitor-inspired)

For more control, build modular dashboard from scratch:

**Architecture Pattern** (inspired by worldmonitor):
```
dashboard/
├── index.html          # Main page structure
├── css/
│   ├── base.css       # Reset, typography, variables
│   ├── layout.css     # Grid, containers, responsive
│   └── components.css # Cards, charts, widgets
├── js/
│   ├── config.js      # API endpoints, settings
│   ├── data.js        # Data fetching & caching
│   ├── charts.js      # Visualization logic
│   └── main.js        # Initialization
└── assets/
    └── icons/         # SVG icons
```

**Core HTML Structure:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard</title>
  <link rel="stylesheet" href="css/base.css">
  <link rel="stylesheet" href="css/layout.css">
  <link rel="stylesheet" href="css/components.css">
</head>
<body>
  <div class="dashboard">
    <aside class="sidebar">
      <nav class="nav">
        <!-- Navigation -->
      </nav>
    </aside>

    <main class="main-content">
      <header class="header">
        <h1 class="title">Dashboard</h1>
      </header>

      <div class="grid">
        <!-- Dashboard cards -->
        <div class="card">
          <h2 class="card-title">Metrics</h2>
          <div class="card-body">
            <canvas id="chart1"></canvas>
          </div>
        </div>
      </div>
    </main>
  </div>

  <script src="js/config.js"></script>
  <script src="js/data.js"></script>
  <script src="js/charts.js"></script>
  <script src="js/main.js"></script>
</body>
</html>
```

**Responsive CSS Grid Layout:**
```css
/* Mobile-first grid */
.grid {
  display: grid;
  gap: 1.5rem;
  padding: 1.5rem;
}

/* Tablet: 2 columns */
@media (min-width: 768px) {
  .grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Desktop: 3 columns */
@media (min-width: 1024px) {
  .grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .card.wide {
    grid-column: span 2;
  }

  .card.full {
    grid-column: span 3;
  }
}
```

---

## 3. Visualization Libraries

Choose the right library based on requirements:

### Chart.js ⭐ RECOMMENDED (Default Choice)

**Best for:** Simple charts, quick implementation, good defaults
**Pros:** Easy to use, responsive, canvas-based (fast), extensive docs
**Cons:** Limited customization vs D3.js

```html
<!-- Include Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<canvas id="myChart"></canvas>

<script>
const ctx = document.getElementById('myChart').getContext('2d');
const chart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
    datasets: [{
      label: 'Sales',
      data: [12, 19, 3, 5, 2],
      borderColor: 'rgb(75, 192, 192)',
      tension: 0.1
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false
  }
});

// Update chart with new data
function updateChart(newData) {
  chart.data.datasets[0].data = newData;
  chart.update();
}
</script>
```

### ApexCharts (For Beautiful Real-time Dashboards)

**Best for:** Marketing dashboards, real-time data, aesthetics
**Pros:** Beautiful defaults, smooth animations, real-time updates, annotations
**Cons:** Slightly more complex API

```html
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>

<div id="chart"></div>

<script>
const options = {
  chart: {
    type: 'area',
    height: 350,
    animations: {
      enabled: true,
      dynamicAnimation: {
        speed: 1000
      }
    }
  },
  series: [{
    name: 'Value',
    data: [31, 40, 28, 51, 42, 109, 100]
  }],
  xaxis: {
    categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul']
  }
};

const chart = new ApexCharts(document.querySelector("#chart"), options);
chart.render();

// Real-time updates
function addDataPoint(value) {
  chart.appendData([{
    data: [value]
  }]);
}
</script>
```

### D3.js (For Custom Visualizations)

**Best for:** Custom visualizations, full creative control, complex data
**Pros:** Maximum flexibility, powerful data binding
**Cons:** Steep learning curve, more code required

**Only use D3.js when:**
- User explicitly requests custom/unique visualizations
- Standard chart types (line, bar, pie) are insufficient
- Need complex interactions or animations

```html
<script src="https://d3js.org/d3.v7.min.js"></script>

<svg id="chart" width="600" height="400"></svg>

<script>
const data = [30, 86, 168, 281, 303, 365];

const svg = d3.select("#chart");
const margin = {top: 20, right: 20, bottom: 30, left: 40};
const width = 600 - margin.left - margin.right;
const height = 400 - margin.top - margin.bottom;

const x = d3.scaleBand()
  .domain(d3.range(data.length))
  .range([0, width])
  .padding(0.1);

const y = d3.scaleLinear()
  .domain([0, d3.max(data)])
  .range([height, 0]);

const g = svg.append("g")
  .attr("transform", `translate(${margin.left},${margin.top})`);

g.selectAll(".bar")
  .data(data)
  .join("rect")
  .attr("class", "bar")
  .attr("x", (d, i) => x(i))
  .attr("y", d => y(d))
  .attr("width", x.bandwidth())
  .attr("height", d => height - y(d))
  .attr("fill", "steelblue");
</script>
```

**Library Selection Guide:**
```
User needs simple charts? → Chart.js
User needs beautiful real-time dashboard? → ApexCharts
User needs custom/unique visualizations? → D3.js
User unsure? → Chart.js (safest default)
```

---

## 4. Real-time Data Integration

### SSE (Server-Sent Events) ⭐ RECOMMENDED

**Use SSE for:** Server-to-client streaming (95% of dashboard use cases)
**Pros:** Simple, auto-reconnects, works over HTTP, better TTFB
**Cons:** Unidirectional only (server → client)

**Why SSE in 2026:**
- HTTP/3 (QUIC) eliminates head-of-line blocking
- Perfect for AI streaming, live metrics, notifications
- Simpler than WebSocket for one-way data flow
- Better for dashboard updates (no client→server messages needed)

**Client-side Implementation:**
```javascript
// Connect to SSE endpoint
const eventSource = new EventSource('/api/dashboard-updates');

// Listen for updates
eventSource.addEventListener('metric-update', (event) => {
  const data = JSON.parse(event.data);
  updateChart(data);
});

eventSource.addEventListener('error', (error) => {
  console.error('SSE error:', error);
  // Auto-reconnects by default
});

// Close connection when done
function cleanup() {
  eventSource.close();
}
```

**Server-side (if building backend):**
```python
# FastAPI example
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio
import json

app = FastAPI()

async def event_stream():
    while True:
        # Fetch latest data
        data = get_dashboard_metrics()

        # SSE format: "event: name\ndata: {json}\n\n"
        yield f"event: metric-update\ndata: {json.dumps(data)}\n\n"

        await asyncio.sleep(5)  # Update every 5 seconds

@app.get("/api/dashboard-updates")
async def stream_updates():
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )
```

### WebSocket (For Bidirectional Communication)

**Use WebSocket when:**
- User needs to send data back to server (chat, collaborative editing)
- Sub-second latency required (trading platforms, multiplayer games)
- True bidirectional communication needed

**Client-side:**
```javascript
const ws = new WebSocket('wss://api.example.com/ws');

ws.onopen = () => {
  console.log('Connected');
  ws.send(JSON.stringify({ type: 'subscribe', channel: 'metrics' }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  updateChart(data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected');
  // Implement reconnection logic
  setTimeout(connectWebSocket, 5000);
};
```

### Polling (Fallback)

**Use polling when:**
- SSE/WebSocket not available
- Simple use case with low update frequency
- Maximum compatibility needed

```javascript
async function pollData() {
  try {
    const response = await fetch('/api/metrics');
    const data = await response.json();
    updateChart(data);
  } catch (error) {
    console.error('Polling error:', error);
  }
}

// Poll every 10 seconds
setInterval(pollData, 10000);
pollData(); // Initial load
```

---

## 5. Dashboard Design Best Practices (2026)

### Visual Hierarchy

**Priority Placement:**
- Most critical data: top-left (natural eye flow)
- Secondary metrics: top-right
- Detailed charts: center and below
- Actions/filters: top or sidebar

**Example Layout:**
```html
<div class="grid">
  <!-- Top: Key metrics (full width) -->
  <div class="card full">
    <div class="metrics-row">
      <div class="metric">
        <span class="metric-label">Total Revenue</span>
        <span class="metric-value">$142,592</span>
        <span class="metric-change positive">+12.5%</span>
      </div>
      <!-- More metrics -->
    </div>
  </div>

  <!-- Middle: Charts -->
  <div class="card wide">
    <canvas id="revenue-chart"></canvas>
  </div>
  <div class="card">
    <canvas id="users-chart"></canvas>
  </div>

  <!-- Bottom: Detailed tables -->
  <div class="card full">
    <table class="data-table">
      <!-- Table content -->
    </table>
  </div>
</div>
```

### Mobile-First Responsive Design

**Approach:**
1. Design for mobile (320px) first
2. Progressive enhancement for tablet (768px+)
3. Desktop layout (1024px+)

**Key Patterns:**
```css
/* Mobile: Stack vertically */
.metrics-row {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Tablet: 2 columns */
@media (min-width: 768px) {
  .metrics-row {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .metric {
    flex: 1 1 calc(50% - 0.5rem);
  }
}

/* Desktop: 4 columns */
@media (min-width: 1024px) {
  .metric {
    flex: 1 1 calc(25% - 0.75rem);
  }
}

/* Touch-friendly controls (min 44x44px) */
.button {
  min-height: 44px;
  min-width: 44px;
  padding: 0.75rem 1.5rem;
}
```

### Accessibility

**Essential Practices:**
- Color-blind safe palettes (use patterns + color)
- ARIA labels for screen readers
- Keyboard navigation support
- Sufficient contrast ratios (WCAG AA minimum)

```html
<!-- Accessible chart wrapper -->
<div class="chart-container" role="img" aria-label="Revenue trend showing 12% growth over last quarter">
  <canvas id="chart"></canvas>

  <!-- Fallback data table for screen readers -->
  <table class="sr-only">
    <caption>Revenue Data</caption>
    <thead>
      <tr>
        <th>Month</th>
        <th>Revenue</th>
      </tr>
    </thead>
    <tbody>
      <tr><td>January</td><td>$12,000</td></tr>
      <!-- More rows -->
    </tbody>
  </table>
</div>
```

```css
/* Screen reader only class */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

/* Color-blind safe palette */
:root {
  --color-primary: #0066CC;    /* Blue */
  --color-success: #28A745;    /* Green */
  --color-warning: #FFC107;    /* Amber */
  --color-danger: #DC3545;     /* Red */
  --color-info: #17A2B8;       /* Cyan */
}
```

### Performance Optimization

**Critical Practices:**
```javascript
// 1. Debounce resize events
let resizeTimeout;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimeout);
  resizeTimeout = setTimeout(() => {
    chart.resize();
  }, 250);
});

// 2. Limit data points for large datasets
function decimateData(data, maxPoints = 100) {
  if (data.length <= maxPoints) return data;

  const step = Math.ceil(data.length / maxPoints);
  return data.filter((_, i) => i % step === 0);
}

// 3. Use RequestAnimationFrame for smooth updates
function smoothUpdate(newValue) {
  requestAnimationFrame(() => {
    updateMetric(newValue);
  });
}

// 4. Lazy load charts (Intersection Observer)
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      initializeChart(entry.target);
      observer.unobserve(entry.target);
    }
  });
});

document.querySelectorAll('.chart-container').forEach(el => {
  observer.observe(el);
});
```

### Dark Mode Support

```css
/* CSS Variables for theming */
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f8f9fa;
  --text-primary: #212529;
  --text-secondary: #6c757d;
  --border-color: #dee2e6;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary: #1a1a1a;
    --bg-secondary: #2d2d2d;
    --text-primary: #e9ecef;
    --text-secondary: #adb5bd;
    --border-color: #495057;
  }
}

body {
  background-color: var(--bg-primary);
  color: var(--text-primary);
}

.card {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
}
```

---

## 6. Complete Dashboard Example

Here's a production-ready template combining all best practices:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Live Dashboard</title>
  <link href="https://cdn.jsdelivr.net/npm/@tabler/core@latest/dist/css/tabler.min.css" rel="stylesheet"/>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    .metric-card {
      text-align: center;
      padding: 1.5rem;
    }
    .metric-value {
      font-size: 2.5rem;
      font-weight: bold;
      margin: 0.5rem 0;
    }
    .metric-change {
      font-size: 0.9rem;
      font-weight: 500;
    }
    .metric-change.positive { color: #28a745; }
    .metric-change.negative { color: #dc3545; }
    .chart-container {
      position: relative;
      height: 300px;
    }
  </style>
</head>
<body>
  <div class="page">
    <div class="page-wrapper">
      <div class="page-header">
        <div class="container-xl">
          <h1 class="page-title">Analytics Dashboard</h1>
        </div>
      </div>

      <div class="page-body">
        <div class="container-xl">
          <!-- Key Metrics -->
          <div class="row row-cards mb-3">
            <div class="col-sm-6 col-lg-3">
              <div class="card metric-card">
                <div class="metric-label text-muted">Total Users</div>
                <div class="metric-value" id="total-users">0</div>
                <div class="metric-change positive" id="users-change">+0%</div>
              </div>
            </div>
            <div class="col-sm-6 col-lg-3">
              <div class="card metric-card">
                <div class="metric-label text-muted">Revenue</div>
                <div class="metric-value" id="revenue">$0</div>
                <div class="metric-change positive" id="revenue-change">+0%</div>
              </div>
            </div>
            <div class="col-sm-6 col-lg-3">
              <div class="card metric-card">
                <div class="metric-label text-muted">Conversion</div>
                <div class="metric-value" id="conversion">0%</div>
                <div class="metric-change" id="conversion-change">+0%</div>
              </div>
            </div>
            <div class="col-sm-6 col-lg-3">
              <div class="card metric-card">
                <div class="metric-label text-muted">Active Now</div>
                <div class="metric-value" id="active">0</div>
                <div class="metric-change" id="active-change">--</div>
              </div>
            </div>
          </div>

          <!-- Charts -->
          <div class="row row-cards">
            <div class="col-lg-8">
              <div class="card">
                <div class="card-header">
                  <h3 class="card-title">Revenue Trend</h3>
                </div>
                <div class="card-body">
                  <div class="chart-container">
                    <canvas id="revenueChart"></canvas>
                  </div>
                </div>
              </div>
            </div>
            <div class="col-lg-4">
              <div class="card">
                <div class="card-header">
                  <h3 class="card-title">Traffic Sources</h3>
                </div>
                <div class="card-body">
                  <div class="chart-container">
                    <canvas id="trafficChart"></canvas>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    // Chart configurations
    const revenueChart = new Chart(document.getElementById('revenueChart'), {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Revenue',
          data: [],
          borderColor: '#0066CC',
          backgroundColor: 'rgba(0, 102, 204, 0.1)',
          tension: 0.4,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          y: { beginAtZero: true }
        }
      }
    });

    const trafficChart = new Chart(document.getElementById('trafficChart'), {
      type: 'doughnut',
      data: {
        labels: ['Direct', 'Social', 'Search', 'Referral'],
        datasets: [{
          data: [30, 25, 35, 10],
          backgroundColor: ['#0066CC', '#28A745', '#FFC107', '#DC3545']
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom' }
        }
      }
    });

    // Real-time updates with SSE
    const eventSource = new EventSource('/api/dashboard-updates');

    eventSource.addEventListener('metrics', (event) => {
      const data = JSON.parse(event.data);

      // Update metric cards
      document.getElementById('total-users').textContent = data.users.toLocaleString();
      document.getElementById('revenue').textContent = '$' + data.revenue.toLocaleString();
      document.getElementById('conversion').textContent = data.conversion + '%';
      document.getElementById('active').textContent = data.active.toLocaleString();

      // Update changes
      updateChange('users-change', data.usersChange);
      updateChange('revenue-change', data.revenueChange);
      updateChange('conversion-change', data.conversionChange);

      // Update charts
      revenueChart.data.labels.push(data.timestamp);
      revenueChart.data.datasets[0].data.push(data.revenue);

      // Keep only last 20 points
      if (revenueChart.data.labels.length > 20) {
        revenueChart.data.labels.shift();
        revenueChart.data.datasets[0].data.shift();
      }

      revenueChart.update('none'); // No animation for real-time
    });

    function updateChange(elementId, value) {
      const element = document.getElementById(elementId);
      element.textContent = (value >= 0 ? '+' : '') + value + '%';
      element.className = 'metric-change ' + (value >= 0 ? 'positive' : 'negative');
    }

    // Fallback to polling if SSE fails
    eventSource.onerror = () => {
      console.log('SSE failed, falling back to polling');
      eventSource.close();
      setInterval(fetchData, 10000);
    };

    async function fetchData() {
      try {
        const response = await fetch('/api/metrics');
        const data = await response.json();
        // Update dashboard with data
      } catch (error) {
        console.error('Fetch error:', error);
      }
    }
  </script>
</body>
</html>
```

---

## 7. Workflow for Dashboard Creation

When a user asks you to create a dashboard, follow this workflow:

### Step 1: Requirements Gathering
```markdown
Ask the user:
1. What data do you want to display? (metrics, trends, comparisons)
2. Do you have data sources already? (If no, proceed to discovery)
3. Real-time updates needed? (yes/no, update frequency)
4. Target devices? (desktop-only, mobile-first, both)
5. Preferred style? (minimal, professional, colorful)
```

### Step 2: Data Source Discovery (if needed)
```markdown
1. Identify domain(s): finance, weather, social, etc.
2. Use web_search to find appropriate APIs
3. Recommend 2-3 options with examples
4. Document API endpoints and authentication
```

### Step 3: Architecture Decision
```markdown
Choose approach:
- **Template-based (Tabler/AdminKit)**: Fast, professional, best for standard dashboards
- **Custom HTML/CSS/JS**: More control, best for unique requirements
- **Hybrid**: Template + custom visualizations

Choose visualization library:
- **Chart.js**: Default choice for most use cases
- **ApexCharts**: If real-time + beautiful aesthetics required
- **D3.js**: Only if custom visualizations explicitly needed
```

### Step 4: Implementation
```markdown
1. Create HTML structure (responsive grid layout)
2. Add CSS (mobile-first, accessibility, dark mode)
3. Integrate chart library
4. Implement data fetching (API calls)
5. Add real-time updates (SSE preferred, polling fallback)
6. Test responsiveness and accessibility
```

### Step 5: Documentation
```markdown
Provide user with:
1. Installation instructions
2. API setup guide (if external APIs used)
3. Customization options
4. How to deploy (static host, backend requirements)
```

---

## 8. Common Patterns & Recipes

### Pattern: Multi-source Dashboard

Combining data from Star Child's built-in APIs and external sources:

```javascript
// config.js
const API_CONFIG = {
  coingecko: {
    baseUrl: 'https://pro-api.coingecko.com/api/v3',
    apiKey: process.env.COINGECKO_API_KEY || 'YOUR_API_KEY'
  },
  twelvedata: {
    baseUrl: 'https://api.twelvedata.com',
    apiKey: process.env.TWELVEDATA_API_KEY || 'YOUR_API_KEY'
  },
  openMeteo: {
    baseUrl: 'https://api.open-meteo.com/v1'
  }
};

// data.js
async function fetchAllData() {
  const results = await Promise.all([
    fetchCryptoPrices(),
    fetchStockPrices(),
    fetchWeather(),
    fetchNews()
  ]);

  return {
    crypto: results[0],
    stocks: results[1],
    weather: results[2],
    news: results[3],
    timestamp: new Date().toISOString()
  };
}

// CoinGecko - Multiple crypto prices
async function fetchCryptoPrices() {
  const response = await fetch(
    `${API_CONFIG.coingecko.baseUrl}/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true`,
    {
      headers: {
        'x-cg-pro-api-key': API_CONFIG.coingecko.apiKey
      }
    }
  );

  if (!response.ok) {
    throw new Error(`CoinGecko API error: ${response.status}`);
  }

  return response.json();
}

// Twelve Data - Stock prices
async function fetchStockPrices() {
  const symbols = ['AAPL', 'MSFT', 'GOOGL'];
  const promises = symbols.map(symbol =>
    fetch(`${API_CONFIG.twelvedata.baseUrl}/price?symbol=${symbol}&apikey=${API_CONFIG.twelvedata.apiKey}`)
      .then(r => r.json())
      .then(data => ({ symbol, price: parseFloat(data.price) }))
  );

  const results = await Promise.all(promises);
  return results.reduce((acc, { symbol, price }) => {
    acc[symbol] = price;
    return acc;
  }, {});
}

// Open-Meteo - Weather (no auth required)
async function fetchWeather() {
  const params = new URLSearchParams({
    latitude: 52.52,
    longitude: 13.41,
    current_weather: true
  });

  const response = await fetch(`${API_CONFIG.openMeteo.baseUrl}/forecast?${params}`);
  return response.json();
}

// Hacker News - Tech news (no auth required)
async function fetchNews() {
  const response = await fetch('https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=5');
  return response.json();
}

// main.js
async function initializeDashboard() {
  try {
    const data = await fetchAllData();

    // Update crypto cards
    updateCryptoCard('bitcoin', data.crypto.bitcoin.usd, data.crypto.bitcoin.usd_24h_change);
    updateCryptoCard('ethereum', data.crypto.ethereum.usd, data.crypto.ethereum.usd_24h_change);
    updateCryptoCard('solana', data.crypto.solana.usd, data.crypto.solana.usd_24h_change);

    // Update stock cards
    updateStockCard('AAPL', data.stocks.AAPL);
    updateStockCard('MSFT', data.stocks.MSFT);
    updateStockCard('GOOGL', data.stocks.GOOGL);

    // Update weather widget
    updateWeatherWidget(data.weather);

    // Update news feed
    updateNewsFeed(data.news.hits);

  } catch (error) {
    console.error('Dashboard initialization failed:', error);
    showError('Failed to load dashboard data. Please try again.');
  }
}

function updateCryptoCard(coinId, price, change24h) {
  const card = document.getElementById(`crypto-${coinId}`);
  if (!card) return;

  card.querySelector('.price').textContent = '$' + price.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });

  const changeEl = card.querySelector('.change');
  const changeValue = change24h.toFixed(2);
  changeEl.textContent = (change24h >= 0 ? '+' : '') + changeValue + '%';
  changeEl.className = 'change ' + (change24h >= 0 ? 'positive' : 'negative');
}

function updateStockCard(symbol, price) {
  const card = document.getElementById(`stock-${symbol}`);
  if (!card) return;

  card.querySelector('.price').textContent = '$' + price.toFixed(2);
}

function updateWeatherWidget(weatherData) {
  const widget = document.getElementById('weather-widget');
  if (!widget) return;

  const temp = weatherData.current_weather.temperature;
  const windSpeed = weatherData.current_weather.windspeed;

  widget.querySelector('.temperature').textContent = temp + '°C';
  widget.querySelector('.wind').textContent = windSpeed + ' km/h';
}

function updateNewsFeed(newsItems) {
  const feed = document.getElementById('news-feed');
  if (!feed) return;

  feed.innerHTML = newsItems.map(item => `
    <div class="news-item">
      <a href="${item.url}" target="_blank">${item.title}</a>
      <span class="news-meta">${item.points} points • ${item.author}</span>
    </div>
  `).join('');
}

function showError(message) {
  const errorEl = document.getElementById('error-message');
  if (errorEl) {
    errorEl.textContent = message;
    errorEl.style.display = 'block';
    setTimeout(() => errorEl.style.display = 'none', 5000);
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initializeDashboard);

// Auto-refresh every 5 minutes
setInterval(initializeDashboard, 5 * 60 * 1000);
```

**HTML Structure for Multi-source Dashboard:**
```html
<div class="dashboard-grid">
  <!-- Crypto Section -->
  <div class="section">
    <h2>Cryptocurrency</h2>
    <div class="cards">
      <div class="card" id="crypto-bitcoin">
        <h3>Bitcoin</h3>
        <div class="price">$0</div>
        <div class="change">0%</div>
      </div>
      <div class="card" id="crypto-ethereum">
        <h3>Ethereum</h3>
        <div class="price">$0</div>
        <div class="change">0%</div>
      </div>
      <div class="card" id="crypto-solana">
        <h3>Solana</h3>
        <div class="price">$0</div>
        <div class="change">0%</div>
      </div>
    </div>
  </div>

  <!-- Stocks Section -->
  <div class="section">
    <h2>Stock Market</h2>
    <div class="cards">
      <div class="card" id="stock-AAPL">
        <h3>Apple</h3>
        <div class="price">$0</div>
      </div>
      <div class="card" id="stock-MSFT">
        <h3>Microsoft</h3>
        <div class="price">$0</div>
      </div>
      <div class="card" id="stock-GOOGL">
        <h3>Google</h3>
        <div class="price">$0</div>
      </div>
    </div>
  </div>

  <!-- Weather Widget -->
  <div class="card" id="weather-widget">
    <h3>Weather</h3>
    <div class="temperature">--°C</div>
    <div class="wind">-- km/h</div>
  </div>

  <!-- News Feed -->
  <div class="section">
    <h2>Tech News</h2>
    <div id="news-feed"></div>
  </div>
</div>

<div id="error-message" class="error" style="display: none;"></div>
```

### Pattern: Error Handling & Loading States

```html
<div class="card">
  <div class="card-header">
    <h3>Bitcoin Price</h3>
  </div>
  <div class="card-body">
    <!-- Loading state -->
    <div class="loading" id="crypto-loading">
      <div class="spinner"></div>
      <p>Loading...</p>
    </div>

    <!-- Error state -->
    <div class="error" id="crypto-error" style="display: none;">
      <p class="error-message"></p>
      <button onclick="retryFetch()">Retry</button>
    </div>

    <!-- Content -->
    <div class="content" id="crypto-content" style="display: none;">
      <div class="metric-value" id="btc-price">$0</div>
    </div>
  </div>
</div>

<script>
async function fetchCryptoWithStates() {
  const loadingEl = document.getElementById('crypto-loading');
  const errorEl = document.getElementById('crypto-error');
  const contentEl = document.getElementById('crypto-content');

  // Show loading
  loadingEl.style.display = 'block';
  errorEl.style.display = 'none';
  contentEl.style.display = 'none';

  try {
    const response = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd');

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    // Show content
    loadingEl.style.display = 'none';
    contentEl.style.display = 'block';

    document.getElementById('btc-price').textContent =
      '$' + data.bitcoin.usd.toLocaleString();

  } catch (error) {
    // Show error
    loadingEl.style.display = 'none';
    errorEl.style.display = 'block';
    errorEl.querySelector('.error-message').textContent =
      'Failed to load Bitcoin price: ' + error.message;
  }
}
</script>
```

### Pattern: Caching for Performance

```javascript
// Simple in-memory cache with TTL
class DataCache {
  constructor(ttlSeconds = 300) {
    this.cache = new Map();
    this.ttl = ttlSeconds * 1000;
  }

  get(key) {
    const item = this.cache.get(key);
    if (!item) return null;

    if (Date.now() > item.expires) {
      this.cache.delete(key);
      return null;
    }

    return item.data;
  }

  set(key, data) {
    this.cache.set(key, {
      data,
      expires: Date.now() + this.ttl
    });
  }

  clear() {
    this.cache.clear();
  }
}

const dataCache = new DataCache(300); // 5 minute TTL

async function fetchWithCache(url, cacheKey) {
  // Check cache first
  const cached = dataCache.get(cacheKey);
  if (cached) {
    console.log('Cache hit:', cacheKey);
    return cached;
  }

  // Fetch fresh data
  console.log('Cache miss:', cacheKey);
  const response = await fetch(url);
  const data = await response.json();

  // Store in cache
  dataCache.set(cacheKey, data);

  return data;
}

// Usage
const weather = await fetchWithCache(
  'https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current_weather=true',
  'weather-berlin'
);
```

---

## 9. Deployment & Hosting

### Static Hosting (No Backend)

If dashboard uses only client-side JavaScript and public APIs:

**Options:**
1. **GitHub Pages** - Free, simple for static sites
2. **Netlify** - Free tier, instant deploys, custom domains
3. **Vercel** - Free tier, excellent performance
4. **Cloudflare Pages** - Free, fast global CDN

**Deployment Steps (Netlify):**
```bash
# 1. Build your dashboard
mkdir my-dashboard
cd my-dashboard
# Copy your HTML/CSS/JS files

# 2. Initialize git
git init
git add .
git commit -m "Initial dashboard"

# 3. Push to GitHub
gh repo create my-dashboard --public --source=. --push

# 4. Connect to Netlify (or use drag-and-drop on netlify.com)
netlify deploy --prod
```

### With Backend (SSE/API)

If you need server-side data processing or SSE:

**Simple FastAPI Backend:**
```python
# backend/main.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import json

app = FastAPI()

# Serve static dashboard files
app.mount("/static", StaticFiles(directory="dashboard"), name="static")

@app.get("/")
async def root():
    return FileResponse("dashboard/index.html")

# SSE endpoint for real-time updates
async def event_generator():
    while True:
        # Fetch data from external APIs
        data = {
            "users": 1250,
            "revenue": 45230,
            "conversion": 3.2,
            "active": 42,
            "timestamp": "12:00"
        }

        yield f"event: metrics\ndata: {json.dumps(data)}\n\n"
        await asyncio.sleep(5)

@app.get("/api/dashboard-updates")
async def stream():
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Run with: uvicorn main:app --reload
```

**Deploy to Render/Railway/Fly.io:**
All offer free tiers for hobby projects with FastAPI support.

---

## 10. Troubleshooting

### Common Issues

**CORS Errors:**
```javascript
// If API doesn't support CORS, use a proxy
const PROXY = 'https://corsproxy.io/?';
const response = await fetch(PROXY + encodeURIComponent(apiUrl));
```

**Rate Limiting:**
```javascript
// Implement exponential backoff
async function fetchWithRetry(url, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url);

      if (response.status === 429) {
        // Rate limited, wait and retry
        const waitTime = Math.pow(2, i) * 1000;
        console.log(`Rate limited, waiting ${waitTime}ms`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
        continue;
      }

      return response;
    } catch (error) {
      if (i === maxRetries - 1) throw error;
    }
  }
}
```

**Chart Not Rendering:**
```javascript
// Ensure canvas is visible before initialization
const canvas = document.getElementById('myChart');
if (canvas.offsetParent === null) {
  // Canvas is hidden, wait for it to be visible
  const observer = new MutationObserver(() => {
    if (canvas.offsetParent !== null) {
      initializeChart();
      observer.disconnect();
    }
  });
  observer.observe(canvas.parentElement, { attributes: true });
}
```

---

## 11. Resources & References

### Official Documentation
- Chart.js: https://www.chartjs.org/docs/
- ApexCharts: https://apexcharts.com/docs/
- D3.js: https://d3js.org/
- Tabler: https://tabler.io/docs/
- Bootstrap: https://getbootstrap.com/docs/

### API Directories
- Public APIs (900+): https://github.com/public-apis/public-apis
- Free Public APIs: https://www.freepublicapis.com/
- RapidAPI Hub: https://rapidapi.com/hub

### Design Resources
- Dashboard Inspiration: https://dribbble.com/tags/dashboard
- Color Palettes: https://coolors.co/
- Icons: https://tabler-icons.io/

### Learning Resources
- MDN Web Docs: https://developer.mozilla.org/
- Web.dev (Performance): https://web.dev/
- A11y (Accessibility): https://www.a11yproject.com/

---

## Summary

When creating dashboards:

1. **Start with requirements** - Understand user needs, data sources, devices
2. **Choose wisely** - Template (Tabler) for speed, custom for control
3. **Default to Chart.js** - Simple, reliable, good for 90% of cases
4. **Use SSE for real-time** - Simpler than WebSocket for most dashboards
5. **Mobile-first always** - Design for smallest screen first
6. **Accessibility matters** - Color-blind safe, ARIA labels, keyboard nav
7. **Performance counts** - Cache data, debounce events, lazy load
8. **Help with data sources** - Research thoroughly when users need APIs

**Golden Rule:** Build the simplest dashboard that meets requirements. Don't over-engineer.
