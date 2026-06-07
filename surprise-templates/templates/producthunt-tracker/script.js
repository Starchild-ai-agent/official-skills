/* ============================================================
   Product Hunt Tracker — script.js

   Skeleton: A12 Masonry Grid
   Hover: C9 box-shadow
   Entrance: D1 translateY(40px)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Mock Data ---------- */
  var PRODUCTS = [
    { rank: 1, name: 'CodePilot AI', desc: 'AI-powered code review assistant that catches bugs before they ship. Integrates with GitHub and GitLab.', votes: 847, category: 'devtools', tags: ['AI', 'Developer Tools'] },
    { rank: 2, name: 'DesignSync', desc: 'Real-time design collaboration platform with version control for Figma files.', votes: 623, category: 'design', tags: ['Design', 'Collaboration'] },
    { rank: 3, name: 'MetricFlow', desc: 'Open-source metrics layer that transforms your data warehouse into a semantic layer.', votes: 512, category: 'saas', tags: ['Analytics', 'SaaS'] },
    { rank: 4, name: 'PromptForge', desc: 'Build, test, and version control your AI prompts with A/B testing and analytics.', votes: 489, category: 'ai', tags: ['AI', 'Prompts'] },
    { rank: 5, name: 'TaskZen', desc: 'Minimalist task manager with AI-powered prioritization and focus mode.', votes: 445, category: 'productivity', tags: ['Productivity', 'AI'] },
    { rank: 6, name: 'APIShield', desc: 'Automated API security testing that runs in your CI/CD pipeline. Finds vulnerabilities before deployment.', votes: 398, category: 'devtools', tags: ['Security', 'API'] },
    { rank: 7, name: 'ColorMind', desc: 'AI color palette generator that understands brand psychology and accessibility requirements.', votes: 367, category: 'design', tags: ['Design', 'AI'] },
    { rank: 8, name: 'DataPipe', desc: 'No-code ETL platform for startups. Connect any data source in minutes.', votes: 334, category: 'saas', tags: ['Data', 'No-Code'] },
    { rank: 9, name: 'VoiceNote AI', desc: 'Transform voice memos into structured notes with action items and calendar events.', votes: 312, category: 'ai', tags: ['AI', 'Notes'] },
    { rank: 10, name: 'GitFlow Pro', desc: 'Visual Git workflow manager with automated branch policies and merge conflict prevention.', votes: 289, category: 'devtools', tags: ['Git', 'Developer Tools'] },
    { rank: 11, name: 'FocusBlock', desc: 'Website blocker that adapts to your work patterns using machine learning.', votes: 256, category: 'productivity', tags: ['Productivity', 'ML'] },
    { rank: 12, name: 'PixelPerfect', desc: 'Automated visual regression testing for web apps. Catches UI bugs across browsers.', votes: 234, category: 'devtools', tags: ['Testing', 'QA'] },
  ];

  var TREND_DATA = {
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    devtools: [12, 15, 8, 22, 18, 10, 14],
    ai: [8, 12, 18, 14, 25, 20, 16],
    saas: [6, 9, 11, 8, 12, 7, 10],
    design: [4, 7, 5, 9, 6, 8, 5],
    productivity: [3, 5, 7, 4, 8, 6, 4],
  };

  var currentFilter = 'all';
  var trendChart = null;

  /* ---------- Theme ---------- */
  var themeToggle = document.getElementById('theme-toggle');
  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('pht-theme', theme);
    if (trendChart) updateChartColors();
  }
  themeToggle.addEventListener('click', function () {
    var current = document.documentElement.getAttribute('data-theme') || 'light';
    setTheme(current === 'light' ? 'dark' : 'light');
  });
  var savedTheme = localStorage.getItem('pht-theme') ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  setTheme(savedTheme);

  /* ---------- Filters ---------- */
  document.querySelectorAll('.filter-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.filter-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      currentFilter = btn.getAttribute('data-filter');
      renderProducts();
    });
  });

  /* ---------- Trend Chart ---------- */
  function initChart() {
    var ctx = document.getElementById('trend-chart').getContext('2d');
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';
    var labelColor = isDark ? 'rgba(226,232,240,0.5)' : 'rgba(15,23,42,0.5)';

    trendChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: TREND_DATA.labels,
        datasets: [
          { label: 'Dev Tools', data: TREND_DATA.devtools, borderColor: '#f43f5e', backgroundColor: 'rgba(244,63,94,0.1)', tension: 0.4, fill: true },
          { label: 'AI', data: TREND_DATA.ai, borderColor: '#8b5cf6', backgroundColor: 'rgba(139,92,246,0.05)', tension: 0.4, fill: false },
          { label: 'SaaS', data: TREND_DATA.saas, borderColor: '#06b6d4', backgroundColor: 'rgba(6,182,212,0.05)', tension: 0.4, fill: false },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: labelColor, font: { family: "'Figtree', sans-serif", size: 11 } } },
        },
        scales: {
          x: { grid: { color: gridColor }, ticks: { color: labelColor, font: { family: "'IBM Plex Mono', monospace", size: 10 } } },
          y: { grid: { color: gridColor }, ticks: { color: labelColor, font: { family: "'IBM Plex Mono', monospace", size: 10 } } },
        },
      },
    });
  }

  function updateChartColors() {
    if (!trendChart) return;
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';
    var labelColor = isDark ? 'rgba(226,232,240,0.5)' : 'rgba(15,23,42,0.5)';
    trendChart.options.scales.x.grid.color = gridColor;
    trendChart.options.scales.y.grid.color = gridColor;
    trendChart.options.scales.x.ticks.color = labelColor;
    trendChart.options.scales.y.ticks.color = labelColor;
    trendChart.options.plugins.legend.labels.color = labelColor;
    trendChart.update();
  }

  /* ---------- Render Products ---------- */
  function renderProducts() {
    var grid = document.getElementById('product-grid');
    var products = currentFilter === 'all' ? PRODUCTS : PRODUCTS.filter(function (p) { return p.category === currentFilter; });

    var html = '';
    products.forEach(function (p) {
      var tagsHtml = p.tags.map(function (t) {
        return '<span class="product-card__tag">' + t + '</span>';
      }).join('');

      html += '<div class="product-card">' +
        '<div class="product-card__rank">#' + p.rank + '</div>' +
        '<div class="product-card__name">' + p.name + '</div>' +
        '<div class="product-card__desc">' + p.desc + '</div>' +
        '<div class="product-card__votes">\u25B2 ' + p.votes + '</div>' +
        '<div class="product-card__tags">' + tagsHtml + '</div>' +
        '</div>';
    });
    grid.innerHTML = html;

    if (!prefersReducedMotion) {
      gsap.utils.toArray('.product-card').forEach(function (el, i) {
        gsap.from(el, {
          scrollTrigger: { trigger: el, start: 'top 92%', toggleActions: 'play none none none' },
          opacity: 0, y: 40, duration: 0.5, delay: i * 0.05, ease: 'power2.out',
        });
      });
    }
  }

  /* ---------- GSAP Animations (D1 translateY(40px)) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    gsap.from('.hero__title', { opacity: 0, y: 40, duration: 0.7, ease: 'power3.out' });
    gsap.from('.hero__subtitle', { opacity: 0, y: 30, duration: 0.6, delay: 0.1, ease: 'power3.out' });
    gsap.from('.hero__stats', { opacity: 0, y: 40, duration: 0.6, delay: 0.2, ease: 'power2.out' });
    gsap.from('.filters', { opacity: 0, y: 20, duration: 0.5, delay: 0.3, ease: 'power2.out' });

    gsap.from('.chart-wrapper', {
      scrollTrigger: { trigger: '.chart-wrapper', start: 'top 85%' },
      opacity: 0, y: 40, duration: 0.7, ease: 'power2.out',
    });

    gsap.utils.toArray('.section__title').forEach(function (el) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 88%' },
        opacity: 0, y: 30, duration: 0.6, ease: 'power3.out',
      });
    });
  }

  /* ---------- Init ---------- */
  initChart();
  renderProducts();
  initAnimations();

})();
