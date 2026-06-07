/* ============================================================
   Web3 Glossary — script.js
   D18 · Sidebar + Content · Stagger top-to-bottom · GSAP 3
   ============================================================ */

(function () {
  'use strict';

  /* ---------- 50+ Web3 Terms ---------- */
  const TERMS = [
    { term: 'Airdrop', def: 'Free distribution of tokens to wallet addresses, often used for marketing or rewarding early adopters.', example: 'Uniswap airdropped 400 UNI to every wallet that had used the protocol.', category: 'general', related: ['Token', 'Wallet'] },
    { term: 'AMM', def: 'Automated Market Maker — a decentralized exchange mechanism that uses liquidity pools and mathematical formulas instead of order books.', example: 'x * y = k is the constant product formula used by Uniswap.', category: 'defi', related: ['DEX', 'Liquidity Pool'] },
    { term: 'Blockchain', def: 'A distributed, immutable ledger that records transactions across a network of computers.', example: 'Bitcoin\'s blockchain has been running since January 2009.', category: 'general', related: ['Block', 'Node', 'Consensus'] },
    { term: 'Block', def: 'A batch of transactions bundled together and added to the blockchain.', example: 'Ethereum produces a new block approximately every 12 seconds.', category: 'general', related: ['Blockchain', 'Gas'] },
    { term: 'Bridge', def: 'A protocol that enables transferring assets between different blockchains.', example: 'Use a bridge to move ETH from Ethereum mainnet to Arbitrum.', category: 'layer2', related: ['Layer 2', 'Cross-chain'] },
    { term: 'Burn', def: 'Permanently removing tokens from circulation by sending them to an inaccessible address.', example: 'EIP-1559 burns a portion of ETH gas fees with every transaction.', category: 'general', related: ['Token', 'Deflation'] },
    { term: 'Cold Wallet', def: 'A cryptocurrency wallet that is not connected to the internet, providing enhanced security.', example: 'Ledger Nano X is a popular cold wallet for storing crypto offline.', category: 'wallet', related: ['Hot Wallet', 'Hardware Wallet', 'Seed Phrase'] },
    { term: 'Consensus', def: 'The mechanism by which a blockchain network agrees on the current state of the ledger.', example: 'Ethereum switched from Proof of Work to Proof of Stake consensus.', category: 'consensus', related: ['PoS', 'PoW', 'Validator'] },
    { term: 'Cross-chain', def: 'Technology enabling interaction and asset transfer between different blockchain networks.', example: 'Cosmos IBC protocol enables cross-chain communication.', category: 'layer2', related: ['Bridge', 'Interoperability'] },
    { term: 'DAO', def: 'Decentralized Autonomous Organization — a community-governed entity where decisions are made through token-holder voting.', example: 'MakerDAO governs the DAI stablecoin through MKR token voting.', category: 'defi', related: ['Governance', 'Token'] },
    { term: 'dApp', def: 'Decentralized Application — an application built on a blockchain that operates without central control.', example: 'Uniswap is a dApp for decentralized token trading.', category: 'general', related: ['Smart Contract', 'Web3'] },
    { term: 'DeFi', def: 'Decentralized Finance — financial services built on blockchain without traditional intermediaries like banks.', example: 'Aave and Compound are leading DeFi lending protocols.', category: 'defi', related: ['AMM', 'Yield Farming', 'Liquidity Pool'] },
    { term: 'DEX', def: 'Decentralized Exchange — a platform for trading tokens directly from your wallet without a central authority.', example: 'Uniswap, SushiSwap, and Curve are popular DEXes.', category: 'defi', related: ['AMM', 'Liquidity Pool', 'CEX'] },
    { term: 'EIP', def: 'Ethereum Improvement Proposal — a design document for proposing changes to the Ethereum protocol.', example: 'EIP-1559 introduced a base fee burn mechanism for gas.', category: 'general', related: ['Ethereum', 'Gas'] },
    { term: 'ERC-20', def: 'A token standard on Ethereum that defines a common interface for fungible tokens.', example: 'USDC, LINK, and UNI are all ERC-20 tokens.', category: 'general', related: ['Token', 'ERC-721', 'Smart Contract'] },
    { term: 'ERC-721', def: 'A token standard for non-fungible tokens (NFTs) on Ethereum, where each token is unique.', example: 'CryptoPunks and Bored Apes use the ERC-721 standard.', category: 'nft', related: ['NFT', 'ERC-20', 'ERC-1155'] },
    { term: 'ERC-1155', def: 'A multi-token standard that supports both fungible and non-fungible tokens in a single contract.', example: 'Gaming items often use ERC-1155 for efficiency.', category: 'nft', related: ['NFT', 'ERC-721'] },
    { term: 'Flash Loan', def: 'An uncollateralized loan that must be borrowed and repaid within a single transaction block.', example: 'Aave pioneered flash loans for arbitrage and liquidation.', category: 'defi', related: ['DeFi', 'Arbitrage'] },
    { term: 'Floor Price', def: 'The lowest listed price for an NFT in a collection.', example: 'The Bored Ape Yacht Club floor price peaked at over 100 ETH.', category: 'nft', related: ['NFT', 'Marketplace'] },
    { term: 'Fork', def: 'A change to a blockchain\'s protocol. A hard fork creates a new chain; a soft fork is backward-compatible.', example: 'Ethereum Classic is a hard fork of Ethereum after the DAO hack.', category: 'general', related: ['Blockchain', 'Consensus'] },
    { term: 'Gas', def: 'The unit measuring computational effort required to execute operations on Ethereum.', example: 'Complex smart contract calls require more gas than simple transfers.', category: 'general', related: ['Gwei', 'EIP', 'Transaction'] },
    { term: 'Governance', def: 'The process by which protocol changes are proposed and voted on by token holders.', example: 'Compound\'s COMP token grants voting power on protocol upgrades.', category: 'defi', related: ['DAO', 'Token'] },
    { term: 'Gwei', def: 'A denomination of ETH equal to 10⁻⁹ ETH, commonly used to express gas prices.', example: 'Gas prices of 20 gwei are considered low on Ethereum mainnet.', category: 'general', related: ['Gas', 'Wei'] },
    { term: 'Hardware Wallet', def: 'A physical device that stores private keys offline for maximum security.', example: 'Ledger and Trezor are the most popular hardware wallet brands.', category: 'wallet', related: ['Cold Wallet', 'Seed Phrase'] },
    { term: 'Hash', def: 'A fixed-length string produced by a cryptographic function, used to verify data integrity.', example: 'SHA-256 produces a 256-bit hash used in Bitcoin mining.', category: 'general', related: ['Block', 'Mining'] },
    { term: 'Hot Wallet', def: 'A cryptocurrency wallet connected to the internet for convenient access and transactions.', example: 'MetaMask is a popular hot wallet browser extension.', category: 'wallet', related: ['Cold Wallet', 'MetaMask'] },
    { term: 'Impermanent Loss', def: 'The temporary loss of value experienced by liquidity providers when token prices diverge from the ratio at deposit.', example: 'Providing ETH/USDC liquidity during a 2x ETH price move causes ~5.7% IL.', category: 'defi', related: ['Liquidity Pool', 'AMM', 'Yield Farming'] },
    { term: 'Interoperability', def: 'The ability of different blockchain networks to communicate and share data with each other.', example: 'Polkadot\'s parachain architecture enables blockchain interoperability.', category: 'layer2', related: ['Cross-chain', 'Bridge'] },
    { term: 'IPFS', def: 'InterPlanetary File System — a peer-to-peer protocol for storing and sharing data in a distributed file system.', example: 'Many NFT metadata and images are stored on IPFS.', category: 'general', related: ['NFT', 'Decentralization'] },
    { term: 'Layer 1', def: 'The base blockchain network (e.g., Ethereum, Bitcoin, Solana) that processes and finalizes transactions.', example: 'Ethereum is a Layer 1 blockchain; Arbitrum is built on top of it.', category: 'layer2', related: ['Layer 2', 'Blockchain'] },
    { term: 'Layer 2', def: 'A scaling solution built on top of a Layer 1 blockchain to increase throughput and reduce fees.', example: 'Arbitrum and Optimism are Ethereum Layer 2 rollups.', category: 'layer2', related: ['Layer 1', 'Rollup', 'Bridge'] },
    { term: 'Liquidity Pool', def: 'A smart contract holding paired tokens that enables decentralized trading via an AMM.', example: 'The ETH/USDC pool on Uniswap holds billions in liquidity.', category: 'defi', related: ['AMM', 'DEX', 'Impermanent Loss'] },
    { term: 'Mainnet', def: 'The primary, production blockchain network where real transactions occur with real value.', example: 'After testing on Goerli, the contract was deployed to Ethereum mainnet.', category: 'general', related: ['Testnet', 'Blockchain'] },
    { term: 'MEV', def: 'Maximal Extractable Value — profit that block producers can extract by reordering, inserting, or censoring transactions.', example: 'Sandwich attacks are a common form of MEV extraction on DEXes.', category: 'defi', related: ['Gas', 'DEX', 'Flashbots'] },
    { term: 'MetaMask', def: 'A popular browser extension and mobile wallet for interacting with Ethereum and EVM-compatible chains.', example: 'Connect your MetaMask wallet to use Uniswap or OpenSea.', category: 'wallet', related: ['Hot Wallet', 'dApp'] },
    { term: 'Minting', def: 'The process of creating new tokens or NFTs on a blockchain.', example: 'Minting an NFT writes its metadata permanently to the blockchain.', category: 'nft', related: ['NFT', 'Smart Contract'] },
    { term: 'Multi-sig', def: 'A wallet requiring multiple private key signatures to authorize a transaction, enhancing security.', example: 'Gnosis Safe is a popular multi-sig wallet for DAOs.', category: 'wallet', related: ['Wallet', 'DAO', 'Security'] },
    { term: 'NFT', def: 'Non-Fungible Token — a unique digital asset on a blockchain representing ownership of art, collectibles, or other items.', example: 'Beeple\'s NFT sold for $69 million at Christie\'s auction.', category: 'nft', related: ['ERC-721', 'Minting', 'Floor Price'] },
    { term: 'Node', def: 'A computer that maintains a copy of the blockchain and validates transactions.', example: 'Running a full Ethereum node requires syncing the entire chain history.', category: 'general', related: ['Blockchain', 'Validator'] },
    { term: 'Oracle', def: 'A service that provides external real-world data to smart contracts on the blockchain.', example: 'Chainlink oracles provide price feeds to DeFi protocols.', category: 'defi', related: ['Smart Contract', 'DeFi'] },
    { term: 'Optimistic Rollup', def: 'A Layer 2 scaling solution that assumes transactions are valid and only runs computation in case of disputes.', example: 'Optimism and Arbitrum are leading optimistic rollup implementations.', category: 'layer2', related: ['Layer 2', 'Rollup', 'ZK Rollup'] },
    { term: 'PoS', def: 'Proof of Stake — a consensus mechanism where validators stake tokens as collateral to propose and validate blocks.', example: 'Ethereum transitioned to PoS with The Merge in September 2022.', category: 'consensus', related: ['Consensus', 'Validator', 'Staking'] },
    { term: 'PoW', def: 'Proof of Work — a consensus mechanism where miners solve computational puzzles to validate blocks.', example: 'Bitcoin uses PoW consensus, requiring significant energy.', category: 'consensus', related: ['Consensus', 'Mining', 'Hash'] },
    { term: 'Private Key', def: 'A secret cryptographic key that proves ownership and authorizes transactions from a wallet.', example: 'Never share your private key — anyone with it controls your funds.', category: 'wallet', related: ['Wallet', 'Seed Phrase', 'Public Key'] },
    { term: 'Rollup', def: 'A Layer 2 scaling technique that bundles multiple transactions into a single proof submitted to Layer 1.', example: 'Rollups can reduce gas costs by 10-100x compared to L1.', category: 'layer2', related: ['Layer 2', 'Optimistic Rollup', 'ZK Rollup'] },
    { term: 'Seed Phrase', def: 'A 12 or 24-word mnemonic that can recover a cryptocurrency wallet and all its accounts.', example: 'Write your seed phrase on paper and store it in a safe place.', category: 'wallet', related: ['Private Key', 'Wallet'] },
    { term: 'Slashing', def: 'A penalty mechanism in PoS where validators lose staked tokens for malicious behavior or downtime.', example: 'Ethereum validators can be slashed for double-signing blocks.', category: 'consensus', related: ['PoS', 'Validator', 'Staking'] },
    { term: 'Smart Contract', def: 'Self-executing code deployed on a blockchain that automatically enforces the terms of an agreement.', example: 'Solidity is the primary language for writing Ethereum smart contracts.', category: 'general', related: ['dApp', 'ERC-20', 'Solidity'] },
    { term: 'Stablecoin', def: 'A cryptocurrency designed to maintain a stable value, typically pegged to a fiat currency like USD.', example: 'USDC and DAI are popular stablecoins pegged to the US dollar.', category: 'defi', related: ['DeFi', 'Token'] },
    { term: 'Staking', def: 'Locking up tokens to support network operations (validation) in exchange for rewards.', example: 'Staking 32 ETH is required to run an Ethereum validator node.', category: 'consensus', related: ['PoS', 'Validator', 'Yield'] },
    { term: 'Testnet', def: 'A blockchain network used for testing where tokens have no real value.', example: 'Developers test smart contracts on Sepolia before deploying to mainnet.', category: 'general', related: ['Mainnet', 'Smart Contract'] },
    { term: 'Token', def: 'A digital asset created on an existing blockchain, representing utility, governance, or value.', example: 'UNI is a governance token for the Uniswap protocol.', category: 'general', related: ['ERC-20', 'Governance'] },
    { term: 'TVL', def: 'Total Value Locked — the total amount of assets deposited in a DeFi protocol.', example: 'Aave\'s TVL exceeded $10 billion at its peak.', category: 'defi', related: ['DeFi', 'Liquidity Pool'] },
    { term: 'Validator', def: 'A node operator in a PoS network that proposes and attests to new blocks.', example: 'Over 900,000 validators secure the Ethereum network.', category: 'consensus', related: ['PoS', 'Staking', 'Node'] },
    { term: 'Wallet', def: 'Software or hardware that stores private keys and enables users to manage their crypto assets.', example: 'MetaMask, Phantom, and Ledger are popular crypto wallets.', category: 'wallet', related: ['Private Key', 'Hot Wallet', 'Cold Wallet'] },
    { term: 'Web3', def: 'The vision of a decentralized internet built on blockchain technology, giving users ownership of their data and assets.', example: 'Web3 applications let users sign in with their wallet instead of email.', category: 'general', related: ['dApp', 'Blockchain', 'Decentralization'] },
    { term: 'Wei', def: 'The smallest denomination of ETH, equal to 10⁻¹⁸ ETH.', example: '1 ETH = 1,000,000,000,000,000,000 wei.', category: 'general', related: ['Gwei', 'Gas'] },
    { term: 'Whale', def: 'An individual or entity holding a very large amount of cryptocurrency.', example: 'Whale wallets moving large amounts of BTC can signal market shifts.', category: 'general', related: ['Token', 'Market'] },
    { term: 'Yield Farming', def: 'The practice of moving assets between DeFi protocols to maximize returns.', example: 'Yield farmers often chase the highest APY across lending protocols.', category: 'defi', related: ['DeFi', 'Liquidity Pool', 'APY'] },
    { term: 'ZK Rollup', def: 'A Layer 2 scaling solution that uses zero-knowledge proofs to validate transactions off-chain.', example: 'zkSync and StarkNet are leading ZK rollup implementations.', category: 'layer2', related: ['Layer 2', 'Rollup', 'Zero-Knowledge Proof'] },
    { term: 'Zero-Knowledge Proof', def: 'A cryptographic method that proves a statement is true without revealing the underlying data.', example: 'ZK proofs enable private transactions while maintaining verifiability.', category: 'general', related: ['ZK Rollup', 'Privacy'] }
  ];

  /* ---------- Theme Toggle ---------- */
  const html = document.documentElement;
  const themeBtn = document.getElementById('themeToggle');
  const stored = localStorage.getItem('glossary-theme');
  if (stored) html.setAttribute('data-theme', stored);

  themeBtn.addEventListener('click', () => {
    const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('glossary-theme', next);
  });

  /* ---------- State ---------- */
  let activeCategory = 'all';
  let searchQuery = '';
  let highlightedTerm = null;

  /* ---------- Build Alpha Nav ---------- */
  const alphaNav = document.getElementById('alphaNav');
  const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
  const usedLetters = new Set(TERMS.map(t => t.term[0].toUpperCase()));

  letters.forEach(letter => {
    const btn = document.createElement('button');
    btn.className = 'sidebar__letter' + (usedLetters.has(letter) ? '' : ' sidebar__letter--disabled');
    btn.textContent = letter;
    btn.dataset.letter = letter;
    if (usedLetters.has(letter)) {
      btn.addEventListener('click', () => scrollToLetter(letter));
    }
    alphaNav.appendChild(btn);
  });

  function scrollToLetter(letter) {
    const el = document.getElementById('letter-' + letter);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      // Highlight active letter
      alphaNav.querySelectorAll('.sidebar__letter').forEach(b => b.classList.remove('sidebar__letter--active'));
      const btn = alphaNav.querySelector(`[data-letter="${letter}"]`);
      if (btn) btn.classList.add('sidebar__letter--active');
    }
  }

  /* ---------- Category Tags ---------- */
  const categoryTags = document.getElementById('categoryTags');
  categoryTags.addEventListener('click', (e) => {
    const tag = e.target.closest('.tag');
    if (!tag) return;
    activeCategory = tag.dataset.cat;
    categoryTags.querySelectorAll('.tag').forEach(t => t.classList.remove('tag--active'));
    tag.classList.add('tag--active');
    renderTerms();
  });

  /* ---------- Search ---------- */
  const searchInput = document.getElementById('searchInput');
  searchInput.addEventListener('input', (e) => {
    searchQuery = e.target.value.trim().toLowerCase();
    renderTerms();
  });

  /* ---------- Random Term ---------- */
  const randomBtn = document.getElementById('randomBtn');
  randomBtn.addEventListener('click', () => {
    const idx = Math.floor(Math.random() * TERMS.length);
    const term = TERMS[idx];
    highlightedTerm = term.term;
    searchQuery = '';
    searchInput.value = '';
    activeCategory = 'all';
    categoryTags.querySelectorAll('.tag').forEach(t => t.classList.remove('tag--active'));
    categoryTags.querySelector('[data-cat="all"]').classList.add('tag--active');
    renderTerms();

    // Scroll to highlighted term
    setTimeout(() => {
      const el = document.querySelector('.term-card--highlight');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);
  });

  /* ---------- Render Terms ---------- */
  const termsList = document.getElementById('termsList');
  const termsEmpty = document.getElementById('termsEmpty');

  function filterTerms() {
    return TERMS.filter(t => {
      const matchCat = activeCategory === 'all' || t.category === activeCategory;
      const matchSearch = !searchQuery ||
        t.term.toLowerCase().includes(searchQuery) ||
        t.def.toLowerCase().includes(searchQuery) ||
        t.category.toLowerCase().includes(searchQuery);
      return matchCat && matchSearch;
    });
  }

  function renderTerms() {
    const filtered = filterTerms();

    if (filtered.length === 0) {
      termsList.innerHTML = '';
      termsEmpty.style.display = 'block';
      return;
    }

    termsEmpty.style.display = 'none';

    // Group by first letter
    const groups = {};
    filtered.forEach(t => {
      const letter = t.term[0].toUpperCase();
      if (!groups[letter]) groups[letter] = [];
      groups[letter].push(t);
    });

    const sortedLetters = Object.keys(groups).sort();

    termsList.innerHTML = sortedLetters.map(letter => {
      const cards = groups[letter].map(t => {
        const isHighlighted = highlightedTerm === t.term;
        const relatedHtml = t.related.length > 0
          ? `<div class="term-card__related">
              <span class="term-card__related-label">Related:</span>
              ${t.related.map(r => `<button class="term-card__link" data-search="${r}">${r}</button>`).join('')}
            </div>`
          : '';

        return `<article class="term-card${isHighlighted ? ' term-card--highlight' : ''}" data-term="${t.term}">
          <h3 class="term-card__name">${t.term}<code class="term-card__code">${t.category}</code></h3>
          <p class="term-card__def">${t.def}</p>
          <div class="term-card__example">${t.example}</div>
          ${relatedHtml}
        </article>`;
      }).join('');

      return `<div class="letter-group" id="letter-${letter}">
        <h2 class="letter-group__heading">${letter}</h2>
        ${cards}
      </div>`;
    }).join('');

    // Related term click handlers
    termsList.querySelectorAll('.term-card__link').forEach(link => {
      link.addEventListener('click', () => {
        const search = link.dataset.search;
        searchInput.value = search;
        searchQuery = search.toLowerCase();
        highlightedTerm = null;
        renderTerms();
      });
    });

    // Animate cards (stagger top-to-bottom, D4)
    animateCards();
  }

  /* ---------- GSAP Animations ---------- */
  function initAnimations() {
    if (typeof gsap === 'undefined') return;
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;

    gsap.registerPlugin(ScrollTrigger);

    gsap.from('.hero__heading', { y: -20, opacity: 0, duration: 0.7, ease: 'power2.out' });
    gsap.from('.hero__sub', { y: -20, opacity: 0, duration: 0.7, delay: 0.1, ease: 'power2.out' });
    gsap.from('.hero__search-wrap', { y: -20, opacity: 0, duration: 0.7, delay: 0.2, ease: 'power2.out' });
    gsap.from('.hero__tags', { y: -20, opacity: 0, duration: 0.7, delay: 0.3, ease: 'power2.out' });
  }

  function animateCards() {
    if (typeof gsap === 'undefined') return;
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;

    const cards = termsList.querySelectorAll('.term-card');
    cards.forEach((card, i) => {
      gsap.from(card, {
        y: 20,
        opacity: 0,
        duration: 0.4,
        delay: Math.min(i * 0.04, 1.2),
        ease: 'power2.out',
        scrollTrigger: {
          trigger: card,
          start: 'top 92%',
          toggleActions: 'play none none none'
        }
      });
    });
  }

  /* ---------- Init ---------- */
  function init() {
    initAnimations();
    renderTerms();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
