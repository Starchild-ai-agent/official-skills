/* ============================================================
   Airdrop Eligibility Checker — script.js
   Layout: A15 Checklist + H15 Score Hero
   Entrance: D11 rotate(-2deg) → rotate(0)
   APIs: All mock data (airdrop eligibility APIs require auth)
   Animation: GSAP 3 + ScrollTrigger (CDN)
   ============================================================ */
(function () {
  'use strict';
  gsap.registerPlugin(ScrollTrigger);
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';
  const ICON_CHECK = '<svg class="check-item__icon check-item__icon--pass" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>';
  const ICON_X = '<svg class="check-item__icon check-item__icon--fail" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';

  /* ============================================================
     MOCK DATA
     ============================================================ */
  const AIRDROPS = [
    { id: 'layerzero-s2', name: 'LayerZero Season 2', symbol: 'ZRO', status: 'pending', estValue: '$420-$1,200', deadline: '2025-09-30', conditions: [
      { label: 'Bridge 5+ times via LayerZero', met: true, value: '12 txns' },
      { label: 'Use 3+ supported chains', met: true, value: '5 chains' },
      { label: 'Volume > $1,000', met: true, value: '$3,450' },
      { label: 'Hold ZRO tokens', met: false, value: '0 ZRO' },
    ]},
    { id: 'zksync-s2', name: 'zkSync Season 2', symbol: 'ZK', status: 'upcoming', estValue: '$300-$800', deadline: '2025-12-31', conditions: [
      { label: '10+ transactions on zkSync Era', met: true, value: '24 txns' },
      { label: 'Interact with 5+ dApps', met: true, value: '7 dApps' },
      { label: 'Bridge to zkSync Era', met: true, value: '3 bridges' },
      { label: 'Provide liquidity on DEX', met: false, value: 'None' },
      { label: 'Hold position > 90 days', met: true, value: '142 days' },
    ]},
    { id: 'scroll-s1', name: 'Scroll Airdrop', symbol: 'SCR', status: 'confirmed', estValue: '$180-$500', deadline: '2025-08-15', conditions: [
      { label: 'Bridge to Scroll mainnet', met: true, value: '2 bridges' },
      { label: '5+ transactions', met: true, value: '18 txns' },
      { label: 'Interact with 3+ protocols', met: true, value: '5 protocols' },
    ]},
    { id: 'monad', name: 'Monad Testnet', symbol: 'MON', status: 'pending', estValue: '$500-$2,000', deadline: '2026-03-31', conditions: [
      { label: 'Join Monad testnet', met: true, value: 'Active' },
      { label: 'Complete 20+ test txns', met: false, value: '8 txns' },
      { label: 'Participate in community', met: true, value: 'Discord L3' },
      { label: 'Deploy test contract', met: false, value: 'Not done' },
    ]},
    { id: 'berachain', name: 'Berachain', symbol: 'BERA', status: 'pending', estValue: '$600-$1,500', deadline: '2026-06-30', conditions: [
      { label: 'Use Berachain testnet', met: true, value: 'Active' },
      { label: 'Provide liquidity in BEX', met: false, value: 'None' },
      { label: 'Mint Bong Bears NFT', met: false, value: 'Not held' },
      { label: 'Delegate BGT tokens', met: false, value: '0 BGT' },
    ]},
    { id: 'eigenlayer-s2', name: 'EigenLayer S2', symbol: 'EIGEN', status: 'confirmed', estValue: '$250-$700', deadline: '2025-07-31', conditions: [
      { label: 'Restake ETH/LST', met: true, value: '2.5 ETH' },
      { label: 'Hold for 30+ days', met: true, value: '95 days' },
    ]},
    { id: 'starknet-provisions', name: 'Starknet Provisions', symbol: 'STRK', status: 'expired', estValue: '$150-$400', deadline: '2025-03-15', conditions: [
      { label: 'Early Ethereum user', met: true, value: 'Qualified' },
      { label: 'Claim before deadline', met: false, value: 'Missed' },
    ]},
    { id: 'celestia-genesis', name: 'Celestia Genesis', symbol: 'TIA', status: 'expired', estValue: '$800-$2,500', deadline: '2024-10-31', conditions: [
      { label: 'Staked ATOM before snapshot', met: false, value: 'No ATOM' },
    ]},
  ];

  const CLAIMED_HISTORY = [
    { name: 'Arbitrum', symbol: 'ARB', amount: '1,250 ARB', usd: '$1,487', date: 'Mar 2023' },
    { name: 'Optimism S1', symbol: 'OP', amount: '776 OP', usd: '$1,164', date: 'Jun 2022' },
    { name: 'EigenLayer S1', symbol: 'EIGEN', amount: '110 EIGEN', usd: '$385', date: 'May 2024' },
    { name: 'Jito', symbol: 'JTO', amount: '420 JTO', usd: '$1,260', date: 'Dec 2023' },
    { name: 'Jupiter', symbol: 'JUP', amount: '850 JUP', usd: '$680', date: 'Jan 2024' },
  ];

  const RECOMMENDED_ACTIONS = [
    { title: 'Provide liquidity on zkSync DEX', desc: 'Add liquidity to SyncSwap or Mute.io to qualify for zkSync S2 airdrop', impact: '+15 pts' },
    { title: 'Buy & hold ZRO tokens', desc: 'Hold LayerZero tokens to boost eligibility for Season 2 distribution', impact: '+10 pts' },
    { title: 'Deploy contract on Monad testnet', desc: 'Deploy a simple smart contract to complete Monad testnet requirements', impact: '+12 pts' },
    { title: 'Stake in Berachain BEX', desc: 'Provide liquidity in Berachain DEX and delegate BGT for airdrop eligibility', impact: '+20 pts' },
    { title: 'Bridge assets to Scroll', desc: 'Increase Scroll activity by bridging and swapping on native DEXs', impact: '+8 pts' },
  ];

  const GENERAL_CHECKLIST = [
    { label: 'Wallet age > 1 year', met: true, value: '2.3 yrs' },
    { label: 'Total transactions > 100', met: true, value: '347 txns' },
    { label: 'Unique protocols used > 10', met: true, value: '23 protocols' },
    { label: 'Multi-chain activity (3+ chains)', met: true, value: '6 chains' },
    { label: 'NFT holder', met: true, value: '12 NFTs' },
    { label: 'Governance participation', met: false, value: '0 votes' },
    { label: 'Testnet participation', met: true, value: '3 testnets' },
    { label: 'DeFi TVL > $500', met: true, value: '$2,180' },
  ];

  /* ============================================================
     GSAP ANIMATIONS — D11 rotate entrance
     ============================================================ */
  function animateHeroEntrance() {
    if (prefersReducedMotion) { gsap.set('.hero__content > *', { opacity: 1, y: 0 }); return; }
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    tl.from('.hero__status-bar', { opacity: 0, y: 20, duration: 0.6 })
      .from('.hero__eyebrow', { opacity: 0, y: 12, duration: 0.4 }, '-=0.3')
      .from('.hero__title', { opacity: 0, y: 30, duration: 0.7, ease: 'power4.out' }, '-=0.3')
      .from('.hero__score-block', { opacity: 0, scale: 0.9, duration: 0.8 }, '-=0.3');
  }

  function animateCardEntrance() {
    if (prefersReducedMotion) { gsap.set('.check-item-group', { opacity: 1, rotation: 0 }); return; }
    /* D11: rotate(-2deg) → rotate(0) */
    gsap.utils.toArray('.check-item-group').forEach((el, i) => {
      gsap.to(el, {
        opacity: 1,
        rotation: 0,
        duration: 0.7,
        delay: i * 0.1,
        ease: 'power3.out',
        scrollTrigger: { trigger: el, start: 'top 88%', once: true },
      });
    });
  }

  function initHeroParallax() {
    if (prefersReducedMotion) return;
    gsap.to('.hero__crosshatch', {
      yPercent: 15, ease: 'none',
      scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: 1 },
    });
  }

  /* ============================================================
     UTILITIES
     ============================================================ */
  function showSkeleton(id, count, type) {
    const c = document.getElementById(id);
    if (!c) return;
    let h = '';
    for (let i = 0; i < count; i++) {
      if (type === 'airdrop') h += '<div class="airdrop-item"><div class="skeleton" style="width:36px;height:36px;border-radius:50%"></div><div style="flex:1"><div class="skeleton skeleton--text"></div><div class="skeleton" style="width:40%;height:0.7rem"></div></div><div class="skeleton" style="width:60px;height:16px"></div><div class="skeleton" style="width:80px;height:22px;border-radius:4px"></div></div>';
      else if (type === 'check') h += '<div class="check-item"><div class="skeleton" style="width:18px;height:18px;border-radius:50%"></div><div class="skeleton skeleton--text" style="flex:1"></div><div class="skeleton" style="width:50px;height:14px"></div></div>';
      else if (type === 'action') h += '<div class="action-item"><div class="skeleton" style="width:24px;height:24px;border-radius:50%"></div><div style="flex:1"><div class="skeleton skeleton--text"></div><div class="skeleton" style="width:80%;height:0.7rem"></div></div></div>';
      else if (type === 'claimed') h += '<div class="claimed-item"><div class="skeleton" style="width:28px;height:28px;border-radius:50%"></div><div style="flex:1"><div class="skeleton skeleton--text"></div></div><div class="skeleton" style="width:60px;height:16px"></div></div>';
    }
    c.innerHTML = h;
  }

  function showError(id, msg, retryFn) {
    const c = document.getElementById(id);
    if (!c) return;
    c.innerHTML = `<div class="error-state">${ICON_ALERT}<p class="error-state__message">${msg}</p>${retryFn ? '<button class="error-state__retry" data-retry="true">Retry</button>' : ''}</div>`;
    if (retryFn) { const btn = c.querySelector('[data-retry]'); if (btn) btn.addEventListener('click', retryFn); }
  }

  function startClock() {
    const el = document.getElementById('hero-time');
    if (!el) return;
    function tick() { el.textContent = new Date().toLocaleString('en-US', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }); }
    tick(); setInterval(tick, 1000);
  }

  /* ============================================================
     RENDERERS
     ============================================================ */
  function computeScore() {
    const total = GENERAL_CHECKLIST.length;
    const passed = GENERAL_CHECKLIST.filter(c => c.met).length;
    return Math.round((passed / total) * 100);
  }

  function renderHeroScore() {
    const score = computeScore();
    const confirmed = AIRDROPS.filter(a => a.status === 'confirmed').length;
    const pending = AIRDROPS.filter(a => a.status === 'pending' || a.status === 'upcoming').length;
    const expired = AIRDROPS.filter(a => a.status === 'expired').length;

    const scoreEl = document.getElementById('hero-score');
    const confirmedEl = document.getElementById('hero-confirmed');
    const pendingEl = document.getElementById('hero-pending');
    const expiredEl = document.getElementById('hero-expired');

    if (scoreEl) scoreEl.textContent = score;
    if (confirmedEl) confirmedEl.textContent = confirmed.toString();
    if (pendingEl) pendingEl.textContent = pending.toString();
    if (expiredEl) expiredEl.textContent = expired.toString();

    /* Animate score ring */
    const arc = document.getElementById('hero-score-arc');
    if (arc) {
      const circumference = 2 * Math.PI * 52; /* r=52 */
      const offset = circumference - (score / 100) * circumference;
      arc.style.strokeDasharray = circumference;
      arc.style.strokeDashoffset = offset;
    }
  }

  function renderChecklist() {
    const container = document.getElementById('checklist');
    const progressBadge = document.getElementById('checklist-progress');
    if (!container) return;

    showSkeleton('checklist', 6, 'check');
    setTimeout(() => {
      const passed = GENERAL_CHECKLIST.filter(c => c.met).length;
      if (progressBadge) progressBadge.textContent = `${passed}/${GENERAL_CHECKLIST.length}`;

      let html = '';
      GENERAL_CHECKLIST.forEach((c) => {
        const icon = c.met ? ICON_CHECK : ICON_X;
        html += `<div class="check-item">${icon}<span class="check-item__label">${c.label}</span><span class="check-item__value">${c.value}</span></div>`;
      });
      container.innerHTML = html;
      if (!prefersReducedMotion) {
        gsap.from('.check-item', { opacity: 0, y: 12, stagger: 0.05, duration: 0.3, ease: 'power3.out' });
      }
    }, 500);
  }

  function renderAirdropList() {
    const container = document.getElementById('airdrop-list');
    const countBadge = document.getElementById('airdrop-count');
    if (!container) return;

    showSkeleton('airdrop-list', 5, 'airdrop');
    setTimeout(() => {
      if (countBadge) countBadge.textContent = AIRDROPS.length + ' found';
      let html = '';
      AIRDROPS.forEach((a) => {
        const statusClass = `airdrop-item__status--${a.status}`;
        const statusLabel = { confirmed: 'Confirmed', pending: 'Pending', expired: 'Expired', upcoming: 'Upcoming' }[a.status] || a.status;
        html += `<div class="airdrop-item">
          <div class="airdrop-item__logo">${a.symbol.substring(0, 2)}</div>
          <div class="airdrop-item__info">
            <div class="airdrop-item__name">${a.name}</div>
            <div class="airdrop-item__deadline">Deadline: ${a.deadline}</div>
          </div>
          <div class="airdrop-item__value">
            <div class="airdrop-item__est-value">${a.estValue}</div>
            <div class="airdrop-item__est-label">Est. value</div>
          </div>
          <div class="airdrop-item__status ${statusClass}">${statusLabel}</div>
        </div>`;
      });
      container.innerHTML = html;
      if (!prefersReducedMotion) {
        gsap.from('.airdrop-item', { opacity: 0, x: -16, stagger: 0.06, duration: 0.4, ease: 'power3.out' });
      }
    }, 400);
  }

  function renderActions() {
    const container = document.getElementById('actions-list');
    if (!container) return;
    showSkeleton('actions-list', 4, 'action');
    setTimeout(() => {
      let html = '';
      RECOMMENDED_ACTIONS.forEach((a, i) => {
        html += `<div class="action-item">
          <div class="action-item__number">${i + 1}</div>
          <div class="action-item__content">
            <div class="action-item__title">${a.title}</div>
            <div class="action-item__desc">${a.desc}</div>
          </div>
          <div class="action-item__impact">${a.impact}</div>
        </div>`;
      });
      container.innerHTML = html;
      if (!prefersReducedMotion) {
        gsap.from('.action-item', { opacity: 0, y: 16, stagger: 0.08, duration: 0.5, ease: 'power3.out' });
      }
    }, 600);
  }

  function renderClaimed() {
    const container = document.getElementById('claimed-list');
    if (!container) return;
    showSkeleton('claimed-list', 4, 'claimed');
    setTimeout(() => {
      let html = '';
      CLAIMED_HISTORY.forEach((c) => {
        html += `<div class="claimed-item">
          <div class="claimed-item__icon">${c.symbol.substring(0, 2)}</div>
          <div class="claimed-item__info">
            <div class="claimed-item__name">${c.name}</div>
            <div class="claimed-item__date">${c.date}</div>
          </div>
          <div class="claimed-item__amount">${c.amount}</div>
          <div class="claimed-item__usd">${c.usd}</div>
        </div>`;
      });
      container.innerHTML = html;
      if (!prefersReducedMotion) {
        gsap.from('.claimed-item', { opacity: 0, x: 16, stagger: 0.06, duration: 0.4, ease: 'power3.out' });
      }
    }, 700);
  }

  /* ---------- Hero Image Fallback ---------- */
  function setupHeroImage() {
    const url = '{{HERO_IMAGE_URL}}';
    if (url && !url.startsWith('{{')) {
      const bg = document.querySelector('.hero__bg-image');
      if (bg) { bg.style.backgroundImage = `url('${url}')`; bg.style.opacity = '0.15'; }
    }
  }

  /* ---------- Theme Toggle ---------- */
  function initTheme() {
    const stored = localStorage.getItem('airdrop-checker-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = stored || (prefersDark ? 'dark' : 'light');
    if (theme === 'light') document.documentElement.setAttribute('data-theme', 'light');
    else document.documentElement.removeAttribute('data-theme');

    const btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.addEventListener('click', () => {
        const isLight = document.documentElement.getAttribute('data-theme') === 'light';
        if (isLight) { document.documentElement.removeAttribute('data-theme'); localStorage.setItem('airdrop-checker-theme', 'dark'); }
        else { document.documentElement.setAttribute('data-theme', 'light'); localStorage.setItem('airdrop-checker-theme', 'light'); }
      });
    }
  }

  /* ============================================================
     INIT
     ============================================================ */
  function init() {
    initTheme();
    startClock();
    setupHeroImage();
    animateHeroEntrance();
    animateCardEntrance();
    initHeroParallax();
    renderHeroScore();
    renderChecklist();
    renderAirdropList();
    renderActions();
    renderClaimed();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
