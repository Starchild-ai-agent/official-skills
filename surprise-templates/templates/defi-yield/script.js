/* ============================================================
   DeFi Yield Optimizer — script.js

   APIs: DeFi Llama Yields (free, CORS-friendly) + CoinGecko
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
        if (raw.startsWith('{{')) return ['ethereum', 'usd-coin', 'tether', 'wrapped-bitcoin', 'dai'];
        return JSON.parse(raw);
      } catch {
        return ['ethereum', 'usd-coin', 'tether', 'wrapped-bitcoin', 'dai'];
      }
    })(),
    heroImageUrl: (() => {
      const raw = '{{HERO_IMAGE_URL}}';
      if (raw.startsWith('{{')) return '';
      return raw;
    })(),
    maxRetries: 2,
    retryBaseDelay: 1500,
    maxPools: 50,
  };

  /* Token symbol mapping for DeFi Llama matching */
  const TOKEN_SYMBOLS = {
    'ethereum': ['ETH', 'WETH', 'stETH', 'rETH', 'cbETH'],
    'usd-coin': ['USDC'],
    'tether': ['USDT'],
    'wrapped-bitcoin': ['WBTC', 'BTC'],
    'dai': ['DAI'],
    'solana': ['SOL', 'mSOL', 'stSOL'],
    'bitcoin': ['WBTC', 'BTC'],
  };

  const API = {
    yields: () => 'https://yields.llama.fi/pools',
  };

  const ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';

  /* ---------- State ---------- */
  let apyChart = null;
  let chainPieChart = null;
  let currentSortCol = 'apy';
  let currentSortDir = 'desc';
  let poolsData = [];

  /* ============================================================
     GSAP ANIMATION SYSTEM
     ============================================================ */

  function animateHeroEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.kpi-bar__brand > *, .kpi-bar__strip', { opacity: 1, scale: 1 });
      return;
    }

    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

    tl.from('.kpi-bar__label', { opacity: 0, scale: 0.95, duration: 0.5 })
      .from('.kpi-bar__title', { opacity: 0, scale: 0.95, duration: 0.6, ease: 'power4.out' }, '-=0.3')
      .from('.kpi-bar__subtitle', { opacity: 0, scale: 0.95, duration: 0.4 }, '-=0.3')
      .from('.kpi-bar__strip', { opacity: 0, scale: 0.95, duration: 0.6 }, '-=0.2');
  }

  function animateCardEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.section-block', { opacity: 1, scale: 1 });
      return;
    }

    const blocks = gsap.utils.toArray('.section-block');
    blocks.forEach((block, i) => {
      gsap.to(block, {
        opacity: 1,
        scale: 1,
        duration: 0.7,
        delay: i * 0.12,
        ease: 'power3.out',
        scrollTrigger: {
          trigger: block,
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
    const block = cardElement.closest('.section-block') || cardElement;
    block.classList.add('data-pulse');
    setTimeout(() => block.classList.remove('data-pulse'), 600);
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
    if (value >= 1e12) return '$' + (value / 1e12).toFixed(2) + 'T';
    if (value >= 1e9) return '$' + (value / 1e9).toFixed(2) + 'B';
    if (value >= 1e6) return '$' + (value / 1e6).toFixed(2) + 'M';
    if (value >= 1e3) return '$' + (value / 1e3).toFixed(1) + 'K';
    return '$' + value.toFixed(2);
  }

  function formatPercent(value) {
    if (value == null) return '--';
    return value.toFixed(2) + '%';
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
    if (type === 'table') {
      let rows = '';
      for (let i = 0; i < 8; i++) {
        rows += `<tr>
          <td><div class="skeleton skeleton--text" style="width:80px"></div></td>
          <td><div class="skeleton skeleton--text" style="width:60px"></div></td>
          <td><div class="skeleton skeleton--text" style="width:50px"></div></td>
          <td><div class="skeleton skeleton--text" style="width:70px"></div></td>
          <td><div class="skeleton skeleton--text" style="width:50px"></div></td>
        </tr>`;
      }
      container.innerHTML = `<table class="yield-table"><tbody>${rows}</tbody></table>`;
    } else if (type === 'chart') {
      container.innerHTML = '<div class="skeleton skeleton--chart"></div>';
    } else if (type === 'risk') {
      let html = '';
      for (let i = 0; i < 5; i++) {
        html += `<div class="risk-card">
          <div class="risk-card__info">
            <div class="skeleton skeleton--text" style="width:100px"></div>
            <div class="skeleton skeleton--text" style="width:60px;margin-top:4px"></div>
          </div>
          <div class="skeleton" style="width:60px;height:24px;border-radius:4px"></div>
        </div>`;
      }
      container.innerHTML = html;
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
     DATA FETCHING & FILTERING
     ============================================================ */

  function getRelevantSymbols() {
    const symbols = new Set();
    CONFIG.trackedTokens.forEach((token) => {
      const mapped = TOKEN_SYMBOLS[token];
      if (mapped) mapped.forEach((s) => symbols.add(s.toUpperCase()));
    });
    return symbols;
  }

  async function fetchYieldData() {
    /* Show skeletons */
    showSkeleton('yield-table', 'table');
    showSkeleton('apy-chart-container', 'chart');
    showSkeleton('risk-cards', 'risk');
    showSkeleton('pie-container', 'chart');

    try {
      const data = await fetchWithRetry(API.yields());
      if (!data || !data.data || data.data.length === 0) {
        throw new Error('No yield data available');
      }

      const relevantSymbols = getRelevantSymbols();

      /* Filter pools that contain any of the tracked token symbols */
      let filtered = data.data.filter((pool) => {
        if (!pool.symbol || !pool.apy || pool.apy <= 0) return false;
        if (pool.tvlUsd < 100000) return false; /* Min $100K TVL */

        const poolSymbols = pool.symbol.toUpperCase().split('-');
        return poolSymbols.some((s) => relevantSymbols.has(s));
      });

      /* Sort by APY descending, take top pools */
      filtered.sort((a, b) => b.apy - a.apy);
      filtered = filtered.slice(0, CONFIG.maxPools);

      poolsData = filtered;

      /* Render all sections */
      renderYieldTable(filtered);
      renderApyChart(filtered.slice(0, 10));
      renderRiskCards(filtered);
      renderChainPie(filtered);
      updateHeroMetrics(filtered);

    } catch (err) {
      showError('yield-table', 'Failed to load yield data', fetchYieldData);
      showError('apy-chart-container', 'Failed to load chart', fetchYieldData);
      showError('risk-cards', 'Failed to load risk data', fetchYieldData);
      showError('pie-container', 'Failed to load chain data', fetchYieldData);
    }
  }

  /* ============================================================
     HERO METRICS
     ============================================================ */

  function updateHeroMetrics(pools) {
    const heroTopApy = document.getElementById('hero-top-apy');
    const heroPools = document.getElementById('hero-pools');
    const heroProtocols = document.getElementById('hero-protocols');

    const topApy = pools.length > 0 ? pools[0].apy : 0;
    const uniqueProtocols = new Set(pools.map((p) => p.project)).size;

    if (heroTopApy) animateCounter(heroTopApy, topApy, '', '%', 2);
    if (heroPools) animateCounter(heroPools, pools.length, '', '', 0);
    if (heroProtocols) animateCounter(heroProtocols, uniqueProtocols, '', '', 0);
  }

  /* ============================================================
     YIELD TABLE (SORTABLE)
     ============================================================ */

  function renderYieldTable(pools) {
    const container = document.getElementById('yield-table');
    if (!container) return;

    const sortedPools = sortPools(pools, currentSortCol, currentSortDir);

    let html = `
      <table class="yield-table">
        <thead>
          <tr>
            <th data-sort="project" class="${currentSortCol === 'project' ? 'sorted-' + currentSortDir : ''}">Protocol</th>
            <th data-sort="symbol" class="${currentSortCol === 'symbol' ? 'sorted-' + currentSortDir : ''}">Pool</th>
            <th data-sort="apy" class="${currentSortCol === 'apy' ? 'sorted-' + currentSortDir : ''}">APY</th>
            <th data-sort="tvlUsd" class="${currentSortCol === 'tvlUsd' ? 'sorted-' + currentSortDir : ''}">TVL</th>
            <th data-sort="chain" class="${currentSortCol === 'chain' ? 'sorted-' + currentSortDir : ''}">Chain</th>
          </tr>
        </thead>
        <tbody>`;

    sortedPools.forEach((pool) => {
      html += `
          <tr>
            <td>${pool.project || 'Unknown'}</td>
            <td>${pool.symbol || '--'}</td>
            <td class="yield-table__apy">${formatPercent(pool.apy)}</td>
            <td>${formatUSD(pool.tvlUsd)}</td>
            <td><span class="yield-table__chain">${pool.chain || '--'}</span></td>
          </tr>`;
    });

    html += '</tbody></table>';
    container.innerHTML = html;

    /* Attach sort handlers */
    const headers = container.querySelectorAll('th[data-sort]');
    headers.forEach((th) => {
      th.addEventListener('click', () => {
        const col = th.dataset.sort;
        if (currentSortCol === col) {
          currentSortDir = currentSortDir === 'asc' ? 'desc' : 'asc';
        } else {
          currentSortCol = col;
          currentSortDir = col === 'apy' || col === 'tvlUsd' ? 'desc' : 'asc';
        }
        renderYieldTable(poolsData);
      });
    });

    pulseCard(container.closest('.section-block'));
  }

  function sortPools(pools, col, dir) {
    return [...pools].sort((a, b) => {
      let va = a[col];
      let vb = b[col];

      if (typeof va === 'string') va = va.toLowerCase();
      if (typeof vb === 'string') vb = vb.toLowerCase();

      if (va < vb) return dir === 'asc' ? -1 : 1;
      if (va > vb) return dir === 'asc' ? 1 : -1;
      return 0;
    });
  }

  /* ============================================================
     APY BAR CHART
     ============================================================ */

  function renderApyChart(topPools) {
    const container = document.getElementById('apy-chart-container');
    if (!container) return;

    container.innerHTML = '<canvas id="apy-chart" aria-label="APY distribution bar chart" role="img"></canvas>';
    const canvas = document.getElementById('apy-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    const accentColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-accent').trim() || '#39ff14';
    const textColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-text-muted').trim() || 'rgba(255,255,255,0.3)';
    const borderColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-border').trim() || 'rgba(255,255,255,0.06)';

    const labels = topPools.map((p) => p.project + ' (' + p.symbol + ')');
    const apyValues = topPools.map((p) => p.apy);

    /* Generate gradient colors based on APY value */
    const maxApy = Math.max(...apyValues);
    const colors = apyValues.map((apy) => {
      const intensity = Math.min(apy / maxApy, 1);
      return `rgba(57, 255, 20, ${0.3 + intensity * 0.7})`;
    });

    if (apyChart) apyChart.destroy();

    apyChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'APY %',
          data: apyValues,
          backgroundColor: colors,
          borderColor: accentColor,
          borderWidth: 1,
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(0,0,0,0.85)',
            titleFont: { family: "'Satoshi', sans-serif", size: 12 },
            bodyFont: { family: "'JetBrains Mono', monospace", size: 11 },
            padding: 12,
            cornerRadius: 6,
            callbacks: {
              label: (ctx) => `APY: ${ctx.parsed.x.toFixed(2)}%`,
            },
          },
        },
        scales: {
          x: {
            grid: { color: borderColor, drawBorder: false },
            ticks: {
              color: textColor,
              font: { family: "'JetBrains Mono', monospace", size: 10 },
              callback: (val) => val.toFixed(0) + '%',
            },
          },
          y: {
            grid: { display: false },
            ticks: {
              color: textColor,
              font: { family: "'Satoshi', sans-serif", size: 10 },
              maxRotation: 0,
            },
          },
        },
        animation: prefersReducedMotion ? false : {
          duration: 1000,
          easing: 'easeOutQuart',
        },
      },
    });

    pulseCard(container.closest('.section-block'));
  }

  /* ============================================================
     RISK CARDS
     ============================================================ */

  function renderRiskCards(pools) {
    const container = document.getElementById('risk-cards');
    if (!container) return;

    /* Group by protocol and sum TVL */
    const protocolMap = {};
    pools.forEach((pool) => {
      const key = pool.project || 'Unknown';
      if (!protocolMap[key]) {
        protocolMap[key] = { name: key, tvl: 0, poolCount: 0 };
      }
      protocolMap[key].tvl += pool.tvlUsd || 0;
      protocolMap[key].poolCount++;
    });

    /* Sort by TVL descending, take top 5 */
    const protocols = Object.values(protocolMap)
      .sort((a, b) => b.tvl - a.tvl)
      .slice(0, 5);

    let html = '';
    protocols.forEach((protocol) => {
      /* Risk rating based on TVL */
      let ratingClass, ratingLabel;
      if (protocol.tvl >= 1e9) {
        ratingClass = 'risk-card__rating--low';
        ratingLabel = 'Low Risk';
      } else if (protocol.tvl >= 1e8) {
        ratingClass = 'risk-card__rating--medium';
        ratingLabel = 'Medium';
      } else {
        ratingClass = 'risk-card__rating--high';
        ratingLabel = 'Higher Risk';
      }

      html += `
        <div class="risk-card">
          <div class="risk-card__info">
            <div class="risk-card__name">${protocol.name}</div>
            <div class="risk-card__tvl">TVL: ${formatUSD(protocol.tvl)} · ${protocol.poolCount} pools</div>
          </div>
          <div class="risk-card__rating ${ratingClass}">${ratingLabel}</div>
        </div>`;
    });

    container.innerHTML = html;

    /* Stagger risk cards */
    if (!prefersReducedMotion) {
      const items = container.querySelectorAll('.risk-card');
      gsap.from(items, {
        opacity: 0,
        x: -20,
        duration: 0.5,
        stagger: 0.08,
        ease: 'power2.out',
      });
    }

    pulseCard(container.closest('.section-block'));
  }

  /* ============================================================
     CHAIN DISTRIBUTION PIE
     ============================================================ */

  function renderChainPie(pools) {
    const container = document.getElementById('pie-container');
    if (!container) return;

    container.innerHTML = '<canvas id="chain-pie" aria-label="Chain distribution pie chart" role="img"></canvas>';
    const canvas = document.getElementById('chain-pie');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    /* Count pools per chain */
    const chainCounts = {};
    pools.forEach((pool) => {
      const chain = pool.chain || 'Unknown';
      chainCounts[chain] = (chainCounts[chain] || 0) + 1;
    });

    /* Sort and take top 6, group rest as "Other" */
    const sorted = Object.entries(chainCounts).sort((a, b) => b[1] - a[1]);
    const top6 = sorted.slice(0, 6);
    const otherCount = sorted.slice(6).reduce((sum, [, count]) => sum + count, 0);
    if (otherCount > 0) top6.push(['Other', otherCount]);

    const labels = top6.map(([chain]) => chain);
    const values = top6.map(([, count]) => count);

    const chartColors = [
      getComputedStyle(document.documentElement).getPropertyValue('--chart-1').trim() || '#39ff14',
      getComputedStyle(document.documentElement).getPropertyValue('--chart-2').trim() || '#00e5ff',
      getComputedStyle(document.documentElement).getPropertyValue('--chart-3').trim() || '#bf00ff',
      getComputedStyle(document.documentElement).getPropertyValue('--chart-4').trim() || '#ff006e',
      getComputedStyle(document.documentElement).getPropertyValue('--chart-5').trim() || '#ffbe0b',
      getComputedStyle(document.documentElement).getPropertyValue('--chart-6').trim() || '#8338ec',
      'rgba(255,255,255,0.2)',
    ];

    const textColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-text-muted').trim() || 'rgba(255,255,255,0.3)';

    if (chainPieChart) chainPieChart.destroy();

    chainPieChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: chartColors.slice(0, labels.length),
          borderColor: 'transparent',
          borderWidth: 2,
          hoverOffset: 8,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        cutout: '55%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: textColor,
              font: { family: "'Satoshi', sans-serif", size: 11 },
              padding: 12,
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
              label: (ctx) => `${ctx.label}: ${ctx.parsed} pools`,
            },
          },
        },
        animation: prefersReducedMotion ? false : {
          duration: 1000,
          easing: 'easeOutQuart',
        },
      },
    });

    pulseCard(container.closest('.section-block'));
  }

  /* ============================================================
     THEME TOGGLE
     ============================================================ */

  function initThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;

    const saved = localStorage.getItem('defi-yield-theme');
    if (saved === 'light') document.documentElement.setAttribute('data-theme', 'light');

    btn.addEventListener('click', () => {
      const isLight = document.documentElement.getAttribute('data-theme') === 'light';
      if (isLight) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('defi-yield-theme', 'dark');
      } else {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('defi-yield-theme', 'light');
      }

      /* Re-render charts with new theme colors */
      if (poolsData.length > 0) {
        setTimeout(() => {
          renderApyChart(poolsData.slice(0, 10));
          renderChainPie(poolsData);
        }, 100);
      }
    });
  }

  /* ============================================================
     HERO IMAGE
     ============================================================ */

  function initHeroImage() {
    /* KPI bar layout — no hero background image */
  }

  /* ============================================================
     INIT
     ============================================================ */

  function init() {
    startClock();
    initThemeToggle();
    initHeroImage();
    animateHeroEntrance();

    /* Load data */
    fetchYieldData();

    /* Animate cards after data loads */
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
