/* ============================================================
   Trading Intelligence Dashboard — script.js
   Redesigned with GSAP + taste-skill motion principles
   
   APIs: CoinGecko (free, no key) + Alternative.me Fear & Greed
   Animation: GSAP 3 + ScrollTrigger (CDN)
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Register GSAP Plugins ---------- */
  gsap.registerPlugin(ScrollTrigger);

  /* ---------- Reduced Motion Check ---------- */
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Configuration ---------- */
  const CONFIG = {
    trackedTokens: (() => {
      try {
        const raw = '{{TRACKED_TOKENS}}';
        if (raw.startsWith('{{')) return ['bitcoin', 'ethereum', 'solana'];
        return JSON.parse(raw);
      } catch {
        return ['bitcoin', 'ethereum', 'solana'];
      }
    })(),
    refreshIntervals: {
      prices: 60_000,
      sentiment: 300_000,
      trending: 300_000,
      global: 300_000,
    },
    maxRetries: 2,
    retryBaseDelay: 1500,
  };

  const API = {
    prices: (ids) =>
      `https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=${ids}&order=market_cap_desc&sparkline=true&price_change_percentage=24h,7d`,
    trending: () =>
      'https://api.coingecko.com/api/v3/search/trending',
    global: () =>
      'https://api.coingecko.com/api/v3/global',
    fearGreed: () =>
      'https://api.alternative.me/fng/?limit=1',
  };

  const ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';

  /* ============================================================
     GSAP ANIMATION SYSTEM
     ============================================================ */

  /**
   * Hero entrance animation — staggered reveal
   * Motivated: hierarchy (draw attention to title first, then metrics)
   */
  function animateHeroEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.hero__content > *', { opacity: 1, y: 0 });
      return;
    }

    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

    tl.from('.hero__status-bar', {
      opacity: 0,
      y: 20,
      duration: 0.6,
    })
    .from('.hero__title', {
      opacity: 0,
      y: 40,
      duration: 0.8,
      ease: 'power4.out',
    }, '-=0.3')
    .from('.hero__subtitle', {
      opacity: 0,
      y: 20,
      duration: 0.5,
    }, '-=0.4')
    .from('.hero__metrics', {
      opacity: 0,
      y: 30,
      scale: 0.97,
      duration: 0.7,
    }, '-=0.3')
    .from('.hero__scroll-indicator', {
      opacity: 0,
      duration: 0.5,
    }, '-=0.3');
  }

  /**
   * Card entrance — ScrollTrigger stagger
   * Motivated: storytelling (reveal content in sequence as user scrolls)
   */
  function animateCardEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.card', { opacity: 1, y: 0 });
      return;
    }

    const cards = gsap.utils.toArray('.card');
    cards.forEach((card, i) => {
      gsap.to(card, {
        opacity: 1,
        y: 0,
        duration: 0.8,
        delay: i * 0.12,
        ease: 'power3.out',
        scrollTrigger: {
          trigger: card,
          start: 'top 85%',
          once: true,
        },
      });
    });
  }

  /**
   * 3D Tilt effect on cards
   * Motivated: feedback (acknowledging pointer position, adding depth)
   */
  function initCardTilt() {
    if (prefersReducedMotion) return;

    const cards = document.querySelectorAll('[data-tilt]');
    cards.forEach((card) => {
      const bezel = card.querySelector('.card__bezel');
      if (!bezel) return;

      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;

        gsap.to(bezel, {
          rotateY: x * 4,
          rotateX: -y * 4,
          duration: 0.4,
          ease: 'power2.out',
          transformPerspective: 800,
        });
      });

      card.addEventListener('mouseleave', () => {
        gsap.to(bezel, {
          rotateY: 0,
          rotateX: 0,
          duration: 0.6,
          ease: 'power3.out',
        });
      });
    });
  }

  /**
   * Counter animation — animate numbers from 0 to target
   * Motivated: state transition (showing data has loaded/changed)
   */
  function animateCounter(element, targetValue, prefix, suffix, decimals) {
    if (prefersReducedMotion) {
      element.textContent = prefix + targetValue + suffix;
      return;
    }

    const obj = { val: 0 };
    gsap.to(obj, {
      val: targetValue,
      duration: 1.2,
      ease: 'power2.out',
      onUpdate: () => {
        const formatted = decimals > 0
          ? obj.val.toFixed(decimals)
          : Math.round(obj.val).toLocaleString('en-US');
        element.textContent = prefix + formatted + suffix;
      },
      onComplete: () => {
        element.classList.add('value-updated');
        setTimeout(() => element.classList.remove('value-updated'), 800);
      },
    });
  }

  /**
   * Data refresh pulse — visual feedback when data updates
   * Motivated: feedback (acknowledging data refresh)
   */
  function pulseCard(cardElement) {
    if (prefersReducedMotion || !cardElement) return;
    const inner = cardElement.querySelector('.card__inner');
    if (!inner) return;
    inner.classList.add('data-pulse');
    setTimeout(() => inner.classList.remove('data-pulse'), 600);
  }

  /**
   * Sparkline draw animation — chart line draws in
   * Motivated: storytelling (data appearing progressively)
   */
  function animateSparklineDraw(chart) {
    if (prefersReducedMotion || !chart) return;

    const dataset = chart.data.datasets[0];
    const originalData = [...dataset.data];
    const len = originalData.length;

    dataset.data = new Array(len).fill(null);
    chart.update('none');

    const obj = { progress: 0 };
    gsap.to(obj, {
      progress: 1,
      duration: 0.8,
      ease: 'power2.out',
      onUpdate: () => {
        const visibleCount = Math.ceil(obj.progress * len);
        dataset.data = originalData.map((v, i) => (i < visibleCount ? v : null));
        chart.update('none');
      },
    });
  }

  /**
   * Hero parallax — subtle grid-lines movement on scroll
   * Motivated: hierarchy (creating depth between layers)
   */
  function initHeroParallax() {
    if (prefersReducedMotion) return;

    gsap.to('.hero__grid-lines', {
      yPercent: 20,
      ease: 'none',
      scrollTrigger: {
        trigger: '.hero',
        start: 'top top',
        end: 'bottom top',
        scrub: 1,
      },
    });
  }

  /* ============================================================
     UTILITY FUNCTIONS
     ============================================================ */

  async function fetchWithRetry(url, retries = CONFIG.maxRetries) {
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
      } catch (err) {
        if (attempt === retries) throw err;
        const delay = CONFIG.retryBaseDelay * (attempt + 1);
        await new Promise((r) => setTimeout(r, delay));
      }
    }
  }

  function formatUSD(value, compact) {
    if (value == null) return '--';
    if (compact) {
      if (value >= 1e12) return '$' + (value / 1e12).toFixed(2) + 'T';
      if (value >= 1e9) return '$' + (value / 1e9).toFixed(2) + 'B';
      if (value >= 1e6) return '$' + (value / 1e6).toFixed(2) + 'M';
    }
    if (value >= 1) return '$' + value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (value >= 0.01) return '$' + value.toFixed(4);
    return '$' + value.toFixed(8);
  }

  function formatPercent(value) {
    if (value == null) return '--';
    const sign = value >= 0 ? '+' : '';
    return sign + value.toFixed(2) + '%';
  }

  function getChangeClass(value) {
    if (value == null) return '';
    return value >= 0 ? 'price-item__change--up' : 'price-item__change--down';
  }

  function getTextClass(value) {
    if (value == null) return '';
    return value >= 0 ? 'text-up' : 'text-down';
  }

  /* ---------- Clock ---------- */
  function startClock() {
    const el = document.getElementById('hero-time');
    if (!el) return;
    function tick() {
      const now = new Date();
      el.textContent = now.toLocaleString('en-US', {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      });
    }
    tick();
    setInterval(tick, 1000);
  }

  /* ---------- Skeleton Helpers ---------- */
  function showSkeleton(containerId, count, type) {
    const container = document.getElementById(containerId);
    if (!container) return;
    let html = '';
    for (let i = 0; i < count; i++) {
      if (type === 'price') {
        html += `
          <div class="price-item">
            <div class="price-item__top">
              <div class="skeleton" style="width:80px;height:28px;border-radius:14px"></div>
              <div class="skeleton" style="width:50px;height:20px"></div>
            </div>
            <div class="skeleton skeleton--value"></div>
            <div class="skeleton skeleton--chart"></div>
          </div>`;
      } else if (type === 'trending') {
        html += `
          <div class="trending-item">
            <div class="skeleton" style="width:20px;height:20px;border-radius:50%"></div>
            <div class="skeleton" style="width:24px;height:24px;border-radius:50%"></div>
            <div style="flex:1"><div class="skeleton skeleton--text"></div></div>
            <div class="skeleton" style="width:60px;height:16px"></div>
          </div>`;
      } else if (type === 'stat') {
        html += `
          <div class="market-stat">
            <div class="skeleton skeleton--text" style="margin:0 auto 0.5rem"></div>
            <div class="skeleton skeleton--value" style="margin:0 auto"></div>
          </div>`;
      }
    }
    container.innerHTML = html;
  }

  function showError(containerId, message, retryFn) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = `
      <div class="error-state">
        ${ICON_ALERT}
        <p class="error-state__message">${message}</p>
        ${retryFn ? '<button class="error-state__retry" data-retry="true">Retry</button>' : ''}
      </div>`;
    if (retryFn) {
      const btn = container.querySelector('[data-retry]');
      if (btn) btn.addEventListener('click', retryFn);
    }
  }

  /* ---------- Mini Sparkline Charts (Chart.js) ---------- */
  const sparklineCharts = {};

  function createSparkline(canvasId, data, isPositive) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    if (sparklineCharts[canvasId]) {
      sparklineCharts[canvasId].destroy();
    }

    const color = isPositive
      ? getComputedStyle(document.documentElement).getPropertyValue('--color-accent').trim() || '#39ff14'
      : getComputedStyle(document.documentElement).getPropertyValue('--color-danger').trim() || '#ff4757';

    const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
    gradient.addColorStop(0, isPositive ? 'rgba(57,255,20,0.15)' : 'rgba(255,71,87,0.15)');
    gradient.addColorStop(1, 'rgba(0,0,0,0)');

    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.map((_, i) => i),
        datasets: [{
          data: data,
          borderColor: color,
          borderWidth: 1.5,
          backgroundColor: gradient,
          fill: true,
          pointRadius: 0,
          tension: 0.4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        scales: {
          x: { display: false },
          y: { display: false },
        },
        animation: { duration: 0 },
      },
    });

    sparklineCharts[canvasId] = chart;

    /* Animate the sparkline draw-in */
    animateSparklineDraw(chart);
  }

  /* ---------- Fear & Greed Gauge (Canvas) ---------- */
  function drawGauge(value, label) {
    const canvas = document.getElementById('gauge-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    const cx = w / 2;
    const cy = h - 10;
    const radius = Math.min(cx, cy) - 10;
    const startAngle = Math.PI;

    /* Background arc segments */
    const segments = [
      { end: 0.25, color: '#ff4757' },
      { end: 0.45, color: '#ff8c42' },
      { end: 0.55, color: '#ffd93d' },
      { end: 0.75, color: '#6bcb77' },
      { end: 1.0,  color: '#39ff14' },
    ];

    let prevEnd = 0;
    segments.forEach((seg) => {
      const a1 = startAngle + prevEnd * Math.PI;
      const a2 = startAngle + seg.end * Math.PI;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, a1, a2);
      ctx.lineWidth = 12;
      ctx.strokeStyle = seg.color;
      ctx.lineCap = 'round';
      ctx.globalAlpha = 0.15;
      ctx.stroke();
      prevEnd = seg.end;
    });

    /* Active arc — animated with GSAP */
    ctx.globalAlpha = 1;
    const activeGrad = ctx.createLinearGradient(cx - radius, cy, cx + radius, cy);
    activeGrad.addColorStop(0, '#ff4757');
    activeGrad.addColorStop(0.5, '#ffd93d');
    activeGrad.addColorStop(1, '#39ff14');

    if (prefersReducedMotion) {
      /* Static draw */
      const activeEnd = startAngle + (value / 100) * Math.PI;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, startAngle, activeEnd);
      ctx.lineWidth = 12;
      ctx.strokeStyle = activeGrad;
      ctx.lineCap = 'round';
      ctx.stroke();

      /* Needle */
      const needleAngle = startAngle + (value / 100) * Math.PI;
      const needleLen = radius - 18;
      const nx = cx + needleLen * Math.cos(needleAngle);
      const ny = cy + needleLen * Math.sin(needleAngle);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(nx, ny);
      ctx.lineWidth = 2;
      ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--color-text').trim() || '#e8e8f0';
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(cx, cy, 4, 0, 2 * Math.PI);
      ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--color-text').trim() || '#e8e8f0';
      ctx.fill();
    } else {
      /* Animated gauge sweep */
      const obj = { progress: 0 };
      gsap.to(obj, {
        progress: value / 100,
        duration: 1.5,
        ease: 'power3.out',
        onUpdate: () => {
          /* Clear and redraw background */
          ctx.clearRect(0, 0, w, h);
          let prev = 0;
          segments.forEach((seg) => {
            const a1 = startAngle + prev * Math.PI;
            const a2 = startAngle + seg.end * Math.PI;
            ctx.beginPath();
            ctx.arc(cx, cy, radius, a1, a2);
            ctx.lineWidth = 12;
            ctx.strokeStyle = seg.color;
            ctx.lineCap = 'round';
            ctx.globalAlpha = 0.15;
            ctx.stroke();
            prev = seg.end;
          });

          /* Active arc */
          ctx.globalAlpha = 1;
          const activeEnd = startAngle + obj.progress * Math.PI;
          ctx.beginPath();
          ctx.arc(cx, cy, radius, startAngle, activeEnd);
          ctx.lineWidth = 12;
          ctx.strokeStyle = activeGrad;
          ctx.lineCap = 'round';
          ctx.stroke();

          /* Needle */
          const needleAngle = startAngle + obj.progress * Math.PI;
          const needleLen = radius - 18;
          const nx = cx + needleLen * Math.cos(needleAngle);
          const ny = cy + needleLen * Math.sin(needleAngle);
          ctx.beginPath();
          ctx.moveTo(cx, cy);
          ctx.lineTo(nx, ny);
          ctx.lineWidth = 2;
          ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--color-text').trim() || '#e8e8f0';
          ctx.stroke();

          /* Center dot */
          ctx.beginPath();
          ctx.arc(cx, cy, 4, 0, 2 * Math.PI);
          ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--color-text').trim() || '#e8e8f0';
          ctx.fill();
        },
      });
    }

    /* Update text elements */
    const valueEl = document.getElementById('gauge-value');
    const labelEl = document.getElementById('gauge-label');
    if (valueEl) {
      animateCounter(valueEl, value, '', '', 0);
    }
    if (labelEl) {
      labelEl.textContent = label;
      if (value <= 25) labelEl.style.color = '#ff4757';
      else if (value <= 45) labelEl.style.color = '#ff8c42';
      else if (value <= 55) labelEl.style.color = '#ffd93d';
      else if (value <= 75) labelEl.style.color = '#6bcb77';
      else labelEl.style.color = '#39ff14';
    }
  }

  /* ============================================================
     DATA FETCHERS
     ============================================================ */

  /* 1. Price Tracker */
  let isFirstPriceLoad = true;
  async function fetchPrices() {
    const container = document.getElementById('price-grid');
    if (!container) return;

    if (isFirstPriceLoad) {
      showSkeleton('price-grid', CONFIG.trackedTokens.length, 'price');
    }

    try {
      const ids = CONFIG.trackedTokens.join(',');
      const data = await fetchWithRetry(API.prices(ids));

      if (!data || data.length === 0) {
        showError('price-grid', 'No price data available', fetchPrices);
        return;
      }

      let html = '';
      data.forEach((coin) => {
        const change24h = coin.price_change_percentage_24h;
        const canvasId = `spark-${coin.id}`;

        html += `
          <div class="price-item">
            <div class="price-item__top">
              <div class="price-item__name">
                <img class="price-item__icon" src="${coin.image}" alt="${coin.name}" loading="lazy" />
                <div>
                  <div class="price-item__symbol">${coin.symbol}</div>
                  <div class="price-item__token-name">${coin.name}</div>
                </div>
              </div>
              <span class="price-item__change ${getChangeClass(change24h)}">${formatPercent(change24h)}</span>
            </div>
            <div class="price-item__value">${formatUSD(coin.current_price)}</div>
            <div class="price-item__chart">
              <canvas id="${canvasId}"></canvas>
            </div>
          </div>`;
      });

      container.innerHTML = html;

      /* Pulse the parent card on data refresh (not first load) */
      if (!isFirstPriceLoad) {
        pulseCard(container.closest('.card'));
      }

      /* Draw sparklines + animate price items entrance */
      requestAnimationFrame(() => {
        data.forEach((coin) => {
          const sparkData = coin.sparkline_in_7d?.price || [];
          if (sparkData.length > 0) {
            const sampled = sampleArray(sparkData, 48);
            createSparkline(`spark-${coin.id}`, sampled, coin.price_change_percentage_24h >= 0);
          }
        });

        /* Stagger entrance for price items on first load */
        if (isFirstPriceLoad && !prefersReducedMotion) {
          gsap.from('.price-item', {
            opacity: 0,
            y: 20,
            stagger: 0.08,
            duration: 0.5,
            ease: 'power3.out',
          });
          isFirstPriceLoad = false;
        }
      });
    } catch (err) {
      showError('price-grid', 'Failed to load price data. Check your connection.', fetchPrices);
    }
  }

  /* 2. Fear & Greed Index */
  async function fetchFearGreed() {
    const container = document.getElementById('gauge-container');
    if (!container) return;

    try {
      const data = await fetchWithRetry(API.fearGreed());
      const entry = data?.data?.[0];

      if (!entry) {
        showError('gauge-container', 'Sentiment data unavailable', fetchFearGreed);
        return;
      }

      const value = parseInt(entry.value, 10);
      const label = entry.value_classification;
      const timestamp = new Date(parseInt(entry.timestamp, 10) * 1000);

      drawGauge(value, label);

      const updatedEl = document.getElementById('gauge-updated');
      if (updatedEl) {
        updatedEl.textContent = 'Updated: ' + timestamp.toLocaleDateString('en-US', {
          month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
        });
      }
    } catch (err) {
      showError('gauge-container', 'Failed to load sentiment data', fetchFearGreed);
    }
  }

  /* 3. Trending Tokens */
  let isFirstTrendingLoad = true;
  async function fetchTrending() {
    const container = document.getElementById('trending-list');
    if (!container) return;

    if (isFirstTrendingLoad) {
      showSkeleton('trending-list', 7, 'trending');
    }

    try {
      const data = await fetchWithRetry(API.trending());
      const coins = data?.coins?.slice(0, 7) || [];

      if (coins.length === 0) {
        showError('trending-list', 'No trending data available', fetchTrending);
        return;
      }

      let html = '';
      coins.forEach((item, idx) => {
        const coin = item.item;
        const priceChange = coin.data?.price_change_percentage_24h?.usd;
        html += `
          <div class="trending-item">
            <span class="trending-item__rank">${idx + 1}</span>
            <img class="trending-item__icon" src="${coin.small}" alt="${coin.name}" loading="lazy" />
            <div class="trending-item__info">
              <div class="trending-item__name">${coin.name}</div>
              <div class="trending-item__symbol">${coin.symbol}</div>
            </div>
            <div class="trending-item__price">${coin.data?.price ? formatUSD(parseFloat(coin.data.price.replace(/[$,]/g, ''))) : '--'}</div>
            <div class="trending-item__change ${getTextClass(priceChange)}">${priceChange != null ? formatPercent(priceChange) : '--'}</div>
          </div>`;
      });

      container.innerHTML = html;

      if (!isFirstTrendingLoad) {
        pulseCard(container.closest('.card'));
      }

      /* Stagger entrance for trending items */
      if (isFirstTrendingLoad && !prefersReducedMotion) {
        gsap.from('.trending-item', {
          opacity: 0,
          x: -16,
          stagger: 0.06,
          duration: 0.4,
          ease: 'power3.out',
        });
        isFirstTrendingLoad = false;
      }
    } catch (err) {
      showError('trending-list', 'Failed to load trending data', fetchTrending);
    }
  }

  /* 4. Global Market Data */
  let isFirstGlobalLoad = true;
  async function fetchGlobal() {
    const container = document.getElementById('market-stats');
    if (!container) return;

    if (isFirstGlobalLoad) {
      showSkeleton('market-stats', 3, 'stat');
    }

    try {
      const data = await fetchWithRetry(API.global());
      const g = data?.data;

      if (!g) {
        showError('market-stats', 'Market data unavailable', fetchGlobal);
        return;
      }

      const mcap = g.total_market_cap?.usd;
      const vol = g.total_volume?.usd;
      const btcDom = g.market_cap_percentage?.btc;
      const mcapChange = g.market_cap_change_percentage_24h_usd;

      container.innerHTML = `
        <div class="market-stat">
          <div class="market-stat__label">Total Market Cap</div>
          <div class="market-stat__value">${formatUSD(mcap, true)}</div>
          <div class="market-stat__sub ${getTextClass(mcapChange)}">${formatPercent(mcapChange)} 24h</div>
        </div>
        <div class="market-stat">
          <div class="market-stat__label">BTC Dominance</div>
          <div class="market-stat__value">${btcDom != null ? btcDom.toFixed(1) + '%' : '--'}</div>
          <div class="market-stat__sub text-muted">of total market</div>
        </div>
        <div class="market-stat">
          <div class="market-stat__label">24h Volume</div>
          <div class="market-stat__value">${formatUSD(vol, true)}</div>
          <div class="market-stat__sub text-muted">global trading</div>
        </div>`;

      if (!isFirstGlobalLoad) {
        pulseCard(container.closest('.card'));
      }

      /* Stagger entrance for market stats */
      if (isFirstGlobalLoad && !prefersReducedMotion) {
        gsap.from('.market-stat', {
          opacity: 0,
          y: 16,
          scale: 0.96,
          stagger: 0.1,
          duration: 0.5,
          ease: 'power3.out',
        });
        isFirstGlobalLoad = false;
      }
    } catch (err) {
      showError('market-stats', 'Failed to load market overview', fetchGlobal);
    }
  }

  /* ---------- Utility: Sample Array ---------- */
  function sampleArray(arr, targetLen) {
    if (arr.length <= targetLen) return arr;
    const step = arr.length / targetLen;
    const result = [];
    for (let i = 0; i < targetLen; i++) {
      result.push(arr[Math.floor(i * step)]);
    }
    return result;
  }

  /* ---------- Auto-Refresh Scheduler (disabled — paid API) ---------- */
  function scheduleRefresh() {
    // No auto-refresh — CoinGecko is paid per request
  }

  /* ---------- Gauge Resize Handler (debounced) ---------- */
  function handleGaugeResize() {
    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        const valueEl = document.getElementById('gauge-value');
        if (valueEl && valueEl.textContent && valueEl.textContent !== '--') {
          const labelEl = document.getElementById('gauge-label');
          drawGauge(
            parseInt(valueEl.textContent, 10),
            labelEl ? labelEl.textContent : ''
          );
        }
      }, 250);
    });
  }

  /* ---------- Hero Image Fallback ---------- */
  function setupHeroImage() {
    const heroImageUrl = '{{HERO_IMAGE_URL}}';
    if (heroImageUrl && !heroImageUrl.startsWith('{{')) {
      const bgDiv = document.querySelector('.hero__bg-image');
      if (bgDiv) {
        bgDiv.style.backgroundImage = `url('${heroImageUrl}')`;
        bgDiv.style.opacity = '0.15';
      }
    }
  }

  /* ---------- Theme Toggle (light / dark) ---------- */
  function initTheme() {
    const stored = localStorage.getItem('trading-intel-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = stored || (prefersDark ? 'dark' : 'light');

    if (theme === 'light') {
      document.documentElement.setAttribute('data-theme', 'light');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }

    const btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.addEventListener('click', () => {
        const isLight = document.documentElement.getAttribute('data-theme') === 'light';
        if (isLight) {
          document.documentElement.removeAttribute('data-theme');
          localStorage.setItem('trading-intel-theme', 'dark');
        } else {
          document.documentElement.setAttribute('data-theme', 'light');
          localStorage.setItem('trading-intel-theme', 'light');
        }
        /* Redraw gauge — canvas ignores CSS variable changes */
        const valueEl = document.getElementById('gauge-value');
        if (valueEl && valueEl.textContent && valueEl.textContent !== '--') {
          const labelEl = document.getElementById('gauge-label');
          drawGauge(parseInt(valueEl.textContent, 10), labelEl ? labelEl.textContent : '');
        }
      });
    }
  }

  /* ============================================================
     INIT
     ============================================================ */
  function init() {
    initTheme();
    startClock();
    setupHeroImage();
    handleGaugeResize();

    /* GSAP Animations */
    animateHeroEntrance();
    animateCardEntrance();
    initCardTilt();
    initHeroParallax();

    /* Stagger initial API calls to avoid rate limits */
    fetchPrices();
    setTimeout(fetchFearGreed, 500);
    setTimeout(fetchTrending, 1000);
    setTimeout(fetchGlobal, 1500);

    /* Schedule auto-refresh */
    scheduleRefresh();
  }

  /* Wait for DOM + Chart.js + GSAP */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
