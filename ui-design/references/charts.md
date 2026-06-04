# Charts & Data Visualization Reference

Guidelines for creating professional charts in dashboards. These are design standards — implement the actual chart code fresh each time.

---

## Library Selection

Load via CDN in `<script>` tag:

| Library | Use When |
|---------|----------|
| **Chart.js** (`chart.js@4`) | Most dashboards. Simple API, good defaults, lightweight (~65KB) |
| **ECharts** (`echarts@5`) | Complex/interactive dashboards. Rich features, larger (~300KB) |
| **uPlot** (`uplot@1`) | High-performance time series. Minimal, fast (~35KB) |

Default to Chart.js unless the dashboard needs advanced interactions (drill-down, linked charts, complex tooltips).

---

## Chart Type Selection

| Data Pattern | Use | Don't Use |
|-------------|-----|-----------|
| Trend over time | Line chart | Bar chart (unless discrete periods) |
| Comparing categories | Vertical bar chart | Pie chart |
| Long category labels | Horizontal bar chart | Vertical bar (labels get truncated) |
| Parts of a whole (≤5 segments) | Donut chart | Pie chart with >5 segments |
| Parts of a whole (>5 segments) | Horizontal bar chart | Pie or donut (too many slices) |
| Distribution | Area chart | Pie chart |
| Single metric vs target | Progress bar or gauge | Full chart (overkill) |
| Inline trend indicator | Sparkline (canvas mini-chart) | Full chart in a stat card |

**Never use**: 3D charts, radar charts for simple data, pie charts with >5 segments.

---

## Styling Rules

### Colors
- **Use your page's CSS custom properties** for chart colors. Never use library default colors.
- Read CSS variables with `getComputedStyle(document.documentElement).getPropertyValue(...)`.
- For multi-series: derive variations from your accent (adjust opacity or lightness), or use a harmonious set that matches your palette.
- All data colors must pass 3:1 contrast against the chart background.

### Grid & Axes
- Grid lines: very subtle — use your border/separator color or lower opacity. Grid should never compete with data.
- Axis labels: use your muted text color, 12px font size.
- Include units on axis labels ($ / % / K / M).
- Hide the axis border line.
- X-axis grid: usually hidden. Y-axis grid: subtle horizontal lines.

### Tooltips
- Style tooltips to match your page theme (background, text color, border, border-radius).
- Show exact values on hover/tap.
- Use crosshair or index mode for better hover behavior on line/area charts.

### Legend
- Always show legend for multi-series charts.
- Position: below the chart or inline with the title. Never detached far from the chart.
- Use point-style (small circles) instead of rectangles for cleaner look.

### Responsiveness
- Charts must resize with their container. Set responsive mode and disable fixed aspect ratio.
- Set chart container height explicitly (e.g., 200-320px range depending on importance).
- On mobile, consider simplifying: fewer data points, abbreviated labels, hidden legend.

---

## Chart Container Anti-Expansion (CRITICAL)

**Problem:** Chart.js and ECharts in responsive mode will infinitely expand their height if the container doesn't have a strictly fixed height. This happens because:
1. The chart reads the container's height → renders at that height
2. The render increases the container's scrollHeight → triggers a resize observer
3. The resize observer re-reads the (now larger) height → re-renders taller
4. Infinite loop → page becomes unusable

**The fix — always use this exact container pattern:**

```html
<!-- ✅ CORRECT: Fixed-height wrapper with position:relative + canvas -->
<div class="chart-card">
  <h3>Chart Title</h3>
  <div class="chart-container" style="height: 280px; position: relative;">
    <canvas id="myChart"></canvas>
  </div>
</div>
```

```css
/* ✅ CORRECT: Chart container CSS */
.chart-container {
  position: relative;   /* REQUIRED — canvas positions relative to this */
  height: 280px;        /* REQUIRED — explicit px height, NOT min-height, NOT auto */
  width: 100%;          /* OK — width can be flexible */
  overflow: hidden;     /* SAFETY — prevent any overflow from expanding parent */
}

/* ❌ WRONG — these will cause infinite expansion: */
.chart-container {
  height: auto;         /* ❌ auto height = chart decides = infinite growth */
  min-height: 280px;    /* ❌ min-height without max = can grow forever */
  flex: 1;              /* ❌ flex child without explicit height = expansion */
  height: 100%;         /* ❌ percentage of flex/grid parent = unstable */
}
```

**Chart.js configuration (mandatory):**
```js
new Chart(ctx, {
  // ...
  options: {
    responsive: true,
    maintainAspectRatio: false,  // REQUIRED — let container control height
    // ...
  }
});
```

**ECharts configuration (mandatory):**
```js
const chart = echarts.init(container);
// Container MUST have explicit px height before init

// If you need to handle resize:
window.addEventListener('resize', () => {
  chart.resize();  // ECharts resize — reads container dimensions
});
// Do NOT call chart.resize() inside a ResizeObserver on the chart container itself — infinite loop!
```

**Additional safety rules:**
- Never put a chart container inside a CSS Grid or Flexbox child without an explicit `height` in px
- Never use `height: 100%` on a chart container unless the parent chain all the way up has explicit heights
- Never call `chart.resize()` or `chart.update()` inside a ResizeObserver that observes the chart's own container
- Always set `overflow: hidden` on the chart container as a safety net
- If using CSS Grid for dashboard layout, set `grid-template-rows` with explicit values (e.g., `280px`), not `auto` or `1fr`

---

## Chart Container Design

Every chart should be wrapped in a card with:
1. **Title** (left-aligned, semibold)
2. **Optional period selector** (right-aligned, small toggle buttons)
3. **Chart area** (fixed height via explicit px, responsive width)
4. **Optional footer** (summary text or legend)

---

## Empty & Error States

- **No data**: Show a centered message with a muted icon. Never show an empty chart frame with axes but no data.
- **Loading**: Show a skeleton placeholder matching the chart's dimensions. Not a spinner.
- **Error**: Show error message with a retry action. Never show a broken/partial chart.

---

## Mock Data

When generating dashboards, create realistic mock data:

### Time Series
- Generate 7-30 data points with natural fluctuation (random walk with mean reversion)
- Don't use round numbers (not 1000, 2000, 3000 — use 1,247, 2,089, 2,834)
- Include a general trend (upward, downward, or seasonal) — not flat lines
- Use realistic date labels

### Category Data
- Use real-world category names (actual product names, city names, department names)
- Values should have natural variance — not evenly distributed
- Include both positive and negative changes where appropriate

### Proportional Data
- Segments should have realistic proportions (not equal slices)
- Include one dominant segment (40-60%) and several smaller ones
- Labels should be specific ("Desktop Chrome" not "Category A")

---

## Dashboard Layout Principles

Don't copy a fixed layout template. Instead, follow these principles:

### Information Hierarchy
1. **KPI summary row** at the top — the most important metrics at a glance (typically 3-5 stat cards)
2. **Primary chart** — the main data story, given the most space
3. **Supporting charts** — secondary data, smaller than the primary
4. **Detail table** — granular data for users who want to drill down

### Layout Guidelines
- Use CSS Grid. Vary column spans — not every chart should be the same width.
- The primary chart should be visually dominant (wider or taller than supporting charts).
- KPI cards stack to 2-column on tablet, single column on mobile.
- Charts stack vertically on mobile.
- Tables get horizontal scroll on mobile.

### Constraints
- Maximum 3-4 charts + 1 table per dashboard view. More than that overwhelms.
- Not every chart should be the same height. Vary: one tall primary + shorter supporting charts.
- Choose the 4-6 most important KPIs. Don't show every metric.

---

## Checklist

- [ ] Chart type matches the data pattern
- [ ] Colors match the page palette (not library defaults)
- [ ] Axis labels include units
- [ ] Tooltips show exact values
- [ ] Grid lines are subtle
- [ ] Chart is responsive
- [ ] Empty/error states handled
- [ ] Mock data looks realistic (not round numbers, has variance)
- [ ] Legend visible for multi-series
- [ ] Font sizes readable (≥12px)
- [ ] Dashboard layout varies chart sizes (not all identical)
- [ ] Primary chart is visually dominant
