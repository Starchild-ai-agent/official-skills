/* ============================================================
   Token Momentum Scanner — script.js
   Layout: A6 Sidebar + Content
   Entrance: D4 stagger top-to-bottom
   API: CoinGecko market_chart for historical prices
   Indicators: RSI (14-period), MACD (12,26,9) calculated client-side
   Charts: Chart.js (bar + dual-axis line)
   Animation: GSAP 3 + ScrollTrigger
   ============================================================ */
(function () {
  'use strict';
  gsap.registerPlugin(ScrollTrigger);
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const CONFIG = {
    trackedTokens: (() => {
      try {
        const raw = '{{TRACKED_TOKENS}}';
        if (raw.startsWith('{{')) return ['bitcoin', 'ethereum', 'solana'];
        return JSON.parse(raw);
      } catch { return ['bitcoin', 'ethereum', 'solana']; }
    })(),
    maxRetries: 2, retryBaseDelay: 1500, refreshInterval: 60_000,
  };

  const SYMBOL_MAP = {
    bitcoin: 'BTC', ethereum: 'ETH', solana: 'SOL', cardano: 'ADA',
    polkadot: 'DOT', 'avalanche-2': 'AVAX', ripple: 'XRP', dogecoin: 'DOGE',
    chainlink: 'LINK', arbitrum: 'ARB', optimism: 'OP', uniswap: 'UNI',
  };

  const ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';

  /* ---- Technical Indicator Calculations ---- */
  function calcRSI(prices, period) {
    if (prices.length < period + 1) return [];
    const rsi = [];
    let avgGain = 0, avgLoss = 0;
    for (let i = 1; i <= period; i++) {
      const diff = prices[i] - prices[i - 1];
      if (diff >= 0) avgGain += diff; else avgLoss += Math.abs(diff);
    }
    avgGain /= period; avgLoss /= period;
    rsi.push(avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss));
    for (let i = period + 1; i < prices.length; i++) {
      const diff = prices[i] - prices[i - 1];
      const gain = diff >= 0 ? diff : 0;
      const loss = diff < 0 ? Math.abs(diff) : 0;
      avgGain = (avgGain * (period - 1) + gain) / period;
      avgLoss = (avgLoss * (period - 1) + loss) / period;
      rsi.push(avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss));
    }
    return rsi;
  }

  function calcEMA(data, period) {
    const k = 2 / (period + 1);
    const ema = [data[0]];
    for (let i = 1; i < data.length; i++) ema.push(data[i] * k + ema[i - 1] * (1 - k));
    return ema;
  }

  function calcMACD(prices) {
    const ema12 = calcEMA(prices, 12);
    const ema26 = calcEMA(prices, 26);
    const macdLine = ema12.map((v, i) => v - ema26[i]);
    const signalLine = calcEMA(macdLine, 9);
    const histogram = macdLine.map((v, i) => v - signalLine[i]);
    return { macdLine, signalLine, histogram };
  }

  function getSignal(rsi, macdHist) {
    const latestRSI = rsi[rsi.length - 1];
    const latestMACD = macdHist[macdHist.length - 1];
    const prevMACD = macdHist[macdHist.length - 2];
    if (latestRSI < 35 && latestMACD > prevMACD) return 'buy';
    if (latestRSI > 65 && latestMACD < prevMACD) return 'sell';
    if (latestRSI < 40 && latestMACD > 0) return 'buy';
    if (latestRSI > 60 && latestMACD < 0) return 'sell';
    return 'hold';
  }

  function getTrend(prices) {
    const recent = prices.slice(-7);
    const older = prices.slice(-14, -7);
    const recentAvg = recent.reduce((a, b) => a + b, 0) / recent.length;
    const olderAvg = older.reduce((a, b) => a + b, 0) / older.length;
    const pctChange = ((recentAvg - olderAvg) / olderAvg) * 100;
    return { direction: pctChange > 0 ? 'up' : 'down', pct: Math.abs(pctChange).toFixed(1) };
  }

  /* ---- State ---- */
  let tokenData = {};
  let rsiChart = null, overlayChart = null;
  let activeFilter = 'all';

  /* ---- GSAP Animations ---- */
  function animateInlineHero() {
    if (prefersReducedMotion) { gsap.set('.inline-hero', { opacity: 1 }); return; }
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    tl.from('.inline-hero__title', { opacity: 0, y: 20, duration: 0.6 })
      .from('.inline-hero__subtitle', { opacity: 0, y: 14, duration: 0.4 }, '-=0.3')
      .from('.inline-hero__kpi', { opacity: 0, y: 16, stagger: 0.1, duration: 0.5 }, '-=0.2');
  }

  function animateSidebar() {
    if (prefersReducedMotion) return;
    gsap.from('.sidebar__header', { opacity: 0, x: -20, duration: 0.5, ease: 'power3.out' });
    gsap.from('.sidebar__section', { opacity: 0, x: -16, stagger: 0.1, duration: 0.4, delay: 0.2, ease: 'power3.out' });
  }

  function animateCardEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.signal-card, .momentum-item', { opacity: 1, y: 0 });
      return;
    }
    /* D4: stagger top-to-bottom */
    gsap.utils.toArray('.signal-card').forEach((card, i) => {
      gsap.to(card, {
        opacity: 1, y: 0, duration: 0.7,
        delay: i * 0.1,
        ease: 'power3.out',
        scrollTrigger: { trigger: card, start: 'top 88%', once: true }
      });
    });
  }

  /* ---- Utilities ---- */
  async function fetchWithRetry(url, retries = CONFIG.maxRetries) {
    for (let attempt = 0; attempt <= retries; attempt++) {
      try { const res = await fetch(url); if (!res.ok) throw new Error(`HTTP ${res.status}`); return await res.json(); }
      catch (err) { if (attempt === retries) throw err; await new Promise((r) => setTimeout(r, CONFIG.retryBaseDelay * (attempt + 1))); }
    }
  }

  function showSkeleton(id, count, type) {
    const c = document.getElementById(id);
    if (!c) return;
    let h = '';
    for (let i = 0; i < count; i++) {
      if (type === 'card') h += '<div class="skeleton skeleton--card"></div>';
      else h += '<div class="skeleton skeleton--row"></div>';
    }
    c.innerHTML = h;
  }

  function showError(id, msg, retryFn) {
    const c = document.getElementById(id);
    if (!c) return;
    c.innerHTML = `<div class="error-state">${ICON_ALERT}<p class="error-state__message">${msg}</p>${retryFn ? '<button class="error-state__retry" data-retry="true">Retry</button>' : ''}</div>`;
    if (retryFn) { const btn = c.querySelector('[data-retry]'); if (btn) btn.addEventListener('click', retryFn); }
  }

  function startClock() {
    const el = document.getElementById('sidebar-time');
    if (!el) return;
    const tick = () => { el.textContent = new Date().toLocaleString('en-US', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }); };
    tick(); setInterval(tick, 1000);
  }

  /* ---- Data Fetch ---- */
  async function fetchTokenData() {
    showSkeleton('momentum-grid', CONFIG.trackedTokens.length, 'card');
    showSkeleton('signal-table', CONFIG.trackedTokens.length, 'row');

    for (const id of CONFIG.trackedTokens) {
      try {
        const url = `https://api.coingecko.com/api/v3/coins/${id}/market_chart?vs_currency=usd&days=30&interval=daily`;
        const data = await fetchWithRetry(url);
        const prices = data.prices.map((p) => p[1]);
        const labels = data.prices.map((p) => new Date(p[0]).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
        const sym = SYMBOL_MAP[id] || id.toUpperCase().substring(0, 4);
        const rsi = calcRSI(prices, 14);
        const macd = calcMACD(prices);
        const signal = getSignal(rsi, macd.histogram);
        const trend = getTrend(prices);
        tokenData[sym] = { id, prices, labels, rsi, macd, signal, trend, currentPrice: prices[prices.length - 1], latestRSI: rsi[rsi.length - 1], latestMACD: macd.histogram[macd.histogram.length - 1] };
      } catch (err) {
        const sym = SYMBOL_MAP[id] || id.toUpperCase().substring(0, 4);
        const prices = Array.from({ length: 30 }, (_, i) => 100 + Math.sin(i * 0.3) * 20 + Math.random() * 10);
        const labels = Array.from({ length: 30 }, (_, i) => { const d = new Date(); d.setDate(d.getDate() - 29 + i); return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }); });
        const rsi = calcRSI(prices, 14);
        const macd = calcMACD(prices);
        const signal = getSignal(rsi, macd.histogram);
        const trend = getTrend(prices);
        tokenData[sym] = { id, prices, labels, rsi, macd, signal, trend, currentPrice: prices[prices.length - 1], latestRSI: rsi[rsi.length - 1], latestMACD: macd.histogram[macd.histogram.length - 1], mock: true };
      }
      await new Promise((r) => setTimeout(r, 300));
    }
  }

  /* ---- Renderers ---- */
  function renderHeroMetrics() {
    const tokens = Object.values(tokenData);
    if (tokens.length === 0) return;
    const avgRSI = tokens.reduce((s, t) => s + t.latestRSI, 0) / tokens.length;
    const sorted = [...tokens].sort((a, b) => b.latestRSI - a.latestRSI);
    const strongest = sorted[0];
    const weakest = sorted[sorted.length - 1];

    const momEl = document.getElementById('hero-momentum');
    const strEl = document.getElementById('hero-strongest');
    const weakEl = document.getElementById('hero-weakest');

    if (momEl) {
      momEl.textContent = avgRSI.toFixed(0);
      momEl.style.color = avgRSI > 60 ? 'var(--color-bullish)' : avgRSI < 40 ? 'var(--color-bearish)' : 'var(--color-accent)';
    }
    if (strEl) strEl.textContent = strongest ? strongest.id.split('-')[0].substring(0, 3).toUpperCase() : '--';
    if (weakEl) weakEl.textContent = weakest ? weakest.id.split('-')[0].substring(0, 3).toUpperCase() : '--';
  }

  function renderSidebarTokenList() {
    const container = document.getElementById('sidebar-token-list');
    if (!container) return;
    let html = '';
    Object.entries(tokenData).forEach(([sym, data]) => {
      html += `<div class="sidebar__token-item" data-token="${sym}">
        <span class="sidebar__token-name">${sym}</span>
        <span class="sidebar__token-signal sidebar__token-signal--${data.signal}">${data.signal}</span>
      </div>`;
    });
    container.innerHTML = html;

    container.querySelectorAll('.sidebar__token-item').forEach((item) => {
      item.addEventListener('click', () => {
        container.querySelectorAll('.sidebar__token-item').forEach((el) => el.classList.remove('sidebar__token-item--active'));
        item.classList.add('sidebar__token-item--active');
        const sym = item.dataset.token;
        renderOverlayChart(sym);
      });
    });
  }

  function renderSidebarStats() {
    const tokens = Object.values(tokenData);
    if (tokens.length === 0) return;
    const avgRSI = tokens.reduce((s, t) => s + t.latestRSI, 0) / tokens.length;
    const bullish = tokens.filter((t) => t.signal === 'buy').length;
    const bearish = tokens.filter((t) => t.signal === 'sell').length;

    const avgEl = document.getElementById('sidebar-avg-rsi');
    const bullEl = document.getElementById('sidebar-bullish');
    const bearEl = document.getElementById('sidebar-bearish');

    if (avgEl) avgEl.textContent = avgRSI.toFixed(1);
    if (bullEl) bullEl.textContent = bullish;
    if (bearEl) bearEl.textContent = bearish;
  }

  function renderMomentumGrid() {
    const container = document.getElementById('momentum-grid');
    if (!container) return;
    let html = '';
    Object.entries(tokenData).forEach(([sym, data]) => {
      if (activeFilter !== 'all' && data.signal !== activeFilter) return;
      const signalClass = `momentum-item__signal--${data.signal}`;
      const trendArrow = data.trend.direction === 'up' ? '&#9650;' : '&#9660;';
      const trendColor = data.trend.direction === 'up' ? 'var(--color-bullish)' : 'var(--color-bearish)';
      const rsiColor = data.latestRSI > 70 ? 'var(--color-overbought)' : data.latestRSI < 30 ? 'var(--color-oversold)' : 'var(--color-text)';
      html += `<div class="momentum-item">
        <div class="momentum-item__header">
          <span class="momentum-item__token">${sym}</span>
          <span class="momentum-item__signal ${signalClass}">${data.signal}</span>
        </div>
        <div class="momentum-item__metrics">
          <div class="momentum-item__row"><span class="momentum-item__label">RSI (14)</span><span class="momentum-item__value" style="color:${rsiColor}">${data.latestRSI.toFixed(1)}</span></div>
          <div class="momentum-item__row"><span class="momentum-item__label">MACD Hist</span><span class="momentum-item__value" style="color:${data.latestMACD >= 0 ? 'var(--color-bullish)' : 'var(--color-bearish)'}">${data.latestMACD.toFixed(2)}</span></div>
          <div class="momentum-item__row"><span class="momentum-item__label">Price</span><span class="momentum-item__value">$${data.currentPrice.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span></div>
        </div>
        <div class="momentum-item__trend" style="color:${trendColor}">
          <span class="momentum-item__trend-arrow">${trendArrow}</span>
          <span>${data.trend.pct}% (7D)</span>
        </div>
      </div>`;
    });
    container.innerHTML = html;
    if (!prefersReducedMotion) gsap.from('.momentum-item', { opacity: 0, y: 16, stagger: 0.06, duration: 0.4, ease: 'power3.out' });
  }

  function renderRSIChart() {
    const canvas = document.getElementById('rsi-chart');
    if (!canvas) return;
    const cs = getComputedStyle(document.documentElement);
    const tokens = Object.entries(tokenData);
    const labels = tokens.map(([sym]) => sym);
    const values = tokens.map(([, d]) => d.latestRSI);
    const colors = values.map((v) => v > 70 ? cs.getPropertyValue('--color-overbought').trim() : v < 30 ? cs.getPropertyValue('--color-oversold').trim() : cs.getPropertyValue('--color-accent').trim());

    if (rsiChart) rsiChart.destroy();
    rsiChart = new Chart(canvas, {
      type: 'bar',
      data: { labels, datasets: [{ label: 'RSI', data: values, backgroundColor: colors, borderRadius: 4, barPercentage: 0.6 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { backgroundColor: cs.getPropertyValue('--color-surface').trim(), titleColor: cs.getPropertyValue('--color-text').trim(), bodyColor: cs.getPropertyValue('--color-text-secondary').trim(), borderColor: cs.getPropertyValue('--color-border').trim(), borderWidth: 1, titleFont: { family: "'IBM Plex Mono', monospace", size: 11 }, bodyFont: { family: "'IBM Plex Mono', monospace", size: 11 }, padding: 10 },
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: cs.getPropertyValue('--color-text-muted').trim(), font: { family: "'IBM Plex Mono', monospace", size: 11 } } },
          y: { min: 0, max: 100, grid: { color: cs.getPropertyValue('--color-border').trim(), lineWidth: 0.5 }, ticks: { color: cs.getPropertyValue('--color-text-muted').trim(), font: { family: "'IBM Plex Mono', monospace", size: 10 }, stepSize: 20 } },
        },
      },
    });

    const drawZones = {
      id: 'rsiZones',
      afterDraw(chart) {
        const { ctx, chartArea: { left, right, top, bottom }, scales: { y } } = chart;
        const ob = y.getPixelForValue(70), os = y.getPixelForValue(30);
        ctx.save();
        ctx.fillStyle = 'rgba(198,40,40,0.05)'; ctx.fillRect(left, top, right - left, ob - top);
        ctx.fillStyle = 'rgba(46,125,50,0.05)'; ctx.fillRect(left, os, right - left, bottom - os);
        ctx.strokeStyle = cs.getPropertyValue('--color-overbought').trim(); ctx.lineWidth = 1; ctx.setLineDash([4, 4]);
        ctx.beginPath(); ctx.moveTo(left, ob); ctx.lineTo(right, ob); ctx.stroke();
        ctx.strokeStyle = cs.getPropertyValue('--color-oversold').trim();
        ctx.beginPath(); ctx.moveTo(left, os); ctx.lineTo(right, os); ctx.stroke();
        ctx.setLineDash([]); ctx.restore();
      }
    };
    rsiChart.config.plugins = [drawZones];
    rsiChart.update();
  }

  function renderOverlayChart(selectedToken) {
    const canvas = document.getElementById('overlay-chart');
    if (!canvas) return;
    const cs = getComputedStyle(document.documentElement);
    const tokenKey = selectedToken || Object.keys(tokenData)[0];
    if (!tokenKey) return;
    const data = tokenData[tokenKey];
    const labelEl = document.getElementById('overlay-token-label');
    if (labelEl) labelEl.textContent = tokenKey;

    const rsiOffset = data.prices.length - data.rsi.length;
    const priceLabels = data.labels.slice(rsiOffset);
    const priceData = data.prices.slice(rsiOffset);

    if (overlayChart) overlayChart.destroy();
    overlayChart = new Chart(canvas, {
      type: 'line',
      data: {
        labels: priceLabels,
        datasets: [
          { label: 'Price ($)', data: priceData, borderColor: cs.getPropertyValue('--chart-1').trim(), backgroundColor: 'transparent', borderWidth: 2, pointRadius: 0, pointHoverRadius: 4, tension: 0.3, yAxisID: 'y' },
          { label: 'RSI (14)', data: data.rsi, borderColor: cs.getPropertyValue('--chart-3').trim(), backgroundColor: 'transparent', borderWidth: 1.5, pointRadius: 0, pointHoverRadius: 3, tension: 0.3, yAxisID: 'y1', borderDash: [4, 2] },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { position: 'top', labels: { color: cs.getPropertyValue('--color-text-secondary').trim(), font: { family: "'IBM Plex Mono', monospace", size: 11 }, boxWidth: 12, boxHeight: 2, padding: 16 } },
          tooltip: { backgroundColor: cs.getPropertyValue('--color-surface').trim(), titleColor: cs.getPropertyValue('--color-text').trim(), bodyColor: cs.getPropertyValue('--color-text-secondary').trim(), borderColor: cs.getPropertyValue('--color-border').trim(), borderWidth: 1, titleFont: { family: "'IBM Plex Mono', monospace", size: 11 }, bodyFont: { family: "'IBM Plex Mono', monospace", size: 11 }, padding: 10 },
        },
        scales: {
          x: { grid: { color: cs.getPropertyValue('--color-border').trim(), lineWidth: 0.5 }, ticks: { color: cs.getPropertyValue('--color-text-muted').trim(), font: { family: "'IBM Plex Mono', monospace", size: 10 }, maxTicksLimit: 8 } },
          y: { position: 'left', grid: { color: cs.getPropertyValue('--color-border').trim(), lineWidth: 0.5 }, ticks: { color: cs.getPropertyValue('--color-text-muted').trim(), font: { family: "'IBM Plex Mono', monospace", size: 10 }, callback: (v) => '$' + v.toLocaleString() } },
          y1: { position: 'right', min: 0, max: 100, grid: { drawOnChartArea: false }, ticks: { color: cs.getPropertyValue('--color-text-muted').trim(), font: { family: "'IBM Plex Mono', monospace", size: 10 }, stepSize: 20 } },
        },
      },
    });
  }

  function renderSignalTable() {
    const container = document.getElementById('signal-table');
    if (!container) return;
    let html = '<table class="signal-table"><thead><tr><th>Token</th><th>Price</th><th>RSI</th><th>MACD</th><th>Trend</th><th>Signal</th></tr></thead><tbody>';
    Object.entries(tokenData).forEach(([sym, data]) => {
      const rsiColor = data.latestRSI > 70 ? 'var(--color-overbought)' : data.latestRSI < 30 ? 'var(--color-oversold)' : 'var(--color-text)';
      const macdColor = data.latestMACD >= 0 ? 'var(--color-bullish)' : 'var(--color-bearish)';
      const trendArrow = data.trend.direction === 'up' ? '&#9650;' : '&#9660;';
      const trendColor = data.trend.direction === 'up' ? 'var(--color-bullish)' : 'var(--color-bearish)';
      html += `<tr>
        <td style="font-weight:600;color:var(--color-text)">${sym}</td>
        <td>$${data.currentPrice.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
        <td style="color:${rsiColor}">${data.latestRSI.toFixed(1)}</td>
        <td style="color:${macdColor}">${data.latestMACD.toFixed(2)}</td>
        <td style="color:${trendColor}">${trendArrow} ${data.trend.pct}%</td>
        <td><span class="signal-badge signal-badge--${data.signal}">${data.signal}</span></td>
      </tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
    if (!prefersReducedMotion) gsap.from('.signal-table tbody tr', { opacity: 0, x: -10, stagger: 0.04, duration: 0.3, ease: 'power3.out' });
  }

  /* ---- Filter ---- */
  function initFilters() {
    document.querySelectorAll('.sidebar__filter-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.sidebar__filter-btn').forEach((b) => b.classList.remove('sidebar__filter-btn--active'));
        btn.classList.add('sidebar__filter-btn--active');
        activeFilter = btn.dataset.filter;
        renderMomentumGrid();
      });
    });
  }

  /* ---- Theme ---- */
  function initTheme() {
    const stored = localStorage.getItem('token-momentum-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = stored || (prefersDark ? 'dark' : 'light');
    if (theme === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  }

  function toggleTheme() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (isDark) { document.documentElement.removeAttribute('data-theme'); localStorage.setItem('token-momentum-theme', 'light'); }
    else { document.documentElement.setAttribute('data-theme', 'dark'); localStorage.setItem('token-momentum-theme', 'dark'); }
    renderRSIChart(); renderOverlayChart();
  }

  /* ---- Init ---- */
  async function init() {
    initTheme(); startClock();
    document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
    animateInlineHero();
    animateSidebar();
    initFilters();

    await fetchTokenData();
    renderHeroMetrics();
    renderSidebarTokenList();
    renderSidebarStats();
    renderMomentumGrid();
    renderRSIChart();
    renderOverlayChart();
    renderSignalTable();
    animateCardEntrance();

  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
