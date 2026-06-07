/* ============================================================
   Viral Tweet Analyzer — script.js

   Skeleton: A8 Comparison (viral vs normal side-by-side)
   Entry: D19 alternating odd:-20px even:+20px
   Cards: .analysis-panel
   Animation: GSAP 3 + ScrollTrigger (CDN)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);

  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var CONFIG = {
    twitterHandle: (function () {
      var raw = '{{TWITTER_HANDLE}}';
      if (raw.startsWith('{{')) return '@growthhacker';
      return raw;
    })(),
  };

  /* ---------- Simulated Viral Pattern Data ---------- */
  var VIRAL_PATTERNS = [
    { name: 'Questions', score: 92, engagementRate: '8.4%', desc: 'Tweets that ask thought-provoking questions generate 3x more replies.', examples: '"What\'s the most underrated skill in tech?" — 2.4K likes, 890 replies' },
    { name: 'Numbered Lists', score: 87, engagementRate: '7.2%', desc: 'Listicles with 5-10 items get the highest saves and retweets.', examples: '"7 tools that saved me 10 hours/week:" — 5.1K likes, 2.3K retweets' },
    { name: 'Personal Stories', score: 78, engagementRate: '6.8%', desc: 'Vulnerability and authenticity drive deep engagement.', examples: '"I got fired 3 times before 30. Here\'s what I learned:" — 8.2K likes' },
    { name: 'Data & Stats', score: 71, engagementRate: '5.9%', desc: 'Surprising statistics with visual context get high quote-tweet rates.', examples: '"98% of startups fail. But 73% share this pattern:" — 3.7K likes' },
    { name: 'Hot Takes', score: 65, engagementRate: '5.1%', desc: 'Contrarian opinions spark debate. Best when backed by reasoning.', examples: '"Unpopular opinion: College is the worst investment" — 6.5K likes' },
    { name: 'How-To Guides', score: 82, engagementRate: '6.5%', desc: 'Step-by-step tutorials get high bookmark rates.', examples: '"How to build a $10K/mo side project in 90 days:" — 4.8K likes' },
  ];

  var NORMAL_PATTERNS = [
    { name: 'Status Updates', score: 22, engagementRate: '0.8%', desc: 'Generic "what I\'m doing" tweets with no hook or value proposition.', examples: '"Just had coffee and starting work" — 3 likes' },
    { name: 'Link Drops', score: 31, engagementRate: '1.2%', desc: 'Sharing links without context or commentary. Algorithm deprioritizes.', examples: '"Check this out: [link]" — 12 likes, 2 retweets' },
    { name: 'Vague Opinions', score: 28, engagementRate: '0.9%', desc: 'Opinions without specifics or supporting evidence.', examples: '"This is so true" — 5 likes' },
    { name: 'Self-Promotion', score: 35, engagementRate: '1.5%', desc: 'Direct product/service promotion without value-first approach.', examples: '"Buy my course! Link in bio" — 8 likes, 1 reply' },
    { name: 'Retweet-Only', score: 18, engagementRate: '0.4%', desc: 'Retweeting without adding commentary or perspective.', examples: 'RT @someone: [their content] — 0 engagement on your profile' },
    { name: 'Long Rants', score: 25, engagementRate: '0.7%', desc: 'Unstructured complaints without actionable takeaways.', examples: '"I can\'t believe [company] did this again..." — 4 likes' },
  ];

  var SCATTER_DATA = [];
  var rng = function (min, max) { return Math.random() * (max - min) + min; };
  for (var i = 0; i < 25; i++) {
    SCATTER_DATA.push({ x: Math.round(rng(35, 85)), y: parseFloat(rng(4, 12).toFixed(1)), viral: true });
  }
  for (var j = 0; j < 15; j++) {
    SCATTER_DATA.push({ x: Math.round(rng(5, 30)), y: parseFloat(rng(1.5, 6).toFixed(1)), viral: false });
  }
  for (var k = 0; k < 12; k++) {
    SCATTER_DATA.push({ x: Math.round(rng(100, 280)), y: parseFloat(rng(0.5, 4).toFixed(1)), viral: false });
  }
  SCATTER_DATA.push({ x: 52, y: 18.3, viral: true });
  SCATTER_DATA.push({ x: 67, y: 15.7, viral: true });
  SCATTER_DATA.push({ x: 43, y: 14.2, viral: true });

  var TWEET_TEMPLATES = [
    { name: 'The Question Hook', badge: '92% viral score', template: 'What\'s the one thing about [TOPIC] that nobody talks about?\n\nI\'ll go first:\n\n[YOUR INSIGHT]\n\nThis changed how I think about [RELATED TOPIC].', charCount: 140 },
    { name: 'The Numbered List', badge: '87% viral score', template: '[NUMBER] [TOPIC] tips that took me [TIME] to learn:\n\n1. [TIP 1]\n2. [TIP 2]\n3. [TIP 3]\n4. [TIP 4]\n5. [TIP 5]\n\nWhich one resonates most?', charCount: 180 },
    { name: 'The Story Arc', badge: '78% viral score', template: 'In [YEAR], I [FAILURE/CHALLENGE].\n\nEveryone told me to [CONVENTIONAL ADVICE].\n\nInstead, I [UNCONVENTIONAL ACTION].\n\n[TIME] later, here\'s what happened:\n\n🧵', charCount: 160 },
    { name: 'The Data Drop', badge: '71% viral score', template: 'I analyzed [NUMBER] [THINGS] and found something surprising:\n\n[STAT 1] — [INSIGHT]\n[STAT 2] — [INSIGHT]\n[STAT 3] — [INSIGHT]\n\nThe biggest takeaway? [CONCLUSION]', charCount: 200 },
  ];

  /* ---------- Theme Toggle ---------- */
  (function initTheme() {
    var toggle = document.getElementById('theme-toggle');
    var stored = localStorage.getItem('theme');
    if (stored === 'light') document.documentElement.setAttribute('data-theme', 'light');
    toggle.addEventListener('click', function () {
      var isLight = document.documentElement.getAttribute('data-theme') === 'light';
      document.documentElement.setAttribute('data-theme', isLight ? 'dark' : 'light');
      localStorage.setItem('theme', isLight ? 'dark' : 'light');
      updateChartColors();
    });
  })();

  /* ---------- Render KPIs ---------- */
  function renderKPIs() {
    var bestPattern = VIRAL_PATTERNS.reduce(function (best, p) { return p.score > best.score ? p : best; });
    var avgEngagement = VIRAL_PATTERNS.reduce(function (s, p) { return s + parseFloat(p.engagementRate); }, 0) / VIRAL_PATTERNS.length;
    var viralScore = Math.round(bestPattern.score * 0.85 + avgEngagement * 2);

    document.getElementById('kpi-viral-score').textContent = Math.min(viralScore, 100);
    document.getElementById('kpi-best-pattern').textContent = bestPattern.name;
    document.getElementById('kpi-pattern-rate').textContent = bestPattern.engagementRate + ' avg';
    document.getElementById('kpi-avg-engagement').textContent = avgEngagement.toFixed(1) + '%';

    document.querySelectorAll('.kpi-card').forEach(function (card) {
      card.classList.remove('skeleton');
    });
  }

  /* ---------- Comparison Columns (A8) ---------- */
  function renderComparison() {
    var viralCol = document.getElementById('viral-col');
    var normalCol = document.getElementById('normal-col');

    viralCol.innerHTML = VIRAL_PATTERNS.map(function (p) {
      return '<div class="analysis-panel" data-animate>' +
        '<div class="analysis-panel__header">' +
          '<span class="analysis-panel__name">' + p.name + '</span>' +
          '<span class="analysis-panel__score">' + p.score + '</span>' +
        '</div>' +
        '<div class="analysis-panel__bar-wrap">' +
          '<div class="analysis-panel__bar" style="width:' + p.score + '%"></div>' +
        '</div>' +
        '<p class="analysis-panel__desc">' + p.desc + '</p>' +
        '<div class="analysis-panel__example">' + p.examples + '</div>' +
      '</div>';
    }).join('');

    normalCol.innerHTML = NORMAL_PATTERNS.map(function (p) {
      return '<div class="analysis-panel" data-animate>' +
        '<div class="analysis-panel__header">' +
          '<span class="analysis-panel__name">' + p.name + '</span>' +
          '<span class="analysis-panel__score">' + p.score + '</span>' +
        '</div>' +
        '<div class="analysis-panel__bar-wrap">' +
          '<div class="analysis-panel__bar analysis-panel__bar--muted" style="width:' + p.score + '%"></div>' +
        '</div>' +
        '<p class="analysis-panel__desc">' + p.desc + '</p>' +
        '<div class="analysis-panel__example">' + p.examples + '</div>' +
      '</div>';
    }).join('');
  }

  /* ---------- Scatter Chart ---------- */
  var scatterChart = null;

  function renderScatterChart() {
    var wrap = document.getElementById('scatter-chart-wrap');
    var skeleton = wrap.querySelector('.skeleton-chart');
    if (skeleton) skeleton.remove();

    var ctx = document.getElementById('scatter-chart').getContext('2d');
    var isDark = document.documentElement.getAttribute('data-theme') !== 'light';

    var viralPoints = SCATTER_DATA.filter(function (d) { return d.viral; });
    var normalPoints = SCATTER_DATA.filter(function (d) { return !d.viral; });

    scatterChart = new Chart(ctx, {
      type: 'scatter',
      data: {
        datasets: [
          {
            label: 'Viral Tweets',
            data: viralPoints,
            backgroundColor: isDark ? 'rgba(244,63,94,0.7)' : 'rgba(225,29,72,0.6)',
            borderColor: isDark ? '#f43f5e' : '#e11d48',
            borderWidth: 1,
            pointRadius: 6,
            pointHoverRadius: 9,
          },
          {
            label: 'Regular Tweets',
            data: normalPoints,
            backgroundColor: isDark ? 'rgba(237,237,240,0.15)' : 'rgba(24,24,27,0.12)',
            borderColor: isDark ? 'rgba(237,237,240,0.3)' : 'rgba(24,24,27,0.25)',
            borderWidth: 1,
            pointRadius: 4,
            pointHoverRadius: 7,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            title: { display: true, text: 'Word Count', color: isDark ? 'rgba(237,237,240,0.5)' : 'rgba(24,24,27,0.5)', font: { family: "'Space Mono', monospace", size: 11, weight: 700 } },
            ticks: { color: isDark ? 'rgba(237,237,240,0.4)' : 'rgba(24,24,27,0.4)', font: { family: "'Space Mono', monospace", size: 10 } },
            grid: { color: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)' },
          },
          y: {
            title: { display: true, text: 'Engagement Rate (%)', color: isDark ? 'rgba(237,237,240,0.5)' : 'rgba(24,24,27,0.5)', font: { family: "'Space Mono', monospace", size: 11, weight: 700 } },
            beginAtZero: true,
            ticks: { color: isDark ? 'rgba(237,237,240,0.4)' : 'rgba(24,24,27,0.4)', font: { family: "'Space Mono', monospace", size: 10 }, callback: function (v) { return v + '%'; } },
            grid: { color: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)' },
          },
        },
        plugins: {
          legend: { position: 'top', labels: { color: isDark ? '#ededf0' : '#18181b', font: { family: "'Urbanist', sans-serif", size: 12 }, usePointStyle: true, pointStyle: 'circle', padding: 16 } },
          tooltip: {
            backgroundColor: isDark ? '#18181b' : '#fafafa',
            titleColor: isDark ? '#ededf0' : '#18181b',
            bodyColor: isDark ? 'rgba(237,237,240,0.7)' : 'rgba(24,24,27,0.7)',
            borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
            borderWidth: 1,
            titleFont: { family: "'Clash Display', sans-serif", weight: 600 },
            bodyFont: { family: "'Space Mono', monospace" },
            padding: 12,
            callbacks: { label: function (ctx) { return ctx.parsed.x + ' words · ' + ctx.parsed.y + '% engagement'; } },
          },
        },
      },
    });
  }

  /* ---------- Tweet Templates ---------- */
  function renderTemplates() {
    var grid = document.getElementById('template-grid');

    grid.innerHTML = TWEET_TEMPLATES.map(function (tmpl, idx) {
      return '<div class="analysis-panel" data-animate>' +
        '<div class="template-card__header">' +
          '<span class="template-card__name">' + tmpl.name + '</span>' +
          '<span class="template-card__badge">' + tmpl.badge + '</span>' +
        '</div>' +
        '<textarea class="template-card__textarea" id="template-textarea-' + idx + '" spellcheck="false">' + tmpl.template + '</textarea>' +
        '<div class="template-card__footer">' +
          '<span id="template-count-' + idx + '">' + tmpl.template.length + ' / 280 chars</span>' +
          '<button class="template-card__copy-btn" data-idx="' + idx + '" type="button">Copy</button>' +
        '</div>' +
      '</div>';
    }).join('');

    TWEET_TEMPLATES.forEach(function (_, idx) {
      var textarea = document.getElementById('template-textarea-' + idx);
      var counter = document.getElementById('template-count-' + idx);
      textarea.addEventListener('input', function () {
        var len = textarea.value.length;
        counter.textContent = len + ' / 280 chars';
        counter.style.color = len > 280 ? 'var(--color-negative)' : 'var(--color-text-muted)';
      });
    });

    grid.addEventListener('click', function (e) {
      var btn = e.target.closest('.template-card__copy-btn');
      if (!btn) return;
      var idx = btn.getAttribute('data-idx');
      var textarea = document.getElementById('template-textarea-' + idx);
      navigator.clipboard.writeText(textarea.value).then(function () {
        btn.textContent = 'COPIED!';
        setTimeout(function () { btn.textContent = 'Copy'; }, 1500);
      }).catch(function () {
        textarea.select();
        document.execCommand('copy');
        btn.textContent = 'COPIED!';
        setTimeout(function () { btn.textContent = 'Copy'; }, 1500);
      });
    });
  }

  /* ---------- Update Chart Colors ---------- */
  function updateChartColors() {
    if (scatterChart) { scatterChart.destroy(); renderScatterChart(); }
  }

  /* ---------- GSAP Animations — D19 alternating odd:-20px even:+20px ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    gsap.from('.hero__eyebrow', { opacity: 0, duration: 0.5, ease: 'power2.out' });
    gsap.from('.hero__title', { x: -30, opacity: 0, duration: 0.8, delay: 0.1, ease: 'power3.out' });
    gsap.from('.hero__subtitle', { x: -20, opacity: 0, duration: 0.6, delay: 0.25, ease: 'power3.out' });
    gsap.from('.hero__right .kpi-card', { x: 30, opacity: 0, duration: 0.5, stagger: 0.1, delay: 0.3, ease: 'power3.out' });

    var sections = document.querySelectorAll('.section');
    sections.forEach(function (section) {
      var title = section.querySelector('.section__title');
      if (title) {
        gsap.from(title, {
          scrollTrigger: { trigger: section, start: 'top 80%', toggleActions: 'play none none none' },
          y: 30, opacity: 0, duration: 0.6, ease: 'power3.out',
        });
      }

      /* D19: alternating direction */
      var cards = section.querySelectorAll('[data-animate]');
      if (cards.length) {
        cards.forEach(function (card, i) {
          var xOffset = (i % 2 === 0) ? -20 : 20;
          gsap.from(card, {
            scrollTrigger: { trigger: card, start: 'top 85%', toggleActions: 'play none none none' },
            x: xOffset, opacity: 0, duration: 0.5, ease: 'power3.out',
          });
        });
      }
    });

    gsap.from('.chart-container--scatter', {
      scrollTrigger: { trigger: '#section-scatter', start: 'top 80%', toggleActions: 'play none none none' },
      x: -20, opacity: 0, duration: 0.7, ease: 'power3.out',
    });
  }

  /* ---------- Error Handling ---------- */
  function showError(msg) {
    var toast = document.getElementById('error-toast');
    document.getElementById('error-msg').textContent = msg;
    toast.hidden = false;
  }

  document.getElementById('error-close').addEventListener('click', function () {
    document.getElementById('error-toast').hidden = true;
  });

  /* ---------- Init ---------- */
  function init() {
    try {
      renderKPIs();
      renderComparison();
      renderScatterChart();
      renderTemplates();
      initAnimations();
    } catch (err) {
      showError('Failed to initialize: ' + err.message);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
