/* ============================================================
   Tech Product Launch Feed — script.js
   Mock data · GSAP 3 + ScrollTrigger
   ============================================================ */
(function () {
  'use strict';
  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var CATS = ['All', 'AI', 'Developer Tools', 'SaaS', 'Design', 'Productivity', 'Crypto'];
  var PRODUCTS = [
    { name: 'CodePilot Pro', desc: 'AI-powered code review assistant that catches bugs before they ship. Integrates with GitHub, GitLab, and Bitbucket.', source: 'ph', tags: ['AI', 'Developer Tools'], votes: 842, comments: 156 },
    { name: 'DesignSync', desc: 'Real-time design collaboration platform. Think Figma meets Notion for design systems.', source: 'ph', tags: ['Design', 'SaaS'], votes: 634, comments: 89 },
    { name: 'TerminalAI', desc: 'Natural language terminal. Describe what you want in English, get the exact command.', source: 'hn', tags: ['AI', 'Developer Tools'], votes: 523, comments: 234 },
    { name: 'MetricFlow', desc: 'Open-source metrics layer for data teams. Define metrics once, use everywhere.', source: 'hn', tags: ['Developer Tools', 'SaaS'], votes: 412, comments: 178 },
    { name: 'FocusMode', desc: 'Distraction blocker that learns your work patterns. Blocks sites during deep work, allows during breaks.', source: 'ph', tags: ['Productivity'], votes: 389, comments: 67 },
    { name: 'ChainDeploy', desc: 'One-click smart contract deployment across 20+ chains. Built-in testing and verification.', source: 'ph', tags: ['Crypto', 'Developer Tools'], votes: 356, comments: 92 },
    { name: 'VoiceNotes AI', desc: 'Record meetings, get structured notes with action items. Supports 40+ languages.', source: 'ph', tags: ['AI', 'Productivity'], votes: 298, comments: 54 },
    { name: 'APIForge', desc: 'Generate production-ready APIs from natural language descriptions. Includes auth, rate limiting, and docs.', source: 'hn', tags: ['AI', 'Developer Tools'], votes: 267, comments: 145 },
    { name: 'PixelPerfect', desc: 'Automated visual regression testing for web apps. Catches CSS bugs across browsers.', source: 'ph', tags: ['Developer Tools', 'Design'], votes: 234, comments: 43 },
    { name: 'DataVault', desc: 'End-to-end encrypted data warehouse. SOC2 compliant out of the box.', source: 'hn', tags: ['SaaS', 'Developer Tools'], votes: 198, comments: 87 },
    { name: 'TokenTracker', desc: 'Portfolio tracking with DeFi position aggregation. Supports 50+ protocols across 10 chains.', source: 'ph', tags: ['Crypto'], votes: 187, comments: 38 },
    { name: 'WriterBot', desc: 'AI writing assistant trained on your brand voice. Generates blog posts, emails, and social content.', source: 'ph', tags: ['AI', 'Productivity'], votes: 176, comments: 29 },
    { name: 'GitInsights', desc: 'Engineering analytics dashboard. Track velocity, code quality, and team health metrics.', source: 'hn', tags: ['Developer Tools', 'SaaS'], votes: 165, comments: 112 },
    { name: 'ColorScale', desc: 'AI-powered color palette generator for design systems. Ensures WCAG accessibility compliance.', source: 'ph', tags: ['Design', 'AI'], votes: 154, comments: 22 },
    { name: 'BridgeKit', desc: 'Cross-chain bridge SDK for developers. Add bridging to your dApp in 10 lines of code.', source: 'hn', tags: ['Crypto', 'Developer Tools'], votes: 143, comments: 67 },
    { name: 'ScheduleAI', desc: 'AI scheduling assistant that negotiates meeting times via email. No more back-and-forth.', source: 'ph', tags: ['AI', 'Productivity'], votes: 132, comments: 18 },
    { name: 'InfraWatch', desc: 'Real-time infrastructure monitoring with AI anomaly detection. Replaces 5 monitoring tools.', source: 'hn', tags: ['Developer Tools', 'SaaS'], votes: 121, comments: 56 },
    { name: 'MockupMagic', desc: 'Generate product mockups from screenshots. 200+ device frames and backgrounds.', source: 'ph', tags: ['Design'], votes: 98, comments: 15 }
  ];
  var activeFilter = 'All';
  var $ = function (s) { return document.querySelector(s); };
  function initTheme() {
    var saved = localStorage.getItem('tech-launches-theme');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  }
  initTheme();
  $('#theme-toggle').addEventListener('click', function () {
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
    localStorage.setItem('tech-launches-theme', isDark ? 'light' : 'dark');
  });
  function renderFilters() {
    var el = $('#filter-tabs');
    el.innerHTML = CATS.map(function (c) {
      return '<button class="filter-tab ' + (c === activeFilter ? 'active' : '') + '" data-cat="' + c + '">' + c + '</button>';
    }).join('');
    el.querySelectorAll('.filter-tab').forEach(function (tab) {
      tab.addEventListener('click', function () { activeFilter = tab.dataset.cat; renderFilters(); renderProducts(); });
    });
  }
  function renderProducts() {
    var items = activeFilter === 'All' ? PRODUCTS : PRODUCTS.filter(function (p) { return p.tags.indexOf(activeFilter) !== -1; });
    var grid = $('#product-grid');
    grid.innerHTML = items.map(function (p) {
      var srcClass = p.source === 'ph' ? 'product-card__source--ph' : 'product-card__source--hn';
      var srcLabel = p.source === 'ph' ? 'PH' : 'HN';
      return '<div class="product-card"><div class="product-card__header"><span class="product-card__name">' + p.name + '</span><span class="product-card__source ' + srcClass + '">' + srcLabel + '</span></div><div class="product-card__desc">' + p.desc + '</div><div class="product-card__tags">' + p.tags.map(function (t) { return '<span class="product-card__tag">' + t + '</span>'; }).join('') + '</div><div class="product-card__footer"><span class="product-card__votes">' + p.votes + ' votes</span><span class="product-card__comments">' + p.comments + ' comments</span></div></div>';
    }).join('');
    var phCount = items.filter(function (p) { return p.source === 'ph'; }).length;
    var hnCount = items.filter(function (p) { return p.source === 'hn'; }).length;
    $('#stat-total').textContent = items.length;
    $('#stat-ph').textContent = phCount;
    $('#stat-hn').textContent = hnCount;
    if (!prefersReducedMotion) {
      gsap.from('.product-card', { y: 40, opacity: 0, duration: 0.5, stagger: 0.04, ease: 'power3.out', clearProps: 'transform,opacity' });
    }
  }
  function initAnimations() {
    if (prefersReducedMotion) return;
    var tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    tl.from('.hero__label', { y: 40, opacity: 0, duration: 0.5 })
      .from('.hero__title', { y: 40, opacity: 0, duration: 0.7 }, '-=0.3')
      .from('.hero__subtitle', { y: 40, opacity: 0, duration: 0.5 }, '-=0.3')
      .from('.hero__stat', { y: 40, opacity: 0, duration: 0.4, stagger: 0.08 }, '-=0.2');
  }
  function init() { renderFilters(); renderProducts(); initAnimations(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
