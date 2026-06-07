/* ============================================================
   CT Alpha — script.js
   Skeleton: A10 Notification/Alert | Entry: D2 stagger left-to-right
   Hero: H12 Alert Banner | Cards: .alpha-signal
   ============================================================ */
(function () {
  'use strict';
  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var SIGNALS = [
    { time: '14:32', type: 'discovery', title: 'New DEX on Base with 400% volume spike', desc: 'Aerodrome fork "BaseDEX" launched 6 hours ago. Already $12M TVL. Team is anon but contracts verified.', tokens: ['BASE','AERO'], quality: 88, source: 'On-chain Scanner' },
    { time: '13:15', type: 'airdrop', title: 'LayerZero Season 2 criteria leaked', desc: 'Insider info suggests LayerZero S2 airdrop will weight cross-chain message volume heavily. Minimum 50 messages across 5+ chains.', tokens: ['ZRO','STG'], quality: 82, source: 'CT Insider' },
    { time: '12:48', type: 'protocol', title: 'Uniswap v4 hooks going live on mainnet', desc: 'Uniswap v4 with custom hooks deploying to Ethereum mainnet this week. First hooks include dynamic fee, TWAP oracle, and limit orders.', tokens: ['UNI','ETH'], quality: 95, source: 'Official Announcement' },
    { time: '11:22', type: 'discovery', title: 'AI agent token $AGEN stealth launched', desc: 'New AI agent framework token launched on Solana. Built by ex-Anthropic engineers. $2M market cap, growing fast.', tokens: ['AGEN','SOL'], quality: 71, source: 'CT Alpha Group' },
    { time: '10:05', type: 'governance', title: 'Arbitrum DAO voting on 200M ARB incentive program', desc: 'Major governance proposal to allocate 200M ARB tokens for ecosystem incentives over 12 months.', tokens: ['ARB'], quality: 90, source: 'Governance Forum' },
    { time: '09:30', type: 'vulnerability', title: 'Critical bug found in popular yield aggregator', desc: 'White hat discovered reentrancy vulnerability in YieldMax protocol. $45M at risk. Emergency pause executed.', tokens: ['ETH'], quality: 96, source: 'Security Researcher' },
    { time: '08:15', type: 'discovery', title: 'Pendle-style yield tokenization coming to Solana', desc: 'New protocol "SolYield" bringing fixed-rate yield and yield trading to Solana. Backed by Multicoin Capital.', tokens: ['SOL','PENDLE'], quality: 78, source: 'VC Leak' },
    { time: '07:00', type: 'airdrop', title: 'Scroll airdrop confirmed for Q3', desc: 'Scroll team confirmed token launch and airdrop for active users. Bridge activity, DEX volume, and lending positions will be weighted.', tokens: ['SCR','ETH'], quality: 85, source: 'Official Blog' },
    { time: '06:20', type: 'protocol', title: 'EigenLayer restaking rewards going live', desc: 'EigenLayer activating slashing and reward distribution for AVS operators. Expected 4-8% additional APR on staked ETH.', tokens: ['EIGEN','ETH'], quality: 92, source: 'Official Announcement' },
    { time: '05:45', type: 'discovery', title: 'New memecoin launchpad gaining traction on Base', desc: 'FunBase launching memecoins with bonding curve mechanics similar to pump.fun. Already 500+ tokens launched in 24h.', tokens: ['BASE','FUNB'], quality: 55, source: 'CT Degen Chat' },
  ];

  var typeCounts = {};
  SIGNALS.forEach(function (s) { typeCounts[s.type] = (typeCounts[s.type] || 0) + 1; });

  var QUALITY_CATEGORIES = [
    { title: 'Official Announcements', score: 96, credibility: 98, timeliness: 82, count: SIGNALS.filter(function(s){return s.source==='Official Announcement'||s.source==='Official Blog'}).length },
    { title: 'On-chain Scanners', score: 88, credibility: 90, timeliness: 95, count: SIGNALS.filter(function(s){return s.source==='On-chain Scanner'}).length },
    { title: 'CT Alpha Groups', score: 68, credibility: 62, timeliness: 94, count: SIGNALS.filter(function(s){return s.source.indexOf('CT')!==-1}).length },
    { title: 'Security Researchers', score: 97, credibility: 98, timeliness: 99, count: SIGNALS.filter(function(s){return s.source==='Security Researcher'}).length },
  ];

  /* Theme Toggle */
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

  /* Clock */
  function updateClock() {
    var el = document.getElementById('hero-time');
    var now = new Date();
    el.textContent = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    el.setAttribute('datetime', now.toISOString());
  }
  updateClock(); setInterval(updateClock, 1000);

  /* KPIs */
  function renderKPIs() {
    document.getElementById('kpi-signal-count').textContent = SIGNALS.length;
    var top = SIGNALS.reduce(function(b,s){return s.quality>b.quality?s:b});
    document.getElementById('kpi-top-signal').textContent = top.title.substring(0,20) + '…';
    document.getElementById('kpi-top-signal-type').textContent = top.type;
    var avg = Math.round(SIGNALS.reduce(function(s,sig){return s+sig.quality},0)/SIGNALS.length);
    document.getElementById('kpi-avg-quality').textContent = avg + '/100';
    document.querySelectorAll('.kpi-card').forEach(function(c){c.classList.remove('skeleton')});
  }

  /* Alpha Signal Feed (A10 Notification/Alert) */
  function renderTimeline() {
    var feed = document.getElementById('timeline');
    feed.innerHTML = SIGNALS.map(function (sig) {
      return '<div class="alpha-signal" data-animate>' +
        '<div class="alpha-signal__header">' +
          '<span class="alpha-signal__time">' + sig.time + '</span>' +
          '<span class="alpha-signal__type">' + sig.type + '</span>' +
          '<span class="alpha-signal__quality">Q: ' + sig.quality + '</span>' +
        '</div>' +
        '<div class="alpha-signal__title">' + sig.title + '</div>' +
        '<p class="alpha-signal__desc">' + sig.desc + '</p>' +
        '<div class="alpha-signal__tokens">' +
          sig.tokens.map(function(t){return '<span class="alpha-signal__token">$'+t+'</span>'}).join('') +
        '</div>' +
        '<span class="alpha-signal__source">Source: ' + sig.source + '</span>' +
      '</div>';
    }).join('');
  }

  /* Source Doughnut */
  var sourceChart = null;
  function renderSourceChart() {
    var wrap = document.getElementById('source-chart-wrap');
    var skeleton = wrap.querySelector('.skeleton-chart');
    if (skeleton) skeleton.remove();
    var ctx = document.getElementById('source-chart').getContext('2d');
    var isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    var labels = Object.keys(typeCounts).map(function(k){return k.charAt(0).toUpperCase()+k.slice(1)});
    var data = Object.values(typeCounts);
    var colors = ['#f59e0b','#fbbf24','#d97706','#92400e','#78350f'];

    sourceChart = new Chart(ctx, {
      type: 'doughnut',
      data: { labels: labels, datasets: [{ data: data, backgroundColor: colors.slice(0,labels.length), borderColor: isDark ? '#1a1a1a' : '#fafaf9', borderWidth: 3, hoverOffset: 8 }] },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '55%',
        plugins: {
          legend: { position: 'bottom', labels: { color: isDark ? '#e5e5e5' : '#1c1917', font: { family: "'Lexend', sans-serif", size: 12 }, usePointStyle: true, pointStyle: 'circle', padding: 16 } },
          tooltip: { backgroundColor: isDark ? '#1a1a1a' : '#fafaf9', titleColor: isDark ? '#e5e5e5' : '#1c1917', bodyColor: isDark ? 'rgba(229,229,229,0.7)' : 'rgba(28,25,23,0.7)', borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)', borderWidth: 1, titleFont: { family: "'Victor Mono', monospace", weight: 600 }, bodyFont: { family: "'Victor Mono', monospace" }, padding: 12 },
        },
      },
    });
  }

  /* Quality Cards */
  function renderQuality() {
    var grid = document.getElementById('quality-grid');
    grid.innerHTML = QUALITY_CATEGORIES.map(function (cat) {
      return '<div class="alpha-signal" data-animate>' +
        '<div class="alpha-signal__title">' + cat.title + '</div>' +
        '<div class="alpha-signal__bar-wrap"><div class="alpha-signal__bar" style="width:' + cat.score + '%"></div></div>' +
        '<div class="alpha-signal__score-row">' +
          '<span>Score: <span class="alpha-signal__score-value">' + cat.score + '</span></span>' +
          '<span>Credibility: <span class="alpha-signal__score-value">' + cat.credibility + '</span></span>' +
          '<span>Timeliness: <span class="alpha-signal__score-value">' + cat.timeliness + '</span></span>' +
          '<span>' + cat.count + ' signals</span>' +
        '</div>' +
      '</div>';
    }).join('');
  }

  function updateChartColors() {
    if (sourceChart) { sourceChart.destroy(); renderSourceChart(); }
  }

  /* GSAP — D2 stagger left-to-right */
  function initAnimations() {
    if (prefersReducedMotion) return;
    gsap.from('.alert-banner', { x: -60, opacity: 0, duration: 0.7, ease: 'power3.out' });
    gsap.from('.kpi-card', { x: -40, opacity: 0, duration: 0.5, stagger: 0.1, delay: 0.2, ease: 'power3.out' });

    var sections = document.querySelectorAll('.section');
    sections.forEach(function (section) {
      var title = section.querySelector('.section__title');
      if (title) {
        gsap.from(title, {
          scrollTrigger: { trigger: section, start: 'top 80%', toggleActions: 'play none none none' },
          x: -40, opacity: 0, duration: 0.6, ease: 'power3.out',
        });
      }
      var cards = section.querySelectorAll('[data-animate]');
      if (cards.length) {
        gsap.from(cards, {
          scrollTrigger: { trigger: section, start: 'top 75%', toggleActions: 'play none none none' },
          x: -40, opacity: 0, duration: 0.5, stagger: 0.06, ease: 'power3.out',
        });
      }
    });
    gsap.from('.chart-container--doughnut', {
      scrollTrigger: { trigger: '#section-sources', start: 'top 80%', toggleActions: 'play none none none' },
      x: -40, opacity: 0, duration: 0.7, ease: 'power3.out',
    });
  }

  function showError(msg) {
    var toast = document.getElementById('error-toast');
    document.getElementById('error-msg').textContent = msg;
    toast.hidden = false;
  }
  document.getElementById('error-close').addEventListener('click', function () {
    document.getElementById('error-toast').hidden = true;
  });

  function init() {
    try {
      renderKPIs();
      renderTimeline();
      renderSourceChart();
      renderQuality();
      initAnimations();
    } catch (err) {
      showError('Failed to initialize: ' + err.message);
    }
  }

  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', init); }
  else { init(); }
})();
