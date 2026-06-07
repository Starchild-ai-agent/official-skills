/* ============================================================
   Competitor Token Analysis — script.js

   APIs: CoinGecko (free, no key)
   Animation: GSAP 3 + ScrollTrigger
   Entrance: D8 translateX(40px)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var $ = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel) { return document.querySelectorAll(sel); };

  var MOCK_DATA = {
    ethereum: {
      name: 'Ethereum', symbol: 'ETH', price: 3842, mcap: '$462B',
      tvl: '$58.2B', holders: '120M+', devActivity: 'Very High',
      change24h: '+2.4%', change7d: '+5.1%',
      sparkline: [3650, 3680, 3720, 3690, 3750, 3800, 3842],
      strengths: ['Largest DeFi ecosystem', 'Most battle-tested smart contracts', 'Strong institutional adoption', 'EIP-4844 reduced L2 costs 90%'],
      weaknesses: ['High L1 gas fees', 'Slower finality vs competitors', 'Complex validator requirements', 'MEV extraction concerns']
    },
    solana: {
      name: 'Solana', symbol: 'SOL', price: 178, mcap: '$82B',
      tvl: '$8.1B', holders: '25M+', devActivity: 'High',
      change24h: '+3.8%', change7d: '+12.3%',
      sparkline: [155, 158, 162, 168, 170, 175, 178],
      strengths: ['Sub-second finality', 'Very low transaction fees', 'Strong DePIN ecosystem', 'Firedancer client diversity'],
      weaknesses: ['Network outage history', 'Validator hardware requirements', 'Smaller DeFi TVL', 'Token concentration concerns']
    },
    'avalanche-2': {
      name: 'Avalanche', symbol: 'AVAX', price: 42, mcap: '$17B',
      tvl: '$2.8B', holders: '8M+', devActivity: 'Medium',
      change24h: '+1.2%', change7d: '+3.5%',
      sparkline: [39, 39.5, 40, 40.5, 41, 41.5, 42],
      strengths: ['Subnet architecture', 'Fast finality (< 1s)', 'Enterprise partnerships', 'Custom VM support'],
      weaknesses: ['Lower developer mindshare', 'Smaller ecosystem', 'Complex subnet setup', 'Token unlock pressure']
    },
    cardano: {
      name: 'Cardano', symbol: 'ADA', price: 0.72, mcap: '$25B',
      tvl: '$420M', holders: '4.5M+', devActivity: 'Medium',
      change24h: '-0.8%', change7d: '+1.2%',
      sparkline: [0.70, 0.71, 0.72, 0.71, 0.70, 0.71, 0.72],
      strengths: ['Peer-reviewed research', 'Low energy consumption', 'Strong community governance', 'Hydra scaling solution'],
      weaknesses: ['Slow development pace', 'Limited DeFi ecosystem', 'Haskell developer scarcity', 'Lower TVL vs peers']
    },
    polkadot: {
      name: 'Polkadot', symbol: 'DOT', price: 8.50, mcap: '$12B',
      tvl: '$1.2B', holders: '3M+', devActivity: 'High',
      change24h: '+0.5%', change7d: '+2.8%',
      sparkline: [8.10, 8.20, 8.25, 8.30, 8.35, 8.40, 8.50],
      strengths: ['Parachain interoperability', 'Shared security model', 'On-chain governance', 'Substrate framework'],
      weaknesses: ['Complex parachain auctions', 'Fragmented liquidity', 'Steep learning curve', 'Parachain slot costs']
    }
  };

  var priceChart = null;

  var METRICS = [
    { key: 'price', label: 'Price', format: function (v) { return '$' + v.toLocaleString(); }, higher: true },
    { key: 'mcap', label: 'Market Cap', format: function (v) { return v; }, higher: true },
    { key: 'tvl', label: 'TVL', format: function (v) { return v; }, higher: true },
    { key: 'holders', label: 'Holders', format: function (v) { return v; }, higher: true },
    { key: 'devActivity', label: 'Dev Activity', format: function (v) { return v; }, higher: false },
    { key: 'change24h', label: '24h Change', format: function (v) { return v; }, higher: false },
    { key: 'change7d', label: '7d Change', format: function (v) { return v; }, higher: false }
  ];

  function getTokenA() { return MOCK_DATA[$('#token-a').value]; }
  function getTokenB() { return MOCK_DATA[$('#token-b').value]; }

  function renderComparison() {
    var a = getTokenA();
    var b = getTokenB();
    if (!a || !b) return;

    var grid = $('#comparison-grid');
    var html = '<div class="comp-header comp-header--a">' + a.name + ' (' + a.symbol + ')</div>' +
      '<div class="comp-header comp-header--label">Metric</div>' +
      '<div class="comp-header comp-header--b">' + b.name + ' (' + b.symbol + ')</div>';

    METRICS.forEach(function (m) {
      var valA = m.format(a[m.key]);
      var valB = m.format(b[m.key]);
      html += '<div class="comp-row">' +
        '<div class="comp-cell comp-cell--a">' + valA + '</div>' +
        '<div class="comp-cell comp-cell--label">' + m.label + '</div>' +
        '<div class="comp-cell comp-cell--b">' + valB + '</div>' +
      '</div>';
    });

    grid.innerHTML = html;

    if (!prefersReducedMotion) {
      gsap.fromTo('.comp-cell',
        { opacity: 0, x: 40 },
        { opacity: 1, x: 0, duration: 0.4, stagger: 0.03, ease: 'power2.out' }
      );
    }
  }

  function renderPriceChart() {
    var a = getTokenA();
    var b = getTokenB();
    if (!a || !b) return;

    var ctx = $('#price-chart').getContext('2d');
    var style = getComputedStyle(document.documentElement);
    var textColor = style.getPropertyValue('--color-text-secondary').trim();
    var borderColor = style.getPropertyValue('--color-border').trim();
    var colorA = style.getPropertyValue('--color-token-a').trim();
    var colorB = style.getPropertyValue('--color-token-b').trim();

    var labels = ['7d', '6d', '5d', '4d', '3d', '2d', '1d'];

    // Normalize to percentage change
    var baseA = a.sparkline[0];
    var baseB = b.sparkline[0];
    var normA = a.sparkline.map(function (v) { return ((v - baseA) / baseA * 100).toFixed(2); });
    var normB = b.sparkline.map(function (v) { return ((v - baseB) / baseB * 100).toFixed(2); });

    if (priceChart) priceChart.destroy();

    priceChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: a.symbol,
            data: normA,
            borderColor: colorA,
            backgroundColor: colorA + '20',
            fill: true,
            tension: 0.4,
            pointRadius: 4,
            pointHoverRadius: 7,
            borderWidth: 2
          },
          {
            label: b.symbol,
            data: normB,
            borderColor: colorB,
            backgroundColor: colorB + '20',
            fill: true,
            tension: 0.4,
            pointRadius: 4,
            pointHoverRadius: 7,
            borderWidth: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            position: 'top',
            labels: { color: textColor, font: { family: "'Figtree', sans-serif", size: 12 } }
          },
          tooltip: {
            callbacks: {
              label: function (c) { return c.dataset.label + ': ' + c.parsed.y + '%'; }
            }
          }
        },
        scales: {
          x: {
            ticks: { color: textColor, font: { family: "'JetBrains Mono', monospace", size: 11 } },
            grid: { display: false }
          },
          y: {
            ticks: {
              color: textColor,
              font: { family: "'JetBrains Mono', monospace", size: 11 },
              callback: function (v) { return v + '%'; }
            },
            grid: { color: borderColor }
          }
        }
      }
    });
  }

  function renderSWOT() {
    var a = getTokenA();
    var b = getTokenB();
    if (!a || !b) return;

    var grid = $('#swot-grid');
    var cards = [
      { token: a.name, type: 'strength', items: a.strengths },
      { token: a.name, type: 'weakness', items: a.weaknesses },
      { token: b.name, type: 'strength', items: b.strengths },
      { token: b.name, type: 'weakness', items: b.weaknesses }
    ];

    grid.innerHTML = cards.map(function (c) {
      var itemsHtml = c.items.map(function (item) {
        return '<li class="swot-card__item">' + item + '</li>';
      }).join('');

      return '<div class="swot-card swot-card--' + c.type + '" style="opacity:0">' +
        '<div class="swot-card__header">' +
          '<span class="swot-card__token">' + c.token + '</span>' +
          '<span class="swot-card__type swot-card__type--' + c.type + '">' +
            (c.type === 'strength' ? 'Strengths' : 'Weaknesses') +
          '</span>' +
        '</div>' +
        '<ul class="swot-card__list">' + itemsHtml + '</ul>' +
      '</div>';
    }).join('');

    if (!prefersReducedMotion) {
      gsap.fromTo('.swot-card',
        { opacity: 0, x: 40 },
        { opacity: 1, x: 0, duration: 0.5, stagger: 0.12, ease: 'power2.out',
          scrollTrigger: { trigger: '#swot-section', start: 'top 80%', toggleActions: 'play none none none' }
        }
      );
    } else {
      $$('.swot-card').forEach(function (el) { el.style.opacity = '1'; });
    }
  }

  function renderAll() {
    renderComparison();
    renderPriceChart();
    renderSWOT();
  }

  function initTheme() {
    var saved = localStorage.getItem('competitor-analysis-theme');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
    $('#theme-toggle').addEventListener('click', function () {
      var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
      localStorage.setItem('competitor-analysis-theme', isDark ? 'light' : 'dark');
      renderPriceChart();
    });
  }

  function initSelectors() {
    $('#token-a').addEventListener('change', renderAll);
    $('#token-b').addEventListener('change', renderAll);
  }

  function initAnimations() {
    if (prefersReducedMotion) return;
    var heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl
      .from('.hero__label', { opacity: 0, y: 20, duration: 0.5 })
      .from('.hero__title', { opacity: 0, x: 40, duration: 0.7 }, '-=0.3')
      .from('.hero__subtitle', { opacity: 0, x: 30, duration: 0.5 }, '-=0.3')
      .from('.hero__selector', { opacity: 0, y: 20, duration: 0.5 }, '-=0.2');

    $$('.section').forEach(function (section) {
      gsap.from(section.querySelector('.section__title'), {
        scrollTrigger: { trigger: section, start: 'top 85%', toggleActions: 'play none none none' },
        opacity: 0, x: 40, duration: 0.6, ease: 'power2.out'
      });
    });
  }

  function init() {
    initTheme();
    renderAll();
    initSelectors();
    initAnimations();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();