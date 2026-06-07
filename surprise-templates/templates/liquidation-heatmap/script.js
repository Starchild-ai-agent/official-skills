/* ============================================================
   Liquidation Heatmap — script.js
   API: CoinGecko (free, no key) for current prices as reference
   Mock Data: Built-in liquidation distribution data
   Canvas: Custom heatmap rendering
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
    prices: (ids) => `https://pro-api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=${ids}&order=market_cap_desc&sparkline=false`,
  };

  const SYMBOL_MAP = {
    bitcoin: 'BTC', ethereum: 'ETH', solana: 'SOL', cardano: 'ADA',
    polkadot: 'DOT', 'avalanche-2': 'AVAX', ripple: 'XRP', dogecoin: 'DOGE',
    chainlink: 'LINK', arbitrum: 'ARB', optimism: 'OP', uniswap: 'UNI',
  };

  const ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';

  /* ============================================================
     MOCK DATA — Liquidation Distribution
     Real liquidation data APIs (Coinglass, etc.) require paid
     subscriptions and API keys. Using realistic simulated data.
     ============================================================ */

  const MOCK_PRICES = { BTC: 67500, ETH: 3450, SOL: 178 };

  function generateLiquidationData(token) {
    const cp = MOCK_PRICES[token] || 100;
    const levels = [];
    const range = cp * 0.2;
    const steps = 40;
    const stepSize = (range * 2) / steps;
    for (let i = 0; i < steps; i++) {
      const price = cp - range + i * stepSize;
      const distFromCurrent = Math.abs(price - cp) / cp;
      let longLiq = 0, shortLiq = 0;
      if (price < cp) {
        longLiq = Math.max(0, (1 - distFromCurrent * 4) * Math.random() * 50e6 + Math.random() * 5e6);
        shortLiq = Math.random() * 2e6;
      } else {
        shortLiq = Math.max(0, (1 - distFromCurrent * 4) * Math.random() * 50e6 + Math.random() * 5e6);
        longLiq = Math.random() * 2e6;
      }
      const cf = Math.exp(-distFromCurrent * 8);
      longLiq *= (1 + cf * 3);
      shortLiq *= (1 + cf * 3);
      levels.push({ price: Math.round(price * 100) / 100, longLiq: Math.round(longLiq), shortLiq: Math.round(shortLiq), totalLiq: Math.round(longLiq + shortLiq) });
    }
    return levels;
  }

  function generateRecentLiquidations() {
    const tokens = CONFIG.trackedTokens.map((t) => SYMBOL_MAP[t] || t.toUpperCase().substring(0, 4));
    const sides = ['long', 'short'];
    const exchanges = ['Binance', 'Bybit', 'OKX', 'Bitget', 'dYdX'];
    const items = [];
    const now = Date.now();
    for (let i = 0; i < 20; i++) {
      const token = tokens[Math.floor(Math.random() * tokens.length)];
      const side = sides[Math.floor(Math.random() * sides.length)];
      const exchange = exchanges[Math.floor(Math.random() * exchanges.length)];
      const price = MOCK_PRICES[token] || 100;
      const liqPrice = price * (side === 'long' ? (0.85 + Math.random() * 0.12) : (1.03 + Math.random() * 0.12));
      const amount = Math.floor(Math.random() * 5e6 + 1e5);
      const minsAgo = Math.floor(Math.random() * 1440);
      items.push({ token, side, exchange, liqPrice: Math.round(liqPrice * 100) / 100, amount, time: new Date(now - minsAgo * 60000) });
    }
    return items.sort((a, b) => b.time - a.time);
  }

  function computeRiskScore(ld, cp) {
    const nearby = ld.filter((l) => Math.abs(l.price - cp) / cp < 0.05);
    const totalNearby = nearby.reduce((s, l) => s + l.totalLiq, 0);
    const totalAll = ld.reduce((s, l) => s + l.totalLiq, 0);
    return Math.min(100, Math.round((totalAll > 0 ? totalNearby / totalAll : 0) * 200));
  }

  function computeLongShortRatio(ld) {
    const tl = ld.reduce((s, l) => s + l.longLiq, 0);
    const ts = ld.reduce((s, l) => s + l.shortLiq, 0);
    const total = tl + ts;
    return { longPct: total > 0 ? Math.round((tl / total) * 100) : 50, shortPct: total > 0 ? Math.round((ts / total) * 100) : 50, ratio: ts > 0 ? (tl / ts).toFixed(2) : '1.00' };
  }

  function findRiskZones(ld, cp) {
    const sorted = [...ld].sort((a, b) => b.totalLiq - a.totalLiq).slice(0, 8);
    const clusters = [];
    let cur = [sorted[0]];
    for (let i = 1; i < sorted.length; i++) {
      if (Math.abs(sorted[i].price - cur[cur.length - 1].price) / cp < 0.02) { cur.push(sorted[i]); }
      else { clusters.push(cur); cur = [sorted[i]]; }
    }
    clusters.push(cur);
    return clusters.map((cl) => {
      const minP = Math.min(...cl.map((c) => c.price));
      const maxP = Math.max(...cl.map((c) => c.price));
      const tl = cl.reduce((s, c) => s + c.totalLiq, 0);
      const dp = Math.abs((minP + maxP) / 2 - cp) / cp;
      let sev = 'moderate';
      if (dp < 0.03 && tl > 20e6) sev = 'critical';
      else if (dp < 0.06 && tl > 10e6) sev = 'warning';
      return { minPrice: minP, maxPrice: maxP, totalLiq: tl, severity: sev, distPct: dp, side: (minP + maxP) / 2 < cp ? 'Below' : 'Above' };
    }).sort((a, b) => ({ critical: 0, warning: 1, moderate: 2 })[a.severity] - ({ critical: 0, warning: 1, moderate: 2 })[b.severity]).slice(0, 5);
  }

  const primaryToken = SYMBOL_MAP[CONFIG.trackedTokens[0]] || 'BTC';
  let liqData = generateLiquidationData(primaryToken);
  let recentLiqs = generateRecentLiquidations();
  let currentPrice = MOCK_PRICES[primaryToken] || 67500;
  let riskScore = computeRiskScore(liqData, currentPrice);
  let lsRatio = computeLongShortRatio(liqData);
  let riskZones = findRiskZones(liqData, currentPrice);

  /* ---- GSAP — D6 scale(1.05) → scale(1) entrance ---- */
  function animateHeroEntrance() {
    if (prefersReducedMotion) { gsap.set('.hero__content', { opacity: 1, y: 0 }); return; }
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    tl.from('.hero__top', { opacity: 0, y: 20, duration: 0.6 })
      .from('.hero__title', { opacity: 0, y: 30, duration: 0.7, ease: 'power4.out' }, '-=0.3')
      .from('.hero__subtitle', { opacity: 0, y: 15, duration: 0.4 }, '-=0.3')
      .from('.hero__stats-row', { opacity: 0, y: 20, scale: 0.97, duration: 0.6 }, '-=0.2');
  }

  function animateCardEntrance() {
    if (prefersReducedMotion) { gsap.set('.data-block', { opacity: 1, scale: 1 }); return; }
    /* D6: scale(1.05) → scale(1) */
    gsap.utils.toArray('.data-block').forEach((block, i) => {
      gsap.to(block, { opacity: 1, scale: 1, duration: 0.7, delay: i * 0.12, ease: 'power3.out',
        scrollTrigger: { trigger: block, start: 'top 88%', once: true } });
    });
  }

  /* ---- UTILITIES ---- */
  async function fetchWithRetry(url, retries = CONFIG.maxRetries) {
    for (let attempt = 0; attempt <= retries; attempt++) {
      try { const res = await fetch(url); if (!res.ok) throw new Error(`HTTP ${res.status}`); return await res.json(); }
      catch (err) { if (attempt === retries) throw err; await new Promise((r) => setTimeout(r, CONFIG.retryBaseDelay * (attempt + 1))); }
    }
  }

  function formatUSD(v, compact) {
    if (v == null) return '--';
    if (compact) { if (v >= 1e9) return '$' + (v / 1e9).toFixed(2) + 'B'; if (v >= 1e6) return '$' + (v / 1e6).toFixed(1) + 'M'; if (v >= 1e3) return '$' + (v / 1e3).toFixed(1) + 'K'; }
    return '$' + v.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  }

  function timeAgo(date) {
    const diff = Date.now() - date.getTime();
    const mins = Math.floor(diff / 60000);
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
      if (type === 'row') h += '<div class="skeleton skeleton--row"></div>';
      else if (type === 'zone') h += '<div class="risk-zone"><div class="skeleton" style="width:100%;height:50px"></div></div>';
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

  /* ---- RENDERERS ---- */
  function renderHeroMetrics() {
    const riskEl = document.getElementById('hero-risk-score');
    const liqEl = document.getElementById('hero-liquidated');
    const lsEl = document.getElementById('hero-ls-ratio');
    if (riskEl) {
      riskEl.textContent = riskScore + '/100';
      riskEl.style.color = riskScore >= 70 ? 'var(--color-danger)' : riskScore >= 40 ? 'var(--color-warning)' : 'var(--color-success)';
    }
    if (liqEl) { liqEl.textContent = formatUSD(recentLiqs.reduce((s, l) => s + l.amount, 0), true); }
    if (lsEl) { lsEl.textContent = lsRatio.ratio; }
  }

  function renderHeatmap() {
    const canvas = document.getElementById('heatmap-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const container = canvas.parentElement;
    const w = container.clientWidth;
    const h = container.clientHeight - 30;
    canvas.width = w * dpr; canvas.height = h * dpr;
    canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
    ctx.scale(dpr, dpr);

    const cs = getComputedStyle(document.documentElement);
    const textColor = cs.getPropertyValue('--color-text-muted').trim();
    const bgColor = cs.getPropertyValue('--color-surface').trim();
    const accentColor = cs.getPropertyValue('--color-accent').trim();

    ctx.fillStyle = bgColor; ctx.fillRect(0, 0, w, h);

    const padL = 70, padR = 20, padT = 20, padB = 40;
    const chartW = w - padL - padR, chartH = h - padT - padB;
    const maxLiq = Math.max(...liqData.map((l) => Math.max(l.longLiq, l.shortLiq)));
    const minPrice = Math.min(...liqData.map((l) => l.price));
    const maxPrice = Math.max(...liqData.map((l) => l.price));
    const priceRange = maxPrice - minPrice;
    const barH = chartH / liqData.length - 1;

    liqData.forEach((level, i) => {
      const y = padT + (i / liqData.length) * chartH;
      const longW = maxLiq > 0 ? (level.longLiq / maxLiq) * (chartW / 2) : 0;
      const shortW = maxLiq > 0 ? (level.shortLiq / maxLiq) * (chartW / 2) : 0;
      const centerX = padL + chartW / 2;
      const longI = maxLiq > 0 ? level.longLiq / maxLiq : 0;
      ctx.fillStyle = `rgba(76,175,80,${0.15 + longI * 0.7})`;
      ctx.fillRect(centerX - longW, y, longW, barH);
      const shortI = maxLiq > 0 ? level.shortLiq / maxLiq : 0;
      ctx.fillStyle = `rgba(224,90,58,${0.15 + shortI * 0.7})`;
      ctx.fillRect(centerX, y, shortW, barH);
    });

    const currentY = padT + ((currentPrice - minPrice) / priceRange) * chartH;
    ctx.strokeStyle = accentColor; ctx.lineWidth = 1.5; ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(padL, currentY); ctx.lineTo(w - padR, currentY); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = accentColor; ctx.font = '10px "Fira Code", monospace'; ctx.textAlign = 'right';
    ctx.fillText('$' + currentPrice.toLocaleString(), padL - 6, currentY + 3);

    ctx.fillStyle = textColor; ctx.font = '9px "Fira Code", monospace'; ctx.textAlign = 'right';
    for (let i = 0; i <= 6; i++) {
      const price = minPrice + (i / 6) * priceRange;
      const y = padT + (i / 6) * chartH;
      ctx.fillText('$' + Math.round(price).toLocaleString(), padL - 6, y + 3);
    }

    ctx.textAlign = 'center';
    const centerX = padL + chartW / 2;
    ctx.fillStyle = '#4caf50'; ctx.fillText('LONG LIQUIDATIONS', centerX - chartW / 4, h - 8);
    ctx.fillStyle = '#e05a3a'; ctx.fillText('SHORT LIQUIDATIONS', centerX + chartW / 4, h - 8);

    const legendEl = document.getElementById('heatmap-legend');
    if (legendEl) legendEl.innerHTML = '<span>Low</span><div class="heatmap-legend__bar"></div><span>High</span>';
  }

  function renderGauge() {
    const canvas = document.getElementById('gauge-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const cw = canvas.clientWidth, ch = canvas.clientHeight;
    canvas.width = cw * dpr; canvas.height = ch * dpr; ctx.scale(dpr, dpr);

    const cx = cw / 2, cy = ch - 10, radius = Math.min(cx, cy) - 10, startAngle = Math.PI;
    const cs = getComputedStyle(document.documentElement);
    const longColor = cs.getPropertyValue('--color-long').trim() || '#4caf50';
    const shortColor = cs.getPropertyValue('--color-short').trim() || '#e05a3a';
    const neutralColor = cs.getPropertyValue('--color-neutral').trim() || '#e8a832';

    const segments = [
      { end: 0.3, color: shortColor }, { end: 0.45, color: '#e88a42' },
      { end: 0.55, color: neutralColor }, { end: 0.7, color: '#8bc34a' }, { end: 1.0, color: longColor },
    ];

    const drawBg = () => {
      let prev = 0;
      segments.forEach((seg) => {
        ctx.beginPath(); ctx.arc(cx, cy, radius, startAngle + prev * Math.PI, startAngle + seg.end * Math.PI);
        ctx.lineWidth = 12; ctx.strokeStyle = seg.color; ctx.lineCap = 'round'; ctx.globalAlpha = 0.15; ctx.stroke(); prev = seg.end;
      });
      ctx.globalAlpha = 1;
    };

    const drawNeedle = (p) => {
      const angle = startAngle + p * Math.PI;
      ctx.beginPath(); ctx.arc(cx, cy, radius, startAngle, angle); ctx.lineWidth = 12;
      const grad = ctx.createLinearGradient(cx - radius, cy, cx + radius, cy);
      grad.addColorStop(0, shortColor); grad.addColorStop(0.5, neutralColor); grad.addColorStop(1, longColor);
      ctx.strokeStyle = grad; ctx.lineCap = 'round'; ctx.stroke();
    };

    const progress = lsRatio.longPct / 100;
    if (prefersReducedMotion) { drawBg(); drawNeedle(progress); }
    else {
      const obj = { p: 0 };
      gsap.to(obj, { p: progress, duration: 1.5, ease: 'power3.out', onUpdate: () => {
        ctx.clearRect(0, 0, cw, ch); drawBg(); drawNeedle(obj.p);
      }});
    }

    const valueEl = document.getElementById('gauge-value');
    const labelEl = document.getElementById('gauge-label');
    if (valueEl) valueEl.textContent = lsRatio.ratio;
    if (labelEl) {
      const r = parseFloat(lsRatio.ratio);
      if (r > 1.3) { labelEl.textContent = 'LONG HEAVY'; labelEl.style.color = longColor; }
      else if (r > 1.05) { labelEl.textContent = 'SLIGHTLY LONG'; labelEl.style.color = longColor; }
      else if (r < 0.7) { labelEl.textContent = 'SHORT HEAVY'; labelEl.style.color = shortColor; }
      else if (r < 0.95) { labelEl.textContent = 'SLIGHTLY SHORT'; labelEl.style.color = shortColor; }
      else { labelEl.textContent = 'BALANCED'; labelEl.style.color = neutralColor; }
    }

    const breakdown = document.getElementById('gauge-breakdown');
    if (breakdown) {
      breakdown.innerHTML = `
        <div class="gauge-row"><span class="gauge-row__label">Long Exposure</span><span class="gauge-row__value text-up">${lsRatio.longPct}%</span></div>
        <div class="gauge-row"><span class="gauge-row__label">Short Exposure</span><span class="gauge-row__value text-down">${lsRatio.shortPct}%</span></div>
        <div class="gauge-row"><span class="gauge-row__label">Risk Score</span><span class="gauge-row__value">${riskScore}/100</span></div>
        <div class="gauge-row"><span class="gauge-row__label">Current Price</span><span class="gauge-row__value">$${currentPrice.toLocaleString()}</span></div>`;
    }
  }

  function renderRiskZones() {
    const container = document.getElementById('risk-zones');
    if (!container) return;
    showSkeleton('risk-zones', 4, 'zone');
    setTimeout(() => {
      let html = '';
      const maxLiq = Math.max(...riskZones.map((z) => z.totalLiq));
      riskZones.forEach((zone) => {
        const fillPct = maxLiq > 0 ? (zone.totalLiq / maxLiq) * 100 : 0;
        const barColor = zone.severity === 'critical' ? 'var(--color-danger)' : zone.severity === 'warning' ? 'var(--color-warning)' : 'var(--color-neutral)';
        html += `<div class="risk-zone risk-zone--${zone.severity}">
          <div class="risk-zone__header"><span class="risk-zone__range">$${zone.minPrice.toLocaleString()} - $${zone.maxPrice.toLocaleString()}</span><span class="risk-zone__severity risk-zone__severity--${zone.severity}">${zone.severity}</span></div>
          <div class="risk-zone__detail"><span>${zone.side} current price</span><span>${formatUSD(zone.totalLiq, true)} at risk</span></div>
          <div class="risk-zone__bar"><div class="risk-zone__bar-fill" style="width:${fillPct}%;background:${barColor}"></div></div>
        </div>`;
      });
      container.innerHTML = html;
      if (!prefersReducedMotion) gsap.from('.risk-zone', { opacity: 0, x: 16, stagger: 0.06, duration: 0.4, ease: 'power3.out' });
    }, 400);
  }

  function renderLiqList() {
    const container = document.getElementById('liq-list');
    if (!container) return;
    showSkeleton('liq-list', 8, 'row');
    setTimeout(() => {
      let html = '';
      recentLiqs.forEach((item) => {
        html += `<div class="liq-item">
          <span class="liq-item__time">${timeAgo(item.time)}</span>
          <span class="liq-item__side liq-item__side--${item.side}">${item.side}</span>
          <span class="liq-item__token">${item.token}</span>
          <span class="liq-item__price">@ $${item.liqPrice.toLocaleString()}</span>
          <span class="liq-item__amount">${formatUSD(item.amount, true)}</span>
        </div>`;
      });
      container.innerHTML = html;
      if (!prefersReducedMotion) gsap.from('.liq-item', { opacity: 0, x: -12, stagger: 0.03, duration: 0.3, ease: 'power3.out' });
    }, 500);
  }

  /* ---- THEME ---- */
  function initTheme() {
    const stored = localStorage.getItem('liquidation-heatmap-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = stored || (prefersDark ? 'dark' : 'light');
    if (theme === 'light') document.documentElement.setAttribute('data-theme', 'light');

    const heroImg = '{{HERO_IMAGE_URL}}';
    if (heroImg && !heroImg.startsWith('{{')) {
      const bgEl = document.querySelector('.hero__bg-image');
      if (bgEl) { bgEl.style.backgroundImage = `url(${heroImg})`; bgEl.style.opacity = '0.1'; }
    }
  }

  function toggleTheme() {
    const isLight = document.documentElement.getAttribute('data-theme') === 'light';
    if (isLight) {
      document.documentElement.removeAttribute('data-theme');
      localStorage.setItem('liquidation-heatmap-theme', 'dark');
    } else {
      document.documentElement.setAttribute('data-theme', 'light');
      localStorage.setItem('liquidation-heatmap-theme', 'light');
    }
    renderHeatmap();
    renderGauge();
  }

  /* ---- DATA FETCH ---- */
  async function fetchPrices() {
    try {
      const ids = CONFIG.trackedTokens.join(',');
      const data = await fetchWithRetry(API.prices(ids));
      data.forEach((coin) => {
        const sym = coin.symbol.toUpperCase();
        MOCK_PRICES[sym] = coin.current_price;
      });
      currentPrice = MOCK_PRICES[primaryToken] || currentPrice;
    } catch (err) {
      console.warn('CoinGecko price fetch failed, using mock prices:', err.message);
    }
  }

  async function refreshData() {
    await fetchPrices();
    liqData = generateLiquidationData(primaryToken);
    recentLiqs = generateRecentLiquidations();
    riskScore = computeRiskScore(liqData, currentPrice);
    lsRatio = computeLongShortRatio(liqData);
    riskZones = findRiskZones(liqData, currentPrice);
    renderHeroMetrics();
    renderHeatmap();
    renderGauge();
    renderRiskZones();
    renderLiqList();
  }

  /* ---- INIT ---- */
  function init() {
    initTheme();
    startClock();
    document.getElementById('theme-toggle').addEventListener('click', toggleTheme);

    renderHeroMetrics();
    renderHeatmap();
    renderGauge();
    renderRiskZones();
    renderLiqList();

    fetchPrices().then(() => {
      liqData = generateLiquidationData(primaryToken);
      riskScore = computeRiskScore(liqData, currentPrice);
      lsRatio = computeLongShortRatio(liqData);
      riskZones = findRiskZones(liqData, currentPrice);
      renderHeroMetrics();
      renderHeatmap();
      renderGauge();
      renderRiskZones();
      renderLiqList();
    });

    animateHeroEntrance();
    animateCardEntrance();

    window.addEventListener('resize', renderHeatmap);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();