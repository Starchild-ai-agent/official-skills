/* ============================================================
   Funding Rate Dashboard — script.js
   API: CoinGecko (free, no key) for token prices
   Mock Data: Built-in funding rate data for Binance, Bybit, OKX, etc.
   Charts: Chart.js (line)
   Animation: GSAP 3 + ScrollTrigger (CDN)
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
    maxRetries: 2,
    retryBaseDelay: 1500,
    refreshInterval: 60_000,
  };

  const API = {
    prices: (ids) => `https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=${ids}&order=market_cap_desc&sparkline=false`,
  };

  const SYMBOL_MAP = {
    bitcoin: 'BTC', ethereum: 'ETH', solana: 'SOL', cardano: 'ADA',
    polkadot: 'DOT', 'avalanche-2': 'AVAX', ripple: 'XRP', dogecoin: 'DOGE',
    chainlink: 'LINK', arbitrum: 'ARB', optimism: 'OP', uniswap: 'UNI',
  };

  const ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';

  const EXCHANGES = ['Binance', 'Bybit', 'OKX', 'Bitget', 'dYdX', 'Hyperliquid'];

  /* ============================================================
     MOCK DATA — Funding Rates
     Real funding rate APIs (Binance, Bybit, OKX) require specific
     endpoints and may have CORS restrictions. Using realistic
     simulated data that mirrors actual market patterns.
     ============================================================ */

  function generateFundingRates() {
    const tokens = CONFIG.trackedTokens.map((t) => SYMBOL_MAP[t] || t.toUpperCase().substring(0, 4));
    const rates = [];

    tokens.forEach((token) => {
      const baseRate = (Math.random() - 0.35) * 0.08;
      EXCHANGES.forEach((exchange) => {
        const variance = (Math.random() - 0.5) * 0.02;
        const rate = baseRate + variance;
        const annualized = rate * 3 * 365;
        rates.push({
          token,
          exchange,
          rate8h: rate,
          annualized,
          nextFunding: Math.floor(Math.random() * 480),
          openInterest: Math.floor(Math.random() * 500_000_000 + 50_000_000),
          volume24h: Math.floor(Math.random() * 2_000_000_000 + 100_000_000),
        });
      });
    });

    return rates;
  }

  function generateHistoryData() {
    const days = 7;
    const points = days * 3;
    const labels = [];
    const datasets = {};

    EXCHANGES.slice(0, 3).forEach((ex) => {
      datasets[ex] = [];
    });

    const now = Date.now();
    for (let i = points - 1; i >= 0; i--) {
      const date = new Date(now - i * 8 * 3600_000);
      labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' ' + date.getHours() + ':00');

      Object.keys(datasets).forEach((ex) => {
        const base = (Math.random() - 0.4) * 0.06;
        datasets[ex].push(parseFloat((base * 100).toFixed(4)));
      });
    }

    return { labels, datasets };
  }

  function findArbitrageOpportunities(rates) {
    const opportunities = [];
    const tokenGroups = {};

    rates.forEach((r) => {
      if (!tokenGroups[r.token]) tokenGroups[r.token] = [];
      tokenGroups[r.token].push(r);
    });

    Object.entries(tokenGroups).forEach(([token, group]) => {
      for (let i = 0; i < group.length; i++) {
        for (let j = i + 1; j < group.length; j++) {
          const spread = Math.abs(group[i].rate8h - group[j].rate8h);
          if (spread > 0.005) {
            const long = group[i].rate8h < group[j].rate8h ? group[i] : group[j];
            const short = group[i].rate8h < group[j].rate8h ? group[j] : group[i];
            opportunities.push({
              token,
              longExchange: long.exchange,
              shortExchange: short.exchange,
              longRate: long.rate8h,
              shortRate: short.rate8h,
              spread,
              annualizedSpread: spread * 3 * 365,
            });
          }
        }
      }
    });

    return opportunities.sort((a, b) => b.spread - a.spread).slice(0, 6);
  }

  let fundingRates = generateFundingRates();
  let historyData = generateHistoryData();
  let arbOpportunities = findArbitrageOpportunities(fundingRates);
  let historyChart = null;
  let sortColumn = 'rate8h';
  let sortAsc = false;
  let priceData = {};

  /* ============================================================ GSAP — D2 stagger left-to-right ============================================================ */
  function animateHeroEntrance() {
    if (prefersReducedMotion) { gsap.set('.hero__terminal', { opacity: 1, y: 0 }); return; }
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    tl.from('.hero__terminal', { opacity: 0, y: 20, duration: 0.6 })
      .from('.hero__prompt', { opacity: 0, x: -20, duration: 0.5 }, '-=0.2')
      .from('.hero__output', { opacity: 0, duration: 0.4 }, '-=0.2')
      .from('.hero__metric', { opacity: 0, x: -16, stagger: 0.08, duration: 0.4 }, '-=0.2');
  }

  function animateCardEntrance() {
    if (prefersReducedMotion) { gsap.set('.cmd-panel', { opacity: 1, x: 0 }); return; }
    /* D2: stagger from left to right */
    gsap.utils.toArray('.cmd-panel').forEach((panel, i) => {
      gsap.to(panel, { opacity: 1, x: 0, duration: 0.6, delay: i * 0.1, ease: 'power3.out',
        scrollTrigger: { trigger: panel, start: 'top 88%', once: true } });
    });
  }

  /* ============================================================ UTILITIES ============================================================ */
  async function fetchWithRetry(url, retries = CONFIG.maxRetries) {
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
      } catch (err) {
        if (attempt === retries) throw err;
        await new Promise((r) => setTimeout(r, CONFIG.retryBaseDelay * (attempt + 1)));
      }
    }
  }

  function formatRate(rate) {
    if (rate == null) return '--';
    const pct = (rate * 100).toFixed(4);
    return (rate >= 0 ? '+' : '') + pct + '%';
  }

  function formatUSD(v, compact) {
    if (v == null) return '--';
    if (compact) {
      if (v >= 1e9) return '$' + (v / 1e9).toFixed(2) + 'B';
      if (v >= 1e6) return '$' + (v / 1e6).toFixed(1) + 'M';
      if (v >= 1e3) return '$' + (v / 1e3).toFixed(1) + 'K';
    }
    return '$' + v.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  }

  function rateClass(rate) {
    if (rate > 0.001) return 'rate-positive';
    if (rate < -0.001) return 'rate-negative';
    return 'rate-neutral';
  }

  function showSkeleton(id, count, type) {
    const c = document.getElementById(id);
    if (!c) return;
    let h = '';
    for (let i = 0; i < count; i++) {
      if (type === 'row') h += '<div class="skeleton skeleton--row"></div>';
      else if (type === 'arb') h += '<div class="arb-card"><div class="skeleton" style="width:100%;height:60px"></div></div>';
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
    const el = document.getElementById('hero-time');
    if (!el) return;
    const tick = () => { el.textContent = new Date().toLocaleString('en-US', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }); };
    tick(); setInterval(tick, 1000);
  }

  function getChartColors() {
    const cs = getComputedStyle(document.documentElement);
    return [1, 2, 3, 4, 5, 6].map((i) => cs.getPropertyValue('--chart-' + i).trim());
  }

  /* ============================================================ RENDERERS ============================================================ */

  function renderHeroMetrics() {
    const btcRates = fundingRates.filter((r) => r.token === 'BTC');
    const avgBtcRate = btcRates.length > 0 ? btcRates.reduce((s, r) => s + r.rate8h, 0) / btcRates.length : 0;

    const btcEl = document.getElementById('hero-btc-funding');
    const arbEl = document.getElementById('hero-arb-signal');
    const exEl = document.getElementById('hero-exchanges');

    if (btcEl) {
      btcEl.textContent = formatRate(avgBtcRate);
      btcEl.style.color = avgBtcRate >= 0 ? 'var(--color-bullish)' : 'var(--color-bearish)';
    }
    if (arbEl) {
      const topArb = arbOpportunities[0];
      arbEl.textContent = topArb ? formatRate(topArb.spread) : 'NONE';
      arbEl.style.color = topArb && topArb.spread > 0.01 ? 'var(--color-accent)' : 'var(--color-text-muted)';
    }
    if (exEl) exEl.textContent = EXCHANGES.length.toString();
  }

  function renderFundingTable() {
    const container = document.getElementById('funding-table');
    if (!container) return;

    showSkeleton('funding-table', 8, 'row');

    setTimeout(() => {
      const sorted = [...fundingRates].sort((a, b) => {
        let va = a[sortColumn], vb = b[sortColumn];
        if (typeof va === 'string') { va = va.toLowerCase(); vb = vb.toLowerCase(); }
        return sortAsc ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
      });

      let html = '<table class="rate-table"><thead><tr>';
      const columns = [
        { key: 'token', label: 'Token' },
        { key: 'exchange', label: 'Exchange' },
        { key: 'rate8h', label: '8H Rate' },
        { key: 'annualized', label: 'Annual.' },
        { key: 'nextFunding', label: 'Next (min)' },
        { key: 'openInterest', label: 'Open Interest' },
        { key: 'volume24h', label: '24H Volume' },
      ];

      columns.forEach((col) => {
        const cls = sortColumn === col.key ? ' class="sorted"' : '';
        html += `<th${cls} data-sort="${col.key}">${col.label}</th>`;
      });
      html += '</tr></thead><tbody>';

      sorted.forEach((row) => {
        html += `<tr>
          <td><span class="token-cell">${row.token}</span></td>
          <td><span class="exchange-name">${row.exchange}</span></td>
          <td class="${rateClass(row.rate8h)}">${formatRate(row.rate8h)}</td>
          <td class="${rateClass(row.annualized)}">${(row.annualized * 100).toFixed(1)}%</td>
          <td>${row.nextFunding}m</td>
          <td>${formatUSD(row.openInterest, true)}</td>
          <td>${formatUSD(row.volume24h, true)}</td>
        </tr>`;
      });

      html += '</tbody></table>';
      container.innerHTML = html;

      container.querySelectorAll('th[data-sort]').forEach((th) => {
        th.addEventListener('click', () => {
          const col = th.dataset.sort;
          if (sortColumn === col) { sortAsc = !sortAsc; }
          else { sortColumn = col; sortAsc = true; }
          renderFundingTable();
        });
      });

      if (!prefersReducedMotion) {
        gsap.from('.rate-table tbody tr', { opacity: 0, x: -10, stagger: 0.03, duration: 0.3, ease: 'power3.out' });
      }
    }, 300);
  }

  function renderHistoryChart() {
    const container = document.getElementById('history-chart-container');
    const canvas = document.getElementById('history-chart');
    if (!canvas || !container) return;

    const colors = getChartColors();
    const exchanges = Object.keys(historyData.datasets);

    const datasets = exchanges.map((ex, i) => ({
      label: ex,
      data: historyData.datasets[ex],
      borderColor: colors[i],
      backgroundColor: 'transparent',
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 4,
      tension: 0.3,
    }));

    if (historyChart) historyChart.destroy();

    historyChart = new Chart(canvas, {
      type: 'line',
      data: { labels: historyData.labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              color: getComputedStyle(document.documentElement).getPropertyValue('--color-text-secondary').trim(),
              font: { family: "'IBM Plex Mono', monospace", size: 11 },
              boxWidth: 12, boxHeight: 2, padding: 16,
            },
          },
          tooltip: {
            backgroundColor: getComputedStyle(document.documentElement).getPropertyValue('--color-surface').trim(),
            titleColor: getComputedStyle(document.documentElement).getPropertyValue('--color-text').trim(),
            bodyColor: getComputedStyle(document.documentElement).getPropertyValue('--color-text-secondary').trim(),
            borderColor: getComputedStyle(document.documentElement).getPropertyValue('--color-border').trim(),
            borderWidth: 1,
            titleFont: { family: "'IBM Plex Mono', monospace", size: 11 },
            bodyFont: { family: "'IBM Plex Mono', monospace", size: 11 },
            padding: 10,
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(4)}%`,
            },
          },
        },
        scales: {
          x: {
            grid: { color: getComputedStyle(document.documentElement).getPropertyValue('--color-border').trim(), lineWidth: 0.5 },
            ticks: {
              color: getComputedStyle(document.documentElement).getPropertyValue('--color-text-muted').trim(),
              font: { family: "'IBM Plex Mono', monospace", size: 10 },
              maxTicksLimit: 8,
            },
          },
          y: {
            grid: { color: getComputedStyle(document.documentElement).getPropertyValue('--color-border').trim(), lineWidth: 0.5 },
            ticks: {
              color: getComputedStyle(document.documentElement).getPropertyValue('--color-text-muted').trim(),
              font: { family: "'IBM Plex Mono', monospace", size: 10 },
              callback: (v) => v.toFixed(3) + '%',
            },
          },
        },
      },
    });
  }

  function renderArbList() {
    const container = document.getElementById('arb-list');
    if (!container) return;

    showSkeleton('arb-list', 4, 'arb');

    setTimeout(() => {
      if (arbOpportunities.length === 0) {
        container.innerHTML = '<div class="error-state"><p class="error-state__message">No significant arbitrage opportunities detected</p></div>';
        return;
      }

      let html = '';
      arbOpportunities.forEach((arb) => {
        html += `<div class="arb-card">
          <div class="arb-card__header">
            <span class="arb-card__pair">${arb.token}</span>
            <span class="arb-card__spread">${formatRate(arb.spread)}</span>
          </div>
          <div class="arb-card__detail">
            <div class="arb-card__exchange">
              <span class="arb-card__label">Long (pay less)</span>
              <span>${arb.longExchange} ${formatRate(arb.longRate)}</span>
            </div>
            <div class="arb-card__exchange" style="text-align:right">
              <span class="arb-card__label">Short (receive more)</span>
              <span>${arb.shortExchange} ${formatRate(arb.shortRate)}</span>
            </div>
          </div>
        </div>`;
      });

      container.innerHTML = html;

      if (!prefersReducedMotion) {
        gsap.from('.arb-card', { opacity: 0, y: 12, stagger: 0.06, duration: 0.4, ease: 'power3.out' });
      }
    }, 500);
  }

  function renderHeatmap() {
    const container = document.getElementById('heatmap-container');
    if (!container) return;

    const tokens = [...new Set(fundingRates.map((r) => r.token))];
    const exchanges = EXCHANGES;

    let html = '<table class="heatmap-table"><thead><tr><th></th>';
    exchanges.forEach((ex) => {
      html += `<th>${ex}</th>`;
    });
    html += '</tr></thead><tbody>';

    tokens.forEach((token) => {
      html += `<tr><td class="heatmap-label">${token}</td>`;
      exchanges.forEach((exchange) => {
        const rate = fundingRates.find((r) => r.token === token && r.exchange === exchange);
        if (!rate) {
          html += '<td>--</td>';
          return;
        }
        const val = rate.rate8h;
        const bg = getHeatmapColor(val);
        const textColor = Math.abs(val) > 0.02 ? '#fff' : 'var(--color-text)';
        html += `<td style="background:${bg};color:${textColor}" title="${token} @ ${exchange}: ${formatRate(val)}">${formatRate(val)}</td>`;
      });
      html += '</tr>';
    });

    html += '</tbody></table>';
    container.innerHTML = html;
  }

  function getHeatmapColor(val) {
    if (val >= 0) {
      const intensity = Math.min(val / 0.05, 1);
      const r = Math.round(16 + intensity * 0);
      const g = Math.round(100 + intensity * 85);
      const b = Math.round(60 + intensity * 69);
      const a = 0.25 + intensity * 0.55;
      return `rgba(${r},${g},${b},${a})`;
    } else {
      const intensity = Math.min(Math.abs(val) / 0.05, 1);
      const r = Math.round(180 + intensity * 59);
      const g = Math.round(50 - intensity * 20);
      const b = Math.round(40 - intensity * 10);
      const a = 0.25 + intensity * 0.55;
      return `rgba(${r},${g},${b},${a})`;
    }
  }

  /* ============================================================ THEME ============================================================ */
  function initTheme() {
    const stored = localStorage.getItem('funding-rate-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = stored || (prefersDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);

    const heroImg = '{{HERO_IMAGE_URL}}';
    if (heroImg && !heroImg.startsWith('{{')) {
      const bgEl = document.querySelector('.hero__bg-image');
      if (bgEl) { bgEl.style.backgroundImage = `url(${heroImg})`; bgEl.style.opacity = '0.12'; }
    }
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('funding-rate-theme', next);
    renderHistoryChart();
    renderHeatmap();
  }

  /* ============================================================ DATA FETCH ============================================================ */
  async function fetchPrices() {
    try {
      const ids = CONFIG.trackedTokens.join(',');
      const data = await fetchWithRetry(API.prices(ids));
      data.forEach((coin) => {
        priceData[coin.symbol.toUpperCase()] = coin;
      });
    } catch (err) {
      console.warn('CoinGecko price fetch failed, using mock rates only:', err.message);
    }
  }

  async function refreshData() {
    fundingRates = generateFundingRates();
    arbOpportunities = findArbitrageOpportunities(fundingRates);
    await fetchPrices();
    renderHeroMetrics();
    renderFundingTable();
    renderArbList();
    renderHeatmap();
  }

  /* ============================================================ INIT ============================================================ */
  function init() {
    initTheme();
    startClock();

    document.getElementById('theme-toggle').addEventListener('click', toggleTheme);

    const sortBtn = document.getElementById('sort-toggle');
    if (sortBtn) {
      sortBtn.addEventListener('click', () => {
        sortAsc = !sortAsc;
        renderFundingTable();
      });
    }

    renderHeroMetrics();
    renderFundingTable();
    renderHistoryChart();
    renderArbList();
    renderHeatmap();

    fetchPrices().then(() => {
      renderHeroMetrics();
    });

    animateHeroEntrance();
    animateCardEntrance();

    /* No resize listener needed — heatmap is now an HTML table */
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
