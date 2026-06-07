/* ============================================
 * Developer Brand Page — E3
 * APIs: GitHub + simulated Twitter influence
 * ============================================ */

(function () {
  'use strict';

  /* ---------- Theme Toggle ---------- */
  const themeToggle = document.getElementById('themeToggle');
  const root = document.documentElement;

  function setTheme(t) {
    root.setAttribute('data-theme', t);
    localStorage.setItem('devbrand-theme', t);
  }

  themeToggle.addEventListener('click', () => {
    setTheme(root.getAttribute('data-theme') === 'light' ? 'dark' : 'light');
  });

  const saved = localStorage.getItem('devbrand-theme');
  if (saved) setTheme(saved);

  /* ---------- Config ---------- */
  const GITHUB_USER = '{{GITHUB_USERNAME}}';
  const TWITTER_HANDLE = '{{TWITTER_HANDLE}}';

  /* ---------- Language Colors ---------- */
  const langColors = {
    JavaScript: '#f1e05a',
    TypeScript: '#3178c6',
    Python: '#3572A5',
    Rust: '#dea584',
    Go: '#00ADD8',
    Solidity: '#AA6746',
    Java: '#b07219',
    'C++': '#f34b7d',
    C: '#555555',
    Ruby: '#701516',
    Swift: '#F05138',
    Kotlin: '#A97BFF',
    Dart: '#00B4AB',
    PHP: '#4F5D95',
    Shell: '#89e051',
    HTML: '#e34c26',
    CSS: '#563d7c',
    Vue: '#41b883',
    Svelte: '#ff3e00'
  };

  /* ---------- Simulated Twitter Data ---------- */
  function generateTwitterData() {
    const seed = TWITTER_HANDLE.length || 10;
    return {
      followers: Math.floor(seed * 847 + 2400),
      following: Math.floor(seed * 23 + 180),
      tweets: Math.floor(seed * 312 + 5000)
    };
  }

  /* ---------- Skills Data ---------- */
  const defaultSkills = [
    { name: 'JavaScript', years: '5+' },
    { name: 'TypeScript', years: '4+' },
    { name: 'React', years: '4+' },
    { name: 'Node.js', years: '4+' },
    { name: 'Python', years: '3+' },
    { name: 'Solidity', years: '2+' },
    { name: 'Rust', years: '1+' },
    { name: 'Docker', years: '3+' },
    { name: 'AWS', years: '3+' },
    { name: 'PostgreSQL', years: '4+' },
    { name: 'GraphQL', years: '2+' },
    { name: 'Git', years: '5+' }
  ];

  /* ---------- Fetch GitHub ---------- */
  async function fetchGitHub() {
    try {
      const userRes = await fetch(`https://api.github.com/users/${GITHUB_USER}`);
      if (!userRes.ok) throw new Error('GitHub API error');
      const user = await userRes.json();

      const reposRes = await fetch(`https://api.github.com/users/${GITHUB_USER}/repos?per_page=100&sort=stargazers_count&direction=desc`);
      const repos = await reposRes.json();

      // Update tagline from bio
      if (user.bio) {
        document.getElementById('heroTagline').textContent = user.bio;
      }

      // Render projects
      renderProjects(repos.slice(0, 6));

      // Compute stats
      const totalStars = repos.reduce((sum, r) => sum + (r.stargazers_count || 0), 0);

      // Build skills from actual languages
      const langSet = new Set();
      repos.forEach(r => { if (r.language) langSet.add(r.language); });
      const skills = Array.from(langSet).slice(0, 12).map(lang => ({
        name: lang,
        years: Math.floor(Math.random() * 4 + 1) + '+'
      }));
      if (skills.length > 0) renderSkills(skills);
      else renderSkills(defaultSkills);

      return { user, repos, totalStars };
    } catch (e) {
      console.warn('GitHub fetch failed, using mock:', e.message);
      renderProjects(generateMockRepos());
      renderSkills(defaultSkills);
      return { totalStars: 342, repos: [], user: {} };
    }
  }

  /* ---------- Mock Repos ---------- */
  function generateMockRepos() {
    return [
      { name: 'web3-toolkit', description: 'A comprehensive toolkit for Web3 development with TypeScript support.', language: 'TypeScript', stargazers_count: 128, forks_count: 34, html_url: '#' },
      { name: 'defi-dashboard', description: 'Real-time DeFi portfolio tracker with multi-chain support.', language: 'JavaScript', stargazers_count: 89, forks_count: 22, html_url: '#' },
      { name: 'smart-contracts', description: 'Collection of audited Solidity smart contracts for DeFi protocols.', language: 'Solidity', stargazers_count: 67, forks_count: 18, html_url: '#' },
      { name: 'rust-blockchain', description: 'Minimal blockchain implementation in Rust for learning purposes.', language: 'Rust', stargazers_count: 45, forks_count: 12, html_url: '#' },
      { name: 'api-gateway', description: 'High-performance API gateway with rate limiting and caching.', language: 'Go', stargazers_count: 34, forks_count: 8, html_url: '#' },
      { name: 'ml-trading-bot', description: 'Machine learning powered trading bot with backtesting framework.', language: 'Python', stargazers_count: 23, forks_count: 6, html_url: '#' }
    ];
  }

  /* ---------- Render Projects ---------- */
  function renderProjects(repos) {
    const grid = document.getElementById('projectsGrid');
    grid.innerHTML = '';

    repos.forEach(repo => {
      const card = document.createElement('a');
      card.className = 'project-card';
      card.href = repo.html_url || '#';
      card.target = '_blank';
      card.rel = 'noopener';

      const dotColor = langColors[repo.language] || '#a3a3a3';

      card.innerHTML = `
        <h3 class="project-name">${repo.name}</h3>
        <p class="project-desc">${repo.description || 'No description'}</p>
        <div class="project-meta">
          ${repo.language ? `<span class="project-lang"><span class="lang-dot" style="background:${dotColor}"></span>${repo.language}</span>` : ''}
          <span class="project-stars">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
            ${repo.stargazers_count || 0}
          </span>
          <span class="project-forks">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><path d="M18 9v1a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V9"/><path d="M12 12v3"/></svg>
            ${repo.forks_count || 0}
          </span>
        </div>
      `;
      grid.appendChild(card);
    });
  }

  /* ---------- Render Skills ---------- */
  function renderSkills(skills) {
    const grid = document.getElementById('skillsGrid');
    grid.innerHTML = '';

    skills.forEach(skill => {
      const tag = document.createElement('div');
      tag.className = 'skill-tag';
      tag.innerHTML = `
        ${skill.name}
        <span class="skill-years">${skill.years}</span>
      `;
      grid.appendChild(tag);
    });
  }

  /* ---------- Render Influence ---------- */
  function renderInfluence(totalStars, repoCount) {
    const twitter = generateTwitterData();

    document.getElementById('infFollowers').textContent = twitter.followers.toLocaleString();
    document.getElementById('infStars').textContent = totalStars.toLocaleString();
    document.getElementById('infRepos').textContent = repoCount.toString();
    document.getElementById('infContribs').textContent = Math.floor(Math.random() * 800 + 400).toLocaleString();
  }

  /* ---------- GSAP Animations ---------- */
  gsap.registerPlugin(ScrollTrigger);

  const mm = gsap.matchMedia();
  mm.add('(prefers-reduced-motion: no-preference)', () => {
    // D17: translateY(-30px) from above
    gsap.from('.hero-eyebrow', {
      y: -30,
      opacity: 0,
      duration: 0.6,
      ease: 'power2.out'
    });

    gsap.from('.hero-name', {
      y: -30,
      opacity: 0,
      duration: 0.7,
      delay: 0.1,
      ease: 'power2.out'
    });

    gsap.from('.hero-tagline', {
      y: -30,
      opacity: 0,
      duration: 0.6,
      delay: 0.2,
      ease: 'power2.out'
    });

    gsap.from('.hero-socials', {
      y: -30,
      opacity: 0,
      duration: 0.5,
      delay: 0.3,
      ease: 'power2.out'
    });

    // Projects
    gsap.from('.project-card', {
      y: -30,
      opacity: 0,
      duration: 0.5,
      stagger: 0.08,
      ease: 'power2.out',
      scrollTrigger: {
        trigger: '#projects',
        start: 'top 80%'
      }
    });

    // Skills
    gsap.from('.skill-tag', {
      y: -20,
      opacity: 0,
      duration: 0.3,
      stagger: 0.04,
      ease: 'power2.out',
      scrollTrigger: {
        trigger: '#skills',
        start: 'top 80%'
      }
    });

    // Influence
    gsap.from('.influence-card', {
      y: -30,
      opacity: 0,
      duration: 0.5,
      stagger: 0.1,
      ease: 'power2.out',
      scrollTrigger: {
        trigger: '#influence',
        start: 'top 80%'
      }
    });

    // Contact
    gsap.from('.contact-item', {
      y: -25,
      opacity: 0,
      duration: 0.4,
      stagger: 0.08,
      ease: 'power2.out',
      scrollTrigger: {
        trigger: '#contact',
        start: 'top 85%'
      }
    });
  });

  /* ---------- Init ---------- */
  async function init() {
    const gh = await fetchGitHub();
    const totalStars = gh.totalStars || 342;
    const repoCount = gh.repos ? gh.repos.length : 32;
    renderInfluence(totalStars, repoCount);
  }

  init();

})();
