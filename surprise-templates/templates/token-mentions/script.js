/* ============================================================
   Token Mentions Tracker — script.js
   Mock data · GSAP 3 + ScrollTrigger · Chart.js
   ============================================================ */
(function () {
  'use strict';
  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var TOKENS = [
    { symbol: 'BTC', name: 'Bitcoin', mentions: 4820, change: '+12%', up: true },
    { symbol: 'ETH', name: 'Ethereum', mentions: 3650, change: '+8%', up: true },
    { symbol: 'SOL', name: 'Solana', mentions: 2940, change: '+22%', up: true },
    { symbol: 'ARB', name: 'Arbitrum', mentions: 1870, change: '-3%', up: false },
    { symbol: 'LINK', name: 'Chainlink', mentions: 1540, change: '+5%', up: true },
    { symbol: 'AVAX', name: 'Avalanche', mentions: 1320, change: '-7%', up: false },
    { symbol: 'MATIC', name: 'Polygon', mentions: 1180, change: '+2%', up: true },
    { symbol: 'OP', name: 'Optimism', mentions: 980, change: '+15%', up: true },
    { symbol: 'DOGE', name: 'Dogecoin', mentions: 870, change: '+45%', up: true },
    { symbol: 'DOT', name: 'Polkadot', mentions: 720, change: '-2%', up: false }
  ];

  var TREND_DATA = {
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    datasets: [
      { label: 'BTC', data: [680, 720, 650, 710, 780, 640, 640], borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.1)' },
      { label: 'ETH', data: [520, 540, 480, 560, 590, 510, 450], borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.1)' },
      { label: 'SOL', data: [320, 380, 420, 450, 480, 440, 450], borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.1)' }
    ]
  };

  var SENTIMENT = { bullish: 52, neutral: 30, bearish: 18 };

  var KOL_MENTIONS = [
    { name: 'CryptoWhale', handle: '@cryptowhale', initials: 'CW', text: 'BTC breaking out of the descending wedge. Target $100K by end of month. Accumulation zone is NOW.', time: '15m ago', token: 'BTC' },
    { name: 'DeFi Degen', handle: '@defidegen', initials: 'DD', text: 'SOL ecosystem is on fire. New DEX volumes hitting ATH. This is the chain to watch in 2025.', time: '32m ago', token: 'SOL' },
    { name: 'Alpha Hunter', handle: '@alphahunter', initials: 'AH', text: 'ETH staking yields are climbing. With EIP-4844 live, L2 costs dropped 90%. Bullish for the ecosystem.', time: '1h ago', token: 'ETH' },
    { name: 'Macro Guru', handle: '@macroguru', initials: 'MG', text: 'Fed pivot incoming. Risk assets will pump. BTC and ETH are my top picks for Q3.', time: '2h ago', token: 'BTC' },
    { name: 'NFT Collector', handle: '@nftcollector', initials: 'NC', text: 'ARB airdrop season 2 rumors getting louder. Bridging activity up 300% this week.', time: '3h ago', token: 'ARB' },
    { name: 'Chain Analyst', handle: '@chainanalyst', initials: 'CA', text: 'LINK oracle integrations hit new ATH. 1,200+ protocols now using Chainlink. Fundamentals are strong.', time: '4h ago', token: 'LINK' },
    { name: 'Yield Farmer', handle: '@yieldfarmer', initials: 'YF', text: 'OP superchain thesis playing out. Base + OP + Mode = unstoppable L2 coalition.', time: '5h ago', token: 'OP' },
    { name: 'Meme Lord', handle: '@memelord', initials: 'ML', text: 'DOGE community is back. Elon just tweeted a Shiba. You know what happens next.', time: '6h ago', token: 'DOGE' }
  ];

  var $ = function (sel) { return document.querySelector(sel); };

  /* Theme */
  function initTheme() {
    var saved = localStorage.getItem('token-mentions-theme');
    if (saved === 'light') document.documentElement.setAttribute('data-theme', 'light');
  }
  initTheme();
  $('#theme-toggle').addEventListener('click', function () {
    var isLight = document.documentElement.getAttribute('data-theme') === 'light';
    document.documentElement.setAttribute('data-theme', isLight ? '' : 'light');
    localStorage.setItem('token-mentions-theme', isLight ? 'dark' : 'light');
  });

  /* Gauges */
  function renderGauges() {
    var el = $('#hero-gauges');
    var totalMentions = TOKENS.reduce(function (s, t) { return s + t.mentions; }, 0);
    var gauges = [
      { label: 'Total Mentions', value: totalMentions.toLocaleString(), sub: 'Last 24h' },
      { label: 'Top Token', value: TOKENS[0].symbol, sub: TOKENS[0].mentions.toLocaleString() + ' mentions' },
      { label: 'Sentiment', value: SENTIMENT.bullish + '%', sub: 'Bullish' },
      { label: 'Active KOLs', value: '142', sub: 'Tracked accounts' }
    ];
    el.innerHTML = gauges.map(function (g) {
      return '<div class="gauge-card"><div class="gauge-card__label">' + g.label + '</div><div class="gauge-card__value">' + g.value + '</div><div class="gauge-card__sub">' + g.sub + '</div></div>';
    }).join('');
  }

  /* Ranking */
  function renderRanking() {
    var el = $('#ranking-list');
    el.innerHTML = TOKENS.map(function (t, i) {
      return '<div class="ranking-item"><span class="ranking-item__rank">#' + (i + 1) + '</span><span class="ranking-item__token">' + t.symbol + '</span><span class="ranking-item__count">' + t.mentions.toLocaleString() + '</span><span class="ranking-item__change ranking-item__change--' + (t.up ? 'up' : 'down') + '">' + t.change + '</span></div>';
    }).join('');
  }

  /* Trend Chart */
  function renderTrendChart() {
    var ctx = $('#trend-chart').getContext('2d');
    var style = getComputedStyle(document.documentElement);
    var textColor = style.getPropertyValue('--color-text-muted').trim() || '#999';
    var borderColor = style.getPropertyValue('--color-border').trim() || '#333';
    new Chart(ctx, {
      type: 'line',
      data: TREND_DATA,
      options: {
        responsive: true,
        maintainAspectRatio: true,
        interaction: { intersect: false, mode: 'index' },
        plugins: { legend: { labels: { color: textColor, font: { family: 'Space Mono', size: 11 } } } },
        scales: {
          x: { ticks: { color: textColor, font: { family: 'Space Mono', size: 10 } }, grid: { color: borderColor } },
          y: { ticks: { color: textColor, font: { family: 'Space Mono', size: 10 } }, grid: { color: borderColor } }
        }
      }
    });
  }

  /* Sentiment Chart */
  function renderSentimentChart() {
    var ctx = $('#sentiment-chart').getContext('2d');
    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Bullish', 'Neutral', 'Bearish'],
        datasets: [{ data: [SENTIMENT.bullish, SENTIMENT.neutral, SENTIMENT.bearish], backgroundColor: ['#22c55e', '#f59e0b', '#ef4444'], borderWidth: 0 }]
      },
      options: {
        responsive: true,
        cutout: '65%',
        plugins: { legend: { display: false } }
      }
    });
    var legend = $('#sentiment-legend');
    var items = [
      { label: 'Bullish ' + SENTIMENT.bullish + '%', color: '#22c55e' },
      { label: 'Neutral ' + SENTIMENT.neutral + '%', color: '#f59e0b' },
      { label: 'Bearish ' + SENTIMENT.bearish + '%', color: '#ef4444' }
    ];
    legend.innerHTML = items.map(function (it) {
      return '<div class="sentiment-legend__item"><span class="sentiment-legend__dot" style="background:' + it.color + '"></span>' + it.label + '</div>';
    }).join('');
  }

  /* KOL Timeline */
  function renderKOLTimeline() {
    var el = $('#kol-list');
    el.innerHTML = KOL_MENTIONS.map(function (k) {
      return '<div class="kol-item"><div class="kol-item__avatar">' + k.initials + '</div><div class="kol-item__body"><div class="kol-item__name">' + k.name + ' <span class="kol-item__handle">' + k.handle + '</span></div><div class="kol-item__text">' + k.text + '</div><div class="kol-item__meta"><span class="kol-item__time">' + k.time + '</span><span class="kol-item__token-tag">$' + k.token + '</span></div></div></div>';
    }).join('');
  }

  /* Animations */
  function initAnimations() {
    if (prefersReducedMotion) return;
    var heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl.from('.hero__label', { opacity: 0, y: 10, duration: 0.5 })
      .from('.hero__title', { opacity: 0, y: 16, duration: 0.7 }, '-=0.3')
      .from('.hero__subtitle', { opacity: 0, y: 10, duration: 0.5 }, '-=0.3')
      .from('.gauge-card', { opacity: 0, y: 20, duration: 0.4, stagger: 0.08 }, '-=0.2');
    gsap.from('.ranking-item', {
      scrollTrigger: { trigger: '#dashboard', start: 'top 80%', once: true },
      opacity: 0, y: 16, duration: 0.4, stagger: 0.04, ease: 'power3.out'
    });
    gsap.from('.kol-item', {
      scrollTrigger: { trigger: '#kol-timeline', start: 'top 80%', once: true },
      opacity: 0, y: 16, duration: 0.5, stagger: 0.06, ease: 'power3.out'
    });
  }

  function init() {
    renderGauges();
    renderRanking();
    renderTrendChart();
    renderSentimentChart();
    renderKOLTimeline();
    initAnimations();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
