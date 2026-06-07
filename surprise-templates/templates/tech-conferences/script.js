/* ============================================================
   Tech Conference Finder — script.js

   Skeleton: A13 Calendar
   Hover: C10 左侧边框
   Entrance: D15 clip-path
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Conference Data ---------- */
  var now = new Date();
  var year = now.getFullYear();
  var month = now.getMonth();

  var CONFERENCES = [
    { name: 'React Summit', date: new Date(year, month + 1, 14), location: 'Amsterdam, NL', type: 'offline', topics: ['web', 'ai'], tags: ['React', 'Frontend'] },
    { name: 'AI Dev World', date: new Date(year, month + 1, 22), location: 'Online', type: 'online', topics: ['ai'], tags: ['AI/ML', 'LLM'] },
    { name: 'KubeCon Europe', date: new Date(year, month + 2, 5), location: 'Paris, FR', type: 'offline', topics: ['devops'], tags: ['Kubernetes', 'DevOps'] },
    { name: 'JSConf', date: new Date(year, month + 2, 18), location: 'Berlin, DE', type: 'offline', topics: ['web'], tags: ['JavaScript', 'Web'] },
    { name: 'MLOps Summit', date: new Date(year, month + 1, 8), location: 'Online', type: 'online', topics: ['ai', 'devops'], tags: ['MLOps', 'AI'] },
    { name: 'DevOpsDays', date: new Date(year, month + 3, 2), location: 'London, UK', type: 'offline', topics: ['devops'], tags: ['DevOps', 'SRE'] },
    { name: 'Vue.js Live', date: new Date(year, month + 2, 25), location: 'Online', type: 'online', topics: ['web'], tags: ['Vue', 'Frontend'] },
    { name: 'PyCon', date: new Date(year, month + 3, 15), location: 'Pittsburgh, US', type: 'offline', topics: ['ai', 'web'], tags: ['Python', 'AI'] },
    { name: 'GraphQL Summit', date: new Date(year, month + 1, 28), location: 'San Francisco, US', type: 'offline', topics: ['web'], tags: ['GraphQL', 'API'] },
    { name: 'Cloud Native Day', date: new Date(year, month + 4, 10), location: 'Online', type: 'online', topics: ['devops'], tags: ['Cloud', 'CNCF'] },
  ];

  var currentFilter = 'all';
  var calYear = now.getFullYear();
  var calMonth = now.getMonth();

  /* ---------- Theme ---------- */
  var themeToggle = document.getElementById('theme-toggle');
  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('tc-theme', theme);
  }
  themeToggle.addEventListener('click', function () {
    var current = document.documentElement.getAttribute('data-theme') || 'light';
    setTheme(current === 'light' ? 'dark' : 'light');
  });
  var savedTheme = localStorage.getItem('tc-theme') ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  setTheme(savedTheme);

  /* ---------- Countdown ---------- */
  function getNextConference() {
    var future = CONFERENCES.filter(function (c) { return c.date > now; });
    future.sort(function (a, b) { return a.date - b.date; });
    return future[0] || null;
  }

  function updateCountdown() {
    var next = getNextConference();
    if (!next) {
      document.getElementById('cd-days').textContent = '00';
      document.getElementById('cd-hours').textContent = '00';
      document.getElementById('cd-mins').textContent = '00';
      document.getElementById('cd-secs').textContent = '00';
      return;
    }
    var diff = next.date.getTime() - Date.now();
    if (diff < 0) diff = 0;
    var days = Math.floor(diff / 86400000);
    var hours = Math.floor((diff % 86400000) / 3600000);
    var mins = Math.floor((diff % 3600000) / 60000);
    var secs = Math.floor((diff % 60000) / 1000);
    document.getElementById('cd-days').textContent = String(days).padStart(2, '0');
    document.getElementById('cd-hours').textContent = String(hours).padStart(2, '0');
    document.getElementById('cd-mins').textContent = String(mins).padStart(2, '0');
    document.getElementById('cd-secs').textContent = String(secs).padStart(2, '0');
  }
  updateCountdown();
  setInterval(updateCountdown, 1000);

  /* ---------- Filters ---------- */
  document.querySelectorAll('.filter-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.filter-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      currentFilter = btn.getAttribute('data-filter');
      renderConferences();
    });
  });

  function filterConferences() {
    if (currentFilter === 'all') return CONFERENCES;
    if (currentFilter === 'online') return CONFERENCES.filter(function (c) { return c.type === 'online'; });
    if (currentFilter === 'offline') return CONFERENCES.filter(function (c) { return c.type === 'offline'; });
    return CONFERENCES.filter(function (c) { return c.topics.indexOf(currentFilter) !== -1; });
  }

  /* ---------- Calendar ---------- */
  var MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

  function renderCalendar() {
    document.getElementById('cal-month').textContent = MONTH_NAMES[calMonth] + ' ' + calYear;
    var grid = document.getElementById('cal-grid');
    var firstDay = new Date(calYear, calMonth, 1).getDay();
    var daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
    var today = new Date();

    var eventDays = {};
    CONFERENCES.forEach(function (c) {
      if (c.date.getFullYear() === calYear && c.date.getMonth() === calMonth) {
        eventDays[c.date.getDate()] = true;
      }
    });

    var html = '';
    for (var i = 0; i < firstDay; i++) {
      html += '<div class="cal-day cal-day--other"></div>';
    }
    for (var d = 1; d <= daysInMonth; d++) {
      var classes = 'cal-day';
      if (d === today.getDate() && calMonth === today.getMonth() && calYear === today.getFullYear()) {
        classes += ' cal-day--today';
      }
      if (eventDays[d]) {
        classes += ' cal-day--event';
      }
      html += '<div class="' + classes + '">' + d + '</div>';
    }
    grid.innerHTML = html;
  }

  document.getElementById('cal-prev').addEventListener('click', function () {
    calMonth--;
    if (calMonth < 0) { calMonth = 11; calYear--; }
    renderCalendar();
  });
  document.getElementById('cal-next').addEventListener('click', function () {
    calMonth++;
    if (calMonth > 11) { calMonth = 0; calYear++; }
    renderCalendar();
  });

  /* ---------- Conference List ---------- */
  function renderConferences() {
    var list = document.getElementById('conf-list');
    var confs = filterConferences();
    confs.sort(function (a, b) { return a.date - b.date; });

    if (confs.length === 0) {
      list.innerHTML = '<p style="color:var(--color-text-muted)">No conferences match this filter</p>';
      return;
    }

    var html = '';
    confs.forEach(function (c) {
      var monthStr = MONTH_NAMES[c.date.getMonth()].substring(0, 3).toUpperCase();
      var dayStr = c.date.getDate();
      var typeClass = c.type === 'online' ? 'conf-card__tag--online' : 'conf-card__tag--offline';
      var typeLabel = c.type === 'online' ? 'Online' : 'In-Person';
      var tagsHtml = '<span class="conf-card__tag ' + typeClass + '">' + typeLabel + '</span>';
      c.tags.forEach(function (t) {
        tagsHtml += '<span class="conf-card__tag">' + t + '</span>';
      });

      html += '<div class="conf-card">' +
        '<div class="conf-card__date">' +
        '<span class="conf-card__date-month">' + monthStr + '</span>' +
        '<span class="conf-card__date-day">' + dayStr + '</span>' +
        '</div>' +
        '<div class="conf-card__info">' +
        '<div class="conf-card__name">' + c.name + '</div>' +
        '<div class="conf-card__location">' + c.location + '</div>' +
        '<div class="conf-card__tags">' + tagsHtml + '</div>' +
        '</div></div>';
    });
    list.innerHTML = html;

    if (!prefersReducedMotion) {
      gsap.utils.toArray('.conf-card').forEach(function (el, i) {
        gsap.from(el, {
          scrollTrigger: { trigger: el, start: 'top 90%', toggleActions: 'play none none none' },
          clipPath: 'inset(0 100% 0 0)', opacity: 0, duration: 0.6, delay: i * 0.06, ease: 'power2.out',
        });
      });
    }
  }

  /* ---------- GSAP Animations (D15 clip-path) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    gsap.from('.hero__label', { opacity: 0, y: 15, duration: 0.5, ease: 'power3.out' });
    gsap.from('.hero__countdown', { opacity: 0, clipPath: 'inset(0 100% 0 0)', duration: 0.8, delay: 0.15, ease: 'power2.out' });
    gsap.from('.hero__title', { opacity: 0, y: 20, duration: 0.6, delay: 0.3, ease: 'power3.out' });
    gsap.from('.hero__subtitle', { opacity: 0, y: 15, duration: 0.5, delay: 0.4, ease: 'power3.out' });

    gsap.from('.filters', {
      scrollTrigger: { trigger: '.filters', start: 'top 90%' },
      opacity: 0, clipPath: 'inset(0 100% 0 0)', duration: 0.7, ease: 'power2.out',
    });

    gsap.from('.calendar', {
      scrollTrigger: { trigger: '.calendar', start: 'top 85%' },
      opacity: 0, clipPath: 'inset(0 0 100% 0)', duration: 0.8, ease: 'power2.out',
    });

    gsap.utils.toArray('.section__title').forEach(function (el) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 88%' },
        opacity: 0, clipPath: 'inset(0 100% 0 0)', duration: 0.6, ease: 'power3.out',
      });
    });
  }

  /* ---------- Init ---------- */
  renderCalendar();
  renderConferences();
  initAnimations();

})();
