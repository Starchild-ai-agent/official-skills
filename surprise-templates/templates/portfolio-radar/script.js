/* ============================================================
   Portfolio Risk Radar — script.js
   APIs: CoinGecko (free, no key)
   Features: Doughnut allocation, Radar risk chart, Holdings table,
             Market overview, Diversification score (HHI-based)
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Configuration ---------- */
  const CONFIG = {
    trackedTokens: (() => {
      try {
        const raw = '{{TRACKED_TOKENS}}';
        if (raw.startsWith('{{')) return ['bitcoin', 'ethereum', 'solana', 'cardano', 'polkadot'];
        return JSON.parse(raw);
      } catch {
        return ['bitcoin', 'ethereum', 'solana', 'cardano', 'polkadot'];
      }
    })(),
    refreshIntervals: {
      prices: 120_000,
      global: 300_000,
    },
    maxRetries: 2,
    retryBaseDelay: 1500,
  };

  const API = {
    prices: (ids) =>
      `https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=${ids}&order=market_cap_desc&sparkline=false&price_change_percentage=24h`,
    global: () =>
      'https://api.coingecko.com/api/v3/global',
  };

  /* SVG icons (Lucide) */
  const ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';

  /* Chart instances */
  let doughnutChart = null;
  let radarChart = null;

  /* Cached data for theme-switch redraws */
  let cachedPortfolioData = null;
  let cachedRiskScores = null;

  /* ---------- Utility: Fetch with Retry ---------- */
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

  /* ---------- Utility: Formatters ---------- */
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

  function getTextClass(value) {
    if (value == null) return '';
    return value >= 0 ? 'text-up' : 'text-down';
  }

  function getChangeClass(value) {
    if (value == null) return '';
    return value >= 0 ? 'hero__portfolio-change--up' : 'hero__portfolio-change--down';
  }

  /* ---------- CSS Variable Reader ---------- */
  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
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
      if (type === 'chart') {
        html += '<div class="skeleton skeleton--chart"></div>';
      } else if (type === 'row') {
        html += '<div class="skeleton skeleton--row"></div>';
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

  /* ---------- Risk Score Calculations ---------- */

  /**
   * Calculate risk scores for the portfolio based on market data.
   * Returns an object with 5 dimensions (0-100 each):
   * - volatility: based on 24h price change magnitude
   * - liquidity: based on total volume / market cap ratio
   * - marketCap: based on average market cap rank
   * - correlation: simulated based on how similar price changes are
   * - concentration: based on HHI of portfolio weights
   */
  function calculateRiskScores(coins) {
    const totalMcap = coins.reduce((s, c) => s + (c.market_cap || 0), 0);
    const weights = coins.map((c) => (c.market_cap || 0) / (totalMcap || 1));

    /* Volatility: average absolute 24h change, scaled 0-100 */
    const avgVolatility = coins.reduce((s, c) => s + Math.abs(c.price_change_percentage_24h || 0), 0) / coins.length;
    const volatility = Math.min(100, Math.round(avgVolatility * 5));

    /* Liquidity: average volume/mcap ratio, higher = more liquid = lower risk */
    const avgLiqRatio = coins.reduce((s, c) => {
      const ratio = (c.total_volume || 0) / (c.market_cap || 1);
      return s + ratio;
    }, 0) / coins.length;
    const liquidity = Math.min(100, Math.round(avgLiqRatio * 500));

    /* Market Cap: based on average rank, lower rank = lower risk */
    const avgRank = coins.reduce((s, c) => s + (c.market_cap_rank || 100), 0) / coins.length;
    const marketCapScore = Math.max(0, Math.min(100, Math.round(100 - avgRank * 1.5)));

    /* Correlation: simulated — how similar are the 24h changes */
    const changes = coins.map((c) => c.price_change_percentage_24h || 0);
    const avgChange = changes.reduce((s, v) => s + v, 0) / changes.length;
    const variance = changes.reduce((s, v) => s + Math.pow(v - avgChange, 2), 0) / changes.length;
    const correlation = Math.max(0, Math.min(100, 100 - Math.round(Math.sqrt(variance) * 10)));

    /* Concentration: HHI-based */
    const hhi = weights.reduce((s, w) => s + w * w, 0);
    const maxHHI = 1; // single asset
    const minHHI = 1 / coins.length; // equal distribution
    const normalizedHHI = (hhi - minHHI) / (maxHHI - minHHI || 1);
    const concentration = Math.round(normalizedHHI * 100);

    return { volatility, liquidity, marketCap: marketCapScore, correlation, concentration };
  }

  /**
   * Calculate diversification score (0-100) based on HHI.
   * Lower HHI = better diversification = higher score.
   */
  function calculateDiversityScore(coins) {
    const totalMcap = coins.reduce((s, c) => s + (c.market_cap || 0), 0);
    if (totalMcap === 0) return { score: 0, hhi: 1, effectiveN: 1, label: 'N/A' };

    const weights = coins.map((c) => (c.market_cap || 0) / totalMcap);
    const hhi = weights.reduce((s, w) => s + w * w, 0);
    const effectiveN = 1 / hhi; // effective number of assets

    /* Score: 100 = perfectly diversified, 0 = single asset */
    const minHHI = 1 / coins.length;
    const score = Math.round(((1 - hhi) / (1 - minHHI || 1)) * 100);

    let label;
    if (score >= 80) label = 'Excellent';
    else if (score >= 60) label = 'Good';
    else if (score >= 40) label = 'Moderate';
    else if (score >= 20) label = 'Concentrated';
    else label = 'High Risk';

    return { score: Math.max(0, Math.min(100, score)), hhi, effectiveN, label };
  }

  /**
   * Determine risk level for a single coin.
   */
  function getRiskLevel(coin) {
    const rank = coin.market_cap_rank || 999;
    const vol = Math.abs(coin.price_change_percentage_24h || 0);

    if (rank <= 10 && vol < 5) return 'low';
    if (rank <= 30 && vol < 10) return 'medium';
    if (rank > 50 || vol > 15) return 'high';
    return 'medium';
  }

  /* ---------- Chart: Allocation Doughnut ---------- */
  function renderAllocationChart(coins) {
    const canvas = document.getElementById('allocation-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    if (doughnutChart) {
      doughnutChart.destroy();
    }

    const totalMcap = coins.reduce((s, c) => s + (c.market_cap || 0), 0);
    const labels = coins.map((c) => c.symbol.toUpperCase());
    const data = coins.map((c) => (c.market_cap || 0) / (totalMcap || 1) * 100);
    const chartColors = [
      cssVar('--chart-1') || '#00bcd4',
      cssVar('--chart-2') || '#ff6f61',
      cssVar('--chart-3') || '#26c6da',
      cssVar('--chart-4') || '#ffab40',
      cssVar('--chart-5') || '#7c4dff',
      cssVar('--chart-6') || '#69f0ae',
    ];

    doughnutChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: chartColors.slice(0, coins.length),
          borderColor: 'transparent',
          borderWidth: 0,
          hoverOffset: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '68%',
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: cssVar('--bg-card') || 'rgba(15,30,53,0.95)',
            titleColor: cssVar('--text-primary') || '#d4e5f7',
            bodyColor: cssVar('--text-secondary') || '#7a9bb5',
            borderColor: cssVar('--border') || 'rgba(0,188,212,0.12)',
            borderWidth: 1,
            padding: 10,
            cornerRadius: 8,
            titleFont: { family: cssVar('--font-heading') || 'Outfit' },
            bodyFont: { family: cssVar('--font-mono') || 'Fira Code' },
            callbacks: {
              label: (ctx) => ` ${ctx.parsed.toFixed(1)}%`,
            },
          },
        },
        animation: { duration: 800, easing: 'easeOutQuart' },
      },
    });

    /* Update center text */
    const centerValue = document.getElementById('allocation-center-value');
    if (centerValue) {
      centerValue.textContent = coins.length.toString();
    }

    /* Update legend */
    const legendContainer = document.getElementById('allocation-legend');
    if (legendContainer) {
      legendContainer.innerHTML = coins.map((c, i) => {
        const pct = data[i];
        const color = chartColors[i % chartColors.length];
        return `
          <div class="legend-item">
            <span class="legend-item__dot" style="background:${color}"></span>
            <span class="legend-item__name">${c.name}</span>
            <span class="legend-item__pct">${pct.toFixed(1)}%</span>
          </div>`;
      }).join('');
    }
  }

  /* ---------- Chart: Risk Radar ---------- */
  function renderRadarChart(scores) {
    const canvas = document.getElementById('radar-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    if (radarChart) {
      radarChart.destroy();
    }

    const labels = ['Volatility', 'Liquidity', 'Market Cap', 'Correlation', 'Concentration'];
    const data = [scores.volatility, scores.liquidity, scores.marketCap, scores.correlation, scores.concentration];

    radarChart = new Chart(ctx, {
      type: 'radar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Risk Profile',
          data: data,
          backgroundColor: cssVar('--radar-fill') || 'rgba(0,188,212,0.15)',
          borderColor: cssVar('--radar-stroke') || 'rgba(0,188,212,0.7)',
          borderWidth: 2,
          pointBackgroundColor: cssVar('--accent-1') || '#00bcd4',
          pointBorderColor: cssVar('--accent-1') || '#00bcd4',
          pointRadius: 4,
          pointHoverRadius: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: cssVar('--bg-card') || 'rgba(15,30,53,0.95)',
            titleColor: cssVar('--text-primary') || '#d4e5f7',
            bodyColor: cssVar('--text-secondary') || '#7a9bb5',
            borderColor: cssVar('--border') || 'rgba(0,188,212,0.12)',
            borderWidth: 1,
            padding: 10,
            cornerRadius: 8,
            bodyFont: { family: cssVar('--font-mono') || 'Fira Code' },
            callbacks: {
              label: (ctx) => ` ${ctx.parsed.r}/100`,
            },
          },
        },
        scales: {
          r: {
            beginAtZero: true,
            max: 100,
            ticks: {
              stepSize: 20,
              color: cssVar('--text-muted') || '#4e6d85',
              backdropColor: 'transparent',
              font: { family: cssVar('--font-mono') || 'Fira Code', size: 10 },
            },
            grid: {
              color: cssVar('--radar-grid') || 'rgba(0,188,212,0.08)',
            },
            angleLines: {
              color: cssVar('--radar-grid') || 'rgba(0,188,212,0.08)',
            },
            pointLabels: {
              color: cssVar('--text-secondary') || '#7a9bb5',
              font: { family: cssVar('--font-body') || 'Source Sans 3', size: 12, weight: '600' },
            },
          },
        },
        animation: { duration: 1000, easing: 'easeOutQuart' },
      },
    });

    /* Update summary metrics */
    const avgRisk = Math.round((scores.volatility + scores.concentration + (100 - scores.liquidity) + (100 - scores.marketCap)) / 4);
    const summaryEl = document.getElementById('radar-summary');
    if (summaryEl) {
      summaryEl.innerHTML = `
        <div class="radar-metric">
          <div class="radar-metric__value">${avgRisk}</div>
          <div class="radar-metric__label">Avg Risk</div>
        </div>
        <div class="radar-metric">
          <div class="radar-metric__value">${scores.volatility}</div>
          <div class="radar-metric__label">Volatility</div>
        </div>
        <div class="radar-metric">
          <div class="radar-metric__value">${scores.concentration}</div>
          <div class="radar-metric__label">Concentration</div>
        </div>`;
    }
  }

  /* ---------- Holdings Table ---------- */
  function renderHoldingsTable(coins) {
    const container = document.getElementById('holdings-table');
    if (!container) return;

    const totalMcap = coins.reduce((s, c) => s + (c.market_cap || 0), 0);

    let rows = '';
    coins.forEach((coin) => {
      const change = coin.price_change_percentage_24h;
      const weight = ((coin.market_cap || 0) / (totalMcap || 1) * 100);
      const risk = getRiskLevel(coin);

      rows += `
        <tr>
          <td>
            <div class="holdings-table__token">
              <img class="holdings-table__icon" src="${coin.image}" alt="${coin.name}" loading="lazy" />
              <div>
                <div class="holdings-table__name">${coin.name}</div>
                <div class="holdings-table__symbol">${coin.symbol}</div>
              </div>
            </div>
          </td>
          <td class="holdings-table__price">${formatUSD(coin.current_price)}</td>
          <td class="holdings-table__change ${getTextClass(change)}">${formatPercent(change)}</td>
          <td class="holdings-table__pct">${weight.toFixed(1)}%</td>
          <td><span class="risk-badge risk-badge--${risk}">${risk}</span></td>
        </tr>`;
    });

    container.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Token</th>
            <th>Price</th>
            <th>24h Change</th>
            <th>Weight</th>
            <th>Risk</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  /* ---------- Diversification Score Ring ---------- */
  function renderDiversityScore(coins) {
    const { score, hhi, effectiveN, label } = calculateDiversityScore(coins);

    /* SVG ring */
    const ringFg = document.getElementById('score-ring-fg');
    const circumference = 2 * Math.PI * 68; // r=68
    if (ringFg) {
      ringFg.style.strokeDasharray = circumference;
      ringFg.style.strokeDashoffset = circumference;
      /* Animate after a brief delay */
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          const offset = circumference - (score / 100) * circumference;
          ringFg.style.strokeDashoffset = offset;
        });
      });
    }

    /* Value */
    const valueEl = document.getElementById('diversity-value');
    if (valueEl) valueEl.textContent = score;

    /* Label */
    const labelEl = document.getElementById('diversity-label');
    if (labelEl) labelEl.textContent = label;

    /* Description */
    const descEl = document.getElementById('diversity-desc');
    if (descEl) {
      if (score >= 60) {
        descEl.textContent = 'Your portfolio shows good diversification across multiple assets, reducing concentration risk.';
      } else if (score >= 30) {
        descEl.textContent = 'Your portfolio has moderate diversification. Consider adding more uncorrelated assets.';
      } else {
        descEl.textContent = 'Your portfolio is highly concentrated. Diversifying across more assets could reduce risk.';
      }
    }

    /* Breakdown */
    const breakdownEl = document.getElementById('diversity-breakdown');
    if (breakdownEl) {
      breakdownEl.innerHTML = `
        <div class="breakdown-item">
          <div class="breakdown-item__value">${(hhi * 10000).toFixed(0)}</div>
          <div class="breakdown-item__label">HHI Index</div>
        </div>
        <div class="breakdown-item">
          <div class="breakdown-item__value">${effectiveN.toFixed(1)}</div>
          <div class="breakdown-item__label">Effective N</div>
        </div>
        <div class="breakdown-item">
          <div class="breakdown-item__value">${coins.length}</div>
          <div class="breakdown-item__label">Assets</div>
        </div>`;
    }
  }

  /* ---------- Data Fetchers ---------- */

  /* Main portfolio data fetch */
  async function fetchPortfolioData() {
    showSkeleton('allocation-chart-area', 1, 'chart');
    showSkeleton('radar-chart-area', 1, 'chart');
    showSkeleton('holdings-table', 4, 'row');

    try {
      const ids = CONFIG.trackedTokens.join(',');
      const data = await fetchWithRetry(API.prices(ids));

      if (!data || data.length === 0) {
        showError('allocation-chart-area', 'No portfolio data available', fetchPortfolioData);
        showError('radar-chart-area', 'No risk data available', fetchPortfolioData);
        showError('holdings-table', 'No holdings data available', fetchPortfolioData);
        return;
      }

      /* Cache data for theme-switch redraws */
      cachedPortfolioData = data;

      /* Update hero portfolio value */
      const totalValue = data.reduce((s, c) => s + (c.market_cap || 0), 0);
      const heroValue = document.getElementById('hero-portfolio-value');
      if (heroValue) heroValue.textContent = formatUSD(totalValue, true);

      /* Calculate weighted 24h change */
      const weightedChange = data.reduce((s, c) => {
        const weight = (c.market_cap || 0) / (totalValue || 1);
        return s + weight * (c.price_change_percentage_24h || 0);
      }, 0);
      const heroChange = document.getElementById('hero-portfolio-change');
      if (heroChange) {
        heroChange.textContent = formatPercent(weightedChange);
        heroChange.className = 'hero__portfolio-change ' + getChangeClass(weightedChange);
      }

      /* Render allocation chart */
      const allocArea = document.getElementById('allocation-chart-area');
      if (allocArea) {
        allocArea.innerHTML = `
          <div class="allocation-chart">
            <div class="allocation-chart__canvas-wrap">
              <canvas id="allocation-canvas" aria-label="Asset allocation doughnut chart" role="img"></canvas>
              <div class="allocation-chart__center">
                <div class="allocation-chart__center-label">Assets</div>
                <div class="allocation-chart__center-value" id="allocation-center-value">${data.length}</div>
              </div>
            </div>
            <div class="allocation-chart__legend" id="allocation-legend"></div>
          </div>`;
        renderAllocationChart(data);
      }

      /* Calculate and render risk radar */
      const scores = calculateRiskScores(data);
      cachedRiskScores = scores;
      const radarArea = document.getElementById('radar-chart-area');
      if (radarArea) {
        radarArea.innerHTML = `
          <div class="radar-chart">
            <div class="radar-chart__canvas-wrap">
              <canvas id="radar-canvas" aria-label="Risk radar chart showing 5 risk dimensions" role="img"></canvas>
            </div>
            <div class="radar-chart__summary" id="radar-summary"></div>
          </div>`;
        renderRadarChart(scores);
      }

      /* Render holdings table */
      renderHoldingsTable(data);

      /* Render diversity score */
      renderDiversityScore(data);

      /* Re-observe new scroll-reveal elements */
      observeReveal();

    } catch (err) {
      showError('allocation-chart-area', 'Failed to load portfolio data. Check your connection.', fetchPortfolioData);
      showError('radar-chart-area', 'Failed to load risk data.', fetchPortfolioData);
      showError('holdings-table', 'Failed to load holdings data.', fetchPortfolioData);
    }
  }

  /* Global market data */
  async function fetchGlobal() {
    const container = document.getElementById('market-stats');
    if (!container) return;

    showSkeleton('market-stats', 3, 'stat');

    try {
      const data = await fetchWithRetry(API.global());
      const g = data?.data;

      if (!g) {
        showError('market-stats', 'Market data unavailable', fetchGlobal);
        return;
      }

      const mcap = g.total_market_cap?.usd;
      const btcDom = g.market_cap_percentage?.btc;
      const mcapChange = g.market_cap_change_percentage_24h_usd;
      const activeCryptos = g.active_cryptocurrencies;

      container.innerHTML = `
        <div class="market-stat scroll-reveal">
          <div class="market-stat__label">Total Market Cap</div>
          <div class="market-stat__value">${formatUSD(mcap, true)}</div>
          <div class="market-stat__sub ${getTextClass(mcapChange)}">${formatPercent(mcapChange)} 24h</div>
        </div>
        <div class="market-stat scroll-reveal">
          <div class="market-stat__label">BTC Dominance</div>
          <div class="market-stat__value">${btcDom != null ? btcDom.toFixed(1) + '%' : '--'}</div>
          <div class="market-stat__sub text-muted">of total market</div>
        </div>
        <div class="market-stat scroll-reveal">
          <div class="market-stat__label">Active Cryptos</div>
          <div class="market-stat__value">${activeCryptos != null ? activeCryptos.toLocaleString() : '--'}</div>
          <div class="market-stat__sub text-muted">tracked globally</div>
        </div>`;

      observeReveal();
    } catch (err) {
      showError('market-stats', 'Failed to load market overview', fetchGlobal);
    }
  }

  /* ---------- Scroll Reveal (IntersectionObserver, per SKILL.md) ---------- */
  function observeReveal() {
    const elements = document.querySelectorAll('.scroll-reveal:not(.visible)');
    if (!elements.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -10% 0px' }
    );

    elements.forEach((el) => observer.observe(el));
  }

  /* ---------- Auto-Refresh Scheduler (disabled — paid API) ---------- */
  function scheduleRefresh() {
    // No auto-refresh — CoinGecko is paid per request
  }

  /* ---------- Hero Image Fallback ---------- */
  function setupHeroImage() {
    const heroImageUrl = '{{HERO_IMAGE_URL}}';
    if (heroImageUrl && !heroImageUrl.startsWith('{{')) {
      const bgDiv = document.querySelector('.hero__bg-image');
      if (bgDiv) {
        bgDiv.style.backgroundImage = `url('${heroImageUrl}')`;
      }
    }
  }

  /* ---------- Theme Toggle (light / dark) ---------- */
  function initTheme() {
    const stored = localStorage.getItem('portfolio-radar-theme');
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
          localStorage.setItem('portfolio-radar-theme', 'dark');
        } else {
          document.documentElement.setAttribute('data-theme', 'light');
          localStorage.setItem('portfolio-radar-theme', 'light');
        }
        /* Redraw charts with new theme colors */
        if (cachedPortfolioData) {
          renderAllocationChart(cachedPortfolioData);
        }
        if (cachedRiskScores) {
          renderRadarChart(cachedRiskScores);
        }
      });
    }
  }

  /* ---------- Init ---------- */
  function init() {
    initTheme();
    startClock();
    setupHeroImage();

    /* Stagger initial API calls to avoid rate limits */
    fetchPortfolioData();
    setTimeout(fetchGlobal, 800);

    /* Observe initial static scroll-reveal elements */
    observeReveal();

    /* Schedule auto-refresh */
    scheduleRefresh();
  }

  /* Wait for DOM + Chart.js */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();