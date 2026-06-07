/* ============================================================
   Portfolio Correlation Matrix — script.js
   Layout: A17 Full-width Sections + H2 Compact Stats Bar
   Entrance: D17 translateY(-30px) from above
   API: CoinGecko /coins/{id}/market_chart (free, no key)
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
        if (raw.startsWith('{{')) return ['bitcoin', 'ethereum', 'solana', 'cardano', 'polkadot', 'avalanche-2'];
        return JSON.parse(raw);
      } catch { return ['bitcoin', 'ethereum', 'solana', 'cardano', 'polkadot', 'avalanche-2']; }
    })(),
    maxRetries: 2,
    retryBaseDelay: 1500,
    refreshInterval: 300_000,
  };

  const SYMBOL_MAP = {
    bitcoin: 'BTC', ethereum: 'ETH', solana: 'SOL', cardano: 'ADA',
    polkadot: 'DOT', 'avalanche-2': 'AVAX', ripple: 'XRP', dogecoin: 'DOGE',
    chainlink: 'LINK', 'matic-network': 'MATIC', uniswap: 'UNI', litecoin: 'LTC',
    cosmos: 'ATOM', near: 'NEAR', arbitrum: 'ARB', optimism: 'OP',
  };

  const API = {
    marketChart: (id, days) =>
      `https://pro-api.coingecko.com/api/v3/coins/${id}/market_chart?vs_currency=usd&days=${days}&interval=daily`,
  };

  const ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';

  let currentDays = 30;
  let correlationMatrix = {};
  let priceData = {};

  /* ============================================================
     GSAP — D17 translateY(-30px) entrance
     ============================================================ */
  function animateHeroEntrance() {
    if (prefersReducedMotion) { gsap.set('.hero__top-row, .hero__stats-bar', { opacity: 1, y: 0 }); return; }
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    tl.from('.hero__brand', { opacity: 0, y: 20, duration: 0.6 })
      .from('.hero__time', { opacity: 0, duration: 0.4 }, '-=0.3')
      .from('.hero__stats-bar', { opacity: 0, y: 20, duration: 0.7 }, '-=0.3');
  }

  function animateSectionEntrance() {
    if (prefersReducedMotion) { gsap.set('.section-panel', { opacity: 1, y: 0 }); return; }
    /* D17: translateY(-30px) → 0 */
    gsap.utils.toArray('.section-panel').forEach((el, i) => {
      gsap.to(el, {
        opacity: 1, y: 0, duration: 0.7, delay: i * 0.1, ease: 'power3.out',
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

  function getSymbol(id) { return SYMBOL_MAP[id] || id.toUpperCase().substring(0, 4); }

  function showSkeleton(id, count, type) {
    const c = document.getElementById(id);
    if (!c) return;
    let h = '';
    for (let i = 0; i < count; i++) {
      if (type === 'corr') h += '<div class="corr-item"><div class="skeleton" style="width:80px;height:16px"></div><div class="skeleton" style="width:80px;height:6px"></div><div class="skeleton" style="width:40px;height:16px"></div></div>';
      else if (type === 'tip') h += '<div class="tip-item"><div class="skeleton" style="width:20px;height:20px;border-radius:50%"></div><div style="flex:1"><div class="skeleton skeleton--text"></div><div class="skeleton" style="width:80%;height:.7rem"></div></div></div>';
      else if (type === 'suggestion') h += '<div class="suggestion-item"><div class="skeleton skeleton--text"></div><div class="skeleton" style="width:80%;height:.7rem"></div></div>';
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

  /* ============================================================
     CORRELATION MATH
     ============================================================ */
  function pearsonCorrelation(x, y) {
    const n = Math.min(x.length, y.length);
    if (n < 3) return 0;
    let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;
    for (let i = 0; i < n; i++) {
      sumX += x[i]; sumY += y[i]; sumXY += x[i] * y[i];
      sumX2 += x[i] * x[i]; sumY2 += y[i] * y[i];
    }
    const num = n * sumXY - sumX * sumY;
    const den = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));
    return den === 0 ? 0 : num / den;
  }

  function pricesToReturns(prices) {
    const returns = [];
    for (let i = 1; i < prices.length; i++) {
      returns.push(prices[i - 1] === 0 ? 0 : (prices[i] - prices[i - 1]) / prices[i - 1]);
    }
    return returns;
  }

  function buildCorrelationMatrix(data, tokens) {
    const matrix = {};
    const returns = {};
    tokens.forEach((t) => { if (data[t]) returns[t] = pricesToReturns(data[t]); });
    const validTokens = tokens.filter((t) => returns[t] && returns[t].length > 2);
    validTokens.forEach((a) => {
      matrix[a] = {};
      validTokens.forEach((b) => {
        matrix[a][b] = a === b ? 1.0 : pearsonCorrelation(returns[a], returns[b]);
      });
    });
    return { matrix, validTokens };
  }

  /* ============================================================
     DATA FETCHING
     ============================================================ */
  async function fetchAllPriceData() {
    const tokens = CONFIG.trackedTokens;
    priceData = {};
    for (let i = 0; i < tokens.length; i++) {
      try {
        const data = await fetchWithRetry(API.marketChart(tokens[i], currentDays));
        if (data && data.prices) priceData[tokens[i]] = data.prices.map((p) => p[1]);
      } catch (err) { /* skip */ }
      if (i < tokens.length - 1) await new Promise((r) => setTimeout(r, 2000));
    }
    if (Object.keys(priceData).length < 2) {
      showError('heatmap-container', 'Not enough price data. Try again later.', fetchAndRender);
      showError('corr-ranking', 'Insufficient data for correlation analysis', fetchAndRender);
      return false;
    }
    const result = buildCorrelationMatrix(priceData, CONFIG.trackedTokens);
    correlationMatrix = result.matrix;
    return true;
  }

  /* ============================================================
     RENDERERS
     ============================================================ */
  function renderHeatmap() {
    const canvas = document.getElementById('heatmap-canvas');
    if (!canvas) return;
    const tokens = Object.keys(correlationMatrix);
    if (tokens.length === 0) return;

    const n = tokens.length;
    const dpr = window.devicePixelRatio || 1;
    const container = canvas.parentElement;
    const size = Math.min(container.clientWidth, container.clientHeight, 420);
    canvas.width = size * dpr; canvas.height = size * dpr;
    canvas.style.width = size + 'px'; canvas.style.height = size + 'px';

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const labelSpace = 50;
    const cellSize = (size - labelSpace) / n;
    const isDark = !document.documentElement.getAttribute('data-theme');

    tokens.forEach((a, i) => {
      tokens.forEach((b, j) => {
        const val = correlationMatrix[a][b];
        const x = labelSpace + j * cellSize;
        const y = labelSpace + i * cellSize;

        let r, g, bl;
        if (val >= 0) {
          const t = val;
          r = isDark ? Math.round(248 * t) : Math.round(220 * t + 26 * (1 - t));
          g = isDark ? Math.round(113 * t + 20 * (1 - t)) : Math.round(38 * t + 236 * (1 - t));
          bl = isDark ? Math.round(113 * t + 20 * (1 - t)) : Math.round(38 * t + 230 * (1 - t));
        } else {
          const t = -val;
          r = isDark ? Math.round(52 * t + 20 * (1 - t)) : Math.round(5 * t + 236 * (1 - t));
          g = isDark ? Math.round(211 * t + 20 * (1 - t)) : Math.round(150 * t + 236 * (1 - t));
          bl = isDark ? Math.round(153 * t + 20 * (1 - t)) : Math.round(105 * t + 230 * (1 - t));
        }

        ctx.fillStyle = `rgb(${r},${g},${bl})`;
        ctx.fillRect(x + 1, y + 1, cellSize - 2, cellSize - 2);

        if (cellSize > 30) {
          ctx.fillStyle = Math.abs(val) > 0.5 ? '#ffffff' : (isDark ? 'rgba(255,255,255,0.6)' : 'rgba(0,0,0,0.6)');
          ctx.font = `600 ${Math.max(9, cellSize * 0.22)}px 'JetBrains Mono', monospace`;
          ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
          ctx.fillText(val.toFixed(2), x + cellSize / 2, y + cellSize / 2);
        }
      });
    });

    ctx.fillStyle = isDark ? 'rgba(255,255,255,0.5)' : '#6b7280';
    ctx.font = `600 ${Math.max(9, cellSize * 0.25)}px 'JetBrains Mono', monospace`;
    ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
    tokens.forEach((t, i) => { ctx.fillText(getSymbol(t), labelSpace - 6, labelSpace + i * cellSize + cellSize / 2); });

    ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
    tokens.forEach((t, j) => {
      ctx.save();
      ctx.translate(labelSpace + j * cellSize + cellSize / 2, labelSpace - 6);
      ctx.rotate(-Math.PI / 4);
      ctx.fillText(getSymbol(t), 0, 0);
      ctx.restore();
    });
  }

  function renderHeroMetrics() {
    const tokens = Object.keys(correlationMatrix);
    if (tokens.length < 2) return;

    let totalCorr = 0, pairCount = 0;
    let highest = { val: -2, pair: '' }, lowest = { val: 2, pair: '' };

    tokens.forEach((a, i) => {
      tokens.forEach((b, j) => {
        if (i >= j) return;
        const val = correlationMatrix[a][b];
        totalCorr += Math.abs(val); pairCount++;
        if (val > highest.val) highest = { val, pair: `${getSymbol(a)}/${getSymbol(b)}` };
        if (val < lowest.val) lowest = { val, pair: `${getSymbol(a)}/${getSymbol(b)}` };
      });
    });

    const avgCorr = pairCount > 0 ? totalCorr / pairCount : 0;
    const diversityScore = Math.round((1 - avgCorr) * 100);

    const scoreEl = document.getElementById('hero-diversity');
    const highEl = document.getElementById('hero-highest');
    const lowEl = document.getElementById('hero-lowest');
    const countEl = document.getElementById('hero-token-count');

    if (scoreEl) scoreEl.textContent = diversityScore + '/100';
    if (highEl) highEl.textContent = highest.val.toFixed(2) + ' ' + highest.pair;
    if (lowEl) lowEl.textContent = lowest.val.toFixed(2) + ' ' + lowest.pair;
    if (countEl) countEl.textContent = tokens.length.toString();
  }

  function renderCorrelationRanking() {
    const container = document.getElementById('corr-ranking');
    if (!container) return;

    const tokens = Object.keys(correlationMatrix);
    const pairs = [];
    tokens.forEach((a, i) => {
      tokens.forEach((b, j) => {
        if (i >= j) return;
        pairs.push({ a, b, val: correlationMatrix[a][b] });
      });
    });
    pairs.sort((x, y) => Math.abs(y.val) - Math.abs(x.val));

    let html = '';
    pairs.forEach((p) => {
      const isPos = p.val >= 0;
      const barWidth = Math.abs(p.val) * 50;
      const color = isPos ? 'var(--corr-positive)' : 'var(--corr-negative)';
      const fillClass = isPos ? 'corr-item__bar-fill--pos' : 'corr-item__bar-fill--neg';
      const fillStyle = isPos ? `right:50%;width:${barWidth}%` : `left:50%;width:${barWidth}%`;

      html += `<div class="corr-item">
        <span class="corr-item__pair">${getSymbol(p.a)} / ${getSymbol(p.b)}</span>
        <div class="corr-item__bar"><div class="corr-item__bar-center"></div><div class="corr-item__bar-fill ${fillClass}" style="${fillStyle}"></div></div>
        <span class="corr-item__value" style="color:${color}">${p.val >= 0 ? '+' : ''}${p.val.toFixed(3)}</span>
      </div>`;
    });

    container.innerHTML = html;
    if (!prefersReducedMotion) {
      gsap.from('.corr-item', { opacity: 0, x: -16, stagger: 0.04, duration: 0.4, ease: 'power3.out' });
    }
  }

  function renderSuggestions() {
    const container = document.getElementById('suggestions');
    if (!container) return;

    const tokens = Object.keys(correlationMatrix);
    const pairs = [];
    tokens.forEach((a, i) => {
      tokens.forEach((b, j) => {
        if (i >= j) return;
        pairs.push({ a, b, val: correlationMatrix[a][b] });
      });
    });

    const highCorr = pairs.filter((p) => p.val > 0.85).sort((a, b) => b.val - a.val);
    const lowCorr = pairs.filter((p) => p.val < 0.3).sort((a, b) => a.val - b.val);

    let html = '';
    if (highCorr.length > 0) {
      html += `<div class="suggestion-item"><div class="suggestion-item__title"><span class="suggestion-item__icon">⚠</span>High Correlation Warning</div><div class="suggestion-item__desc">${highCorr.slice(0, 2).map((p) => `${getSymbol(p.a)}/${getSymbol(p.b)} (${p.val.toFixed(2)})`).join(', ')} move together. Consider reducing one position.</div></div>`;
    }
    if (lowCorr.length > 0) {
      html += `<div class="suggestion-item"><div class="suggestion-item__title"><span class="suggestion-item__icon">✓</span>Good Diversification</div><div class="suggestion-item__desc">${lowCorr.slice(0, 2).map((p) => `${getSymbol(p.a)}/${getSymbol(p.b)} (${p.val.toFixed(2)})`).join(', ')} provide good diversification.</div></div>`;
    }
    if (pairs.length > 0) {
      const avgCorr = pairs.reduce((s, p) => s + Math.abs(p.val), 0) / pairs.length;
      const rating = avgCorr < 0.4 ? 'Well Diversified' : avgCorr < 0.6 ? 'Moderate' : 'Concentrated';
      html += `<div class="suggestion-item"><div class="suggestion-item__title"><span class="suggestion-item__icon">◉</span>Portfolio Rating: ${rating}</div><div class="suggestion-item__desc">Average absolute correlation: ${avgCorr.toFixed(3)}. ${avgCorr > 0.6 ? 'Consider adding uncorrelated assets.' : 'Your portfolio has reasonable diversification.'}</div></div>`;
    }

    container.innerHTML = html || '<div class="suggestion-item"><div class="suggestion-item__desc">Analyzing correlations...</div></div>';
    if (!prefersReducedMotion) {
      gsap.from('.suggestion-item', { opacity: 0, y: 12, stagger: 0.08, duration: 0.4, ease: 'power3.out' });
    }
  }

  function renderTips() {
    const container = document.getElementById('tips-list');
    if (!container) return;

    const tips = [
      { title: 'Correlation ≠ Causation', desc: 'High correlation means prices move together, not that one causes the other.' },
      { title: 'Time Window Matters', desc: 'Short-term correlations (7D) can differ significantly from long-term (90D).' },
      { title: 'Target: Below 0.5', desc: 'Pairs with correlation below 0.5 provide meaningful diversification.' },
      { title: 'Rebalance Periodically', desc: 'Correlations shift over time. Review monthly and rebalance when concentrations emerge.' },
    ];

    const iconSvg = '<svg class="tip-item__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>';

    let html = '';
    tips.forEach((t) => {
      html += `<div class="tip-item">${iconSvg}<div class="tip-item__content"><div class="tip-item__title">${t.title}</div><div class="tip-item__desc">${t.desc}</div></div></div>`;
    });
    container.innerHTML = html;
    if (!prefersReducedMotion) {
      gsap.from('.tip-item', { opacity: 0, y: 16, stagger: 0.08, duration: 0.5, ease: 'power3.out' });
    }
  }

  /* ============================================================
     ORCHESTRATION
     ============================================================ */
  async function fetchAndRender() {
    showSkeleton('corr-ranking', 8, 'corr');
    showSkeleton('suggestions', 3, 'suggestion');
    showSkeleton('tips-list', 4, 'tip');

    const success = await fetchAllPriceData();
    if (!success) return;

    renderHeatmap();
    renderHeroMetrics();
    renderCorrelationRanking();
    renderSuggestions();
    renderTips();
  }

  function initTimeSelector() {
    const btns = document.querySelectorAll('.time-btn');
    btns.forEach((btn) => {
      btn.addEventListener('click', () => {
        btns.forEach((b) => b.classList.remove('time-btn--active'));
        btn.classList.add('time-btn--active');
        currentDays = parseInt(btn.dataset.days, 10);
        fetchAndRender();
      });
    });
  }

  function setupHeroImage() {
    const url = '{{HERO_IMAGE_URL}}';
    if (url && !url.startsWith('{{')) {
      const bg = document.querySelector('.hero__bg-image');
      if (bg) { bg.style.backgroundImage = `url('${url}')`; bg.style.opacity = '0.15'; }
    }
  }

  function initTheme() {
    const stored = localStorage.getItem('correlation-matrix-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if ((stored || (prefersDark ? 'dark' : 'light')) === 'light') document.documentElement.setAttribute('data-theme', 'light');
    else document.documentElement.removeAttribute('data-theme');

    const btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.addEventListener('click', () => {
        const isLight = document.documentElement.getAttribute('data-theme') === 'light';
        if (isLight) { document.documentElement.removeAttribute('data-theme'); localStorage.setItem('correlation-matrix-theme', 'dark'); }
        else { document.documentElement.setAttribute('data-theme', 'light'); localStorage.setItem('correlation-matrix-theme', 'light'); }
        if (Object.keys(correlationMatrix).length > 0) renderHeatmap();
      });
    }
  }

  function handleResize() {
    let timer;
    window.addEventListener('resize', () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        if (Object.keys(correlationMatrix).length > 0) renderHeatmap();
      }, 250);
    });
  }

  function init() {
    initTheme();
    startClock();
    setupHeroImage();
    initTimeSelector();
    handleResize();
    animateHeroEntrance();
    animateSectionEntrance();
    fetchAndRender();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
