/* ============================================================
   Narrative Tracker — script.js
   Skeleton: A17 Full-width Sections | Entry: D17 translateY(-30px) from top
   Hero: H10 Inline | Cards: .narrative-section
   ============================================================ */
(function () {
  'use strict';
  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var NARRATIVES = [
    { name: 'AI × Crypto', score: 94, change7d: '+18', tokens: [{name:'TAO',correlation:0.92},{name:'RENDER',correlation:0.88},{name:'FET',correlation:0.85},{name:'NEAR',correlation:0.72}], lifecycle: [30,42,55,68,78,85,90,94] },
    { name: 'RWA Tokenization', score: 87, change7d: '+24', tokens: [{name:'ONDO',correlation:0.95},{name:'MKR',correlation:0.78},{name:'CRVUSD',correlation:0.65}], lifecycle: [15,22,35,48,60,72,82,87] },
    { name: 'DePIN', score: 78, change7d: '+12', tokens: [{name:'HNT',correlation:0.90},{name:'RNDR',correlation:0.82},{name:'MOBILE',correlation:0.75},{name:'DIMO',correlation:0.68}], lifecycle: [20,28,38,48,55,65,72,78] },
    { name: 'L2 Scaling', score: 72, change7d: '-5', tokens: [{name:'ARB',correlation:0.88},{name:'OP',correlation:0.85},{name:'STRK',correlation:0.72},{name:'MANTA',correlation:0.60}], lifecycle: [65,72,80,85,82,78,75,72] },
    { name: 'Meme Coins', score: 65, change7d: '-15', tokens: [{name:'PEPE',correlation:0.95},{name:'WIF',correlation:0.92},{name:'BONK',correlation:0.88}], lifecycle: [40,55,72,88,92,85,75,65] },
    { name: 'GameFi Revival', score: 58, change7d: '+8', tokens: [{name:'IMX',correlation:0.85},{name:'GALA',correlation:0.78},{name:'BEAM',correlation:0.72}], lifecycle: [25,30,35,40,45,50,55,58] },
    { name: 'Bitcoin DeFi', score: 52, change7d: '+20', tokens: [{name:'STX',correlation:0.90},{name:'ORDI',correlation:0.82},{name:'ALEX',correlation:0.70}], lifecycle: [10,15,20,28,35,42,48,52] },
    { name: 'Restaking', score: 45, change7d: '-8', tokens: [{name:'EIGEN',correlation:0.92},{name:'ALT',correlation:0.75},{name:'ETHFI',correlation:0.70}], lifecycle: [55,62,68,65,58,52,48,45] },
  ];

  var CHART_COLORS = ['#15803d','#d97706','#0369a1','#9333ea','#dc2626','#0891b2','#c2410c','#6d28d9'];
  var WEEK_LABELS = ['W1','W2','W3','W4','W5','W6','W7','W8'];

  /* Theme Toggle */
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

  /* KPIs */
  function renderKPIs() {
    var sorted = NARRATIVES.slice().sort(function(a,b){return b.score-a.score});
    var dominant = sorted[0];
    document.getElementById('kpi-dominant').textContent = dominant.name;
    document.getElementById('kpi-dominant-score').textContent = 'Score: ' + dominant.score;
    var emerging = NARRATIVES.slice().sort(function(a,b){return parseInt(b.change7d)-parseInt(a.change7d)})[0];
    document.getElementById('kpi-emerging').textContent = emerging.name;
    document.getElementById('kpi-emerging-change').textContent = emerging.change7d + ' in 7d';
    document.getElementById('kpi-narratives').textContent = NARRATIVES.length;
    document.querySelectorAll('.kpi-card').forEach(function(c){c.classList.remove('skeleton')});
  }

  /* Full-width Narrative Sections (A17) */
  function renderNarrativeSections() {
    var container = document.getElementById('narrative-sections');
    container.innerHTML = NARRATIVES.map(function (n) {
      var changeClass = parseInt(n.change7d) >= 0 ? 'narrative-section__change--positive' : 'narrative-section__change--negative';
      var changeIcon = parseInt(n.change7d) >= 0 ? '▲' : '▼';
      return '<div class="narrative-section" data-animate>' +
        '<div class="narrative-section__inner">' +
          '<div class="narrative-section__left">' +
            '<div class="narrative-section__name">' + n.name + '</div>' +
            '<div class="narrative-section__score">' + n.score + '</div>' +
            '<div class="narrative-section__change ' + changeClass + '">' + changeIcon + ' ' + n.change7d + ' (7d)</div>' +
            '<div class="narrative-section__bar-wrap"><div class="narrative-section__bar" style="width:' + n.score + '%"></div></div>' +
          '</div>' +
          '<div class="narrative-section__right">' +
            '<div class="narrative-section__tokens">' +
              n.tokens.map(function(t) {
                return '<div class="narrative-section__token">' +
                  '<span class="narrative-section__token-name">$' + t.name + '</span>' +
                  '<span class="narrative-section__token-corr">' + (t.correlation * 100).toFixed(0) + '%</span>' +
                '</div>';
              }).join('') +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>';
    }).join('');
  }

  /* Token Association Cards */
  function renderTokenAssociations() {
    var grid = document.getElementById('token-assoc-grid');
    grid.innerHTML = NARRATIVES.map(function (n) {
      return '<div class="token-assoc-card" data-animate>' +
        '<div class="token-assoc-card__name">' + n.name + '</div>' +
        '<div class="token-assoc-card__tokens">' +
          n.tokens.map(function(t) {
            var pct = Math.round(t.correlation * 100);
            return '<div class="token-assoc-card__row">' +
              '<span class="token-assoc-card__token-name">$' + t.name + '</span>' +
              '<div class="token-assoc-card__bar-wrap"><div class="token-assoc-card__bar" style="width:' + pct + '%"></div></div>' +
              '<span class="token-assoc-card__corr">' + pct + '%</span>' +
            '</div>';
          }).join('') +
        '</div>' +
      '</div>';
    }).join('');
  }

  /* Lifecycle Line Chart */
  var lifecycleChart = null;
  function renderLifecycleChart() {
    var wrap = document.getElementById('lifecycle-chart-wrap');
    var skeleton = wrap.querySelector('.skeleton-chart');
    if (skeleton) skeleton.remove();
    var ctx = document.getElementById('lifecycle-chart').getContext('2d');
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    lifecycleChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: WEEK_LABELS,
        datasets: NARRATIVES.map(function(n, idx) {
          return { label: n.name, data: n.lifecycle, borderColor: CHART_COLORS[idx], backgroundColor: CHART_COLORS[idx] + '18', borderWidth: 2, pointRadius: 3, pointHoverRadius: 6, tension: 0.3, fill: false };
        }),
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
          x: { ticks: { color: isDark ? 'rgba(232,232,226,0.4)' : 'rgba(26,26,24,0.4)', font: { family: "'IBM Plex Mono', monospace", size: 10 } }, grid: { color: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)' } },
          y: { beginAtZero: true, max: 100, title: { display: true, text: 'Heat Score', color: isDark ? 'rgba(232,232,226,0.5)' : 'rgba(26,26,24,0.5)', font: { family: "'IBM Plex Mono', monospace", size: 11, weight: 700 } }, ticks: { color: isDark ? 'rgba(232,232,226,0.4)' : 'rgba(26,26,24,0.4)', font: { family: "'IBM Plex Mono', monospace", size: 10 } }, grid: { color: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)' } },
        },
        plugins: {
          legend: { position: 'top', labels: { color: isDark ? '#e8e8e2' : '#1a1a18', font: { family: "'Source Sans 3', sans-serif", size: 12 }, usePointStyle: true, pointStyle: 'circle', padding: 16 } },
          tooltip: { backgroundColor: isDark ? '#1a1c18' : '#fefdfb', titleColor: isDark ? '#e8e8e2' : '#1a1a18', bodyColor: isDark ? 'rgba(232,232,226,0.7)' : 'rgba(26,26,24,0.7)', borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)', borderWidth: 1, titleFont: { family: "'Newsreader', serif", weight: 700 }, bodyFont: { family: "'IBM Plex Mono', monospace" }, padding: 12 },
        },
      },
    });
  }

  function updateChartColors() {
    if (lifecycleChart) { lifecycleChart.destroy(); renderLifecycleChart(); }
  }

  /* GSAP — D17 translateY(-30px) from top */
  function initAnimations() {
    if (prefersReducedMotion) return;
    gsap.from('.hero__inline', { y: -30, opacity: 0, duration: 0.7, ease: 'power3.out' });
    gsap.from('.kpi-card', { y: -30, opacity: 0, duration: 0.5, stagger: 0.08, delay: 0.2, ease: 'power3.out' });

    /* Full-width narrative sections */
    var narrativeSections = document.querySelectorAll('.narrative-section[data-animate]');
    narrativeSections.forEach(function (section) {
      gsap.from(section, {
        scrollTrigger: { trigger: section, start: 'top 85%', toggleActions: 'play none none none' },
        y: -30, opacity: 0, duration: 0.6, ease: 'power3.out',
      });
    });

    var sections = document.querySelectorAll('.section');
    sections.forEach(function (section) {
      var title = section.querySelector('.section__title');
      if (title) {
        gsap.from(title, {
          scrollTrigger: { trigger: section, start: 'top 80%', toggleActions: 'play none none none' },
          y: -30, opacity: 0, duration: 0.6, ease: 'power3.out',
        });
      }
      var cards = section.querySelectorAll('[data-animate]');
      if (cards.length) {
        gsap.from(cards, {
          scrollTrigger: { trigger: section, start: 'top 75%', toggleActions: 'play none none none' },
          y: -30, opacity: 0, duration: 0.5, stagger: 0.06, ease: 'power3.out',
        });
      }
    });

    gsap.from('.chart-container--line', {
      scrollTrigger: { trigger: '#section-lifecycle', start: 'top 80%', toggleActions: 'play none none none' },
      y: -30, opacity: 0, duration: 0.7, ease: 'power3.out',
    });
  }

  function showError(msg) {
    var toast = document.getElementById('error-toast');
    document.getElementById('error-msg').textContent = msg;
    toast.hidden = false;
  }
  document.getElementById('error-close').addEventListener('click', function () {
    document.getElementById('error-toast').hidden = true;
  });

  function init() {
    try {
      renderKPIs();
      renderNarrativeSections();
      renderLifecycleChart();
      renderTokenAssociations();
      initAnimations();
    } catch (err) {
      showError('Failed to initialize: ' + err.message);
    }
  }

  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', init); }
  else { init(); }
})();
