/* ============================================================
   ICO/IDO Calendar — script.js
   Skeleton: A13 Calendar · Hover: C10 左侧边框
   Entrance: D15 clip-path · Hero: H13 Countdown
   ============================================================ */
(function () {
  'use strict';
  var $ = function (s) { return document.querySelector(s); };
  var $$ = function (s) { return document.querySelectorAll(s); };

  /* ---------- Mock Data ---------- */
  var now = new Date();
  var y = now.getFullYear();
  var m = now.getMonth();

  var PROJECTS = [
    { name: 'NexaChain', type: 'ico', date: new Date(y, m, 15), platform: 'Ethereum', raise: '$2.5M', risk: 'low', desc: 'Layer-2 scaling solution' },
    { name: 'MetaVault', type: 'ido', date: new Date(y, m, 18), platform: 'BSC', raise: '$800K', risk: 'med', desc: 'DeFi yield aggregator' },
    { name: 'PixelRealm', type: 'ino', date: new Date(y, m, 22), platform: 'Solana', raise: '$1.2M', risk: 'low', desc: 'NFT gaming metaverse' },
    { name: 'ZeroGas', type: 'ico', date: new Date(y, m, 28), platform: 'Polygon', raise: '$5M', risk: 'med', desc: 'Gasless transaction protocol' },
    { name: 'AuraFi', type: 'ido', date: new Date(y, m + 1, 3), platform: 'Arbitrum', raise: '$1.5M', risk: 'high', desc: 'AI-powered trading bot' },
    { name: 'ChainGuard', type: 'ico', date: new Date(y, m + 1, 8), platform: 'Ethereum', raise: '$3M', risk: 'low', desc: 'Smart contract security' },
    { name: 'DataMesh', type: 'ido', date: new Date(y, m + 1, 14), platform: 'Avalanche', raise: '$2M', risk: 'med', desc: 'Decentralized data marketplace' },
    { name: 'SynthWave', type: 'ino', date: new Date(y, m + 1, 20), platform: 'Solana', raise: '$600K', risk: 'high', desc: 'Music NFT platform' },
    { name: 'OmniDEX', type: 'ido', date: new Date(y, m + 1, 25), platform: 'Optimism', raise: '$4M', risk: 'low', desc: 'Cross-chain DEX aggregator' },
    { name: 'VaultX', type: 'ico', date: new Date(y, m + 2, 5), platform: 'Ethereum', raise: '$10M', risk: 'low', desc: 'Institutional custody solution' }
  ];

  var currentMonth = m;
  var currentYear = y;
  var currentFilter = 'all';

  /* ---------- Theme ---------- */
  var savedTheme = localStorage.getItem('ic_theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  $('#themeToggle').addEventListener('click', function () {
    var cur = document.documentElement.getAttribute('data-theme');
    var nxt = cur === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', nxt);
    localStorage.setItem('ic_theme', nxt);
  });

  /* ---------- Countdown ---------- */
  function updateCountdown() {
    var future = PROJECTS.filter(function (p) { return p.date > new Date(); })
      .sort(function (a, b) { return a.date - b.date; });
    if (future.length === 0) return;
    var target = future[0].date.getTime();
    var diff = target - Date.now();
    if (diff < 0) diff = 0;
    var d = Math.floor(diff / 86400000);
    var h = Math.floor((diff % 86400000) / 3600000);
    var mn = Math.floor((diff % 3600000) / 60000);
    var s = Math.floor((diff % 60000) / 1000);
    $('#cdDays').textContent = String(d).padStart(2, '0');
    $('#cdHours').textContent = String(h).padStart(2, '0');
    $('#cdMins').textContent = String(mn).padStart(2, '0');
    $('#cdSecs').textContent = String(s).padStart(2, '0');
  }
  setInterval(updateCountdown, 1000);
  updateCountdown();

  /* ---------- Calendar ---------- */
  function renderCalendar() {
    var cal = $('#calendar');
    var days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    var html = days.map(function (d) { return '<div class="cal-header">' + d + '</div>'; }).join('');

    var firstDay = new Date(currentYear, currentMonth, 1).getDay();
    var daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
    var today = new Date();

    for (var i = 0; i < firstDay; i++) html += '<div class="cal-day cal-day--empty"></div>';

    for (var d = 1; d <= daysInMonth; d++) {
      var isToday = d === today.getDate() && currentMonth === today.getMonth() && currentYear === today.getFullYear();
      var cls = 'cal-day' + (isToday ? ' cal-day--today' : '');
      var dots = '';
      PROJECTS.forEach(function (p) {
        if (p.date.getDate() === d && p.date.getMonth() === currentMonth && p.date.getFullYear() === currentYear) {
          dots += '<div class="cal-day__dot cal-day__dot--' + p.type + '" title="' + p.name + '"></div>';
        }
      });
      html += '<div class="' + cls + '"><span class="cal-day__num">' + d + '</span>' + dots + '</div>';
    }

    cal.innerHTML = html;
    var monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    $('#calMonth').textContent = monthNames[currentMonth] + ' ' + currentYear;
  }

  $('#prevMonth').addEventListener('click', function () {
    currentMonth--;
    if (currentMonth < 0) { currentMonth = 11; currentYear--; }
    renderCalendar();
  });
  $('#nextMonth').addEventListener('click', function () {
    currentMonth++;
    if (currentMonth > 11) { currentMonth = 0; currentYear++; }
    renderCalendar();
  });

  /* ---------- Project List ---------- */
  function renderProjects() {
    var list = $('#projectList');
    var filtered = currentFilter === 'all' ? PROJECTS : PROJECTS.filter(function (p) { return p.type === currentFilter; });
    filtered.sort(function (a, b) { return a.date - b.date; });

    list.innerHTML = filtered.map(function (p) {
      var dateStr = p.date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
      return '<div class="project-card">' +
        '<div class="project-card__header">' +
          '<span class="project-card__name">' + p.name + '</span>' +
          '<span class="project-card__type project-card__type--' + p.type + '">' + p.type.toUpperCase() + '</span>' +
        '</div>' +
        '<div class="project-card__meta">' +
          '<div class="project-card__meta-item"><span class="project-card__meta-label">Date</span><span class="project-card__meta-value">' + dateStr + '</span></div>' +
          '<div class="project-card__meta-item"><span class="project-card__meta-label">Platform</span><span class="project-card__meta-value">' + p.platform + '</span></div>' +
          '<div class="project-card__meta-item"><span class="project-card__meta-label">Raise</span><span class="project-card__meta-value">' + p.raise + '</span></div>' +
          '<div class="project-card__meta-item"><span class="project-card__meta-label">Risk</span><span class="project-card__meta-value risk-' + p.risk + '">' + p.risk.toUpperCase() + '</span></div>' +
        '</div>' +
      '</div>';
    }).join('');
  }

  $$('.filter-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      $$('.filter-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      currentFilter = btn.dataset.filter;
      renderProjects();
    });
  });

  /* ---------- Init ---------- */
  renderCalendar();
  renderProjects();

  /* ---------- GSAP ---------- */
  if (typeof gsap !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
    var mm = gsap.matchMedia();
    mm.add('(prefers-reduced-motion: no-preference)', function () {
      gsap.from('.hero', { clipPath: 'inset(0 100% 0 0)', opacity: 0, duration: 0.8, ease: 'power2.out' });
      gsap.from('.countdown', { clipPath: 'inset(0 100% 0 0)', opacity: 0, duration: 0.6, delay: 0.3, ease: 'power2.out' });
      gsap.from('.calendar-section', {
        clipPath: 'inset(0 100% 0 0)', opacity: 0, duration: 0.7, ease: 'power2.out',
        scrollTrigger: { trigger: '.calendar-section', start: 'top 85%' }
      });
      gsap.from('.project-card', {
        clipPath: 'inset(0 100% 0 0)', opacity: 0, duration: 0.5, stagger: 0.08, ease: 'power2.out',
        scrollTrigger: { trigger: '.projects', start: 'top 85%' }
      });
    });
  }
})();
