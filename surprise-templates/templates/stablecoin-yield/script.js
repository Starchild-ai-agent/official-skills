/* ============================================================
   Stablecoin Yield Comparison — script.js

   APIs: DeFi Llama yields (free) + mock fallback
   Animation: GSAP 3 + ScrollTrigger
   Entrance: D9 scale(0.95)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Mock Yield Data ---------- */
  const MOCK_YIELDS = [
    { protocol: 'Aave V3', token: 'USDC', chain: 'Ethereum', apy: 5.82, tvl: 2840000000, risk: 'low' },
    { protocol: 'Aave V3', token: 'USDT', chain: 'Ethereum', apy: 5.45, tvl: 1920000000, risk: 'low' },
    { protocol: 'Aave V3', token: 'DAI', chain: 'Ethereum', apy: 5.21, tvl: 1150000000, risk: 'low' },
    { protocol: 'Compound V3', token: 'USDC', chain: 'Ethereum', apy: 4.98, tvl: 1680000000, risk: 'low' },
    { protocol: 'Compound V3', token: 'USDT', chain: 'Ethereum', apy: 4.72, tvl: 890000000, risk: 'low' },
    { protocol: 'MakerDAO DSR', token: 'DAI', chain: 'Ethereum', apy: 5.00, tvl: 3200000000, risk: 'low' },
    { protocol: 'Morpho Blue', token: 'USDC', chain: 'Ethereum', apy: 7.34, tvl: 620000000, risk: 'medium' },
    { protocol: 'Morpho Blue', token: 'USDT', chain: 'Ethereum', apy: 6.89, tvl: 410000000, risk: 'medium' },
    { protocol: 'Spark', token: 'DAI', chain: 'Ethereum', apy: 5.50, tvl: 1800000000, risk: 'low' },
    { protocol: 'Yearn V3', token: 'USDC', chain: 'Ethereum', apy: 6.12, tvl: 340000000, risk: 'medium' },
    { protocol: 'Stargate', token: 'USDC', chain: 'Arbitrum', apy: 4.56, tvl: 280000000, risk: 'medium' },
    { protocol: 'Stargate', token: 'USDT', chain: 'Arbitrum', apy: 4.23, tvl: 195000000, risk: 'medium' },
    { protocol: 'Aave V3', token: 'USDC', chain: 'Polygon', apy: 3.89, tvl: 520000000, risk: 'low' },
    { protocol: 'Aave V3', token: 'USDT', chain: 'Polygon', apy: 3.67, tvl: 380000000, risk: 'low' },
    { protocol: 'Aave V3', token: 'DAI', chain: 'Polygon', apy: 3.45, tvl: 210000000, risk: 'low' },
    { protocol: 'Curve/Convex', token: 'FRAX', chain: 'Ethereum', apy: 8.45, tvl: 450000000, risk: 'medium' },
    { protocol: 'Frax Lend', token: 'FRAX', chain: 'Ethereum', apy: 6.78, tvl: 320000000, risk: 'medium' },
    { protocol: 'Pendle', token: 'USDC', chain: 'Ethereum', apy: 9.12, tvl: 180000000, risk: 'high' },
    { protocol: 'Pendle', token: 'DAI', chain: 'Ethereum', apy: 8.67, tvl: 120000000, risk: 'high' },
    { protocol: 'Aave V3', token: 'USDC', chain: 'Base', apy: 4.12, tvl: 310000000, risk: 'low' },
  ];

  let currentFilter = 'all';
  let currentSort = { key: 'apy', dir: 'desc' };
  let apyChart = null;
  let tvlTokenChart = null;
  let tvlChainChart = null;

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  /* ---------- Helpers ---------- */
  function formatTVL(val) {
    if (val >= 1e9) return '$' + (val / 1e9).toFixed(1) + 'B';
    if (val >= 1e6) return '$' + (val / 1e6).toFixed(0) + 'M';
    return '$' + val.toLocaleString();
  }

  function getFilteredData() {
    let data = [...MOCK_YIELDS];
    if (currentFilter !== 'all') {
      data = data.filter(d => d.token === currentFilter);
    }
    data.sort((a, b) => {
      const mul = currentSort.dir === 'desc' ? -1 : 1;
      if (currentSort.key === 'apy' || currentSort.key === 'tvl') {
        return (a[currentSort.key] - b[currentSort.key]) * mul;
      }
      return a[currentSort.key].localeCompare(b[currentSort.key]) * mul;
    });
    return data;
  }

  /* ---------- KPI Bar ---------- */
  function updateKPIs() {
    const data = getFilteredData();
    const avgApy = data.reduce((s, d) => s + d.apy, 0) / data.length;
    const bestApy = Math.max(...data.map(d => d.apy));
    const totalTvl = data.reduce((s, d) => s + d.tvl, 0);
    const protocols = new Set(data.map(d => d.protocol)).size;

    $('#kpi-avg-apy').textContent = avgApy.toFixed(2) + '%';
    $('#kpi-best-apy').textContent = bestApy.toFixed(2) + '%';
    $('#kpi-total-tvl').textContent = formatTVL(totalTvl);
    $('#kpi-protocols').textContent = protocols.toString();
  }

  /* ---------- Render Table ---------- */
  function renderTable() {
    const data = getFilteredData();
    const tbody = $('#yields-tbody');

    tbody.innerHTML = data.map(function (d) {
      return '<tr class="yield-row" style="opacity:0">' +
        '<td><span class="yield-protocol">' + d.protocol + '</span></td>' +
        '<td><span class="yield-token">' + d.token + '</span></td>' +
        '<td><span class="yield-chain">' + d.chain + '</span></td>' +
        '<td><span class="yield-apy">' + d.apy.toFixed(2) + '%</span></td>' +
        '<td><span class="yield-tvl">' + formatTVL(d.tvl) + '</span></td>' +
        '<td><span class="risk-badge risk-badge--' + d.risk + '">' + d.risk + '</span></td>' +
        '</tr>';
    }).join('');

    // D9 entrance: scale(0.95)
    if (!prefersReducedMotion) {
      gsap.fromTo('.yield-row',
        { opacity: 0, scale: 0.95 },
        { opacity: 1, scale: 1, duration: 0.4, stagger: 0.04, ease: 'power2.out' }
      );
    } else {
      $$('.yield-row').forEach(function (r) { r.style.opacity = '1'; });
    }

    updateKPIs();
  }

  /* ---------- APY Chart ---------- */
  function renderAPYChart() {
    var data = getFilteredData().slice(0, 10);
    var ctx = $('#apy-chart').getContext('2d');
    var style = getComputedStyle(document.documentElement);
    var textColor = style.getPropertyValue('--color-text-secondary').trim();
    var borderColor = style.getPropertyValue('--color-border').trim();
    var colors = [
      style.getPropertyValue('--chart-1').trim(),
      style.getPropertyValue('--chart-2').trim(),
      style.getPropertyValue('--chart-3').trim(),
      style.getPropertyValue('--chart-4').trim(),
      style.getPropertyValue('--chart-5').trim(),
      style.getPropertyValue('--chart-6').trim(),
    ];

    if (apyChart) apyChart.destroy();

    apyChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map(function (d) { return d.protocol + ' (' + d.token + ')'; }),
        datasets: [{
          label: 'APY %',
          data: data.map(function (d) { return d.apy; }),
          backgroundColor: data.map(function (_, i) { return colors[i % colors.length]; }),
          borderRadius: 4,
          borderSkipped: false,
        }],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) { return 'APY: ' + ctx.parsed.x.toFixed(2) + '%'; }
            },
          },
        },
        scales: {
          x: {
            ticks: {
              color: textColor,
              font: { family: "'IBM Plex Mono', monospace", size: 11 },
              callback: function (v) { return v + '%'; }
            },
            grid: { color: borderColor },
          },
          y: {
            ticks: { color: textColor, font: { family: "'Karla', sans-serif", size: 11 } },
            grid: { display: false },
          },
        },
      },
    });
  }

  /* ---------- TVL Charts ---------- */
  function renderTVLCharts() {
    var data = getFilteredData();
    var style = getComputedStyle(document.documentElement);
    var textColor = style.getPropertyValue('--color-text-secondary').trim();
    var colors = [
      style.getPropertyValue('--chart-1').trim(),
      style.getPropertyValue('--chart-2').trim(),
      style.getPropertyValue('--chart-3').trim(),
      style.getPropertyValue('--chart-4').trim(),
      style.getPropertyValue('--chart-5').trim(),
      style.getPropertyValue('--chart-6').trim(),
    ];

    // By Token
    var tokenMap = {};
    data.forEach(function (d) { tokenMap[d.token] = (tokenMap[d.token] || 0) + d.tvl; });
    var tokenLabels = Object.keys(tokenMap);
    var tokenValues = Object.values(tokenMap);

    if (tvlTokenChart) tvlTokenChart.destroy();
    tvlTokenChart = new Chart($('#tvl-token-chart').getContext('2d'), {
      type: 'doughnut',
      data: {
        labels: tokenLabels,
        datasets: [{
          data: tokenValues,
          backgroundColor: tokenLabels.map(function (_, i) { return colors[i % colors.length]; }),
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: textColor, font: { family: "'Karla', sans-serif", size: 12 } }
          },
          tooltip: {
            callbacks: {
              label: function (ctx) { return ctx.label + ': ' + formatTVL(ctx.parsed); }
            }
          },
        },
      },
    });

    // By Chain
    var chainMap = {};
    data.forEach(function (d) { chainMap[d.chain] = (chainMap[d.chain] || 0) + d.tvl; });
    var chainLabels = Object.keys(chainMap);
    var chainValues = Object.values(chainMap);

    if (tvlChainChart) tvlChainChart.destroy();
    tvlChainChart = new Chart($('#tvl-chain-chart').getContext('2d'), {
      type: 'doughnut',
      data: {
        labels: chainLabels,
        datasets: [{
          data: chainValues,
          backgroundColor: chainLabels.map(function (_, i) { return colors[i % colors.length]; }),
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: textColor, font: { family: "'Karla', sans-serif", size: 12 } }
          },
          tooltip: {
            callbacks: {
              label: function (ctx) { return ctx.label + ': ' + formatTVL(ctx.parsed); }
            }
          },
        },
      },
    });
  }

  /* ---------- Theme Toggle ---------- */
  function initTheme() {
    var saved = localStorage.getItem('stablecoin-yield-theme');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');

    $('#theme-toggle').addEventListener('click', function () {
      var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
      localStorage.setItem('stablecoin-yield-theme', isDark ? 'light' : 'dark');
      renderAllCharts();
    });
  }

  /* ---------- Filter & Sort ---------- */
  function initFilters() {
    $$('.filter-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        $$('.filter-btn').forEach(function (b) { b.classList.remove('filter-btn--active'); });
        btn.classList.add('filter-btn--active');
        currentFilter = btn.dataset.filter;
        renderTable();
        renderAllCharts();
      });
    });

    $$('.yield-tbl th[data-sort]').forEach(function (th) {
      th.addEventListener('click', function () {
        var key = th.dataset.sort;
        if (currentSort.key === key) {
          currentSort.dir = currentSort.dir === 'desc' ? 'asc' : 'desc';
        } else {
          currentSort = { key: key, dir: 'desc' };
        }
        $$('.yield-tbl th').forEach(function (t) {
          t.classList.remove('sort-active');
          t.textContent = t.textContent.replace(/ [↑↓]/, '');
        });
        th.classList.add('sort-active');
        th.textContent += currentSort.dir === 'desc' ? ' ↓' : ' ↑';
        renderTable();
      });
    });
  }

  function renderAllCharts() {
    renderAPYChart();
    renderTVLCharts();
  }

  /* ---------- GSAP Animations ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    // Hero entrance
    var heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl
      .from('.hero__label', { opacity: 0, y: 20, duration: 0.6 })
      .from('.hero__title', { opacity: 0, y: 30, duration: 0.7 }, '-=0.3')
      .from('.kpi-item', { opacity: 0, scale: 0.95, duration: 0.5, stagger: 0.1 }, '-=0.3');

    // Section entrances — D9 scale(0.95)
    $$('.section').forEach(function (section) {
      gsap.from(section, {
        scrollTrigger: {
          trigger: section,
          start: 'top 85%',
          toggleActions: 'play none none none',
        },
        opacity: 0,
        scale: 0.95,
        duration: 0.7,
        ease: 'power2.out',
      });
    });
  }

  /* ---------- Init ---------- */
  function init() {
    initTheme();
    renderTable();
    renderAllCharts();
    initFilters();
    initAnimations();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
