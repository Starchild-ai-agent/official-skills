/* ============================================================
   Cross-Chain Migration Advisor — script.js

   APIs: CoinGecko (free, no key) + built-in mock bridge data
   Animation: GSAP 3 + ScrollTrigger
   Entrance: D8 translateX(40px)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Mock Bridge Data ---------- */
  const BRIDGES = {
    'ethereum-arbitrum': [
      { name: 'Arbitrum Bridge', fee: 0.001, feePercent: 0.1, speed: '10 min', speedMin: 10, security: 'high', securityScore: 95, steps: ['Deposit on L1', 'Wait for confirmation', 'Receive on Arbitrum'] },
      { name: 'Stargate', fee: 0.003, feePercent: 0.3, speed: '2 min', speedMin: 2, security: 'high', securityScore: 90, steps: ['Approve token', 'Bridge via LayerZero', 'Receive on Arbitrum'] },
      { name: 'Hop Protocol', fee: 0.004, feePercent: 0.4, speed: '5 min', speedMin: 5, security: 'medium', securityScore: 80, steps: ['Approve token', 'Send via Hop', 'Bonder relays', 'Receive on Arbitrum'] },
      { name: 'Across Protocol', fee: 0.002, feePercent: 0.2, speed: '1 min', speedMin: 1, security: 'high', securityScore: 88, steps: ['Deposit', 'Relayer fills', 'Receive on Arbitrum'] },
      { name: 'Celer cBridge', fee: 0.005, feePercent: 0.5, speed: '3 min', speedMin: 3, security: 'medium', securityScore: 75, steps: ['Lock on source', 'Validator confirm', 'Mint on Arbitrum'] },
    ],
    'ethereum-base': [
      { name: 'Base Bridge', fee: 0.001, feePercent: 0.1, speed: '15 min', speedMin: 15, security: 'high', securityScore: 95, steps: ['Deposit on L1', 'Wait for finality', 'Receive on Base'] },
      { name: 'Stargate', fee: 0.003, feePercent: 0.3, speed: '2 min', speedMin: 2, security: 'high', securityScore: 90, steps: ['Approve token', 'Bridge via LayerZero', 'Receive on Base'] },
      { name: 'Across Protocol', fee: 0.002, feePercent: 0.2, speed: '1 min', speedMin: 1, security: 'high', securityScore: 88, steps: ['Deposit', 'Relayer fills', 'Receive on Base'] },
    ],
    'ethereum-optimism': [
      { name: 'Optimism Bridge', fee: 0.001, feePercent: 0.1, speed: '20 min', speedMin: 20, security: 'high', securityScore: 95, steps: ['Deposit on L1', 'Wait for sequencer', 'Receive on OP'] },
      { name: 'Stargate', fee: 0.003, feePercent: 0.3, speed: '2 min', speedMin: 2, security: 'high', securityScore: 90, steps: ['Approve', 'Bridge via LZ', 'Receive on OP'] },
      { name: 'Hop Protocol', fee: 0.004, feePercent: 0.4, speed: '5 min', speedMin: 5, security: 'medium', securityScore: 80, steps: ['Approve', 'Send via Hop', 'Receive on OP'] },
    ],
    'ethereum-polygon': [
      { name: 'Polygon Bridge', fee: 0.001, feePercent: 0.1, speed: '30 min', speedMin: 30, security: 'high', securityScore: 92, steps: ['Deposit on L1', 'Checkpoint', 'Receive on Polygon'] },
      { name: 'Stargate', fee: 0.003, feePercent: 0.3, speed: '2 min', speedMin: 2, security: 'high', securityScore: 90, steps: ['Approve', 'Bridge via LZ', 'Receive on Polygon'] },
      { name: 'Hop Protocol', fee: 0.005, feePercent: 0.5, speed: '5 min', speedMin: 5, security: 'medium', securityScore: 78, steps: ['Approve', 'Send via Hop', 'Receive on Polygon'] },
    ],
    'ethereum-zksync': [
      { name: 'zkSync Bridge', fee: 0.001, feePercent: 0.1, speed: '15 min', speedMin: 15, security: 'high', securityScore: 93, steps: ['Deposit on L1', 'ZK proof generation', 'Receive on zkSync'] },
      { name: 'Orbiter Finance', fee: 0.003, feePercent: 0.3, speed: '1 min', speedMin: 1, security: 'medium', securityScore: 82, steps: ['Send to Orbiter', 'Cross-rollup relay', 'Receive on zkSync'] },
    ],
  };

  const CHAIN_GAS = {
    ethereum: { name: 'Ethereum', gas: '$4.20' },
    polygon: { name: 'Polygon', gas: '$0.01' },
    bsc: { name: 'BNB Chain', gas: '$0.08' },
    avalanche: { name: 'Avalanche', gas: '$0.15' },
    optimism: { name: 'Optimism', gas: '$0.05' },
    arbitrum: { name: 'Arbitrum', gas: '$0.12' },
    base: { name: 'Base', gas: '$0.03' },
    zksync: { name: 'zkSync Era', gas: '$0.04' },
  };

  /* ---------- DOM References ---------- */
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const sourceSelect = $('#source-chain');
  const targetSelect = $('#target-chain');
  const amountInput = $('#bridge-amount');
  const swapBtn = $('#swap-chains');
  const routesTbody = $('#routes-tbody');
  const feeCanvas = $('#fee-chart');
  const heroSource = $('#hero-source');
  const heroTarget = $('#hero-target');
  const heroSourceGas = $('#hero-source-gas');
  const heroTargetGas = $('#hero-target-gas');

  let feeChart = null;

  /* ---------- Scoring Algorithm ---------- */
  function scoreRoute(route, amount) {
    const feeCost = route.feePercent * amount / 100;
    const feeScore = Math.max(0, 100 - feeCost * 10);
    const speedScore = Math.max(0, 100 - route.speedMin * 2);
    const secScore = route.securityScore;
    return Math.round(feeScore * 0.35 + speedScore * 0.30 + secScore * 0.35);
  }

  /* ---------- Get Routes ---------- */
  function getRoutes() {
    const source = sourceSelect.value;
    const target = targetSelect.value;
    const key = `${source}-${target}`;
    const amount = parseFloat(amountInput.value) || 1000;

    // Try exact match, then generate fallback
    let routes = BRIDGES[key];
    if (!routes) {
      routes = [
        { name: 'Stargate', fee: 0.003, feePercent: 0.3, speed: '2 min', speedMin: 2, security: 'high', securityScore: 90, steps: ['Approve', 'Bridge via LayerZero', `Receive on ${CHAIN_GAS[target]?.name || target}`] },
        { name: 'Across Protocol', fee: 0.002, feePercent: 0.2, speed: '1 min', speedMin: 1, security: 'high', securityScore: 88, steps: ['Deposit', 'Relayer fills', `Receive on ${CHAIN_GAS[target]?.name || target}`] },
        { name: 'Hop Protocol', fee: 0.005, feePercent: 0.5, speed: '5 min', speedMin: 5, security: 'medium', securityScore: 78, steps: ['Approve', 'Send via Hop', `Receive on ${CHAIN_GAS[target]?.name || target}`] },
      ];
    }

    return routes.map(r => ({
      ...r,
      totalFee: (r.feePercent * amount / 100).toFixed(2),
      score: scoreRoute(r, amount),
    })).sort((a, b) => b.score - a.score);
  }

  /* ---------- Render Routes Table ---------- */
  function renderRoutes() {
    const routes = getRoutes();
    const bestScore = routes[0]?.score || 0;

    routesTbody.innerHTML = routes.map((r, i) => `
      <tr class="route-row" style="opacity:0">
        <td><span class="route-badge">${r.name}</span></td>
        <td><span class="route-fee">$${r.totalFee}</span></td>
        <td><span class="route-speed">${r.speed}</span></td>
        <td>
          <span class="route-security">
            <span class="security-dot security-dot--${r.security}"></span>
            ${r.security.charAt(0).toUpperCase() + r.security.slice(1)}
          </span>
        </td>
        <td><span class="route-score">${r.score}</span></td>
        <td>${r.score === bestScore ? '<span class="route-best-tag">Best</span>' : ''}</td>
      </tr>
    `).join('');

    // Animate rows — D8 translateX(40px)
    if (!prefersReducedMotion) {
      gsap.fromTo('.route-row', 
        { opacity: 0, x: 40 },
        { opacity: 1, x: 0, duration: 0.5, stagger: 0.08, ease: 'power2.out' }
      );
    } else {
      $$('.route-row').forEach(r => r.style.opacity = '1');
    }

    // Update best path card
    const best = routes[0];
    if (best) {
      $('#best-bridge').textContent = best.name;
      $('#best-score').textContent = best.score + '/100';
      $('#best-fee').textContent = '$' + best.totalFee;
      $('#best-time').textContent = best.speed;
      $('#best-security').textContent = best.security.charAt(0).toUpperCase() + best.security.slice(1);

      const stepsEl = $('#best-steps');
      stepsEl.innerHTML = best.steps.map((s, i) => 
        `<span class="step-node">${s}</span>${i < best.steps.length - 1 ? '<span class="step-arrow">→</span>' : ''}`
      ).join('');
    }

    // Update hero
    const sourceChain = CHAIN_GAS[sourceSelect.value];
    const targetChain = CHAIN_GAS[targetSelect.value];
    if (sourceChain) {
      heroSource.textContent = sourceChain.name;
      heroSourceGas.textContent = '~' + sourceChain.gas + ' gas';
    }
    if (targetChain) {
      heroTarget.textContent = targetChain.name;
      heroTargetGas.textContent = '~' + targetChain.gas + ' gas';
    }

    renderFeeChart(routes);
  }

  /* ---------- Fee Chart ---------- */
  function renderFeeChart(routes) {
    const ctx = feeCanvas.getContext('2d');
    const style = getComputedStyle(document.documentElement);
    const accent = style.getPropertyValue('--color-accent').trim();
    const textColor = style.getPropertyValue('--color-text-secondary').trim();
    const borderColor = style.getPropertyValue('--color-border').trim();

    const colors = [
      style.getPropertyValue('--chart-1').trim(),
      style.getPropertyValue('--chart-2').trim(),
      style.getPropertyValue('--chart-3').trim(),
      style.getPropertyValue('--chart-4').trim(),
      style.getPropertyValue('--chart-5').trim(),
      style.getPropertyValue('--chart-6').trim(),
    ];

    if (feeChart) feeChart.destroy();

    feeChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: routes.map(r => r.name),
        datasets: [{
          label: 'Fee (USD)',
          data: routes.map(r => parseFloat(r.totalFee)),
          backgroundColor: routes.map((_, i) => colors[i % colors.length]),
          borderRadius: 6,
          borderSkipped: false,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `Fee: $${ctx.parsed.y.toFixed(2)}`,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: textColor, font: { family: "'Figtree', sans-serif", size: 11 } },
            grid: { display: false },
          },
          y: {
            ticks: {
              color: textColor,
              font: { family: "'JetBrains Mono', monospace", size: 11 },
              callback: (v) => '$' + v,
            },
            grid: { color: borderColor },
          },
        },
      },
    });
  }

  /* ---------- Theme Toggle ---------- */
  function initTheme() {
    const saved = localStorage.getItem('crosschain-theme');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');

    $('#theme-toggle').addEventListener('click', () => {
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
      localStorage.setItem('crosschain-theme', isDark ? 'light' : 'dark');
      // Re-render chart with new theme colors
      renderRoutes();
    });
  }

  /* ---------- GSAP Animations ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    // Hero entrance
    const heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl
      .from('.hero__label', { opacity: 0, y: 20, duration: 0.6 })
      .from('.hero__title', { opacity: 0, y: 30, duration: 0.7 }, '-=0.3')
      .from('.hero__subtitle', { opacity: 0, y: 20, duration: 0.5 }, '-=0.3')
      .from('.hero__chain-card', { opacity: 0, x: (i) => i === 0 ? -40 : 40, duration: 0.6, stagger: 0.15 }, '-=0.2')
      .from('.hero__arrow', { opacity: 0, scale: 0.5, duration: 0.4 }, '-=0.4');

    // Section entrances — D8 translateX(40px)
    $$('.section').forEach(section => {
      gsap.from(section, {
        scrollTrigger: {
          trigger: section,
          start: 'top 85%',
          toggleActions: 'play none none none',
        },
        opacity: 0,
        x: 40,
        duration: 0.7,
        ease: 'power2.out',
      });
    });
  }

  /* ---------- Event Listeners ---------- */
  function initEvents() {
    sourceSelect.addEventListener('change', renderRoutes);
    targetSelect.addEventListener('change', renderRoutes);
    amountInput.addEventListener('input', renderRoutes);

    swapBtn.addEventListener('click', () => {
      const srcVal = sourceSelect.value;
      const tgtVal = targetSelect.value;

      // Check if values exist in opposite selects
      const srcOptions = Array.from(sourceSelect.options).map(o => o.value);
      const tgtOptions = Array.from(targetSelect.options).map(o => o.value);

      if (tgtOptions.includes(srcVal) && srcOptions.includes(tgtVal)) {
        sourceSelect.value = tgtVal;
        targetSelect.value = srcVal;
        renderRoutes();
      }
    });
  }

  /* ---------- Init ---------- */
  function init() {
    initTheme();
    renderRoutes();
    initAnimations();
    initEvents();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
