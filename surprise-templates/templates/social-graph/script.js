/* ============================================================
   Social Graph — script.js

   Pure frontend with built-in simulated social network data.
   Canvas network graph renders in full-bleed hero background.
   Stacked sections below for leaderboard, types, heatmap.

   Skeleton: A4 Full-bleed | Entry: D6 scale(1.05)→scale(1)
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

  /* ---------- Simulated Social Network Data ---------- */
  var CONNECTIONS = [
    { name: 'CryptoSage', handle: '@cryptosage', avatar: 'C', interactions: 342, type: 'mutual', category: 'core' },
    { name: 'DevBuilder', handle: '@devbuilder', avatar: 'D', interactions: 287, type: 'mutual', category: 'core' },
    { name: 'AIResearcher', handle: '@airesearcher', avatar: 'A', interactions: 256, type: 'mutual', category: 'core' },
    { name: 'DesignLead', handle: '@designlead', avatar: 'D', interactions: 198, type: 'mutual', category: 'core' },
    { name: 'StartupGuru', handle: '@startupguru', avatar: 'S', interactions: 176, type: 'following', category: 'active' },
    { name: 'DataNerd', handle: '@datanerd', avatar: 'D', interactions: 154, type: 'mutual', category: 'active' },
    { name: 'TechWriter', handle: '@techwriter', avatar: 'T', interactions: 132, type: 'following', category: 'active' },
    { name: 'ProductHunt', handle: '@producthunt', avatar: 'P', interactions: 118, type: 'following', category: 'active' },
    { name: 'OpenSourceFan', handle: '@opensourcefan', avatar: 'O', interactions: 95, type: 'mutual', category: 'casual' },
    { name: 'MarketWatch', handle: '@marketwatch', avatar: 'M', interactions: 87, type: 'following', category: 'casual' },
    { name: 'ScienceDaily', handle: '@sciencedaily', avatar: 'S', interactions: 72, type: 'following', category: 'casual' },
    { name: 'BookClub', handle: '@bookclub', avatar: 'B', interactions: 64, type: 'mutual', category: 'casual' },
    { name: 'FitnessCoach', handle: '@fitnesscoach', avatar: 'F', interactions: 48, type: 'following', category: 'peripheral' },
    { name: 'NewsBreaker', handle: '@newsbreaker', avatar: 'N', interactions: 41, type: 'following', category: 'peripheral' },
    { name: 'PhotoArtist', handle: '@photoartist', avatar: 'P', interactions: 35, type: 'mutual', category: 'peripheral' },
  ];

  var INTERACTION_TYPES = {
    replies: 38,
    retweets: 25,
    likes: 28,
    quotes: 9,
  };

  var HEATMAP_DATA = [
    { day: 'Mon', hours: [2,3,1,0,0,1,5,12,18,22,15,10,8,14,16,20,18,12,8,6,5,4,3,2] },
    { day: 'Tue', hours: [1,2,1,0,0,2,6,14,20,25,18,12,9,16,18,22,20,14,10,7,5,3,2,1] },
    { day: 'Wed', hours: [3,2,1,0,0,1,4,10,16,20,14,11,7,12,15,18,16,11,8,6,4,3,2,2] },
    { day: 'Thu', hours: [2,1,1,0,0,2,5,13,19,24,17,13,10,15,17,21,19,13,9,7,5,4,3,1] },
    { day: 'Fri', hours: [1,2,1,0,0,1,4,11,17,21,16,12,8,13,16,19,17,12,9,8,6,5,4,2] },
    { day: 'Sat', hours: [4,3,2,1,0,0,2,5,8,12,14,16,15,14,12,10,8,7,6,8,10,8,6,4] },
    { day: 'Sun', hours: [3,2,2,1,0,0,1,4,6,10,12,14,13,12,10,9,7,6,5,7,9,7,5,3] },
  ];

  var CATEGORY_COLORS = {
    core: '#10b981',
    active: '#34d399',
    casual: '#6ee7b7',
    peripheral: '#a7f3d0',
  };

  /* ---------- Theme Toggle ---------- */
  (function initTheme() {
    var toggle = document.getElementById('theme-toggle');
    var stored = localStorage.getItem('theme');
    if (stored === 'light') document.documentElement.setAttribute('data-theme', 'light');
    toggle.addEventListener('click', function () {
      var isLight = document.documentElement.getAttribute('data-theme') === 'light';
      document.documentElement.setAttribute('data-theme', isLight ? 'dark' : 'light');
      localStorage.setItem('theme', isLight ? 'dark' : 'light');
      updateChartColors();
      renderNetworkGraph();
      renderHeatmap();
    });
  })();

  /* ---------- Render KPIs ---------- */
  function renderKPIs() {
    var totalConnections = CONNECTIONS.length;
    var coreCount = CONNECTIONS.filter(function (c) { return c.category === 'core'; }).length;
    var totalInteractions = CONNECTIONS.reduce(function (s, c) { return s + c.interactions; }, 0);
    var influenceScore = Math.min(100, Math.round((totalInteractions / 20) + (coreCount * 5)));

    document.getElementById('kpi-network-size').textContent = totalConnections;
    document.getElementById('kpi-inner-circle').textContent = coreCount;
    document.getElementById('kpi-influence').textContent = influenceScore;

    document.querySelectorAll('.kpi-card').forEach(function (card) {
      card.classList.remove('skeleton');
    });
  }

  /* ---------- Canvas Network Graph (in hero) ---------- */
  function renderNetworkGraph() {
    var canvas = document.getElementById('network-canvas');
    var ctx = canvas.getContext('2d');
    var hero = canvas.parentElement;
    var rect = hero.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
    ctx.scale(dpr, dpr);

    var w = rect.width;
    var h = rect.height;
    var cx = w / 2;
    var cy = h / 2;
    var isDark = document.documentElement.getAttribute('data-theme') !== 'light';

    ctx.clearRect(0, 0, w, h);

    var centerRadius = 24;
    var rings = { core: 0.18, active: 0.30, casual: 0.42, peripheral: 0.56 };
    var nodes = [];

    var categoryGroups = {};
    CONNECTIONS.forEach(function (c) {
      if (!categoryGroups[c.category]) categoryGroups[c.category] = [];
      categoryGroups[c.category].push(c);
    });

    Object.keys(categoryGroups).forEach(function (cat) {
      var group = categoryGroups[cat];
      var ringRadius = Math.min(w, h) * rings[cat];
      group.forEach(function (conn, i) {
        var angle = (2 * Math.PI * i / group.length) - Math.PI / 2;
        var nodeRadius = Math.max(6, Math.min(16, conn.interactions / 25));
        nodes.push({
          x: cx + ringRadius * Math.cos(angle),
          y: cy + ringRadius * Math.sin(angle),
          radius: nodeRadius,
          color: CATEGORY_COLORS[cat],
          name: conn.name,
          interactions: conn.interactions,
          category: cat,
        });
      });
    });

    // Draw edges
    nodes.forEach(function (node) {
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(node.x, node.y);
      ctx.strokeStyle = isDark ? 'rgba(16,185,129,0.08)' : 'rgba(5,150,105,0.06)';
      ctx.lineWidth = Math.max(0.5, node.interactions / 200);
      ctx.stroke();
    });

    // Draw nodes
    nodes.forEach(function (node) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.radius + 3, 0, 2 * Math.PI);
      ctx.fillStyle = node.color + '15';
      ctx.fill();

      ctx.beginPath();
      ctx.arc(node.x, node.y, node.radius, 0, 2 * Math.PI);
      ctx.fillStyle = node.color;
      ctx.fill();

      ctx.fillStyle = isDark ? 'rgba(223,240,236,0.6)' : 'rgba(15,41,34,0.6)';
      ctx.font = '500 9px "Fira Code", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(node.name, node.x, node.y + node.radius + 12);
    });

    // Center node
    ctx.beginPath();
    ctx.arc(cx, cy, centerRadius + 5, 0, 2 * Math.PI);
    ctx.fillStyle = isDark ? 'rgba(16,185,129,0.12)' : 'rgba(5,150,105,0.10)';
    ctx.fill();

    ctx.beginPath();
    ctx.arc(cx, cy, centerRadius, 0, 2 * Math.PI);
    ctx.fillStyle = isDark ? '#10b981' : '#059669';
    ctx.fill();

    ctx.fillStyle = '#fff';
    ctx.font = 'bold 12px "Azeret Mono", monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('YOU', cx, cy);

    // Render legend
    var legendEl = document.getElementById('network-legend');
    legendEl.innerHTML = Object.keys(CATEGORY_COLORS).map(function (cat) {
      var count = (categoryGroups[cat] || []).length;
      return '<div class="network-legend__item">' +
        '<span class="network-legend__dot" style="background:' + CATEGORY_COLORS[cat] + '"></span>' +
        '<span>' + cat.charAt(0).toUpperCase() + cat.slice(1) + ' (' + count + ')</span>' +
      '</div>';
    }).join('');
  }

  /* ---------- Leaderboard ---------- */
  function renderLeaderboard() {
    var container = document.getElementById('leaderboard');
    var sorted = CONNECTIONS.slice().sort(function (a, b) { return b.interactions - a.interactions; });
    var top10 = sorted.slice(0, 10);
    var maxInteractions = top10[0].interactions;

    container.innerHTML = top10.map(function (conn, i) {
      var pct = Math.round((conn.interactions / maxInteractions) * 100);
      return '<div class="network-panel" data-animate>' +
        '<span class="network-panel__rank">#' + (i + 1) + '</span>' +
        '<div class="network-panel__avatar">' + conn.avatar + '</div>' +
        '<div class="network-panel__info">' +
          '<span class="network-panel__name">' + conn.name + '</span>' +
          '<span class="network-panel__handle">' + conn.handle + '</span>' +
        '</div>' +
        '<div class="network-panel__bar-wrap">' +
          '<div class="network-panel__bar-track">' +
            '<div class="network-panel__bar" style="width:' + pct + '%"></div>' +
          '</div>' +
          '<span class="network-panel__count">' + conn.interactions + '</span>' +
        '</div>' +
      '</div>';
    }).join('');
  }

  /* ---------- Interaction Types Doughnut ---------- */
  var typesChart = null;

  function renderTypesChart() {
    var wrap = document.getElementById('types-chart-wrap');
    var skeleton = wrap.querySelector('.skeleton-chart');
    if (skeleton) skeleton.remove();

    var ctx = document.getElementById('types-chart').getContext('2d');
    var isDark = document.documentElement.getAttribute('data-theme') !== 'light';

    var labels = Object.keys(INTERACTION_TYPES).map(function (k) {
      return k.charAt(0).toUpperCase() + k.slice(1);
    });
    var data = Object.values(INTERACTION_TYPES);
    var colors = ['#10b981', '#34d399', '#6ee7b7', '#a7f3d0'];

    typesChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: colors,
          borderColor: isDark ? '#0f1f1c' : '#f0fdf9',
          borderWidth: 3,
          hoverOffset: 8,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '60%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: isDark ? '#dff0ec' : '#0f2922',
              font: { family: "'Lexend', sans-serif", size: 12 },
              usePointStyle: true,
              pointStyle: 'circle',
              padding: 16,
            },
          },
          tooltip: {
            backgroundColor: isDark ? '#0f1f1c' : '#f0fdf9',
            titleColor: isDark ? '#dff0ec' : '#0f2922',
            bodyColor: isDark ? 'rgba(223,240,236,0.7)' : 'rgba(15,41,34,0.7)',
            borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
            borderWidth: 1,
            titleFont: { family: "'Azeret Mono', monospace", weight: 600 },
            bodyFont: { family: "'Fira Code', monospace" },
            padding: 12,
            callbacks: {
              label: function (ctx) { return ctx.label + ': ' + ctx.parsed + '%'; },
            },
          },
        },
      },
    });
  }

  /* ---------- Activity Heatmap ---------- */
  function renderHeatmap() {
    var wrap = document.getElementById('heatmap-wrap');
    var skeleton = wrap.querySelector('.skeleton-chart');
    if (skeleton) skeleton.remove();

    var heatmapEl = document.getElementById('heatmap');
    var isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    var maxVal = 0;
    HEATMAP_DATA.forEach(function (row) {
      row.hours.forEach(function (v) { if (v > maxVal) maxVal = v; });
    });

    var html = '';
    html += '<div class="heatmap__label"></div>';
    for (var h = 0; h < 24; h++) {
      html += '<div class="heatmap__hour-label">' + (h % 3 === 0 ? h + 'h' : '') + '</div>';
    }

    HEATMAP_DATA.forEach(function (row) {
      html += '<div class="heatmap__label">' + row.day + '</div>';
      row.hours.forEach(function (val) {
        var intensity = maxVal > 0 ? val / maxVal : 0;
        var bg;
        if (isDark) {
          bg = 'rgba(16,185,129,' + (0.05 + intensity * 0.85) + ')';
        } else {
          bg = 'rgba(5,150,105,' + (0.05 + intensity * 0.75) + ')';
        }
        html += '<div class="heatmap__cell" style="background:' + bg + '" title="' + row.day + ' ' + val + ' interactions"></div>';
      });
    });

    heatmapEl.innerHTML = html;
  }

  /* ---------- Update Chart Colors on Theme Change ---------- */
  function updateChartColors() {
    if (typesChart) { typesChart.destroy(); renderTypesChart(); }
  }

  /* ---------- GSAP Animations — D6 scale(1.05) → scale(1) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    /* Hero elements */
    gsap.from('.hero__eyebrow', { opacity: 0, duration: 0.6, ease: 'power2.out' });
    gsap.from('.hero__title', { scale: 1.05, opacity: 0, duration: 0.8, delay: 0.1, ease: 'power3.out' });
    gsap.from('.hero__subtitle', { scale: 1.05, opacity: 0, duration: 0.6, delay: 0.25, ease: 'power3.out' });
    gsap.from('.kpi-card', { scale: 1.05, opacity: 0, duration: 0.5, stagger: 0.1, delay: 0.4, ease: 'power3.out' });

    /* Sections — D6 scale entry */
    var sections = document.querySelectorAll('.section');
    sections.forEach(function (section) {
      var title = section.querySelector('.section__title');
      if (title) {
        gsap.from(title, {
          scrollTrigger: { trigger: section, start: 'top 80%', toggleActions: 'play none none none' },
          scale: 1.05, opacity: 0, duration: 0.6, ease: 'power3.out',
        });
      }

      var cards = section.querySelectorAll('[data-animate]');
      if (cards.length) {
        gsap.from(cards, {
          scrollTrigger: { trigger: section, start: 'top 75%', toggleActions: 'play none none none' },
          scale: 1.05, opacity: 0, duration: 0.5, stagger: 0.06, ease: 'power3.out',
        });
      }
    });

    gsap.from('.chart-container--doughnut', {
      scrollTrigger: { trigger: '#section-types', start: 'top 80%', toggleActions: 'play none none none' },
      scale: 1.05, opacity: 0, duration: 0.7, ease: 'power3.out',
    });

    gsap.from('.heatmap-wrap', {
      scrollTrigger: { trigger: '#section-heatmap', start: 'top 80%', toggleActions: 'play none none none' },
      scale: 1.05, opacity: 0, duration: 0.7, ease: 'power3.out',
    });
  }

  /* ---------- Resize Handler ---------- */
  var resizeTimer;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      renderNetworkGraph();
    }, 250);
  });

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
      renderNetworkGraph();
      renderLeaderboard();
      renderTypesChart();
      renderHeatmap();
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
