/* ============================================================
   Market Cycle Indicators — script.js

   Layout: A18 Accordion/Expandable Sections
   Hover:  C3 translateX(4px) (CSS)
   Entry:  D18 typewriter (GSAP stagger on chars)
   Hero:   H6 Terminal Header

   APIs:
   - CoinGecko (BTC price history + global market data)
   - Alternative.me Fear & Greed Index
   - Built-in simulated cycle indicator data

   Animation: GSAP 3 + ScrollTrigger + TextPlugin (CDN)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger, TextPlugin);

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const CONFIG = {
    heroImageUrl: (() => {
      const raw = '{{HERO_IMAGE_URL}}';
      if (raw.startsWith('{{')) return '';
      return raw;
    })(),
    maxRetries: 2,
    retryBaseDelay: 1500,
  };

  const API = {
    btcPrice: () => 'https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=365&interval=daily',
    btcCurrent: () => 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true&include_market_cap=true',
    fearGreed: () => 'https://api.alternative.me/fng/?limit=1',
  };

  const ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';
  const CHEVRON_SVG = '<svg class="accordion-section__chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>';

  /* ---------- Simulated Indicators ---------- */
  function generateSimulatedIndicators(btcPrice) {
    const price = btcPrice || 67000;
    const mvrvZScore = 1.8 + Math.random() * 2.5;
    const piCycleRatio = 0.65 + Math.random() * 0.25;
    const wma200 = price * (0.35 + Math.random() * 0.15);
    const wma200Multiplier = price / wma200;
    return {
      mvrvZScore: parseFloat(mvrvZScore.toFixed(2)),
      piCycleRatio: parseFloat(piCycleRatio.toFixed(3)),
      wma200,
      wma200Multiplier: parseFloat(wma200Multiplier.toFixed(2)),
      puellMultiple: parseFloat((0.8 + Math.random() * 2.0).toFixed(2)),
      rhodlRatio: Math.round(1000 + Math.random() * 30000),
    };
  }

  function determineCyclePhase(fearGreedValue, indicators) {
    const scores = { accumulation: 0, markup: 0, distribution: 0, markdown: 0 };
    if (fearGreedValue < 25) { scores.accumulation += 3; scores.markdown += 1; }
    else if (fearGreedValue < 45) { scores.accumulation += 2; }
    else if (fearGreedValue < 55) { scores.markup += 1; scores.distribution += 1; }
    else if (fearGreedValue < 75) { scores.markup += 2; scores.distribution += 1; }
    else { scores.distribution += 3; scores.markup += 1; }
    if (indicators.mvrvZScore < 0.5) { scores.accumulation += 3; }
    else if (indicators.mvrvZScore < 2) { scores.accumulation += 1; scores.markup += 2; }
    else if (indicators.mvrvZScore < 4) { scores.markup += 2; scores.distribution += 1; }
    else { scores.distribution += 3; }
    if (indicators.piCycleRatio < 0.7) { scores.accumulation += 2; }
    else if (indicators.piCycleRatio < 0.85) { scores.markup += 2; }
    else if (indicators.piCycleRatio < 0.95) { scores.distribution += 2; }
    else { scores.distribution += 3; }
    if (indicators.wma200Multiplier < 1.5) { scores.accumulation += 3; }
    else if (indicators.wma200Multiplier < 3) { scores.markup += 2; }
    else if (indicators.wma200Multiplier < 4) { scores.distribution += 2; }
    else { scores.distribution += 3; }
    const entries = Object.entries(scores);
    entries.sort((a, b) => b[1] - a[1]);
    const phase = entries[0][0];
    const totalScore = entries.reduce((sum, [, v]) => sum + v, 0);
    const compositeScore = Math.round((entries[0][1] / totalScore) * 100);
    return { phase, compositeScore, scores };
  }

  /* ---------- Static Data ---------- */
  const HISTORICAL_CYCLES = [
    { name: 'Cycle 1', period: '2011 – 2013', peak: '$1,150', peakDate: 'Nov 2013', bottom: '$2', bottomDate: 'Nov 2011', drawdown: '-87%', duration: '~24 months', halvingToTop: '~12 months' },
    { name: 'Cycle 2', period: '2015 – 2017', peak: '$19,800', peakDate: 'Dec 2017', bottom: '$152', bottomDate: 'Jan 2015', drawdown: '-84%', duration: '~36 months', halvingToTop: '~18 months' },
    { name: 'Cycle 3', period: '2018 – 2021', peak: '$69,000', peakDate: 'Nov 2021', bottom: '$3,122', bottomDate: 'Dec 2018', drawdown: '-77%', duration: '~36 months', halvingToTop: '~18 months' },
    { name: 'Cycle 4', period: '2022 – Present', peak: 'TBD', peakDate: 'TBD', bottom: '$15,476', bottomDate: 'Nov 2022', drawdown: '-77%', duration: 'Ongoing', halvingToTop: 'Apr 2024 halving' },
  ];

  const PHASE_INFO = [
    { id: 'accumulation', icon: '🧊', name: 'Accumulation', desc: 'Smart money accumulates while retail sentiment is at its lowest. Prices consolidate near cycle lows with low volatility.', traits: ['Fear & Greed < 25', 'MVRV Z-Score < 0.5', 'Price near 200WMA', 'Low trading volume', 'Negative media sentiment'] },
    { id: 'markup', icon: '🚀', name: 'Markup (Bull Run)', desc: 'Prices break out of accumulation range. Increasing volume, improving sentiment, and growing institutional interest.', traits: ['Fear & Greed 40-70', 'MVRV Z-Score 1-3', 'Price above 200WMA', 'Rising volume trend', 'Growing media coverage'] },
    { id: 'distribution', icon: '⚖️', name: 'Distribution', desc: 'Smart money distributes to late buyers. Extreme greed, parabolic price action, and euphoric sentiment.', traits: ['Fear & Greed > 75', 'MVRV Z-Score > 4', 'Pi Cycle Top signal', 'Record trading volume', 'Mainstream media frenzy'] },
    { id: 'markdown', icon: '📉', name: 'Markdown (Bear Market)', desc: 'Prices decline from cycle highs. Capitulation events, declining interest, and prolonged downtrend.', traits: ['Fear & Greed 10-30', 'MVRV Z-Score declining', 'Price falling toward 200WMA', 'Declining volume', 'Negative news cycle'] },
  ];

  /* ---------- State ---------- */
  let priceChart = null;
  let gaugeCharts = [];

  /* ---------- fetchWithRetry ---------- */
  async function fetchWithRetry(url, retries = CONFIG.maxRetries) {
    for (let i = 0; i <= retries; i++) {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return await res.json();
      } catch (err) {
        if (i === retries) throw err;
        await new Promise(r => setTimeout(r, CONFIG.retryBaseDelay * (i + 1)));
      }
    }
  }

  /* ---------- Theme Toggle ---------- */
  function initTheme() {
    const toggle = document.getElementById('theme-toggle');
    const saved = localStorage.getItem('market-cycle-theme');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
    toggle.addEventListener('click', function () {
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      if (isDark) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('market-cycle-theme', 'light');
      } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('market-cycle-theme', 'dark');
      }
      rebuildCharts();
    });
  }

  function initHeroImage() {
    if (!CONFIG.heroImageUrl) return;
    var el = document.querySelector('.hero__bg-image');
    if (el) el.style.backgroundImage = 'url(' + CONFIG.heroImageUrl + ')';
  }

  function updateClock() {
    var el = document.getElementById('hero-time');
    if (!el) return;
    var now = new Date();
    el.textContent = now.toLocaleString('en-US', { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    el.setAttribute('datetime', now.toISOString());
  }

  /* ---------- Accordion Toggle ---------- */
  function initAccordion(containerId) {
    var container = document.getElementById(containerId);
    if (!container) return;
    container.addEventListener('click', function (e) {
      var header = e.target.closest('.accordion-section__header');
      if (!header) return;
      var section = header.closest('.accordion-section');
      if (!section) return;
      var isActive = section.classList.contains('accordion-section--active');
      container.querySelectorAll('.accordion-section--active').forEach(function (s) {
        s.classList.remove('accordion-section--active');
      });
      if (!isActive) {
        section.classList.add('accordion-section--active');
      }
    });
  }

  /* ---------- Gauge Chart ---------- */
  function createGaugeChart(canvasId, value, max, color) {
    var ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    var styles = getComputedStyle(document.documentElement);
    var borderColor = styles.getPropertyValue('--color-border').trim() || 'rgba(0,0,0,0.08)';
    return new Chart(ctx, {
      type: 'doughnut',
      data: {
        datasets: [{ data: [value, Math.max(0, max - value)], backgroundColor: [color, borderColor], borderWidth: 0, circumference: 270, rotation: 225 }],
      },
      options: { responsive: true, maintainAspectRatio: false, cutout: '78%', plugins: { legend: { display: false }, tooltip: { enabled: false } } },
    });
  }

  /* ---------- Render Gauge Accordion ---------- */
  function renderGauges(fearGreedValue, fearGreedLabel, indicators) {
    var accordion = document.getElementById('gauges-accordion');
    if (!accordion) return;
    var gaugeData = [
      { id: 'gauge-fg', title: 'Fear & Greed Index', value: fearGreedValue, max: 100, label: fearGreedLabel, color: fearGreedValue < 25 ? '#c62828' : fearGreedValue < 50 ? '#d4960a' : fearGreedValue < 75 ? '#66bb6a' : '#357a38', desc: 'Market sentiment is currently "' + fearGreedLabel + '". The Fear & Greed Index measures overall market emotion on a scale of 0 (extreme fear) to 100 (extreme greed).', badge: fearGreedValue < 30 ? 'FEAR' : fearGreedValue < 70 ? 'NEUTRAL' : 'GREED' },
      { id: 'gauge-mvrv', title: 'MVRV Z-Score', value: indicators.mvrvZScore, max: 7, label: indicators.mvrvZScore < 1 ? 'Undervalued' : indicators.mvrvZScore < 3 ? 'Fair Value' : 'Overheated', color: indicators.mvrvZScore < 1 ? '#357a38' : indicators.mvrvZScore < 3 ? '#d4960a' : '#c62828', desc: 'Z-Score of ' + indicators.mvrvZScore + ' — ' + (indicators.mvrvZScore < 1 ? 'historically undervalued zone.' : indicators.mvrvZScore < 3 ? 'fair value range.' : 'overheated territory.'), badge: indicators.mvrvZScore < 1 ? 'LOW' : indicators.mvrvZScore < 3 ? 'MID' : 'HIGH' },
      { id: 'gauge-pi', title: 'Pi Cycle Top Indicator', value: indicators.piCycleRatio * 100, max: 100, label: indicators.piCycleRatio < 0.8 ? 'Safe' : indicators.piCycleRatio < 0.95 ? 'Warming' : 'Danger', color: indicators.piCycleRatio < 0.8 ? '#357a38' : indicators.piCycleRatio < 0.95 ? '#d4960a' : '#c62828', desc: 'Ratio at ' + (indicators.piCycleRatio * 100).toFixed(1) + '% — ' + (indicators.piCycleRatio < 0.8 ? 'no top signal.' : indicators.piCycleRatio < 0.95 ? 'approaching caution zone.' : 'near historical top signal.'), badge: indicators.piCycleRatio < 0.8 ? 'SAFE' : indicators.piCycleRatio < 0.95 ? 'WARN' : 'DANGER' },
    ];

    accordion.innerHTML = gaugeData.map(function (g, i) {
      var displayVal = typeof g.value === 'number' && g.value < 10 ? g.value.toFixed(1) : Math.round(g.value);
      return '<div class="accordion-section ' + (i === 0 ? 'accordion-section--active' : '') + '" data-animate>' +
        '<div class="accordion-section__header">' +
          '<div class="accordion-section__left">' +
            '<span class="accordion-section__title">' + g.title + '</span>' +
            '<span class="accordion-section__badge">' + g.badge + '</span>' +
          '</div>' +
          CHEVRON_SVG +
        '</div>' +
        '<div class="accordion-section__body">' +
          '<div class="accordion-section__content">' +
            '<div class="accordion-gauge">' +
              '<div class="accordion-gauge__canvas-wrap">' +
                '<canvas id="' + g.id + '" width="120" height="120"></canvas>' +
                '<div class="accordion-gauge__value-overlay">' +
                  '<span class="accordion-gauge__value">' + displayVal + '</span>' +
                  '<span class="accordion-gauge__label">' + g.label + '</span>' +
                '</div>' +
              '</div>' +
              '<div class="accordion-gauge__info">' +
                '<p class="accordion-gauge__desc">' + g.desc + '</p>' +
              '</div>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>';
    }).join('');

    gaugeCharts.forEach(function (c) { if (c) c.destroy(); });
    gaugeCharts = gaugeData.map(function (g) { return createGaugeChart(g.id, g.value, g.max, g.color); });
    initAccordion('gauges-accordion');
  }

  /* ---------- Render Price Chart ---------- */
  function renderPriceChart(priceData) {
    var skeleton = document.getElementById('price-chart-skeleton');
    var errorEl = document.getElementById('price-chart-error');
    var ctx = document.getElementById('price-chart');
    if (!ctx) return;
    if (skeleton) skeleton.hidden = true;
    if (errorEl) errorEl.hidden = true;
    if (priceChart) priceChart.destroy();

    var styles = getComputedStyle(document.documentElement);
    var textColor = styles.getPropertyValue('--color-text-secondary').trim();
    var borderColor = styles.getPropertyValue('--color-border').trim();
    var accentColor = styles.getPropertyValue('--color-accent').trim();
    var successColor = styles.getPropertyValue('--color-success').trim() || '#357a38';

    var labels = priceData.map(function (p) {
      return new Date(p[0]).toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
    });
    var prices = priceData.map(function (p) { return p[1]; });
    var wmaLine = prices.map(function (p, i) { return p * (0.35 + (i / prices.length) * 0.15); });

    priceChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          { label: 'BTC Price', data: prices, borderColor: accentColor, backgroundColor: accentColor + '15', fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2, yAxisID: 'y' },
          { label: '200-Week MA (simulated)', data: wmaLine, borderColor: successColor, borderDash: [6, 4], fill: false, tension: 0.4, pointRadius: 0, borderWidth: 1.5, yAxisID: 'y' },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: true, position: 'top', labels: { color: textColor, font: { family: "'JetBrains Mono', monospace", size: 11 }, boxWidth: 12, padding: 16 } },
          tooltip: { backgroundColor: 'rgba(0,0,0,0.85)', titleFont: { family: "'JetBrains Mono', monospace", size: 11 }, bodyFont: { family: "'JetBrains Mono', monospace", size: 11 }, padding: 10, cornerRadius: 6, callbacks: { label: function (c) { return c.dataset.label + ': $' + c.parsed.y.toLocaleString('en-US', { maximumFractionDigits: 0 }); } } },
        },
        scales: {
          x: { ticks: { color: textColor, font: { family: "'JetBrains Mono', monospace", size: 10 }, maxTicksLimit: 12 }, grid: { color: borderColor } },
          y: { position: 'left', ticks: { color: textColor, font: { family: "'JetBrains Mono', monospace", size: 10 }, callback: function (v) { return '$' + (v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v); } }, grid: { color: borderColor } },
        },
      },
    });
  }

  function showPriceChartError(msg) {
    var skeleton = document.getElementById('price-chart-skeleton');
    var errorEl = document.getElementById('price-chart-error');
    var errorContent = document.getElementById('price-chart-error-content');
    if (skeleton) skeleton.hidden = true;
    if (errorEl) errorEl.hidden = false;
    if (errorContent) {
      errorContent.innerHTML = ICON_ALERT + '<h3 class="error-state__title">Chart Unavailable</h3><p class="error-state__msg">' + msg + '</p><button class="error-state__retry" onclick="location.reload()">Retry</button>';
    }
  }

  /* ---------- Render Timeline Accordion ---------- */
  function renderTimeline() {
    var accordion = document.getElementById('timeline-accordion');
    if (!accordion) return;
    accordion.innerHTML = HISTORICAL_CYCLES.map(function (cycle, i) {
      return '<div class="accordion-section ' + (i === HISTORICAL_CYCLES.length - 1 ? 'accordion-section--active' : '') + '" data-animate>' +
        '<div class="accordion-section__header">' +
          '<div class="accordion-section__left">' +
            '<span class="accordion-section__title">' + cycle.name + '</span>' +
            '<span class="accordion-section__badge">' + cycle.period + '</span>' +
          '</div>' +
          CHEVRON_SVG +
        '</div>' +
        '<div class="accordion-section__body"><div class="accordion-section__content">' +
          '<div class="accordion-timeline-stats">' +
            '<div class="accordion-timeline-stat"><span class="accordion-timeline-stat__label">Peak</span><span class="accordion-timeline-stat__value">' + cycle.peak + '</span></div>' +
            '<div class="accordion-timeline-stat"><span class="accordion-timeline-stat__label">Bottom</span><span class="accordion-timeline-stat__value">' + cycle.bottom + '</span></div>' +
            '<div class="accordion-timeline-stat"><span class="accordion-timeline-stat__label">Drawdown</span><span class="accordion-timeline-stat__value">' + cycle.drawdown + '</span></div>' +
            '<div class="accordion-timeline-stat"><span class="accordion-timeline-stat__label">Duration</span><span class="accordion-timeline-stat__value">' + cycle.duration + '</span></div>' +
            '<div class="accordion-timeline-stat"><span class="accordion-timeline-stat__label">Halving → Top</span><span class="accordion-timeline-stat__value">' + cycle.halvingToTop + '</span></div>' +
          '</div>' +
        '</div></div>' +
      '</div>';
    }).join('');
    initAccordion('timeline-accordion');
  }

  /* ---------- Render Phase Accordion ---------- */
  function renderPhaseCards(currentPhase) {
    var accordion = document.getElementById('phases-accordion');
    if (!accordion) return;
    accordion.innerHTML = PHASE_INFO.map(function (p) {
      return '<div class="accordion-section ' + (p.id === currentPhase ? 'accordion-section--active' : '') + '" data-animate>' +
        '<div class="accordion-section__header">' +
          '<div class="accordion-section__left">' +
            '<span class="accordion-section__icon">' + p.icon + '</span>' +
            '<span class="accordion-section__title">' + p.name + '</span>' +
            (p.id === currentPhase ? '<span class="accordion-section__badge">CURRENT</span>' : '') +
          '</div>' +
          CHEVRON_SVG +
        '</div>' +
        '<div class="accordion-section__body"><div class="accordion-section__content">' +
          '<p class="accordion-phase__desc">' + p.desc + '</p>' +
          '<ul class="accordion-phase__traits">' +
            p.traits.map(function (t) { return '<li class="accordion-phase__trait">' + t + '</li>'; }).join('') +
          '</ul>' +
        '</div></div>' +
      '</div>';
    }).join('');
    initAccordion('phases-accordion');
  }

  /* ---------- Update Hero ---------- */
  function updateHero(phase, compositeScore) {
    var phaseNames = { accumulation: 'Accumulation', markup: 'Markup', distribution: 'Distribution', markdown: 'Markdown' };
    var phaseName = document.getElementById('phase-name');
    var scoreValue = document.getElementById('score-value');
    if (phaseName) phaseName.textContent = phaseNames[phase] || '--';
    if (scoreValue) scoreValue.textContent = compositeScore;
  }

  /* ---------- Rebuild Charts ---------- */
  function rebuildCharts() {
    if (priceChart) {
      var styles = getComputedStyle(document.documentElement);
      var textColor = styles.getPropertyValue('--color-text-secondary').trim();
      var borderColor = styles.getPropertyValue('--color-border').trim();
      var accentColor = styles.getPropertyValue('--color-accent').trim();
      priceChart.options.scales.x.ticks.color = textColor;
      priceChart.options.scales.x.grid.color = borderColor;
      priceChart.options.scales.y.ticks.color = textColor;
      priceChart.options.scales.y.grid.color = borderColor;
      priceChart.options.plugins.legend.labels.color = textColor;
      priceChart.data.datasets[0].borderColor = accentColor;
      priceChart.data.datasets[0].backgroundColor = accentColor + '15';
      priceChart.update('none');
    }
  }

  /* ---------- GSAP Animations: D18 Typewriter ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    var typewriterEl = document.getElementById('hero-typewriter');
    if (typewriterEl) {
      var finalText = 'cycle analysis complete. all indicators loaded.';
      typewriterEl.textContent = '';
      gsap.to(typewriterEl, { duration: 2, text: { value: finalText, delimiter: '' }, ease: 'none', delay: 0.5 });
    }

    gsap.from('.hero__terminal-line', { opacity: 0, x: -10, duration: 0.4, stagger: 0.12, ease: 'power2.out', delay: 0.3 });

    gsap.utils.toArray('[data-animate]').forEach(function (el) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 88%', toggleActions: 'play none none none' },
        opacity: 0, x: -20, duration: 0.6, ease: 'power2.out',
      });
    });

    gsap.utils.toArray('.section__header').forEach(function (header) {
      gsap.from(header, {
        scrollTrigger: { trigger: header, start: 'top 85%', toggleActions: 'play none none none' },
        y: 25, opacity: 0, duration: 0.6, ease: 'power2.out',
      });
    });
  }

  /* ---------- Main Init ---------- */
  async function init() {
    initTheme();
    initHeroImage();
    updateClock();
    setInterval(updateClock, 30000);

    renderTimeline();

    var fearGreedValue = 50;
    var fearGreedLabel = 'Neutral';
    var btcPrice = 67000;
    var priceHistory = null;

    try {
      var results = await Promise.allSettled([
        fetchWithRetry(API.fearGreed()),
        fetchWithRetry(API.btcCurrent()),
        fetchWithRetry(API.btcPrice()),
      ]);

      if (results[0].status === 'fulfilled' && results[0].value && results[0].value.data && results[0].value.data[0]) {
        fearGreedValue = parseInt(results[0].value.data[0].value, 10);
        fearGreedLabel = results[0].value.data[0].value_classification;
      }
      if (results[1].status === 'fulfilled' && results[1].value && results[1].value.bitcoin) {
        btcPrice = results[1].value.bitcoin.usd;
      }
      if (results[2].status === 'fulfilled' && results[2].value && results[2].value.prices) {
        priceHistory = results[2].value.prices;
      }
    } catch (err) {
      console.warn('API fetch failed, using simulated data:', err);
    }

    var indicators = generateSimulatedIndicators(btcPrice);
    var cycleResult = determineCyclePhase(fearGreedValue, indicators);

    updateHero(cycleResult.phase, cycleResult.compositeScore);
    renderGauges(fearGreedValue, fearGreedLabel, indicators);

    if (priceHistory && priceHistory.length > 0) {
      renderPriceChart(priceHistory);
    } else {
      var simPrices = [];
      var now = Date.now();
      var price = 25000;
      for (var i = 365; i >= 0; i--) {
        price += price * (Math.random() * 0.06 - 0.025);
        price = Math.max(15000, price);
        simPrices.push([now - i * 86400000, price]);
      }
      renderPriceChart(simPrices);
    }

    renderPhaseCards(cycleResult.phase);

    requestAnimationFrame(function () {
      initAnimations();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
