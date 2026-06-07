/* ============================================================
   NFT Community Radar — script.js

   APIs: CoinGecko (ETH price) + Built-in NFT community data
   Animation: GSAP 3 + ScrollTrigger
   Entrance: D14 fade + scale(0.9)
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Register GSAP Plugins ---------- */
  gsap.registerPlugin(ScrollTrigger);

  /* ---------- Reduced Motion Check ---------- */
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Configuration ---------- */
  const CONFIG = {
    maxRetries: 2,
    retryBaseDelay: 1500,
  };

  const API = {
    ethPrice: () =>
      'https://pro-api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd&include_24hr_change=true',
  };

  /* ---------- Mock Data ---------- */
  const DISCUSSIONS = [
    { author: 'CryptoWhale', handle: '@cryptowhale', collection: 'Bored Ape Yacht Club', text: 'Floor price holding strong at 28 ETH. Community governance vote coming next week — could be a catalyst.', sentiment: 'bullish', replies: 142, likes: 891 },
    { author: 'NFTAnalyst', handle: '@nftanalyst', collection: 'Azuki', text: 'Azuki team just announced a new physical merch drop. Holders get early access. This is how you build community.', sentiment: 'bullish', replies: 67, likes: 423 },
    { author: 'DegenTrader', handle: '@degentrader', collection: 'Pudgy Penguins', text: 'Pudgy Penguins Walmart partnership is driving mainstream adoption. Volume up 340% this week.', sentiment: 'bullish', replies: 234, likes: 1205 },
    { author: 'ArtCollector', handle: '@artcollector', collection: 'Art Blocks', text: 'New curated drop from Tyler Hobbs. Generative art continues to push boundaries. Reserve your spot.', sentiment: 'neutral', replies: 89, likes: 567 },
    { author: 'FloorSweeper', handle: '@floorsweeper', collection: 'Doodles', text: 'Doodles 2 migration has been rocky. Some holders frustrated with the timeline. Watching closely.', sentiment: 'bearish', replies: 178, likes: 342 },
    { author: 'MetaverseMax', handle: '@metaversemax', collection: 'Otherside', text: 'Otherside second trip was incredible. 10K concurrent players. The metaverse is being built in real-time.', sentiment: 'bullish', replies: 312, likes: 1890 },
    { author: 'WhaleAlert', handle: '@whalealert', collection: 'CryptoPunks', text: 'Punk #5822 just sold for 8000 ETH. Alien punks remain the ultimate blue chip. Only 9 exist.', sentiment: 'bullish', replies: 456, likes: 3201 },
    { author: 'NFTSkeptic', handle: '@nftskeptic', collection: 'Moonbirds', text: 'Moonbirds going CC0 was controversial. Some holders feel the value proposition changed. Mixed signals.', sentiment: 'bearish', replies: 201, likes: 678 },
    { author: 'GalleryOwner', handle: '@galleryowner', collection: 'Fidenza', text: 'Fidenza #313 exhibited at Art Basel. When traditional art world meets on-chain art, magic happens.', sentiment: 'neutral', replies: 45, likes: 289 },
    { author: 'CommunityLead', handle: '@communitylead', collection: 'CloneX', text: 'Nike x CloneX collab dropping next month. Physical + digital fashion convergence is here.', sentiment: 'bullish', replies: 167, likes: 945 },
  ];

  const SENTIMENT_DATA = {
    overall: { bullish: 58, bearish: 22, neutral: 20 },
    collections: [
      { name: 'Bored Ape YC', bullish: 65, bearish: 15, neutral: 20 },
      { name: 'CryptoPunks', bullish: 72, bearish: 10, neutral: 18 },
      { name: 'Azuki', bullish: 55, bearish: 25, neutral: 20 },
      { name: 'Pudgy Penguins', bullish: 78, bearish: 8, neutral: 14 },
      { name: 'Doodles', bullish: 35, bearish: 40, neutral: 25 },
    ],
  };

  const EVENTS = [
    { date: '2024-08-15', title: 'BAYC Governance Vote', desc: 'Community vote on treasury allocation for Q4 initiatives', type: 'Governance' },
    { date: '2024-08-18', title: 'Azuki Merch Drop', desc: 'Physical merchandise exclusive to Azuki holders', type: 'Drop' },
    { date: '2024-08-22', title: 'Art Blocks Curated #28', desc: 'New generative art collection by acclaimed artist', type: 'Mint' },
    { date: '2024-08-25', title: 'Otherside Trip #3', desc: 'Third metaverse experience for Otherdeed holders', type: 'Event' },
    { date: '2024-09-01', title: 'NFT NYC Afterparty', desc: 'Community gathering during NFT NYC conference', type: 'Social' },
    { date: '2024-09-05', title: 'CloneX x Nike Drop', desc: 'Digital wearables with physical counterparts', type: 'Drop' },
  ];

  const RANKINGS = [
    { name: 'CryptoPunks', floor: '48.5 ETH', volume: '1,234 ETH', holders: '3,891', sentiment: 'bullish' },
    { name: 'Bored Ape YC', floor: '28.2 ETH', volume: '892 ETH', holders: '5,621', sentiment: 'bullish' },
    { name: 'Pudgy Penguins', floor: '12.8 ETH', volume: '2,156 ETH', holders: '4,892', sentiment: 'bullish' },
    { name: 'Azuki', floor: '8.4 ETH', volume: '567 ETH', holders: '5,234', sentiment: 'neutral' },
    { name: 'Milady', floor: '5.2 ETH', volume: '1,890 ETH', holders: '4,123', sentiment: 'bullish' },
    { name: 'Doodles', floor: '3.1 ETH', volume: '234 ETH', holders: '4,567', sentiment: 'bearish' },
    { name: 'Art Blocks', floor: '2.8 ETH', volume: '456 ETH', holders: '8,901', sentiment: 'neutral' },
    { name: 'CloneX', floor: '2.1 ETH', volume: '345 ETH', holders: '6,789', sentiment: 'neutral' },
  ];

  /* ============================================================
     GSAP ANIMATION SYSTEM
     ============================================================ */

  function animateHeroEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.hero__content > *', { opacity: 1 });
      return;
    }
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    tl.from('.hero__eyebrow', { opacity: 0, y: -15, duration: 0.5 })
      .from('.hero__title', { opacity: 0, y: 30, duration: 0.7 }, '-=0.2')
      .from('.hero__subtitle', { opacity: 0, y: 15, duration: 0.5 }, '-=0.3')
      .from('.hero__metric', { opacity: 0, y: 20, stagger: 0.12, duration: 0.5 }, '-=0.2');
  }

  /** D14: fade + scale(0.9) entrance */
  function animateCardEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.community-card, .sentiment-chart-wrap, .sentiment-item, .event-card, .rankings-table-wrap', {
        opacity: 1, scale: 1,
      });
      return;
    }

    const targets = gsap.utils.toArray('.community-card, .sentiment-chart-wrap, .sentiment-item, .event-card, .rankings-table-wrap');
    targets.forEach((el) => {
      gsap.to(el, {
        opacity: 1,
        scale: 1,
        duration: 0.6,
        ease: 'power2.out',
        scrollTrigger: {
          trigger: el,
          start: 'top 90%',
          toggleActions: 'play none none none',
        },
      });
    });
  }

  /* ============================================================
     THEME TOGGLE
     ============================================================ */
  function initThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    const html = document.documentElement;
    const stored = localStorage.getItem('nft-community-theme');
    if (stored) html.setAttribute('data-theme', stored);

    btn.addEventListener('click', () => {
      const current = html.getAttribute('data-theme') || 'light';
      const next = current === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-theme', next);
      localStorage.setItem('nft-community-theme', next);
    });
  }

  /* ============================================================
     DATA FETCHING
     ============================================================ */
  async function fetchWithRetry(url, retries = CONFIG.maxRetries) {
    for (let i = 0; i <= retries; i++) {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
      } catch (err) {
        if (i === retries) throw err;
        await new Promise((r) => setTimeout(r, CONFIG.retryBaseDelay * (i + 1)));
      }
    }
  }

  /* ---------- ETH Price ---------- */
  async function loadEthPrice() {
    const el = document.getElementById('metric-eth');
    if (!el) return;
    try {
      const data = await fetchWithRetry(API.ethPrice());
      const price = data.ethereum.usd;
      el.textContent = `$${price.toLocaleString()}`;
    } catch {
      el.textContent = '$3,450';
    }
  }

  /* ---------- Discussions Masonry ---------- */
  function loadDiscussions() {
    const container = document.getElementById('discussions-masonry');
    if (!container) return;

    document.getElementById('metric-discussions').textContent = DISCUSSIONS.length.toString();
    document.getElementById('metric-activity').textContent = '87.4';

    container.innerHTML = DISCUSSIONS.map((d) => {
      const initial = d.author.charAt(0).toUpperCase();
      const sentimentClass = `community-card__sentiment--${d.sentiment}`;
      return `
        <div class="community-card">
          <div class="community-card__author">
            <div class="community-card__avatar">${initial}</div>
            <div>
              <div class="community-card__name">${d.author}</div>
              <div class="community-card__handle">${d.handle}</div>
            </div>
          </div>
          <div class="community-card__collection">${d.collection}</div>
          <p class="community-card__text">${d.text}</p>
          <div class="community-card__meta">
            <span>${d.replies} replies</span>
            <span>${d.likes} likes</span>
            <span class="community-card__sentiment ${sentimentClass}">${d.sentiment}</span>
          </div>
        </div>`;
    }).join('');
  }

  /* ---------- Sentiment Chart ---------- */
  function loadSentimentChart() {
    const canvas = document.getElementById('sentiment-chart');
    if (!canvas) return;

    const style = getComputedStyle(document.documentElement);
    const bullish = style.getPropertyValue('--color-bullish').trim();
    const bearish = style.getPropertyValue('--color-bearish').trim();
    const neutral = style.getPropertyValue('--color-neutral').trim();

    new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: ['Bullish', 'Bearish', 'Neutral'],
        datasets: [{
          data: [SENTIMENT_DATA.overall.bullish, SENTIMENT_DATA.overall.bearish, SENTIMENT_DATA.overall.neutral],
          backgroundColor: [bullish, bearish, neutral],
          borderWidth: 0,
          spacing: 3,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '65%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: style.getPropertyValue('--color-text-secondary').trim(),
              font: { family: 'Space Mono', size: 11 },
              padding: 16,
            },
          },
          tooltip: {
            backgroundColor: style.getPropertyValue('--color-surface').trim(),
            titleColor: style.getPropertyValue('--color-text').trim(),
            bodyColor: style.getPropertyValue('--color-text-secondary').trim(),
            titleFont: { family: 'Space Mono' },
            bodyFont: { family: 'Space Mono' },
            borderColor: style.getPropertyValue('--color-border').trim(),
            borderWidth: 1,
          },
        },
      },
    });
  }

  /* ---------- Sentiment Breakdown ---------- */
  function loadSentimentBreakdown() {
    const container = document.getElementById('sentiment-breakdown');
    if (!container) return;

    container.innerHTML = SENTIMENT_DATA.collections.map((c) => `
      <div class="sentiment-item">
        <div class="sentiment-item__name">${c.name}</div>
        <div class="sentiment-item__bar">
          <div class="sentiment-item__fill sentiment-item__fill--bullish" style="width: ${c.bullish}%"></div>
        </div>
        <div class="sentiment-item__stats">
          <span>Bullish ${c.bullish}%</span>
          <span>Bearish ${c.bearish}%</span>
          <span>Neutral ${c.neutral}%</span>
        </div>
      </div>
    `).join('');
  }

  /* ---------- Events ---------- */
  function loadEvents() {
    const container = document.getElementById('events-list');
    if (!container) return;

    container.innerHTML = EVENTS.map((e) => `
      <div class="event-card">
        <div class="event-card__date">${e.date}</div>
        <div class="event-card__title">${e.title}</div>
        <p class="event-card__desc">${e.desc}</p>
        <span class="event-card__type">${e.type}</span>
      </div>
    `).join('');
  }

  /* ---------- Rankings Table ---------- */
  function loadRankings() {
    const tbody = document.getElementById('rankings-body');
    if (!tbody) return;

    tbody.innerHTML = RANKINGS.map((r, i) => `
      <tr>
        <td>${i + 1}</td>
        <td class="collection-name">${r.name}</td>
        <td>${r.floor}</td>
        <td>${r.volume}</td>
        <td>${r.holders}</td>
        <td><span class="sentiment-tag sentiment-tag--${r.sentiment}">${r.sentiment}</span></td>
      </tr>
    `).join('');
  }

  /* ============================================================
     HERO IMAGE
     ============================================================ */
  function initHeroImage() {
    const heroImageUrl = '{{HERO_IMAGE_URL}}';
    if (heroImageUrl && !heroImageUrl.startsWith('{{')) {
      const bg = document.querySelector('.hero__bg');
      if (bg) bg.style.setProperty('--hero-image', `url(${heroImageUrl})`);
    }
  }

  /* ============================================================
     INIT
     ============================================================ */
  function init() {
    initThemeToggle();
    initHeroImage();
    loadDiscussions();
    loadSentimentChart();
    loadSentimentBreakdown();
    loadEvents();
    loadRankings();
    loadEthPrice();

    animateHeroEntrance();
    requestAnimationFrame(() => {
      animateCardEntrance();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
