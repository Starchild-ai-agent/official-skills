/* ============================================================
   Event Tracker — script.js
   Mock data · GSAP 3 + ScrollTrigger
   ============================================================ */
(function () {
  'use strict';
  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var EVENT_TYPES = ['All', 'Conference', 'Hackathon', 'AMA', 'Launch', 'Meetup'];
  var now = new Date();
  var year = now.getFullYear();
  var month = now.getMonth();
  var d = now.getDate();
  var EVENTS = [
    { name: 'ETH Global Bangkok', date: new Date(year, month, d + 3), type: 'Hackathon', desc: '48-hour hackathon with $500K in prizes. Focus on DeFi and social protocols.' },
    { name: 'Solana Breakpoint', date: new Date(year, month, d + 7), type: 'Conference', desc: 'Annual Solana conference featuring ecosystem updates and developer workshops.' },
    { name: 'Vitalik AMA on Reddit', date: new Date(year, month, d + 2), type: 'AMA', desc: 'Ethereum co-founder discusses roadmap, danksharding, and account abstraction.' },
    { name: 'Uniswap V4 Launch', date: new Date(year, month, d + 10), type: 'Launch', desc: 'Major DEX upgrade with hooks architecture and singleton pool design.' },
    { name: 'DeFi Summit NYC', date: new Date(year, month, d + 14), type: 'Conference', desc: 'Two-day summit on institutional DeFi adoption and regulatory frameworks.' },
    { name: 'Chainlink SmartCon', date: new Date(year, month, d + 18), type: 'Conference', desc: 'Oracle network conference with CCIP updates and new data feed announcements.' },
    { name: 'Base Builder Hackathon', date: new Date(year, month, d + 5), type: 'Hackathon', desc: 'Build on Base L2 with mentorship from Coinbase engineers. $200K prizes.' },
    { name: 'Polygon zkEVM AMA', date: new Date(year, month, d + 1), type: 'AMA', desc: 'Technical deep-dive into Polygon zkEVM performance and upcoming upgrades.' },
    { name: 'Arbitrum Orbit Launch', date: new Date(year, month, d + 12), type: 'Launch', desc: 'New L3 framework launch enabling custom chain deployment on Arbitrum.' },
    { name: 'Web3 Builders Meetup SF', date: new Date(year, month, d + 6), type: 'Meetup', desc: 'Monthly meetup for Web3 developers in San Francisco. Networking and demos.' },
    { name: 'Cosmos Interchain Summit', date: new Date(year, month, d + 21), type: 'Conference', desc: 'IBC protocol updates and cross-chain communication standards.' },
    { name: 'Starknet Mainnet V2', date: new Date(year, month, d + 16), type: 'Launch', desc: 'Major network upgrade with improved throughput and reduced transaction costs.' }
  ];
  var activeFilter = 'All';
  var $ = function (sel) { return document.querySelector(sel); };

  function initTheme() {
    var saved = localStorage.getItem('event-tracker-theme');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  }
  initTheme();
  $('#theme-toggle').addEventListener('click', function () {
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
    localStorage.setItem('event-tracker-theme', isDark ? 'light' : 'dark');
  });

  function updateCountdown() {
    var sorted = EVENTS.filter(function (e) { return e.date > now; }).sort(function (a, b) { return a.date - b.date; });
    if (sorted.length === 0) return;
    var diff = sorted[0].date.getTime() - Date.now();
    if (diff <= 0) return;
    var days = Math.floor(diff / 86400000);
    var hours = Math.floor((diff % 86400000) / 3600000);
    var mins = Math.floor((diff % 3600000) / 60000);
    var secs = Math.floor((diff % 60000) / 1000);
    $('#cd-days').textContent = String(days).padStart(2, '0');
    $('#cd-hours').textContent = String(hours).padStart(2, '0');
    $('#cd-mins').textContent = String(mins).padStart(2, '0');
    $('#cd-secs').textContent = String(secs).padStart(2, '0');
  }

  function renderFilters() {
    var tabs = $('#filter-tabs');
    tabs.innerHTML = EVENT_TYPES.map(function (t) {
      return '<button class="filter-tab ' + (t === activeFilter ? 'active' : '') + '" data-type="' + t + '">' + t + '</button>';
    }).join('');
    tabs.querySelectorAll('.filter-tab').forEach(function (tab) {
      tab.addEventListener('click', function () {
        activeFilter = tab.dataset.type;
        renderFilters();
        renderEventList();
      });
    });
  }

  function renderCalendar() {
    var cal = $('#calendar');
    var firstDay = new Date(year, month, 1);
    var lastDay = new Date(year, month + 1, 0);
    var startDow = firstDay.getDay();
    var daysInMonth = lastDay.getDate();
    var monthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];
    var weekdays = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    var html = '<div class="calendar__header"><span class="calendar__month">' + monthNames[month] + ' ' + year + '</span></div>';
    html += '<div class="calendar__weekdays">' + weekdays.map(function (wd) { return '<div class="calendar__weekday">' + wd + '</div>'; }).join('') + '</div>';
    html += '<div class="calendar__days">';
    var prevDays = new Date(year, month, 0).getDate();
    for (var i = startDow - 1; i >= 0; i--) {
      html += '<div class="calendar__day calendar__day--other"><span class="calendar__day-number">' + (prevDays - i) + '</span></div>';
    }
    for (var dd = 1; dd <= daysInMonth; dd++) {
      var isToday = dd === now.getDate();
      var dayEvts = EVENTS.filter(function (e) { return e.date.getMonth() === month && e.date.getDate() === dd; });
      var evtHtml = dayEvts.slice(0, 2).map(function (e) { return '<span class="calendar__day-event">' + e.name + '</span>'; }).join('');
      html += '<div class="calendar__day ' + (isToday ? 'calendar__day--today' : '') + '"><span class="calendar__day-number">' + dd + '</span>' + evtHtml + '</div>';
    }
    var totalCells = startDow + daysInMonth;
    var remaining = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
    for (var r = 1; r <= remaining; r++) {
      html += '<div class="calendar__day calendar__day--other"><span class="calendar__day-number">' + r + '</span></div>';
    }
    html += '</div>';
    cal.innerHTML = html;
  }

  function renderEventList() {
    var items = activeFilter === 'All' ? EVENTS.slice() : EVENTS.filter(function (e) { return e.type === activeFilter; });
    items.sort(function (a, b) { return a.date - b.date; });
    var monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    var list = $('#event-list');
    list.innerHTML = items.map(function (item) {
      var diff = item.date.getTime() - Date.now();
      var daysLeft = Math.max(0, Math.ceil(diff / 86400000));
      var cdText = daysLeft === 0 ? 'Today' : daysLeft === 1 ? 'Tomorrow' : daysLeft + ' days left';
      return '<div class="event-item"><div class="event-item__date"><span class="event-item__date-month">' + monthNames[item.date.getMonth()] + '</span><span class="event-item__date-day">' + item.date.getDate() + '</span></div><div class="event-item__body"><div class="event-item__name">' + item.name + '</div><div class="event-item__desc">' + item.desc + '</div><div class="event-item__meta"><span class="event-item__tag">' + item.type + '</span><span class="event-item__countdown">' + cdText + '</span></div></div></div>';
    }).join('');
    if (!prefersReducedMotion) {
      gsap.from('.event-item', { clipPath: 'inset(0 100% 0 0)', opacity: 0, duration: 0.5, stagger: 0.05, ease: 'power3.out', clearProps: 'clipPath,opacity' });
    }
  }

  function initAnimations() {
    if (prefersReducedMotion) return;
    var heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl.from('.hero__label', { clipPath: 'inset(0 100% 0 0)', opacity: 0, duration: 0.6 })
      .from('.hero__title', { clipPath: 'inset(0 100% 0 0)', opacity: 0, duration: 0.7 }, '-=0.3')
      .from('.hero__subtitle', { clipPath: 'inset(0 100% 0 0)', opacity: 0, duration: 0.5 }, '-=0.3')
      .from('.countdown-unit', { clipPath: 'inset(0 100% 0 0)', opacity: 0, duration: 0.4, stagger: 0.08 }, '-=0.2');
    gsap.from('.calendar', {
      scrollTrigger: { trigger: '#calendar-section', start: 'top 80%', once: true },
      clipPath: 'inset(0 100% 0 0)', opacity: 0, duration: 0.8, ease: 'power3.out'
    });
  }

  function init() {
    renderFilters();
    renderCalendar();
    renderEventList();
    updateCountdown();
    setInterval(updateCountdown, 1000);
    initAnimations();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
