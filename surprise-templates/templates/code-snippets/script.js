/* ============================================================
   Code Snippet Library — script.js

   Layout: A3 Split Screen (left list, right preview)
   Hover:  C15 left border + bg change (CSS)
   Entry:  D7 translateX(-20px) from left
   Hero:   H7 Minimal Hero

   Pure frontend — no external APIs.
   Animation: GSAP 3 + ScrollTrigger (CDN)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var CONFIG = {
    heroImageUrl: (function () {
      var raw = '{{HERO_IMAGE_URL}}';
      if (raw.indexOf('{{') === 0) return '';
      return raw;
    })(),
  };

  var STORAGE_KEY = 'code-snippets-data';
  var FAVS_KEY = 'code-snippets-favs';

  /* ---------- Built-in Snippets ---------- */
  var BUILTIN_SNIPPETS = [
    { id: 'js-debounce', title: 'Debounce Function', lang: 'javascript', code: 'function debounce(fn, delay = 300) {\n  let timer;\n  return (...args) => {\n    clearTimeout(timer);\n    timer = setTimeout(() => fn(...args), delay);\n  };\n}\n\n// Usage\nconst handleSearch = debounce((query) => {\n  console.log(\'Searching:\', query);\n}, 500);' },
    { id: 'js-throttle', title: 'Throttle Function', lang: 'javascript', code: 'function throttle(fn, limit = 300) {\n  let inThrottle = false;\n  return (...args) => {\n    if (!inThrottle) {\n      fn(...args);\n      inThrottle = true;\n      setTimeout(() => (inThrottle = false), limit);\n    }\n  };\n}' },
    { id: 'js-deepclone', title: 'Deep Clone', lang: 'javascript', code: 'function deepClone(obj) {\n  if (obj === null || typeof obj !== \'object\') return obj;\n  if (obj instanceof Date) return new Date(obj);\n  if (obj instanceof RegExp) return new RegExp(obj);\n  const clone = Array.isArray(obj) ? [] : {};\n  for (const key of Object.keys(obj)) {\n    clone[key] = deepClone(obj[key]);\n  }\n  return clone;\n}' },
    { id: 'js-fetchwithretry', title: 'Fetch with Retry', lang: 'javascript', code: 'async function fetchWithRetry(url, options = {}, retries = 3) {\n  for (let i = 0; i <= retries; i++) {\n    try {\n      const res = await fetch(url, options);\n      if (!res.ok) throw new Error(`HTTP ${res.status}`);\n      return await res.json();\n    } catch (err) {\n      if (i === retries) throw err;\n      const delay = Math.min(1000 * 2 ** i, 10000);\n      await new Promise(r => setTimeout(r, delay));\n    }\n  }\n}' },
    { id: 'js-groupby', title: 'Group By Key', lang: 'javascript', code: 'function groupBy(arr, key) {\n  return arr.reduce((groups, item) => {\n    const val = typeof key === \'function\' ? key(item) : item[key];\n    (groups[val] ??= []).push(item);\n    return groups;\n  }, {});\n}' },
    { id: 'py-retry', title: 'Retry Decorator', lang: 'python', code: 'import functools\nimport time\n\ndef retry(max_retries=3, delay=1, backoff=2):\n    def decorator(func):\n        @functools.wraps(func)\n        def wrapper(*args, **kwargs):\n            _delay = delay\n            for attempt in range(max_retries + 1):\n                try:\n                    return func(*args, **kwargs)\n                except Exception as e:\n                    if attempt == max_retries:\n                        raise\n                    time.sleep(_delay)\n                    _delay *= backoff\n        return wrapper\n    return decorator' },
    { id: 'py-singleton', title: 'Singleton Pattern', lang: 'python', code: 'class Singleton:\n    _instances = {}\n\n    def __new__(cls, *args, **kwargs):\n        if cls not in cls._instances:\n            cls._instances[cls] = super().__new__(cls)\n        return cls._instances[cls]' },
    { id: 'py-contextmanager', title: 'Context Manager', lang: 'python', code: 'from contextlib import contextmanager\nimport time\n\n@contextmanager\ndef timer(label="Block"):\n    start = time.perf_counter()\n    try:\n        yield\n    finally:\n        elapsed = time.perf_counter() - start\n        print(f"{label}: {elapsed:.4f}s")' },
    { id: 'py-dataclass', title: 'Dataclass with Validation', lang: 'python', code: 'from dataclasses import dataclass, field\nfrom typing import List\n\n@dataclass\nclass Config:\n    host: str = "localhost"\n    port: int = 8080\n    debug: bool = False\n    allowed_origins: List[str] = field(default_factory=list)\n\n    def __post_init__(self):\n        if not 1 <= self.port <= 65535:\n            raise ValueError(f"Invalid port: {self.port}")' },
    { id: 'rs-error', title: 'Custom Error Type', lang: 'rust', code: 'use std::fmt;\n\n#[derive(Debug)]\nenum AppError {\n    NotFound(String),\n    Unauthorized,\n    Internal(String),\n}\n\nimpl fmt::Display for AppError {\n    fn fmt(&self, f: &mut fmt::Formatter<\'_>) -> fmt::Result {\n        match self {\n            Self::NotFound(msg) => write!(f, "Not found: {}", msg),\n            Self::Unauthorized => write!(f, "Unauthorized"),\n            Self::Internal(msg) => write!(f, "Internal error: {}", msg),\n        }\n    }\n}\n\nimpl std::error::Error for AppError {}' },
    { id: 'rs-builder', title: 'Builder Pattern', lang: 'rust', code: '#[derive(Debug)]\nstruct Request {\n    url: String,\n    method: String,\n    headers: Vec<(String, String)>,\n    timeout: u64,\n}\n\nstruct RequestBuilder {\n    url: String,\n    method: String,\n    headers: Vec<(String, String)>,\n    timeout: u64,\n}\n\nimpl RequestBuilder {\n    fn new(url: &str) -> Self {\n        Self { url: url.to_string(), method: "GET".to_string(), headers: vec![], timeout: 30 }\n    }\n    fn method(mut self, m: &str) -> Self { self.method = m.to_string(); self }\n    fn header(mut self, k: &str, v: &str) -> Self { self.headers.push((k.to_string(), v.to_string())); self }\n    fn build(self) -> Request { Request { url: self.url, method: self.method, headers: self.headers, timeout: self.timeout } }\n}' },
    { id: 'sol-erc20', title: 'Minimal ERC-20 Token', lang: 'solidity', code: '// SPDX-License-Identifier: MIT\npragma solidity ^0.8.20;\n\ncontract Token {\n    string public name;\n    string public symbol;\n    uint8 public constant decimals = 18;\n    uint256 public totalSupply;\n    mapping(address => uint256) public balanceOf;\n    mapping(address => mapping(address => uint256)) public allowance;\n\n    event Transfer(address indexed from, address indexed to, uint256 value);\n\n    constructor(string memory _name, string memory _symbol, uint256 _supply) {\n        name = _name;\n        symbol = _symbol;\n        totalSupply = _supply * 10 ** decimals;\n        balanceOf[msg.sender] = totalSupply;\n    }\n\n    function transfer(address to, uint256 amount) external returns (bool) {\n        require(balanceOf[msg.sender] >= amount, "Insufficient balance");\n        balanceOf[msg.sender] -= amount;\n        balanceOf[to] += amount;\n        emit Transfer(msg.sender, to, amount);\n        return true;\n    }\n}' },
  ];

  /* ---------- State ---------- */
  var snippets = [];
  var favorites = new Set();
  var activeFilter = 'all';
  var searchQuery = '';
  var selectedSnippetId = null;

  /* ---------- Load/Save ---------- */
  function loadState() {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        snippets = BUILTIN_SNIPPETS.concat(JSON.parse(saved));
      } else {
        snippets = BUILTIN_SNIPPETS.slice();
      }
    } catch (e) {
      snippets = BUILTIN_SNIPPETS.slice();
    }
    try {
      var savedFavs = localStorage.getItem(FAVS_KEY);
      if (savedFavs) favorites = new Set(JSON.parse(savedFavs));
    } catch (e) {
      favorites = new Set();
    }
  }

  function saveCustomSnippets() {
    var custom = snippets.filter(function (s) { return !BUILTIN_SNIPPETS.find(function (b) { return b.id === s.id; }); });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(custom));
  }

  function saveFavorites() {
    localStorage.setItem(FAVS_KEY, JSON.stringify(Array.from(favorites)));
  }

  /* ---------- Theme ---------- */
  function initTheme() {
    var toggle = document.getElementById('theme-toggle');
    var saved = localStorage.getItem('code-snippets-theme');
    if (saved === 'light') document.documentElement.setAttribute('data-theme', 'light');
    toggle.addEventListener('click', function () {
      var isLight = document.documentElement.getAttribute('data-theme') === 'light';
      if (isLight) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('code-snippets-theme', 'dark');
      } else {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('code-snippets-theme', 'light');
      }
    });
  }

  function initHeroImage() {
    if (!CONFIG.heroImageUrl) return;
    var el = document.querySelector('.hero__bg-image');
    if (el) el.style.backgroundImage = 'url(' + CONFIG.heroImageUrl + ')';
  }

  /* ---------- Toast ---------- */
  function showToast(msg) {
    var toast = document.getElementById('toast');
    var text = document.getElementById('toast-text');
    if (!toast || !text) return;
    text.textContent = msg;
    toast.hidden = false;
    toast.classList.add('show');
    setTimeout(function () {
      toast.classList.remove('show');
      setTimeout(function () { toast.hidden = true; }, 300);
    }, 2000);
  }

  /* ---------- Copy ---------- */
  async function copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      showToast('Copied to clipboard');
    } catch (e) {
      var textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      showToast('Copied to clipboard');
    }
  }

  /* ---------- Helpers ---------- */
  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function getFilteredSnippets() {
    var filtered = snippets;
    if (activeFilter !== 'all') {
      filtered = filtered.filter(function (s) { return s.lang === activeFilter; });
    }
    if (searchQuery) {
      var q = searchQuery.toLowerCase();
      filtered = filtered.filter(function (s) {
        return s.title.toLowerCase().indexOf(q) !== -1 || s.code.toLowerCase().indexOf(q) !== -1 || s.lang.toLowerCase().indexOf(q) !== -1;
      });
    }
    return filtered;
  }

  function getLanguages() {
    var langs = new Set(snippets.map(function (s) { return s.lang; }));
    return ['all'].concat(Array.from(langs).sort());
  }

  /* ---------- Update Stats ---------- */
  function updateHeroStats() {
    var totalEl = document.getElementById('stat-total');
    var langsEl = document.getElementById('stat-langs');
    if (totalEl) totalEl.textContent = snippets.length;
    if (langsEl) langsEl.textContent = new Set(snippets.map(function (s) { return s.lang; })).size;
  }

  /* ---------- Render Filter Bar ---------- */
  function renderFilterBar() {
    var bar = document.getElementById('filter-bar');
    if (!bar) return;
    var languages = getLanguages();
    bar.innerHTML = languages.map(function (lang) {
      return '<button class="filter-tab ' + (lang === activeFilter ? 'filter-tab--active' : '') + '" data-lang="' + lang + '" type="button">' + (lang === 'all' ? 'All' : lang) + '</button>';
    }).join('');
    bar.querySelectorAll('.filter-tab').forEach(function (tab) {
      tab.addEventListener('click', function () {
        activeFilter = tab.dataset.lang;
        renderFilterBar();
        renderSnippetList();
      });
    });
  }

  /* ---------- Render Snippet List (Left Panel) ---------- */
  function renderSnippetList() {
    var list = document.getElementById('snippets-grid');
    if (!list) return;
    var filtered = getFilteredSnippets();

    if (filtered.length === 0) {
      list.innerHTML = '<div style="padding: var(--space-m); text-align: center; color: var(--color-text-muted); font-size: var(--text-sm);">No snippets found' + (searchQuery ? ' for "' + escapeHtml(searchQuery) + '"' : '') + '.</div>';
      return;
    }

    list.innerHTML = filtered.map(function (s) {
      var isFav = favorites.has(s.id);
      var isActive = s.id === selectedSnippetId;
      return '<div class="snippet-item ' + (isActive ? 'snippet-item--active' : '') + '" data-id="' + s.id + '">' +
        '<div class="snippet-item__title">' + escapeHtml(s.title) + '</div>' +
        '<div class="snippet-item__meta">' +
          '<span class="snippet-item__lang">' + s.lang + '</span>' +
          (isFav ? '<span class="snippet-item__fav">★</span>' : '') +
        '</div>' +
      '</div>';
    }).join('');

    /* Click handlers */
    list.querySelectorAll('.snippet-item').forEach(function (item) {
      item.addEventListener('click', function () {
        selectedSnippetId = item.dataset.id;
        renderSnippetList();
        showPreview(selectedSnippetId);
      });
    });
  }

  /* ---------- Show Preview (Right Panel) ---------- */
  function showPreview(snippetId) {
    var snippet = snippets.find(function (s) { return s.id === snippetId; });
    if (!snippet) return;

    var emptyEl = document.getElementById('preview-empty');
    var contentEl = document.getElementById('preview-content');
    var titleEl = document.getElementById('preview-title');
    var langEl = document.getElementById('preview-lang');
    var codeEl = document.getElementById('preview-code');
    var favBtn = document.getElementById('preview-fav-btn');
    var copyBtn = document.getElementById('preview-copy-btn');

    if (emptyEl) emptyEl.hidden = true;
    if (contentEl) contentEl.hidden = false;
    if (titleEl) titleEl.textContent = snippet.title;
    if (langEl) langEl.textContent = snippet.lang;

    if (codeEl) {
      var highlighted = Prism.highlight(
        snippet.code,
        Prism.languages[snippet.lang] || Prism.languages.javascript,
        snippet.lang
      );
      codeEl.innerHTML = highlighted;
      codeEl.className = 'language-' + snippet.lang;
    }

    /* Fav button */
    if (favBtn) {
      var isFav = favorites.has(snippet.id);
      favBtn.textContent = isFav ? '★' : '☆';
      favBtn.className = 'preview-header__btn preview-header__btn--fav' + (isFav ? ' active' : '');
      favBtn.onclick = function () {
        if (favorites.has(snippet.id)) {
          favorites.delete(snippet.id);
        } else {
          favorites.add(snippet.id);
        }
        saveFavorites();
        renderSnippetList();
        showPreview(snippet.id);
      };
    }

    /* Copy button */
    if (copyBtn) {
      copyBtn.onclick = function () {
        copyToClipboard(snippet.code);
      };
    }

    /* Animate preview entrance */
    if (!prefersReducedMotion) {
      gsap.from(contentEl, { x: 20, opacity: 0, duration: 0.3, ease: 'power2.out' });
    }
  }

  /* ---------- Search ---------- */
  function initSearch() {
    var input = document.getElementById('search-input');
    if (!input) return;
    var debounceTimer;
    input.addEventListener('input', function () {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function () {
        searchQuery = input.value.trim();
        renderSnippetList();
      }, 250);
    });
  }

  /* ---------- Add Form ---------- */
  function initAddForm() {
    var form = document.getElementById('add-form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var title = document.getElementById('snippet-title').value.trim();
      var lang = document.getElementById('snippet-lang').value;
      var code = document.getElementById('snippet-code').value;
      if (!title || !code) return;
      var id = 'custom-' + Date.now();
      snippets.push({ id: id, title: title, lang: lang, code: code });
      saveCustomSnippets();
      form.reset();
      updateHeroStats();
      renderFilterBar();
      renderSnippetList();
      showToast('Snippet added');
    });
  }

  /* ---------- GSAP Animations: D7 translateX(-20px) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    gsap.from('.hero', { opacity: 0, y: -15, duration: 0.5, ease: 'power2.out' });

    gsap.from('.split-screen__left', {
      x: -20, opacity: 0, duration: 0.6, ease: 'power2.out', delay: 0.2,
    });
    gsap.from('.split-screen__right', {
      x: 20, opacity: 0, duration: 0.6, ease: 'power2.out', delay: 0.3,
    });

    gsap.utils.toArray('.snippet-item').forEach(function (item, i) {
      gsap.from(item, {
        x: -20, opacity: 0, duration: 0.4, delay: i * 0.04, ease: 'power2.out',
      });
    });

    gsap.utils.toArray('.section__header').forEach(function (header) {
      gsap.from(header, {
        scrollTrigger: { trigger: header, start: 'top 85%', toggleActions: 'play none none none' },
        x: -20, opacity: 0, duration: 0.6, ease: 'power2.out',
      });
    });
  }

  /* ---------- Main Init ---------- */
  function init() {
    initTheme();
    initHeroImage();
    loadState();
    updateHeroStats();
    renderFilterBar();
    renderSnippetList();
    initSearch();
    initAddForm();
    requestAnimationFrame(function () { initAnimations(); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
