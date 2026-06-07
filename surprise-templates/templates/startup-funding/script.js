/* ============================================================
   Startup Funding Tracker — script.js
   Mock data · GSAP 3 + ScrollTrigger · Chart.js
   ============================================================ */
(function () {
  'use strict';
  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var NEWS = [
    { company: 'NeuralScale AI', round: 'Series B', amount: '$120M', desc: 'AI infrastructure startup building next-gen inference engines. Led by Andreessen Horowitz.', investors: 'a16z, Sequoia', date: '2 hours ago' },
    { company: 'ChainVault', round: 'Series A', amount: '$45M', desc: 'Institutional-grade crypto custody solution with MPC technology.', investors: 'Paradigm, Coinbase Ventures', date: '5 hours ago' },
    { company: 'HealthOS', round: 'Seed', amount: '$8M', desc: 'AI-powered clinical decision support platform for hospitals.', investors: 'YC, Khosla Ventures', date: '8 hours ago' },
    { company: 'RoboFleet', round: 'Series C', amount: '$250M', desc: 'Autonomous delivery robot fleet operating in 15 US cities.', investors: 'Tiger Global, Coatue', date: '12 hours ago' },
    { company: 'DataMesh', round: 'Series A', amount: '$32M', desc: 'Real-time data pipeline platform for ML teams. 300% ARR growth.', investors: 'Lightspeed, Index', date: '1 day ago' },
    { company: 'GreenGrid', round: 'Series B', amount: '$85M', desc: 'AI-optimized renewable energy grid management.', investors: 'Breakthrough Energy', date: '1 day ago' },
    { company: 'FinStack', round: 'Seed', amount: '$5M', desc: 'Embedded finance API for SaaS platforms.', investors: 'Ribbit Capital, Stripe', date: '2 days ago' },
    { company: 'SpaceLink', round: 'Series A', amount: '$60M', desc: 'Low-earth orbit satellite communication for IoT devices.', investors: 'Founders Fund, Lux', date: '2 days ago' }
  ];
  var SECTORS = [
    { name: 'AI / ML', deals: 42, amount: '$2.8B' },
    { name: 'Fintech', deals: 28, amount: '$1.5B' },
    { name: 'Climate Tech', deals: 22, amount: '$1.2B' },
    { name: 'Crypto / Web3', deals: 18, amount: '$890M' },
    { name: 'Healthcare', deals: 15, amount: '$720M' },
    { name: 'SaaS', deals: 35, amount: '$680M' },
    { name: 'Robotics', deals: 12, amount: '$540M' },
    { name: 'Space Tech', deals: 8, amount: '$420M' }
  ];
  var INVESTORS = [
    { name: 'Andreessen Horowitz', type: 'VC Firm', deals: 18, deployed: '$1.2B', focus: 'AI, Crypto' },
    { name: 'Sequoia Capital', type: 'VC Firm', deals: 15, deployed: '$980M', focus: 'AI, Fintech' },
    { name: 'Paradigm', type: 'Crypto Fund', deals: 12, deployed: '$650M', focus: 'DeFi, Infra' },
    { name: 'Y Combinator', type: 'Accelerator', deals: 45, deployed: '$180M', focus: 'Early Stage' },
    { name: 'Tiger Global', type: 'Crossover', deals: 8, deployed: '$1.5B', focus: 'Growth, SaaS' },
    { name: 'Founders Fund', type: 'VC Firm', deals: 10, deployed: '$720M', focus: 'Deep Tech' }
  ];
  var $ = function (s) { return document.querySelector(s); };
  function initTheme() {
    var saved = localStorage.getItem('startup-funding-theme');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  }
  initTheme();
  $('#theme-toggle').addEventListener('click', function () {
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
    localStorage.setItem('startup-funding-theme', isDark ? 'light' : 'dark');
  });
  function renderNews() {
    $('#news-list').innerHTML = NEWS.map(function (n) {
      return '<div class="news-item"><div class="news-item__header"><span class="news-item__company">' + n.company + '</span><span class="news-item__round">' + n.round + '</span><span class="news-item__amount">' + n.amount + '</span></div><div class="news-item__desc">' + n.desc + '</div><div class="news-item__meta">' + n.investors + ' · ' + n.date + '</div></div>';
    }).join('');
  }
  function renderChart() {
    new Chart($('#round-chart').getContext('2d'), {
      type: 'doughnut',
      data: { labels: ['Seed','Series A','Series B','Series C+'], datasets: [{ data: [35,28,18,12], backgroundColor: ['#0284c7','#0ea5e9','#38bdf8','#7dd3fc'], borderWidth: 0 }] },
      options: { responsive: true, cutout: '60%', plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', font: { family: 'IBM Plex Mono', size: 11 } } } } }
    });
  }
  function renderSectors() {
    $('#sector-list').innerHTML = SECTORS.map(function (s, i) {
      return '<div class="sector-item"><span class="sector-item__rank">#' + (i+1) + '</span><span class="sector-item__name">' + s.name + '</span><span class="sector-item__deals">' + s.deals + ' deals</span><span class="sector-item__amount">' + s.amount + '</span></div>';
    }).join('');
  }
  function renderInvestors() {
    $('#investor-grid').innerHTML = INVESTORS.map(function (v) {
      return '<div class="investor-card"><div class="investor-card__name">' + v.name + '</div><div class="investor-card__type">' + v.type + '</div><div class="investor-card__stat"><span class="investor-card__stat-label">Deals</span><span class="investor-card__stat-value">' + v.deals + '</span></div><div class="investor-card__stat"><span class="investor-card__stat-label">Deployed</span><span class="investor-card__stat-value">' + v.deployed + '</span></div><div class="investor-card__stat"><span class="investor-card__stat-label">Focus</span><span class="investor-card__stat-value">' + v.focus + '</span></div></div>';
    }).join('');
  }
  function initAnimations() {
    if (prefersReducedMotion) return;
    var tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    tl.from('.hero__label', { y: -30, opacity: 0, duration: 0.5 })
      .from('.hero__title', { y: -30, opacity: 0, duration: 0.7 }, '-=0.3')
      .from('.hero__subtitle', { y: -30, opacity: 0, duration: 0.5 }, '-=0.3')
      .from('.hero__stat-card', { y: -30, opacity: 0, duration: 0.4, stagger: 0.1 }, '-=0.2');
    gsap.from('.news-item', { scrollTrigger: { trigger: '#news', start: 'top 80%', once: true }, y: -30, opacity: 0, duration: 0.4, stagger: 0.05, ease: 'power3.out' });
    gsap.from('.sector-item', { scrollTrigger: { trigger: '#distribution', start: 'top 80%', once: true }, y: -30, opacity: 0, duration: 0.3, stagger: 0.04, ease: 'power3.out' });
    gsap.from('.investor-card', { scrollTrigger: { trigger: '#investors', start: 'top 80%', once: true }, y: -30, opacity: 0, duration: 0.4, stagger: 0.06, ease: 'power3.out' });
  }
  function init() { renderNews(); renderChart(); renderSectors(); renderInvestors(); initAnimations(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
