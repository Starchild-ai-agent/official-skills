/* ============================================================
   Personalized Crypto News Feed — script.js

   APIs: Built-in mock news data
   Animation: GSAP 3 + ScrollTrigger
   Entrance: D10 translateX(-50px)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var $ = function (sel) { return document.querySelector(sel); };
  var $$ = function (sel) { return document.querySelectorAll(sel); };

  /* ---------- Mock News Data ---------- */
  var NEWS = [
    { id: 1, headline: 'Ethereum L2 TVL Surpasses $45B as Base and Arbitrum Lead Growth', excerpt: 'Layer 2 scaling solutions continue to attract capital with Base seeing a 340% increase in TVL over the past quarter, driven by DeFi protocol deployments.', category: 'L2', sentiment: 'bullish', source: 'The Block', trust: 5, time: '2m ago', tokens: ['ethereum'] },
    { id: 2, headline: 'SEC Delays Decision on Spot Solana ETF Applications', excerpt: 'The Securities and Exchange Commission has pushed back its deadline for reviewing multiple Solana ETF applications, citing need for additional public comment.', category: 'Regulation', sentiment: 'bearish', source: 'CoinDesk', trust: 5, time: '15m ago', tokens: ['solana'] },
    { id: 3, headline: 'Uniswap V4 Hooks Drive 200% Surge in DEX Volume', excerpt: 'The introduction of custom hooks in Uniswap V4 has enabled novel trading strategies, pushing decentralized exchange volumes to new monthly highs.', category: 'DeFi', sentiment: 'bullish', source: 'DeFi Pulse', trust: 4, time: '32m ago', tokens: ['ethereum', 'uniswap'] },
    { id: 4, headline: 'Bitcoin Mining Difficulty Reaches All-Time High After Halving', excerpt: 'Network hash rate continues to climb despite reduced block rewards, with mining difficulty adjusting upward for the fifth consecutive period.', category: 'Market', sentiment: 'neutral', source: 'Bitcoin Magazine', trust: 5, time: '1h ago', tokens: ['bitcoin'] },
    { id: 5, headline: 'Pudgy Penguins Floor Price Drops 30% Amid NFT Market Cooldown', excerpt: 'Blue-chip NFT collections face selling pressure as broader market sentiment shifts, with Pudgy Penguins seeing significant floor price decline.', category: 'NFT', sentiment: 'bearish', source: 'NFT Now', trust: 3, time: '1h ago', tokens: [] },
    { id: 6, headline: 'Aave Proposes Integration with Chainlink CCIP for Cross-Chain Lending', excerpt: 'Aave governance forum sees new proposal to leverage Chainlink cross-chain interoperability protocol for unified lending markets across multiple chains.', category: 'DeFi', sentiment: 'bullish', source: 'The Defiant', trust: 4, time: '2h ago', tokens: ['ethereum', 'chainlink'] },
    { id: 7, headline: 'EU MiCA Regulations Take Full Effect, Exchanges Scramble to Comply', excerpt: 'European crypto exchanges face new compliance requirements as Markets in Crypto-Assets regulation enters its final implementation phase.', category: 'Regulation', sentiment: 'neutral', source: 'Reuters', trust: 5, time: '2h ago', tokens: [] },
    { id: 8, headline: 'Solana DePIN Projects Attract $2B in New Investment', excerpt: 'Decentralized physical infrastructure networks built on Solana see massive capital inflows, with Helium and Render leading the charge.', category: 'Market', sentiment: 'bullish', source: 'Messari', trust: 4, time: '3h ago', tokens: ['solana'] },
    { id: 9, headline: 'Optimism Superchain Adds Three New Chains in Single Week', excerpt: 'The OP Stack continues to gain adoption as three new rollups join the Superchain ecosystem, bringing total chain count to over 30.', category: 'L2', sentiment: 'bullish', source: 'L2Beat', trust: 4, time: '3h ago', tokens: ['ethereum', 'optimism'] },
    { id: 10, headline: 'Stablecoin Market Cap Hits $180B Record', excerpt: 'Total stablecoin supply reaches new all-time high, with USDC gaining market share from USDT for the first time in 18 months.', category: 'Market', sentiment: 'bullish', source: 'CoinGecko', trust: 5, time: '4h ago', tokens: [] },
    { id: 11, headline: 'Art Blocks Curated Drops New Generative Collection', excerpt: 'Renowned generative art platform Art Blocks releases highly anticipated curated collection, selling out in under 3 minutes.', category: 'NFT', sentiment: 'neutral', source: 'ArtNet', trust: 3, time: '4h ago', tokens: ['ethereum'] },
    { id: 12, headline: 'Arbitrum DAO Approves $50M Gaming Catalyst Program', excerpt: 'Arbitrum governance passes proposal to fund gaming ecosystem development with a $50 million incentive program over 12 months.', category: 'L2', sentiment: 'bullish', source: 'The Block', trust: 5, time: '5h ago', tokens: ['ethereum'] },
    { id: 13, headline: 'MakerDAO Rebrands to Sky Protocol, Launches New Governance Token', excerpt: 'The largest DeFi lending protocol completes its rebranding initiative, introducing SKY token alongside the existing MKR governance structure.', category: 'DeFi', sentiment: 'neutral', source: 'DeFi Llama', trust: 4, time: '5h ago', tokens: ['ethereum'] },
    { id: 14, headline: 'Japan Considers Lowering Crypto Tax Rate to 20%', excerpt: 'Japanese financial regulators propose reducing cryptocurrency capital gains tax from the current progressive rate to a flat 20%, aligning with traditional securities.', category: 'Regulation', sentiment: 'bullish', source: 'Nikkei', trust: 5, time: '6h ago', tokens: [] },
    { id: 15, headline: 'Polygon zkEVM Processes 10M Transactions in Single Day', excerpt: 'Polygon zero-knowledge rollup hits new throughput milestone, demonstrating scalability improvements from recent Napoli upgrade.', category: 'L2', sentiment: 'bullish', source: 'Polygon Blog', trust: 3, time: '7h ago', tokens: ['polygon'] },
  ];

  var currentCategory = 'all';
  var displayCount = 8;

  /* ---------- Render Feed ---------- */
  function renderFeed() {
    var filtered = NEWS.filter(function (n) {
      return currentCategory === 'all' || n.category === currentCategory;
    });
    var visible = filtered.slice(0, displayCount);
    var container = $('#feed-container');

    container.innerHTML = visible.map(function (n) {
      var trustDots = '';
      for (var i = 0; i < 5; i++) {
        trustDots += '<span class="source-trust__dot' + (i < n.trust ? ' source-trust__dot--filled' : '') + '"></span>';
      }

      return '<article class="feed-item" data-id="' + n.id + '" style="opacity:0">' +
        '<div class="feed-item__time">' + n.time + '</div>' +
        '<div class="feed-item__content">' +
          '<h3 class="feed-item__headline">' + n.headline + '</h3>' +
          '<p class="feed-item__excerpt">' + n.excerpt + '</p>' +
          '<div class="feed-item__meta">' +
            '<span class="feed-item__tag">' + n.category + '</span>' +
            '<span class="feed-item__sentiment sentiment--' + n.sentiment + '">' + n.sentiment + '</span>' +
            '<span class="feed-item__source">' + n.source + ' <span class="source-trust">' + trustDots + '</span></span>' +
          '</div>' +
        '</div>' +
      '</article>';
    }).join('');

    // D10 entrance: translateX(-50px)
    if (!prefersReducedMotion) {
      gsap.fromTo('.feed-item',
        { opacity: 0, x: -50 },
        { opacity: 1, x: 0, duration: 0.5, stagger: 0.06, ease: 'power2.out' }
      );
    } else {
      $$('.feed-item').forEach(function (el) { el.style.opacity = '1'; });
    }

    // Show/hide load more
    var loadMoreBtn = $('#load-more');
    if (displayCount >= filtered.length) {
      loadMoreBtn.style.display = 'none';
    } else {
      loadMoreBtn.style.display = 'block';
    }

    // Update alert banner with latest
    if (visible.length > 0) {
      $('#alert-text').textContent = visible[0].headline;
    }
  }

  /* ---------- Theme Toggle ---------- */
  function initTheme() {
    var saved = localStorage.getItem('personalized-news-theme');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');

    $('#theme-toggle').addEventListener('click', function () {
      var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
      localStorage.setItem('personalized-news-theme', isDark ? 'light' : 'dark');
    });
  }

  /* ---------- Filters ---------- */
  function initFilters() {
    $$('.filter-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        $$('.filter-btn').forEach(function (b) { b.classList.remove('filter-btn--active'); });
        btn.classList.add('filter-btn--active');
        currentCategory = btn.dataset.cat;
        displayCount = 8;
        renderFeed();
      });
    });

    $('#load-more').addEventListener('click', function () {
      displayCount += 5;
      renderFeed();
    });
  }

  /* ---------- GSAP Animations ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    var heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl
      .from('.hero__alert-banner', { opacity: 0, y: -20, duration: 0.5 })
      .from('.hero__title', { opacity: 0, x: -50, duration: 0.7 }, '-=0.2')
      .from('.hero__subtitle', { opacity: 0, x: -30, duration: 0.5 }, '-=0.3');

    gsap.from('.filter-bar', {
      scrollTrigger: {
        trigger: '.filter-bar',
        start: 'top 90%',
        toggleActions: 'play none none none',
      },
      opacity: 0,
      x: -50,
      duration: 0.6,
      ease: 'power2.out',
    });
  }

  /* ---------- Init ---------- */
  function init() {
    initTheme();
    renderFeed();
    initFilters();
    initAnimations();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
