/* ============================================================
   Crypto Events Calendar — script.js

   APIs: Built-in mock event data
   Animation: GSAP 3 + ScrollTrigger
   Entrance: D15 clip-path
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var $ = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel) { return document.querySelectorAll(sel); };

  var now = new Date();
  var currentYear = now.getFullYear();
  var currentMonth = now.getMonth();
  var viewYear = currentYear;
  var viewMonth = currentMonth;
  var currentFilter = 'all';

  var MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  var DAYS = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];

  var EVENTS = [
    { title: 'ETH Denver 2026', desc: 'Largest Ethereum hackathon and conference.', type: 'conference', date: new Date(currentYear, currentMonth, 8) },
    { title: 'Ethereum Pectra Upgrade', desc: 'Major protocol upgrade with EIP-7702.', type: 'upgrade', date: new Date(currentYear, currentMonth, 12) },
    { title: 'Uniswap Governance Vote #42', desc: 'Fee switch activation vote.', type: 'vote', date: new Date(currentYear, currentMonth, 15) },
    { title: 'Solana Breakpoint', desc: 'Annual Solana ecosystem conference.', type: 'conference', date: new Date(currentYear, currentMonth, 18) },
    { title: 'Arbitrum AMA', desc: 'Community AMA on Stylus and Orbit.', type: 'ama', date: new Date(currentYear, currentMonth, 20) },
    { title: 'Base V2 Launch', desc: 'Improved throughput and lower fees.', type: 'launch', date: new Date(currentYear, currentMonth, 22) },
    { title: 'MakerDAO Endgame Vote', desc: 'SubDAO structure governance vote.', type: 'vote', date: new Date(currentYear, currentMonth, 25) },
    { title: 'Polygon zkEVM Upgrade', desc: 'ZK proof system upgrade.', type: 'upgrade', date: new Date(currentYear, currentMonth, 28) },
    { title: 'Token2049 Singapore', desc: 'Premier crypto conference in Asia.', type: 'conference', date: new Date(currentYear, currentMonth + 1, 5) },
    { title: 'Chainlink CCIP V2', desc: 'Cross-chain protocol major release.', type: 'launch', date: new Date(currentYear, currentMonth + 1, 10) },
    { title: 'Aave V4 AMA', desc: 'Unified liquidity layer discussion.', type: 'ama', date: new Date(currentYear, currentMonth + 1, 14) },
    { title: 'OP Superchain Vote', desc: 'Revenue sharing model vote.', type: 'vote', date: new Date(currentYear, currentMonth + 1, 20) }
  ];

  function getFilteredEvents() {
    return EVENTS.filter(function (e) {
      return currentFilter === 'all' || e.type === currentFilter;
    }).sort(function (a, b) { return a.date - b.date; });
  }

  function getNextEvent() {
    var future = EVENTS.filter(function (e) { return e.date > now; })
      .sort(function (a, b) { return a.date - b.date; });
    return future[0] || null;
  }

  var countdownInterval = null;

  function updateCountdown() {
    var next = getNextEvent();
    if (!next) {
      $('#next-event-name').textContent = 'No upcoming events';
      return;
    }
    $('#next-event-name').textContent = next.title;

    function tick() {
      var diff = next.date - new Date();
      if (diff <= 0) diff = 0;
      var days = Math.floor(diff / 86400000);
      var hours = Math.floor((diff % 86400000) / 3600000);
      var mins = Math.floor((diff % 3600000) / 60000);
      var secs = Math.floor((diff % 60000) / 1000);
      $('#cd-days').textContent = String(days).padStart(2, '0');
      $('#cd-hours').textContent = String(hours).padStart(2, '0');
      $('#cd-mins').textContent = String(mins).padStart(2, '0');
      $('#cd-secs').textContent = String(secs).padStart(2, '0');
    }

    tick();
    if (countdownInterval) clearInterval(countdownInterval);
    countdownInterval = setInterval(tick, 1000);
  }

  function renderCalendar() {
    var grid = $('#calendar-grid');
    var firstDay = new Date(viewYear, viewMonth, 1).getDay();
    var daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
    var today = now.getDate();
    var isCurrentMonth = viewYear === currentYear && viewMonth === currentMonth;

    $('#cal-month-label').textContent = MONTHS[viewMonth] + ' ' + viewYear;

    var html = DAYS.map(function (d) {
      return '<div class="cal-day-header">' + d + '</div>';
    }).join('');

    var i;
    for (i = 0; i < firstDay; i++) {
      html += '<div class="cal-day cal-day--empty"></div>';
    }

    for (var day = 1; day <= daysInMonth; day++) {
      var isToday = isCurrentMonth && day === today;
      var dayEvents = EVENTS.filter(function (e) {
        return e.date.getFullYear() === viewYear && e.date.getMonth() === viewMonth && e.date.getDate() === day;
      });
      var dots = dayEvents.map(function (e) {
        return '<span class="cal-event-dot cal-event-dot--' + e.type + '" title="' + e.title + '"></span>';
      }).join('');

      html += '<div class="cal-day' + (isToday ? ' cal-day--today' : '') + '">' +
        '<div class="cal-day__number">' + day + '</div>' +
        '<div>' + dots + '</div></div>';
    }

    grid.innerHTML = html;

    if (!prefersReducedMotion) {
      gsap.fromTo('.cal-day:not(.cal-day--empty)',
        { opacity: 0, clipPath: 'inset(100% 0 0 0)' },
        { opacity: 1, clipPath: 'inset(0% 0 0 0)', duration: 0.3, stagger: 0.015, ease: 'power2.out' }
      );
    }
  }

  function renderEventsList() {
    var events = getFilteredEvents();
    var list = $('#events-list');

    list.innerHTML = events.map(function (e) {
      var day = e.date.getDate();
      var month = MONTHS[e.date.getMonth()].substring(0, 3);
      return '<div class="event-card" style="opacity:0">' +
        '<div class="event-card__date">' +
          '<span class="event-card__date-day">' + day + '</span>' +
          '<span class="event-card__date-month">' + month + '</span>' +
        '</div>' +
        '<div class="event-card__content">' +
          '<h3 class="event-card__title">' + e.title + '</h3>' +
          '<p class="event-card__desc">' + e.desc + '</p>' +
          '<div class="event-card__meta">' +
            '<span class="event-type-tag event-type-tag--' + e.type + '">' + e.type + '</span>' +
          '</div>' +
        '</div></div>';
    }).join('');

    if (!prefersReducedMotion) {
      gsap.fromTo('.event-card',
        { opacity: 0, clipPath: 'inset(0 100% 0 0)' },
        { opacity: 1, clipPath: 'inset(0 0% 0 0)', duration: 0.5, stagger: 0.08, ease: 'power2.out' }
      );
    } else {
      $$('.event-card').forEach(function (el) { el.style.opacity = '1'; });
    }
  }

  function initTheme() {
    var saved = localStorage.getItem('crypto-events-theme');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
    $('#theme-toggle').addEventListener('click', function () {
      var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
      localStorage.setItem('crypto-events-theme', isDark ? 'light' : 'dark');
    });
  }

  function initFilters() {
    $$('.filter-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        $$('.filter-btn').forEach(function (b) { b.classList.remove('filter-btn--active'); });
        btn.classList.add('filter-btn--active');
        currentFilter = btn.dataset.type;
        renderEventsList();
      });
    });
  }

  function initCalNav() {
    $('#cal-prev').addEventListener('click', function () {
      viewMonth--;
      if (viewMonth < 0) { viewMonth = 11; viewYear--; }
      renderCalendar();
    });
    $('#cal-next').addEventListener('click', function () {
      viewMonth++;
      if (viewMonth > 11) { viewMonth = 0; viewYear++; }
      renderCalendar();
    });
  }

  function initAnimations() {
    if (prefersReducedMotion) return;
    var heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl
      .from('.hero__label', { opacity: 0, y: 20, duration: 0.5 })
      .from('.hero__title', { opacity: 0, clipPath: 'inset(100% 0 0 0)', duration: 0.7 }, '-=0.2')
      .from('.countdown-unit', { opacity: 0, y: 20, duration: 0.4, stagger: 0.1 }, '-=0.3');
  }

  function init() {
    initTheme();
    updateCountdown();
    renderCalendar();
    renderEventsList();
    initFilters();
    initCalNav();
    initAnimations();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
