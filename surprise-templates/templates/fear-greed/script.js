/* ============================================================
   Crypto Fear & Greed Index — script.js

   APIs: Alternative.me Fear & Greed (unlimited) + CoinGecko (30/min)
   Visuals: Canvas gauge (arc gradient) + Chart.js trend line
   Animation: IntersectionObserver scroll-reveal
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Reduced Motion ---------- */
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Configuration ---------- */
  const CONFIG = {
    maxRetries: 2,
    retryBaseDelay: 1500,
    trendDays: 31,
    templateId: 'fear-greed',
  };

  const API = {
    fng: (limit) =>
      `https://api.alternative.me/fng/?limit=${limit}&format=json`,
    globalMarket: () =>
      'https://api.coingecko.com/api/v3/global',
    coinPrice: (ids) =>
      `https://api.coingecko.com/api/v3/simple/price?ids=${ids}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true`,
  };

  /* ---------- Lucide SVG Icons ---------- */
  const ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';

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

  function showError(containerId, message, retryFn) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = `
      <div class="error-state">
        ${ICON_ALERT}
        <p class="error-state__message">${message}</p>
        <button class="error-state__retry" type="button">Retry</button>
      </div>`;
    const btn = container.querySelector('.error-state__retry');
    if (btn && retryFn) {
      btn.addEventListener('click', retryFn);
    }
  }

  function formatCurrency(value) {
    if (value == null) return '--';
    if (value >= 1e12) return '$' + (value / 1e12).toFixed(2) + 'T';
    if (value >= 1e9) return '$' + (value / 1e9).toFixed(2) + 'B';
    if (value >= 1e6) return '$' + (value / 1e6).toFixed(2) + 'M';
    return '$' + value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function formatPercent(value) {
    if (value == null) return '--';
    const sign = value >= 0 ? '+' : '';
    return sign + value.toFixed(2) + '%';
  }

  function getClassification(value) {
    const v = parseInt(value, 10);
    if (v <= 24) return 'Extreme Fear';
    if (v <= 49) return 'Fear';
    if (v <= 54) return 'Neutral';
    if (v <= 74) return 'Greed';
    return 'Extreme Greed';
  }

  function getCSSVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  /* ============================================================
     THEME
     ============================================================ */

  function initTheme() {
    const stored = localStorage.getItem(CONFIG.templateId + '-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = stored || (prefersDark ? 'dark' : 'light');
    if (theme === 'light') {
      document.documentElement.setAttribute('data-theme', 'light');
    }
    document.getElementById('theme-toggle')?.addEventListener('click', () => {
      const isLight = document.documentElement.getAttribute('data-theme') === 'light';
      if (isLight) {
        document.documentElement.removeAttribute('data-theme');
      } else {
        document.documentElement.setAttribute('data-theme', 'light');
      }
      localStorage.setItem(CONFIG.templateId + '-theme', isLight ? 'dark' : 'light');
      // Redraw canvas gauge on theme change
      if (lastGaugeValue !== null) {
        drawGauge(lastGaugeValue);
      }
      // Redraw chart on theme change
      if (lastTrendData) {
        renderTrendChart(lastTrendData);
      }
    });
  }

  /* ============================================================
     DATE DISPLAY
     ============================================================ */

  function initDate() {
    const el = document.getElementById('header-date');
    if (!el) return;
    const now = new Date();
    el.textContent = now.toLocaleDateString('en-US', {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }

  /* ============================================================
     SCROLL REVEAL
     ============================================================ */

  function initScrollReveal() {
    if (prefersReducedMotion) {
      document.querySelectorAll('.scroll-reveal').forEach((el) => {
        el.classList.add('visible');
      });
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -10% 0px' }
    );
    document.querySelectorAll('.scroll-reveal').forEach((el) => observer.observe(el));
  }

  /* ============================================================
     CANVAS GAUGE — Fear & Greed Arc
     ============================================================ */

  let lastGaugeValue = null;

  function drawGauge(value) {
    lastGaugeValue = value;
    const canvas = document.getElementById('gauge-canvas');
    if (!canvas) return;

    const dpr = window.devicePixelRatio || 1;
    const displayW = canvas.clientWidth || 520;
    const displayH = canvas.clientHeight || 320;
    canvas.width = displayW * dpr;
    canvas.height = displayH * dpr;

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, displayW, displayH);

    const cx = displayW / 2;
    const cy = displayH - 40;
    const outerR = Math.min(cx - 20, cy - 20);
    const arcWidth = outerR * 0.18;
    const innerR = outerR - arcWidth;

    const startAngle = Math.PI;
    const endAngle = 2 * Math.PI;

    // Read theme colors
    const fearColor = getCSSVar('--gauge-fear') || '#ef4444';
    const midColor = getCSSVar('--gauge-mid') || '#eab308';
    const greedColor = getCSSVar('--gauge-greed') || '#22c55e';
    const bgColor = getCSSVar('--bg-secondary') || '#0f0f2a';
    const textMuted = getCSSVar('--text-muted') || 'rgba(232,232,240,0.3)';

    // Background track
    ctx.beginPath();
    ctx.arc(cx, cy, outerR, startAngle, endAngle);
    ctx.arc(cx, cy, innerR, endAngle, startAngle, true);
    ctx.closePath();
    ctx.fillStyle = bgColor;
    ctx.fill();

    // Gradient arc
    const gradient = ctx.createLinearGradient(cx - outerR, cy, cx + outerR, cy);
    gradient.addColorStop(0, fearColor);
    gradient.addColorStop(0.35, midColor);
    gradient.addColorStop(0.65, midColor);
    gradient.addColorStop(1, greedColor);

    const valueAngle = startAngle + (value / 100) * Math.PI;

    ctx.beginPath();
    ctx.arc(cx, cy, outerR, startAngle, valueAngle);
    ctx.arc(cx, cy, innerR, valueAngle, startAngle, true);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Tick marks
    ctx.strokeStyle = textMuted;
    ctx.lineWidth = 1;
    for (let i = 0; i <= 10; i++) {
      const angle = startAngle + (i / 10) * Math.PI;
      const tickOuter = outerR + 6;
      const tickInner = outerR + 2;
      ctx.beginPath();
      ctx.moveTo(cx + tickOuter * Math.cos(angle), cy + tickOuter * Math.sin(angle));
      ctx.lineTo(cx + tickInner * Math.cos(angle), cy + tickInner * Math.sin(angle));
      ctx.stroke();
    }

    // Tick labels (0, 25, 50, 75, 100)
    ctx.font = `500 ${Math.max(10, outerR * 0.06)}px 'Geist Mono', monospace`;
    ctx.fillStyle = textMuted;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const labels = [0, 25, 50, 75, 100];
    labels.forEach((label) => {
      const angle = startAngle + (label / 100) * Math.PI;
      const labelR = outerR + 18;
      const lx = cx + labelR * Math.cos(angle);
      const ly = cy + labelR * Math.sin(angle);
      ctx.fillText(label.toString(), lx, ly);
    });

    // Needle
    const needleAngle = startAngle + (value / 100) * Math.PI;
    const needleLen = innerR - 10;
    const needleBase = 4;

    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(needleAngle);

    ctx.beginPath();
    ctx.moveTo(needleLen, 0);
    ctx.lineTo(0, -needleBase);
    ctx.lineTo(0, needleBase);
    ctx.closePath();
    ctx.fillStyle = getCSSVar('--text-primary') || '#e8e8f0';
    ctx.fill();

    ctx.restore();

    // Center dot
    ctx.beginPath();
    ctx.arc(cx, cy, 6, 0, 2 * Math.PI);
    ctx.fillStyle = getCSSVar('--accent-1') || '#7c6aff';
    ctx.fill();
  }

  function animateGauge(targetValue) {
    if (prefersReducedMotion) {
      drawGauge(targetValue);
      return;
    }
    let current = 0;
    const duration = 1200;
    const start = performance.now();

    function step(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      current = eased * targetValue;
      drawGauge(current);
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    }
    requestAnimationFrame(step);
  }

  /* ============================================================
     TREND CHART (Chart.js)
     ============================================================ */

  let trendChart = null;
  let lastTrendData = null;

  function renderTrendChart(data) {
    lastTrendData = data;
    const canvas = document.getElementById('trend-chart');
    if (!canvas) return;

    if (trendChart) {
      trendChart.destroy();
      trendChart = null;
    }

    const labels = data.map((d) => {
      const date = new Date(d.timestamp * 1000);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    const values = data.map((d) => parseInt(d.value, 10));

    const lineColor = getCSSVar('--chart-line') || '#7c6aff';
    const fillStart = getCSSVar('--chart-fill-start') || 'rgba(124,106,255,0.3)';
    const fillEnd = getCSSVar('--chart-fill-end') || 'rgba(124,106,255,0.02)';
    const gridColor = getCSSVar('--chart-grid') || 'rgba(232,232,240,0.06)';
    const textColor = getCSSVar('--text-secondary') || 'rgba(232,232,240,0.55)';

    const ctx = canvas.getContext('2d');
    const gradientFill = ctx.createLinearGradient(0, 0, 0, canvas.parentElement.clientHeight);
    gradientFill.addColorStop(0, fillStart);
    gradientFill.addColorStop(1, fillEnd);

    trendChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Fear & Greed Index',
            data: values,
            borderColor: lineColor,
            backgroundColor: gradientFill,
            borderWidth: 2,
            fill: true,
            tension: 0.35,
            pointRadius: 0,
            pointHoverRadius: 5,
            pointHoverBackgroundColor: lineColor,
            pointHoverBorderColor: lineColor,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: getCSSVar('--bg-card') || 'rgba(18,18,48,0.9)',
            titleColor: getCSSVar('--text-primary') || '#e8e8f0',
            bodyColor: getCSSVar('--text-secondary') || 'rgba(232,232,240,0.55)',
            borderColor: getCSSVar('--border') || 'rgba(124,106,255,0.12)',
            borderWidth: 1,
            cornerRadius: 8,
            padding: 12,
            titleFont: { family: "'Syne', system-ui", weight: '600', size: 13 },
            bodyFont: { family: "'Geist Mono', monospace", size: 12 },
            callbacks: {
              label: function (context) {
                const val = context.parsed.y;
                return val + ' — ' + getClassification(val);
              },
            },
          },
        },
        scales: {
          x: {
            grid: { color: gridColor, drawBorder: false },
            ticks: {
              color: textColor,
              font: { family: "'Geist Mono', monospace", size: 10 },
              maxRotation: 0,
              maxTicksLimit: 8,
            },
            border: { display: false },
          },
          y: {
            min: 0,
            max: 100,
            grid: { color: gridColor, drawBorder: false },
            ticks: {
              color: textColor,
              font: { family: "'Geist Mono', monospace", size: 10 },
              stepSize: 25,
            },
            border: { display: false },
          },
        },
      },
    });
  }

  /* ============================================================
     SCALE BAR HIGHLIGHT
     ============================================================ */

  function highlightScale(value) {
    const v = parseInt(value, 10);
    const segments = document.querySelectorAll('.scale-bar__segment');
    segments.forEach((seg) => {
      const range = seg.dataset.range;
      if (!range) return;
      const [min, max] = range.split('-').map(Number);
      if (v >= min && v <= max) {
        seg.classList.add('active');
      } else {
        seg.classList.remove('active');
      }
    });
  }

  /* ============================================================
     DATA FETCHING — Fear & Greed Index
     ============================================================ */

  async function loadFearGreedData() {
    try {
      const data = await fetchWithRetry(API.fng(CONFIG.trendDays));
      if (!data || !data.data || data.data.length === 0) {
        throw new Error('No data returned');
      }

      const entries = data.data;
      const current = entries[0];
      const currentValue = parseInt(current.value, 10);

      // Update score display
      const scoreEl = document.getElementById('gauge-score');
      const labelEl = document.getElementById('gauge-label');
      if (scoreEl) scoreEl.textContent = currentValue;
      if (labelEl) labelEl.textContent = getClassification(currentValue);

      // Animate gauge
      animateGauge(currentValue);

      // Highlight scale bar
      highlightScale(currentValue);

      // Yesterday / Week / Month stats
      const yesterday = entries[1];
      const weekAgo = entries[7];
      const monthAgo = entries[entries.length - 1];

      if (yesterday) {
        const el = document.getElementById('stat-yesterday');
        const cls = document.getElementById('stat-yesterday-class');
        if (el) el.textContent = yesterday.value;
        if (cls) cls.textContent = getClassification(yesterday.value);
      }
      if (weekAgo) {
        const el = document.getElementById('stat-week');
        const cls = document.getElementById('stat-week-class');
        if (el) el.textContent = weekAgo.value;
        if (cls) cls.textContent = getClassification(weekAgo.value);
      }
      if (monthAgo) {
        const el = document.getElementById('stat-month');
        const cls = document.getElementById('stat-month-class');
        if (el) el.textContent = monthAgo.value;
        if (cls) cls.textContent = getClassification(monthAgo.value);
      }

      // Last updated
      const updatedEl = document.getElementById('last-updated');
      if (updatedEl) {
        const ts = new Date(current.timestamp * 1000);
        updatedEl.textContent = 'Updated: ' + ts.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        });
      }

      // Trend chart (reverse to chronological order)
      const trendData = entries.slice().reverse();
      renderTrendChart(trendData);

      // Remove skeleton states from stat values
      document.querySelectorAll('.hero__stat-value').forEach((el) => {
        el.classList.remove('skeleton-text');
      });

    } catch (err) {
      showError('trend-chart-wrap', 'Failed to load Fear & Greed data', loadFearGreedData);
      // Show fallback gauge
      drawGauge(50);
      const scoreEl = document.getElementById('gauge-score');
      const labelEl = document.getElementById('gauge-label');
      if (scoreEl) scoreEl.textContent = '--';
      if (labelEl) labelEl.textContent = 'Unavailable';
    }
  }

  /* ============================================================
     DATA FETCHING — Market Overview (CoinGecko)
     ============================================================ */

  async function loadMarketData() {
    try {
      // Fetch BTC + ETH prices
      const priceData = await fetchWithRetry(API.coinPrice('bitcoin,ethereum'));
      if (!priceData) throw new Error('No price data');

      // BTC
      const btc = priceData.bitcoin;
      if (btc) {
        const priceEl = document.getElementById('btc-price');
        const changeEl = document.getElementById('btc-change');
        if (priceEl) {
          priceEl.textContent = formatCurrency(btc.usd);
          priceEl.classList.remove('skeleton-text');
        }
        if (changeEl) {
          const change = btc.usd_24h_change;
          changeEl.textContent = formatPercent(change);
          changeEl.className = 'market-card__change ' +
            (change >= 0 ? 'market-card__change--up' : 'market-card__change--down');
        }
      }

      // ETH
      const eth = priceData.ethereum;
      if (eth) {
        const priceEl = document.getElementById('eth-price');
        const changeEl = document.getElementById('eth-change');
        if (priceEl) {
          priceEl.textContent = formatCurrency(eth.usd);
          priceEl.classList.remove('skeleton-text');
        }
        if (changeEl) {
          const change = eth.usd_24h_change;
          changeEl.textContent = formatPercent(change);
          changeEl.className = 'market-card__change ' +
            (change >= 0 ? 'market-card__change--up' : 'market-card__change--down');
        }
      }

    } catch (err) {
      // Graceful degradation — show error in BTC card
      const btcPrice = document.getElementById('btc-price');
      const ethPrice = document.getElementById('eth-price');
      if (btcPrice) { btcPrice.textContent = '--'; btcPrice.classList.remove('skeleton-text'); }
      if (ethPrice) { ethPrice.textContent = '--'; ethPrice.classList.remove('skeleton-text'); }
    }

    // Fetch global market data (separate call to avoid single point of failure)
    try {
      const globalData = await fetchWithRetry(API.globalMarket());
      if (!globalData || !globalData.data) throw new Error('No global data');

      const g = globalData.data;

      // Total market cap
      const mcapEl = document.getElementById('mcap-value');
      const mcapChangeEl = document.getElementById('mcap-change');
      if (mcapEl) {
        mcapEl.textContent = formatCurrency(g.total_market_cap?.usd);
        mcapEl.classList.remove('skeleton-text');
      }
      if (mcapChangeEl) {
        const change = g.market_cap_change_percentage_24h_usd;
        mcapChangeEl.textContent = formatPercent(change);
        mcapChangeEl.className = 'market-card__change ' +
          (change >= 0 ? 'market-card__change--up' : 'market-card__change--down');
      }

      // BTC dominance
      const domEl = document.getElementById('dom-value');
      const domChangeEl = document.getElementById('dom-change');
      if (domEl) {
        const domValue = g.market_cap_percentage?.btc;
        domEl.textContent = domValue != null ? domValue.toFixed(1) + '%' : '--';
        domEl.classList.remove('skeleton-text');
      }
      if (domChangeEl) {
        // No 24h change for dominance from this endpoint, show label instead
        domChangeEl.textContent = 'of total market';
        domChangeEl.className = 'market-card__change';
        domChangeEl.style.color = getCSSVar('--text-muted');
        domChangeEl.style.background = 'transparent';
      }

    } catch (err) {
      const mcapEl = document.getElementById('mcap-value');
      const domEl = document.getElementById('dom-value');
      if (mcapEl) { mcapEl.textContent = '--'; mcapEl.classList.remove('skeleton-text'); }
      if (domEl) { domEl.textContent = '--'; domEl.classList.remove('skeleton-text'); }
    }
  }

  /* ============================================================
     CANVAS RESIZE HANDLER
     ============================================================ */

  function initResizeHandler() {
    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        if (lastGaugeValue !== null) {
          drawGauge(lastGaugeValue);
        }
      }, 200);
    });
  }

  /* ============================================================
     INIT
     ============================================================ */

  function init() {
    initTheme();
    initDate();
    initScrollReveal();
    initResizeHandler();

    // Draw initial empty gauge
    drawGauge(0);

    // Load data
    loadFearGreedData();
    loadMarketData();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
