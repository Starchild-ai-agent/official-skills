/* ============================================================
   Gas Fee Tracker — script.js

   APIs:
   - Etherscan Gas Oracle (free, no key required for basic endpoint)
   - CoinGecko (ETH price for USD cost calculation)
   
   Note: Etherscan's free gas oracle may require an API key in some
   regions. If the API fails, simulated gas data is used as fallback.
   The 24h trend chart uses simulated historical data since free
   historical gas APIs are not available without authentication.

   Animation: GSAP 3 + ScrollTrigger (CDN)
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Register GSAP Plugins ---------- */
  gsap.registerPlugin(ScrollTrigger);

  /* ---------- Reduced Motion Check ---------- */
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Configuration ---------- */
  const CONFIG = {
    heroImageUrl: (() => {
      const raw = '{{HERO_IMAGE_URL}}';
      if (raw.startsWith('{{')) return '';
      return raw;
    })(),
    maxRetries: 2,
    retryBaseDelay: 1500,
    refreshInterval: 60_000,
  };

  const API = {
    gasOracle: () =>
      'https://api.etherscan.io/api?module=gastracker&action=gasoracle',
    ethPrice: () =>
      'https://pro-api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currency=usd',
  };

  /* Common transaction gas limits */
  const TX_TYPES = [
    { name: 'ETH Transfer', gasLimit: 21000, icon: '↗' },
    { name: 'ERC-20 Transfer', gasLimit: 65000, icon: '🔄' },
    { name: 'Uniswap Swap', gasLimit: 150000, icon: '⚡' },
    { name: 'NFT Mint', gasLimit: 200000, icon: '🎨' },
    { name: 'Contract Deploy', gasLimit: 1500000, icon: '📦' },
    { name: 'Bridge Transfer', gasLimit: 250000, icon: '🌉' },
  ];

  const ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';

  /* ---------- State ---------- */
  let trendChart = null;
  let ethPriceUsd = 0;
  let gasHistory = [];
  let refreshTimer = null;

  /* ============================================================
     SIMULATED GAS DATA (fallback)
     Used when Etherscan API is unavailable or rate-limited.
     ============================================================ */

  function generateSimulatedGas() {
    const base = 15 + Math.random() * 30;
    return {
      SafeGasPrice: Math.round(base * 0.7).toString(),
      ProposeGasPrice: Math.round(base).toString(),
      FastGasPrice: Math.round(base * 1.5).toString(),
      suggestBaseFee: (base * 0.8).toFixed(2),
    };
  }

  function generateSimulated24hHistory() {
    const now = Date.now();
    const points = [];
    let base = 20 + Math.random() * 15;

    for (let i = 24; i >= 0; i--) {
      const time = now - i * 3600000;
      /* Simulate higher gas during business hours (UTC 14-22 = US daytime) */
      const hour = new Date(time).getUTCHours();
      let multiplier = 1;
      if (hour >= 14 && hour <= 22) multiplier = 1.3 + Math.random() * 0.5;
      else if (hour >= 6 && hour <= 10) multiplier = 1.1 + Math.random() * 0.3;
      else multiplier = 0.6 + Math.random() * 0.3;

      base = base + (Math.random() - 0.5) * 5;
      base = Math.max(8, Math.min(80, base));

      points.push({
        time: new Date(time),
        low: Math.round(base * multiplier * 0.7),
        avg: Math.round(base * multiplier),
        high: Math.round(base * multiplier * 1.5),
      });
    }

    return points;
  }

  /* ============================================================
     GSAP ANIMATION SYSTEM
     ============================================================ */

  function animateHeroEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.gauge-hero__info > *, .gauge-hero__gauge-wrap, .gauge-hero__kpis', { opacity: 1 });
      return;
    }

    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

    tl.from('.gauge-hero__label', { opacity: 0, filter: 'blur(8px)', duration: 0.5 })
      .from('.gauge-hero__title', { opacity: 0, filter: 'blur(8px)', duration: 0.6 }, '-=0.3')
      .from('.gauge-hero__subtitle', { opacity: 0, filter: 'blur(8px)', duration: 0.4 }, '-=0.3')
      .from('.gauge-hero__gauge-wrap', { opacity: 0, filter: 'blur(8px)', duration: 0.7 }, '-=0.4')
      .from('.gauge-hero__kpis', { opacity: 0, filter: 'blur(8px)', duration: 0.6 }, '-=0.3');
  }

  function animateCardEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.metric-card', { opacity: 1, filter: 'blur(0)' });
      return;
    }

    const cards = gsap.utils.toArray('.metric-card');
    cards.forEach((card, i) => {
      gsap.to(card, {
        opacity: 1,
        filter: 'blur(0px)',
        duration: 0.8,
        delay: i * 0.15,
        ease: 'power3.out',
        scrollTrigger: {
          trigger: card,
          start: 'top 85%',
          once: true,
        },
      });
    });
  }

  function animateCounter(element, targetValue, prefix, suffix, decimals) {
    if (prefersReducedMotion) {
      const formatted = decimals > 0
        ? targetValue.toFixed(decimals)
        : Math.round(targetValue).toLocaleString('en-US');
      element.textContent = prefix + formatted + suffix;
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
    const card = cardElement.closest('.metric-card') || cardElement;
    card.classList.add('data-pulse');
    setTimeout(() => card.classList.remove('data-pulse'), 600);
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

  function gweiToUsd(gwei, gasLimit) {
    if (!ethPriceUsd || !gwei) return '--';
    const ethCost = (gwei * gasLimit * 1e-9);
    const usdCost = ethCost * ethPriceUsd;
    if (usdCost < 0.01) return '<$0.01';
    if (usdCost < 1) return '$' + usdCost.toFixed(3);
    return '$' + usdCost.toFixed(2);
  }

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
  function showSkeleton(containerId, type) {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (type === 'cost') {
      let html = '';
      for (let i = 0; i < 6; i++) {
        html += `<div class="cost-item">
          <div class="cost-item__header">
            <div class="skeleton skeleton--text" style="width:100px"></div>
            <div class="skeleton skeleton--text" style="width:50px"></div>
          </div>
          <div class="cost-item__prices">
            <div class="skeleton skeleton--text" style="width:80%"></div>
            <div class="skeleton skeleton--text" style="width:80%"></div>
          </div>
        </div>`;
      }
      container.innerHTML = html;
    } else if (type === 'chart') {
      container.innerHTML = '<div class="skeleton skeleton--chart"></div>';
    } else if (type === 'advice') {
      let html = '';
      for (let i = 0; i < 4; i++) {
        html += `<div class="advice-item">
          <div class="skeleton" style="width:32px;height:32px;border-radius:50%"></div>
          <div class="advice-item__content">
            <div class="skeleton skeleton--text" style="width:120px"></div>
            <div class="skeleton skeleton--text" style="width:200px;margin-top:4px"></div>
          </div>
        </div>`;
      }
      container.innerHTML = html;
    } else if (type === 'gauge') {
      container.innerHTML = `
        <div class="gauge">
          <div class="skeleton" style="width:200px;height:110px;border-radius:100px 100px 0 0"></div>
        </div>
        <div class="skeleton skeleton--text" style="width:80px"></div>`;
    }
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
     GAS GAUGE (Canvas)
     ============================================================ */

  function drawGauge(value, label) {
    const canvas = document.getElementById('gauge-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    const cx = w / 2;
    const cy = h - 10;
    const radius = Math.min(cx, cy) - 10;
    const startAngle = Math.PI;

    /* Background arc segments: Low → Medium → High → Very High */
    const segments = [
      { end: 0.25, color: '#39ff14' },
      { end: 0.50, color: '#6bcb77' },
      { end: 0.70, color: '#ffbe0b' },
      { end: 0.85, color: '#ff8c42' },
      { end: 1.0,  color: '#ff4757' },
    ];

    /* Normalize value: 0-100 Gwei maps to 0-1 */
    const maxGwei = 100;
    const normalizedValue = Math.min(value / maxGwei, 1);

    function drawFrame(progress) {
      ctx.clearRect(0, 0, w, h);

      /* Background arcs */
      let prevEnd = 0;
      segments.forEach((seg) => {
        const a1 = startAngle + prevEnd * Math.PI;
        const a2 = startAngle + seg.end * Math.PI;
        ctx.beginPath();
        ctx.arc(cx, cy, radius, a1, a2);
        ctx.lineWidth = 14;
        ctx.strokeStyle = seg.color;
        ctx.lineCap = 'round';
        ctx.globalAlpha = 0.12;
        ctx.stroke();
        prevEnd = seg.end;
      });

      /* Active arc */
      ctx.globalAlpha = 1;
      const activeGrad = ctx.createLinearGradient(cx - radius, cy, cx + radius, cy);
      activeGrad.addColorStop(0, '#39ff14');
      activeGrad.addColorStop(0.5, '#ffbe0b');
      activeGrad.addColorStop(1, '#ff4757');

      const activeEnd = startAngle + progress * Math.PI;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, startAngle, activeEnd);
      ctx.lineWidth = 14;
      ctx.strokeStyle = activeGrad;
      ctx.lineCap = 'round';
      ctx.stroke();

      /* Needle */
      const needleAngle = startAngle + progress * Math.PI;
      const needleLen = radius - 20;
      const nx = cx + needleLen * Math.cos(needleAngle);
      const ny = cy + needleLen * Math.sin(needleAngle);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(nx, ny);
      ctx.lineWidth = 2;
      ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--color-text').trim() || '#f0ece8';
      ctx.stroke();

      /* Center dot */
      ctx.beginPath();
      ctx.arc(cx, cy, 4, 0, 2 * Math.PI);
      ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--color-text').trim() || '#f0ece8';
      ctx.fill();
    }

    if (prefersReducedMotion) {
      drawFrame(normalizedValue);
    } else {
      const obj = { progress: 0 };
      gsap.to(obj, {
        progress: normalizedValue,
        duration: 1.5,
        ease: 'power3.out',
        onUpdate: () => drawFrame(obj.progress),
      });
    }

    /* Update text elements */
    const valueEl = document.getElementById('gauge-value');
    const labelEl = document.getElementById('gauge-label');
    if (valueEl) animateCounter(valueEl, value, '', '', 0);
    if (labelEl) {
      labelEl.textContent = label;
      if (normalizedValue <= 0.25) labelEl.style.color = '#39ff14';
      else if (normalizedValue <= 0.50) labelEl.style.color = '#6bcb77';
      else if (normalizedValue <= 0.70) labelEl.style.color = '#ffbe0b';
      else if (normalizedValue <= 0.85) labelEl.style.color = '#ff8c42';
      else labelEl.style.color = '#ff4757';
    }
  }

  function getGasLabel(gwei) {
    if (gwei <= 15) return 'Very Low';
    if (gwei <= 30) return 'Low';
    if (gwei <= 50) return 'Moderate';
    if (gwei <= 80) return 'High';
    return 'Very High';
  }

  /* ============================================================
     DATA FETCHING
     ============================================================ */

  let isFirstLoad = true;

  async function fetchGasData() {
    if (isFirstLoad) {
      showSkeleton('gauge-container', 'gauge');
      showSkeleton('cost-grid', 'cost');
      showSkeleton('advice-list', 'advice');
    }

    let gasData;
    let usingSimulated = false;

    /* Try Etherscan API first */
    try {
      const response = await fetchWithRetry(API.gasOracle());
      if (response && response.status === '1' && response.result) {
        gasData = response.result;
      } else {
        throw new Error('Invalid response');
      }
    } catch {
      /* Fallback to simulated data */
      gasData = generateSimulatedGas();
      usingSimulated = true;
    }

    /* Fetch ETH price */
    try {
      const priceData = await fetchWithRetry(API.ethPrice());
      if (priceData && priceData.ethereum) {
        ethPriceUsd = priceData.ethereum.usd;
      }
    } catch {
      /* Use last known price or default */
      if (!ethPriceUsd) ethPriceUsd = 3500;
    }

    const low = parseInt(gasData.SafeGasPrice, 10) || 0;
    const avg = parseInt(gasData.ProposeGasPrice, 10) || 0;
    const high = parseInt(gasData.FastGasPrice, 10) || 0;

    /* Update hero metrics */
    const heroLow = document.getElementById('hero-low');
    const heroAvg = document.getElementById('hero-avg');
    const heroHigh = document.getElementById('hero-high');

    if (heroLow) animateCounter(heroLow, low, '', ' Gwei', 0);
    if (heroAvg) animateCounter(heroAvg, avg, '', ' Gwei', 0);
    if (heroHigh) animateCounter(heroHigh, high, '', ' Gwei', 0);

    /* Draw gauge */
    drawGauge(avg, getGasLabel(avg));

    /* Render cost estimator */
    renderCostGrid(low, avg, high);

    /* Render advice */
    renderAdvice(avg, usingSimulated);

    /* Track history for trend chart */
    gasHistory.push({
      time: new Date(),
      low,
      avg,
      high,
    });

    /* Generate simulated 24h history on first load */
    if (isFirstLoad) {
      const simHistory = generateSimulated24hHistory();
      gasHistory = [...simHistory, ...gasHistory];
      renderTrendChart();
    } else if (gasHistory.length > 1) {
      renderTrendChart();
    }

    isFirstLoad = false;

    /* Pulse gauge card */
    /* Gauge is now in hero, no card to pulse */
  }

  /* ============================================================
     COST ESTIMATOR
     ============================================================ */

  function renderCostGrid(low, avg, high) {
    const container = document.getElementById('cost-grid');
    if (!container) return;

    let html = '';
    TX_TYPES.forEach((tx) => {
      html += `
        <div class="cost-item">
          <div class="cost-item__header">
            <span class="cost-item__name">${tx.icon} ${tx.name}</span>
            <span class="cost-item__gas">${tx.gasLimit.toLocaleString()} gas</span>
          </div>
          <div class="cost-item__prices">
            <div class="cost-item__price-row">
              <span class="cost-item__label">Low</span>
              <span class="cost-item__value cost-item__value--low">${gweiToUsd(low, tx.gasLimit)}</span>
            </div>
            <div class="cost-item__price-row">
              <span class="cost-item__label">Avg</span>
              <span class="cost-item__value cost-item__value--avg">${gweiToUsd(avg, tx.gasLimit)}</span>
            </div>
            <div class="cost-item__price-row">
              <span class="cost-item__label">High</span>
              <span class="cost-item__value cost-item__value--high">${gweiToUsd(high, tx.gasLimit)}</span>
            </div>
          </div>
        </div>`;
    });

    container.innerHTML = html;
    pulseCard(container.closest('.metric-card'));
  }

  /* ============================================================
     TREND CHART
     ============================================================ */

  function renderTrendChart() {
    const container = document.getElementById('trend-chart-container');
    if (!container) return;

    container.innerHTML = '<canvas id="trend-chart" aria-label="24 hour gas price trend chart" role="img"></canvas>';
    const canvas = document.getElementById('trend-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    const accentColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-accent').trim() || '#ff6b35';
    const lowColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-low').trim() || '#39ff14';
    const highColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-high').trim() || '#ff4757';
    const textColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-text-muted').trim() || 'rgba(255,255,255,0.3)';
    const borderColor = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-border').trim() || 'rgba(255,255,255,0.06)';

    const labels = gasHistory.map((p) => p.time);
    const lowData = gasHistory.map((p) => ({ x: p.time, y: p.low }));
    const avgData = gasHistory.map((p) => ({ x: p.time, y: p.avg }));
    const highData = gasHistory.map((p) => ({ x: p.time, y: p.high }));

    if (trendChart) trendChart.destroy();

    trendChart = new Chart(ctx, {
      type: 'line',
      data: {
        datasets: [
          {
            label: 'Low',
            data: lowData,
            borderColor: lowColor,
            backgroundColor: 'transparent',
            borderWidth: 1.5,
            pointRadius: 0,
            tension: 0.3,
            borderDash: [4, 4],
          },
          {
            label: 'Average',
            data: avgData,
            borderColor: accentColor,
            backgroundColor: accentColor.replace(')', ',0.08)').replace('rgb', 'rgba'),
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.3,
            fill: true,
          },
          {
            label: 'High',
            data: highData,
            borderColor: highColor,
            backgroundColor: 'transparent',
            borderWidth: 1.5,
            pointRadius: 0,
            tension: 0.3,
            borderDash: [4, 4],
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            position: 'top',
            align: 'end',
            labels: {
              color: textColor,
              font: { family: "'Inter', sans-serif", size: 11 },
              padding: 16,
              usePointStyle: true,
              pointStyleWidth: 8,
            },
          },
          tooltip: {
            backgroundColor: 'rgba(0,0,0,0.85)',
            titleFont: { family: "'Inter', sans-serif", size: 12 },
            bodyFont: { family: "'JetBrains Mono', monospace", size: 11 },
            padding: 12,
            cornerRadius: 6,
            callbacks: {
              title: (items) => {
                if (!items.length) return '';
                return items[0].raw.x.toLocaleTimeString('en-US', {
                  hour: '2-digit',
                  minute: '2-digit',
                  hour12: false,
                });
              },
              label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y} Gwei`,
            },
          },
        },
        scales: {
          x: {
            type: 'time',
            time: {
              unit: 'hour',
              displayFormats: { hour: 'HH:mm' },
            },
            grid: { color: borderColor, drawBorder: false },
            ticks: {
              color: textColor,
              font: { family: "'JetBrains Mono', monospace", size: 10 },
              maxTicksLimit: 8,
            },
          },
          y: {
            grid: { color: borderColor, drawBorder: false },
            ticks: {
              color: textColor,
              font: { family: "'JetBrains Mono', monospace", size: 10 },
              callback: (val) => val + ' Gwei',
            },
          },
        },
        animation: prefersReducedMotion ? false : {
          duration: 1000,
          easing: 'easeOutQuart',
        },
      },
    });

    pulseCard(container.closest('.metric-card'));
  }

  /* ============================================================
     ADVICE
     ============================================================ */

  function renderAdvice(avgGwei, isSimulated) {
    const container = document.getElementById('advice-list');
    if (!container) return;

    const now = new Date();
    const hour = now.getUTCHours();

    const adviceItems = [];

    /* Current gas level advice */
    if (avgGwei <= 15) {
      adviceItems.push({
        icon: '✅',
        iconClass: 'advice-item__icon--good',
        title: 'Excellent Time to Transact',
        desc: `Gas is very low at ${avgGwei} Gwei. Execute pending transactions now for minimal fees.`,
      });
    } else if (avgGwei <= 30) {
      adviceItems.push({
        icon: '👍',
        iconClass: 'advice-item__icon--good',
        title: 'Good Time to Transact',
        desc: `Gas is reasonable at ${avgGwei} Gwei. Standard transactions are cost-effective.`,
      });
    } else if (avgGwei <= 50) {
      adviceItems.push({
        icon: '⚠️',
        iconClass: 'advice-item__icon--warn',
        title: 'Moderate Gas — Consider Waiting',
        desc: `Gas is at ${avgGwei} Gwei. Non-urgent transactions can wait for lower fees.`,
      });
    } else {
      adviceItems.push({
        icon: '🔴',
        iconClass: 'advice-item__icon--bad',
        title: 'High Gas — Wait If Possible',
        desc: `Gas is elevated at ${avgGwei} Gwei. Only execute urgent transactions.`,
      });
    }

    /* Time-based advice */
    if (hour >= 2 && hour <= 6) {
      adviceItems.push({
        icon: '🌙',
        iconClass: 'advice-item__icon--good',
        title: 'Off-Peak Hours (UTC)',
        desc: 'Currently in the lowest gas window. US and EU markets are closed.',
      });
    } else if (hour >= 14 && hour <= 20) {
      adviceItems.push({
        icon: '📈',
        iconClass: 'advice-item__icon--warn',
        title: 'Peak Hours (UTC)',
        desc: 'US market hours typically see higher gas. Consider waiting until 02:00-06:00 UTC.',
      });
    } else {
      adviceItems.push({
        icon: '⏰',
        iconClass: 'advice-item__icon--good',
        title: 'Moderate Hours (UTC)',
        desc: 'Gas is typically moderate now. Best window is 02:00-06:00 UTC for lowest fees.',
      });
    }

    /* Savings tip */
    adviceItems.push({
      icon: '💡',
      iconClass: 'advice-item__icon--good',
      title: 'Pro Tip: Use EIP-1559',
      desc: 'Set a max fee slightly above base fee with a small priority fee. Overpayment is refunded.',
    });

    /* Simulated data notice */
    if (isSimulated) {
      adviceItems.push({
        icon: 'ℹ️',
        iconClass: 'advice-item__icon--warn',
        title: 'Using Simulated Data',
        desc: 'Etherscan API is unavailable. Displayed gas prices are simulated for demonstration.',
      });
    }

    let html = '';
    adviceItems.forEach((item) => {
      html += `
        <div class="advice-item">
          <div class="advice-item__icon ${item.iconClass}">${item.icon}</div>
          <div class="advice-item__content">
            <div class="advice-item__title">${item.title}</div>
            <div class="advice-item__desc">${item.desc}</div>
          </div>
        </div>`;
    });

    container.innerHTML = html;

    /* Stagger advice items */
    if (!prefersReducedMotion) {
      const items = container.querySelectorAll('.advice-item');
      gsap.from(items, {
        opacity: 0,
        x: -20,
        duration: 0.5,
        stagger: 0.08,
        ease: 'power2.out',
      });
    }

    pulseCard(container.closest('.metric-card'));
  }

  /* ============================================================
     THEME TOGGLE
     ============================================================ */

  function initThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;

    const saved = localStorage.getItem('gas-tracker-theme');
    if (saved === 'light') document.documentElement.setAttribute('data-theme', 'light');

    btn.addEventListener('click', () => {
      const isLight = document.documentElement.getAttribute('data-theme') === 'light';
      if (isLight) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('gas-tracker-theme', 'dark');
      } else {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('gas-tracker-theme', 'light');
      }

      /* Re-render chart and gauge with new theme colors */
      setTimeout(() => {
        if (gasHistory.length > 0) renderTrendChart();
        const avgEl = document.getElementById('hero-avg');
        if (avgEl) {
          const avgText = avgEl.textContent;
          const avgVal = parseInt(avgText, 10);
          if (!isNaN(avgVal)) drawGauge(avgVal, getGasLabel(avgVal));
        }
      }, 100);
    });
  }

  /* ============================================================
     HERO IMAGE
     ============================================================ */

  function initHeroImage() {
    /* Gauge hero layout — no background image */
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
    fetchGasData();

    /* Animate cards after data loads */
    setTimeout(() => {
      animateCardEntrance();
    }, 200);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();