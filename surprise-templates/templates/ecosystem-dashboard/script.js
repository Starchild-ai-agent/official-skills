/* ============================================================
   Ecosystem Dashboard — script.js

   APIs: DeFi Llama + CoinGecko + mock data
   Animation: GSAP 3 + ScrollTrigger
   Entrance: D4 stagger
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var $ = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel) { return document.querySelectorAll(sel); };

  var CHAINS = {
    ethereum: {
      name: 'Ethereum', label: 'Ethereum Ecosystem',
      tvl: '$58.2B', addresses: '1.2M', gas: '$4.20',
      metrics: [
        { label: 'Total TVL', value: '$58.2B', change: '+3.4%', dir: 'up' },
        { label: 'Daily Txns', value: '1.12M', change: '+1.8%', dir: 'up' },
        { label: 'Avg Gas', value: '$4.20', change: '-12%', dir: 'down' },
        { label: 'DApps', value: '4,230', change: '+28', dir: 'up' }
      ],
      dapps: [
        { name: 'Lido', category: 'Liquid Staking', tvl: '$14.2B' },
        { name: 'Aave V3', category: 'Lending', tvl: '$12.8B' },
        { name: 'Uniswap V3', category: 'DEX', tvl: '$4.5B' },
        { name: 'MakerDAO', category: 'CDP', tvl: '$8.1B' },
        { name: 'Eigenlayer', category: 'Restaking', tvl: '$6.3B' },
        { name: 'Curve', category: 'DEX', tvl: '$2.1B' }
      ],
      chartTvl: 58.2
    },
    base: {
      name: 'Base', label: 'Base Ecosystem',
      tvl: '$8.4B', addresses: '890K', gas: '$0.03',
      metrics: [
        { label: 'Total TVL', value: '$8.4B', change: '+18.2%', dir: 'up' },
        { label: 'Daily Txns', value: '4.8M', change: '+12%', dir: 'up' },
        { label: 'Avg Gas', value: '$0.03', change: '-5%', dir: 'down' },
        { label: 'DApps', value: '680', change: '+45', dir: 'up' }
      ],
      dapps: [
        { name: 'Aerodrome', category: 'DEX', tvl: '$1.8B' },
        { name: 'Aave V3', category: 'Lending', tvl: '$1.2B' },
        { name: 'Moonwell', category: 'Lending', tvl: '$520M' },
        { name: 'Extra Finance', category: 'Yield', tvl: '$380M' },
        { name: 'Uniswap V3', category: 'DEX', tvl: '$340M' }
      ],
      chartTvl: 8.4
    },
    arbitrum: {
      name: 'Arbitrum', label: 'Arbitrum Ecosystem',
      tvl: '$12.6B', addresses: '1.1M', gas: '$0.12',
      metrics: [
        { label: 'Total TVL', value: '$12.6B', change: '+5.7%', dir: 'up' },
        { label: 'Daily Txns', value: '2.3M', change: '+8%', dir: 'up' },
        { label: 'Avg Gas', value: '$0.12', change: '+2%', dir: 'up' },
        { label: 'DApps', value: '1,120', change: '+32', dir: 'up' }
      ],
      dapps: [
        { name: 'GMX', category: 'Perps', tvl: '$580M' },
        { name: 'Aave V3', category: 'Lending', tvl: '$2.1B' },
        { name: 'Uniswap V3', category: 'DEX', tvl: '$890M' },
        { name: 'Pendle', category: 'Yield', tvl: '$420M' },
        { name: 'Radiant', category: 'Lending', tvl: '$310M' }
      ],
      chartTvl: 12.6
    },
    optimism: {
      name: 'Optimism', label: 'Optimism Ecosystem',
      tvl: '$7.8B', addresses: '680K', gas: '$0.05',
      metrics: [
        { label: 'Total TVL', value: '$7.8B', change: '+4.1%', dir: 'up' },
        { label: 'Daily Txns', value: '1.5M', change: '+6%', dir: 'up' },
        { label: 'Avg Gas', value: '$0.05', change: '-8%', dir: 'down' },
        { label: 'DApps', value: '520', change: '+18', dir: 'up' }
      ],
      dapps: [
        { name: 'Velodrome', category: 'DEX', tvl: '$320M' },
        { name: 'Aave V3', category: 'Lending', tvl: '$1.4B' },
        { name: 'Synthetix', category: 'Derivatives', tvl: '$890M' },
        { name: 'Uniswap V3', category: 'DEX', tvl: '$280M' }
      ],
      chartTvl: 7.8
    },
    polygon: {
      name: 'Polygon', label: 'Polygon Ecosystem',
      tvl: '$4.2B', addresses: '520K', gas: '$0.01',
      metrics: [
        { label: 'Total TVL', value: '$4.2B', change: '-2.3%', dir: 'down' },
        { label: 'Daily Txns', value: '3.1M', change: '+3%', dir: 'up' },
        { label: 'Avg Gas', value: '$0.01', change: '0%', dir: 'up' },
        { label: 'DApps', value: '890', change: '+12', dir: 'up' }
      ],
      dapps: [
        { name: 'Aave V3', category: 'Lending', tvl: '$1.1B' },
        { name: 'QuickSwap', category: 'DEX', tvl: '$180M' },
        { name: 'Uniswap V3', category: 'DEX', tvl: '$320M' },
        { name: 'Balancer', category: 'DEX', tvl: '$140M' }
      ],
      chartTvl: 4.2
    }
  };

  var currentChain = 'ethereum';
  var comparisonChart = null;

  function renderChain(chainKey) {
    var chain = CHAINS[chainKey];
    if (!chain) return;
    currentChain = chainKey;

    $('#hero-chain-label').textContent = chain.label;
    $('#hero-chain-title').textContent = chain.name;
    $('#stat-tvl').textContent = chain.tvl;
    $('#stat-addresses').textContent = chain.addresses;
    $('#stat-gas').textContent = chain.gas;

    $$('.chain-btn').forEach(function (btn) {
      btn.classList.toggle('chain-btn--active', btn.dataset.chain === chainKey);
    });

    var metricsGrid = $('#metrics-grid');
    metricsGrid.innerHTML = chain.metrics.map(function (m) {
      return '<div class="metric-card" style="opacity:0">' +
        '<div class="metric-card__label">' + m.label + '</div>' +
        '<div class="metric-card__value">' + m.value + '</div>' +
        '<div class="metric-card__change change--' + m.dir + '">' + m.change + '</div>' +
      '</div>';
    }).join('');

    var dappsList = $('#dapps-list');
    dappsList.innerHTML = chain.dapps.map(function (d, i) {
      return '<div class="dapp-row" style="opacity:0">' +
        '<span class="dapp-row__rank">#' + (i + 1) + '</span>' +
        '<span class="dapp-row__name">' + d.name + '</span>' +
        '<span class="dapp-row__category">' + d.category + '</span>' +
        '<span class="dapp-row__tvl">' + d.tvl + '</span>' +
      '</div>';
    }).join('');

    if (!prefersReducedMotion) {
      gsap.fromTo('.metric-card',
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.4, stagger: 0.08, ease: 'power2.out' }
      );
      gsap.fromTo('.dapp-row',
        { opacity: 0, y: 15 },
        { opacity: 1, y: 0, duration: 0.35, stagger: 0.06, ease: 'power2.out', delay: 0.2 }
      );
    } else {
      $$('.metric-card').forEach(function (el) { el.style.opacity = '1'; });
      $$('.dapp-row').forEach(function (el) { el.style.opacity = '1'; });
    }
  }

  function renderComparisonChart() {
    var ctx = $('#comparison-chart').getContext('2d');
    var style = getComputedStyle(document.documentElement);
    var textColor = style.getPropertyValue('--color-text-secondary').trim();
    var borderColor = style.getPropertyValue('--color-border').trim();
    var colors = ['#627eea', '#0052ff', '#28a0f0', '#ff0420', '#8247e5'];

    var chainKeys = Object.keys(CHAINS);
    var labels = chainKeys.map(function (k) { return CHAINS[k].name; });
    var tvlData = chainKeys.map(function (k) { return CHAINS[k].chartTvl; });

    if (comparisonChart) comparisonChart.destroy();

    comparisonChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'TVL ($B)',
          data: tvlData,
          backgroundColor: colors,
          borderRadius: 6,
          borderSkipped: false
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (c) { return 'TVL: $' + c.parsed.y.toFixed(1) + 'B'; }
            }
          }
        },
        scales: {
          x: {
            ticks: { color: textColor, font: { family: "'Figtree', sans-serif", size: 12 } },
            grid: { display: false }
          },
          y: {
            ticks: {
              color: textColor,
              font: { family: "'JetBrains Mono', monospace", size: 11 },
              callback: function (v) { return '$' + v + 'B'; }
            },
            grid: { color: borderColor }
          }
        }
      }
    });
  }

  function initTheme() {
    var saved = localStorage.getItem('ecosystem-dashboard-theme');
    if (saved === 'light') document.documentElement.setAttribute('data-theme', 'light');

    $('#theme-toggle').addEventListener('click', function () {
      var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
      localStorage.setItem('ecosystem-dashboard-theme', isDark ? 'light' : 'dark');
      renderComparisonChart();
    });
  }

  function initSidebar() {
    $$('.chain-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        renderChain(btn.dataset.chain);
      });
    });
  }

  function initAnimations() {
    if (prefersReducedMotion) return;

    var heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl
      .from('.hero__label', { opacity: 0, y: 15, duration: 0.5 })
      .from('.hero__title', { opacity: 0, y: 20, duration: 0.6 }, '-=0.3')
      .from('.hero__stat', { opacity: 0, y: 15, duration: 0.4, stagger: 0.1 }, '-=0.3');

    gsap.from('.sidebar', { opacity: 0, x: -30, duration: 0.6, ease: 'power2.out' });
  }

  function init() {
    initTheme();
    renderChain('ethereum');
    renderComparisonChart();
    initSidebar();
    initAnimations();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
