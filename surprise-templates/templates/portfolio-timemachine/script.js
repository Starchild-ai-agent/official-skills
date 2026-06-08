/* ============================================================
   Portfolio Time Machine — script.js

   APIs: CoinGecko (free, no key) — historical market chart data
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
    portfolioValue: (() => {
      const raw = '{{PORTFOLIO_VALUE}}';
      if (raw.startsWith('{{')) return 10000;
      const val = parseFloat(raw);
      return isNaN(val) ? 10000 : val;
    })(),
    heroImageUrl: (() => {
      const raw = '{{HERO_IMAGE_URL}}';
      if (raw.startsWith('{{')) return '';
      return raw;
    })(),
    selectedPeriod: 180,
    maxRetries: 2,
    retryBaseDelay: 1500,
  };

  const SCENARIO_TOKENS = ['bitcoin', 'ethereum', 'solana'];

  const API = {
    marketChart: (id, days) =>
      `https://api.coingecko.com/api/v3/coins/${id}/market_chart?vs_currency=usd&days=${days}&interval=daily`,
    currentPrice: (ids) =>
      `https://api.coingecko.com/api/v3/simple/price?ids=${ids}&vs_currency=usd`,
  };

  const ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';

  /* ---------- State ---------- */
  let chartInstance = null;
  let historicalData = {};

  /* ============================================================
     GSAP ANIMATION SYSTEM
     ============================================================ */

  function animateHeroEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.hero-minimal__left > *, .hero-minimal__right > *', { opacity: 1, x: 0 });
      return;
    }

    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

    tl.from('.hero-minimal__label', { opacity: 0, x: 30, duration: 0.5 })
      .from('.hero-minimal__title', { opacity: 0, x: 30, duration: 0.7, ease: 'power4.out' }, '-=0.3')
      .from('.hero-minimal__subtitle', { opacity: 0, x: 30, duration: 0.4 }, '-=0.3')
      .from('.hero-minimal__kpi', { opacity: 0, x: 30, duration: 0.5, stagger: 0.1 }, '-=0.2')
      .from('.hero-minimal__time', { opacity: 0, duration: 0.4 }, '-=0.2');
  }

  function animateCardEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.timeline-card', { opacity: 1, x: 0 });
      return;
    }

    const cards = gsap.utils.toArray('.timeline-card');
    cards.forEach((card, i) => {
      gsap.to(card, {
        opacity: 1,
        x: 0,
        duration: 0.8,
        delay: i * 0.15,
        ease: 'power3.out',
        scrollTrigger: {
          trigger: card,
          start: 'top 85%',
          once: true,
        },
      });
    });

    /* Animate timeline dots */
    const dots = gsap.utils.toArray('.timeline-node__dot');
    dots.forEach((dot, i) => {
      gsap.from(dot, {
        scale: 0,
        duration: 0.4,
        delay: i * 0.15 + 0.3,
        ease: 'back.out(2)',
        scrollTrigger: {
          trigger: dot,
          start: 'top 85%',
          once: true,
        },
      });
    });
  }

  function animateCounter(element, targetValue, prefix, suffix, decimals) {
    if (prefersReducedMotion) {
      const formatted = decimals > 0
        ? targetValue.toFixed(decimals)
        : Math.round(targetValue).toLocaleString('en-US');
      element.textContent = prefix + formatted + suffix;
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

  function pulseCard(cardElement) {
    if (prefersReducedMotion || !cardElement) return;
    const card = cardElement.closest('.timeline-card') || cardElement;
    card.classList.add('data-pulse');
    setTimeout(() => card.classList.remove('data-pulse'), 600);
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

  function formatUSD(value) {
    if (value == null) return '--';
    if (value >= 1e6) return '$' + (value / 1e6).toFixed(2) + 'M';
    if (value >= 1e3) return '$' + value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    return '$' + value.toFixed(2);
  }

  function formatPercent(value) {
    if (value == null) return '--';
    const sign = value >= 0 ? '+' : '';
    return sign + value.toFixed(2) + '%';
  }

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
  function showSkeleton(containerId, type) {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (type === 'scenario') {
      container.innerHTML = `
        <div class="skeleton skeleton--value" style="margin-bottom:8px"></div>
        <div class="skeleton" style="width:80px;height:22px;margin-bottom:12px"></div>
        <div class="skeleton skeleton--text" style="margin-bottom:8px"></div>
        <div class="skeleton skeleton--text"></div>`;
    } else if (type === 'chart') {
      container.innerHTML = '<div class="skeleton skeleton--chart"></div>';
    } else if (type === 'table') {
      let rows = '';
      for (let i = 0; i < 4; i++) {
        rows += `<tr>
          <td><div class="skeleton skeleton--text" style="width:60px"></div></td>
          <td><div class="skeleton skeleton--text" style="width:80px"></div></td>
          <td><div class="skeleton skeleton--text" style="width:60px"></div></td>
          <td><div class="skeleton skeleton--text" style="width:80px"></div></td>
        </tr>`;
      }
      container.innerHTML = `<table class="comparison-table"><tbody>${rows}</tbody></table>`;
    }
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

  /* ============================================================
     DATA FETCHING
     ============================================================ */

  async function fetchHistoricalData(period) {
    const days = period || CONFIG.selectedPeriod;

    /* Show skeletons */
    SCENARIO_TOKENS.forEach((token) => {
      showSkeleton(`scenario-${token}`, 'scenario');
    });
    showSkeleton('chart-container', 'chart');
    showSkeleton('comparison-table', 'table');

    try {
      /* Fetch historical data for all scenario tokens with staggered requests */
      const results = {};
      for (const token of SCENARIO_TOKENS) {
        results[token] = await fetchWithRetry(API.marketChart(token, days));
        /* Small delay between requests to respect rate limits */
        await new Promise((r) => setTimeout(r, 300));
      }

      historicalData = results;

      /* Process and render */
      renderScenarios(results, days);
      renderChart(results, days);
      renderComparisonTable(results, days);

    } catch (err) {
      SCENARIO_TOKENS.forEach((token) => {
        showError(`scenario-${token}`, 'Failed to load data', () => fetchHistoricalData(days));
      });
      showError('chart-container', 'Failed to load chart data', () => fetchHistoricalData(days));
      showError('comparison-table', 'Failed to load comparison data', () => fetchHistoricalData(days));
    }
  }

  /* ============================================================
     SCENARIO RENDERING
     ============================================================ */

  function renderScenarios(data, days) {
    let bestScenarioValue = 0;
    let bestScenarioToken = '';

    SCENARIO_TOKENS.forEach((token) => {
      const container = document.getElementById(`scenario-${token}`);
      if (!container || !data[token]) return;

      const prices = data[token].prices;
      if (!prices || prices.length < 2) {
        showError(`scenario-${token}`, 'Insufficient data');
        return;
      }

      const startPrice = prices[0][1];
      const endPrice = prices[prices.length - 1][1];
      const priceChange = ((endPrice - startPrice) / startPrice) * 100;

      /* Calculate hypothetical value */
      const coinsAtStart = CONFIG.portfolioValue / startPrice;
      const hypotheticalValue = coinsAtStart * endPrice;
      const gain = hypotheticalValue - CONFIG.portfolioValue;

      if (hypotheticalValue > bestScenarioValue) {
        bestScenarioValue = hypotheticalValue;
        bestScenarioToken = token;
      }

      const changeClass = priceChange >= 0 ? 'scenario__change--up' : 'scenario__change--down';
      const arrow = priceChange >= 0 ? '↑' : '↓';

      container.innerHTML = `
        <div class="scenario__value">${formatUSD(hypotheticalValue)}</div>
        <div class="scenario__change ${changeClass}">${arrow} ${formatPercent(priceChange)}</div>
        <div class="scenario__detail">
          <span class="scenario__detail-label">Entry Price</span>
          <span class="scenario__detail-value">${formatUSD(startPrice)}</span>
        </div>
        <div class="scenario__detail">
          <span class="scenario__detail-label">Current Price</span>
          <span class="scenario__detail-value">${formatUSD(endPrice)}</span>
        </div>
        <div class="scenario__detail">
          <span class="scenario__detail-label">P&L</span>
          <span class="scenario__detail-value ${gain >= 0 ? 'text-up' : 'text-down'}">${gain >= 0 ? '+' : ''}${formatUSD(gain)}</span>
        </div>`;

      pulseCard(container.closest('.timeline-card'));
    });

    /* Update hero metrics */
    const heroCurrent = document.getElementById('hero-current');
    const heroBest = document.getElementById('hero-best');
    const heroGain = document.getElementById('hero-gain');

    if (heroCurrent) animateCounter(heroCurrent, CONFIG.portfolioValue, '$', '', 0);
    if (heroBest) animateCounter(heroBest, bestScenarioValue, '$', '', 0);
    if (heroGain) {
      const gainPct = ((bestScenarioValue - CONFIG.portfolioValue) / CONFIG.portfolioValue) * 100;
      animateCounter(heroGain, gainPct, '+', '%', 1);
    }
  }

  /* ============================================================
     CHART RENDERING
     ============================================================ */

  function renderChart(data, days) {
    const container = document.getElementById('chart-container');
    if (!container) return;

    /* Restore canvas */
    container.innerHTML = '<canvas id="price-chart" aria-label="Historical price comparison chart" role="img"></canvas>';
    const canvas = document.getElementById('price-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    const chartColors = [
      getComputedStyle(document.documentElement).getPropertyValue('--chart-1').trim() || '#ffbe0b',
      getComputedStyle(document.documentElement).getPropertyValue('--chart-2').trim() || '#00e5ff',
      getComputedStyle(document.documentElement).getPropertyValue('--chart-3').trim() || '#bf00ff',
    ];

    const textColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-text-muted').trim() || 'rgba(255,255,255,0.3)';
    const borderColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-border').trim() || 'rgba(255,255,255,0.06)';

    /* Normalize all prices to percentage change from start */
    const datasets = SCENARIO_TOKENS.map((token, i) => {
      const prices = data[token]?.prices || [];
      if (prices.length === 0) return null;

      const startPrice = prices[0][1];
      const normalizedData = prices.map((p) => ({
        x: new Date(p[0]),
        y: ((p[1] - startPrice) / startPrice) * 100,
      }));

      return {
        label: token.charAt(0).toUpperCase() + token.slice(1),
        data: normalizedData,
        borderColor: chartColors[i],
        backgroundColor: 'transparent',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.3,
      };
    }).filter(Boolean);

    if (chartInstance) chartInstance.destroy();

    chartInstance = new Chart(ctx, {
      type: 'line',
      data: { datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            position: 'top',
            align: 'end',
            labels: {
              color: textColor,
              font: { family: "'Satoshi', sans-serif", size: 11 },
              padding: 16,
              usePointStyle: true,
              pointStyleWidth: 8,
            },
          },
          tooltip: {
            backgroundColor: 'rgba(0,0,0,0.85)',
            titleFont: { family: "'Satoshi', sans-serif", size: 12 },
            bodyFont: { family: "'JetBrains Mono', monospace", size: 11 },
            padding: 12,
            cornerRadius: 6,
            callbacks: {
              title: (items) => {
                if (!items.length) return '';
                return items[0].raw.x.toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                });
              },
              label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y >= 0 ? '+' : ''}${ctx.parsed.y.toFixed(2)}%`,
            },
          },
        },
        scales: {
          x: {
            type: 'time',
            time: {
              unit: days <= 30 ? 'day' : days <= 90 ? 'week' : 'month',
              displayFormats: {
                day: 'MMM d',
                week: 'MMM d',
                month: 'MMM yyyy',
              },
            },
            grid: { color: borderColor, drawBorder: false },
            ticks: {
              color: textColor,
              font: { family: "'JetBrains Mono', monospace", size: 10 },
              maxTicksLimit: 8,
            },
          },
          y: {
            grid: { color: borderColor, drawBorder: false },
            ticks: {
              color: textColor,
              font: { family: "'JetBrains Mono', monospace", size: 10 },
              callback: (val) => (val >= 0 ? '+' : '') + val.toFixed(0) + '%',
            },
          },
        },
        animation: prefersReducedMotion ? false : {
          duration: 1000,
          easing: 'easeOutQuart',
        },
      },
    });

    pulseCard(container.closest('.timeline-card'));
  }

  /* ============================================================
     COMPARISON TABLE
     ============================================================ */

  function renderComparisonTable(data, days) {
    const container = document.getElementById('comparison-table');
    if (!container) return;

    const badge = document.getElementById('table-period-badge');
    if (badge) badge.textContent = `${days} days`;

    const rows = SCENARIO_TOKENS.map((token) => {
      const prices = data[token]?.prices || [];
      if (prices.length < 2) return null;

      const startPrice = prices[0][1];
      const endPrice = prices[prices.length - 1][1];
      const change = ((endPrice - startPrice) / startPrice) * 100;
      const coinsAtStart = CONFIG.portfolioValue / startPrice;
      const hypotheticalValue = coinsAtStart * endPrice;
      const pnl = hypotheticalValue - CONFIG.portfolioValue;

      return {
        token: token.charAt(0).toUpperCase() + token.slice(1),
        symbol: token === 'bitcoin' ? 'BTC' : token === 'ethereum' ? 'ETH' : 'SOL',
        change,
        hypotheticalValue,
        pnl,
      };
    }).filter(Boolean);

    let html = `
      <table class="comparison-table">
        <thead>
          <tr>
            <th>Asset</th>
            <th>Price Change</th>
            <th>Hypothetical Value</th>
            <th>P&amp;L</th>
          </tr>
        </thead>
        <tbody>`;

    rows.forEach((row) => {
      const changeClass = row.change >= 0 ? 'text-up' : 'text-down';
      const pnlClass = row.pnl >= 0 ? 'text-up' : 'text-down';

      html += `
          <tr>
            <td><strong>${row.token}</strong> <span style="color:var(--color-text-muted)">${row.symbol}</span></td>
            <td class="${changeClass}">${formatPercent(row.change)}</td>
            <td class="text-accent">${formatUSD(row.hypotheticalValue)}</td>
            <td class="${pnlClass}">${row.pnl >= 0 ? '+' : ''}${formatUSD(row.pnl)}</td>
          </tr>`;
    });

    /* Add "Hold" row */
    html += `
          <tr>
            <td><strong>Hold (No Change)</strong></td>
            <td style="color:var(--color-text-muted)">0.00%</td>
            <td>${formatUSD(CONFIG.portfolioValue)}</td>
            <td style="color:var(--color-text-muted)">$0</td>
          </tr>`;

    html += '</tbody></table>';
    container.innerHTML = html;

    pulseCard(container.closest('.timeline-card'));
  }

  /* ============================================================
     TIME PERIOD SELECTOR
     ============================================================ */

  function initTimePeriodSelector() {
    const selector = document.getElementById('time-selector');
    if (!selector) return;

    selector.addEventListener('click', (e) => {
      const btn = e.target.closest('.time-selector__btn');
      if (!btn) return;

      const period = parseInt(btn.dataset.period, 10);
      if (isNaN(period) || period === CONFIG.selectedPeriod) return;

      /* Update active state */
      selector.querySelectorAll('.time-selector__btn').forEach((b) => {
        b.classList.remove('time-selector__btn--active');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('time-selector__btn--active');
      btn.setAttribute('aria-selected', 'true');

      CONFIG.selectedPeriod = period;
      fetchHistoricalData(period);
    });
  }

  /* ============================================================
     THEME TOGGLE
     ============================================================ */

  function initThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;

    const saved = localStorage.getItem('timemachine-theme');
    if (saved === 'light') document.documentElement.setAttribute('data-theme', 'light');

    btn.addEventListener('click', () => {
      const isLight = document.documentElement.getAttribute('data-theme') === 'light';
      if (isLight) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('timemachine-theme', 'dark');
      } else {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('timemachine-theme', 'light');
      }

      /* Re-render chart with new theme colors */
      if (Object.keys(historicalData).length > 0) {
        setTimeout(() => renderChart(historicalData, CONFIG.selectedPeriod), 100);
      }
    });
  }

  /* ============================================================
     HERO IMAGE
     ============================================================ */

  function initHeroImage() {
    /* Minimal hero layout — no background image needed */
  }

  /* ============================================================
     INIT
     ============================================================ */

  function init() {
    startClock();
    initThemeToggle();
    initHeroImage();
    initTimePeriodSelector();
    animateHeroEntrance();

    /* Load data */
    fetchHistoricalData(CONFIG.selectedPeriod);

    /* Animate timeline cards after data loads */
    setTimeout(() => {
      animateCardEntrance();
    }, 200);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
