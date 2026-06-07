/* ============================================================
   Topic Dashboard — script.js
   Skeleton: A9 Dashboard Grid 3-col | Entry: D13 blur(8px)→blur(0)
   Hero: H9 Gauge | Cards: .topic-metric
   ============================================================ */
(function () {
  'use strict';
  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var TOPICS = [
    { name: 'Bitcoin ETF Inflows', score: 97, trend: 'up', tweets: 48200, category: 'Crypto', trendData: [42,55,61,68,74,82,88,91,95,97,96,97] },
    { name: 'GPT-5 Release', score: 94, trend: 'up', tweets: 62100, category: 'AI', trendData: [30,35,40,52,65,78,85,90,92,93,94,94] },
    { name: 'Solana DeFi Summer', score: 89, trend: 'up', tweets: 31400, category: 'Crypto', trendData: [45,50,55,60,65,70,75,80,84,87,88,89] },
    { name: 'Fed Rate Decision', score: 86, trend: 'flat', tweets: 55800, category: 'Macro', trendData: [80,82,84,85,86,86,85,86,86,85,86,86] },
    { name: 'RWA Tokenization', score: 82, trend: 'up', tweets: 18900, category: 'Crypto', trendData: [35,40,48,55,60,65,70,74,78,80,81,82] },
    { name: 'Apple Vision Pro 2', score: 78, trend: 'down', tweets: 42300, category: 'Tech', trendData: [92,90,88,86,84,82,81,80,79,78,78,78] },
    { name: 'Ethereum Pectra', score: 75, trend: 'up', tweets: 22100, category: 'Crypto', trendData: [40,45,50,55,58,62,65,68,71,73,74,75] },
    { name: 'AI Agent Economy', score: 72, trend: 'up', tweets: 15600, category: 'AI', trendData: [25,30,35,42,48,55,60,64,67,70,71,72] },
    { name: 'DePIN Growth', score: 68, trend: 'up', tweets: 12800, category: 'Crypto', trendData: [30,35,38,42,48,52,56,60,63,66,67,68] },
    { name: 'US Election Polls', score: 65, trend: 'flat', tweets: 89200, category: 'Politics', trendData: [60,62,63,64,65,64,65,66,65,64,65,65] },
    { name: 'Meme Coin Season', score: 61, trend: 'down', tweets: 28700, category: 'Crypto', trendData: [78,75,72,70,68,66,65,64,63,62,61,61] },
    { name: 'Quantum Computing', score: 58, trend: 'up', tweets: 9400, category: 'Tech', trendData: [30,32,35,38,42,45,48,50,53,55,57,58] },
  ];

  var ALERTS = [
    { topic: 'Bitcoin ETF Inflows', badge: 'SPIKE +130%', desc: 'BlackRock iShares Bitcoin Trust recorded its largest single-day inflow of $1.2B.', prevScore: 42, currentScore: 97, tweetVelocity: '2,400/hr' },
    { topic: 'GPT-5 Release', badge: 'SPIKE +213%', desc: 'OpenAI announced GPT-5 with native multimodal reasoning. 40% improvement over GPT-4o.', prevScore: 30, currentScore: 94, tweetVelocity: '3,100/hr' },
    { topic: 'AI Agent Economy', badge: 'SPIKE +188%', desc: 'Multiple AI agent frameworks announced token launches simultaneously.', prevScore: 25, currentScore: 72, tweetVelocity: '890/hr' },
  ];

  var TIME_LABELS = ['00:00','02:00','04:00','06:00','08:00','10:00','12:00','14:00','16:00','18:00','20:00','22:00'];
  var CHART_COLORS = ['#6366f1','#16a34a','#d97706','#dc2626','#0d9488'];

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
      renderGauge();
    });
  })();

  function formatNum(n) {
    if (n >= 1000) return (n / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
    return n.toString();
  }

  /* Gauge (H9) */
  function renderGauge() {
    var canvas = document.getElementById('gauge-canvas');
    var ctx = canvas.getContext('2d');
    var dpr = window.devicePixelRatio || 1;
    var w = 200, h = 120;
    canvas.width = w * dpr; canvas.height = h * dpr;
    canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var cx = w / 2, cy = h - 10, r = 80;
    var avgScore = Math.round(TOPICS.reduce(function(s,t){return s+t.score},0)/TOPICS.length);

    // Background arc
    ctx.beginPath();
    ctx.arc(cx, cy, r, Math.PI, 0, false);
    ctx.lineWidth = 12;
    ctx.strokeStyle = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';
    ctx.lineCap = 'round';
    ctx.stroke();

    // Value arc
    var pct = avgScore / 100;
    ctx.beginPath();
    ctx.arc(cx, cy, r, Math.PI, Math.PI + (Math.PI * pct), false);
    ctx.lineWidth = 12;
    ctx.strokeStyle = isDark ? '#818cf8' : '#6366f1';
    ctx.lineCap = 'round';
    ctx.stroke();

    document.getElementById('gauge-value').textContent = avgScore;
  }

  /* Dashboard Grid (topic-metric cards) */
  function renderDashboard() {
    var grid = document.getElementById('dashboard-grid');
    grid.innerHTML = TOPICS.map(function (topic) {
      var trendClass = 'topic-metric__trend--' + topic.trend;
      var trendIcon = topic.trend === 'up' ? '▲' : topic.trend === 'down' ? '▼' : '—';
      return '<div class="topic-metric" data-animate>' +
        '<span class="topic-metric__category">' + topic.category + '</span>' +
        '<div class="topic-metric__name">' + topic.name + '</div>' +
        '<div class="topic-metric__score">' + topic.score + '</div>' +
        '<div class="topic-metric__bar-wrap"><div class="topic-metric__bar" style="width:' + topic.score + '%"></div></div>' +
        '<div class="topic-metric__meta">' +
          '<span class="' + trendClass + '">' + trendIcon + ' ' + topic.trend + '</span>' +
          '<span>' + formatNum(topic.tweets) + ' tweets</span>' +
        '</div>' +
      '</div>';
    }).join('');
  }

  /* Alerts */
  function renderAlerts() {
    var grid = document.getElementById('alert-grid');
    grid.innerHTML = ALERTS.map(function (alert) {
      return '<div class="topic-metric" data-animate>' +
        '<span class="topic-metric__badge">' + alert.badge + '</span>' +
        '<div class="topic-metric__name">' + alert.topic + '</div>' +
        '<p class="topic-metric__desc">' + alert.desc + '</p>' +
        '<div class="topic-metric__meta">' +
          '<span>Prev: ' + alert.prevScore + '</span>' +
          '<span>Now: ' + alert.currentScore + '</span>' +
          '<span class="topic-metric__velocity">' + alert.tweetVelocity + '</span>' +
        '</div>' +
      '</div>';
    }).join('');
  }

  /* Trend Line Chart */
  var trendChart = null;
  function renderTrendChart() {
    var wrap = document.getElementById('trend-chart-wrap');
    var skeleton = wrap.querySelector('.skeleton-chart');
    if (skeleton) skeleton.remove();
    var ctx = document.getElementById('trend-chart').getContext('2d');
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var topTopics = TOPICS.slice(0, 5);

    trendChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: TIME_LABELS,
        datasets: topTopics.map(function (topic, idx) {
          return { label: topic.name, data: topic.trendData, borderColor: CHART_COLORS[idx], backgroundColor: CHART_COLORS[idx] + '18', borderWidth: 2, pointRadius: 3, pointHoverRadius: 6, tension: 0.3, fill: false };
        }),
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
          x: { ticks: { color: isDark ? 'rgba(226,232,240,0.4)' : 'rgba(15,23,42,0.4)', font: { family: "'JetBrains Mono', monospace", size: 10 } }, grid: { color: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)' } },
          y: { beginAtZero: true, max: 100, title: { display: true, text: 'Heat Score', color: isDark ? 'rgba(226,232,240,0.5)' : 'rgba(15,23,42,0.5)', font: { family: "'JetBrains Mono', monospace", size: 11, weight: 700 } }, ticks: { color: isDark ? 'rgba(226,232,240,0.4)' : 'rgba(15,23,42,0.4)', font: { family: "'JetBrains Mono', monospace", size: 10 } }, grid: { color: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)' } },
        },
        plugins: {
          legend: { position: 'top', labels: { color: isDark ? '#e2e8f0' : '#0f172a', font: { family: "'Nunito Sans', sans-serif", size: 12 }, usePointStyle: true, pointStyle: 'circle', padding: 16 } },
          tooltip: { backgroundColor: isDark ? '#1e293b' : '#f8fafc', titleColor: isDark ? '#e2e8f0' : '#0f172a', bodyColor: isDark ? 'rgba(226,232,240,0.7)' : 'rgba(15,23,42,0.7)', borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)', borderWidth: 1, titleFont: { family: "'Urbanist', sans-serif", weight: 700 }, bodyFont: { family: "'JetBrains Mono', monospace" }, padding: 12 },
        },
      },
    });
  }

  function updateChartColors() {
    if (trendChart) { trendChart.destroy(); renderTrendChart(); }
  }

  /* GSAP — D13 blur(8px)→blur(0) */
  function initAnimations() {
    if (prefersReducedMotion) return;
    gsap.fromTo('.hero__text', { filter: 'blur(8px)', opacity: 0 }, { filter: 'blur(0px)', opacity: 1, duration: 0.8, ease: 'power3.out', clearProps: 'filter,opacity' });
    gsap.fromTo('.hero__gauge', { filter: 'blur(8px)', opacity: 0 }, { filter: 'blur(0px)', opacity: 1, duration: 0.8, delay: 0.2, ease: 'power3.out', clearProps: 'filter,opacity' });

    var sections = document.querySelectorAll('.section');
    sections.forEach(function (section) {
      var title = section.querySelector('.section__title');
      if (title) {
        gsap.fromTo(title,
          { filter: 'blur(8px)', opacity: 0 },
          { filter: 'blur(0px)', opacity: 1, duration: 0.6, ease: 'power3.out', clearProps: 'filter,opacity',
            scrollTrigger: { trigger: section, start: 'top 80%', toggleActions: 'play none none none' }
          }
        );
      }
      var cards = section.querySelectorAll('[data-animate]');
      if (cards.length) {
        gsap.fromTo(cards,
          { filter: 'blur(8px)', opacity: 0 },
          { filter: 'blur(0px)', opacity: 1, duration: 0.5, stagger: 0.06, ease: 'power3.out', clearProps: 'filter,opacity',
            scrollTrigger: { trigger: section, start: 'top 75%', toggleActions: 'play none none none' }
          }
        );
      }
    });
    gsap.fromTo('.chart-container--line',
      { filter: 'blur(8px)', opacity: 0 },
      { filter: 'blur(0px)', opacity: 1, duration: 0.7, ease: 'power3.out', clearProps: 'filter,opacity',
        scrollTrigger: { trigger: '#section-trends', start: 'top 80%', toggleActions: 'play none none none' }
      }
    );
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
      renderGauge();
      renderDashboard();
      renderTrendChart();
      renderAlerts();
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
