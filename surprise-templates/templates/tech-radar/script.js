/* ============================================================
   Tech Stack Trend Radar — script.js
   
   APIs: GitHub (public, 60 req/hr) + HackerNews Firebase (unlimited)
   Animation: IntersectionObserver scroll-reveal (no GSAP — editorial feel)
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Reduced Motion ---------- */
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Configuration ---------- */
  const CONFIG = {
    techStack: (() => {
      try {
        const raw = '{{TECH_STACK}}';
        if (raw.startsWith('{{')) return ['typescript', 'react', 'python'];
        return JSON.parse(raw);
      } catch {
        return ['typescript', 'react', 'python'];
      }
    })(),
    githubUsername: (() => {
      const raw = '{{GITHUB_USERNAME}}';
      return raw.startsWith('{{') ? '' : raw;
    })(),
    maxRetries: 2,
    retryBaseDelay: 1500,
  };

  const API = {
    /* GitHub trending — unofficial but CORS-friendly */
    trending: () =>
      'https://api.gitterapp.com/repositories?since=daily&spoken_language_code=en',
    /* HackerNews Firebase — fully public, no rate limit */
    hnTop: () =>
      'https://hacker-news.firebaseio.com/v0/topstories.json',
    hnItem: (id) =>
      `https://hacker-news.firebaseio.com/v0/item/${id}.json`,
    /* GitHub public API — 60 req/hr unauthenticated */
    githubUser: (username) =>
      `https://api.github.com/users/${username}`,
    githubRepos: (username) =>
      `https://api.github.com/users/${username}/repos?sort=updated&per_page=10`,
  };

  const ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';

  /* ---------- Dev Quotes ---------- */
  const DEV_QUOTES = [
    { text: 'Any fool can write code that a computer can understand. Good programmers write code that humans can understand.', author: 'Martin Fowler' },
    { text: 'First, solve the problem. Then, write the code.', author: 'John Johnson' },
    { text: 'The best error message is the one that never shows up.', author: 'Thomas Fuchs' },
    { text: 'Code is like humor. When you have to explain it, it\'s bad.', author: 'Cory House' },
    { text: 'Simplicity is the soul of efficiency.', author: 'Austin Freeman' },
    { text: 'Make it work, make it right, make it fast.', author: 'Kent Beck' },
    { text: 'Programs must be written for people to read, and only incidentally for machines to execute.', author: 'Harold Abelson' },
    { text: 'The most disastrous thing that you can ever learn is your first programming language.', author: 'Alan Kay' },
    { text: 'Walking on water and developing software from a specification are easy if both are frozen.', author: 'Edward V. Berard' },
    { text: 'Measuring programming progress by lines of code is like measuring aircraft building progress by weight.', author: 'Bill Gates' },
  ];

  /* ---------- Language Colors (GitHub convention) ---------- */
  const LANG_COLORS = {
    JavaScript: '#f1e05a', TypeScript: '#3178c6', Python: '#3572A5',
    Java: '#b07219', Go: '#00ADD8', Rust: '#dea584',
    'C++': '#f34b7d', C: '#555555', 'C#': '#178600',
    Ruby: '#701516', PHP: '#4F5D95', Swift: '#F05138',
    Kotlin: '#A97BFF', Dart: '#00B4AB', Scala: '#c22d40',
    Shell: '#89e051', Lua: '#000080', Zig: '#ec915c',
    Elixir: '#6e4a7e', Haskell: '#5e5086', Vue: '#41b883',
    Svelte: '#ff3e00', HTML: '#e34c26', CSS: '#563d7c',
    Jupyter: '#DA5B0B', R: '#198CE7',
  };

  /* ============================================================
     UTILITY FUNCTIONS
     ============================================================ */

  async function fetchWithRetry(url, retries = CONFIG.maxRetries) {
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
      } catch (err) {
        if (attempt === retries) throw err;
        const delay = CONFIG.retryBaseDelay * (attempt + 1);
        await new Promise((r) => setTimeout(r, delay));
      }
    }
  }

  function showError(containerId, message, retryFn) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = `
      <div class="error-state">
        ${ICON_ALERT}
        <p class="error-state__message">${message}</p>
        ${retryFn ? '<button class="error-state__retry" data-retry="true">Retry</button>' : ''}
      </div>`;
    if (retryFn) {
      const btn = container.querySelector('[data-retry]');
      if (btn) btn.addEventListener('click', retryFn);
    }
  }

  function showSkeleton(containerId, count, type) {
    const container = document.getElementById(containerId);
    if (!container) return;
    let html = '';
    for (let i = 0; i < count; i++) {
      if (type === 'repo') {
        html += `
          <div class="repo-card">
            <div class="skeleton" style="width:100px;height:16px"></div>
            <div class="skeleton skeleton--text" style="margin-top:8px"></div>
            <div class="skeleton" style="width:60%;height:14px;margin-top:6px"></div>
          </div>`;
      } else if (type === 'hn') {
        html += `
          <li class="hn-item">
            <div></div>
            <div>
              <div class="skeleton skeleton--text"></div>
              <div class="skeleton" style="width:40%;height:12px;margin-top:6px"></div>
            </div>
          </li>`;
      }
    }
    container.innerHTML = html;
  }

  function formatNumber(n) {
    if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
    return String(n);
  }

  function timeAgo(timestamp) {
    const seconds = Math.floor((Date.now() / 1000) - timestamp);
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
    return Math.floor(seconds / 86400) + 'd ago';
  }

  /* ============================================================
     DATA FETCHERS
     ============================================================ */

  /* 1. GitHub Trending Repos */
  async function fetchTrending() {
    const container = document.getElementById('trending-repos');
    if (!container) return;

    showSkeleton('trending-repos', 7, 'repo');

    try {
      const data = await fetchWithRetry(API.trending());
      const repos = (data || []).slice(0, 7);

      if (repos.length === 0) {
        showError('trending-repos', 'No trending repos found', fetchTrending);
        return;
      }

      let html = '';
      repos.forEach((repo) => {
        const langColor = LANG_COLORS[repo.language] || '#888';
        html += `
          <div class="repo-card scroll-reveal">
            <div class="repo-card__header">
              <img class="repo-card__avatar" src="${repo.avatar || `https://github.com/${repo.author}.png?size=48`}" alt="" loading="lazy" />
              <span class="repo-card__owner">${repo.author}</span>
            </div>
            <div class="repo-card__name">
              <a href="${repo.url || `https://github.com/${repo.author}/${repo.name}`}" target="_blank" rel="noopener noreferrer">${repo.name}</a>
            </div>
            <p class="repo-card__desc">${repo.description || ''}</p>
            <div class="repo-card__meta">
              ${repo.language ? `<span class="repo-card__lang"><span class="repo-card__lang-dot" style="background:${langColor}"></span>${repo.language}</span>` : ''}
              <span class="repo-card__stars">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="m12 2 3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
                ${formatNumber(repo.stars || 0)}
              </span>
              ${repo.currentPeriodStars ? `<span class="repo-card__stars-today">+${formatNumber(repo.currentPeriodStars)} today</span>` : ''}
            </div>
          </div>`;
      });

      container.innerHTML = html;
      initScrollReveal();
    } catch (err) {
      /* Fallback: try GitHub search API */
      try {
        const fallback = await fetchWithRetry(
          'https://api.github.com/search/repositories?q=stars:>1000+pushed:>' +
          new Date(Date.now() - 7 * 86400000).toISOString().split('T')[0] +
          '&sort=stars&order=desc&per_page=7'
        );
        const repos = fallback?.items || [];
        if (repos.length === 0) throw new Error('No results');

        let html = '';
        repos.forEach((repo) => {
          const langColor = LANG_COLORS[repo.language] || '#888';
          html += `
            <div class="repo-card scroll-reveal">
              <div class="repo-card__header">
                <img class="repo-card__avatar" src="${repo.owner?.avatar_url || ''}" alt="" loading="lazy" />
                <span class="repo-card__owner">${repo.owner?.login || ''}</span>
              </div>
              <div class="repo-card__name">
                <a href="${repo.html_url}" target="_blank" rel="noopener noreferrer">${repo.name}</a>
              </div>
              <p class="repo-card__desc">${repo.description || ''}</p>
              <div class="repo-card__meta">
                ${repo.language ? `<span class="repo-card__lang"><span class="repo-card__lang-dot" style="background:${langColor}"></span>${repo.language}</span>` : ''}
                <span class="repo-card__stars">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="m12 2 3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
                  ${formatNumber(repo.stargazers_count || 0)}
                </span>
              </div>
            </div>`;
        });

        container.innerHTML = html;
        initScrollReveal();
      } catch {
        showError('trending-repos', 'Failed to load trending repos', fetchTrending);
      }
    }
  }

  /* 2. Hacker News Top Stories */
  async function fetchHackerNews() {
    const container = document.getElementById('hn-stories');
    if (!container) return;

    showSkeleton('hn-stories', 10, 'hn');

    try {
      const ids = await fetchWithRetry(API.hnTop());
      const topIds = (ids || []).slice(0, 10);

      if (topIds.length === 0) {
        showError('hn-stories', 'No stories available', fetchHackerNews);
        return;
      }

      const stories = await Promise.all(
        topIds.map((id) => fetchWithRetry(API.hnItem(id)).catch(() => null))
      );

      let html = '';
      stories.filter(Boolean).forEach((story) => {
        const domain = story.url ? new URL(story.url).hostname.replace('www.', '') : 'news.ycombinator.com';
        html += `
          <li class="hn-item scroll-reveal">
            <div></div>
            <div>
              <div class="hn-item__title">
                <a href="${story.url || `https://news.ycombinator.com/item?id=${story.id}`}" target="_blank" rel="noopener noreferrer">${story.title}</a>
              </div>
              <div class="hn-item__meta">
                <span class="hn-item__points">${story.score} pts</span>
                &middot; ${story.by}
                &middot; ${timeAgo(story.time)}
                &middot; <a href="https://news.ycombinator.com/item?id=${story.id}" target="_blank" rel="noopener noreferrer">${story.descendants || 0} comments</a>
                &middot; ${domain}
              </div>
            </div>
          </li>`;
      });

      container.innerHTML = html;
      initScrollReveal();
    } catch (err) {
      showError('hn-stories', 'Failed to load Hacker News', fetchHackerNews);
    }
  }

  /* 3. Language Popularity Chart */
  function renderLanguageChart() {
    const canvas = document.getElementById('lang-chart');
    if (!canvas) return;

    /* Static data — TIOBE-inspired, updated periodically */
    const languages = [
      { name: 'Python', share: 28.1 },
      { name: 'JavaScript', share: 16.4 },
      { name: 'TypeScript', share: 12.3 },
      { name: 'Java', share: 8.2 },
      { name: 'Go', share: 5.1 },
      { name: 'Rust', share: 4.8 },
      { name: 'C/C++', share: 4.5 },
      { name: 'Other', share: 20.6 },
    ];

    /* Highlight user's stack */
    const userStack = CONFIG.techStack.map((s) => s.toLowerCase());
    const colors = languages.map((lang) => {
      const isUser = userStack.some((s) =>
        lang.name.toLowerCase().includes(s) || s.includes(lang.name.toLowerCase())
      );
      return isUser
        ? getComputedStyle(document.documentElement).getPropertyValue('--chart-1').trim() || '#c23616'
        : getComputedStyle(document.documentElement).getPropertyValue('--color-border').trim() || '#d4cfc6';
    });

    const ctx = canvas.getContext('2d');
    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: languages.map((l) => l.name),
        datasets: [{
          data: languages.map((l) => l.share),
          backgroundColor: colors,
          borderWidth: 2,
          borderColor: getComputedStyle(document.documentElement).getPropertyValue('--color-bg').trim() || '#faf8f4',
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '55%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              font: { family: "'Geist Mono', monospace", size: 11 },
              color: getComputedStyle(document.documentElement).getPropertyValue('--color-text-secondary').trim() || '#5c5a55',
              padding: 12,
              usePointStyle: true,
              pointStyleWidth: 8,
            },
          },
          tooltip: {
            callbacks: {
              label: (ctx) => ` ${ctx.label}: ${ctx.parsed}%`,
            },
          },
        },
        animation: prefersReducedMotion ? false : { animateRotate: true, duration: 800 },
      },
    });
  }

  /* 4. Stack Tags */
  function renderStackTags() {
    const container = document.getElementById('stack-tags');
    if (!container) return;

    const html = CONFIG.techStack
      .map((tag) => `<span class="stack-tag">${tag}</span>`)
      .join('');
    container.innerHTML = html;
  }

  /* 5. Dev Quote */
  function renderQuote() {
    const quoteEl = document.getElementById('dev-quote');
    if (!quoteEl) return;

    const quote = DEV_QUOTES[Math.floor(Math.random() * DEV_QUOTES.length)];
    const textEl = quoteEl.querySelector('.pull-quote__text');
    const citeEl = quoteEl.querySelector('.pull-quote__cite');
    if (textEl) textEl.textContent = quote.text;
    if (citeEl) citeEl.textContent = '— ' + quote.author;
  }

  /* 6. GitHub User Stats (optional) */
  async function fetchGitHubUser() {
    if (!CONFIG.githubUsername) return;

    const section = document.getElementById('github-section');
    const container = document.getElementById('github-stats');
    const handle = document.getElementById('github-handle');
    if (!section || !container) return;

    try {
      const [user, repos] = await Promise.all([
        fetchWithRetry(API.githubUser(CONFIG.githubUsername)),
        fetchWithRetry(API.githubRepos(CONFIG.githubUsername)),
      ]);

      if (!user) return;

      section.style.display = 'block';
      if (handle) handle.textContent = '@' + user.login;

      const totalStars = (repos || []).reduce((sum, r) => sum + (r.stargazers_count || 0), 0);
      const topLangs = {};
      (repos || []).forEach((r) => {
        if (r.language) topLangs[r.language] = (topLangs[r.language] || 0) + 1;
      });
      const topLang = Object.entries(topLangs).sort((a, b) => b[1] - a[1])[0];

      container.innerHTML = `
        <div class="github-stat scroll-reveal">
          <div class="github-stat__value">${user.public_repos}</div>
          <div class="github-stat__label">Repos</div>
        </div>
        <div class="github-stat scroll-reveal">
          <div class="github-stat__value">${formatNumber(totalStars)}</div>
          <div class="github-stat__label">Total Stars</div>
        </div>
        <div class="github-stat scroll-reveal">
          <div class="github-stat__value">${user.followers}</div>
          <div class="github-stat__label">Followers</div>
        </div>
        <div class="github-stat scroll-reveal">
          <div class="github-stat__value">${topLang ? topLang[0] : '—'}</div>
          <div class="github-stat__label">Top Language</div>
        </div>`;

      initScrollReveal();
    } catch {
      /* Silently skip — GitHub section stays hidden */
    }
  }

  /* ============================================================
     SCROLL REVEAL (IntersectionObserver)
     ============================================================ */

  function initScrollReveal() {
    if (prefersReducedMotion) {
      document.querySelectorAll('.scroll-reveal').forEach((el) => el.classList.add('visible'));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -10% 0px' }
    );

    document.querySelectorAll('.scroll-reveal:not(.visible)').forEach((el) => observer.observe(el));
  }

  /* ============================================================
     THEME TOGGLE
     ============================================================ */

  function initTheme() {
    const stored = localStorage.getItem('tech-radar-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = stored || (prefersDark ? 'dark' : 'light');

    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    }

    const btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.addEventListener('click', () => {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        if (isDark) {
          document.documentElement.removeAttribute('data-theme');
          localStorage.setItem('tech-radar-theme', 'light');
        } else {
          document.documentElement.setAttribute('data-theme', 'dark');
          localStorage.setItem('tech-radar-theme', 'dark');
        }
      });
    }
  }

  /* ============================================================
     MASTHEAD DATE
     ============================================================ */

  function setMastheadDate() {
    const el = document.getElementById('masthead-date');
    if (!el) return;
    const now = new Date();
    el.textContent = now.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  }

  /* ============================================================
     INIT
     ============================================================ */

  function init() {
    initTheme();
    setMastheadDate();
    renderStackTags();
    renderQuote();

    /* Stagger API calls */
    fetchTrending();
    setTimeout(fetchHackerNews, 300);
    setTimeout(renderLanguageChart, 600);
    setTimeout(fetchGitHubUser, 900);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
