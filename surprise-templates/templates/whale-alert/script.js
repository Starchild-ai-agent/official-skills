/* ============================================================
   Whale Alert Monitor — script.js
   Layout: A10 Notification/Alert Layout
   Entrance: D10 translateX(-50px) from left
   API: CoinGecko (token prices for USD conversion)
   Mock Data: Built-in whale transfer simulation
   Charts: Chart.js (horizontal bar), Canvas (heatmap)
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
        if (raw.startsWith('{{')) return ['bitcoin', 'ethereum', 'tether'];
        return JSON.parse(raw);
      } catch { return ['bitcoin', 'ethereum', 'tether']; }
    })(),
    maxRetries: 2, retryBaseDelay: 1500, refreshInterval: 60_000,
  };

  const API = {
    prices: (ids) => `https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=${ids}&order=market_cap_desc&sparkline=false`,
  };

  const SYMBOL_MAP = {
    bitcoin: 'BTC', ethereum: 'ETH', tether: 'USDT', solana: 'SOL',
    'usd-coin': 'USDC', 'binancecoin': 'BNB', ripple: 'XRP', cardano: 'ADA',
  };

  const ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';

  let tokenPrices = { BTC: 67500, ETH: 3450, USDT: 1.0, SOL: 178, USDC: 1.0, BNB: 610, XRP: 0.52, ADA: 0.45 };

  const WHALE_ADDRESSES = [
    { label: 'Whale Alpha', addr: '0x1a2b...f3e4', tag: 'Unknown Whale' },
    { label: 'Binance Hot', addr: '0x28c6...a9d1', tag: 'Binance' },
    { label: 'Coinbase Prime', addr: '0x3f5c...b2e7', tag: 'Coinbase' },
    { label: 'Whale Bravo', addr: '0x4d8e...c1f0', tag: 'Unknown Whale' },
    { label: 'Kraken', addr: '0x5a7f...d4c3', tag: 'Kraken' },
    { label: 'OKX', addr: '0x6b9a...e5d2', tag: 'OKX' },
    { label: 'Whale Charlie', addr: '0x7c0b...f6e1', tag: 'Unknown Whale' },
    { label: 'Bitfinex', addr: '0x8d1c...a7f0', tag: 'Bitfinex' },
    { label: 'Whale Delta', addr: '0x9e2d...b8a3', tag: 'Unknown Whale' },
    { label: 'Gemini', addr: '0xa3f4...c9b2', tag: 'Gemini' },
  ];

  function generateTransfers(count = 20) {
    const tokens = CONFIG.trackedTokens.map((t) => SYMBOL_MAP[t] || t.toUpperCase().substring(0, 4));
    const transfers = [];
    const now = Date.now();
    for (let i = 0; i < count; i++) {
      const token = tokens[Math.floor(Math.random() * tokens.length)];
      const price = tokenPrices[token] || 100;
      let amount;
      if (token === 'BTC') amount = 50 + Math.random() * 2000;
      else if (token === 'ETH') amount = 500 + Math.random() * 30000;
      else if (token === 'USDT' || token === 'USDC') amount = 1_000_000 + Math.random() * 50_000_000;
      else amount = 10000 + Math.random() * 500000;
      const from = WHALE_ADDRESSES[Math.floor(Math.random() * WHALE_ADDRESSES.length)];
      let to = WHALE_ADDRESSES[Math.floor(Math.random() * WHALE_ADDRESSES.length)];
      while (to.addr === from.addr) to = WHALE_ADDRESSES[Math.floor(Math.random() * WHALE_ADDRESSES.length)];
      const usdValue = amount * price;
      const timestamp = now - Math.random() * 86400_000;
      transfers.push({ token, amount, usdValue, from, to, timestamp, hash: '0x' + Math.random().toString(16).slice(2, 14) });
    }
    return transfers.sort((a, b) => b.timestamp - a.timestamp);
  }

  function generateHeatmapData() {
    const data = [];
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    for (let d = 0; d < 7; d++) {
      for (let h = 0; h < 24; h++) {
        const base = h >= 8 && h <= 20 ? 8 : 3;
        const val = Math.floor(base + Math.random() * 12);
        data.push({ day: d, dayLabel: days[d], hour: h, value: val });
      }
    }
    return data;
  }

  function generateFlowData() {
    const tokens = CONFIG.trackedTokens.slice(0, 5).map((t) => SYMBOL_MAP[t] || t.toUpperCase().substring(0, 4));
    return tokens.map((token) => ({
      token,
      inflow: Math.round(Math.random() * 500 + 100),
      outflow: -Math.round(Math.random() * 500 + 100),
    }));
  }

  function generateLeaderboard() {
    return WHALE_ADDRESSES.map((w) => ({
      ...w,
      txCount: Math.floor(5 + Math.random() * 40),
      totalVolume: Math.round(Math.random() * 200_000_000 + 5_000_000),
      lastSeen: Date.now() - Math.random() * 7200_000,
    })).sort((a, b) => b.totalVolume - a.totalVolume);
  }

  /* ---- Utilities ---- */
  async function fetchWithRetry(url, retries = CONFIG.maxRetries) {
    for (let i = 0; i <= retries; i++) {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
      } catch (err) {
        if (i === retries) throw err;
        await new Promise((r) => setTimeout(r, CONFIG.retryBaseDelay * (i + 1)));
      }
    }
  }

  function fmt(n) {
    if (n >= 1e9) return '$' + (n / 1e9).toFixed(2) + 'B';
    if (n >= 1e6) return '$' + (n / 1e6).toFixed(2) + 'M';
    if (n >= 1e3) return '$' + (n / 1e3).toFixed(1) + 'K';
    return '$' + n.toFixed(2);
  }

  function fmtAmount(n, token) {
    if (token === 'USDT' || token === 'USDC') {
      if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M';
      return (n / 1e3).toFixed(1) + 'K';
    }
    if (n >= 1000) return n.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return n.toFixed(2);
  }

  function timeAgo(ts) {
    const diff = (Date.now() - ts) / 1000;
    if (diff < 60) return Math.floor(diff) + 's ago';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    return Math.floor(diff / 3600) + 'h ago';
  }

  function getSeverity(usdValue) {
    if (usdValue >= 50_000_000) return 'critical';
    if (usdValue >= 10_000_000) return 'high';
    return '';
  }

  /* ---- Theme ---- */
  (function initTheme() {
    const saved = localStorage.getItem('whale-alert-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (prefersDark ? 'dark' : 'light');
    if (theme === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
    document.getElementById('theme-toggle').addEventListener('click', () => {
      const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      if (next === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
      else document.documentElement.removeAttribute('data-theme');
      localStorage.setItem('whale-alert-theme', next);
    });
  })();

  /* ---- Clock ---- */
  function updateClock() {
    const el = document.getElementById('hero-time');
    if (el) {
      const now = new Date();
      el.textContent = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
      el.setAttribute('datetime', now.toISOString());
    }
  }
  updateClock();
  setInterval(updateClock, 1000);

  /* ---- Charts ---- */
  let flowChart = null;

  function getChartColors() {
    const s = getComputedStyle(document.documentElement);
    return {
      text: s.getPropertyValue('--color-text').trim(),
      muted: s.getPropertyValue('--color-text-muted').trim(),
      border: s.getPropertyValue('--color-border').trim(),
      surface: s.getPropertyValue('--color-surface').trim(),
      c1: s.getPropertyValue('--chart-1').trim(),
      c2: s.getPropertyValue('--chart-2').trim(),
    };
  }

  function renderFlowChart(data) {
    const ctx = document.getElementById('flow-chart');
    if (!ctx) return;
    const c = getChartColors();
    const labels = data.map((d) => d.token);
    const inflows = data.map((d) => d.inflow);
    const outflows = data.map((d) => d.outflow);

    if (flowChart) flowChart.destroy();
    flowChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          { label: 'Exchange Inflow ($M)', data: inflows, backgroundColor: c.c1 + 'cc', borderRadius: 4 },
          { label: 'Exchange Outflow ($M)', data: outflows, backgroundColor: c.c2 + 'cc', borderRadius: 4 },
        ],
      },
      options: {
        indexAxis: 'y',
        maintainAspectRatio: false,
        responsive: true,
        plugins: {
          legend: { labels: { color: c.text, font: { family: "'IBM Plex Sans',sans-serif", size: 11 } } },
          tooltip: { backgroundColor: c.surface, titleColor: c.text, bodyColor: c.text, borderColor: c.c1, borderWidth: 1 },
        },
        scales: {
          x: { grid: { color: c.border }, ticks: { color: c.muted, font: { family: "'Source Code Pro',monospace", size: 10 } } },
          y: { grid: { display: false }, ticks: { color: c.text, font: { family: "'IBM Plex Sans',sans-serif", size: 12 } } },
        },
      },
    });
  }

  /* ---- Heatmap (Canvas) ---- */
  function renderHeatmap(data) {
    const canvas = document.getElementById('heatmap-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    const marginLeft = 40;
    const marginTop = 20;
    const marginBottom = 24;
    const marginRight = 10;
    const cols = 24;
    const rows = 7;
    const cellW = (w - marginLeft - marginRight) / cols;
    const cellH = (h - marginTop - marginBottom) / rows;
    const maxVal = Math.max(...data.map((d) => d.value));
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

    ctx.clearRect(0, 0, w, h);

    data.forEach((d) => {
      const x = marginLeft + d.hour * cellW;
      const y = marginTop + d.day * cellH;
      const intensity = d.value / maxVal;
      const r = Math.round(0 + intensity * 0);
      const g = Math.round(40 + intensity * 79);
      const b = Math.round(80 + intensity * 102);
      ctx.fillStyle = `rgba(${r},${g},${b},${0.15 + intensity * 0.85})`;
      ctx.beginPath();
      ctx.roundRect(x + 1, y + 1, cellW - 2, cellH - 2, 3);
      ctx.fill();

      if (cellW > 18 && cellH > 18) {
        ctx.fillStyle = intensity > 0.6 ? '#fff' : 'rgba(224,228,234,0.5)';
        ctx.font = '10px "Source Code Pro",monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(d.value, x + cellW / 2, y + cellH / 2);
      }
    });

    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--color-text-muted').trim() || '#8a90a0';
    ctx.font = '10px "Source Code Pro",monospace';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    days.forEach((day, i) => {
      ctx.fillText(day, marginLeft - 6, marginTop + i * cellH + cellH / 2);
    });

    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    for (let h2 = 0; h2 < 24; h2 += 3) {
      ctx.fillText(h2 + ':00', marginLeft + h2 * cellW + cellW / 2, marginTop + rows * cellH + 6);
    }
  }

  /* ---- Feed ---- */
  function renderFeed(transfers) {
    const container = document.getElementById('feed-container');
    if (!container) return;
    container.innerHTML = transfers.slice(0, 15).map((tx) => {
      const iconClass = tx.token === 'BTC' ? 'btc' : tx.token === 'ETH' ? 'eth' : tx.token === 'USDT' || tx.token === 'USDC' ? 'usdt' : 'other';
      const severity = getSeverity(tx.usdValue);
      const severityClass = severity ? ` alert-item--${severity}` : '';
      return `<div class="alert-item${severityClass}">
        <div class="alert-item__icon alert-item__icon--${iconClass}">${tx.token}</div>
        <div class="alert-item__body">
          <div class="alert-item__amount">${fmtAmount(tx.amount, tx.token)} ${tx.token}</div>
          <div class="alert-item__detail">${tx.from.tag} → ${tx.to.tag}</div>
        </div>
        <div class="alert-item__meta">
          <span class="alert-item__usd">${fmt(tx.usdValue)}</span>
          <div class="alert-item__time">${timeAgo(tx.timestamp)}</div>
        </div>
      </div>`;
    }).join('');

    /* D10: animate from left */
    if (!prefersReducedMotion) {
      gsap.fromTo('.alert-feed .alert-item', { opacity: 0, x: -50 }, { opacity: 1, x: 0, stagger: 0.05, duration: 0.5, ease: 'power3.out' });
    } else {
      gsap.set('.alert-feed .alert-item', { opacity: 1, x: 0 });
    }
  }

  /* ---- Leaderboard ---- */
  function renderLeaderboard(data) {
    const wrap = document.getElementById('leaderboard-wrap');
    if (!wrap) return;
    wrap.innerHTML = `<table class="leaderboard-table">
      <thead><tr><th>#</th><th>Address</th><th>Tag</th><th>Txns</th><th>Volume (24h)</th><th>Last Seen</th></tr></thead>
      <tbody>${data.map((w, i) => `<tr>
        <td class="rank">${i + 1}</td>
        <td class="addr">${w.addr}</td>
        <td>${w.tag}</td>
        <td>${w.txCount}</td>
        <td class="volume">${fmt(w.totalVolume)}</td>
        <td>${timeAgo(w.lastSeen)}</td>
      </tr>`).join('')}</tbody>
    </table>`;
  }

  /* ---- Hero metrics ---- */
  function updateHero(transfers) {
    const alertCount = document.getElementById('hero-alert-count');
    const largest = document.getElementById('hero-largest');
    const volume = document.getElementById('hero-volume');
    if (alertCount) alertCount.textContent = transfers.length;
    if (largest && transfers.length) {
      const max = transfers.reduce((a, b) => a.usdValue > b.usdValue ? a : b);
      largest.textContent = fmt(max.usdValue);
    }
    if (volume) {
      const total = transfers.reduce((s, t) => s + t.usdValue, 0);
      volume.textContent = fmt(total);
    }
  }

  /* ---- GSAP Animations ---- */
  function initAnimations() {
    if (prefersReducedMotion) {
      gsap.set('.alert-item, .alert-item--chart, .alert-item--table', { opacity: 1, x: 0 });
      return;
    }

    /* Hero entrance */
    gsap.from('.alert-banner__bar', { opacity: 0, y: -10, duration: 0.5, ease: 'power3.out' });
    gsap.from('.alert-banner__content', { opacity: 0, y: 20, duration: 0.6, delay: 0.1, ease: 'power3.out' });
    gsap.from('.alert-banner__kpi', { opacity: 0, y: 16, stagger: 0.08, duration: 0.5, delay: 0.3, ease: 'power3.out' });

    /* D10: sections slide from left */
    gsap.utils.toArray('.alert-item--chart, .alert-item--table').forEach((item, i) => {
      gsap.from(item, {
        opacity: 0, x: -30, duration: 0.6,
        delay: i * 0.1,
        ease: 'power3.out',
        scrollTrigger: { trigger: item, start: 'top 88%', once: true }
      });
    });

    gsap.utils.toArray('.alert-section').forEach((section) => {
      gsap.from(section.querySelector('.alert-section__header'), {
        opacity: 0, x: -20, duration: 0.5, ease: 'power3.out',
        scrollTrigger: { trigger: section, start: 'top 85%', once: true }
      });
    });
  }

  /* ---- Main ---- */
  async function init() {
    try {
      const ids = CONFIG.trackedTokens.join(',');
      const priceData = await fetchWithRetry(API.prices(ids));
      if (priceData && Array.isArray(priceData)) {
        priceData.forEach((coin) => {
          const sym = SYMBOL_MAP[coin.id] || coin.symbol?.toUpperCase();
          if (sym) tokenPrices[sym] = coin.current_price;
        });
      }
    } catch (e) { /* Use default prices */ }

    const transfers = generateTransfers(20);
    const heatmapData = generateHeatmapData();
    const flowData = generateFlowData();
    const leaderboard = generateLeaderboard();

    updateHero(transfers);
    renderFeed(transfers);
    renderHeatmap(heatmapData);
    renderFlowChart(flowData);
    renderLeaderboard(leaderboard);
    initAnimations();
  }

  init();

  /* Resize heatmap */
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => renderHeatmap(generateHeatmapData()), 250);
  });
})();
