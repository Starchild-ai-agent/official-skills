/* ============================================================
   Interest Radar — script.js

   Pure frontend with built-in simulated Twitter interest data.
   Renders radar chart (in hero), topic details, trend line chart,
   and recommended accounts.

   Skeleton: A11 Centered | Entry: D5 opacity only
   Animation: GSAP 3 + ScrollTrigger (CDN)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);

  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var CONFIG = {
    heroImageUrl: (function () {
      var raw = '{{HERO_IMAGE_URL}}';
      if (raw.startsWith('{{')) return '';
      return raw;
    })(),
    twitterHandle: (function () {
      var raw = '{{TWITTER_HANDLE}}';
      if (raw.startsWith('{{')) return '@analyst';
      return raw;
    })(),
  };

  /* ---------- Simulated Interest Data ---------- */
  var INTERESTS = [
    { name: 'Technology', weight: 88, icon: '⚙️', trend: 'up', recs: ['Latest AI breakthroughs', 'Developer tools roundup', 'Tech startup analysis'] },
    { name: 'Finance', weight: 72, icon: '📊', trend: 'stable', recs: ['Market analysis threads', 'Investment strategies', 'Fintech innovations'] },
    { name: 'Science', weight: 65, icon: '🔬', trend: 'up', recs: ['Research paper summaries', 'Space exploration updates', 'Climate science data'] },
    { name: 'Design', weight: 58, icon: '🎨', trend: 'down', recs: ['UI/UX case studies', 'Design system guides', 'Typography deep dives'] },
    { name: 'Politics', weight: 45, icon: '🏛️', trend: 'stable', recs: ['Policy analysis', 'Geopolitical commentary', 'Election data threads'] },
    { name: 'Sports', weight: 38, icon: '⚽', trend: 'down', recs: ['Game analytics', 'Player statistics', 'Fantasy sports tips'] },
    { name: 'Entertainment', weight: 52, icon: '🎬', trend: 'up', recs: ['Film reviews', 'Streaming recommendations', 'Pop culture analysis'] },
    { name: 'Health', weight: 42, icon: '🏥', trend: 'stable', recs: ['Wellness research', 'Nutrition science', 'Mental health resources'] },
    { name: 'Education', weight: 60, icon: '📚', trend: 'up', recs: ['Learning techniques', 'Online course reviews', 'Skill development paths'] },
    { name: 'Travel', weight: 30, icon: '✈️', trend: 'down', recs: ['Destination guides', 'Travel hacking tips', 'Cultural experiences'] },
  ];

  var TREND_DATA = {
    labels: Array.from({ length: 30 }, function (_, i) { return 'Day ' + (i + 1); }),
    datasets: [
      { name: 'Technology', color: '#0d9488', data: [80,82,79,85,83,86,84,88,87,85,86,88,90,87,89,88,86,85,87,88,90,89,88,87,86,88,89,88,87,88] },
      { name: 'Finance', color: '#16a34a', data: [70,72,71,73,72,74,73,72,71,73,74,72,71,73,72,74,73,72,71,73,72,74,73,72,71,73,72,74,73,72] },
      { name: 'Science', color: '#d97706', data: [55,56,58,57,59,60,61,62,60,61,63,62,64,63,62,64,63,65,64,63,65,64,63,65,64,63,65,64,65,65] },
      { name: 'Entertainment', color: '#ec4899', data: [40,42,41,43,44,45,46,48,47,49,50,48,49,51,50,52,51,50,52,51,53,52,51,53,52,51,53,52,51,52] },
    ],
  };

  var RECOMMENDED_ACCOUNTS = [
    { name: 'TechInsider', handle: '@techinsider', avatar: 'T', reason: 'Covers AI, developer tools, and startup ecosystem — aligns with your top interest.', tags: ['Technology', 'AI', 'Startups'] },
    { name: 'DataViz Weekly', handle: '@datavizweekly', avatar: 'D', reason: 'Beautiful data visualizations and infographics on science and finance topics.', tags: ['Design', 'Science', 'Finance'] },
    { name: 'ScienceAlert', handle: '@sciencealert', avatar: 'S', reason: 'Breaking science news with accessible explanations — matches your growing science interest.', tags: ['Science', 'Health', 'Education'] },
    { name: 'FinanceThreads', handle: '@financethreads', avatar: 'F', reason: 'In-depth financial analysis threads with charts and data — perfect for your finance interest.', tags: ['Finance', 'Technology'] },
    { name: 'LearnHub', handle: '@learnhub', avatar: 'L', reason: 'Curated learning resources and skill development paths across multiple domains.', tags: ['Education', 'Technology', 'Design'] },
  ];

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

  /* ---------- Compute Diversity Score ---------- */
  function computeDiversityScore(interests) {
    var total = interests.reduce(function (s, i) { return s + i.weight; }, 0);
    var probs = interests.map(function (i) { return i.weight / total; });
    var entropy = -probs.reduce(function (s, p) { return s + (p > 0 ? p * Math.log2(p) : 0); }, 0);
    var maxEntropy = Math.log2(interests.length);
    return Math.round((entropy / maxEntropy) * 100);
  }

  /* ---------- Render KPIs ---------- */
  function renderKPIs() {
    var diversityScore = computeDiversityScore(INTERESTS);
    var sorted = INTERESTS.slice().sort(function (a, b) { return b.weight - a.weight; });
    var topInterest = sorted[0];

    document.getElementById('kpi-diversity').textContent = diversityScore;
    document.getElementById('kpi-top-interest').textContent = topInterest.name;
    document.getElementById('kpi-top-pct').textContent = topInterest.weight + '% weight';
    document.getElementById('kpi-total-topics').textContent = INTERESTS.length;

    document.querySelectorAll('.kpi-card').forEach(function (card) {
      card.classList.remove('skeleton');
    });
  }

  /* ---------- Radar Chart (in hero) ---------- */
  var radarChart = null;

  function renderRadarChart() {
    var wrap = document.querySelector('.hero__chart-wrap');
    var skeleton = wrap.querySelector('.skeleton-chart');
    if (skeleton) skeleton.remove();

    var ctx = document.getElementById('radar-chart').getContext('2d');
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    radarChart = new Chart(ctx, {
      type: 'radar',
      data: {
        labels: INTERESTS.map(function (i) { return i.name; }),
        datasets: [{
          label: 'Interest Weight',
          data: INTERESTS.map(function (i) { return i.weight; }),
          backgroundColor: isDark ? 'rgba(20,184,166,0.15)' : 'rgba(13,148,136,0.12)',
          borderColor: isDark ? '#14b8a6' : '#0d9488',
          borderWidth: 2,
          pointBackgroundColor: isDark ? '#14b8a6' : '#0d9488',
          pointBorderColor: isDark ? '#1c1917' : '#fafaf9',
          pointBorderWidth: 2,
          pointRadius: 5,
          pointHoverRadius: 7,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            beginAtZero: true,
            max: 100,
            ticks: {
              stepSize: 20,
              color: isDark ? 'rgba(231,229,228,0.4)' : 'rgba(28,25,23,0.4)',
              backdropColor: 'transparent',
              font: { family: "'JetBrains Mono', monospace", size: 10 },
            },
            grid: {
              color: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.07)',
            },
            angleLines: {
              color: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.07)',
            },
            pointLabels: {
              color: isDark ? '#e7e5e4' : '#1c1917',
              font: { family: "'Space Grotesk', sans-serif", size: 12, weight: 500 },
            },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: isDark ? '#1c1917' : '#fafaf9',
            titleColor: isDark ? '#e7e5e4' : '#1c1917',
            bodyColor: isDark ? 'rgba(231,229,228,0.7)' : 'rgba(28,25,23,0.7)',
            borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
            borderWidth: 1,
            titleFont: { family: "'Space Grotesk', sans-serif", weight: 600 },
            bodyFont: { family: "'JetBrains Mono', monospace" },
            padding: 12,
            callbacks: {
              label: function (ctx) { return ctx.parsed.r + '% weight'; },
            },
          },
        },
      },
    });
  }

  /* ---------- Trend Line Chart ---------- */
  var trendChart = null;

  function renderTrendChart() {
    var wrap = document.getElementById('trend-chart-wrap');
    var skeleton = wrap.querySelector('.skeleton-chart');
    if (skeleton) skeleton.remove();

    var ctx = document.getElementById('trend-chart').getContext('2d');
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    trendChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: TREND_DATA.labels,
        datasets: TREND_DATA.datasets.map(function (ds) {
          return {
            label: ds.name,
            data: ds.data,
            borderColor: ds.color,
            backgroundColor: ds.color + '18',
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
            tension: 0.4,
            fill: false,
          };
        }),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
          x: {
            ticks: {
              color: isDark ? 'rgba(231,229,228,0.4)' : 'rgba(28,25,23,0.4)',
              font: { family: "'JetBrains Mono', monospace", size: 10 },
              maxTicksLimit: 10,
            },
            grid: { color: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)' },
          },
          y: {
            min: 0,
            max: 100,
            ticks: {
              color: isDark ? 'rgba(231,229,228,0.4)' : 'rgba(28,25,23,0.4)',
              font: { family: "'JetBrains Mono', monospace", size: 10 },
              callback: function (v) { return v + '%'; },
            },
            grid: { color: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)' },
          },
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              color: isDark ? '#e7e5e4' : '#1c1917',
              font: { family: "'Outfit', sans-serif", size: 12 },
              usePointStyle: true,
              pointStyle: 'circle',
              padding: 16,
            },
          },
          tooltip: {
            backgroundColor: isDark ? '#1c1917' : '#fafaf9',
            titleColor: isDark ? '#e7e5e4' : '#1c1917',
            bodyColor: isDark ? 'rgba(231,229,228,0.7)' : 'rgba(28,25,23,0.7)',
            borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
            borderWidth: 1,
            titleFont: { family: "'Space Grotesk', sans-serif", weight: 600 },
            bodyFont: { family: "'JetBrains Mono', monospace" },
            padding: 12,
            callbacks: {
              label: function (ctx) { return ctx.dataset.label + ': ' + ctx.parsed.y + '%'; },
            },
          },
        },
      },
    });
  }

  /* ---------- Topic Cards ---------- */
  function renderTopicCards() {
    var grid = document.getElementById('topic-grid');
    var sorted = INTERESTS.slice().sort(function (a, b) { return b.weight - a.weight; });
    var trendIcons = { up: '↑', down: '↓', stable: '→' };
    var trendColors = { up: 'var(--color-positive)', down: 'var(--color-negative)', stable: 'var(--color-warning)' };

    grid.innerHTML = sorted.map(function (topic) {
      return '<div class="topic-card" data-animate>' +
        '<div class="topic-card__header">' +
          '<span class="topic-card__name">' + topic.icon + ' ' + topic.name + '</span>' +
          '<span class="topic-card__badge">' + topic.weight + '%</span>' +
        '</div>' +
        '<div class="topic-card__bar-wrap">' +
          '<div class="topic-card__bar" style="width:' + topic.weight + '%"></div>' +
        '</div>' +
        '<div style="font-size:var(--text-xs);color:var(--color-text-secondary);margin-bottom:var(--space-xs);font-family:var(--font-mono)">' +
          'Trend: <span style="color:' + trendColors[topic.trend] + '">' + trendIcons[topic.trend] + ' ' + topic.trend + '</span>' +
        '</div>' +
        '<ul class="topic-card__recs">' +
          topic.recs.map(function (r) { return '<li class="topic-card__rec">' + r + '</li>'; }).join('') +
        '</ul>' +
      '</div>';
    }).join('');
  }

  /* ---------- Recommended Accounts ---------- */
  function renderRecommendedAccounts() {
    var grid = document.getElementById('recommend-grid');

    grid.innerHTML = RECOMMENDED_ACCOUNTS.map(function (acc) {
      return '<div class="recommend-card" data-animate>' +
        '<div class="recommend-card__top">' +
          '<div class="recommend-card__avatar">' + acc.avatar + '</div>' +
          '<div class="recommend-card__info">' +
            '<span class="recommend-card__name">' + acc.name + '</span>' +
            '<span class="recommend-card__handle">' + acc.handle + '</span>' +
          '</div>' +
        '</div>' +
        '<p class="recommend-card__reason">' + acc.reason + '</p>' +
        '<div class="recommend-card__tags">' +
          acc.tags.map(function (t) { return '<span class="recommend-card__tag">' + t + '</span>'; }).join('') +
        '</div>' +
      '</div>';
    }).join('');
  }

  /* ---------- Update Chart Colors on Theme Change ---------- */
  function updateChartColors() {
    if (radarChart) { radarChart.destroy(); renderRadarChart(); }
    if (trendChart) { trendChart.destroy(); renderTrendChart(); }
  }

  /* ---------- GSAP Animations — D5 opacity only ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    /* Hero elements fade in */
    gsap.from('.hero__eyebrow', { opacity: 0, duration: 0.6, ease: 'power2.out' });
    gsap.from('.hero__title', { opacity: 0, duration: 0.8, delay: 0.1, ease: 'power2.out' });
    gsap.from('.hero__subtitle', { opacity: 0, duration: 0.6, delay: 0.25, ease: 'power2.out' });
    gsap.from('.hero__chart-wrap', { opacity: 0, duration: 0.9, delay: 0.35, ease: 'power2.out' });

    /* KPI cards fade */
    gsap.from('.kpi-card', { opacity: 0, duration: 0.5, stagger: 0.1, delay: 0.5, ease: 'power2.out' });

    /* Sections — D5 opacity only */
    var sections = document.querySelectorAll('.section');
    sections.forEach(function (section) {
      var title = section.querySelector('.section__title');
      if (title) {
        gsap.from(title, {
          scrollTrigger: { trigger: section, start: 'top 80%', toggleActions: 'play none none none' },
          opacity: 0, duration: 0.6, ease: 'power2.out',
        });
      }

      var cards = section.querySelectorAll('[data-animate]');
      if (cards.length) {
        gsap.from(cards, {
          scrollTrigger: { trigger: section, start: 'top 75%', toggleActions: 'play none none none' },
          opacity: 0, duration: 0.5, stagger: 0.08, ease: 'power2.out',
        });
      }
    });

    gsap.from('.chart-container--line', {
      scrollTrigger: { trigger: '#section-trend', start: 'top 80%', toggleActions: 'play none none none' },
      opacity: 0, duration: 0.7, ease: 'power2.out',
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
      renderRadarChart();
      renderTopicCards();
      renderTrendChart();
      renderRecommendedAccounts();
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
