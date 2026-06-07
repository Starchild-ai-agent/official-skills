/* ============================================
 * Web3 Builder Dashboard — E1
 * APIs: GitHub + CoinGecko + simulated on-chain
 * ============================================ */

(function () {
  'use strict';

  /* ---------- Theme Toggle ---------- */
  const themeToggle = document.getElementById('themeToggle');
  const root = document.documentElement;

  function setTheme(t) {
    root.setAttribute('data-theme', t);
    localStorage.setItem('web3b-theme', t);
  }

  themeToggle.addEventListener('click', () => {
    setTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  });

  const saved = localStorage.getItem('web3b-theme');
  if (saved) setTheme(saved);

  /* ---------- Config ---------- */
  const GITHUB_USER = '{{GITHUB_USERNAME}}';
  const WALLET = '{{WALLET_ADDRESS}}';

  /* ---------- Simulated On-chain Data ---------- */
  function generateOnchainData() {
    const seed = WALLET.length || 42;
    const rng = (n) => ((seed * 9301 + 49297) % 233280) / 233280 * n;
    return {
      transactions: Math.floor(rng(2000) + 150),
      protocols: Math.floor(rng(30) + 5),
      gasSpent: (rng(5) + 0.3).toFixed(2),
      firstTxn: '2022-' + String(Math.floor(rng(12) + 1)).padStart(2, '0') + '-15',
      nftsHeld: Math.floor(rng(50) + 3),
      defiTvl: (rng(50000) + 1000).toFixed(0)
    };
  }

  /* ---------- Simulated Ecosystem Opportunities ---------- */
  const ecosystemData = [
    { name: 'Uniswap Labs', desc: 'Smart contract engineer — Solidity/TypeScript', match: '92%', icon: 'U' },
    { name: 'Aave Protocol', desc: 'Frontend developer — React/Web3.js', match: '87%', icon: 'A' },
    { name: 'Chainlink', desc: 'Oracle integration engineer', match: '84%', icon: 'C' },
    { name: 'Optimism', desc: 'L2 infrastructure developer', match: '79%', icon: 'O' },
    { name: 'Lido Finance', desc: 'Staking protocol contributor', match: '75%', icon: 'L' }
  ];

  /* ---------- Fetch GitHub Data ---------- */
  async function fetchGitHub() {
    try {
      const res = await fetch(`https://api.github.com/users/${GITHUB_USER}`);
      if (!res.ok) throw new Error('GitHub API error');
      const user = await res.json();

      const reposRes = await fetch(`https://api.github.com/users/${GITHUB_USER}/repos?per_page=100&sort=updated`);
      const repos = await reposRes.json();

      // Avatar
      const avatar = document.getElementById('heroAvatar');
      const fallback = document.getElementById('avatarFallback');
      if (user.avatar_url) {
        avatar.src = user.avatar_url;
        avatar.style.display = 'block';
        fallback.style.display = 'none';
      }

      // Stats
      document.getElementById('heroRepos').textContent = user.public_repos || repos.length;

      // Language distribution
      const langCount = {};
      repos.forEach(r => {
        if (r.language) {
          langCount[r.language] = (langCount[r.language] || 0) + 1;
        }
      });

      renderTechChart(langCount);
      return { user, repos, langCount };
    } catch (e) {
      console.warn('GitHub fetch failed, using mock data:', e.message);
      const mockLangs = { JavaScript: 12, TypeScript: 8, Solidity: 5, Rust: 3, Python: 4 };
      document.getElementById('heroRepos').textContent = '32';
      renderTechChart(mockLangs);
      return { langCount: mockLangs };
    }
  }

  /* ---------- Fetch Prices ---------- */
  async function fetchPrices() {
    try {
      const res = await fetch('https://pro-api.coingecko.com/api/v3/simple/price?ids=ethereum,solana,chainlink,uniswap,aave&vs_currencies=usd&include_24hr_change=true');
      if (!res.ok) throw new Error('CoinGecko error');
      const data = await res.json();
      renderPrices(data);
    } catch (e) {
      console.warn('Price fetch failed, using mock:', e.message);
      renderPrices({
        ethereum: { usd: 3450.12, usd_24h_change: 2.34 },
        solana: { usd: 178.56, usd_24h_change: -1.22 },
        chainlink: { usd: 18.90, usd_24h_change: 5.67 },
        uniswap: { usd: 12.45, usd_24h_change: 0.89 },
        aave: { usd: 98.30, usd_24h_change: -0.45 }
      });
    }
  }

  /* ---------- Render Tech Chart (Doughnut) ---------- */
  function renderTechChart(langCount) {
    const labels = Object.keys(langCount).slice(0, 8);
    const values = labels.map(l => langCount[l]);
    const colors = ['#10b981', '#34d399', '#6ee7b7', '#a7f3d0', '#059669', '#047857', '#065f46', '#064e3b'];

    const ctx = document.getElementById('techChart');
    if (!ctx) return;

    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: colors.slice(0, labels.length),
          borderWidth: 0,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        cutout: '65%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: getComputedStyle(document.body).getPropertyValue('--text-secondary').trim() || '#a1a1aa',
              font: { family: "'Albert Sans', sans-serif", size: 11 },
              padding: 12,
              usePointStyle: true,
              pointStyleWidth: 8
            }
          }
        }
      }
    });
  }

  /* ---------- Render Radar Chart ---------- */
  function renderRadarChart(langCount) {
    const skills = ['Solidity', 'JavaScript', 'Rust', 'DeFi', 'NFT'];
    const langKeys = Object.keys(langCount);
    const values = skills.map(s => {
      if (s === 'DeFi') return Math.min(90, Math.floor(Math.random() * 40 + 50));
      if (s === 'NFT') return Math.min(85, Math.floor(Math.random() * 30 + 40));
      const count = langCount[s] || langCount[s.toLowerCase()] || 0;
      return Math.min(100, count * 10 + Math.floor(Math.random() * 20 + 30));
    });

    const ctx = document.getElementById('radarChart');
    if (!ctx) return;

    const accentColor = getComputedStyle(document.body).getPropertyValue('--accent').trim() || '#10b981';

    new Chart(ctx, {
      type: 'radar',
      data: {
        labels: skills,
        datasets: [{
          label: 'Skill Level',
          data: values,
          backgroundColor: 'rgba(16,185,129,.15)',
          borderColor: accentColor,
          borderWidth: 2,
          pointBackgroundColor: accentColor,
          pointRadius: 4,
          pointHoverRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        scales: {
          r: {
            beginAtZero: true,
            max: 100,
            ticks: {
              display: false,
              stepSize: 20
            },
            grid: {
              color: 'rgba(161,161,170,.15)'
            },
            angleLines: {
              color: 'rgba(161,161,170,.15)'
            },
            pointLabels: {
              color: getComputedStyle(document.body).getPropertyValue('--text-secondary').trim() || '#a1a1aa',
              font: { family: "'JetBrains Mono', monospace", size: 11 }
            }
          }
        },
        plugins: {
          legend: { display: false }
        }
      }
    });
  }

  /* ---------- Render On-chain ---------- */
  function renderOnchain(data) {
    document.getElementById('ocTxns').textContent = data.transactions.toLocaleString();
    document.getElementById('ocProtocols').textContent = data.protocols;
    document.getElementById('ocGas').textContent = data.gasSpent + ' ETH';
    document.getElementById('ocFirst').textContent = data.firstTxn;
    document.getElementById('ocNfts').textContent = data.nftsHeld;
    document.getElementById('ocTvl').textContent = '$' + Number(data.defiTvl).toLocaleString();

    document.getElementById('heroTxns').textContent = data.transactions.toLocaleString();
    document.getElementById('heroProtocols').textContent = data.protocols;
  }

  /* ---------- Render Ecosystem ---------- */
  function renderEcosystem() {
    const list = document.getElementById('ecoList');
    ecosystemData.forEach(item => {
      const el = document.createElement('div');
      el.className = 'eco-item';
      el.innerHTML = `
        <div class="eco-icon">${item.icon}</div>
        <div class="eco-info">
          <div class="eco-name">${item.name}</div>
          <div class="eco-desc">${item.desc}</div>
        </div>
        <span class="eco-match">${item.match}</span>
      `;
      list.appendChild(el);
    });
  }

  /* ---------- Render Prices ---------- */
  function renderPrices(data) {
    const list = document.getElementById('priceList');
    const names = { ethereum: 'ETH', solana: 'SOL', chainlink: 'LINK', uniswap: 'UNI', aave: 'AAVE' };

    Object.entries(data).forEach(([key, val]) => {
      const row = document.createElement('div');
      row.className = 'price-row';
      const change = val.usd_24h_change || 0;
      const dir = change >= 0 ? 'up' : 'down';
      row.innerHTML = `
        <span class="price-name">${names[key] || key}</span>
        <span class="price-value">$${val.usd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        <span class="price-change ${dir}">${change >= 0 ? '+' : ''}${change.toFixed(2)}%</span>
      `;
      list.appendChild(row);
    });
  }

  /* ---------- Compute Builder Score ---------- */
  function computeScore(onchain, repoCount) {
    const ghScore = Math.min(50, (repoCount || 20) * 1.5);
    const chainScore = Math.min(50, onchain.transactions * 0.02 + onchain.protocols * 1.5);
    return Math.round(ghScore + chainScore);
  }

  /* ---------- GSAP Animations ---------- */
  gsap.registerPlugin(ScrollTrigger);

  const mm = gsap.matchMedia();
  mm.add('(prefers-reduced-motion: no-preference)', () => {
    // D1: translateY(40px)
    gsap.from('.hero-asymmetric .hero-left', {
      y: 40,
      opacity: 0,
      duration: 0.7,
      ease: 'power2.out'
    });

    gsap.from('.hero-asymmetric .hero-right', {
      y: 40,
      opacity: 0,
      duration: 0.7,
      delay: 0.15,
      ease: 'power2.out'
    });

    gsap.from('.builder-card', {
      y: 40,
      opacity: 0,
      duration: 0.5,
      stagger: 0.1,
      ease: 'power2.out',
      scrollTrigger: {
        trigger: '.bento-grid',
        start: 'top 85%'
      }
    });
  });

  /* ---------- Init ---------- */
  async function init() {
    const onchain = generateOnchainData();
    renderOnchain(onchain);
    renderEcosystem();

    const gh = await fetchGitHub();
    const repoCount = parseInt(document.getElementById('heroRepos').textContent) || 20;

    const score = computeScore(onchain, repoCount);
    document.getElementById('heroScore').textContent = score;

    renderRadarChart(gh.langCount || {});
    fetchPrices();
  }

  init();

})();
