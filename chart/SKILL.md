---
name: chart
version: 3.0.3
description: |
  Interactive web charts: line, bar, candle, scatter, with HTML and screenshot output.

  Use when visualizing data for analysis or BI (e.g. plot BTC vs gold last year, bar chart of revenue by quarter, compare two return series).

metadata:
  starchild:
    emoji: "📊"
    skillKey: chart

user-invocable: true
disable-model-invocation: false

---

# Chart — Project-Based Interactive Charting

Generate interactive chart pages with Apache ECharts. Each chart lives in a dedicated project folder under `output/chart-html/`, making it easy to reuse and iterate.

## When to Use

Any time the user wants a visual chart: price charts, comparisons, dashboards, business analytics, etc.

## Architecture

- **ECharts** (CDN) for rendering
- **ECharts native export (`getDataURL`) + canvas merge** for reliable PNG output
- **Project-based storage**: one folder per chart project
- **No gallery mode**: all artifacts stay in the project folder

## Project Structure (Required)

Each chart project should follow:

```
output/chart-html/
  <project-name>/
    index.html        # chart page
    generate.py       # generation script (for reproducibility)
    README.md         # title / description / data source notes
    data.json         # data snapshot
    screenshot.png    # saved image
```

Example folder name: `btc-90d-20260401`

## Workflow

### Step 1: Pick template or custom layout

Available templates:

| Template | Best for |
|---|---|
| `line.html` | Time-series trends, multi-series comparisons |
| `bar.html` | Category comparisons, rankings |
| `pie.html` | Composition / share breakdown |
| `candlestick.html` | OHLCV price charts |
| `scatter.html` | Correlation, distribution |
| `dashboard.html` | KPI cards + 2×2 multi-chart grid |
| `radar.html` | Multi-dimension scoring |
| `heatmap.html` | Matrix / calendar intensity |
| `dual-axis.html` | Two series with very different scales (e.g. market cap vs stablecoin supply) — left and right Y axes, each with its own label color |
| `multi-panel.html` | Stacked panels sharing one X axis (e.g. price + volume + RSI) — single ECharts instance, tooltip/zoom synced across all panels |
| `waterfall.html` | Incremental contribution breakdown (e.g. P&L attribution, budget variance) — positive/negative bars stacked on a floating base |

### Step 2: Create project folder

Use `create_project(name, description, data_sources)` from `scripts/build_chart.py`.

### Step 3: Build and save chart page

Use either:
- `build_chart(template_name, ...)`
- `build_chart_custom(...)`

Then save as `index.html` in the project folder:
- `save_chart(html, project_dir=project_dir)`

### Step 4: Save reproducible assets

Also save:
- `save_generate_script(script_content, project_dir)` → `generate.py`
- `save_data(data, project_dir)` → `data.json`
- project README is created by `create_project(...)`

### Step 5: Serve preview

Use project-root serving (recommended):

```python
preview_serve(
  title="Chart Preview",
  dir="skills/chart/scripts",
  command="python3 chart_server.py /data/workspace/output/chart-html 7860",
  port=7860
)
```

Then open: `/preview/<id>/<project-name>/index.html`

Important behavior in v3.0.1:
- `chart_server.py` now rewrites preview-prefixed static paths internally (`/preview/<id>/...` → `/...`) before filesystem lookup.
- This guarantees the preview iframe resolves the real project `index.html` instead of falling back to root directory listing.
- Keep project pages under `output/chart-html/<project>/index.html` (do not serve `output/chart-html` directly as a static preview without `chart_server.py`).

### Step 6: Export image

Two modes:
1. **User wants web page + image**: click "💾 Save Image" in page toolbar, saves to current project as `screenshot.png`
2. **User wants image only**: call `screenshot_chart(project_dir)` (Playwright) and send `screenshot.png` directly

### Step 7: Final visual QA (mandatory, render → review → fix)

The runtime tool is `vision_analyze(image_url=<workspace image path or public URL>, question=<specific QA rubric>)`. It analyzes an existing image only — it does NOT render charts. Export the PNG first, then pass it in.

It returns structured `findings` (each with `severity` = critical / major / minor plus `evidence`), a `severity_counts` map, and a `blocking` boolean. **Use `blocking` as the gate signal, not your reading of the prose.** When `structured` is `false` the model did not return parseable findings — re-run once, and if it stays unparseable report the gate as not run.

**Resolution matters.** Tick labels and legend text are exactly what a small PNG loses first. Export `screenshot.png` at 1280px wide or more before review; a thumbnail can only answer coarse questions (empty panel, unreadable palette, collapsed axes).

After `screenshot.png` exists in the project folder:

1. **Run vision review.** Call `vision_analyze(image_url=<absolute path to screenshot.png>, question=<rubric>)`. The rubric must target, at minimum:
   - **Label clipping / overlap** — axis tick labels, data labels, legend entries, title/subtitle not running into chart area or off-canvas.
   - **Legend** — present when needed, distinguishable from series colors, not occluding data.
   - **Color contrast & scale** — series colors distinguishable (including common color-vision deficiencies), zero/gridline visibility, axis scale (linear vs log) appropriate for the data, no misleading truncation.
   - **Data-story clarity** — title states the takeaway, axis units labeled, anomalies/callouts visible, no dead pixels or empty panels.
2. **Triage & fix.** Fix every Critical and Major finding (template choice, series options, axis min/max, label formatter, padding, color token). Re-export `screenshot.png` and re-run `vision_analyze` until `blocking` is `false`. **Cap the loop at 2 re-review rounds** — if Critical/Major findings survive round 2, ship with the remaining findings listed verbatim to the user instead of looping further.
3. **Honest reporting.** If Playwright is unavailable, the chart fails to render, or `screenshot_chart()` errors, state plainly: "Final visual QA was not run — <reason>." Do not declare the chart done based on HTML alone.

Skip this gate only for purely textual / non-visual output (e.g. CSV export with no rendered chart). Multi-panel pages must review each panel and the overall layout together.

## Toolbar Requirements

Every chart page must include these buttons:

```html
<div class="actions">
  <button onclick="downloadPNG(this)">📥 Download PNG</button>
  <button onclick="copyToClipboard(this)">📋 Copy Image</button>
  <button onclick="saveToProject(this)">💾 Save Image</button>
</div>
```

Do not include gallery entry.

## Key Files

| File | Purpose |
|------|---------|
| `skills/chart/scripts/base-styles.css` | Base dark theme CSS |
| `skills/chart/scripts/base-export.js` | Export helpers: download/copy/save-to-project |
| `skills/chart/scripts/build_chart.py` | Project creation, HTML build, data/script save, screenshot |
| `skills/chart/scripts/chart_server.py` | Static server + `/save-chart` API |
| `skills/chart/templates/*.html` | Reusable chart templates |
| `output/chart-html/<project>/*` | All generated chart artifacts |

## Notes

- Embed data directly in HTML (`const DATA = ...`) to avoid iframe CORS issues.
- For multi-chart pages, register all chart instances in `window.CHART_INSTANCES`.
- Use meaningful project names (`topic-range-date`) for easy lookup.
