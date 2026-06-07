/* ============================================================
   Whale Comparison Dashboard — script.js

   APIs: CoinGecko (free, no key) + Simulated whale data
   Animation: GSAP 3 + ScrollTrigger (CDN)
   Note: Whale addresses and holdings are SIMULATED — real on-chain
         whale tracking requires paid APIs (Nansen, Arkham, etc.)
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Register GSAP Plugins ---------- */
  gsap.registerPlugin(ScrollTrigger);

  /* ---------- Reduced Motion Check ---------- */
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Configuration ---------- */
  const CONFIG = {
    walletAddress: (() => {
      const raw = '{{WALLET_ADDRESS}}';
      if (raw.startsWith('{{')) return '0x742d...F4e2';
      return raw;
    })(),
    heroImageUrl: (() => {
      const raw = '{{HERO_IMAGE_URL}}';
      if (raw.startsWith('{{')) return '';
      return raw;
    })(),
    maxRetries: 2,
    retryBaseDelay: 1500,
  };

  const API = {
    prices: (ids) =>
      `https://pro-api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=${ids}&order=market_cap_desc&sparkline=false`,
  };

  /* ============================================================
     SIMULATED WHALE DATA
     Note: In production, this would come from Nansen, Arkham,
     or on-chain indexers. These are well-known whale addresses
     with simulated portfolio allocations.
     ============================================================ */
  const WHALE_DATABASE = [
    {
      name: 'Galaxy Digital',
      address: '0x7Be2...c8A1',
      holdings: { bitcoin: 35, ethereum: 30, solana: 10, chainlink: 8, uniswap: 7, aave: 5, arbitrum: 5 },
      totalValue: 2_400_000_000,
      recentActions: [
        { action: 'buy', token: 'ETH', amount: '$12.5M', time: '2h ago' },
        { action: 'sell', token: 'SOL', amount: '$3.2M', time: '1d ago' },
      ],
    },
    {
      name: 'Jump Trading',
      address: '0x9B3a...d7F5',
      holdings: { bitcoin: 25, ethereum: 35, solana: 15, avalanche: 8, polygon: 7, optimism: 5, arbitrum: 5 },
      totalValue: 1_800_000_000,
      recentActions: [
        { action: 'buy', token: 'SOL', amount: '$8.1M', time: '4h ago' },
        { action: 'buy', token: 'ARB', amount: '$2.4M', time: '2d ago' },
      ],
    },
    {
      name: 'Wintermute',
      address: '0x4Fd1...a3E9',
      holdings: { bitcoin: 20, ethereum: 25, solana: 20, polygon: 10, uniswap: 10, chainlink: 8, aave: 7 },
      totalValue: 950_000_000,
      recentActions: [
        { action: 'sell', token: 'MATIC', amount: '$5.7M', time: '6h ago' },
        { action: 'buy', token: 'UNI', amount: '$1.8M', time: '3d ago' },
      ],
    },
    {
      name: 'Alameda Remnant',
      address: '0xE2c8...b1D4',
      holdings: { bitcoin: 40, ethereum: 20, solana: 25, avalanche: 5, chainlink: 5, arbitrum: 3, optimism: 2 },
      totalValue: 520_000_000,
      recentActions: [
        { action: 'sell', token: 'BTC', amount: '$15.3M', time: '12h ago' },
      ],
    },
    {
      name: 'Three Arrows (Liquidation)',
      address: '0xA7f3...e6C2',
      holdings: { bitcoin: 30, ethereum: 40, solana: 5, avalanche: 10, polygon: 5, uniswap: 5, aave: 5 },
      totalValue: 310_000_000,
      recentActions: [
        { action: 'sell', token: 'ETH', amount: '$22.1M', time: '5d ago' },
        { action: 'sell', token: 'AVAX', amount: '$4.6M', time: '6d ago' },
      ],
    },
    {
      name: 'Paradigm',
      address: '0x1Bc5...f8A3',
      holdings: { bitcoin: 15, ethereum: 30, solana: 20, uniswap: 15, optimism: 10, arbitrum: 5, aave: 5 },
      totalValue: 3_100_000_000,
      recentActions: [
        { action: 'buy', token: 'OP', amount: '$6.2M', time: '1d ago' },
        { action: 'buy', token: 'UNI', amount: '$4.5M', time: '4d ago' },
      ],
    },
    {
      name: 'a16z Crypto',
      address: '0x5De9...c4B7',
      holdings: { bitcoin: 10, ethereum: 25, solana: 25, uniswap: 15, polygon: 10, optimism: 10, arbitrum: 5 },
      totalValue: 4_500_000_000,
      recentActions: [
        { action: 'buy', token: 'SOL', amount: '$18.0M', time: '3d ago' },
      ],
    },
  ];

  /* Simulated user portfolio (used when no real wallet data) */
  const USER_PORTFOLIO = {
    bitcoin: 25,
    ethereum: 30,
    solana: 20,
    chainlink: 8,
    uniswap: 7,
    aave: 5,
    arbitrum: 5,
  };

  const ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';

  /* ============================================================
     GSAP ANIMATION SYSTEM
     ============================================================ */

  function animateHeroEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.sidebar__hero > *, .sidebar__metrics', { opacity: 1, x: 0 });
      return;
    }

    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

    tl.from('.sidebar__status', { opacity: 0, x: -20, duration: 0.6 })
      .from('.sidebar__title', { opacity: 0, x: -30, duration: 0.8, ease: 'power4.out' }, '-=0.3')
      .from('.sidebar__subtitle', { opacity: 0, x: -20, duration: 0.5 }, '-=0.4')
      .from('.sidebar__metrics .sidebar__metric', { opacity: 0, x: -20, duration: 0.5, stagger: 0.1 }, '-=0.3')
      .from('.sidebar__radar', { opacity: 0, x: -20, duration: 0.6 }, '-=0.2');
  }

  function animateCardEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.panel', { opacity: 1, x: 0 });
      return;
    }

    const panels = gsap.utils.toArray('.panel');
    panels.forEach((panel, i) => {
      gsap.to(panel, {
        opacity: 1,
        x: 0,
        duration: 0.8,
        delay: i * 0.15,
        ease: 'power3.out',
        scrollTrigger: {
          trigger: panel,
          start: 'top 85%',
          once: true,
        },
      });
    });
  }

  function animateCounter(element, targetValue, prefix, suffix, decimals) {
    if (prefersReducedMotion) {
      element.textContent = prefix + targetValue + suffix;
      return;
    }

    const obj = { val: 0 };
    gsap.to(obj, {
      val: targetValue,
      duration: 1.2,
      ease: 'power2.out',
      onUpdate: () => {
        const formatted = decimals > 0
          ? obj.val.toFixed(decimals)
          : Math.round(obj.val).toLocaleString('en-US');
        element.textContent = prefix + formatted + suffix;
      },
      onComplete: () => {
        element.classList.add('value-updated');
        setTimeout(() => element.classList.remove('value-updated'), 800);
      },
    });
  }

  function pulseCard(cardElement) {
    if (prefersReducedMotion || !cardElement) return;
    /* For panel-based layout, pulse the panel itself */
    const panel = cardElement.closest('.panel') || cardElement;
    panel.classList.add('data-pulse');
    setTimeout(() => panel.classList.remove('data-pulse'), 600);
  }

  /* ============================================================
     UTILITY FUNCTIONS
     ============================================================ */

  async function fetchWithRetry(url, retries = CONFIG.maxRetries) {
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
      } catch (err) {
        if (attempt === retries) throw err;
        const delay = CONFIG.retryBaseDelay * (attempt + 1);
        await new Promise((r) => setTimeout(r, delay));
      }
    }
  }

  function formatUSD(value, compact) {
    if (value == null) return '--';
    if (compact) {
      if (value >= 1e12) return '$' + (value / 1e12).toFixed(2) + 'T';
      if (value >= 1e9) return '$' + (value / 1e9).toFixed(2) + 'B';
      if (value >= 1e6) return '$' + (value / 1e6).toFixed(2) + 'M';
    }
    return '$' + value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  }

  /* ---------- Clock ---------- */
  function startClock() {
    const el = document.getElementById('hero-time');
    if (!el) return;
    function tick() {
      const now = new Date();
      el.textContent = now.toLocaleString('en-US', {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      });
    }
    tick();
    setInterval(tick, 1000);
  }

  /* ---------- Skeleton Helpers ---------- */
  function showSkeleton(containerId, count, type) {
    const container = document.getElementById(containerId);
    if (!container) return;
    let html = '';
    for (let i = 0; i < count; i++) {
      if (type === 'whale') {
        html += `
          <div class="whale-item">
            <div class="skeleton" style="width:32px;height:32px;border-radius:50%"></div>
            <div class="whale-item__info">
              <div class="skeleton skeleton--text" style="width:120px"></div>
              <div class="skeleton skeleton--text" style="width:80px;margin-top:4px"></div>
            </div>
            <div class="whale-item__score">
              <div class="skeleton skeleton--value" style="width:60px"></div>
              <div class="skeleton skeleton--bar"></div>
            </div>
          </div>`;
      } else if (type === 'timeline') {
        html += `
          <div class="timeline-item">
            <div class="timeline-item__header">
              <div class="skeleton skeleton--text" style="width:100px"></div>
              <div class="skeleton skeleton--text" style="width:60px"></div>
            </div>
            <div class="skeleton skeleton--text" style="width:200px;margin-top:4px"></div>
          </div>`;
      }
    }
    container.innerHTML = html;
  }

  function showError(containerId, message, retryFn) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = `
      <div class="error-state">
        ${ICON_ALERT}
        <p class="error-state__message">${message}</p>
        ${retryFn ? '<button class="error-state__retry" data-retry="true">Retry</button>' : ''}
      </div>`;
    if (retryFn) {
      const btn = container.querySelector('[data-retry]');
      if (btn) btn.addEventListener('click', retryFn);
    }
  }

  /* ============================================================
     SIMILARITY CALCULATION
     ============================================================ */

  function calculateSimilarity(userHoldings, whaleHoldings) {
    const allTokens = new Set([
      ...Object.keys(userHoldings),
      ...Object.keys(whaleHoldings),
    ]);

    let dotProduct = 0;
    let userMag = 0;
    let whaleMag = 0;

    allTokens.forEach((token) => {
      const u = userHoldings[token] || 0;
      const w = whaleHoldings[token] || 0;
      dotProduct += u * w;
      userMag += u * u;
      whaleMag += w * w;
    });

    if (userMag === 0 || whaleMag === 0) return 0;
    return (dotProduct / (Math.sqrt(userMag) * Math.sqrt(whaleMag))) * 100;
  }

  function getCommonTokens(userHoldings, whaleHoldings) {
    return Object.keys(userHoldings).filter(
      (token) => whaleHoldings[token] && whaleHoldings[token] > 0
    );
  }

  /* ============================================================
     DATA RENDERING
     ============================================================ */

  let radarChart = null;

  function renderWhaleList() {
    const container = document.getElementById('whale-list');
    if (!container) return;

    showSkeleton('whale-list', 5, 'whale');

    /* Calculate similarities */
    const whalesWithSimilarity = WHALE_DATABASE.map((whale) => ({
      ...whale,
      similarity: calculateSimilarity(USER_PORTFOLIO, whale.holdings),
      commonTokens: getCommonTokens(USER_PORTFOLIO, whale.holdings),
    }));

    /* Sort by similarity descending */
    whalesWithSimilarity.sort((a, b) => b.similarity - a.similarity);

    /* Take top 5 */
    const topWhales = whalesWithSimilarity.slice(0, 5);

    /* Update hero metrics */
    const bestMatch = topWhales[0];
    const heroSimilarity = document.getElementById('hero-similarity');
    const heroMatched = document.getElementById('hero-matched');
    const heroCommon = document.getElementById('hero-common');

    if (heroSimilarity) animateCounter(heroSimilarity, bestMatch.similarity, '', '%', 1);
    if (heroMatched) animateCounter(heroMatched, topWhales.length, '', '', 0);
    if (heroCommon) animateCounter(heroCommon, bestMatch.commonTokens.length, '', '', 0);

    /* Render list with slight delay for skeleton effect */
    setTimeout(() => {
      let html = '';
      topWhales.forEach((whale, i) => {
        const rankClass = i === 0 ? 'whale-item__rank--top' : '';
        const tokenTags = whale.commonTokens
          .slice(0, 4)
          .map((t) => `<span class="whale-item__token-tag">${t.substring(0, 4)}</span>`)
          .join('');

        html += `
          <div class="whale-item">
            <div class="whale-item__rank ${rankClass}">#${i + 1}</div>
            <div class="whale-item__info">
              <div class="whale-item__name">${whale.name}</div>
              <div class="whale-item__address">${whale.address}</div>
              <div class="whale-item__tokens">${tokenTags}</div>
            </div>
            <div class="whale-item__score">
              <div class="whale-item__similarity">${whale.similarity.toFixed(1)}%</div>
              <div class="whale-item__bar">
                <div class="whale-item__bar-fill" style="width: ${whale.similarity}%"></div>
              </div>
            </div>
          </div>`;
      });

      container.innerHTML = html;

      /* Animate bar fills */
      if (!prefersReducedMotion) {
        const bars = container.querySelectorAll('.whale-item__bar-fill');
        bars.forEach((bar, i) => {
          const targetWidth = bar.style.width;
          bar.style.width = '0%';
          gsap.to(bar, {
            width: targetWidth,
            duration: 0.8,
            delay: i * 0.1,
            ease: 'power2.out',
          });
        });
      }

      pulseCard(container.closest('.panel'));

      /* Render radar chart for top whale */
      renderRadarChart(topWhales[0]);
    }, 600);

    return whalesWithSimilarity;
  }

  function renderRadarChart(topWhale) {
    const canvas = document.getElementById('radar-chart');
    if (!canvas) return;

    const allTokens = [...new Set([
      ...Object.keys(USER_PORTFOLIO),
      ...Object.keys(topWhale.holdings),
    ])];

    const labels = allTokens.map((t) => t.charAt(0).toUpperCase() + t.slice(1));
    const userData = allTokens.map((t) => USER_PORTFOLIO[t] || 0);
    const whaleData = allTokens.map((t) => topWhale.holdings[t] || 0);

    const accentColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-accent').trim() || '#00e5ff';
    const chartColor2 = getComputedStyle(document.documentElement)
      .getPropertyValue('--chart-3').trim() || '#bf00ff';
    const textColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-text-muted').trim() || 'rgba(255,255,255,0.3)';
    const borderColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-border').trim() || 'rgba(255,255,255,0.06)';

    if (radarChart) radarChart.destroy();

    radarChart = new Chart(canvas, {
      type: 'radar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Your Portfolio',
            data: userData,
            borderColor: accentColor,
            backgroundColor: accentColor.replace(')', ',0.1)').replace('rgb', 'rgba'),
            borderWidth: 2,
            pointRadius: 3,
            pointBackgroundColor: accentColor,
          },
          {
            label: topWhale.name,
            data: whaleData,
            borderColor: chartColor2,
            backgroundColor: chartColor2.replace(')', ',0.1)').replace('rgb', 'rgba'),
            borderWidth: 2,
            pointRadius: 3,
            pointBackgroundColor: chartColor2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: textColor,
              font: { family: "'Satoshi', sans-serif", size: 11 },
              padding: 16,
              boxWidth: 10,
              boxHeight: 10,
              useBorderRadius: true,
              borderRadius: 5,
              pointStyleWidth: 8,
            },
          },
          tooltip: {
            backgroundColor: 'rgba(0,0,0,0.8)',
            titleFont: { family: "'Satoshi', sans-serif" },
            bodyFont: { family: "'JetBrains Mono', monospace", size: 11 },
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.r}%`,
            },
          },
        },
        scales: {
          r: {
            beginAtZero: true,
            max: 45,
            ticks: {
              display: false,
            },
            grid: {
              color: borderColor,
            },
            angleLines: {
              color: borderColor,
            },
            pointLabels: {
              color: textColor,
              font: { family: "'Satoshi', sans-serif", size: 10 },
            },
          },
        },
        animation: prefersReducedMotion ? false : {
          duration: 1000,
          easing: 'easeOutQuart',
        },
      },
    });
  }

  function renderTimeline() {
    const container = document.getElementById('whale-timeline');
    if (!container) return;

    showSkeleton('whale-timeline', 5, 'timeline');

    /* Collect all recent actions from all whales */
    const allActions = [];
    WHALE_DATABASE.forEach((whale) => {
      whale.recentActions.forEach((action) => {
        allActions.push({
          whaleName: whale.name,
          whaleAddress: whale.address,
          ...action,
        });
      });
    });

    setTimeout(() => {
      let html = '';
      allActions.forEach((item) => {
        const actionClass = item.action === 'buy'
          ? 'timeline-item__action--buy'
          : 'timeline-item__action--sell';
        const actionLabel = item.action === 'buy' ? 'Bought' : 'Sold';

        html += `
          <div class="timeline-item">
            <div class="timeline-item__header">
              <span class="timeline-item__action ${actionClass}">${actionLabel} ${item.token}</span>
              <span class="timeline-item__time">${item.time}</span>
            </div>
            <div class="timeline-item__details">
              <div class="timeline-item__detail">
                <span class="timeline-item__detail-label">Whale:</span>
                <span class="timeline-item__detail-value">${item.whaleName}</span>
              </div>
              <div class="timeline-item__detail">
                <span class="timeline-item__detail-label">Amount:</span>
                <span class="timeline-item__detail-value">${item.amount}</span>
              </div>
              <div class="timeline-item__detail">
                <span class="timeline-item__detail-label">Address:</span>
                <span class="timeline-item__detail-value">${item.whaleAddress}</span>
              </div>
            </div>
          </div>`;
      });

      container.innerHTML = html;

      /* Stagger timeline items */
      if (!prefersReducedMotion) {
        const items = container.querySelectorAll('.timeline-item');
        gsap.from(items, {
          opacity: 0,
          x: -20,
          duration: 0.5,
          stagger: 0.08,
          ease: 'power2.out',
        });
      }

      pulseCard(container.closest('.panel'));
    }, 800);
  }

  /* ============================================================
     THEME TOGGLE
     ============================================================ */

  function initThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;

    const saved = localStorage.getItem('whale-theme');
    if (saved === 'light') document.documentElement.setAttribute('data-theme', 'light');

    btn.addEventListener('click', () => {
      const isLight = document.documentElement.getAttribute('data-theme') === 'light';
      if (isLight) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('whale-theme', 'dark');
      } else {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('whale-theme', 'light');
      }

      /* Re-render radar chart with new theme colors */
      const topWhale = WHALE_DATABASE[0];
      if (topWhale) {
        setTimeout(() => renderRadarChart(topWhale), 100);
      }
    });
  }

  /* ============================================================
     HERO IMAGE
     ============================================================ */

  function initHeroImage() {
    /* Split screen layout uses sidebar — no hero bg image needed */
  }

  /* ============================================================
     INIT
     ============================================================ */

  function init() {
    startClock();
    initThemeToggle();
    initHeroImage();
    animateHeroEntrance();

    /* Load data */
    renderWhaleList();
    renderTimeline();

    /* Animate panels after data loads */
    setTimeout(() => {
      animateCardEntrance();
    }, 200);
  }

  /* Wait for DOM */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
