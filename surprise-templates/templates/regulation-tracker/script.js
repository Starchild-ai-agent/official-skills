/* ============================================================
   Crypto Regulation Tracker — script.js

   APIs: Built-in mock regulation data
   Animation: GSAP 3 + ScrollTrigger
   Entrance: D17 translateY(-30px)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var $ = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel) { return document.querySelectorAll(sel); };

  var REGULATIONS = [
    { date: 'Jun 2, 2026', title: 'EU MiCA Phase 3 Enforcement Begins', desc: 'Full enforcement of Markets in Crypto-Assets regulation across all EU member states, requiring licensing for all crypto service providers.', impact: 'high', region: 'Europe', tokens: ['All EU-listed tokens'] },
    { date: 'May 28, 2026', title: 'SEC Approves Spot Ethereum ETF Options', desc: 'Securities and Exchange Commission greenlights options trading on spot Ethereum ETFs, expanding institutional access.', impact: 'medium', region: 'United States', tokens: ['ETH'] },
    { date: 'May 20, 2026', title: 'Japan Lowers Crypto Tax to 20%', desc: 'Japanese Diet passes bill reducing crypto capital gains tax from progressive rates to flat 20%, aligning with securities taxation.', impact: 'medium', region: 'Asia Pacific', tokens: ['All'] },
    { date: 'May 15, 2026', title: 'UK FCA Stablecoin Framework Published', desc: 'Financial Conduct Authority releases final rules for stablecoin issuance and custody in the United Kingdom.', impact: 'high', region: 'United Kingdom', tokens: ['USDC', 'USDT', 'DAI'] },
    { date: 'May 8, 2026', title: 'Brazil Central Bank DeFi Guidelines', desc: 'Banco Central do Brasil issues guidelines for DeFi protocol compliance, requiring KYC for front-end operators.', impact: 'medium', region: 'Latin America', tokens: ['DeFi tokens'] },
    { date: 'Apr 30, 2026', title: 'Singapore MAS Restricts Retail Staking', desc: 'Monetary Authority of Singapore limits retail access to staking services, requiring accredited investor status for yields above 5%.', impact: 'high', region: 'Asia Pacific', tokens: ['ETH', 'SOL', 'DOT'] },
    { date: 'Apr 22, 2026', title: 'US Treasury Mixer Sanctions Update', desc: 'OFAC updates sanctions list to include additional privacy-focused protocols and mixing services.', impact: 'high', region: 'United States', tokens: ['Privacy coins'] },
    { date: 'Apr 15, 2026', title: 'South Korea Travel Rule Expansion', desc: 'Korean Financial Services Commission extends travel rule to cover all crypto transactions above $500.', impact: 'low', region: 'Asia Pacific', tokens: ['All'] },
  ];

  var AFFECTED_TOKENS = [
    { name: 'Ethereum', symbol: 'ETH', risk: 'medium', regulations: 3 },
    { name: 'Tether', symbol: 'USDT', risk: 'high', regulations: 4 },
    { name: 'USD Coin', symbol: 'USDC', risk: 'medium', regulations: 3 },
    { name: 'Solana', symbol: 'SOL', risk: 'low', regulations: 1 },
    { name: 'Monero', symbol: 'XMR', risk: 'high', regulations: 5 },
    { name: 'DAI', symbol: 'DAI', risk: 'medium', regulations: 2 },
  ];

  var TIPS = [
    { title: 'KYC/AML Compliance', desc: 'Ensure all exchange accounts have completed identity verification. Regulators are increasingly requiring full KYC for all crypto transactions.' },
    { title: 'Tax Record Keeping', desc: 'Maintain detailed records of all transactions including dates, amounts, and cost basis. Use crypto tax software for automated tracking.' },
    { title: 'Stablecoin Diversification', desc: 'Spread stablecoin holdings across regulated issuers. MiCA and UK FCA rules may affect availability of certain stablecoins.' },
    { title: 'Privacy Tool Awareness', desc: 'Review your use of mixing services and privacy protocols. OFAC sanctions may apply to certain tools and their users.' },
    { title: 'Jurisdictional Planning', desc: 'Understand the regulatory landscape of your jurisdiction. Consider consulting a crypto-specialized legal advisor for complex holdings.' },
  ];

  var regionChart = null;

  function renderStats() {
    $('#stat-total').textContent = REGULATIONS.length.toString();
    var highCount = REGULATIONS.filter(function (r) { return r.impact === 'high'; }).length;
    $('#stat-high').textContent = highCount.toString();
  }

  function renderTimeline() {
    var timeline = $('#timeline');
    timeline.innerHTML = REGULATIONS.map(function (r) {
      return '<div class="timeline-item" style="opacity:0">' +
        '<div class="timeline-item__date">' + r.date + '</div>' +
        '<h3 class="timeline-item__title">' + r.title + '</h3>' +
        '<p class="timeline-item__desc">' + r.desc + '</p>' +
        '<div class="timeline-item__meta">' +
          '<span class="impact-badge impact-badge--' + r.impact + '">' + r.impact + ' impact</span>' +
          '<span class="region-badge">' + r.region + '</span>' +
        '</div>' +
      '</div>';
    }).join('');

    if (!prefersReducedMotion) {
      gsap.fromTo('.timeline-item',
        { opacity: 0, y: -30 },
        { opacity: 1, y: 0, duration: 0.5, stagger: 0.1, ease: 'power2.out',
          scrollTrigger: { trigger: '#timeline-section', start: 'top 80%', toggleActions: 'play none none none' }
        }
      );
    } else {
      $$('.timeline-item').forEach(function (el) { el.style.opacity = '1'; });
    }
  }

  function renderRegionChart() {
    var ctx = $('#region-chart').getContext('2d');
    var style = getComputedStyle(document.documentElement);
    var textColor = style.getPropertyValue('--color-text-secondary').trim();
    var colors = [
      style.getPropertyValue('--chart-1').trim(),
      style.getPropertyValue('--chart-2').trim(),
      style.getPropertyValue('--chart-3').trim(),
      style.getPropertyValue('--chart-4').trim(),
      style.getPropertyValue('--chart-5').trim(),
      style.getPropertyValue('--chart-6').trim()
    ];

    var regionMap = {};
    REGULATIONS.forEach(function (r) {
      regionMap[r.region] = (regionMap[r.region] || 0) + 1;
    });

    if (regionChart) regionChart.destroy();

    regionChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: Object.keys(regionMap),
        datasets: [{
          data: Object.values(regionMap),
          backgroundColor: Object.keys(regionMap).map(function (_, i) { return colors[i % colors.length]; }),
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: textColor, font: { family: "'Source Sans 3', sans-serif", size: 12 } }
          }
        }
      }
    });
  }

  function renderTokensGrid() {
    var grid = $('#tokens-grid');
    grid.innerHTML = AFFECTED_TOKENS.map(function (t) {
      return '<div class="token-impact-card" style="opacity:0">' +
        '<div class="token-impact-card__name">' + t.name + '</div>' +
        '<div class="token-impact-card__symbol">' + t.symbol + '</div>' +
        '<div class="token-impact-card__risk">' +
          '<span class="impact-badge impact-badge--' + t.risk + '">' + t.risk + ' risk</span>' +
        '</div>' +
        '<div style="font-size:var(--text-xs);color:var(--color-text-muted);font-family:var(--font-mono)">' +
          t.regulations + ' regulations' +
        '</div>' +
      '</div>';
    }).join('');

    if (!prefersReducedMotion) {
      gsap.fromTo('.token-impact-card',
        { opacity: 0, y: -30 },
        { opacity: 1, y: 0, duration: 0.4, stagger: 0.08, ease: 'power2.out',
          scrollTrigger: { trigger: '#tokens-section', start: 'top 80%', toggleActions: 'play none none none' }
        }
      );
    } else {
      $$('.token-impact-card').forEach(function (el) { el.style.opacity = '1'; });
    }
  }

  function renderTips() {
    var list = $('#tips-list');
    list.innerHTML = TIPS.map(function (t, i) {
      return '<div class="tip-card" style="opacity:0">' +
        '<span class="tip-card__number">' + (i + 1) + '</span>' +
        '<div class="tip-card__content">' +
          '<h3 class="tip-card__title">' + t.title + '</h3>' +
          '<p class="tip-card__desc">' + t.desc + '</p>' +
        '</div>' +
      '</div>';
    }).join('');

    if (!prefersReducedMotion) {
      gsap.fromTo('.tip-card',
        { opacity: 0, y: -30 },
        { opacity: 1, y: 0, duration: 0.4, stagger: 0.1, ease: 'power2.out',
          scrollTrigger: { trigger: '#compliance-section', start: 'top 80%', toggleActions: 'play none none none' }
        }
      );
    } else {
      $$('.tip-card').forEach(function (el) { el.style.opacity = '1'; });
    }
  }

  function initTheme() {
    var saved = localStorage.getItem('regulation-tracker-theme');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
    $('#theme-toggle').addEventListener('click', function () {
      var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
      localStorage.setItem('regulation-tracker-theme', isDark ? 'light' : 'dark');
      renderRegionChart();
    });
  }

  function initAnimations() {
    if (prefersReducedMotion) return;
    var heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl
      .from('.hero__label', { opacity: 0, y: -30, duration: 0.5 })
      .from('.hero__title', { opacity: 0, y: -30, duration: 0.7 }, '-=0.3')
      .from('.hero__subtitle', { opacity: 0, y: -20, duration: 0.5 }, '-=0.3')
      .from('.hero__stat-card', { opacity: 0, y: -30, duration: 0.5, stagger: 0.15 }, '-=0.3');
  }

  function init() {
    initTheme();
    renderStats();
    renderTimeline();
    renderRegionChart();
    renderTokensGrid();
    renderTips();
    initAnimations();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
