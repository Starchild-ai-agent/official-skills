/* ============================================================
   KOL Tracker — script.js

   Skeleton: A19 Feed/Stream | Entry: D10 translateX(-50px)
   Hero: H6 Terminal Header | Cards: .kol-item
   Animation: GSAP 3 + ScrollTrigger (CDN)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);

  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var CONFIG = {
    twitterHandle: (function () {
      var raw = '{{TWITTER_HANDLE}}';
      if (raw.startsWith('{{')) return '@cryptoanalyst';
      return raw;
    })(),
  };

  /* ---------- Simulated KOL Data ---------- */
  var KOLS = [
    { name: 'CryptoHayes', handle: '@CryptoHayes', followers: '1.2M', avatar: 'CH', sentiment: 'bullish', opinion: 'ETH is massively undervalued relative to its fee revenue. The Pectra upgrade will be a catalyst. Accumulating below $4k is a gift.', tokens: ['ETH', 'ENA', 'PENDLE'] },
    { name: 'DegenSpartan', handle: '@DegenSpartan', followers: '890K', avatar: 'DS', sentiment: 'bearish', opinion: 'Market structure looks fragile. Too much leverage in the system. Expecting a 20-30% correction before the next leg up.', tokens: ['BTC', 'SOL'] },
    { name: 'Cobie', handle: '@coaborative', followers: '780K', avatar: 'CB', sentiment: 'bullish', opinion: 'The RWA narrative is just getting started. Tokenized treasuries alone are a $10T addressable market. ONDO and MKR are positioned well.', tokens: ['ONDO', 'MKR', 'ETH'] },
    { name: 'Ansem', handle: '@blknoiz06', followers: '650K', avatar: 'AN', sentiment: 'bullish', opinion: 'Solana DeFi TVL is exploding. JUP and RAY are the picks. The ecosystem is maturing faster than people realize.', tokens: ['SOL', 'JUP', 'RAY'] },
    { name: 'GCR', handle: '@GCRClassic', followers: '520K', avatar: 'GC', sentiment: 'neutral', opinion: 'Watching BTC dominance closely. If it breaks 58%, alts will bleed. If it rejects, rotation into mid-caps is likely.', tokens: ['BTC', 'ETH'] },
    { name: 'Hsaka', handle: '@HsakaTrades', followers: '480K', avatar: 'HS', sentiment: 'bullish', opinion: 'AI x Crypto convergence is the trade of the cycle. TAO, RENDER, and FET are building real infrastructure. Not just hype.', tokens: ['TAO', 'RENDER', 'FET'] },
    { name: 'ZachXBT', handle: '@zachxbt', followers: '1.1M', avatar: 'ZX', sentiment: 'neutral', opinion: 'Multiple projects showing suspicious on-chain activity. Be careful with new launches. Due diligence is more important than ever.', tokens: ['BTC'] },
    { name: 'Pentoshi', handle: '@Pentosh1', followers: '720K', avatar: 'PT', sentiment: 'bullish', opinion: 'BTC weekly structure is incredibly bullish. Higher lows since January. $120k target by Q3 is very much in play.', tokens: ['BTC', 'ETH', 'SOL'] },
  ];

  var sentimentCounts = { bullish: 0, bearish: 0, neutral: 0 };
  KOLS.forEach(function (kol) { sentimentCounts[kol.sentiment]++; });

  var tokenMentions = {};
  KOLS.forEach(function (kol) {
    kol.tokens.forEach(function (token) {
      tokenMentions[token] = (tokenMentions[token] || 0) + 1;
    });
  });
  var sortedTokens = Object.keys(tokenMentions).sort(function (a, b) { return tokenMentions[b] - tokenMentions[a]; });

  var consensusSignals = sortedTokens
    .filter(function (token) { return tokenMentions[token] >= 2; })
    .map(function (token) {
      var mentioningKols = KOLS.filter(function (kol) { return kol.tokens.indexOf(token) !== -1; });
      var bullishCount = mentioningKols.filter(function (k) { return k.sentiment === 'bullish'; }).length;
      var signal = bullishCount >= mentioningKols.length * 0.6 ? 'STRONG BUY' : bullishCount >= mentioningKols.length * 0.4 ? 'MODERATE' : 'MIXED';
      return { token: token, count: tokenMentions[token], kols: mentioningKols.map(function (k) { return k.name; }), signal: signal };
    });

  /* ---------- Theme Toggle ---------- */
  (function initTheme() {
    var toggle = document.getElementById('theme-toggle');
    var stored = localStorage.getItem('theme');
    if (stored === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
    toggle.addEventListener('click', function () {
      var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
      localStorage.setItem('theme', isDark ? 'light' : 'dark');
      updateChartColors();
    });
  })();

  /* ---------- Clock ---------- */
  function updateClock() {
    var el = document.getElementById('hero-time');
    var now = new Date();
    el.textContent = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    el.setAttribute('datetime', now.toISOString());
  }
  updateClock();
  setInterval(updateClock, 1000);

  /* ---------- Render KPIs ---------- */
  function renderKPIs() {
    document.getElementById('kpi-kol-count').textContent = KOLS.length;
    var hottest = KOLS.reduce(function (best, kol) {
      var score = kol.tokens.length * 2 + (kol.sentiment === 'bullish' ? 3 : kol.sentiment === 'bearish' ? 2 : 1);
      return score > best.score ? { kol: kol, score: score } : best;
    }, { kol: KOLS[0], score: 0 });
    document.getElementById('kpi-hot-take').textContent = hottest.kol.tokens[0];
    document.getElementById('kpi-hot-take-by').textContent = 'by ' + hottest.kol.name;
    var pct = Math.round((sentimentCounts.bullish / KOLS.length) * 100);
    document.getElementById('kpi-sentiment').textContent = pct + '% Bullish';
    document.querySelectorAll('.kpi-card').forEach(function (card) { card.classList.remove('skeleton'); });
  }

  /* ---------- KOL Feed Items ---------- */
  function renderKOLCards() {
    var grid = document.getElementById('kol-grid');
    grid.innerHTML = KOLS.map(function (kol) {
      return '<div class="kol-item" data-animate>' +
        '<div class="kol-item__header">' +
          '<div class="kol-item__avatar">' + kol.avatar + '</div>' +
          '<div class="kol-item__info">' +
            '<span class="kol-item__name">' + kol.name + '</span>' +
            '<span class="kol-item__followers">' + kol.handle + ' · ' + kol.followers + '</span>' +
          '</div>' +
          '<span class="kol-item__sentiment-tag kol-item__sentiment-tag--' + kol.sentiment + '">' + kol.sentiment + '</span>' +
        '</div>' +
        '<p class="kol-item__opinion">' + kol.opinion + '</p>' +
        '<div class="kol-item__tokens">' +
          kol.tokens.map(function (t) { return '<span class="kol-item__token-tag">$' + t + '</span>'; }).join('') +
        '</div>' +
      '</div>';
    }).join('');
  }

  /* ---------- Sentiment Doughnut Chart ---------- */
  var sentimentChart = null;

  function renderSentimentChart() {
    var wrap = document.getElementById('sentiment-chart-wrap');
    var skeleton = wrap.querySelector('.skeleton-chart');
    if (skeleton) skeleton.remove();
    var ctx = document.getElementById('sentiment-chart').getContext('2d');
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    sentimentChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Bullish', 'Bearish', 'Neutral'],
        datasets: [{
          data: [sentimentCounts.bullish, sentimentCounts.bearish, sentimentCounts.neutral],
          backgroundColor: [isDark ? '#4ade80' : '#16a34a', isDark ? '#f87171' : '#dc2626', isDark ? '#fbbf24' : '#d97706'],
          borderColor: isDark ? '#1e1b18' : '#faf9f7',
          borderWidth: 3,
          hoverOffset: 8,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '55%',
        plugins: {
          legend: { position: 'bottom', labels: { color: isDark ? '#f5f0ed' : '#1c1917', font: { family: "'Karla', sans-serif", size: 13, weight: 500 }, usePointStyle: true, pointStyle: 'circle', padding: 20 } },
          tooltip: {
            backgroundColor: isDark ? '#1e1b18' : '#faf9f7',
            titleColor: isDark ? '#f5f0ed' : '#1c1917',
            bodyColor: isDark ? 'rgba(245,240,237,0.7)' : 'rgba(28,25,23,0.7)',
            borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
            borderWidth: 1,
            titleFont: { family: "'Lexend Deca', sans-serif", weight: 600 },
            bodyFont: { family: "'Source Code Pro', monospace" },
            padding: 12,
            callbacks: { label: function (ctx) { var total = ctx.dataset.data.reduce(function (s, v) { return s + v; }, 0); return ctx.label + ': ' + ctx.parsed + ' (' + Math.round((ctx.parsed / total) * 100) + '%)'; } },
          },
        },
      },
    });
  }

  /* ---------- Token Mention Bar Chart ---------- */
  var tokenChart = null;

  function renderTokenChart() {
    var wrap = document.getElementById('token-chart-wrap');
    var skeleton = wrap.querySelector('.skeleton-chart');
    if (skeleton) skeleton.remove();
    var ctx = document.getElementById('token-chart').getContext('2d');
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var labels = sortedTokens.slice(0, 10);
    var data = labels.map(function (t) { return tokenMentions[t]; });

    tokenChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels.map(function (t) { return '$' + t; }),
        datasets: [{ label: 'Mentions', data: data, backgroundColor: isDark ? 'rgba(239,68,68,0.6)' : 'rgba(220,38,38,0.5)', borderColor: isDark ? '#ef4444' : '#dc2626', borderWidth: 1, borderRadius: 4 }],
      },
      options: {
        indexAxis: 'y', responsive: true, maintainAspectRatio: false,
        scales: {
          x: { beginAtZero: true, ticks: { stepSize: 1, color: isDark ? 'rgba(245,240,237,0.4)' : 'rgba(28,25,23,0.4)', font: { family: "'Source Code Pro', monospace", size: 11 } }, grid: { color: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)' } },
          y: { ticks: { color: isDark ? 'rgba(245,240,237,0.7)' : 'rgba(28,25,23,0.7)', font: { family: "'Source Code Pro', monospace", size: 12, weight: 600 } }, grid: { display: false } },
        },
        plugins: {
          legend: { display: false },
          tooltip: { backgroundColor: isDark ? '#1e1b18' : '#faf9f7', titleColor: isDark ? '#f5f0ed' : '#1c1917', bodyColor: isDark ? 'rgba(245,240,237,0.7)' : 'rgba(28,25,23,0.7)', borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)', borderWidth: 1, titleFont: { family: "'Lexend Deca', sans-serif", weight: 600 }, bodyFont: { family: "'Source Code Pro', monospace" }, padding: 12, callbacks: { label: function (ctx) { return ctx.parsed.x + ' KOL mentions'; } } },
        },
      },
    });
  }

  /* ---------- Consensus Signal Cards ---------- */
  function renderConsensusCards() {
    var grid = document.getElementById('consensus-grid');
    if (consensusSignals.length === 0) {
      grid.innerHTML = '<div class="kol-item"><p class="consensus-card__kols">No consensus signals detected today.</p></div>';
      return;
    }
    grid.innerHTML = consensusSignals.map(function (sig) {
      return '<div class="kol-item" data-animate>' +
        '<div class="consensus-card__header">' +
          '<span class="consensus-card__token">$' + sig.token + '</span>' +
          '<span class="consensus-card__count">' + sig.count + ' mentions</span>' +
        '</div>' +
        '<p class="consensus-card__kols">Mentioned by: ' + sig.kols.join(', ') + '</p>' +
        '<span class="consensus-card__signal">' + sig.signal + '</span>' +
      '</div>';
    }).join('');
  }

  /* ---------- Update Chart Colors ---------- */
  function updateChartColors() {
    if (sentimentChart) { sentimentChart.destroy(); renderSentimentChart(); }
    if (tokenChart) { tokenChart.destroy(); renderTokenChart(); }
  }

  /* ---------- GSAP Animations — D10 translateX(-50px) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    gsap.from('.terminal-header', { opacity: 0, duration: 0.5, ease: 'power2.out' });
    gsap.from('.terminal-body', { x: -50, opacity: 0, duration: 0.7, delay: 0.15, ease: 'power3.out' });
    gsap.from('.kpi-card', { opacity: 0, duration: 0.5, stagger: 0.08, delay: 0.3, ease: 'power3.out' });

    var sections = document.querySelectorAll('.section');
    sections.forEach(function (section) {
      var title = section.querySelector('.section__title');
      if (title) {
        gsap.from(title, {
          scrollTrigger: { trigger: section, start: 'top 80%', toggleActions: 'play none none none' },
          x: -50, opacity: 0, duration: 0.6, ease: 'power3.out',
        });
      }

      var cards = section.querySelectorAll('[data-animate]');
      if (cards.length) {
        gsap.from(cards, {
          scrollTrigger: { trigger: section, start: 'top 75%', toggleActions: 'play none none none' },
          x: -50, opacity: 0, duration: 0.5, stagger: 0.06, ease: 'power3.out',
        });
      }
    });

    gsap.from('.chart-container--doughnut', {
      scrollTrigger: { trigger: '#section-sentiment', start: 'top 80%', toggleActions: 'play none none none' },
      x: -50, opacity: 0, duration: 0.7, ease: 'power3.out',
    });

    gsap.from('.chart-container--bar', {
      scrollTrigger: { trigger: '#section-tokens', start: 'top 80%', toggleActions: 'play none none none' },
      x: -50, opacity: 0, duration: 0.7, ease: 'power3.out',
    });
  }

  /* ---------- Error Handling ---------- */
  function showError(msg) {
    var toast = document.getElementById('error-toast');
    document.getElementById('error-msg').textContent = msg;
    toast.hidden = false;
  }

  document.getElementById('error-close').addEventListener('click', function () {
    document.getElementById('error-toast').hidden = true;
  });

  /* ---------- Init ---------- */
  function init() {
    try {
      renderKPIs();
      renderKOLCards();
      renderSentimentChart();
      renderTokenChart();
      renderConsensusCards();
      initAnimations();
    } catch (err) {
      showError('Failed to initialize: ' + err.message);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
