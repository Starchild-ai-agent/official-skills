/* ============================================================
   DEX vs CEX Arbitrage — script.js
   Layout: A8 Comparison Layout
   Entrance: D8 translateX(40px) from right
   API: CoinGecko (CEX prices), DeFi Llama (DEX TVL)
   Charts: Chart.js (line)
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

  const API = {
    prices: (ids) => `https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=${ids}&order=market_cap_desc&sparkline=false`,
    tvl: 'https://api.llama.fi/protocols',
  };

  const SYMBOL_MAP = {
    bitcoin: 'BTC', ethereum: 'ETH', solana: 'SOL', cardano: 'ADA',
    polkadot: 'DOT', 'avalanche-2': 'AVAX', ripple: 'XRP', dogecoin: 'DOGE',
    chainlink: 'LINK', arbitrum: 'ARB', optimism: 'OP', uniswap: 'UNI',
  };

  const DEXES = ['Uniswap V3', 'SushiSwap', 'Curve', 'PancakeSwap', '1inch'];
  const ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';

  let cexPrices = {};
  const GAS_PRICE_GWEI = 25 + Math.random() * 30;
  const ETH_PRICE_USD = 3450;

  function generateDexPrices() {
    const tokens = CONFIG.trackedTokens.map((t) => SYMBOL_MAP[t] || t.toUpperCase().substring(0, 4));
    const spreads = [];
    tokens.forEach((token) => {
      const cexPrice = cexPrices[token] || (token === 'BTC' ? 67500 : token === 'ETH' ? 3450 : 178);
      DEXES.forEach((dex) => {
        const slippage = (Math.random() - 0.4) * 0.008;
        const dexPrice = cexPrice * (1 + slippage);
        const spreadPct = ((dexPrice - cexPrice) / cexPrice) * 100;
        const tradeSize = 10000;
        const grossProfit = Math.abs(spreadPct / 100) * tradeSize;
        const gasEstimate = (150000 * GAS_PRICE_GWEI * 1e-9) * ETH_PRICE_USD;
        const netProfit = grossProfit - gasEstimate;
        spreads.push({ token, dex, cexPrice, dexPrice: Math.round(dexPrice * 100) / 100, spreadPct: Math.round(spreadPct * 10000) / 10000, grossProfit: Math.round(grossProfit * 100) / 100, gasEstimate: Math.round(gasEstimate * 100) / 100, netProfit: Math.round(netProfit * 100) / 100, tradeSize });
      });
    });
    return spreads.sort((a, b) => Math.abs(b.spreadPct) - Math.abs(a.spreadPct));
  }

  function generateSpreadHistory() {
    const points = 24;
    const labels = [];
    const datasets = {};
    DEXES.slice(0, 3).forEach((dex) => { datasets[dex] = []; });
    const now = Date.now();
    for (let i = points - 1; i >= 0; i--) {
      const date = new Date(now - i * 3600_000);
      labels.push(date.getHours() + ':00');
      Object.keys(datasets).forEach((dex) => {
        datasets[dex].push(parseFloat(((Math.random() - 0.4) * 0.5).toFixed(3)));
      });
    }
    return { labels, datasets };
  }

  function generateLiquidityData() {
    return DEXES.map((dex) => ({
      name: dex,
      tvl: Math.floor(Math.random() * 5e9 + 5e8),
      volume24h: Math.floor(Math.random() * 1e9 + 1e8),
      pairs: Math.floor(Math.random() * 5000 + 500),
      chain: dex === 'PancakeSwap' ? 'BSC' : dex === 'Curve' ? 'Multi' : 'Ethereum',
    })).sort((a, b) => b.tvl - a.tvl);
  }

  let spreadData = [];
  let spreadHistory = generateSpreadHistory();
  let liquidityData = generateLiquidityData();
  let spreadChart = null;

  /* ---- GSAP ---- */
  function animateHeroEntrance() {
    if (prefersReducedMotion) return;
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    tl.from('.comparison-hero__top', { opacity: 0, y: 20, duration: 0.6 })
      .from('.comparison-hero__side--dex', { opacity: 0, x: -30, duration: 0.6 }, '-=0.2')
      .from('.comparison-hero__vs', { opacity: 0, scale: 0.9, duration: 0.4 }, '-=0.3')
      .from('.comparison-hero__side--cex', { opacity: 0, x: 30, duration: 0.6 }, '-=0.3');
  }

  function animateCardEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.compare-panel, .gas-item', { opacity: 1, x: 0, y: 0 });
      return;
    }
    /* D8: slide from right translateX(40px) */
    gsap.utils.toArray('.compare-panel').forEach((panel, i) => {
      gsap.to(panel, {
        opacity: 1, x: 0, duration: 0.7,
        delay: i * 0.1,
        ease: 'power3.out',
        scrollTrigger: { trigger: panel, start: 'top 88%', once: true }
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

  function formatUSD(v, compact) {
    if (v == null) return '--';
    if (compact) { if (v >= 1e9) return '$' + (v / 1e9).toFixed(2) + 'B'; if (v >= 1e6) return '$' + (v / 1e6).toFixed(1) + 'M'; if (v >= 1e3) return '$' + (v / 1e3).toFixed(1) + 'K'; }
    return '$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function showSkeleton(id, count) {
    const c = document.getElementById(id);
    if (!c) return;
    let h = '';
    for (let i = 0; i < count; i++) h += '<div class="skeleton skeleton--row"></div>';
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

  /* ---- Data Fetch ---- */
  async function fetchCexPrices() {
    try {
      const ids = CONFIG.trackedTokens.join(',');
      const data = await fetchWithRetry(API.prices(ids));
      data.forEach((coin) => { cexPrices[coin.symbol.toUpperCase()] = coin.current_price; });
    } catch (err) {
      cexPrices = { BTC: 67500, ETH: 3450, SOL: 178 };
    }
  }

  async function fetchTVL() {
    try {
      const data = await fetchWithRetry(API.tvl);
      const dexNames = { 'uniswap': 'Uniswap V3', 'sushiswap': 'SushiSwap', 'curve-dex': 'Curve', 'pancakeswap': 'PancakeSwap', '1inch-network': '1inch' };
      data.forEach((protocol) => {
        const slug = protocol.slug;
        if (dexNames[slug]) {
          const match = liquidityData.find((l) => l.name === dexNames[slug]);
          if (match && protocol.tvl) match.tvl = Math.round(protocol.tvl);
        }
      });
    } catch (err) { /* use mock */ }
  }

  /* ---- Renderers ---- */
  function renderHeroMetrics() {
    const bestEl = document.getElementById('hero-best-spread');
    const pairsEl = document.getElementById('hero-pairs');
    const dexAvgEl = document.getElementById('hero-dex-avg');
    const cexAvgEl = document.getElementById('hero-cex-avg');
    const dexBestEl = document.getElementById('hero-dex-best');

    if (spreadData.length > 0) {
      const best = spreadData[0];
      if (bestEl) bestEl.textContent = Math.abs(best.spreadPct).toFixed(3) + '%';
      if (dexBestEl) dexBestEl.textContent = best.dex;

      const tokens = [...new Set(spreadData.map((s) => s.token))];
      if (tokens.length > 0) {
        const avgDex = spreadData.reduce((s, d) => s + d.dexPrice, 0) / spreadData.length;
        const avgCex = spreadData.reduce((s, d) => s + d.cexPrice, 0) / spreadData.length;
        if (dexAvgEl) dexAvgEl.textContent = formatUSD(avgDex, true);
        if (cexAvgEl) cexAvgEl.textContent = formatUSD(avgCex, true);
      }
    }
    if (pairsEl) pairsEl.textContent = spreadData.length.toString();
  }

  function renderComparisonPanels() {
    const dexContainer = document.getElementById('dex-prices');
    const cexContainer = document.getElementById('cex-prices');
    if (!dexContainer || !cexContainer) return;

    const tokens = [...new Set(spreadData.map((s) => s.token))];
    let dexHtml = '';
    let cexHtml = '';

    tokens.forEach((token) => {
      const tokenSpreads = spreadData.filter((s) => s.token === token);
      const bestDex = tokenSpreads[0];
      const cexPrice = bestDex ? bestDex.cexPrice : 0;
      const dexPrice = bestDex ? bestDex.dexPrice : 0;
      const spreadPct = bestDex ? bestDex.spreadPct : 0;
      const spreadClass = Math.abs(spreadPct) > 0.1 ? 'price-item__spread--positive' : 'price-item__spread--negative';

      dexHtml += `<div class="price-item">
        <div><span class="price-item__token">${token}</span><span class="price-item__dex-name">${bestDex ? bestDex.dex : '--'}</span></div>
        <span class="price-item__price" style="color:var(--color-dex)">$${dexPrice.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
      </div>`;

      cexHtml += `<div class="price-item">
        <div><span class="price-item__token">${token}</span><span class="price-item__dex-name">Binance/Coinbase</span></div>
        <div style="text-align:right">
          <span class="price-item__price" style="color:var(--color-cex)">$${cexPrice.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
          <span class="price-item__spread ${spreadClass}">${spreadPct > 0 ? '+' : ''}${spreadPct.toFixed(3)}%</span>
        </div>
      </div>`;
    });

    dexContainer.innerHTML = dexHtml;
    cexContainer.innerHTML = cexHtml;

    if (!prefersReducedMotion) {
      gsap.from('#dex-prices .price-item', { opacity: 0, x: -16, stagger: 0.06, duration: 0.4, ease: 'power3.out' });
      gsap.from('#cex-prices .price-item', { opacity: 0, x: 16, stagger: 0.06, duration: 0.4, ease: 'power3.out' });
    }
  }

  function renderSpreadTable() {
    const container = document.getElementById('spread-table');
    if (!container) return;
    showSkeleton('spread-table', 8);
    setTimeout(() => {
      let html = '<table class="spread-table"><thead><tr><th>Token</th><th>DEX</th><th>CEX Price</th><th>DEX Price</th><th>Spread</th><th>Gross ($10K)</th><th>Gas Est.</th><th>Net Profit</th></tr></thead><tbody>';
      spreadData.forEach((row) => {
        const spreadClass = Math.abs(row.spreadPct) > 0.1 ? 'spread-positive' : 'spread-negative';
        const netColor = row.netProfit > 0 ? 'var(--color-bullish)' : 'var(--color-bearish)';
        html += `<tr>
          <td><span class="token-name">${row.token}</span></td>
          <td>${row.dex}</td>
          <td>$${row.cexPrice.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
          <td>$${row.dexPrice.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
          <td class="${spreadClass}">${row.spreadPct > 0 ? '+' : ''}${row.spreadPct.toFixed(3)}%</td>
          <td class="profit-cell">${formatUSD(row.grossProfit)}</td>
          <td style="color:var(--color-warning)">${formatUSD(row.gasEstimate)}</td>
          <td style="color:${netColor};font-weight:600">${formatUSD(row.netProfit)}</td>
        </tr>`;
      });
      html += '</tbody></table>';
      container.innerHTML = html;
      if (!prefersReducedMotion) gsap.from('.spread-table tbody tr', { opacity: 0, x: 20, stagger: 0.03, duration: 0.3, ease: 'power3.out' });
    }, 300);
  }

  function renderSpreadChart() {
    const canvas = document.getElementById('spread-chart');
    if (!canvas) return;
    const cs = getComputedStyle(document.documentElement);
    const colors = getChartColors();
    const exchanges = Object.keys(spreadHistory.datasets);
    const datasets = exchanges.map((ex, i) => ({
      label: ex, data: spreadHistory.datasets[ex], borderColor: colors[i], backgroundColor: 'transparent', borderWidth: 2, pointRadius: 0, pointHoverRadius: 4, tension: 0.3,
    }));
    if (spreadChart) spreadChart.destroy();
    spreadChart = new Chart(canvas, {
      type: 'line',
      data: { labels: spreadHistory.labels, datasets },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { position: 'top', labels: { color: cs.getPropertyValue('--color-text-secondary').trim(), font: { family: "'Fira Code', monospace", size: 11 }, boxWidth: 12, boxHeight: 2, padding: 16 } },
          tooltip: { backgroundColor: cs.getPropertyValue('--color-surface').trim(), titleColor: cs.getPropertyValue('--color-text').trim(), bodyColor: cs.getPropertyValue('--color-text-secondary').trim(), borderColor: cs.getPropertyValue('--color-border').trim(), borderWidth: 1, titleFont: { family: "'Fira Code', monospace", size: 11 }, bodyFont: { family: "'Fira Code', monospace", size: 11 }, padding: 10, callbacks: { label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(3)}%` } },
        },
        scales: {
          x: { grid: { color: cs.getPropertyValue('--color-border').trim(), lineWidth: 0.5 }, ticks: { color: cs.getPropertyValue('--color-text-muted').trim(), font: { family: "'Fira Code', monospace", size: 10 }, maxTicksLimit: 8 } },
          y: { grid: { color: cs.getPropertyValue('--color-border').trim(), lineWidth: 0.5 }, ticks: { color: cs.getPropertyValue('--color-text-muted').trim(), font: { family: "'Fira Code', monospace", size: 10 }, callback: (v) => v.toFixed(2) + '%' } },
        },
      },
    });
  }

  function renderLiquidityList() {
    const container = document.getElementById('liquidity-list');
    if (!container) return;
    const maxTVL = Math.max(...liquidityData.map((l) => l.tvl));
    let html = '';
    liquidityData.forEach((liq) => {
      const fillPct = maxTVL > 0 ? (liq.tvl / maxTVL) * 100 : 0;
      html += `<div class="liq-item">
        <div class="liq-item__header"><span class="liq-item__name">${liq.name}</span><span class="liq-item__tvl">${formatUSD(liq.tvl, true)}</span></div>
        <div class="liq-item__detail"><span>${liq.chain}</span><span>Vol: ${formatUSD(liq.volume24h, true)}</span></div>
        <div class="liq-item__bar"><div class="liq-item__bar-fill" style="width:${fillPct}%"></div></div>
      </div>`;
    });
    container.innerHTML = html;
    if (!prefersReducedMotion) gsap.from('.liq-item', { opacity: 0, x: 20, stagger: 0.06, duration: 0.4, ease: 'power3.out' });
  }

  function renderGasAnalysis() {
    const container = document.getElementById('gas-analysis');
    if (!container) return;
    const tokens = [...new Set(spreadData.map((s) => s.token))];
    let html = '';
    tokens.forEach((token) => {
      const tokenSpreads = spreadData.filter((s) => s.token === token);
      const bestSpread = tokenSpreads[0];
      if (!bestSpread) return;
      const gasUSD = bestSpread.gasEstimate;
      const gross = bestSpread.grossProfit;
      const net = bestSpread.netProfit;
      let verdict = 'unprofitable', verdictClass = 'gas-item__verdict--unprofitable';
      if (net > gasUSD * 0.5) { verdict = 'profitable'; verdictClass = 'gas-item__verdict--profitable'; }
      else if (net > 0) { verdict = 'marginal'; verdictClass = 'gas-item__verdict--marginal'; }
      const netColor = net > 0 ? 'var(--color-bullish)' : 'var(--color-bearish)';
      html += `<div class="gas-item">
        <div class="gas-item__header"><span class="gas-item__token">${token}</span><span class="gas-item__verdict ${verdictClass}">${verdict}</span></div>
        <div class="gas-item__rows">
          <div class="gas-item__row"><span class="gas-item__label">Best Spread</span><span class="gas-item__value">${Math.abs(bestSpread.spreadPct).toFixed(3)}%</span></div>
          <div class="gas-item__row"><span class="gas-item__label">Best DEX</span><span class="gas-item__value">${bestSpread.dex}</span></div>
          <div class="gas-item__row"><span class="gas-item__label">Gross Profit</span><span class="gas-item__value" style="color:var(--color-bullish)">${formatUSD(gross)}</span></div>
          <div class="gas-item__row"><span class="gas-item__label">Gas Cost</span><span class="gas-item__value" style="color:var(--color-warning)">${formatUSD(gasUSD)}</span></div>
          <div class="gas-item__row"><span class="gas-item__label">Gas (gwei)</span><span class="gas-item__value">${GAS_PRICE_GWEI.toFixed(0)}</span></div>
        </div>
        <div class="gas-item__net"><span>Net Profit</span><span style="color:${netColor}">${formatUSD(net)}</span></div>
      </div>`;
    });
    container.innerHTML = html;
    if (!prefersReducedMotion) {
      gsap.from('.gas-item', { opacity: 0, x: 40, stagger: 0.08, duration: 0.5, ease: 'power3.out' });
    }
  }

  /* ---- Theme ---- */
  function initTheme() {
    const stored = localStorage.getItem('dex-arb-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = stored || (prefersDark ? 'dark' : 'light');
    if (theme === 'light') document.documentElement.setAttribute('data-theme', 'light');
  }

  function toggleTheme() {
    const isLight = document.documentElement.getAttribute('data-theme') === 'light';
    if (isLight) { document.documentElement.removeAttribute('data-theme'); localStorage.setItem('dex-arb-theme', 'dark'); }
    else { document.documentElement.setAttribute('data-theme', 'light'); localStorage.setItem('dex-arb-theme', 'light'); }
    renderSpreadChart();
  }

  /* ---- Refresh ---- */
  async function refreshData() {
    await fetchCexPrices();
    spreadData = generateDexPrices();
    spreadHistory = generateSpreadHistory();
    renderHeroMetrics();
    renderComparisonPanels();
    renderSpreadTable();
    renderSpreadChart();
    renderGasAnalysis();
  }

  /* ---- Init ---- */
  async function init() {
    initTheme(); startClock();
    document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
    animateHeroEntrance();

    await fetchCexPrices();
    spreadData = generateDexPrices();

    renderHeroMetrics();
    renderComparisonPanels();
    renderSpreadTable();
    renderSpreadChart();
    renderLiquidityList();
    renderGasAnalysis();

    fetchTVL().then(() => renderLiquidityList());

    animateCardEntrance();

  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
