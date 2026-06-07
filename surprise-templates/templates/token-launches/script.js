/* ============================================================
   Token Launch Tracker — script.js
   Mock data · GSAP 3 + ScrollTrigger
   ============================================================ */
(function () {
  'use strict';
  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var now = new Date();
  var TYPES = ['All', 'IDO', 'IEO', 'Fair Launch', 'Private Sale'];

  var LAUNCHES = [
    { name: 'NeuralChain', date: new Date(now.getFullYear(), now.getMonth(), now.getDate() + 2), platform: 'Binance Launchpad', raise: '$15M', type: 'IEO', risk: 'low', chain: 'Ethereum' },
    { name: 'SolFi Protocol', date: new Date(now.getFullYear(), now.getMonth(), now.getDate() + 4), platform: 'Raydium AcceleRaytor', raise: '$3M', type: 'IDO', risk: 'medium', chain: 'Solana' },
    { name: 'ZkBridge', date: new Date(now.getFullYear(), now.getMonth(), now.getDate() + 6), platform: 'DAO Maker', raise: '$5M', type: 'IDO', risk: 'low', chain: 'zkSync' },
    { name: 'MetaVerse AI', date: new Date(now.getFullYear(), now.getMonth(), now.getDate() + 8), platform: 'Seedify', raise: '$2.5M', type: 'IDO', risk: 'high', chain: 'BNB Chain' },
    { name: 'DeFi Nexus', date: new Date(now.getFullYear(), now.getMonth(), now.getDate() + 3), platform: 'Uniswap', raise: 'N/A', type: 'Fair Launch', risk: 'high', chain: 'Ethereum' },
    { name: 'Orbit Protocol', date: new Date(now.getFullYear(), now.getMonth(), now.getDate() + 10), platform: 'Polkastarter', raise: '$4M', type: 'IDO', risk: 'medium', chain: 'Arbitrum' },
    { name: 'ChainGuard', date: new Date(now.getFullYear(), now.getMonth(), now.getDate() + 5), platform: 'Private', raise: '$8M', type: 'Private Sale', risk: 'low', chain: 'Ethereum' },
    { name: 'GameFi World', date: new Date(now.getFullYear(), now.getMonth(), now.getDate() + 12), platform: 'Bybit Launchpad', raise: '$10M', type: 'IEO', risk: 'medium', chain: 'Polygon' },
    { name: 'LiquidStake', date: new Date(now.getFullYear(), now.getMonth(), now.getDate() + 7), platform: 'Fjord Foundry', raise: '$1.5M', type: 'Fair Launch', risk: 'medium', chain: 'Ethereum' },
    { name: 'CrossPay', date: new Date(now.getFullYear(), now.getMonth(), now.getDate() + 15), platform: 'OKX Jumpstart', raise: '$12M', type: 'IEO', risk: 'low', chain: 'Ethereum' }
  ];

  var activeType = 'All';
  var sortBy = 'date';
  var $ = function (sel) { return document.querySelector(sel); };

  function initTheme() {
    var saved = localStorage.getItem('token-launches-theme');
    if (saved === 'light') document.documentElement.setAttribute('data-theme', 'light');
  }
  initTheme();
  $('#theme-toggle').addEventListener('click', function () {
    var isLight = document.documentElement.getAttribute('data-theme') === 'light';
    document.documentElement.setAttribute('data-theme', isLight ? '' : 'light');
    localStorage.setItem('token-launches-theme', isLight ? 'dark' : 'light');
  });

  function renderKPIs() {
    var el = $('#kpi-bar');
    var kpis = [
      { label: 'Upcoming', value: LAUNCHES.length },
      { label: 'This Week', value: LAUNCHES.filter(function (l) { var d = l.date - now; return d > 0 && d < 604800000; }).length },
      { label: 'Total Raise', value: '$61M+' },
      { label: 'Low Risk', value: LAUNCHES.filter(function (l) { return l.risk === 'low'; }).length }
    ];
    el.innerHTML = kpis.map(function (k) {
      return '<div class="kpi-item"><div class="kpi-item__value">' + k.value + '</div><div class="kpi-item__label">' + k.label + '</div></div>';
    }).join('');
  }

  function renderFilters() {
    var tabs = $('#filter-tabs');
    tabs.innerHTML = TYPES.map(function (t) {
      return '<button class="filter-tab ' + (t === activeType ? 'active' : '') + '" data-type="' + t + '">' + t + '</button>';
    }).join('');
    tabs.querySelectorAll('.filter-tab').forEach(function (tab) {
      tab.addEventListener('click', function () {
        activeType = tab.dataset.type;
        renderFilters();
        renderTable();
      });
    });
  }

  function renderTable() {
    var items = activeType === 'All' ? LAUNCHES.slice() : LAUNCHES.filter(function (l) { return l.type === activeType; });
    if (sortBy === 'raise') {
      items.sort(function (a, b) {
        var av = parseFloat(a.raise.replace(/[^0-9.]/g, '')) || 0;
        var bv = parseFloat(b.raise.replace(/[^0-9.]/g, '')) || 0;
        return bv - av;
      });
    } else if (sortBy === 'risk') {
      var order = { low: 0, medium: 1, high: 2 };
      items.sort(function (a, b) { return order[a.risk] - order[b.risk]; });
    } else {
      items.sort(function (a, b) { return a.date - b.date; });
    }

    var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    var table = $('#launch-table');
    var header = '<thead><tr><th>Project</th><th>Date</th><th>Platform</th><th>Raise</th><th>Type</th><th>Chain</th><th>Risk</th><th>Countdown</th></tr></thead>';
    var body = '<tbody>' + items.map(function (l) {
      var diff = l.date.getTime() - Date.now();
      var daysLeft = Math.max(0, Math.ceil(diff / 86400000));
      var cdText = daysLeft === 0 ? 'Today' : daysLeft + 'd';
      var dateStr = months[l.date.getMonth()] + ' ' + l.date.getDate();
      return '<tr><td class="project-name">' + l.name + '</td><td>' + dateStr + '</td><td>' + l.platform + '</td><td>' + l.raise + '</td><td><span class="type-badge">' + l.type + '</span></td><td>' + l.chain + '</td><td><span class="risk-badge risk-badge--' + l.risk + '">' + l.risk + '</span></td><td class="countdown">' + cdText + '</td></tr>';
    }).join('') + '</tbody>';
    table.innerHTML = header + body;

    if (!prefersReducedMotion) {
      gsap.from('.launch-table tbody tr', { scale: 0.95, opacity: 0, duration: 0.4, stagger: 0.04, ease: 'power3.out', clearProps: 'transform,opacity' });
    }
  }

  function initSort() {
    $('#sort-select').addEventListener('change', function (e) {
      sortBy = e.target.value;
      renderTable();
    });
  }

  function initAnimations() {
    if (prefersReducedMotion) return;
    var heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl.from('.hero__label', { scale: 0.95, opacity: 0, duration: 0.5 })
      .from('.hero__title', { scale: 0.95, opacity: 0, duration: 0.7 }, '-=0.3')
      .from('.hero__subtitle', { scale: 0.95, opacity: 0, duration: 0.5 }, '-=0.3')
      .from('.hero__kpi-bar', { scale: 0.95, opacity: 0, duration: 0.5 }, '-=0.2');
  }

  function init() {
    renderKPIs();
    renderFilters();
    renderTable();
    initSort();
    initAnimations();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
