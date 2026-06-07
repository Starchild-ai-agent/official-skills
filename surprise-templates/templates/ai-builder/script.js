/* ============================================================
   AI Builder Toolkit — script.js

   APIs: GitHub (search repos) + Built-in AI model data
   Animation: GSAP 3 + ScrollTrigger
   Entrance: D13 blur(8px) → blur(0)
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Register GSAP Plugins ---------- */
  gsap.registerPlugin(ScrollTrigger);

  /* ---------- Reduced Motion Check ---------- */
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Configuration ---------- */
  const CONFIG = {
    githubUsername: (() => {
      const raw = '{{GITHUB_USERNAME}}';
      return raw.startsWith('{{') ? 'openai' : raw;
    })(),
    maxRetries: 2,
    retryBaseDelay: 1500,
  };

  const API = {
    githubSearch: (q) =>
      `https://api.github.com/search/repositories?q=${encodeURIComponent(q)}&sort=stars&order=desc&per_page=6`,
  };

  /* ---------- Mock Data: AI Models ---------- */
  const AI_MODELS = [
    { name: 'GPT-4o', provider: 'OpenAI', inputPrice: 2.50, outputPrice: 10.00, speed: '~80 tok/s', context: '128K' },
    { name: 'Claude 3.5 Sonnet', provider: 'Anthropic', inputPrice: 3.00, outputPrice: 15.00, speed: '~90 tok/s', context: '200K' },
    { name: 'Gemini 1.5 Pro', provider: 'Google', inputPrice: 1.25, outputPrice: 5.00, speed: '~70 tok/s', context: '2M' },
    { name: 'Llama 3.1 405B', provider: 'Meta', inputPrice: 0.80, outputPrice: 0.80, speed: '~40 tok/s', context: '128K' },
    { name: 'Mistral Large', provider: 'Mistral', inputPrice: 2.00, outputPrice: 6.00, speed: '~65 tok/s', context: '128K' },
    { name: 'Command R+', provider: 'Cohere', inputPrice: 3.00, outputPrice: 15.00, speed: '~55 tok/s', context: '128K' },
  ];

  const MODEL_RELEASES = [
    { name: 'GPT-4o Mini', detail: 'Smaller, faster, cheaper — 128K context', date: '2024-07-18' },
    { name: 'Claude 3.5 Sonnet', detail: 'New benchmark leader in coding tasks', date: '2024-06-20' },
    { name: 'Llama 3.1 405B', detail: 'Largest open-source model to date', date: '2024-07-23' },
    { name: 'Gemini 1.5 Flash', detail: '1M context at ultra-low cost', date: '2024-05-14' },
    { name: 'Mistral NeMo', detail: '12B params, Apache 2.0 license', date: '2024-07-18' },
    { name: 'Phi-3 Medium', detail: 'Microsoft 14B, strong reasoning', date: '2024-05-21' },
  ];

  const TRENDING_PAPERS = [
    { title: 'Scaling Laws for Neural Language Models Revisited', category: 'cs.CL', citations: 342, date: '2024-07' },
    { title: 'Constitutional AI: Harmlessness from AI Feedback', category: 'cs.AI', citations: 891, date: '2024-06' },
    { title: 'Mixture of Experts Meets Instruction Tuning', category: 'cs.LG', citations: 256, date: '2024-07' },
    { title: 'Direct Preference Optimization: Your LM is a Reward Model', category: 'cs.CL', citations: 1203, date: '2024-05' },
    { title: 'Efficient Memory Transformers via Sparse Attention', category: 'cs.LG', citations: 178, date: '2024-07' },
    { title: 'Vision-Language Models for Autonomous Agents', category: 'cs.CV', citations: 445, date: '2024-06' },
    { title: 'Retrieval-Augmented Generation for Knowledge-Intensive Tasks', category: 'cs.IR', citations: 2100, date: '2024-04' },
  ];

  const OPEN_SOURCE_RANKINGS = {
    labels: ['Llama 3.1', 'Mistral', 'Phi-3', 'Qwen 2', 'Gemma 2', 'Command R', 'Yi-1.5', 'DeepSeek V2'],
    scores: [88.7, 85.2, 82.1, 84.5, 81.3, 79.8, 80.2, 86.1],
  };

  const TICKER_MESSAGES = [
    '> GPT-4o-mini released — 15x cheaper than GPT-4o',
    '> Llama 3.1 405B now available — largest open-source LLM',
    '> Claude 3.5 Sonnet tops SWE-bench coding benchmark',
    '> Gemini 1.5 Flash: 1M context window at $0.075/1M tokens',
    '> Mistral NeMo 12B: Apache 2.0, multilingual, 128K context',
    '> DeepSeek-V2 achieves GPT-4 level at 1/10th the cost',
  ];

  const PRICE_MAP = {
    gpt4o: { input: 2.50, output: 10.00 },
    claude: { input: 3.00, output: 15.00 },
    gemini: { input: 1.25, output: 5.00 },
    llama: { input: 0.80, output: 0.80 },
  };

  /* ============================================================
     GSAP ANIMATION SYSTEM
     ============================================================ */

  function animateHeroEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.terminal-hero', { opacity: 1 });
      return;
    }
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    tl.from('.terminal-hero__chrome', { opacity: 0, y: -20, duration: 0.5 })
      .from('.terminal-hero__body', { opacity: 0, y: 20, duration: 0.6 }, '-=0.2')
      .from('.terminal-hero__stats .terminal-hero__stat', {
        opacity: 0, y: 15, stagger: 0.1, duration: 0.4,
      }, '-=0.3');
  }

  /** D13: blur(8px) → blur(0) entrance for panels */
  function animatePanelEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.ai-panel', { opacity: 1, filter: 'blur(0px)' });
      return;
    }
    const panels = gsap.utils.toArray('.ai-panel');
    panels.forEach((panel) => {
      gsap.to(panel, {
        opacity: 1,
        filter: 'blur(0px)',
        duration: 0.8,
        ease: 'power2.out',
        scrollTrigger: {
          trigger: panel,
          start: 'top 88%',
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
    const stored = localStorage.getItem('ai-builder-theme');
    if (stored) html.setAttribute('data-theme', stored);

    btn.addEventListener('click', () => {
      const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-theme', next);
      localStorage.setItem('ai-builder-theme', next);
    });
  }

  /* ============================================================
     TICKER ANIMATION
     ============================================================ */
  function initTicker() {
    const el = document.getElementById('model-ticker');
    if (!el) return;
    let idx = 0;

    function typeMessage(msg) {
      el.innerHTML = '';
      let i = 0;
      const cursor = document.createElement('span');
      cursor.className = 'terminal-hero__cursor';
      cursor.textContent = '▊';

      function typeChar() {
        if (i < msg.length) {
          el.textContent = msg.substring(0, i + 1);
          el.appendChild(cursor);
          i++;
          setTimeout(typeChar, 30 + Math.random() * 20);
        } else {
          setTimeout(() => {
            idx = (idx + 1) % TICKER_MESSAGES.length;
            typeMessage(TICKER_MESSAGES[idx]);
          }, 4000);
        }
      }
      typeChar();
    }

    typeMessage(TICKER_MESSAGES[idx]);
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

  /* ---------- GitHub Repos ---------- */
  async function loadRepos() {
    const container = document.getElementById('repos-list');
    if (!container) return;

    try {
      const data = await fetchWithRetry(API.githubSearch('artificial intelligence machine learning'));
      const repos = (data.items || []).slice(0, 6);
      document.getElementById('stat-repos').textContent = data.total_count
        ? data.total_count.toLocaleString()
        : '100K+';

      container.innerHTML = repos.map((r) => {
        const langColor = getLangColor(r.language);
        return `
          <div class="repo-card">
            <a class="repo-card__name" href="${r.html_url}" target="_blank" rel="noopener">${r.full_name}</a>
            <p class="repo-card__desc">${r.description || 'No description'}</p>
            <div class="repo-card__meta">
              ${r.language ? `<span class="repo-card__meta-item"><span class="repo-card__lang-dot" style="background:${langColor}"></span>${r.language}</span>` : ''}
              <span class="repo-card__meta-item">⭐ ${formatNumber(r.stargazers_count)}</span>
              <span class="repo-card__meta-item">🍴 ${formatNumber(r.forks_count)}</span>
            </div>
          </div>`;
      }).join('');
    } catch {
      container.innerHTML = '<div class="error-state">Failed to load repos. Check network.</div>';
    }
  }

  /* ---------- Model Comparison Table ---------- */
  function loadModelComparison() {
    const tbody = document.getElementById('model-table-body');
    if (!tbody) return;
    document.getElementById('stat-models').textContent = AI_MODELS.length.toString();

    tbody.innerHTML = AI_MODELS.map((m) => `
      <tr>
        <td class="model-name">${m.name}</td>
        <td>${m.provider}</td>
        <td class="price-highlight">$${m.inputPrice.toFixed(2)}</td>
        <td class="price-highlight">$${m.outputPrice.toFixed(2)}</td>
        <td>${m.speed}</td>
        <td>${m.context}</td>
      </tr>
    `).join('');
  }

  /* ---------- Trending Papers ---------- */
  function loadPapers() {
    const container = document.getElementById('papers-list');
    if (!container) return;
    document.getElementById('stat-papers').textContent = TRENDING_PAPERS.length.toString();

    container.innerHTML = TRENDING_PAPERS.map((p) => `
      <div class="paper-item">
        <div class="paper-item__title">${p.title}</div>
        <div class="paper-item__meta">
          <span class="paper-item__category">${p.category}</span>
          <span>${p.citations} citations</span>
          <span>${p.date}</span>
        </div>
      </div>
    `).join('');
  }

  /* ---------- Open Source Rankings Chart ---------- */
  function loadRankingsChart() {
    const canvas = document.getElementById('rankings-chart');
    if (!canvas) return;

    const style = getComputedStyle(document.documentElement);
    const accent = style.getPropertyValue('--color-accent').trim();
    const textMuted = style.getPropertyValue('--color-text-muted').trim();
    const border = style.getPropertyValue('--color-border').trim();

    new Chart(canvas, {
      type: 'bar',
      data: {
        labels: OPEN_SOURCE_RANKINGS.labels,
        datasets: [{
          label: 'MMLU Score',
          data: OPEN_SOURCE_RANKINGS.scores,
          backgroundColor: OPEN_SOURCE_RANKINGS.scores.map((_, i) => {
            const colors = [accent, '#a78bfa', '#34d399', '#fbbf24', '#f87171', '#60a5fa', '#fb923c', '#e879f9'];
            return colors[i % colors.length];
          }),
          borderRadius: 4,
          borderSkipped: false,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1a1630',
            titleFont: { family: 'Fira Code' },
            bodyFont: { family: 'Fira Code' },
          },
        },
        scales: {
          x: {
            min: 70,
            max: 95,
            grid: { color: border },
            ticks: { color: textMuted, font: { family: 'Fira Code', size: 10 } },
          },
          y: {
            grid: { display: false },
            ticks: { color: textMuted, font: { family: 'Exo 2', size: 11 } },
          },
        },
      },
    });
  }

  /* ---------- Model Releases ---------- */
  function loadReleases() {
    const container = document.getElementById('releases-list');
    if (!container) return;

    container.innerHTML = MODEL_RELEASES.map((r) => `
      <div class="release-item">
        <div class="release-item__dot"></div>
        <div class="release-item__content">
          <div class="release-item__name">${r.name}</div>
          <div class="release-item__detail">${r.detail}</div>
        </div>
        <div class="release-item__date">${r.date}</div>
      </div>
    `).join('');
  }

  /* ---------- API Price Calculator ---------- */
  function initCalculator() {
    const modelSelect = document.getElementById('calc-model');
    const inputTokens = document.getElementById('calc-input');
    const outputTokens = document.getElementById('calc-output');
    const resultEl = document.getElementById('calc-result');
    if (!modelSelect || !inputTokens || !outputTokens || !resultEl) return;

    function calculate() {
      const model = PRICE_MAP[modelSelect.value];
      if (!model) return;
      const inCost = parseFloat(inputTokens.value) * model.input;
      const outCost = parseFloat(outputTokens.value) * model.output;
      const total = inCost + outCost;
      resultEl.textContent = `$${total.toFixed(2)}`;
    }

    modelSelect.addEventListener('change', calculate);
    inputTokens.addEventListener('input', calculate);
    outputTokens.addEventListener('input', calculate);
    calculate();
  }

  /* ============================================================
     HELPERS
     ============================================================ */
  function formatNumber(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toString();
  }

  function getLangColor(lang) {
    const colors = {
      Python: '#3572A5', JavaScript: '#f1e05a', TypeScript: '#3178c6',
      Jupyter: '#DA5B0B', Rust: '#dea584', Go: '#00ADD8',
      C: '#555555', 'C++': '#f34b7d', Java: '#b07219',
      Kotlin: '#A97BFF', Swift: '#F05138', Ruby: '#701516',
    };
    return colors[lang] || '#8b8b8b';
  }

  /* ============================================================
     INIT
     ============================================================ */
  function init() {
    initThemeToggle();
    initTicker();
    loadModelComparison();
    loadPapers();
    loadReleases();
    loadRankingsChart();
    initCalculator();
    loadRepos();

    // Animations
    animateHeroEntrance();
    requestAnimationFrame(() => {
      animatePanelEntrance();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
