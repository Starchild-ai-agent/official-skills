/* ============================================================
   Impermanent Loss Calculator — script.js

   APIs: CoinGecko (token prices)
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
    trackedTokens: (() => {
      try {
        const raw = '{{TRACKED_TOKENS}}';
        if (raw.startsWith('{{')) return ['ethereum', 'bitcoin', 'solana'];
        return JSON.parse(raw);
      } catch {
        return ['ethereum', 'bitcoin', 'solana'];
      }
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
    prices: (ids) => `https://api.coingecko.com/api/v3/simple/price?ids=${ids}&vs_currencies=usd`,
  };

  /* ---------- State ---------- */
  let ilChart = null;
  let breakevenChart = null;
  let lastCalcResult = null;

  /* ============================================================
     GSAP ANIMATION SYSTEM
     ============================================================ */

  function animateHeroEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.hero__content > *, .hero__il-preview', { opacity: 1 });
      return;
    }
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    tl.from('.hero__label', { opacity: 0, x: 30, duration: 0.5 })
      .from('.hero__title', { opacity: 0, x: 30, duration: 0.6 }, '-=0.3')
      .from('.hero__subtitle', { opacity: 0, x: 30, duration: 0.4 }, '-=0.3')
      .from('.hero__il-preview', { opacity: 0, scale: 0.9, duration: 0.7 }, '-=0.4');
  }

  function animateCardEntrance() {
    if (prefersReducedMotion) {
      gsap.set('[data-animate]', { opacity: 1, x: 0 });
      return;
    }
    gsap.utils.toArray('[data-animate]').forEach((el, i) => {
      gsap.to(el, {
        scrollTrigger: {
          trigger: el,
          start: 'top 88%',
          toggleActions: 'play none none none',
        },
        opacity: 1,
        x: 0,
        duration: 0.6,
        delay: i * 0.08,
        ease: 'power3.out',
      });
    });
  }

  /* ============================================================
     THEME TOGGLE
     ============================================================ */

  function initThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    const stored = localStorage.getItem('il-theme');
    if (stored === 'dark') document.documentElement.setAttribute('data-theme', 'dark');

    btn.addEventListener('click', () => {
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      if (isDark) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('il-theme', 'light');
      } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('il-theme', 'dark');
      }
      updateChartThemes();
    });
  }

  /* ============================================================
     HERO INTERACTIVE SLIDER
     ============================================================ */

  function initHeroSlider() {
    const slider = document.getElementById('hero-slider');
    const valLabel = document.getElementById('hero-slider-val');
    const ringFill = document.getElementById('hero-ring-fill');
    const ilValue = document.getElementById('hero-il-value');

    slider.addEventListener('input', () => {
      const priceChange = (parseInt(slider.value, 10) - 100) / 100;
      const pctLabel = priceChange >= 0 ? `+${(priceChange * 100).toFixed(0)}%` : `${(priceChange * 100).toFixed(0)}%`;
      valLabel.textContent = pctLabel;

      const ratio = 1 + priceChange;
      const il = ratio > 0 ? 2 * Math.sqrt(ratio) / (1 + ratio) - 1 : 0;
      const ilPct = Math.abs(il * 100);

      ilValue.textContent = `-${ilPct.toFixed(2)}%`;

      const circumference = 326.73;
      const offset = circumference - (ilPct / 50) * circumference;
      ringFill.style.strokeDashoffset = Math.max(0, offset);
    });
  }

  /* ============================================================
     IMPERMANENT LOSS CALCULATION
     ============================================================ */

  function calculateIL(initialPriceA, initialPriceB, currentPriceA, currentPriceB, investment) {
    const initialRatio = initialPriceA / initialPriceB;
    const currentRatio = currentPriceA / currentPriceB;
    const priceRatio = currentRatio / initialRatio;

    // IL formula: IL = 2*sqrt(r)/(1+r) - 1
    const il = 2 * Math.sqrt(priceRatio) / (1 + priceRatio) - 1;

    // HODL value
    const halfInvestA = investment / 2;
    const halfInvestB = investment / 2;
    const tokensA = halfInvestA / initialPriceA;
    const tokensB = halfInvestB / initialPriceB;
    const hodlValue = tokensA * currentPriceA + tokensB * currentPriceB;

    // LP value
    const lpValue = hodlValue * (1 + il);
    const ilDollar = lpValue - hodlValue;

    return {
      il: il * 100,
      lpValue,
      hodlValue,
      ilDollar,
      priceRatio,
      priceChangeA: ((currentPriceA - initialPriceA) / initialPriceA) * 100,
      priceChangeB: ((currentPriceB - initialPriceB) / initialPriceB) * 100,
    };
  }

  function generateILTable(initialPriceA, initialPriceB, currentPriceB, investment) {
    const changes = [-90, -75, -50, -25, -10, 0, 10, 25, 50, 75, 100, 200, 300, 500];
    return changes.map(pct => {
      const newPriceA = initialPriceA * (1 + pct / 100);
      const result = calculateIL(initialPriceA, initialPriceB, newPriceA, currentPriceB, investment);
      return {
        priceChange: pct,
        priceRatio: result.priceRatio,
        il: result.il,
        lpValue: result.lpValue,
        hodlValue: result.hodlValue,
        difference: result.ilDollar,
      };
    });
  }

  /* ============================================================
     RENDER RESULTS
     ============================================================ */

  function renderResults(result) {
    const strip = document.getElementById('results-strip');
    strip.hidden = false;

    document.getElementById('result-il').textContent = `${result.il.toFixed(2)}%`;
    document.getElementById('result-lp-value').textContent = `$${result.lpValue.toFixed(2)}`;
    document.getElementById('result-hodl-value').textContent = `$${result.hodlValue.toFixed(2)}`;
    document.getElementById('result-il-dollar').textContent = `$${result.ilDollar.toFixed(2)}`;

    if (!prefersReducedMotion) {
      gsap.from(strip, { opacity: 0, x: 30, duration: 0.5, ease: 'power3.out' });
    }
  }

  function renderILTable(tableData) {
    const tbody = document.getElementById('il-table-body');
    tbody.innerHTML = tableData.map(row => `
      <tr>
        <td class="${row.priceChange >= 0 ? 'cell-positive' : 'cell-negative'}">${row.priceChange >= 0 ? '+' : ''}${row.priceChange}%</td>
        <td>${row.priceRatio.toFixed(4)}</td>
        <td class="cell-negative">${row.il.toFixed(2)}%</td>
        <td>$${row.lpValue.toFixed(2)}</td>
        <td>$${row.hodlValue.toFixed(2)}</td>
        <td class="${row.difference >= 0 ? 'cell-positive' : 'cell-negative'}">$${row.difference.toFixed(2)}</td>
      </tr>
    `).join('');
  }

  /* ============================================================
     CHARTS
     ============================================================ */

  function getChartColors() {
    const style = getComputedStyle(document.documentElement);
    return {
      accent: style.getPropertyValue('--chart-1').trim(),
      secondary: style.getPropertyValue('--chart-2').trim(),
      tertiary: style.getPropertyValue('--chart-3').trim(),
      text: style.getPropertyValue('--color-text-secondary').trim(),
      border: style.getPropertyValue('--color-border').trim(),
      bg: style.getPropertyValue('--color-surface').trim(),
    };
  }

  function renderILChart(initialPriceA, initialPriceB, currentPriceB, investment) {
    const ctx = document.getElementById('il-chart').getContext('2d');
    const colors = getChartColors();

    const labels = [];
    const lpValues = [];
    const hodlValues = [];

    for (let pct = -80; pct <= 400; pct += 10) {
      const newPriceA = initialPriceA * (1 + pct / 100);
      const result = calculateIL(initialPriceA, initialPriceB, newPriceA, currentPriceB, investment);
      labels.push(`${pct >= 0 ? '+' : ''}${pct}%`);
      lpValues.push(result.lpValue);
      hodlValues.push(result.hodlValue);
    }

    if (ilChart) ilChart.destroy();

    ilChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'LP Value',
            data: lpValues,
            borderColor: colors.accent,
            backgroundColor: colors.accent + '18',
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            pointHoverRadius: 4,
            borderWidth: 2,
          },
          {
            label: 'HODL Value',
            data: hodlValues,
            borderColor: colors.secondary,
            backgroundColor: 'transparent',
            fill: false,
            tension: 0.3,
            pointRadius: 0,
            pointHoverRadius: 4,
            borderWidth: 2,
            borderDash: [6, 3],
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            labels: { color: colors.text, font: { family: "'IBM Plex Mono', monospace", size: 11 } },
          },
          tooltip: {
            backgroundColor: colors.bg,
            titleColor: colors.text,
            bodyColor: colors.text,
            borderColor: colors.border,
            borderWidth: 1,
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: $${ctx.parsed.y.toFixed(2)}`,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: colors.text, font: { family: "'IBM Plex Mono', monospace", size: 10 }, maxTicksLimit: 12 },
            grid: { color: colors.border },
          },
          y: {
            ticks: {
              color: colors.text,
              font: { family: "'IBM Plex Mono', monospace", size: 10 },
              callback: (v) => `$${v.toLocaleString()}`,
            },
            grid: { color: colors.border },
          },
        },
      },
    });
  }

  function renderBreakevenChart(ilPct, investment) {
    const ctx = document.getElementById('breakeven-chart').getContext('2d');
    const colors = getChartColors();

    const absIL = Math.abs(ilPct);
    const days = [30, 60, 90, 120, 180, 365];
    const requiredAPRs = days.map(d => (absIL / 100) / (d / 365) * 100);
    const ilLoss = days.map(() => absIL);

    if (breakevenChart) breakevenChart.destroy();

    breakevenChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: days.map(d => `${d}d`),
        datasets: [
          {
            label: 'Required APR to Break Even',
            data: requiredAPRs,
            backgroundColor: colors.accent + '60',
            borderColor: colors.accent,
            borderWidth: 1,
            borderRadius: 4,
          },
          {
            label: 'IL %',
            data: ilLoss,
            type: 'line',
            borderColor: colors.tertiary,
            backgroundColor: 'transparent',
            pointRadius: 4,
            pointBackgroundColor: colors.tertiary,
            borderWidth: 2,
            borderDash: [4, 4],
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: { color: colors.text, font: { family: "'IBM Plex Mono', monospace", size: 11 } },
          },
          tooltip: {
            backgroundColor: colors.bg,
            titleColor: colors.text,
            bodyColor: colors.text,
            borderColor: colors.border,
            borderWidth: 1,
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)}%`,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: colors.text, font: { family: "'IBM Plex Mono', monospace", size: 10 } },
            grid: { color: colors.border },
          },
          y: {
            ticks: {
              color: colors.text,
              font: { family: "'IBM Plex Mono', monospace", size: 10 },
              callback: (v) => `${v.toFixed(1)}%`,
            },
            grid: { color: colors.border },
          },
        },
      },
    });

    // Update breakeven info
    const info = document.getElementById('breakeven-info');
    const minAPR = requiredAPRs[requiredAPRs.length - 1];
    info.innerHTML = `<p class="breakeven-info__text">
      With an IL of <strong>${absIL.toFixed(2)}%</strong>, you need at least <strong>${minAPR.toFixed(2)}% APR</strong> over 1 year to break even.
      For a 30-day position, you'd need <strong>${requiredAPRs[0].toFixed(2)}% APR</strong>.
    </p>`;
  }

  function updateChartThemes() {
    const form = document.getElementById('lp-form');
    if (lastCalcResult) {
      const initialPriceA = parseFloat(document.getElementById('initial-price-a').value) || 3500;
      const initialPriceB = parseFloat(document.getElementById('initial-price-b').value) || 1;
      const currentPriceB = parseFloat(document.getElementById('current-price-b').value) || 1;
      const investment = parseFloat(document.getElementById('investment-amount').value) || 10000;
      renderILChart(initialPriceA, initialPriceB, currentPriceB, investment);
      renderBreakevenChart(lastCalcResult.il, investment);
    }
  }

  /* ============================================================
     FETCH LIVE PRICES
     ============================================================ */

  async function fetchWithRetry(url, retries = CONFIG.maxRetries) {
    for (let i = 0; i <= retries; i++) {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
      } catch (err) {
        if (i === retries) throw err;
        await new Promise(r => setTimeout(r, CONFIG.retryBaseDelay * (i + 1)));
      }
    }
  }

  async function fetchLivePrices() {
    const tokenA = document.getElementById('token-a').value;
    const tokenB = document.getElementById('token-b').value;
    const btn = document.getElementById('fetch-prices-btn');

    btn.textContent = 'Fetching...';
    btn.disabled = true;

    try {
      const ids = `${tokenA},${tokenB}`;
      const data = await fetchWithRetry(API.prices(ids));

      if (data[tokenA]?.usd) {
        document.getElementById('initial-price-a').value = data[tokenA].usd;
        document.getElementById('current-price-a').value = data[tokenA].usd;
      }
      if (data[tokenB]?.usd) {
        document.getElementById('initial-price-b').value = data[tokenB].usd;
        document.getElementById('current-price-b').value = data[tokenB].usd;
      }
    } catch (err) {
      console.warn('Failed to fetch prices:', err.message);
    } finally {
      btn.textContent = 'Fetch Live Prices';
      btn.disabled = false;
    }
  }

  /* ============================================================
     FORM HANDLER
     ============================================================ */

  function handleFormSubmit(e) {
    e.preventDefault();

    const initialPriceA = parseFloat(document.getElementById('initial-price-a').value);
    const initialPriceB = parseFloat(document.getElementById('initial-price-b').value);
    const currentPriceA = parseFloat(document.getElementById('current-price-a').value);
    const currentPriceB = parseFloat(document.getElementById('current-price-b').value);
    const investment = parseFloat(document.getElementById('investment-amount').value) || 10000;

    if (!initialPriceA || !initialPriceB || !currentPriceA || !currentPriceB) {
      return;
    }

    const result = calculateIL(initialPriceA, initialPriceB, currentPriceA, currentPriceB, investment);
    lastCalcResult = result;

    renderResults(result);
    renderILChart(initialPriceA, initialPriceB, currentPriceB, investment);

    const tableData = generateILTable(initialPriceA, initialPriceB, currentPriceB, investment);
    renderILTable(tableData);

    renderBreakevenChart(result.il, investment);
  }

  /* ============================================================
     INIT DEFAULT TABLE & CHART
     ============================================================ */

  function initDefaults() {
    const defaultInitialA = 3500;
    const defaultInitialB = 1;
    const defaultCurrentB = 1;
    const defaultInvestment = 10000;

    const tableData = generateILTable(defaultInitialA, defaultInitialB, defaultCurrentB, defaultInvestment);
    renderILTable(tableData);
    renderILChart(defaultInitialA, defaultInitialB, defaultCurrentB, defaultInvestment);

    const defaultResult = calculateIL(defaultInitialA, defaultInitialB, defaultInitialA, defaultCurrentB, defaultInvestment);
    renderBreakevenChart(defaultResult.il || 0.01, defaultInvestment);
  }

  /* ============================================================
     BOOTSTRAP
     ============================================================ */

  function init() {
    initThemeToggle();
    initHeroSlider();
    animateHeroEntrance();
    animateCardEntrance();
    initDefaults();

    document.getElementById('lp-form').addEventListener('submit', handleFormSubmit);
    document.getElementById('fetch-prices-btn').addEventListener('click', fetchLivePrices);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
