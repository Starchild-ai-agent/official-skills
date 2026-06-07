/* ============================================================
   DeFi Developer Console — script.js

   APIs: DeFi Llama (TVL) + CoinGecko (ETH price) + Mock data
   Animation: GSAP 3 + ScrollTrigger
   Entrance: D2 stagger left-to-right
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Register GSAP Plugins ---------- */
  gsap.registerPlugin(ScrollTrigger);

  /* ---------- Reduced Motion Check ---------- */
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Configuration ---------- */
  const CONFIG = {
    maxRetries: 2,
    retryBaseDelay: 1500,
  };

  const API = {
    defiTvl: () => 'https://api.llama.fi/protocols',
    ethPrice: () =>
      'https://pro-api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd&include_24hr_change=true',
  };

  /* ---------- Mock Data ---------- */
  const CONTRACTS = [
    { name: 'LiquidityPool.sol', address: '0x7a25...3f8e', status: 'deployed', interactions: '12,847' },
    { name: 'YieldVault.sol', address: '0x3b91...a2c4', status: 'deployed', interactions: '8,234' },
    { name: 'StakingRewards.sol', address: '0x9e4f...7d1b', status: 'deployed', interactions: '45,891' },
    { name: 'GovernanceV2.sol', address: '0x1c8a...5e9f', status: 'pending', interactions: '0' },
    { name: 'FlashLoan.sol', address: '0x6d2e...8b3c', status: 'deployed', interactions: '3,456' },
    { name: 'OracleAdapter.sol', address: '0x4f7c...1a2d', status: 'error', interactions: '—' },
  ];

  const YIELD_STRATEGIES = [
    { pool: 'ETH/USDC', protocol: 'Uniswap V3', apy: '18.4%', tvl: '$234M' },
    { pool: 'stETH/ETH', protocol: 'Curve', apy: '5.2%', tvl: '$1.8B' },
    { pool: 'WBTC/ETH', protocol: 'Balancer', apy: '12.1%', tvl: '$89M' },
    { pool: 'DAI/USDC/USDT', protocol: 'Curve 3pool', apy: '3.8%', tvl: '$2.1B' },
    { pool: 'GLP', protocol: 'GMX', apy: '22.7%', tvl: '$456M' },
    { pool: 'rETH/WETH', protocol: 'Aura', apy: '8.9%', tvl: '$167M' },
  ];

  const GAS_TIPS = [
    { title: 'Batch Transactions', desc: 'Use multicall to batch multiple contract calls into one transaction', savings: 'Save ~40% gas' },
    { title: 'Storage Optimization', desc: 'Pack struct variables to use fewer storage slots (uint128 pairs)', savings: 'Save ~20K gas/slot' },
    { title: 'Off-peak Timing', desc: 'Execute non-urgent txns during weekends (UTC 2-6 AM)', savings: 'Save ~30-50% gas' },
    { title: 'Use calldata', desc: 'Replace memory with calldata for read-only function params', savings: 'Save ~600 gas/param' },
    { title: 'Assembly for Loops', desc: 'Use inline assembly for tight loops with known bounds', savings: 'Save ~50% per iteration' },
  ];

  const NEW_PROTOCOLS = [
    { name: 'EigenLayer', chain: 'Ethereum', desc: 'Restaking protocol — secure multiple networks with staked ETH' },
    { name: 'Ethena', chain: 'Ethereum', desc: 'Synthetic dollar protocol with delta-neutral yield' },
    { name: 'Jito', chain: 'Solana', desc: 'MEV-aware liquid staking with JitoSOL' },
    { name: 'Kamino', chain: 'Solana', desc: 'Automated liquidity management and lending' },
    { name: 'Morpho', chain: 'Ethereum', desc: 'Peer-to-peer lending optimization layer' },
    { name: 'Pendle', chain: 'Multi', desc: 'Yield tokenization — trade future yield today' },
  ];

  const PROTOCOL_DATA = [
    { name: 'Lido', chain: 'Ethereum', tvl: '$28.5B', change: '+2.3%', category: 'Liquid Staking' },
    { name: 'Aave', chain: 'Multi', tvl: '$12.1B', change: '+1.8%', category: 'Lending' },
    { name: 'MakerDAO', chain: 'Ethereum', tvl: '$8.7B', change: '-0.5%', category: 'CDP' },
    { name: 'Uniswap', chain: 'Multi', tvl: '$5.2B', change: '+3.1%', category: 'DEX' },
    { name: 'EigenLayer', chain: 'Ethereum', tvl: '$15.3B', change: '+8.7%', category: 'Restaking' },
    { name: 'Rocket Pool', chain: 'Ethereum', tvl: '$3.8B', change: '+1.2%', category: 'Liquid Staking' },
    { name: 'Curve', chain: 'Multi', tvl: '$2.1B', change: '-1.4%', category: 'DEX' },
    { name: 'Compound', chain: 'Ethereum', tvl: '$2.8B', change: '+0.9%', category: 'Lending' },
  ];

  const TICKER_MESSAGES = [
    '> TVL across DeFi: $89.2B (+2.1% 24h)',
    '> EigenLayer restaking hits $15B milestone',
    '> Ethereum gas: 12 gwei (low activity)',
    '> Uniswap V4 hooks framework now live on testnet',
    '> Aave V3 deploys on Base — $500M TVL in 48h',
    '> Solana DeFi TVL crosses $5B for first time',
  ];

  /* ============================================================
     GSAP ANIMATION SYSTEM
     ============================================================ */

  function animateHeroEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.terminal-hero', { opacity: 1 });
      return;
    }
    const tl = gsap.timeline({ defaults: { ease: 'power2.out' } });
    tl.from('.terminal-hero__chrome', { opacity: 0, y: -10, duration: 0.4 })
      .from('.terminal-hero__line', { opacity: 0, x: -15, duration: 0.3 }, '-=0.1')
      .from('.terminal-hero__ticker', { opacity: 0, duration: 0.3 }, '-=0.1')
      .from('.terminal-hero__metric', {
        opacity: 0, y: 10, stagger: 0.08, duration: 0.3,
      }, '-=0.1');
  }

  /** D2: stagger left-to-right entrance for panels */
  function animatePanelEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.console-panel', { opacity: 1, x: 0 });
      return;
    }
    const panels = gsap.utils.toArray('.console-panel');
    gsap.to(panels, {
      opacity: 1,
      x: 0,
      duration: 0.5,
      stagger: 0.1,
      ease: 'power2.out',
      scrollTrigger: {
        trigger: '.command-center__grid',
        start: 'top 85%',
        toggleActions: 'play none none none',
      },
    });
  }

  /* ============================================================
     THEME TOGGLE
     ============================================================ */
  function initThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    const html = document.documentElement;
    const stored = localStorage.getItem('defi-console-theme');
    if (stored) html.setAttribute('data-theme', stored);

    btn.addEventListener('click', () => {
      const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-theme', next);
      localStorage.setItem('defi-console-theme', next);
    });
  }

  /* ============================================================
     TICKER
     ============================================================ */
  function initTicker() {
    const el = document.getElementById('defi-ticker');
    if (!el) return;
    let idx = 0;

    function typeMessage(msg) {
      el.innerHTML = '';
      let i = 0;
      const cursor = document.createElement('span');
      cursor.className = 'terminal-hero__cursor';
      cursor.textContent = '_';

      function typeChar() {
        if (i < msg.length) {
          el.textContent = msg.substring(0, i + 1);
          el.appendChild(cursor);
          i++;
          setTimeout(typeChar, 20 + Math.random() * 15);
        } else {
          setTimeout(() => {
            idx = (idx + 1) % TICKER_MESSAGES.length;
            typeMessage(TICKER_MESSAGES[idx]);
          }, 3500);
        }
      }
      typeChar();
    }
    typeMessage(TICKER_MESSAGES[idx]);
  }

  /* ============================================================
     DATA FETCHING
     ============================================================ */
  async function fetchWithRetry(url, retries = CONFIG.maxRetries) {
    for (let i = 0; i <= retries; i++) {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
      } catch (err) {
        if (i === retries) throw err;
        await new Promise((r) => setTimeout(r, CONFIG.retryBaseDelay * (i + 1)));
      }
    }
  }

  /* ---------- TVL Chart ---------- */
  async function loadTvlChart() {
    const canvas = document.getElementById('tvl-chart');
    if (!canvas) return;

    let chartData = PROTOCOL_DATA;

    try {
      const protocols = await fetchWithRetry(API.defiTvl());
      if (protocols && protocols.length > 0) {
        const top8 = protocols
          .sort((a, b) => (b.tvl || 0) - (a.tvl || 0))
          .slice(0, 8);
        chartData = top8.map((p) => ({
          name: p.name,
          tvl: `$${formatBigNumber(p.tvl)}`,
          tvlRaw: p.tvl,
        }));
        document.getElementById('metric-tvl').textContent = `$${formatBigNumber(
          protocols.reduce((sum, p) => sum + (p.tvl || 0), 0)
        )}`;
        document.getElementById('metric-protocols').textContent = protocols.length.toString();
      }
    } catch {
      document.getElementById('metric-tvl').textContent = '$89.2B';
      document.getElementById('metric-protocols').textContent = '2,847';
    }

    const style = getComputedStyle(document.documentElement);
    const accent = style.getPropertyValue('--color-accent').trim();
    const textMuted = style.getPropertyValue('--color-text-muted').trim();
    const border = style.getPropertyValue('--color-border').trim();

    const labels = chartData.map((d) => d.name);
    const values = chartData.map((d) => d.tvlRaw || parseFloat(d.tvl.replace(/[$,BMK]/g, '')) * 1e9);

    new Chart(canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'TVL (USD)',
          data: values,
          backgroundColor: [
            accent, '#06b6d4', '#f59e0b', '#ef4444',
            '#8b5cf6', '#ec4899', '#14b8a6', '#f97316',
          ],
          borderRadius: 2,
          borderSkipped: false,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1a1a1a',
            titleFont: { family: 'Victor Mono', size: 11 },
            bodyFont: { family: 'Victor Mono', size: 10 },
            callbacks: {
              label: (ctx) => `TVL: $${formatBigNumber(ctx.raw)}`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: textMuted, font: { family: 'Victor Mono', size: 9 } },
          },
          y: {
            grid: { color: border },
            ticks: {
              color: textMuted,
              font: { family: 'Victor Mono', size: 9 },
              callback: (v) => '$' + formatBigNumber(v),
            },
          },
        },
      },
    });
  }

  /* ---------- ETH Price ---------- */
  async function loadEthPrice() {
    const el = document.getElementById('metric-eth');
    if (!el) return;
    try {
      const data = await fetchWithRetry(API.ethPrice());
      el.textContent = `$${data.ethereum.usd.toLocaleString()}`;
    } catch {
      el.textContent = '$3,450';
    }
  }

  /* ---------- Contracts ---------- */
  function loadContracts() {
    const container = document.getElementById('contracts-list');
    if (!container) return;

    container.innerHTML = CONTRACTS.map((c) => `
      <div class="contract-item">
        <div>
          <div class="contract-item__name">${c.name}</div>
          <div class="contract-item__address">${c.address}</div>
        </div>
        <div class="contract-item__interactions">${c.interactions} txns</div>
        <span class="contract-item__status contract-item__status--${c.status}">${c.status}</span>
      </div>
    `).join('');
  }

  /* ---------- Yield Strategies ---------- */
  function loadYield() {
    const container = document.getElementById('yield-list');
    if (!container) return;

    container.innerHTML = YIELD_STRATEGIES.map((y) => `
      <div class="yield-item">
        <div>
          <div class="yield-item__pool">${y.pool}</div>
          <div class="yield-item__protocol">${y.protocol}</div>
        </div>
        <div class="yield-item__tvl">${y.tvl}</div>
        <div class="yield-item__apy">${y.apy}</div>
      </div>
    `).join('');
  }

  /* ---------- Gas Tips ---------- */
  function loadGasTips() {
    const container = document.getElementById('gas-tips');
    if (!container) return;
    document.getElementById('metric-gas').textContent = '12 gwei';

    container.innerHTML = GAS_TIPS.map((g) => `
      <div class="gas-tip">
        <div class="gas-tip__title">${g.title}</div>
        <div class="gas-tip__desc">${g.desc}</div>
        <div class="gas-tip__savings">${g.savings}</div>
      </div>
    `).join('');
  }

  /* ---------- New Protocols ---------- */
  function loadReleases() {
    const container = document.getElementById('releases-list');
    if (!container) return;

    container.innerHTML = NEW_PROTOCOLS.map((p) => `
      <div class="release-item">
        <div class="release-item__name">${p.name} <span class="release-item__chain">${p.chain}</span></div>
        <div class="release-item__desc">${p.desc}</div>
      </div>
    `).join('');
  }

  /* ---------- Protocol Table ---------- */
  function loadProtocolTable() {
    const tbody = document.getElementById('protocol-table-body');
    if (!tbody) return;

    tbody.innerHTML = PROTOCOL_DATA.map((p) => {
      const changeClass = p.change.startsWith('+') ? 'change-positive' : 'change-negative';
      return `
        <tr>
          <td class="proto-name">${p.name}</td>
          <td>${p.chain}</td>
          <td>${p.tvl}</td>
          <td class="${changeClass}">${p.change}</td>
          <td>${p.category}</td>
        </tr>`;
    }).join('');
  }

  /* ============================================================
     HELPERS
     ============================================================ */
  function formatBigNumber(n) {
    if (n >= 1e12) return (n / 1e12).toFixed(1) + 'T';
    if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
    if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
    return n.toString();
  }

  /* ============================================================
     INIT
     ============================================================ */
  function init() {
    initThemeToggle();
    initTicker();
    loadContracts();
    loadYield();
    loadGasTips();
    loadReleases();
    loadProtocolTable();
    loadTvlChart();
    loadEthPrice();

    animateHeroEntrance();
    requestAnimationFrame(() => {
      animatePanelEntrance();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
