/* ============================================================
   Smart Money Tracker — script.js
   Layout: A19 Feed/Stream + H4 Asymmetric Hero
   Entrance: D19 alternating translateX odd:-20px even:+20px
   API: CoinGecko (free, no key) for token prices
   Charts: Chart.js (doughnut + bar)
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

  /* ============================================================
     MOCK DATA
     ============================================================ */
  const SMART_MONEY_ENTITIES = [
    { name: 'Jump Trading', type: 'institution' },
    { name: 'Wintermute', type: 'market-maker' },
    { name: 'Alameda Wallet', type: 'whale' },
    { name: 'Galaxy Digital', type: 'institution' },
    { name: 'Paradigm', type: 'vc' },
    { name: 'a16z Capital', type: 'vc' },
    { name: 'Whale 0x7a3...f2d', type: 'whale' },
    { name: 'DWF Labs', type: 'market-maker' },
    { name: 'Binance Hot Wallet', type: 'exchange' },
    { name: 'Coinbase Prime', type: 'exchange' },
  ];

  function generateTimeline() {
    const actions = ['buy', 'sell', 'transfer'];
    const tokens = CONFIG.trackedTokens.map((t) => SYMBOL_MAP[t] || t.toUpperCase().substring(0, 4));
    const items = [];
    const now = Date.now();

    for (let i = 0; i < 15; i++) {
      const entity = SMART_MONEY_ENTITIES[Math.floor(Math.random() * SMART_MONEY_ENTITIES.length)];
      const action = actions[Math.floor(Math.random() * actions.length)];
      const token = tokens[Math.floor(Math.random() * tokens.length)];
      const hoursAgo = Math.floor(Math.random() * 48);
      const amount = (Math.random() * 5000 + 100).toFixed(0);
      const usdValue = (Math.random() * 10_000_000 + 50_000).toFixed(0);

      items.push({
        entity: entity.name, type: entity.type, action, token,
        amount: Number(amount), usdValue: Number(usdValue),
        time: new Date(now - hoursAgo * 3600_000),
      });
    }
    return items.sort((a, b) => b.time - a.time);
  }

  const INSTITUTIONAL_HOLDINGS = [
    { name: 'Grayscale', pct: 28 },
    { name: 'MicroStrategy', pct: 18 },
    { name: 'Galaxy Digital', pct: 12 },
    { name: 'Jump Trading', pct: 10 },
    { name: 'Paradigm', pct: 8 },
    { name: 'Others', pct: 24 },
  ];

  function generateFlowData() {
    const tokens = CONFIG.trackedTokens.map((t) => SYMBOL_MAP[t] || t.toUpperCase().substring(0, 4));
    return tokens.map((t) => ({
      token: t,
      inflow: Math.floor(Math.random() * 8_000_000 + 500_000),
      outflow: -Math.floor(Math.random() * 6_000_000 + 300_000),
    }));
  }

  function computeSignal(timeline) {
    const buys = timeline.filter((t) => t.action === 'buy');
    const sells = timeline.filter((t) => t.action === 'sell');
    const buyVol = buys.reduce((s, t) => s + t.usdValue, 0);
    const sellVol = sells.reduce((s, t) => s + t.usdValue, 0);
    const total = buyVol + sellVol;
    if (total === 0) return { score: 50, label: 'Neutral', buyPct: 50, sellPct: 50 };
    const buyPct = Math.round((buyVol / total) * 100);
    const score = buyPct;
    let label = 'Neutral';
    if (score >= 70) label = 'Bullish';
    else if (score >= 55) label = 'Slightly Bullish';
    else if (score <= 30) label = 'Bearish';
    else if (score <= 45) label = 'Slightly Bearish';
    return { score, label, buyPct, sellPct: 100 - buyPct };
  }

  let timelineData = generateTimeline();
  let flowData = generateFlowData();
  let signal = computeSignal(timelineData);
  let holdingsChart = null;
  let flowChart = null;

  /* ============================================================
     GSAP — D19 alternating translateX entrance
     ============================================================ */
  function animateHeroEntrance() {
    if (prefersReducedMotion) { gsap.set('.hero__left > *, .hero__right > *', { opacity: 1, y: 0 }); return; }
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    tl.from('.hero__status-bar', { opacity: 0, y: 20, duration: 0.6 })
      .from('.hero__title', { opacity: 0, y: 30, duration: 0.7, ease: 'power4.out' }, '-=0.3')
      .from('.hero__subtitle', { opacity: 0, y: 15, duration: 0.4 }, '-=0.3')
      .from('.hero__signal-badge', { opacity: 0, y: 20, duration: 0.5 }, '-=0.2')
      .from('.hero__stat-card', { opacity: 0, x: 30, stagger: 0.1, duration: 0.5 }, '-=0.4');
  }

  function animateFeedEntrance() {
    if (prefersReducedMotion) { gsap.set('.feed-item, .timeline-item', { opacity: 1, x: 0 }); return; }
    /* D19: alternating direction */
    gsap.utils.toArray('.feed-item').forEach((el, i) => {
      const xFrom = i % 2 === 0 ? -20 : 20;
      gsap.to(el, {
        opacity: 1, x: 0, duration: 0.6, delay: i * 0.1, ease: 'power3.out',
        scrollTrigger: { trigger: el, start: 'top 90%', once: true },
      });
    });
  }

  /* ============================================================
     UTILITIES
     ============================================================ */
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

  function formatUSD(v, compact) {
    if (v == null) return '--';
    if (compact) {
      if (v >= 1e9) return '$' + (v / 1e9).toFixed(2) + 'B';
      if (v >= 1e6) return '$' + (v / 1e6).toFixed(2) + 'M';
      if (v >= 1e3) return '$' + (v / 1e3).toFixed(1) + 'K';
    }
    return '$' + v.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  }

  function timeAgo(date) {
    const diff = Date.now() - date.getTime();
    const mins = Math.floor(diff / 60_000);
    if (mins < 60) return mins + 'm ago';
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return hrs + 'h ago';
    return Math.floor(hrs / 24) + 'd ago';
  }

  function showSkeleton(id, count, type) {
    const c = document.getElementById(id);
    if (!c) return;
    let h = '';
    for (let i = 0; i < count; i++) {
      if (type === 'timeline') h += '<div class="timeline-item" style="opacity:1;transform:none"><div class="skeleton" style="width:48px;height:14px"></div><div class="skeleton" style="width:40px;height:18px;border-radius:3px"></div><div style="flex:1"><div class="skeleton skeleton--text"></div></div><div class="skeleton" style="width:60px;height:14px"></div></div>';
      else if (type === 'signal') h += '<div class="signal-row"><div class="skeleton" style="width:60px;height:12px"></div><div class="skeleton" style="width:40px;height:12px"></div></div>';
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

  /* ============================================================
     RENDERERS
     ============================================================ */
  function renderHeroMetrics() {
    const signalEl = document.getElementById('hero-signal');
    const walletsEl = document.getElementById('hero-wallets');
    const movesEl = document.getElementById('hero-moves');
    const ratioEl = document.getElementById('hero-ratio');

    if (signalEl) {
      signalEl.textContent = signal.label.toUpperCase();
      signalEl.style.color = signal.score >= 55 ? 'var(--color-bullish)' : signal.score <= 45 ? 'var(--color-bearish)' : 'var(--color-neutral)';
    }
    if (walletsEl) walletsEl.textContent = SMART_MONEY_ENTITIES.length.toString();
    if (movesEl) movesEl.textContent = timelineData.filter((t) => (Date.now() - t.time.getTime()) < 86400_000).length.toString();
    if (ratioEl) ratioEl.textContent = signal.buyPct + '/' + signal.sellPct;
  }

  function renderTimeline() {
    const container = document.getElementById('timeline');
    if (!container) return;

    showSkeleton('timeline', 8, 'timeline');
    setTimeout(() => {
      let html = '';
      timelineData.forEach((item) => {
        const actionClass = `timeline-item__action--${item.action}`;
        html += `<div class="timeline-item">
          <span class="timeline-item__time">${timeAgo(item.time)}</span>
          <span class="timeline-item__action ${actionClass}">${item.action}</span>
          <div class="timeline-item__info">
            <div class="timeline-item__entity">${item.entity}</div>
            <div class="timeline-item__detail">${item.amount.toLocaleString()} ${item.token}</div>
          </div>
          <span class="timeline-item__amount">${formatUSD(item.usdValue, true)}</span>
        </div>`;
      });
      container.innerHTML = html;
      if (!prefersReducedMotion) {
        gsap.utils.toArray('.timeline-item').forEach((el, i) => {
          const xFrom = i % 2 === 0 ? -20 : 20;
          gsap.fromTo(el, { opacity: 0, x: xFrom }, { opacity: 1, x: 0, duration: 0.4, delay: i * 0.04, ease: 'power3.out' });
        });
      }
    }, 400);
  }

  function renderSignalGauge() {
    const canvas = document.getElementById('signal-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr; canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    const cx = w / 2;
    const cy = h - 10;
    const radius = Math.min(cx, cy) - 10;
    const startAngle = Math.PI;

    const segments = [
      { end: 0.3, color: getComputedStyle(document.documentElement).getPropertyValue('--color-bearish').trim() || '#ef4444' },
      { end: 0.45, color: '#ff8c42' },
      { end: 0.55, color: getComputedStyle(document.documentElement).getPropertyValue('--color-neutral').trim() || '#eab308' },
      { end: 0.7, color: '#6bcb77' },
      { end: 1.0, color: getComputedStyle(document.documentElement).getPropertyValue('--color-bullish').trim() || '#22c55e' },
    ];

    let prev = 0;
    segments.forEach((seg) => {
      ctx.beginPath(); ctx.arc(cx, cy, radius, startAngle + prev * Math.PI, startAngle + seg.end * Math.PI);
      ctx.lineWidth = 12; ctx.strokeStyle = seg.color; ctx.lineCap = 'round'; ctx.globalAlpha = 0.15;
      ctx.stroke(); prev = seg.end;
    });

    ctx.globalAlpha = 1;
    const grad = ctx.createLinearGradient(cx - radius, cy, cx + radius, cy);
    grad.addColorStop(0, segments[0].color);
    grad.addColorStop(0.5, segments[2].color);
    grad.addColorStop(1, segments[4].color);

    const progress = signal.score / 100;
    if (prefersReducedMotion) {
      drawGaugeAt(ctx, cx, cy, radius, startAngle, grad, progress, segments);
    } else {
      const obj = { p: 0 };
      gsap.to(obj, { p: progress, duration: 1.5, ease: 'power3.out', onUpdate: () => {
        ctx.clearRect(0, 0, w, h);
        let p2 = 0;
        segments.forEach((seg) => {
          ctx.beginPath(); ctx.arc(cx, cy, radius, startAngle + p2 * Math.PI, startAngle + seg.end * Math.PI);
          ctx.lineWidth = 12; ctx.strokeStyle = seg.color; ctx.lineCap = 'round'; ctx.globalAlpha = 0.15; ctx.stroke(); p2 = seg.end;
        });
        ctx.globalAlpha = 1;
        drawGaugeAt(ctx, cx, cy, radius, startAngle, grad, obj.p, segments);
      }});
    }

    const valueEl = document.getElementById('signal-value');
    const labelEl = document.getElementById('signal-label');
    if (valueEl) valueEl.textContent = signal.score;
    if (labelEl) {
      labelEl.textContent = signal.label;
      labelEl.style.color = signal.score >= 55 ? 'var(--color-bullish)' : signal.score <= 45 ? 'var(--color-bearish)' : 'var(--color-neutral)';
    }

    const breakdown = document.getElementById('signal-breakdown');
    if (breakdown) {
      breakdown.innerHTML = `
        <div class="signal-row"><span class="signal-row__label">Buy Volume</span><span class="signal-row__value text-up">${signal.buyPct}%</span></div>
        <div class="signal-row"><span class="signal-row__label">Sell Volume</span><span class="signal-row__value text-down">${signal.sellPct}%</span></div>
        <div class="signal-row"><span class="signal-row__label">Active Entities</span><span class="signal-row__value">${SMART_MONEY_ENTITIES.length}</span></div>
        <div class="signal-row"><span class="signal-row__label">24h Transactions</span><span class="signal-row__value">${timelineData.filter((t) => (Date.now() - t.time.getTime()) < 86400_000).length}</span></div>`;
    }
  }

  function drawGaugeAt(ctx, cx, cy, radius, startAngle, grad, progress) {
    const activeEnd = startAngle + progress * Math.PI;
    ctx.beginPath(); ctx.arc(cx, cy, radius, startAngle, activeEnd);
    ctx.lineWidth = 12; ctx.strokeStyle = grad; ctx.lineCap = 'round'; ctx.stroke();

    const needleAngle = startAngle + progress * Math.PI;
    const needleLen = radius - 18;
    const nx = cx + needleLen * Math.cos(needleAngle);
    const ny = cy + needleLen * Math.sin(needleAngle);
    const textColor = getComputedStyle(document.documentElement).getPropertyValue('--color-text').trim() || '#fff';
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(nx, ny);
    ctx.lineWidth = 2; ctx.strokeStyle = textColor; ctx.stroke();
    ctx.beginPath(); ctx.arc(cx, cy, 4, 0, 2 * Math.PI);
    ctx.fillStyle = textColor; ctx.fill();
  }

  function renderHoldingsChart() {
    const canvas = document.getElementById('holdings-chart');
    if (!canvas) return;

    const colors = getChartColors();
    if (holdingsChart) holdingsChart.destroy();

    holdingsChart = new Chart(canvas.getContext('2d'), {
      type: 'doughnut',
      data: {
        labels: INSTITUTIONAL_HOLDINGS.map((h) => h.name),
        datasets: [{ data: INSTITUTIONAL_HOLDINGS.map((h) => h.pct), backgroundColor: colors.slice(0, INSTITUTIONAL_HOLDINGS.length), borderWidth: 0, hoverOffset: 8 }],
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '65%',
        plugins: {
          legend: { position: 'bottom', labels: { color: getComputedStyle(document.documentElement).getPropertyValue('--color-text-secondary').trim(), font: { family: "'Switzer', sans-serif", size: 11 }, padding: 12, usePointStyle: true, pointStyleWidth: 8 } },
          tooltip: {
            backgroundColor: getComputedStyle(document.documentElement).getPropertyValue('--color-surface').trim(),
            titleColor: getComputedStyle(document.documentElement).getPropertyValue('--color-text').trim(),
            bodyColor: getComputedStyle(document.documentElement).getPropertyValue('--color-text-secondary').trim(),
            borderColor: getComputedStyle(document.documentElement).getPropertyValue('--color-border').trim(), borderWidth: 1,
            callbacks: { label: (ctx) => ` ${ctx.label}: ${ctx.parsed}%` },
          },
        },
        animation: prefersReducedMotion ? { duration: 0 } : { animateRotate: true, duration: 1000 },
      },
    });
  }

  function renderFlowChart() {
    const canvas = document.getElementById('flow-chart');
    if (!canvas) return;

    const colors = getChartColors();
    if (flowChart) flowChart.destroy();

    const textColor = getComputedStyle(document.documentElement).getPropertyValue('--color-text-secondary').trim();
    const borderColor = getComputedStyle(document.documentElement).getPropertyValue('--color-border').trim();
    const bullish = getComputedStyle(document.documentElement).getPropertyValue('--color-bullish').trim();
    const bearish = getComputedStyle(document.documentElement).getPropertyValue('--color-bearish').trim();

    flowChart = new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels: flowData.map((f) => f.token),
        datasets: [
          { label: 'Inflow', data: flowData.map((f) => f.inflow), backgroundColor: bullish + '99', borderRadius: 4 },
          { label: 'Outflow', data: flowData.map((f) => f.outflow), backgroundColor: bearish + '99', borderRadius: 4 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { color: textColor, font: { family: "'Switzer', sans-serif", size: 11 }, padding: 12, usePointStyle: true, pointStyleWidth: 8 } },
          tooltip: {
            backgroundColor: getComputedStyle(document.documentElement).getPropertyValue('--color-surface').trim(),
            titleColor: getComputedStyle(document.documentElement).getPropertyValue('--color-text').trim(),
            bodyColor: textColor, borderColor, borderWidth: 1,
            callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${formatUSD(Math.abs(ctx.parsed.y), true)}` },
          },
        },
        scales: {
          x: { grid: { color: borderColor }, ticks: { color: textColor, font: { family: "'JetBrains Mono', monospace", size: 10 } } },
          y: { grid: { color: borderColor }, ticks: { color: textColor, font: { family: "'JetBrains Mono', monospace", size: 10 }, callback: (v) => formatUSD(Math.abs(v), true) } },
        },
        animation: prefersReducedMotion ? { duration: 0 } : { duration: 800 },
      },
    });
  }

  /* ============================================================
     ORCHESTRATION
     ============================================================ */
  function renderAll() {
    renderHeroMetrics();
    renderTimeline();
    renderSignalGauge();
    renderHoldingsChart();
    renderFlowChart();
  }

  function setupHeroImage() {
    const url = '{{HERO_IMAGE_URL}}';
    if (url && !url.startsWith('{{')) {
      const bg = document.querySelector('.hero__bg-image');
      if (bg) { bg.style.backgroundImage = `url('${url}')`; bg.style.opacity = '0.15'; }
    }
  }

  function initTheme() {
    const stored = localStorage.getItem('smart-money-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if ((stored || (prefersDark ? 'dark' : 'light')) === 'light') document.documentElement.setAttribute('data-theme', 'light');
    else document.documentElement.removeAttribute('data-theme');

    const btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.addEventListener('click', () => {
        const isLight = document.documentElement.getAttribute('data-theme') === 'light';
        if (isLight) { document.documentElement.removeAttribute('data-theme'); localStorage.setItem('smart-money-theme', 'dark'); }
        else { document.documentElement.setAttribute('data-theme', 'light'); localStorage.setItem('smart-money-theme', 'light'); }
        setTimeout(() => { renderSignalGauge(); renderHoldingsChart(); renderFlowChart(); }, 100);
      });
    }
  }

  function handleResize() {
    let timer;
    window.addEventListener('resize', () => {
      clearTimeout(timer);
      timer = setTimeout(() => renderSignalGauge(), 250);
    });
  }

  function init() {
    initTheme();
    startClock();
    setupHeroImage();
    handleResize();
    animateHeroEntrance();
    animateFeedEntrance();
    renderAll();
    // No auto-refresh — CoinGecko is paid per request
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
