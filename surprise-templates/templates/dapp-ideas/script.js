/* ============================================================
   DApp Idea Generator — script.js

   Skeleton: A11 Centered
   Hover: C1 translateY(-3px)
   Entrance: D5 opacity
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Ideas Pool ---------- */
  var IDEAS = [
    { title: 'Decentralized Freelance Marketplace', desc: 'A peer-to-peer freelance platform where payments are held in smart contract escrow. Reputation is on-chain and portable across platforms.', chain: 'ethereum', category: 'social', difficulty: 'hard', stack: ['Solidity', 'React', 'The Graph', 'IPFS'] },
    { title: 'NFT-Gated Community Hub', desc: 'A community platform where access to channels, events, and content is gated by NFT ownership. Token-based governance for community decisions.', chain: 'ethereum', category: 'nft', difficulty: 'medium', stack: ['Solidity', 'Next.js', 'IPFS', 'Lens Protocol'] },
    { title: 'On-Chain Voting DAO', desc: 'A governance framework where proposals, voting, and treasury management are fully on-chain with quadratic voting support.', chain: 'ethereum', category: 'dao', difficulty: 'medium', stack: ['Solidity', 'OpenZeppelin Governor', 'React'] },
    { title: 'Yield Aggregator Dashboard', desc: 'Automatically find and allocate funds to the highest-yielding DeFi protocols across multiple chains with risk scoring.', chain: 'polygon', category: 'defi', difficulty: 'hard', stack: ['Solidity', 'Chainlink', 'React', 'Ethers.js'] },
    { title: 'Play-to-Earn RPG', desc: 'A blockchain RPG where characters, items, and land are NFTs. Players earn tokens through quests and PvP battles.', chain: 'solana', category: 'gaming', difficulty: 'hard', stack: ['Anchor', 'Unity', 'Metaplex', 'React'] },
    { title: 'Decentralized Identity Verifier', desc: 'A self-sovereign identity system where users control their credentials. Verifiable credentials stored on-chain with zero-knowledge proofs.', chain: 'polygon', category: 'social', difficulty: 'hard', stack: ['Solidity', 'ZK-SNARKs', 'React', 'Ceramic'] },
    { title: 'NFT Rental Protocol', desc: 'Rent NFTs for gaming, metaverse access, or DeFi collateral without transferring ownership. Time-locked smart contracts handle returns.', chain: 'ethereum', category: 'nft', difficulty: 'medium', stack: ['Solidity', 'ERC-4907', 'React', 'The Graph'] },
    { title: 'Micro-Lending Pool', desc: 'A peer-to-peer micro-lending platform for underbanked communities. Credit scoring based on on-chain activity and social vouching.', chain: 'polygon', category: 'defi', difficulty: 'medium', stack: ['Solidity', 'Chainlink', 'React', 'Aave'] },
    { title: 'Decentralized Prediction Market', desc: 'Create and trade on prediction markets for any event. Oracle-resolved outcomes with automated market makers.', chain: 'arbitrum', category: 'defi', difficulty: 'hard', stack: ['Solidity', 'UMA Oracle', 'React', 'The Graph'] },
    { title: 'On-Chain Music Streaming', desc: 'Artists upload music as NFTs, fans stream and tip directly. Revenue splits handled by smart contracts with no intermediaries.', chain: 'solana', category: 'nft', difficulty: 'medium', stack: ['Anchor', 'Arweave', 'React', 'Web Audio API'] },
    { title: 'DAO Treasury Manager', desc: 'A multi-sig treasury management tool with budgeting, recurring payments, and investment strategies for DAOs.', chain: 'ethereum', category: 'dao', difficulty: 'medium', stack: ['Solidity', 'Safe SDK', 'React', 'The Graph'] },
    { title: 'Blockchain Trivia Game', desc: 'A real-time multiplayer trivia game where players stake tokens to compete. Winners split the pot. Questions sourced from community.', chain: 'solana', category: 'gaming', difficulty: 'easy', stack: ['Anchor', 'React', 'WebSocket', 'Metaplex'] },
  ];

  var savedIdeas = [];

  /* ---------- Theme ---------- */
  var themeToggle = document.getElementById('theme-toggle');
  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('dapp-theme', theme);
  }
  themeToggle.addEventListener('click', function () {
    var current = document.documentElement.getAttribute('data-theme') || 'light';
    setTheme(current === 'light' ? 'dark' : 'light');
  });
  var savedTheme = localStorage.getItem('dapp-theme') ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  setTheme(savedTheme);

  /* ---------- Generate ---------- */
  document.getElementById('generate-btn').addEventListener('click', generateIdea);

  function generateIdea() {
    var chain = document.getElementById('chain-select').value;
    var category = document.getElementById('category-select').value;

    var filtered = IDEAS.filter(function (idea) {
      if (chain !== 'all' && idea.chain !== chain) return false;
      if (category !== 'all' && idea.category !== category) return false;
      return true;
    });

    if (filtered.length === 0) filtered = IDEAS;
    var idea = filtered[Math.floor(Math.random() * filtered.length)];
    renderIdeaCard(idea);

    if (!prefersReducedMotion) {
      gsap.from('.idea-card', { opacity: 0, duration: 0.5, ease: 'power2.out' });
    }
  }

  function renderIdeaCard(idea) {
    var card = document.getElementById('idea-card');
    var diffClass = 'idea-card__badge--difficulty-' + idea.difficulty;

    card.innerHTML =
      '<h3 class="idea-card__title">' + idea.title + '</h3>' +
      '<p class="idea-card__desc">' + idea.desc + '</p>' +
      '<div class="idea-card__meta">' +
      '<span class="idea-card__badge idea-card__badge--chain">' + idea.chain + '</span>' +
      '<span class="idea-card__badge">' + idea.category + '</span>' +
      '<span class="idea-card__badge ' + diffClass + '">' + idea.difficulty + '</span>' +
      '</div>' +
      '<div class="idea-card__stack">Stack: ' + idea.stack.join(' \u00b7 ') + '</div>' +
      '<div class="idea-card__actions">' +
      '<button class="idea-card__action idea-card__action--save" id="save-idea" type="button">Save</button>' +
      '<button class="idea-card__action" id="copy-idea" type="button">Copy</button>' +
      '</div>';

    document.getElementById('save-idea').addEventListener('click', function () {
      saveIdea(idea);
    });
    document.getElementById('copy-idea').addEventListener('click', function () {
      var text = idea.title + ' - ' + idea.desc + ' [' + idea.chain + ', ' + idea.stack.join(', ') + ']';
      if (navigator.clipboard) navigator.clipboard.writeText(text);
    });
  }

  /* ---------- Save / Remove ---------- */
  function saveIdea(idea) {
    var exists = savedIdeas.some(function (s) { return s.title === idea.title; });
    if (!exists) {
      savedIdeas.push(idea);
      renderSaved();
    }
  }

  function renderSaved() {
    var list = document.getElementById('saved-list');
    if (savedIdeas.length === 0) {
      list.innerHTML = '<p class="saved-empty">No saved ideas yet</p>';
      return;
    }

    var html = '';
    savedIdeas.forEach(function (idea, i) {
      html += '<div class="saved-item">' +
        '<div class="saved-item__info">' +
        '<div class="saved-item__title">' + idea.title + '</div>' +
        '<div class="saved-item__meta">' + idea.chain + ' \u00b7 ' + idea.category + ' \u00b7 ' + idea.difficulty + '</div>' +
        '</div>' +
        '<button class="saved-item__remove" data-index="' + i + '" type="button" aria-label="Remove">&times;</button>' +
        '</div>';
    });
    list.innerHTML = html;

    list.querySelectorAll('.saved-item__remove').forEach(function (btn) {
      btn.addEventListener('click', function () {
        savedIdeas.splice(parseInt(btn.getAttribute('data-index')), 1);
        renderSaved();
      });
    });

    if (!prefersReducedMotion) {
      gsap.utils.toArray('.saved-item').forEach(function (el, i) {
        gsap.from(el, {
          scrollTrigger: { trigger: el, start: 'top 92%' },
          opacity: 0, duration: 0.4, delay: i * 0.05, ease: 'power2.out',
        });
      });
    }
  }

  /* ---------- GSAP Animations (D5 opacity) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    gsap.from('.hero__title', { opacity: 0, duration: 0.7, ease: 'power3.out' });
    gsap.from('.hero__subtitle', { opacity: 0, duration: 0.6, delay: 0.15, ease: 'power3.out' });
    gsap.from('.hero__controls', { opacity: 0, duration: 0.5, delay: 0.3, ease: 'power2.out' });

    gsap.from('.idea-card', {
      scrollTrigger: { trigger: '.idea-card', start: 'top 85%' },
      opacity: 0, duration: 0.6, ease: 'power2.out',
    });

    gsap.utils.toArray('.section__title').forEach(function (el) {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 88%' },
        opacity: 0, duration: 0.5, ease: 'power3.out',
      });
    });
  }

  /* ---------- Init ---------- */
  renderSaved();
  initAnimations();

})();
