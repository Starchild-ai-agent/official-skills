/* ============================================================
   NFT Rarity Explorer — script.js

   APIs: Built-in simulated NFT rarity data
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
  };

  /* ---------- Simulated NFT Data ---------- */
  const TRAIT_CATEGORIES = ['Background', 'Body', 'Eyes', 'Mouth', 'Headwear', 'Clothing', 'Accessory'];

  const TRAIT_VALUES = {
    Background: ['Cosmic Purple', 'Midnight Blue', 'Sunset Gold', 'Forest Green', 'Arctic White', 'Lava Red', 'Neon Pink', 'Deep Ocean'],
    Body: ['Diamond', 'Gold', 'Silver', 'Bronze', 'Obsidian', 'Crystal', 'Holographic', 'Matte'],
    Eyes: ['Laser', 'Galaxy', 'Fire', 'Ice', 'Void', 'Rainbow', 'Emerald', 'Ruby', 'Sapphire'],
    Mouth: ['Grin', 'Stoic', 'Fangs', 'Smile', 'Whistle', 'Mask', 'Cigar'],
    Headwear: ['Crown', 'Halo', 'Horns', 'None', 'Beanie', 'Top Hat', 'Bandana', 'Helmet'],
    Clothing: ['Suit', 'Hoodie', 'Armor', 'Robe', 'None', 'Jacket', 'Cape', 'Tuxedo'],
    Accessory: ['Chain', 'Ring', 'None', 'Earring', 'Monocle', 'Watch', 'Pendant'],
  };

  const RARITY_WEIGHTS = {
    Background: { 'Cosmic Purple': 2, 'Midnight Blue': 5, 'Sunset Gold': 3, 'Forest Green': 8, 'Arctic White': 10, 'Lava Red': 4, 'Neon Pink': 6, 'Deep Ocean': 7 },
    Body: { 'Diamond': 1, 'Gold': 3, 'Silver': 5, 'Bronze': 8, 'Obsidian': 4, 'Crystal': 2, 'Holographic': 3, 'Matte': 12 },
    Eyes: { 'Laser': 2, 'Galaxy': 3, 'Fire': 5, 'Ice': 6, 'Void': 1, 'Rainbow': 4, 'Emerald': 7, 'Ruby': 3, 'Sapphire': 5 },
    Mouth: { 'Grin': 10, 'Stoic': 8, 'Fangs': 3, 'Smile': 12, 'Whistle': 5, 'Mask': 2, 'Cigar': 4 },
    Headwear: { 'Crown': 1, 'Halo': 2, 'Horns': 4, 'None': 15, 'Beanie': 8, 'Top Hat': 3, 'Bandana': 6, 'Helmet': 5 },
    Clothing: { 'Suit': 6, 'Hoodie': 10, 'Armor': 3, 'Robe': 4, 'None': 12, 'Jacket': 8, 'Cape': 2, 'Tuxedo': 5 },
    Accessory: { 'Chain': 5, 'Ring': 4, 'None': 15, 'Earring': 6, 'Monocle': 2, 'Watch': 7, 'Pendant': 3 },
  };

  /* Seeded random for consistent data */
  let seed = 42;
  function seededRandom() {
    seed = (seed * 16807 + 0) % 2147483647;
    return (seed - 1) / 2147483646;
  }

  function weightedPick(category) {
    const weights = RARITY_WEIGHTS[category];
    const entries = Object.entries(weights);
    const total = entries.reduce((s, [, w]) => s + w, 0);
    let r = seededRandom() * total;
    for (const [val, w] of entries) {
      r -= w;
      if (r <= 0) return val;
    }
    return entries[entries.length - 1][0];
  }

  function generateNFTCollection(count) {
    const nfts = [];
    const traitCounts = {};

    TRAIT_CATEGORIES.forEach(cat => {
      traitCounts[cat] = {};
      TRAIT_VALUES[cat].forEach(v => { traitCounts[cat][v] = 0; });
    });

    for (let i = 0; i < count; i++) {
      const traits = {};
      TRAIT_CATEGORIES.forEach(cat => {
        const val = weightedPick(cat);
        traits[cat] = val;
        traitCounts[cat][val] = (traitCounts[cat][val] || 0) + 1;
      });
      nfts.push({
        id: i + 1,
        name: `Ethereal #${String(i + 1).padStart(4, '0')}`,
        traits,
        price: Math.round((0.5 + seededRandom() * 20) * 100) / 100,
      });
    }

    // Calculate rarity scores
    nfts.forEach(nft => {
      let score = 0;
      let rarestTrait = { category: '', value: '', rarity: 1 };
      TRAIT_CATEGORIES.forEach(cat => {
        const val = nft.traits[cat];
        const freq = traitCounts[cat][val] / count;
        const traitScore = 1 / freq;
        score += traitScore;
        if (traitScore > rarestTrait.rarity) {
          rarestTrait = { category: cat, value: val, rarity: traitScore };
        }
      });
      nft.rarityScore = Math.round(score * 100) / 100;
      nft.rarestTrait = rarestTrait;
    });

    // Sort by rarity and assign ranks
    nfts.sort((a, b) => b.rarityScore - a.rarityScore);
    nfts.forEach((nft, i) => { nft.rank = i + 1; });

    // Adjust prices based on rarity (rarer = more expensive)
    nfts.forEach(nft => {
      const rarityMultiplier = 1 + (nft.rarityScore / nfts[0].rarityScore) * 15;
      nft.price = Math.round(nft.price * rarityMultiplier * 10) / 10;
    });

    return { nfts, traitCounts };
  }

  /* ---------- State ---------- */
  const COLLECTION_SIZE = 200;
  const { nfts: allNFTs, traitCounts } = generateNFTCollection(COLLECTION_SIZE);
  let filteredNFTs = [...allNFTs];
  let traitChart = null;
  let scatterChart = null;

  /* Generate placeholder image colors based on traits */
  function nftColor(nft) {
    const hue = (nft.id * 137.508) % 360;
    const sat = 40 + (nft.rarityScore % 30);
    const light = 25 + (nft.id % 20);
    return `hsl(${hue}, ${sat}%, ${light}%)`;
  }

  function nftHeight(nft) {
    return 180 + (nft.id * 7) % 120;
  }

  /* ============================================================
     GSAP ANIMATION SYSTEM
     ============================================================ */

  function animateHeroEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.hero__inner > *', { opacity: 1 });
      return;
    }
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    tl.from('.hero__label', { opacity: 0, scale: 0.9, duration: 0.5 })
      .from('.hero__title', { opacity: 0, scale: 0.9, duration: 0.7 }, '-=0.3')
      .from('.hero__subtitle', { opacity: 0, scale: 0.9, duration: 0.4 }, '-=0.3')
      .from('.hero__stat', { opacity: 0, scale: 0.9, duration: 0.5, stagger: 0.1 }, '-=0.2');
  }

  function animateCardEntrance() {
    if (prefersReducedMotion) {
      gsap.set('[data-animate]', { opacity: 1, scale: 1 });
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
        scale: 1,
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
    const stored = localStorage.getItem('nft-rarity-theme');
    if (stored === 'light') document.documentElement.setAttribute('data-theme', 'light');

    btn.addEventListener('click', () => {
      const isLight = document.documentElement.getAttribute('data-theme') === 'light';
      if (isLight) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('nft-rarity-theme', 'dark');
      } else {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('nft-rarity-theme', 'light');
      }
      renderCharts();
    });
  }

  /* ============================================================
     HERO STATS
     ============================================================ */

  function renderHeroStats() {
    const uniqueTraits = TRAIT_CATEGORIES.reduce((sum, cat) => sum + TRAIT_VALUES[cat].length, 0);
    const floorPrice = Math.min(...allNFTs.map(n => n.price));

    document.getElementById('hero-total').textContent = COLLECTION_SIZE.toLocaleString();
    document.getElementById('hero-traits').textContent = uniqueTraits;
    document.getElementById('hero-floor').textContent = `${floorPrice.toFixed(1)} ETH`;

    if (CONFIG.heroImageUrl) {
      document.getElementById('hero-bg').style.backgroundImage = `url(${CONFIG.heroImageUrl})`;
    }
  }

  /* ============================================================
     FILTER SYSTEM
     ============================================================ */

  function initFilters() {
    const catSelect = document.getElementById('trait-category');
    const valSelect = document.getElementById('trait-value');
    const sortSelect = document.getElementById('sort-by');

    TRAIT_CATEGORIES.forEach(cat => {
      const opt = document.createElement('option');
      opt.value = cat;
      opt.textContent = cat;
      catSelect.appendChild(opt);
    });

    catSelect.addEventListener('change', () => {
      const cat = catSelect.value;
      valSelect.innerHTML = '<option value="all">All Values</option>';
      if (cat !== 'all') {
        TRAIT_VALUES[cat].forEach(v => {
          const opt = document.createElement('option');
          opt.value = v;
          opt.textContent = v;
          valSelect.appendChild(opt);
        });
      }
      applyFilters();
    });

    valSelect.addEventListener('change', applyFilters);
    sortSelect.addEventListener('change', applyFilters);
  }

  function applyFilters() {
    const cat = document.getElementById('trait-category').value;
    const val = document.getElementById('trait-value').value;
    const sort = document.getElementById('sort-by').value;

    filteredNFTs = allNFTs.filter(nft => {
      if (cat === 'all') return true;
      if (val === 'all') return true;
      return nft.traits[cat] === val;
    });

    switch (sort) {
      case 'rarity-desc': filteredNFTs.sort((a, b) => b.rarityScore - a.rarityScore); break;
      case 'rarity-asc': filteredNFTs.sort((a, b) => a.rarityScore - b.rarityScore); break;
      case 'price-desc': filteredNFTs.sort((a, b) => b.price - a.price); break;
      case 'price-asc': filteredNFTs.sort((a, b) => a.price - b.price); break;
      case 'id-asc': filteredNFTs.sort((a, b) => a.id - b.id); break;
    }

    renderGallery();
    renderRankingTable();
  }

  /* ============================================================
     RENDER GALLERY — Masonry
     ============================================================ */

  function renderGallery() {
    const gallery = document.getElementById('nft-gallery');
    const displayNFTs = filteredNFTs.slice(0, 40);

    gallery.innerHTML = displayNFTs.map(nft => {
      const bgColor = nftColor(nft);
      const h = nftHeight(nft);
      const rankClass = nft.rank <= 10 ? 'nft-card__rank-badge--gold' : '';

      return `
        <div class="nft-card">
          <div class="nft-card__image" style="height:${h}px;background:${bgColor};display:flex;align-items:center;justify-content:center;">
            <span style="font-family:var(--font-display);font-size:var(--text-2xl);color:rgba(255,255,255,0.3);font-style:italic;">#${nft.id}</span>
          </div>
          <div class="nft-card__body">
            <div class="nft-card__name">${nft.name}</div>
            <div class="nft-card__meta">
              <span class="nft-card__rank-badge ${rankClass}">#${nft.rank}</span>
              <span class="nft-card__rarity">${nft.rarityScore.toFixed(1)}</span>
              <span class="nft-card__price">${nft.price.toFixed(1)} ETH</span>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  /* ============================================================
     RENDER RANKING TABLE
     ============================================================ */

  function renderRankingTable() {
    const tbody = document.getElementById('rarity-table-body');
    const top20 = filteredNFTs.slice(0, 20);

    tbody.innerHTML = top20.map(nft => `
      <tr>
        <td class="${nft.rank <= 3 ? 'cell-gold' : ''}">#${nft.rank}</td>
        <td>${nft.name}</td>
        <td class="cell-accent">${nft.rarityScore.toFixed(2)}</td>
        <td>${nft.rarestTrait.category}: ${nft.rarestTrait.value}</td>
        <td>${nft.price.toFixed(1)} ETH</td>
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
      fourth: style.getPropertyValue('--chart-4').trim(),
      fifth: style.getPropertyValue('--chart-5').trim(),
      sixth: style.getPropertyValue('--chart-6').trim(),
      text: style.getPropertyValue('--color-text-secondary').trim(),
      border: style.getPropertyValue('--color-border').trim(),
      bg: style.getPropertyValue('--color-surface').trim(),
    };
  }

  function renderCharts() {
    renderTraitChart();
    renderScatterChart();
  }

  function renderTraitChart() {
    const ctx = document.getElementById('trait-chart').getContext('2d');
    const colors = getChartColors();
    const colorArr = [colors.accent, colors.secondary, colors.tertiary, colors.fourth, colors.fifth, colors.sixth];

    // Show distribution for "Body" trait as default
    const category = 'Body';
    const labels = Object.keys(traitCounts[category]);
    const data = labels.map(l => traitCounts[category][l]);

    if (traitChart) traitChart.destroy();

    traitChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: `${category} Trait Count`,
          data,
          backgroundColor: labels.map((_, i) => colorArr[i % colorArr.length] + '80'),
          borderColor: labels.map((_, i) => colorArr[i % colorArr.length]),
          borderWidth: 1,
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: colors.bg,
            titleColor: colors.text,
            bodyColor: colors.text,
            borderColor: colors.border,
            borderWidth: 1,
          },
        },
        scales: {
          x: {
            ticks: { color: colors.text, font: { family: "'Space Mono', monospace", size: 10 } },
            grid: { color: colors.border },
          },
          y: {
            ticks: { color: colors.text, font: { family: "'Space Mono', monospace", size: 10 } },
            grid: { display: false },
          },
        },
      },
    });
  }

  function renderScatterChart() {
    const ctx = document.getElementById('scatter-chart').getContext('2d');
    const colors = getChartColors();

    const scatterData = allNFTs.map(nft => ({
      x: nft.rarityScore,
      y: nft.price,
    }));

    if (scatterChart) scatterChart.destroy();

    scatterChart = new Chart(ctx, {
      type: 'scatter',
      data: {
        datasets: [{
          label: 'NFTs',
          data: scatterData,
          backgroundColor: colors.accent + '50',
          borderColor: colors.accent,
          borderWidth: 1,
          pointRadius: 3,
          pointHoverRadius: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: colors.bg,
            titleColor: colors.text,
            bodyColor: colors.text,
            borderColor: colors.border,
            borderWidth: 1,
            callbacks: {
              label: (ctx) => `Score: ${ctx.parsed.x.toFixed(1)} | Price: ${ctx.parsed.y.toFixed(1)} ETH`,
            },
          },
        },
        scales: {
          x: {
            title: { display: true, text: 'Rarity Score', color: colors.text, font: { family: "'Space Mono', monospace", size: 11 } },
            ticks: { color: colors.text, font: { family: "'Space Mono', monospace", size: 10 } },
            grid: { color: colors.border },
          },
          y: {
            title: { display: true, text: 'Price (ETH)', color: colors.text, font: { family: "'Space Mono', monospace", size: 11 } },
            ticks: { color: colors.text, font: { family: "'Space Mono', monospace", size: 10 } },
            grid: { color: colors.border },
          },
        },
      },
    });
  }

  /* ============================================================
     BOOTSTRAP
     ============================================================ */

  function init() {
    initThemeToggle();
    renderHeroStats();
    initFilters();
    renderGallery();
    renderRankingTable();
    renderCharts();
    animateHeroEntrance();
    animateCardEntrance();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
