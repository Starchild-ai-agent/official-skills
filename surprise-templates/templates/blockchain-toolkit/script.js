/* ============================================================
   Blockchain Dev Toolkit — script.js

   Skeleton: A6 Sidebar+Content
   Hover: C7 边框发光
   Entrance: D4 stagger
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Mock Data ---------- */
  var TOOLS = [
    { name: 'Hardhat', desc: 'Ethereum development environment for compiling, deploying, testing, and debugging.', category: 'ide', chains: ['ethereum', 'polygon'], rating: 4.8, url: 'https://hardhat.org' },
    { name: 'Foundry', desc: 'Blazing fast, portable, and modular toolkit for Ethereum application development written in Rust.', category: 'testing', chains: ['ethereum', 'polygon'], rating: 4.9, url: 'https://getfoundry.sh' },
    { name: 'Anchor', desc: 'Framework for Solana smart contract development with IDL generation and client libraries.', category: 'ide', chains: ['solana'], rating: 4.7, url: 'https://anchor-lang.com' },
    { name: 'Tenderly', desc: 'Full-stack infrastructure for smart contract development with debugging, monitoring, and alerting.', category: 'monitor', chains: ['ethereum', 'polygon'], rating: 4.6, url: 'https://tenderly.co' },
    { name: 'Slither', desc: 'Static analysis framework for Solidity that detects vulnerabilities and code quality issues.', category: 'security', chains: ['ethereum', 'polygon'], rating: 4.5, url: 'https://github.com/crytic/slither' },
    { name: 'Remix IDE', desc: 'Browser-based IDE for Solidity development with built-in compiler, debugger, and deployer.', category: 'ide', chains: ['ethereum', 'polygon'], rating: 4.3, url: 'https://remix.ethereum.org' },
    { name: 'Alchemy', desc: 'Blockchain development platform with enhanced APIs, monitoring, and analytics.', category: 'deploy', chains: ['ethereum', 'polygon', 'solana'], rating: 4.7, url: 'https://alchemy.com' },
    { name: 'The Graph', desc: 'Indexing protocol for querying blockchain data with GraphQL subgraphs.', category: 'monitor', chains: ['ethereum', 'polygon'], rating: 4.6, url: 'https://thegraph.com' },
    { name: 'OpenZeppelin', desc: 'Library of secure, reusable smart contracts and security audit tools.', category: 'security', chains: ['ethereum', 'polygon'], rating: 4.9, url: 'https://openzeppelin.com' },
    { name: 'Helius', desc: 'Solana RPC and API platform with webhooks, DAS API, and enhanced transaction parsing.', category: 'deploy', chains: ['solana'], rating: 4.5, url: 'https://helius.dev' },
    { name: 'Echidna', desc: 'Ethereum smart contract fuzzer for property-based testing and vulnerability discovery.', category: 'testing', chains: ['ethereum'], rating: 4.4, url: 'https://github.com/crytic/echidna' },
    { name: 'Vercel + thirdweb', desc: 'Deploy full-stack Web3 apps with serverless functions and blockchain SDK integration.', category: 'deploy', chains: ['ethereum', 'polygon', 'solana'], rating: 4.3, url: 'https://thirdweb.com' },
  ];

  var currentCategory = 'all';
  var currentChain = 'all';

  /* ---------- Theme ---------- */
  var themeToggle = document.getElementById('theme-toggle');
  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('btk-theme', theme);
  }
  themeToggle.addEventListener('click', function () {
    var current = document.documentElement.getAttribute('data-theme') || 'dark';
    setTheme(current === 'dark' ? 'light' : 'dark');
  });
  var savedTheme = localStorage.getItem('btk-theme') ||
    (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  setTheme(savedTheme);

  /* ---------- Chain Selector ---------- */
  document.querySelectorAll('.chain-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.chain-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      currentChain = btn.getAttribute('data-chain');
      renderTools();
    });
  });

  /* ---------- Sidebar Category ---------- */
  document.querySelectorAll('.sidebar__item').forEach(function (item) {
    item.addEventListener('click', function () {
      document.querySelectorAll('.sidebar__item').forEach(function (i) { i.classList.remove('active'); });
      item.classList.add('active');
      currentCategory = item.getAttribute('data-category');
      renderTools();
    });
  });

  /* ---------- Filter ---------- */
  function getFilteredTools() {
    return TOOLS.filter(function (t) {
      if (currentCategory !== 'all' && t.category !== currentCategory) return false;
      if (currentChain !== 'all' && t.chains.indexOf(currentChain) === -1) return false;
      return true;
    });
  }

  /* ---------- Render Tools ---------- */
  function renderTools() {
    var grid = document.getElementById('tools-grid');
    var tools = getFilteredTools();

    if (tools.length === 0) {
      grid.innerHTML = '<p style="color:var(--color-text-muted);grid-column:1/-1">No tools match your filters</p>';
      return;
    }

    var html = '';
    tools.forEach(function (t) {
      var chainsHtml = t.chains.map(function (c) {
        return '<span class="tool-card__chain">' + c + '</span>';
      }).join('');
      var stars = '';
      for (var i = 0; i < 5; i++) {
        stars += i < Math.round(t.rating) ? '\u2605' : '\u2606';
      }

      html += '<div class="tool-card">' +
        '<div class="tool-card__category">' + t.category + '</div>' +
        '<div class="tool-card__name">' + t.name + '</div>' +
        '<div class="tool-card__desc">' + t.desc + '</div>' +
        '<div class="tool-card__footer">' +
        '<div class="tool-card__chains">' + chainsHtml + '</div>' +
        '<span class="tool-card__rating">' + stars + ' ' + t.rating + '</span>' +
        '</div>' +
        '<a class="tool-card__link" href="' + t.url + '" target="_blank" rel="noopener noreferrer">' + t.url + ' \u2192</a>' +
        '</div>';
    });
    grid.innerHTML = html;

    /* D4 stagger entrance */
    if (!prefersReducedMotion) {
      gsap.utils.toArray('.tool-card').forEach(function (el, i) {
        gsap.from(el, {
          opacity: 0, y: 20, duration: 0.4, delay: i * 0.06, ease: 'power2.out',
        });
      });
    }
  }

  /* ---------- GSAP Animations (D4 stagger) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    gsap.from('.hero__inline', { opacity: 0, y: 15, duration: 0.5, ease: 'power3.out' });
    gsap.from('.hero__title', { opacity: 0, y: 20, duration: 0.6, delay: 0.1, ease: 'power3.out' });
    gsap.from('.hero__chain-selector', { opacity: 0, y: 15, duration: 0.5, delay: 0.2, ease: 'power2.out' });

    gsap.from('.sidebar', { opacity: 0, x: -20, duration: 0.6, delay: 0.3, ease: 'power2.out' });
  }

  /* ---------- Init ---------- */
  renderTools();
  initAnimations();

})();
