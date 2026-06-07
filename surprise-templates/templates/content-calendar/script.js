/* ============================================================
   Content Calendar — script.js

   Pure frontend with built-in simulated posting analysis data.
   Renders monthly calendar, best hours bar chart, content type
   suggestion cards (.schedule-card), and posting frequency.

   Skeleton: A13 Calendar | Entry: D15 clip-path inset
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
      if (raw.startsWith('{{')) return '@strategist';
      return raw;
    })(),
  };

  /* ---------- Simulated Data ---------- */
  var BEST_HOURS = [
    { hour: 0, rate: 1.2 }, { hour: 1, rate: 0.8 }, { hour: 2, rate: 0.5 },
    { hour: 3, rate: 0.3 }, { hour: 4, rate: 0.4 }, { hour: 5, rate: 0.9 },
    { hour: 6, rate: 2.1 }, { hour: 7, rate: 3.8 }, { hour: 8, rate: 5.2 },
    { hour: 9, rate: 6.8 }, { hour: 10, rate: 5.5 }, { hour: 11, rate: 4.3 },
    { hour: 12, rate: 5.9 }, { hour: 13, rate: 4.8 }, { hour: 14, rate: 3.6 },
    { hour: 15, rate: 3.2 }, { hour: 16, rate: 4.1 }, { hour: 17, rate: 5.7 },
    { hour: 18, rate: 6.4 }, { hour: 19, rate: 5.1 }, { hour: 20, rate: 4.5 },
    { hour: 21, rate: 3.8 }, { hour: 22, rate: 2.6 }, { hour: 23, rate: 1.8 },
  ];

  var CONTENT_TYPES = [
    { icon: '💬', name: 'Single Tweet', engagementRate: '4.2%', avgImpressions: '2.8K', desc: 'Short, punchy observations or hot takes. Best for quick engagement and starting conversations.', badge: 'Most Frequent' },
    { icon: '🧵', name: 'Thread', engagementRate: '7.8%', avgImpressions: '8.5K', desc: 'In-depth analysis or storytelling across multiple tweets. Highest engagement and shareability.', badge: 'Highest ROI' },
    { icon: '🖼️', name: 'Image Post', engagementRate: '5.6%', avgImpressions: '4.2K', desc: 'Visual content with infographics, screenshots, or photos. Strong for data visualization.', badge: 'Growing' },
    { icon: '🎬', name: 'Video', engagementRate: '6.1%', avgImpressions: '6.7K', desc: 'Short-form video content, tutorials, or commentary. Increasing algorithmic boost.', badge: 'Trending' },
  ];

  var FREQUENCY_DATA = {
    current: { daily: 1.2, weekly: 8, monthly: 35 },
    recommended: { daily: 2.5, weekly: 14, monthly: 60 },
    tips: [
      'Increase posting frequency by 40% to match your audience\'s consumption patterns.',
      'Focus additional posts during peak hours (9 AM and 6 PM) for maximum reach.',
      'Add 2-3 threads per week — they generate 3x more engagement than single tweets.',
    ],
  };

  var DAY_ENGAGEMENT = { 0: 'low', 1: 'medium', 2: 'high', 3: 'high', 4: 'medium', 5: 'low', 6: 'low' };
  var BEST_POST_TIMES = { 0: '10:00 AM', 1: '9:00 AM', 2: '9:00 AM', 3: '12:00 PM', 4: '6:00 PM', 5: '11:00 AM', 6: '10:00 AM' };

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

  /* ---------- Render KPIs ---------- */
  function renderKPIs() {
    var bestHour = BEST_HOURS.reduce(function (best, h) { return h.rate > best.rate ? h : best; });
    var bestTimeStr = (bestHour.hour === 0 ? 12 : (bestHour.hour > 12 ? bestHour.hour - 12 : bestHour.hour)) +
      ':00 ' + (bestHour.hour >= 12 ? 'PM' : 'AM');

    document.getElementById('kpi-best-time').textContent = bestTimeStr;
    document.getElementById('kpi-weekly-posts').textContent = FREQUENCY_DATA.recommended.weekly;
    document.getElementById('kpi-engagement').textContent = '5.4%';

    document.querySelectorAll('.kpi-card').forEach(function (card) {
      card.classList.remove('skeleton');
    });
  }

  /* ---------- Calendar State ---------- */
  var calendarState = {
    year: new Date().getFullYear(),
    month: new Date().getMonth(),
  };

  function renderCalendar() {
    var grid = document.getElementById('calendar-grid');
    var label = document.getElementById('cal-month-label');
    var months = ['January','February','March','April','May','June','July','August','September','October','November','December'];

    label.textContent = months[calendarState.month] + ' ' + calendarState.year;

    var firstDay = new Date(calendarState.year, calendarState.month, 1).getDay();
    var daysInMonth = new Date(calendarState.year, calendarState.month + 1, 0).getDate();

    var html = '';
    var dayNames = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    dayNames.forEach(function (d) {
      html += '<div class="calendar-grid__header">' + d + '</div>';
    });

    for (var e = 0; e < firstDay; e++) {
      html += '<div class="calendar-grid__cell calendar-grid__cell--empty"></div>';
    }

    for (var d = 1; d <= daysInMonth; d++) {
      var dow = new Date(calendarState.year, calendarState.month, d).getDay();
      var level = DAY_ENGAGEMENT[dow];
      var bestTime = BEST_POST_TIMES[dow];
      html += '<div class="calendar-grid__cell calendar-grid__cell--' + level + '" title="' + bestTime + '">' +
        '<span>' + d + '</span>' +
        (level === 'high' ? '<span class="calendar-grid__cell-time">' + bestTime + '</span>' : '') +
      '</div>';
    }

    grid.innerHTML = html;
  }

  document.getElementById('cal-prev').addEventListener('click', function () {
    calendarState.month--;
    if (calendarState.month < 0) { calendarState.month = 11; calendarState.year--; }
    renderCalendar();
  });

  document.getElementById('cal-next').addEventListener('click', function () {
    calendarState.month++;
    if (calendarState.month > 11) { calendarState.month = 0; calendarState.year++; }
    renderCalendar();
  });

  /* ---------- Best Hours Bar Chart ---------- */
  var hoursChart = null;

  function renderHoursChart() {
    var wrap = document.getElementById('hours-chart-wrap');
    var skeleton = wrap.querySelector('.skeleton-chart');
    if (skeleton) skeleton.remove();

    var ctx = document.getElementById('hours-chart').getContext('2d');
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    var maxRate = Math.max.apply(null, BEST_HOURS.map(function (h) { return h.rate; }));
    var barColors = BEST_HOURS.map(function (h) {
      var intensity = h.rate / maxRate;
      if (intensity > 0.7) return isDark ? '#f97316' : '#ea580c';
      if (intensity > 0.4) return isDark ? 'rgba(249,115,22,0.5)' : 'rgba(234,88,12,0.4)';
      return isDark ? 'rgba(249,115,22,0.2)' : 'rgba(234,88,12,0.15)';
    });

    hoursChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: BEST_HOURS.map(function (h) {
          return (h.hour === 0 ? '12' : (h.hour > 12 ? h.hour - 12 : h.hour)) + (h.hour >= 12 ? 'p' : 'a');
        }),
        datasets: [{
          label: 'Engagement Rate',
          data: BEST_HOURS.map(function (h) { return h.rate; }),
          backgroundColor: barColors,
          borderRadius: 4,
          borderSkipped: false,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            ticks: {
              color: isDark ? 'rgba(240,230,218,0.4)' : 'rgba(45,31,20,0.4)',
              font: { family: "'IBM Plex Mono', monospace", size: 10 },
            },
            grid: { display: false },
          },
          y: {
            beginAtZero: true,
            ticks: {
              color: isDark ? 'rgba(240,230,218,0.4)' : 'rgba(45,31,20,0.4)',
              font: { family: "'IBM Plex Mono', monospace", size: 10 },
              callback: function (v) { return v + '%'; },
            },
            grid: { color: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)' },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: isDark ? '#231c16' : '#fdf8f3',
            titleColor: isDark ? '#f0e6da' : '#2d1f14',
            bodyColor: isDark ? 'rgba(240,230,218,0.7)' : 'rgba(45,31,20,0.7)',
            borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
            borderWidth: 1,
            titleFont: { family: "'Lora', serif", weight: 600 },
            bodyFont: { family: "'IBM Plex Mono', monospace" },
            padding: 12,
            callbacks: {
              label: function (ctx) { return 'Engagement: ' + ctx.parsed.y + '%'; },
            },
          },
        },
      },
    });
  }

  /* ---------- Content Type Cards (schedule-card) ---------- */
  function renderContentTypes() {
    var grid = document.getElementById('type-grid');

    grid.innerHTML = CONTENT_TYPES.map(function (type) {
      return '<div class="schedule-card" data-animate>' +
        '<div class="schedule-card__icon">' + type.icon + '</div>' +
        '<div class="schedule-card__name">' + type.name + '</div>' +
        '<div class="schedule-card__stats">' +
          '<span>Eng: <span class="schedule-card__stat-value">' + type.engagementRate + '</span></span>' +
          '<span>Imp: <span class="schedule-card__stat-value">' + type.avgImpressions + '</span></span>' +
        '</div>' +
        '<p class="schedule-card__desc">' + type.desc + '</p>' +
        '<span class="schedule-card__badge">' + type.badge + '</span>' +
      '</div>';
    }).join('');
  }

  /* ---------- Frequency Analysis ---------- */
  function renderFrequency() {
    var wrap = document.getElementById('frequency-wrap');
    var skeleton = wrap.querySelector('.skeleton-chart');
    if (skeleton) skeleton.remove();

    var content = document.getElementById('frequency-content');
    var cur = FREQUENCY_DATA.current;
    var rec = FREQUENCY_DATA.recommended;

    var metrics = [
      { label: 'Daily', current: cur.daily, recommended: rec.daily, unit: 'posts/day' },
      { label: 'Weekly', current: cur.weekly, recommended: rec.weekly, unit: 'posts/week' },
      { label: 'Monthly', current: cur.monthly, recommended: rec.monthly, unit: 'posts/month' },
    ];

    var metersHtml = metrics.map(function (m) {
      var curPct = Math.round((m.current / m.recommended) * 100);
      return '<div class="frequency-meter">' +
        '<div class="frequency-meter__label">' +
          '<span>' + m.label + '</span>' +
          '<span>' + m.current + ' / ' + m.recommended + ' ' + m.unit + '</span>' +
        '</div>' +
        '<div class="frequency-meter__track">' +
          '<div class="frequency-meter__bar frequency-meter__bar--current" style="width:' + Math.min(curPct, 100) + '%"></div>' +
        '</div>' +
      '</div>';
    }).join('');

    var tipsHtml = FREQUENCY_DATA.tips.map(function (tip) {
      return '<div class="frequency-tip">' + tip + '</div>';
    }).join('');

    content.innerHTML =
      '<div class="frequency-col">' +
        '<div class="frequency-col__title">Current vs Recommended</div>' +
        metersHtml +
      '</div>' +
      '<div class="frequency-col">' +
        '<div class="frequency-col__title">Optimization Tips</div>' +
        tipsHtml +
      '</div>';
  }

  /* ---------- Update Chart Colors on Theme Change ---------- */
  function updateChartColors() {
    if (hoursChart) { hoursChart.destroy(); renderHoursChart(); }
  }

  /* ---------- GSAP Animations — D15 clip-path inset(10%) → inset(0) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    /* Hero elements */
    gsap.from('.hero__title', { opacity: 0, y: 20, duration: 0.6, ease: 'power3.out' });
    gsap.from('.hero__subtitle', { opacity: 0, duration: 0.5, delay: 0.15, ease: 'power2.out' });
    gsap.from('.kpi-card', { opacity: 0, duration: 0.4, stagger: 0.08, delay: 0.3, ease: 'power2.out' });

    /* Sections — D15 clip-path entry */
    var sections = document.querySelectorAll('.section');
    sections.forEach(function (section) {
      var title = section.querySelector('.section__title');
      if (title) {
        gsap.from(title, {
          scrollTrigger: { trigger: section, start: 'top 80%', toggleActions: 'play none none none' },
          clipPath: 'inset(10%)', opacity: 0, duration: 0.7, ease: 'power3.out',
        });
      }

      var cards = section.querySelectorAll('[data-animate]');
      if (cards.length) {
        gsap.from(cards, {
          scrollTrigger: { trigger: section, start: 'top 75%', toggleActions: 'play none none none' },
          clipPath: 'inset(10%)', opacity: 0, duration: 0.6, stagger: 0.08, ease: 'power3.out',
        });
      }
    });

    gsap.from('.calendar-grid', {
      scrollTrigger: { trigger: '#section-calendar', start: 'top 80%', toggleActions: 'play none none none' },
      clipPath: 'inset(10%)', opacity: 0, duration: 0.8, ease: 'power3.out',
    });

    gsap.from('.chart-container--bar', {
      scrollTrigger: { trigger: '#section-hours', start: 'top 80%', toggleActions: 'play none none none' },
      clipPath: 'inset(10%)', opacity: 0, duration: 0.7, ease: 'power3.out',
    });

    gsap.from('.frequency-wrap', {
      scrollTrigger: { trigger: '#section-frequency', start: 'top 80%', toggleActions: 'play none none none' },
      clipPath: 'inset(10%)', opacity: 0, duration: 0.7, ease: 'power3.out',
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
      renderCalendar();
      renderHoursChart();
      renderContentTypes();
      renderFrequency();
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
