/* ============================================================
   Airdrop Intel Feed — script.js
   Mock data · GSAP 3 + ScrollTrigger
   ============================================================ */
(function () {
  'use strict';
  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var FILTERS = ['All', 'Confirmed', 'Suspected', 'Expired', 'High Priority'];

  var SIGNALS = [
    { project: 'LayerZero', status: 'confirmed', conditions: 'Bridge assets across 3+ chains. Use Stargate, interact with OFT tokens. Minimum 10 transactions over 6 months.', value: '$2,000 - $8,000', deadline: 'Jun 30, 2025', priority: 'high', source: '@layerzero_labs' },
    { project: 'zkSync Era', status: 'confirmed', conditions: 'Deploy a smart contract, use DEXs (SyncSwap, Mute), provide liquidity. Volume > $10K recommended.', value: '$1,500 - $5,000', deadline: 'TBD', priority: 'high', source: '@zaboris' },
    { project: 'Scroll', status: 'suspected', conditions: 'Bridge to Scroll, interact with native DEXs and lending protocols. Maintain activity over 3+ months.', value: '$500 - $3,000', deadline: 'Q3 2025', priority: 'medium', source: '@scroll_zkp' },
    { project: 'Linea', status: 'suspected', conditions: 'Use Linea bridge, interact with ecosystem dApps. Complete Linea Voyage quests if available.', value: '$300 - $2,000', deadline: 'Q4 2025', priority: 'medium', source: '@LineaBuild' },
    { project: 'Berachain', status: 'suspected', conditions: 'Participate in testnet, provide liquidity in Proof of Liquidity system. Early community engagement.', value: '$1,000 - $5,000', deadline: 'Q3 2025', priority: 'high', source: '@beaboris' },
    { project: 'Monad', status: 'suspected', conditions: 'Join Discord, participate in testnet when available. Follow social channels for early access.', value: '$500 - $4,000', deadline: 'Q4 2025', priority: 'medium', source: '@moaboris' },
    { project: 'Starknet Season 2', status: 'suspected', conditions: 'Continue using Starknet DeFi protocols. Maintain STRK staking positions. New criteria expected.', value: '$200 - $1,500', deadline: 'TBD', priority: 'low', source: '@Starknet' },
    { project: 'Wormhole W2', status: 'suspected', conditions: 'Use Wormhole bridge for cross-chain transfers. Stake W tokens. Participate in governance.', value: '$100 - $800', deadline: 'TBD', priority: 'low', source: '@wormhole' },
    { project: 'Blast Season 2', status: 'expired', conditions: 'Deposit ETH/stablecoins, earn Blast Points and Gold. Season 1 already distributed.', value: 'Expired', deadline: 'Ended', priority: 'low', source: '@blast' },
    { project: 'EigenLayer S1', status: 'expired', conditions: 'Restake ETH through EigenLayer. Season 1 EIGEN tokens already claimed.', value: 'Expired', deadline: 'Ended', priority: 'low', source: '@eigenlayer' }
  ];

  var activeFilter = 'All';
  var $ = function (sel) { return document.querySelector(sel); };

  function initTheme() {
    var saved = localStorage.getItem('airdrop-intel-theme');
    if (saved === 'light') document.documentElement.setAttribute('data-theme', 'light');
  }
  initTheme();
  $('#theme-toggle').addEventListener('click', function () {
    var isLight = document.documentElement.getAttribute('data-theme') === 'light';
    document.documentElement.setAttribute('data-theme', isLight ? '' : 'light');
    localStorage.setItem('airdrop-intel-theme', isLight ? 'dark' : 'light');
  });

  function renderFilters() {
    var tabs = $('#filter-tabs');
    tabs.innerHTML = FILTERS.map(function (f) {
      return '<button class="filter-tab ' + (f === activeFilter ? 'active' : '') + '" data-filter="' + f + '">' + f + '</button>';
    }).join('');
    tabs.querySelectorAll('.filter-tab').forEach(function (tab) {
      tab.addEventListener('click', function () {
        activeFilter = tab.dataset.filter;
        renderFilters();
        renderSignals();
      });
    });
  }

  function renderSignals() {
    var items = SIGNALS;
    if (activeFilter === 'Confirmed') items = SIGNALS.filter(function (s) { return s.status === 'confirmed'; });
    else if (activeFilter === 'Suspected') items = SIGNALS.filter(function (s) { return s.status === 'suspected'; });
    else if (activeFilter === 'Expired') items = SIGNALS.filter(function (s) { return s.status === 'expired'; });
    else if (activeFilter === 'High Priority') items = SIGNALS.filter(function (s) { return s.priority === 'high'; });

    var list = $('#signal-list');
    list.innerHTML = items.map(function (s) {
      return '<div class="signal-card">' +
        '<div class="signal-card__header">' +
          '<span class="signal-card__project">' + s.project + '</span>' +
          '<span class="signal-card__status signal-card__status--' + s.status + '">' + s.status + '</span>' +
        '</div>' +
        '<div class="signal-card__conditions">' + s.conditions + '</div>' +
        '<div class="signal-card__footer">' +
          '<span class="signal-card__meta">Est. Value: <strong>' + s.value + '</strong></span>' +
          '<span class="signal-card__meta">Deadline: <strong>' + s.deadline + '</strong></span>' +
          '<span class="signal-card__meta">Source: ' + s.source + '</span>' +
          '<span class="signal-card__priority signal-card__priority--' + s.priority + '">' + s.priority.toUpperCase() + '</span>' +
        '</div>' +
      '</div>';
    }).join('');

    $('#alert-count').textContent = items.filter(function (s) { return s.status !== 'expired'; }).length + ' active signals';

    if (!prefersReducedMotion) {
      gsap.from('.signal-card', { opacity: 0, y: 20, duration: 0.4, stagger: 0.06, ease: 'power3.out', clearProps: 'opacity,transform' });
    }
  }

  function initAnimations() {
    if (prefersReducedMotion) return;
    var heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl.from('.hero__alert-bar', { opacity: 0, y: 20, duration: 0.5 })
      .from('.hero__title', { opacity: 0, y: 30, duration: 0.7 }, '-=0.3')
      .from('.hero__subtitle', { opacity: 0, y: 20, duration: 0.5 }, '-=0.3');
  }

  function init() {
    renderFilters();
    renderSignals();
    initAnimations();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
