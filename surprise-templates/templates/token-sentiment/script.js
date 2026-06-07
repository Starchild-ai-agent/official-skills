/* ============================================================
   Token Sentiment Indicators — script.js

   APIs: Alternative.me Fear & Greed + CoinGecko + mock social
   Animation: GSAP 3 + ScrollTrigger
   Entrance: D13 blur(8px)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var $ = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel) { return document.querySelectorAll(sel); };

  /* ---------- Mock Token Sentiment Data ---------- */
  var TOKEN_SENTIMENTS = [
    { name: 'Bitcoin', symbol: 'BTC', score: 72, mood: 'greed' },
    { name: 'Ethereum', symbol: 'ETH', score: 65, mood: 'greed' },
    { name: 'Solana', symbol: 'SOL', score: 78, mood: 'extreme-greed' },
    { name: 'Arbitrum', symbol: 'ARB', score: 55, mood: 'neutral' },
    { name: 'Chainlink', symbol: 'LINK', score: 48, mood: 'neutral' },
    { name: 'Avalanche', symbol: 'AVAX', score: 35, mood: 'fear' },
  ];

  var TREND_DATA = {
    labels: ['7d ago', '6d', '5d', '4d', '3d', '2d', '1d', 'Now'],
    datasets: [
      { name: 'BTC', data: [58, 55, 60, 63, 68, 70, 69, 72] },
      { name: 'ETH', data: [52, 50, 55, 58, 62, 60, 63, 65] },
      { name: 'SOL', data: [65, 68, 70, 72, 75, 74, 76, 78] },
    ],
  };

  var SOCIAL_DATA = [
    {
      platform: 'Twitter / X',
      metrics: [
        { label: 'Mentions (24h)', value: '142.3K', trend: 'positive' },
        { label: 'Sentiment Ratio', value: '68% Bull', trend: 'positive' },
        { label: 'Influencer Score', value: '7.4/10', trend: 'positive' },
      ],
    },
    {
      platform: 'Reddit',
      metrics: [
        { label: 'Active Threads', value: '3,847', trend: 'positive' },
        { label: 'Upvote Ratio', value: '72%', trend: 'positive' },
        { label: 'Bear Comments', value: '18%', trend: 'negative' },
      ],
    },
    {
      platform: 'Telegram',
      metrics: [
        { label: 'Group Activity', value: '+23%', trend: 'positive' },
        { label: 'FUD Index', value: '2.1/10', trend: 'positive' },
        { label: 'Whale Alerts', value: '47 today', trend: 'negative' },
      ],
    },
  ];

  var trendChart = null;

  /* ---------- Gauge Helpers ---------- */
  function getMoodLabel(score) {
    if (score <= 20) return 'Extreme Fear';
    if (score <= 40) return 'Fear';
    if (score <= 60) return 'Neutral';
    if (score <= 80) return 'Greed';
    return 'Extreme Greed';
  }

  function getGaugeColor(score) {
    var style = getComputedStyle(document.documentElement);
    if (score <= 40) return style.getPropertyValue('--color-fear').trim();
    if (score <= 60) return style.getPropertyValue('--color-neutral-mood').trim();
    return style.getPropertyValue('--color-greed').trim();
  }

  function setGauge(fillEl, valueEl, labelEl, score) {
    var maxDash = 251;
    var offset = maxDash - (score / 100) * maxDash;
    fillEl.style.strokeDashoffset = offset;
    fillEl.style.stroke = getGaugeColor(score);
    if (valueEl) valueEl.textContent = score;
    if (labelEl) labelEl.textContent = getMoodLabel(score);
  }

  /* ---------- Main Gauge ---------- */
  function renderMainGauge() {
    // Try fetching real Fear & Greed
    fetch('https://api.alternative.me/fng/?limit=1')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var score = parseInt(data.data[0].value, 10);
        setGauge(
          $('#gauge-fill'),
          $('#gauge-value'),
          $('#gauge-label'),
          score
        );
      })
      .catch(function () {
        // Fallback to mock
        setGauge($('#gauge-fill'), $('#gauge-value'), $('#gauge-label'), 62);
      });
  }

  /* ---------- Token Sentiment Cards ---------- */
  function renderSentimentGrid() {
    var grid = $('#sentiment-grid');
    grid.innerHTML = TOKEN_SENTIMENTS.map(function (t) {
      var gaugeId = 'gauge-' + t.symbol.toLowerCase();
      return '<div class="sentiment-card" style="opacity:0">' +
        '<span class="sentiment-card__name">' + t.name + '</span>' +
        '<div class="sentiment-card__gauge">' +
          '<svg class="gauge__svg" viewBox="0 0 200 120">' +
            '<path class="gauge__track" d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke-width="10" stroke-linecap="round"/>' +
            '<path class="gauge__fill" id="' + gaugeId + '" d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke-width="10" stroke-linecap="round" style="stroke-dasharray:251;stroke-dashoffset:251"/>' +
          '</svg>' +
        '</div>' +
        '<span class="sentiment-card__score">' + t.score + '</span>' +
        '<span class="sentiment-card__label mood--' + t.mood + '">' + getMoodLabel(t.score) + '</span>' +
      '</div>';
    }).join('');

    // Animate gauges
    setTimeout(function () {
      TOKEN_SENTIMENTS.forEach(function (t) {
        var fillEl = $('#gauge-' + t.symbol.toLowerCase());
        if (fillEl) {
          var maxDash = 251;
          var offset = maxDash - (t.score / 100) * maxDash;
          fillEl.style.stroke = getGaugeColor(t.score);
          fillEl.style.strokeDashoffset = offset;
        }
      });
    }, 300);

    // D13 entrance: blur(8px)
    if (!prefersReducedMotion) {
      gsap.fromTo('.sentiment-card',
        { opacity: 0, filter: 'blur(8px)' },
        { opacity: 1, filter: 'blur(0px)', duration: 0.6, stagger: 0.1, ease: 'power2.out' }
      );
    } else {
      $$('.sentiment-card').forEach(function (el) { el.style.opacity = '1'; });
    }
  }

  /* ---------- Trend Chart ---------- */
  function renderTrendChart() {
    var ctx = $('#trend-chart').getContext('2d');
    var style = getComputedStyle(document.documentElement);
    var textColor = style.getPropertyValue('--color-text-secondary').trim();
    var borderColor = style.getPropertyValue('--color-border').trim();
    var colors = [
      style.getPropertyValue('--chart-1').trim(),
      style.getPropertyValue('--chart-2').trim(),
      style.getPropertyValue('--chart-3').trim(),
    ];

    if (trendChart) trendChart.destroy();

    trendChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: TREND_DATA.labels,
        datasets: TREND_DATA.datasets.map(function (ds, i) {
          return {
            label: ds.name,
            data: ds.data,
            borderColor: colors[i],
            backgroundColor: colors[i] + '20',
            fill: true,
            tension: 0.4,
            pointRadius: 3,
            pointHoverRadius: 6,
            borderWidth: 2,
          };
        }),
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            position: 'top',
            labels: { color: textColor, font: { family: "'Albert Sans', sans-serif", size: 12 } },
          },
        },
        scales: {
          x: {
            ticks: { color: textColor, font: { family: "'Space Mono', monospace", size: 11 } },
            grid: { color: borderColor },
          },
          y: {
            min: 0, max: 100,
            ticks: {
              color: textColor,
              font: { family: "'Space Mono', monospace", size: 11 },
              stepSize: 20,
            },
            grid: { color: borderColor },
          },
        },
      },
    });
  }

  /* ---------- Social Grid ---------- */
  function renderSocialGrid() {
    var grid = $('#social-grid');
    grid.innerHTML = SOCIAL_DATA.map(function (s) {
      var metricsHtml = s.metrics.map(function (m) {
        return '<div class="social-card__metric">' +
          '<span class="social-card__metric-label">' + m.label + '</span>' +
          '<span class="social-card__metric-value social-card__metric-value--' + m.trend + '">' + m.value + '</span>' +
        '</div>';
      }).join('');

      return '<div class="social-card" style="opacity:0">' +
        '<div class="social-card__platform">' + s.platform + '</div>' +
        metricsHtml +
      '</div>';
    }).join('');

    if (!prefersReducedMotion) {
      gsap.fromTo('.social-card',
        { opacity: 0, filter: 'blur(8px)' },
        {
          opacity: 1, filter: 'blur(0px)', duration: 0.6, stagger: 0.12, ease: 'power2.out',
          scrollTrigger: { trigger: '#social-section', start: 'top 80%', toggleActions: 'play none none none' },
        }
      );
    } else {
      $$('.social-card').forEach(function (el) { el.style.opacity = '1'; });
    }
  }

  /* ---------- Theme Toggle ---------- */
  function initTheme() {
    var saved = localStorage.getItem('token-sentiment-theme');
    if (saved === 'light') {
      document.documentElement.setAttribute('data-theme', 'light');
    }

    $('#theme-toggle').addEventListener('click', function () {
      var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
      localStorage.setItem('token-sentiment-theme', isDark ? 'light' : 'dark');
      renderTrendChart();
      // Re-apply gauge colors
      renderMainGauge();
      TOKEN_SENTIMENTS.forEach(function (t) {
        var fillEl = $('#gauge-' + t.symbol.toLowerCase());
        if (fillEl) fillEl.style.stroke = getGaugeColor(t.score);
      });
    });
  }

  /* ---------- GSAP Animations ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    var heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl
      .from('.hero__label', { opacity: 0, y: 20, duration: 0.5 })
      .from('.hero__title', { opacity: 0, filter: 'blur(8px)', duration: 0.7 }, '-=0.2')
      .from('.hero__gauge-wrap', { opacity: 0, scale: 0.9, duration: 0.8 }, '-=0.3');

    $$('.section').forEach(function (section) {
      gsap.from(section.querySelector('.section__title'), {
        scrollTrigger: {
          trigger: section,
          start: 'top 85%',
          toggleActions: 'play none none none',
        },
        opacity: 0,
        filter: 'blur(8px)',
        duration: 0.6,
        ease: 'power2.out',
      });
    });
  }

  /* ---------- Init ---------- */
  function init() {
    initTheme();
    renderMainGauge();
    renderSentimentGrid();
    renderTrendChart();
    renderSocialGrid();
    initAnimations();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
