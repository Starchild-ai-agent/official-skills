/* ============================================================
   Token Unlock Calendar — script.js
   
   APIs: CoinGecko (free, no key) for current prices
   Mock Data: Built-in unlock schedules for major tokens
   Animation: GSAP 3 + ScrollTrigger (CDN)
   Layout: A13 Calendar + H13 Countdown Hero
   Entrance: D15 clip-path inset reveal
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Register GSAP Plugins ---------- */
  gsap.registerPlugin(ScrollTrigger);

  /* ---------- Reduced Motion Check ---------- */
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Configuration ---------- */
  const CONFIG = {
    trackedTokens: (() => {
      try {
        const raw = '{{TRACKED_TOKENS}}';
        if (raw.startsWith('{{')) return ['arbitrum', 'optimism', 'aptos', 'sui', 'jito', 'starknet', 'sei-network', 'celestia'];
        return JSON.parse(raw);
      } catch {
        return ['arbitrum', 'optimism', 'aptos', 'sui', 'jito', 'starknet', 'sei-network', 'celestia'];
      }
    })(),
    refreshIntervals: {
      prices: 60_000,
    },
    maxRetries: 2,
    retryBaseDelay: 1500,
  };

  const API = {
    prices: (ids) =>
      `https://pro-api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=${ids}&order=market_cap_desc&sparkline=false`,
  };

  const ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';

  /* ============================================================
     MOCK DATA — Token Unlock Schedules
     ============================================================ */
  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth();

  function generateUnlockSchedule() {
    const tokens = [
      {
        id: 'arbitrum', symbol: 'ARB', name: 'Arbitrum',
        totalSupply: 10_000_000_000, circulatingSupply: 3_250_000_000,
        unlocks: [
          { daysFromNow: 3, amount: 92_650_000, type: 'Team & Advisors' },
          { daysFromNow: 12, amount: 43_800_000, type: 'Ecosystem' },
          { daysFromNow: 34, amount: 92_650_000, type: 'Team & Advisors' },
          { daysFromNow: 65, amount: 43_800_000, type: 'Ecosystem' },
        ],
      },
      {
        id: 'optimism', symbol: 'OP', name: 'Optimism',
        totalSupply: 4_294_967_296, circulatingSupply: 1_350_000_000,
        unlocks: [
          { daysFromNow: 7, amount: 31_340_000, type: 'Core Contributors' },
          { daysFromNow: 21, amount: 15_600_000, type: 'Ecosystem Fund' },
          { daysFromNow: 38, amount: 31_340_000, type: 'Core Contributors' },
          { daysFromNow: 52, amount: 15_600_000, type: 'Ecosystem Fund' },
        ],
      },
      {
        id: 'aptos', symbol: 'APT', name: 'Aptos',
        totalSupply: 1_084_452_397, circulatingSupply: 490_000_000,
        unlocks: [
          { daysFromNow: 5, amount: 11_310_000, type: 'Foundation' },
          { daysFromNow: 18, amount: 8_230_000, type: 'Community' },
          { daysFromNow: 36, amount: 11_310_000, type: 'Foundation' },
          { daysFromNow: 67, amount: 8_230_000, type: 'Community' },
        ],
      },
      {
        id: 'sui', symbol: 'SUI', name: 'Sui',
        totalSupply: 10_000_000_000, circulatingSupply: 2_760_000_000,
        unlocks: [
          { daysFromNow: 2, amount: 64_190_000, type: 'Series A/B Investors' },
          { daysFromNow: 15, amount: 28_000_000, type: 'Community Reserve' },
          { daysFromNow: 33, amount: 64_190_000, type: 'Series A/B Investors' },
          { daysFromNow: 60, amount: 28_000_000, type: 'Community Reserve' },
        ],
      },
      {
        id: 'jito', symbol: 'JTO', name: 'Jito',
        totalSupply: 1_000_000_000, circulatingSupply: 135_000_000,
        unlocks: [
          { daysFromNow: 9, amount: 28_570_000, type: 'Core Contributors' },
          { daysFromNow: 25, amount: 11_900_000, type: 'Ecosystem Growth' },
          { daysFromNow: 40, amount: 28_570_000, type: 'Core Contributors' },
        ],
      },
      {
        id: 'starknet', symbol: 'STRK', name: 'Starknet',
        totalSupply: 10_000_000_000, circulatingSupply: 1_800_000_000,
        unlocks: [
          { daysFromNow: 6, amount: 64_000_000, type: 'Early Contributors' },
          { daysFromNow: 20, amount: 35_000_000, type: 'Grants' },
          { daysFromNow: 37, amount: 64_000_000, type: 'Early Contributors' },
          { daysFromNow: 68, amount: 35_000_000, type: 'Grants' },
        ],
      },
      {
        id: 'sei-network', symbol: 'SEI', name: 'Sei',
        totalSupply: 10_000_000_000, circulatingSupply: 3_400_000_000,
        unlocks: [
          { daysFromNow: 11, amount: 55_000_000, type: 'Private Sale' },
          { daysFromNow: 28, amount: 25_000_000, type: 'Ecosystem Reserve' },
          { daysFromNow: 42, amount: 55_000_000, type: 'Private Sale' },
        ],
      },
      {
        id: 'celestia', symbol: 'TIA', name: 'Celestia',
        totalSupply: 1_000_000_000, circulatingSupply: 220_000_000,
        unlocks: [
          { daysFromNow: 4, amount: 42_860_000, type: 'Series A/B Investors' },
          { daysFromNow: 16, amount: 17_500_000, type: 'R&D & Ecosystem' },
          { daysFromNow: 35, amount: 42_860_000, type: 'Series A/B Investors' },
          { daysFromNow: 66, amount: 17_500_000, type: 'R&D & Ecosystem' },
        ],
      },
    ];

    const tracked = tokens.filter((t) => CONFIG.trackedTokens.includes(t.id));

    return tracked.map((token) => ({
      ...token,
      unlocks: token.unlocks.map((u) => {
        const date = new Date(now);
        date.setDate(date.getDate() + u.daysFromNow);
        date.setHours(14, 0, 0, 0);
        return {
          ...u,
          date,
          pctOfCirculating: ((u.amount / token.circulatingSupply) * 100),
        };
      }),
    }));
  }

  const HISTORICAL_PERFORMANCE = [
    { token: 'ARB', change: -8.2, period: '7d', unlockPct: 2.85 },
    { token: 'OP', change: -5.4, period: '7d', unlockPct: 2.32 },
    { token: 'APT', change: -12.1, period: '7d', unlockPct: 2.31 },
    { token: 'SUI', change: -3.7, period: '7d', unlockPct: 2.33 },
    { token: 'JTO', change: -18.5, period: '7d', unlockPct: 21.16 },
    { token: 'STRK', change: -6.9, period: '7d', unlockPct: 3.56 },
    { token: 'TIA', change: -15.3, period: '7d', unlockPct: 19.48 },
    { token: 'SEI', change: -2.1, period: '7d', unlockPct: 1.62 },
  ];

  const unlockData = generateUnlockSchedule();
  let tokenPrices = {};
  let calendarMonth = currentMonth;
  let calendarYear = currentYear;

  /* ============================================================
     GSAP ANIMATION SYSTEM — D15 clip-path inset reveal
     ============================================================ */

  function animateHeroEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.hero__content > *', { opacity: 1, y: 0 });
      return;
    }

    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

    tl.from('.hero__status-bar', { opacity: 0, y: 20, duration: 0.6 })
      .from('.hero__eyebrow', { opacity: 0, y: 12, duration: 0.4 }, '-=0.3')
      .from('.hero__title', { opacity: 0, y: 30, duration: 0.7, ease: 'power4.out' }, '-=0.3')
      .from('.hero__countdown-block', { opacity: 0, scale: 0.95, duration: 0.8 }, '-=0.3')
      .from('.hero__kpi-row', { opacity: 0, y: 20, duration: 0.5 }, '-=0.3');
  }

  function animateCardEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.cal-card, .kpi-strip__item', { opacity: 1, clipPath: 'inset(0)' });
      return;
    }

    /* D15: clip-path inset(10%) → inset(0) */
    const elements = gsap.utils.toArray('.cal-card, .kpi-strip__item');
    elements.forEach((el, i) => {
      gsap.to(el, {
        opacity: 1,
        clipPath: 'inset(0%)',
        duration: 0.7,
        delay: i * 0.08,
        ease: 'power3.out',
        scrollTrigger: {
          trigger: el,
          start: 'top 88%',
          once: true,
        },
      });
    });
  }

  function initHeroParallax() {
    if (prefersReducedMotion) return;

    gsap.to('.hero__grid-dots', {
      yPercent: 15,
      ease: 'none',
      scrollTrigger: {
        trigger: '.hero',
        start: 'top top',
        end: 'bottom top',
        scrub: 1,
      },
    });
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
      if (value >= 1e3) return '$' + (value / 1e3).toFixed(1) + 'K';
    }
    if (value >= 1) return '$' + value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (value >= 0.01) return '$' + value.toFixed(4);
    return '$' + value.toFixed(8);
  }

  function formatNumber(value, compact) {
    if (value == null) return '--';
    if (compact) {
      if (value >= 1e9) return (value / 1e9).toFixed(2) + 'B';
      if (value >= 1e6) return (value / 1e6).toFixed(2) + 'M';
      if (value >= 1e3) return (value / 1e3).toFixed(1) + 'K';
    }
    return value.toLocaleString('en-US');
  }

  function formatPercent(value) {
    if (value == null) return '--';
    const sign = value >= 0 ? '+' : '';
    return sign + value.toFixed(2) + '%';
  }

  function getImpactLevel(pctOfCirculating) {
    if (pctOfCirculating >= 5) return 'high';
    if (pctOfCirculating >= 2) return 'medium';
    return 'low';
  }

  function getImpactLabel(level) {
    return { high: 'HIGH', medium: 'MED', low: 'LOW' }[level] || 'LOW';
  }

  function formatCountdown(targetDate) {
    const diff = targetDate - new Date();
    if (diff <= 0) return 'NOW';
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    if (days > 0) return `${days}d ${hours}h`;
    const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}h ${mins}m`;
  }

  function formatDate(date) {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  /* ---------- Clock ---------- */
  function startClock() {
    const el = document.getElementById('hero-time');
    if (!el) return;
    function tick() {
      const d = new Date();
      el.textContent = d.toLocaleString('en-US', {
        weekday: 'short', year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
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
      if (type === 'unlock') {
        html += `
          <div class="unlock-item">
            <div class="skeleton" style="width:28px;height:28px;border-radius:50%"></div>
            <div style="flex:1"><div class="skeleton skeleton--text"></div><div class="skeleton" style="width:40%;height:0.7rem"></div></div>
            <div class="skeleton" style="width:60px;height:16px"></div>
            <div class="skeleton" style="width:50px;height:16px"></div>
          </div>`;
      } else if (type === 'impact') {
        html += `
          <div class="impact-item">
            <div class="skeleton" style="width:40px;height:22px;border-radius:4px"></div>
            <div style="flex:1"><div class="skeleton skeleton--text"></div></div>
            <div class="skeleton" style="width:50px;height:24px"></div>
          </div>`;
      } else if (type === 'perf') {
        html += `
          <div class="perf-item">
            <div class="skeleton" style="width:40px;height:16px"></div>
            <div class="skeleton" style="flex:1;height:6px"></div>
            <div class="skeleton" style="width:50px;height:16px"></div>
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
     DATA FETCHERS
     ============================================================ */

  let isFirstLoad = true;

  async function fetchPrices() {
    try {
      const ids = CONFIG.trackedTokens.join(',');
      const data = await fetchWithRetry(API.prices(ids));

      if (data && data.length > 0) {
        data.forEach((coin) => {
          tokenPrices[coin.id] = coin.current_price;
        });
      }
    } catch (err) {
      /* Prices are supplementary; continue with mock data */
    }

    renderAll();
  }

  /* ============================================================
     RENDERERS
     ============================================================ */

  function renderAll() {
    renderHeroCountdown();
    renderHeroKPIs();
    renderKPIStrip();
    renderCalendar();
    renderUnlockList();
    renderImpactSummary();
    renderPerformance();

    if (isFirstLoad) {
      isFirstLoad = false;
    }
  }

  /* ---------- Hero Countdown (H13) ---------- */
  function renderHeroCountdown() {
    const allUnlocks = unlockData.flatMap((t) =>
      t.unlocks.map((u) => ({ ...u, tokenId: t.id, symbol: t.symbol, name: t.name }))
    ).sort((a, b) => a.date - b.date);

    const nextUnlock = allUnlocks.find((u) => u.date > now);
    if (!nextUnlock) return;

    const diff = nextUnlock.date - new Date();
    const days = Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)));
    const hours = Math.max(0, Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)));
    const mins = Math.max(0, Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60)));

    const daysEl = document.getElementById('cd-days');
    const hoursEl = document.getElementById('cd-hours');
    const minsEl = document.getElementById('cd-mins');
    const tokenEl = document.getElementById('cd-token-name');

    if (daysEl) daysEl.textContent = String(days).padStart(2, '0');
    if (hoursEl) hoursEl.textContent = String(hours).padStart(2, '0');
    if (minsEl) minsEl.textContent = String(mins).padStart(2, '0');
    if (tokenEl) tokenEl.textContent = `${nextUnlock.symbol} — ${nextUnlock.name} · ${nextUnlock.type}`;
  }

  /* ---------- Hero KPIs ---------- */
  function renderHeroKPIs() {
    const allUnlocks = unlockData.flatMap((t) =>
      t.unlocks.map((u) => ({ ...u, tokenId: t.id, symbol: t.symbol }))
    ).sort((a, b) => a.date - b.date);

    /* This month total value */
    const thisMonthUnlocks = allUnlocks.filter((u) =>
      u.date.getMonth() === currentMonth && u.date.getFullYear() === currentYear
    );
    let monthValue = 0;
    thisMonthUnlocks.forEach((u) => {
      const price = tokenPrices[u.tokenId] || 1;
      monthValue += u.amount * price;
    });

    const monthEl = document.getElementById('hero-month-value');
    if (monthEl) monthEl.textContent = formatUSD(monthValue, true);

    const eventsEl = document.getElementById('hero-events-count');
    if (eventsEl) eventsEl.textContent = allUnlocks.length.toString();
  }

  /* ---------- KPI Strip ---------- */
  function renderKPIStrip() {
    const container = document.getElementById('kpi-strip');
    if (!container) return;

    const allUnlocks = unlockData.flatMap((t) =>
      t.unlocks.map((u) => ({ ...u, tokenId: t.id, symbol: t.symbol }))
    ).sort((a, b) => a.date - b.date);

    const upcoming7d = allUnlocks.filter((u) => {
      const diff = u.date - now;
      return diff > 0 && diff <= 7 * 24 * 60 * 60 * 1000;
    });

    const upcoming30d = allUnlocks.filter((u) => {
      const diff = u.date - now;
      return diff > 0 && diff <= 30 * 24 * 60 * 60 * 1000;
    });

    let value7d = 0;
    upcoming7d.forEach((u) => { value7d += u.amount * (tokenPrices[u.tokenId] || 1); });

    let value30d = 0;
    upcoming30d.forEach((u) => { value30d += u.amount * (tokenPrices[u.tokenId] || 1); });

    const highImpact = allUnlocks.filter((u) => u.pctOfCirculating >= 5 && u.date > now).length;

    container.innerHTML = `
      <div class="kpi-strip__item">
        <span class="kpi-strip__label">7D UNLOCKS</span>
        <span class="kpi-strip__value">${upcoming7d.length}</span>
      </div>
      <div class="kpi-strip__item">
        <span class="kpi-strip__label">7D VALUE</span>
        <span class="kpi-strip__value">${formatUSD(value7d, true)}</span>
      </div>
      <div class="kpi-strip__item">
        <span class="kpi-strip__label">30D VALUE</span>
        <span class="kpi-strip__value">${formatUSD(value30d, true)}</span>
      </div>
      <div class="kpi-strip__item">
        <span class="kpi-strip__label">HIGH IMPACT</span>
        <span class="kpi-strip__value" style="color:var(--impact-high)">${highImpact}</span>
      </div>
    `;
  }

  /* ---------- Calendar ---------- */
  function renderCalendar() {
    const container = document.getElementById('calendar-grid');
    if (!container) return;

    const monthLabel = document.getElementById('cal-month-label');
    if (monthLabel) {
      const d = new Date(calendarYear, calendarMonth, 1);
      monthLabel.textContent = d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    }

    const firstDay = new Date(calendarYear, calendarMonth, 1).getDay();
    const daysInMonth = new Date(calendarYear, calendarMonth + 1, 0).getDate();
    const today = new Date();

    const unlockMap = {};
    unlockData.forEach((token) => {
      token.unlocks.forEach((u) => {
        if (u.date.getMonth() === calendarMonth && u.date.getFullYear() === calendarYear) {
          const day = u.date.getDate();
          if (!unlockMap[day]) unlockMap[day] = [];
          unlockMap[day].push({ symbol: token.symbol, ...u });
        }
      });
    });

    let html = '<div class="calendar-grid__header">';
    ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].forEach((d) => {
      html += `<div class="calendar-grid__day-label">${d}</div>`;
    });
    html += '</div><div class="calendar-grid__body">';

    for (let i = 0; i < firstDay; i++) {
      html += '<div class="calendar-day calendar-day--empty"></div>';
    }

    for (let day = 1; day <= daysInMonth; day++) {
      const isToday = day === today.getDate() && calendarMonth === today.getMonth() && calendarYear === today.getFullYear();
      const hasUnlock = unlockMap[day];
      let classes = 'calendar-day';
      if (isToday) classes += ' calendar-day--today';
      if (hasUnlock) classes += ' calendar-day--has-unlock';

      html += `<div class="${classes}" ${hasUnlock ? `title="${hasUnlock.map((u) => u.symbol).join(', ')} unlock"` : ''}>`;
      html += `<span>${day}</span>`;
      if (hasUnlock) {
        html += `<span class="calendar-day__dot" aria-hidden="true"></span>`;
        if (hasUnlock.length > 1) {
          html += `<span class="calendar-day__count">${hasUnlock.length}</span>`;
        }
      }
      html += '</div>';
    }

    html += '</div>';
    container.innerHTML = html;

    if (isFirstLoad && !prefersReducedMotion) {
      gsap.from('.calendar-day:not(.calendar-day--empty)', {
        opacity: 0,
        scale: 0.8,
        stagger: 0.015,
        duration: 0.3,
        ease: 'power3.out',
      });
    }
  }

  /* ---------- Upcoming Unlocks List ---------- */
  function renderUnlockList() {
    const container = document.getElementById('unlock-list');
    if (!container) return;

    if (isFirstLoad) {
      showSkeleton('unlock-list', 6, 'unlock');
      setTimeout(() => doRenderUnlockList(container), 300);
    } else {
      doRenderUnlockList(container);
    }
  }

  function doRenderUnlockList(container) {
    const allUnlocks = unlockData.flatMap((t) =>
      t.unlocks.map((u) => ({
        ...u,
        tokenId: t.id,
        symbol: t.symbol,
        name: t.name,
        circulatingSupply: t.circulatingSupply,
      }))
    ).sort((a, b) => a.date - b.date);

    if (allUnlocks.length === 0) {
      showError('unlock-list', 'No upcoming unlock events found');
      return;
    }

    let html = '';
    allUnlocks.forEach((u) => {
      const price = tokenPrices[u.tokenId] || 0;
      const usdValue = price > 0 ? u.amount * price : 0;
      const impact = getImpactLevel(u.pctOfCirculating);
      const impactClass = `unlock-item__pct--${impact}`;

      html += `
        <div class="unlock-item">
          <div class="unlock-item__icon">${u.symbol.substring(0, 2)}</div>
          <div class="unlock-item__info">
            <div class="unlock-item__name">${u.name} — ${u.type}</div>
            <div class="unlock-item__date">${formatDate(u.date)} &bull; ${formatCountdown(u.date)}</div>
          </div>
          <div>
            <div class="unlock-item__amount">${formatNumber(u.amount, true)}</div>
            <div class="unlock-item__value">${usdValue > 0 ? formatUSD(usdValue, true) : '--'}</div>
          </div>
          <div class="unlock-item__pct ${impactClass}">${u.pctOfCirculating.toFixed(2)}%</div>
        </div>`;
    });

    container.innerHTML = html;

    if (isFirstLoad && !prefersReducedMotion) {
      gsap.from('.unlock-item', {
        opacity: 0,
        x: -16,
        stagger: 0.06,
        duration: 0.4,
        ease: 'power3.out',
      });
    }
  }

  /* ---------- Impact Summary ---------- */
  function renderImpactSummary() {
    const container = document.getElementById('impact-summary');
    if (!container) return;

    if (isFirstLoad) {
      showSkeleton('impact-summary', 4, 'impact');
      setTimeout(() => doRenderImpactSummary(container), 400);
    } else {
      doRenderImpactSummary(container);
    }
  }

  function doRenderImpactSummary(container) {
    const nextPerToken = unlockData.map((t) => {
      const next = t.unlocks.find((u) => u.date > now);
      if (!next) return null;
      return {
        symbol: t.symbol,
        name: t.name,
        tokenId: t.id,
        pctOfCirculating: next.pctOfCirculating,
        date: next.date,
        amount: next.amount,
        type: next.type,
      };
    }).filter(Boolean).sort((a, b) => b.pctOfCirculating - a.pctOfCirculating);

    if (nextPerToken.length === 0) {
      showError('impact-summary', 'No upcoming events to assess');
      return;
    }

    let html = '';
    nextPerToken.forEach((item) => {
      const impact = getImpactLevel(item.pctOfCirculating);
      const badgeClass = `impact-item__badge--${impact}`;
      const pctColor = impact === 'high' ? 'var(--impact-high)' : impact === 'medium' ? 'var(--impact-medium)' : 'var(--impact-low)';

      html += `
        <div class="impact-item">
          <span class="impact-item__badge ${badgeClass}">${getImpactLabel(impact)}</span>
          <div class="impact-item__info">
            <div class="impact-item__token">${item.symbol} — ${item.name}</div>
            <div class="impact-item__detail">${formatDate(item.date)} &bull; ${item.type}</div>
          </div>
          <div class="impact-item__pct" style="color:${pctColor}">${item.pctOfCirculating.toFixed(2)}%</div>
        </div>`;
    });

    container.innerHTML = html;

    if (isFirstLoad && !prefersReducedMotion) {
      gsap.from('.impact-item', {
        opacity: 0,
        y: 16,
        scale: 0.96,
        stagger: 0.1,
        duration: 0.5,
        ease: 'power3.out',
      });
    }
  }

  /* ---------- Historical Performance ---------- */
  function renderPerformance() {
    const container = document.getElementById('performance-list');
    if (!container) return;

    if (isFirstLoad) {
      showSkeleton('performance-list', 6, 'perf');
      setTimeout(() => doRenderPerformance(container), 500);
    } else {
      doRenderPerformance(container);
    }
  }

  function doRenderPerformance(container) {
    let html = '';
    HISTORICAL_PERFORMANCE.forEach((item) => {
      const isNeg = item.change < 0;
      const barWidth = Math.min(Math.abs(item.change) * 3, 100);
      const barClass = isNeg ? 'perf-item__bar--negative' : 'perf-item__bar--positive';
      const changeColor = isNeg ? 'var(--color-danger)' : 'var(--color-success)';

      html += `
        <div class="perf-item">
          <span class="perf-item__token">${item.token}</span>
          <div class="perf-item__bar-container">
            <div class="perf-item__bar ${barClass}" style="width:${barWidth}%"></div>
          </div>
          <span class="perf-item__change" style="color:${changeColor}">${formatPercent(item.change)}</span>
          <span class="perf-item__period">${item.period}</span>
        </div>`;
    });

    container.innerHTML = html;

    if (isFirstLoad && !prefersReducedMotion) {
      gsap.from('.perf-item', {
        opacity: 0,
        x: 16,
        stagger: 0.06,
        duration: 0.4,
        ease: 'power3.out',
      });

      gsap.from('.perf-item__bar', {
        width: 0,
        stagger: 0.06,
        duration: 0.8,
        ease: 'power3.out',
        delay: 0.2,
      });
    }
  }

  /* ---------- Calendar Navigation ---------- */
  function initCalendarNav() {
    const prevBtn = document.getElementById('cal-prev');
    const nextBtn = document.getElementById('cal-next');

    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        calendarMonth--;
        if (calendarMonth < 0) {
          calendarMonth = 11;
          calendarYear--;
        }
        renderCalendar();
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        calendarMonth++;
        if (calendarMonth > 11) {
          calendarMonth = 0;
          calendarYear++;
        }
        renderCalendar();
      });
    }
  }

  /* ---------- Countdown Updater ---------- */
  function startCountdownUpdater() {
    setInterval(() => {
      renderHeroCountdown();
    }, 60_000);
  }

  /* ---------- Hero Image Fallback ---------- */
  function setupHeroImage() {
    const heroImageUrl = '{{HERO_IMAGE_URL}}';
    if (heroImageUrl && !heroImageUrl.startsWith('{{')) {
      const bgDiv = document.querySelector('.hero__bg-image');
      if (bgDiv) {
        bgDiv.style.backgroundImage = `url('${heroImageUrl}')`;
        bgDiv.style.opacity = '0.15';
      }
    }
  }

  /* ---------- Theme Toggle ---------- */
  function initTheme() {
    const stored = localStorage.getItem('token-unlock-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = stored || (prefersDark ? 'dark' : 'light');

    if (theme === 'light') {
      document.documentElement.setAttribute('data-theme', 'light');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }

    const btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.addEventListener('click', () => {
        const isLight = document.documentElement.getAttribute('data-theme') === 'light';
        if (isLight) {
          document.documentElement.removeAttribute('data-theme');
          localStorage.setItem('token-unlock-theme', 'dark');
        } else {
          document.documentElement.setAttribute('data-theme', 'light');
          localStorage.setItem('token-unlock-theme', 'light');
        }
      });
    }
  }

  /* ---------- Auto-Refresh (disabled — paid API) ---------- */
  function scheduleRefresh() {
    // No auto-refresh — CoinGecko is paid per request
  }

  /* ============================================================
     INIT
     ============================================================ */
  function init() {
    initTheme();
    startClock();
    setupHeroImage();
    initCalendarNav();

    /* GSAP Animations */
    animateHeroEntrance();
    animateCardEntrance();
    initHeroParallax();

    /* Fetch prices and render */
    fetchPrices();

    /* Start countdown updater */
    startCountdownUpdater();

    /* Schedule auto-refresh */
    scheduleRefresh();
  }

  /* Wait for DOM + GSAP */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();