# Build Patterns — Detailed Reference

## Pattern A: Scheduled Task (Cron Job)

**Use when:** User wants recurring monitoring, alerts, or reports.

**Build order (each step verified before the next):**

**Step 1 — Data fetching (verify: real data comes back)**
```python
# Write JUST the data fetching part first
import requests, os, json

def fetch_prices():
    # Use native APIs via requests (not tool calls)
    resp = requests.get("https://api.twelvedata.com/price", params={
        "symbol": "CL1,BZ1",
        "apikey": os.environ.get("TWELVEDATA_API_KEY", "")
    })
    data = resp.json()
    return data

if __name__ == "__main__":
    result = fetch_prices()
    print(json.dumps(result, indent=2))
```
Run it: `python3 tasks/{id}/run.py`
✅ Pass = real prices printed, recent timestamps
❌ Fail = fix before proceeding

**Step 2 — Data validation (verify: bad data gets caught)**
```python
def validate_price(price_str, symbol):
    """Returns (float, error). Error is None if valid."""
    try:
        price = float(price_str)
    except (ValueError, TypeError):
        return None, f"{symbol}: invalid price '{price_str}'"
    if price <= 0 or price > 500:  # reasonable range for crude oil
        return None, f"{symbol}: price {price} out of range"
    return price, None
```
Test with both good and bad inputs.

**Step 3 — Logic/analysis (verify: output format is correct)**
```python
def analyze(prices, thresholds):
    alerts = []
    for symbol, data in prices.items():
        change_pct = data["change_pct"]
        if abs(change_pct) > thresholds["alert_pct"]:
            alerts.append(f"⚠️ {symbol}: {change_pct:+.1f}%")
    return alerts
```
Test with edge cases: exactly at threshold, just above, just below.

**Step 4 — Output formatting (verify: readable, correct numbers)**
```python
# Print only when there's something actionable
output = format_report(prices, alerts)
if output.strip():
    print(output)  # Non-empty stdout → auto-pushed to user
# Empty stdout → silent, no push, no cost
```
Run full pipeline, manually verify every number in output matches raw data.

**Step 5 — Register and activate**
```python
register_task(title="WTI Monitor", schedule="0 * * * *")
# Write verified run.py to tasks/{id}/
# One final dry-run
bash("python3 tasks/{id}/run.py")
# Only then:
activate_task(job_id)
```

### Data Integrity for Tasks with LLM Analysis

**Core principle: Script owns the numbers, LLM owns the words.**

The script fetches data, the LLM analyzes/formats text. Numbers in the final output must come from script variables, NOT from LLM output. This eliminates hallucinated data entirely.

**The template pattern (recommended):**

```python
# ✅ BEST: Script builds the output, LLM only provides analysis text
prices = fetch_prices()

# Ask LLM for qualitative analysis only — no numbers in its output
analysis = llm_call(f"""Given these facts:
- WTI crude is at ${prices['wti']:.2f}, changed {prices['wti_change']:+.1f}% today
- Brent crude is at ${prices['brent']:.2f}, changed {prices['brent_change']:+.1f}% today
Write a 2-sentence market analysis. Do NOT repeat the exact prices — I will insert them myself.""")

# Script assembles final output — numbers from variables, words from LLM
output = f"""🛢️ Oil Market Update
WTI: ${prices['wti']:.2f} ({prices['wti_change']:+.1f}%)
Brent: ${prices['brent']:.2f} ({prices['brent_change']:+.1f}%)

{analysis}"""
print(output)
```

**Why this works:** Even if the LLM hallucinates, the numbers the user sees (`${prices['wti']:.2f}`) come directly from the API response variable, not from LLM text. The LLM output is sandwiched between script-controlled data.

**Fallback — when LLM must reference numbers:**

If the analysis inherently needs to mention numbers (e.g. "WTI is above Brent by $X"), use post-validation:

```python
# ✅ OK: LLM references numbers, but script validates afterward
analysis = llm_call(f"""Analyze these prices:
WTI: ${prices['wti']:.2f} | Brent: ${prices['brent']:.2f}
Use ONLY these exact numbers. Do NOT round or estimate.""")

# Post-check: verify key numbers survive
for key, val in [("WTI", prices['wti']), ("Brent", prices['brent'])]:
    if f"{val:.2f}" not in analysis:
        analysis = analysis.replace(f"${val:.0f}", f"${val:.2f}")  # fix rounding
        print(f"[WARNING] LLM may have altered {key} price", file=sys.stderr)
```

```python
# ❌ WRONG: asking LLM to fetch/know prices
prompt = "What's the current WTI oil price and analyze its trend?"
# LLM will hallucinate a number — guaranteed

# ❌ WRONG: trusting LLM output for the final number display
response = call_agent("Summarize BTC price and trends")
print(response)  # Numbers in here are unverified — user sees hallucinated data
```

### LLM Integration: Two Options

Pick the right weight class for the LLM task:

| Need | Use | Cost |
|------|-----|------|
| Simple summarize/translate/format text | **OpenRouter** (lightweight, direct API call) | ~$0.10-0.30/M tokens |
| Complex analysis needing agent tools | **localhost /chat/stream** (full agent with tools) | heavier, tool calls |

**Rule of thumb:** If the task just needs "read this text, produce that text" → OpenRouter. If it needs to call tools, search the web, or use agent capabilities → /chat/stream.

#### Option 1: OpenRouter via sc-proxy (lightweight LLM)

For simple text tasks (summarize news, translate, format reports). Uses sc-proxy, no auth needed.

```python
import os, base64, tempfile, requests, json

def setup_proxy():
    """One-time proxy setup. Call once at script start."""
    ca_pem = base64.b64decode(os.environ["STARCHILD_API_PROXY_CA_BASE64"])
    with tempfile.NamedTemporaryFile(delete=False, suffix=".crt") as f:
        f.write(ca_pem)
        ca_path = f.name
    proxy_url = f"http://[{os.environ['STARCHILD_API_PROXY_HOST']}]:{os.environ['STARCHILD_API_PROXY_PORT']}"
    return {"http": proxy_url, "https": proxy_url}, ca_path

PROXIES, CA_BUNDLE = setup_proxy()

def llm_call(prompt, model="google/gemini-2.5-flash-lite", max_tokens=1000):
    """Lightweight LLM call via OpenRouter. No agent tools, just text in → text out."""
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        proxies=PROXIES, verify=CA_BUNDLE, timeout=30,
        headers={"Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
    )
    data = resp.json()
    if "choices" not in data:
        raise RuntimeError(f"OpenRouter error: {data}")
    return data["choices"][0]["message"]["content"]
```

**Model selection for OpenRouter:**
- **Cheapest** (summaries, formatting): `google/gemini-2.5-flash-lite` ($0.10/M)
- **Balanced** (analysis, longer text): `google/gemini-2.5-flash` ($0.30/M)
- **Quality** (nuanced writing): `anthropic/claude-sonnet-4` (~$3/M)
- Browse all models: `GET https://openrouter.ai/api/v1/models` (filter by pricing)

#### Option 2: localhost /chat/stream (full agent)

For tasks that need agent capabilities (tool calls, web search, memory, complex reasoning):

```python
import requests, json, sys, os

JOB_ID = os.path.basename(os.path.dirname(os.path.abspath(__file__)))

def call_agent(message):
    resp = requests.post("http://localhost:8000/chat/stream", json={
        "message": message,
        "call_source": "task",
        "internal_options": {"job_id": JOB_ID},
    }, stream=True, timeout=30)
    reply = ""
    for line in resp.iter_lines():
        if not line or not line.startswith(b"data: "): continue
        event = json.loads(line[6:])
        if event.get("type") == "agent_complete":
            reply = (event["data"].get("reply") or "").strip(); break
        elif event.get("type") == "agent_error":
            print(event["data"].get("error"), file=sys.stderr); sys.exit(1)
    return reply
```

---

## Pattern B: Dashboard / Web UI

**Use when:** User wants a visual interface to view data or interact with something.

**Build order:**

**Step 1 — Backend data endpoint (verify: returns correct JSON)**
```python
# app.py — start with just one endpoint
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import requests, os

app = FastAPI()

@app.get("/api/data")
def get_data():
    resp = requests.get("https://api.example.com/data", ...)
    return resp.json()
```
Test: `python3 app.py &` then `curl localhost:8000/api/data`
✅ Pass = valid JSON response

**Step 2 — Minimal frontend (verify: renders in preview)**
```html
<!-- index.html — just enough to prove it connects -->
<div id="app">Loading...</div>
<script>
fetch('api/data')
  .then(r => r.json())
  .then(data => {
    document.getElementById('app').textContent = JSON.stringify(data);
  });
</script>
```
Mount in FastAPI: `app.mount("/", StaticFiles(directory="static", html=True))`
`preview_serve(dir="project", command="python3 app.py", port=8000)`
✅ Pass = `health_check.ok` is true AND data shows in browser panel

**Step 3 — Polish frontend (verify: looks right, data correct)**
Add styling, charts, layout. Verify after each significant change.

**Step 4 — Error handling and edge cases**
What happens when API is down? Empty data? Add graceful fallbacks.

### Dashboard Rules
- Frontend calls backend at relative paths: `fetch('api/data')` not `fetch('/api/data')`
- External APIs go through backend proxy endpoints, never called from frontend JS (CORS blocks it)
- Auto-refresh costs credits — default to manual refresh, let user opt into auto-refresh
- Listen on `127.0.0.1` only, never `0.0.0.0`
- Fullstack = one port: backend serves API + static files

### Visualization Library Selection

```
Simple charts (line/bar/pie)?  → Chart.js (default choice, lightweight, easy)
Beautiful real-time dashboard? → ApexCharts (smooth animations, better aesthetics)
Custom/unique visualizations?  → D3.js (maximum flexibility, steep learning curve)
Unsure?                        → Chart.js
```

| Library | CDN | Best for |
|---------|-----|----------|
| Chart.js | `cdn.jsdelivr.net/npm/chart.js` | 90% of dashboards, simple and reliable |
| ApexCharts | `cdn.jsdelivr.net/npm/apexcharts` | Real-time, annotations, beautiful defaults |
| D3.js | `d3js.org/d3.v7.min.js` | Full creative control, complex data bindling |

### Real-time Data Strategy

```
Server → client only (metrics, live data)?  → SSE (simpler, auto-reconnects)
Bidirectional (chat, collaborative)?        → WebSocket
Simple, low frequency, max compatibility?   → Polling (setInterval + fetch)
```

- **SSE** is the default for dashboards — simpler than WebSocket, auto-reconnects, works over HTTP/3
- **Polling** is the fallback when SSE/WebSocket aren't available
- Always implement fallback: SSE → polling on error

### Error Handling & Loading States

Every dashboard should handle: loading, success, error, and empty states.

```javascript
// Pattern: fetch with loading/error states
async function loadData() {
  showLoading();
  try {
    const resp = await fetch('api/data');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    if (!data || data.length === 0) {
      showEmpty("No data available");
    } else {
      renderDashboard(data);
    }
  } catch (err) {
    showError(`Failed to load: ${err.message}`);
  }
}
```

### Dashboard Design Quick Reference

- **Visual hierarchy**: critical data top-left → secondary top-right → charts center → tables bottom
- **Responsive**: mobile-first (320px → 768px → 1024px), use CSS Grid or Flexbox
- **Dark mode**: use CSS variables + `prefers-color-scheme` media query
- **Accessibility**: color-blind safe palette, ARIA labels, keyboard nav, min 44×44px touch targets
- **Performance**: debounce resize, limit data points (`decimateData`), lazy load off-screen charts

**For complete code examples** (Chart.js, ApexCharts, D3.js, SSE/WebSocket/Polling, responsive layouts, dark mode, accessibility patterns, multi-source dashboards, caching):
→ Read `references/dashboard-examples.md`

---

## Pattern C: One-off Script / Tool

**Build order:**
1. Write the script
2. Run it with test inputs
3. Verify output
4. Deliver to user

Simple scripts = single build loop cycle. Just don't skip "run and verify."

---

## Pattern D: Complex Multi-Component System

For projects with 3+ interacting components:

1. **Draw the data flow** — write it down as a numbered list, show the user
2. **Build each component in isolation** — test with hardcoded inputs
3. **Connect components one at a time** — verify each connection
4. **End-to-end test** — run the whole system, verify final output

**Never build all components at once.** The debugging cost of finding a bug in a 5-component system is 5× higher than in a 1-component system.
