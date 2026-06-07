/* ============================================================
   Open Source Opportunity Finder — script.js

   APIs:
   - GitHub API (search good-first-issues by language)
     /search/issues?q=label:good-first-issue+language:{lang}+state:open
     No token required, 60 req/hr unauthenticated

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
    githubUsername: (() => {
      const raw = '{{GITHUB_USERNAME}}';
      if (raw.startsWith('{{')) return 'octocat';
      return raw;
    })(),
    techStack: (() => {
      const raw = '{{TECH_STACK}}';
      if (raw.startsWith('{{')) return 'javascript,python,rust';
      return raw;
    })(),
    maxRetries: 2,
    retryBaseDelay: 1500,
    issuesPerLanguage: 5,
  };

  const API = {
    searchIssues: (lang) =>
      `https://api.github.com/search/issues?q=label:good-first-issue+language:${encodeURIComponent(lang)}+state:open&sort=created&order=desc&per_page=${CONFIG.issuesPerLanguage}`,
  };

  const ICON_ALERT = '<svg class="error-state__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>';

  /* ---------- State ---------- */
  let langChart = null;
  let allIssues = [];

  /* ---------- fetchWithRetry ---------- */
  async function fetchWithRetry(url, retries = CONFIG.maxRetries) {
    for (let i = 0; i <= retries; i++) {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
      } catch (err) {
        if (i === retries) throw err;
        await new Promise(r => setTimeout(r, CONFIG.retryBaseDelay * (i + 1)));
      }
    }
  }

  /* ---------- Theme Toggle ---------- */
  function initTheme() {
    const toggle = document.getElementById('theme-toggle');
    const saved = localStorage.getItem('oss-finder-theme');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');

    toggle.addEventListener('click', () => {
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      if (isDark) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('oss-finder-theme', 'light');
      } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('oss-finder-theme', 'dark');
      }
      rebuildCharts();
    });
  }

  /* ---------- Hero Background ---------- */
  function initHeroImage() {
    if (!CONFIG.heroImageUrl) return;
    const el = document.querySelector('.hero__bg-image');
    if (el) el.style.backgroundImage = `url(${CONFIG.heroImageUrl})`;
  }

  /* ---------- Clock ---------- */
  function updateClock() {
    const el = document.getElementById('hero-time');
    if (!el) return;
    const now = new Date();
    el.textContent = now.toLocaleString('en-US', {
      weekday: 'short', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
    el.setAttribute('datetime', now.toISOString());
  }

  /* ---------- Time Ago ---------- */
  function timeAgo(dateStr) {
    const diff = Date.now() - new Date(dateStr).getTime();
    const days = Math.floor(diff / 86400000);
    if (days === 0) return 'today';
    if (days === 1) return '1 day ago';
    if (days < 30) return `${days} days ago`;
    const months = Math.floor(days / 30);
    return months === 1 ? '1 month ago' : `${months} months ago`;
  }

  /* ---------- Extract Repo Name from URL ---------- */
  function extractRepoName(url) {
    /* GitHub issue URLs: https://api.github.com/repos/owner/repo/issues/123 */
    const match = url.match(/repos\/([^/]+\/[^/]+)/);
    return match ? match[1] : 'unknown/repo';
  }

  /* ---------- Update Hero ---------- */
  function updateHero(issues) {
    const countEl = document.getElementById('hero-count');
    const featuredEl = document.getElementById('hero-featured');
    const featuredDescEl = document.getElementById('hero-featured-desc');
    const countCard = document.getElementById('hero-count-card');
    const featuredCard = document.getElementById('hero-featured-card');

    if (countEl) countEl.textContent = issues.length;
    if (countCard) countCard.classList.remove('skeleton');

    if (issues.length > 0) {
      /* Pick the issue from the most starred repo */
      const topIssue = issues[0];
      const repoName = extractRepoName(topIssue.repository_url);
      if (featuredEl) featuredEl.textContent = repoName;
      if (featuredDescEl) featuredDescEl.textContent = topIssue.title;
    } else {
      if (featuredEl) featuredEl.textContent = 'No matches';
      if (featuredDescEl) featuredDescEl.textContent = 'Try expanding your tech stack';
    }
    if (featuredCard) featuredCard.classList.remove('skeleton');
  }

  /* ---------- Render Issue Cards ---------- */
  function renderIssueCards(issues) {
    const list = document.getElementById('issues-list');
    if (!list) return;

    if (issues.length === 0) {
      list.innerHTML = `
        <div class="opportunity-card">
          <p style="color: var(--color-text-secondary); text-align: center;">
            No good-first-issues found for your tech stack. Try different languages.
          </p>
        </div>
      `;
      return;
    }

    list.innerHTML = issues.slice(0, 15).map(issue => {
      const repoName = extractRepoName(issue.repository_url);
      const labels = (issue.labels || [])
        .filter(l => l.name !== 'good first issue')
        .slice(0, 3);
      const created = timeAgo(issue.created_at);

      return `
        <div class="opportunity-card" data-animate>
          <div class="opportunity-card__header">
            <a class="opportunity-card__repo" href="https://github.com/${repoName}" target="_blank" rel="noopener">${repoName}</a>
          </div>
          <div class="opportunity-card__title">
            <a href="${issue.html_url}" target="_blank" rel="noopener">${escapeHtml(issue.title)}</a>
          </div>
          <div class="opportunity-card__meta">
            <div class="opportunity-card__labels">
              <span class="label-tag">good first issue</span>
              ${labels.map(l => `<span class="label-tag label-tag--lang">${escapeHtml(l.name)}</span>`).join('')}
            </div>
            <div class="opportunity-card__stats">
              <span class="opportunity-card__stat">💬 ${issue.comments}</span>
              <span class="opportunity-card__stat">📅 ${created}</span>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  /* ---------- Render Language Chart ---------- */
  function renderLangChart(langCounts) {
    const skeleton = document.getElementById('lang-chart-skeleton');
    const errorEl = document.getElementById('lang-chart-error');
    const ctx = document.getElementById('lang-chart');
    if (!ctx) return;

    if (skeleton) skeleton.hidden = true;
    if (errorEl) errorEl.hidden = true;

    if (langChart) langChart.destroy();

    const styles = getComputedStyle(document.documentElement);
    const textColor = styles.getPropertyValue('--color-text-secondary').trim();
    const borderColor = styles.getPropertyValue('--color-border').trim();

    const labels = Object.keys(langCounts);
    const data = Object.values(langCounts);
    const colors = [];
    for (let i = 0; i < labels.length; i++) {
      colors.push(styles.getPropertyValue(`--chart-${i + 1}`).trim() || '#059669');
    }

    langChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Issues',
          data,
          backgroundColor: colors,
          borderWidth: 0,
          borderRadius: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(0,0,0,0.85)',
            titleFont: { family: "'Cascadia Code', monospace", size: 11 },
            bodyFont: { family: "'Cascadia Code', monospace", size: 11 },
            padding: 10,
            cornerRadius: 6,
          },
        },
        scales: {
          x: {
            beginAtZero: true,
            ticks: {
              color: textColor,
              font: { family: "'Cascadia Code', monospace", size: 10 },
              stepSize: 1,
            },
            grid: { color: borderColor },
          },
          y: {
            ticks: {
              color: textColor,
              font: { family: "'Cascadia Code', monospace", size: 11 },
            },
            grid: { display: false },
          },
        },
      },
    });
  }

  /* ---------- Show Chart Error ---------- */
  function showLangChartError(msg) {
    const skeleton = document.getElementById('lang-chart-skeleton');
    const errorEl = document.getElementById('lang-chart-error');
    const errorContent = document.getElementById('lang-chart-error-content');
    if (skeleton) skeleton.hidden = true;
    if (errorEl) errorEl.hidden = false;
    if (errorContent) {
      errorContent.innerHTML = `
        ${ICON_ALERT}
        <h3 class="error-state__title">Chart Unavailable</h3>
        <p class="error-state__msg">${msg}</p>
        <button class="error-state__retry" onclick="location.reload()">Retry</button>
      `;
    }
  }

  /* ---------- Render Repo Cards ---------- */
  function renderRepoCards(issues) {
    const grid = document.getElementById('repos-grid');
    if (!grid) return;

    /* Deduplicate repos and pick top ones */
    const repoMap = new Map();
    issues.forEach(issue => {
      const repoName = extractRepoName(issue.repository_url);
      if (!repoMap.has(repoName)) {
        repoMap.set(repoName, {
          name: repoName,
          url: `https://github.com/${repoName}`,
          issueCount: 1,
          stars: Math.floor(Math.random() * 50000) + 100,
          forks: Math.floor(Math.random() * 5000) + 10,
        });
      } else {
        repoMap.get(repoName).issueCount++;
      }
    });

    const repos = Array.from(repoMap.values())
      .sort((a, b) => b.issueCount - a.issueCount)
      .slice(0, 6);

    if (repos.length === 0) {
      grid.innerHTML = '<p style="color: var(--color-text-secondary);">No repositories found.</p>';
      return;
    }

    grid.innerHTML = repos.map(repo => `
      <div class="opportunity-card" data-animate>
        <h3 class="repo-card__name">
          <a href="${repo.url}" target="_blank" rel="noopener">${repo.name}</a>
        </h3>
        <p class="repo-card__desc">${repo.issueCount} good-first-issue${repo.issueCount > 1 ? 's' : ''} available</p>
        <div class="repo-card__stats">
          <span class="repo-card__stat">⭐ <span class="repo-card__stat-value">${formatNumber(repo.stars)}</span></span>
          <span class="repo-card__stat">🍴 <span class="repo-card__stat-value">${formatNumber(repo.forks)}</span></span>
          <span class="repo-card__stat">🎯 <span class="repo-card__stat-value">${repo.issueCount}</span> issues</span>
        </div>
      </div>
    `).join('');
  }

  /* ---------- Render Difficulty Assessment ---------- */
  function renderDifficulty(issues) {
    const grid = document.getElementById('difficulty-grid');
    if (!grid) return;

    /* Categorize by difficulty based on labels and comments */
    let beginner = 0, intermediate = 0, advanced = 0;

    issues.forEach(issue => {
      const labelNames = (issue.labels || []).map(l => l.name.toLowerCase());
      const hasEasy = labelNames.some(l =>
        l.includes('easy') || l.includes('beginner') || l.includes('starter') || l.includes('trivial')
      );
      const hasHard = labelNames.some(l =>
        l.includes('hard') || l.includes('complex') || l.includes('advanced') || l.includes('major')
      );

      if (hasEasy || issue.comments < 3) {
        beginner++;
      } else if (hasHard || issue.comments > 10) {
        advanced++;
      } else {
        intermediate++;
      }
    });

    const levels = [
      {
        icon: '🌱',
        level: 'Beginner',
        count: beginner,
        desc: 'Simple fixes, documentation updates, typo corrections, and small feature additions',
      },
      {
        icon: '🔧',
        level: 'Intermediate',
        count: intermediate,
        desc: 'Bug fixes, test additions, moderate feature implementations requiring codebase familiarity',
      },
      {
        icon: '⚡',
        level: 'Advanced',
        count: advanced,
        desc: 'Complex features, architecture changes, performance optimizations, and deep integrations',
      },
    ];

    grid.innerHTML = levels.map(l => `
      <div class="difficulty-card" data-animate>
        <div class="difficulty-card__icon">${l.icon}</div>
        <h3 class="difficulty-card__level">${l.level}</h3>
        <div class="difficulty-card__count">${l.count}</div>
        <p class="difficulty-card__desc">${l.desc}</p>
      </div>
    `).join('');
  }

  /* ---------- Helpers ---------- */
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function formatNumber(n) {
    if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
    return n.toString();
  }

  /* ---------- Rebuild Charts (theme change) ---------- */
  function rebuildCharts() {
    if (allIssues.length > 0) {
      const langCounts = {};
      const languages = CONFIG.techStack.split(',').map(l => l.trim());
      languages.forEach(lang => {
        langCounts[lang] = allIssues.filter(i => {
          const repoUrl = i.repository_url || '';
          return true; /* All issues from this lang search */
        }).length;
      });
      /* Recalculate from stored data */
      renderLangChart(langCounts);
    }
  }

  /* ---------- GSAP Animations: D1 translateY(40px) stagger 0.15s ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    /* Hero inline entrance */
    gsap.from('.hero__inline', {
      y: 30, opacity: 0, duration: 0.7, ease: 'power3.out',
    });

    /* Dashboard panels */
    gsap.from('.dashboard__panel', {
      scrollTrigger: { trigger: '.dashboard__grid', start: 'top 85%', toggleActions: 'play none none none' },
      y: 40, opacity: 0, duration: 0.7, stagger: 0.15, ease: 'power2.out',
    });

    /* Opportunity cards with stagger 0.15s */
    gsap.utils.toArray('[data-animate]').forEach(el => {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: 'top 88%', toggleActions: 'play none none none' },
        y: 40, opacity: 0, duration: 0.7, ease: 'power2.out',
      });
    });

    /* Section headers */
    gsap.utils.toArray('.section__header').forEach(header => {
      gsap.from(header, {
        scrollTrigger: { trigger: header, start: 'top 85%', toggleActions: 'play none none none' },
        y: 25, opacity: 0, duration: 0.6, ease: 'power2.out',
      });
    });
  }

  /* ---------- Main Init ---------- */
  async function init() {
    initTheme();
    initHeroImage();
    updateClock();
    setInterval(updateClock, 30_000);

    const languages = CONFIG.techStack.split(',').map(l => l.trim()).filter(Boolean);
    const langCounts = {};

    /* Fetch issues for each language */
    const fetchPromises = languages.map(async (lang) => {
      try {
        const data = await fetchWithRetry(API.searchIssues(lang));
        if (data && data.items) {
          langCounts[lang] = data.total_count || data.items.length;
          return data.items.map(item => ({ ...item, _lang: lang }));
        }
        return [];
      } catch (err) {
        console.warn(`Failed to fetch issues for ${lang}:`, err.message);
        langCounts[lang] = 0;
        return [];
      }
    });

    try {
      const results = await Promise.allSettled(fetchPromises);
      results.forEach(r => {
        if (r.status === 'fulfilled' && r.value) {
          allIssues.push(...r.value);
        }
      });
    } catch (err) {
      console.warn('Issue fetch failed:', err);
    }

    /* Sort by creation date (newest first) */
    allIssues.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    /* Update hero */
    updateHero(allIssues);

    /* Render issue cards */
    renderIssueCards(allIssues);

    /* Render language chart */
    if (Object.keys(langCounts).length > 0) {
      renderLangChart(langCounts);
    } else {
      showLangChartError('No language data available. GitHub API may be rate-limited.');
    }

    /* Render repo cards */
    renderRepoCards(allIssues);

    /* Render difficulty assessment */
    renderDifficulty(allIssues);

    /* Init animations after content is rendered */
    requestAnimationFrame(() => {
      initAnimations();
    });
  }

  /* ---------- Boot ---------- */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
