/* ============================================================
   Password Generator — script.js
   Pure frontend · Web Crypto API
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Constants ---------- */
  const HISTORY_KEY = 'pw-gen-history';
  const MAX_HISTORY = 10;

  const CHARSETS = {
    uppercase: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
    lowercase: 'abcdefghijklmnopqrstuvwxyz',
    numbers:   '0123456789',
    symbols:   '!@#$%^&*()_+-=[]{}|;:,.<>?',
  };

  /* ---------- DOM refs ---------- */
  const passwordDisplay = document.getElementById('passwordDisplay');
  const generateBtn     = document.getElementById('generateBtn');
  const copyBtn         = document.getElementById('copyBtn');
  const lengthSlider    = document.getElementById('lengthSlider');
  const lengthValue     = document.getElementById('lengthValue');
  const optUppercase    = document.getElementById('optUppercase');
  const optLowercase    = document.getElementById('optLowercase');
  const optNumbers      = document.getElementById('optNumbers');
  const optSymbols      = document.getElementById('optSymbols');
  const strengthFill    = document.getElementById('strengthFill');
  const strengthLabel   = document.getElementById('strengthLabel');
  const batchBtn        = document.getElementById('batchBtn');
  const batchCount      = document.getElementById('batchCount');
  const batchList       = document.getElementById('batchList');
  const historyList     = document.getElementById('historyList');
  const historyEmpty    = document.getElementById('historyEmpty');
  const clearHistoryBtn = document.getElementById('clearHistoryBtn');
  const themeToggle     = document.getElementById('themeToggle');

  /* ---------- Theme ---------- */
  function initTheme() {
    const saved = localStorage.getItem('pw-theme');
    if (saved) {
      document.documentElement.setAttribute('data-theme', saved);
    } else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    }
  }

  themeToggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('pw-theme', next);
  });

  initTheme();

  /* ---------- Slider ---------- */
  lengthSlider.addEventListener('input', () => {
    lengthValue.textContent = lengthSlider.value;
  });

  /* ---------- Generate password (Web Crypto) ---------- */
  function getCharPool() {
    let pool = '';
    if (optUppercase.checked) pool += CHARSETS.uppercase;
    if (optLowercase.checked) pool += CHARSETS.lowercase;
    if (optNumbers.checked)   pool += CHARSETS.numbers;
    if (optSymbols.checked)   pool += CHARSETS.symbols;
    return pool || CHARSETS.lowercase; // fallback
  }

  function generatePassword(length) {
    const pool = getCharPool();
    const poolLen = pool.length;
    const array = new Uint32Array(length);
    crypto.getRandomValues(array);

    let password = '';
    for (let i = 0; i < length; i++) {
      password += pool[array[i] % poolLen];
    }
    return password;
  }

  /* ---------- Strength calculation ---------- */
  function calcStrength(password) {
    const len = password.length;
    let score = 0;

    // Length contribution
    if (len >= 8)  score += 1;
    if (len >= 12) score += 1;
    if (len >= 16) score += 1;
    if (len >= 24) score += 1;

    // Character variety
    if (/[a-z]/.test(password)) score += 1;
    if (/[A-Z]/.test(password)) score += 1;
    if (/[0-9]/.test(password)) score += 1;
    if (/[^a-zA-Z0-9]/.test(password)) score += 1;

    // Entropy estimate
    let poolSize = 0;
    if (/[a-z]/.test(password)) poolSize += 26;
    if (/[A-Z]/.test(password)) poolSize += 26;
    if (/[0-9]/.test(password)) poolSize += 10;
    if (/[^a-zA-Z0-9]/.test(password)) poolSize += 26;
    const entropy = len * Math.log2(poolSize || 1);
    if (entropy >= 60) score += 1;
    if (entropy >= 80) score += 1;
    if (entropy >= 100) score += 1;

    // Normalize to 0-100
    const pct = Math.min(100, Math.round((score / 11) * 100));

    let level, color;
    if (pct < 30) {
      level = 'Weak';
      color = 'var(--strength-weak)';
    } else if (pct < 55) {
      level = 'Fair';
      color = 'var(--strength-fair)';
    } else if (pct < 80) {
      level = 'Good';
      color = 'var(--strength-good)';
    } else {
      level = 'Strong';
      color = 'var(--strength-strong)';
    }

    return { pct, level, color };
  }

  function updateStrength(password) {
    const { pct, level, color } = calcStrength(password);
    strengthFill.style.width = pct + '%';
    strengthFill.style.backgroundColor = color;
    strengthLabel.textContent = level;
    strengthLabel.style.color = color;
  }

  /* ---------- Generate & display ---------- */
  let currentPassword = '';

  function doGenerate() {
    const len = parseInt(lengthSlider.value, 10);
    currentPassword = generatePassword(len);
    passwordDisplay.textContent = currentPassword;
    updateStrength(currentPassword);
    addToHistory(currentPassword);

    // Flash animation
    passwordDisplay.classList.remove('copy-flash');
    void passwordDisplay.offsetWidth;
    passwordDisplay.classList.add('copy-flash');
  }

  generateBtn.addEventListener('click', doGenerate);

  /* ---------- Copy ---------- */
  async function copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Fallback
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      return true;
    }
  }

  copyBtn.addEventListener('click', async () => {
    if (!currentPassword) return;
    await copyToClipboard(currentPassword);
    passwordDisplay.classList.remove('copy-flash');
    void passwordDisplay.offsetWidth;
    passwordDisplay.classList.add('copy-flash');
  });

  /* ---------- Batch generate ---------- */
  batchBtn.addEventListener('click', () => {
    const count = Math.min(20, Math.max(2, parseInt(batchCount.value, 10) || 5));
    const len = parseInt(lengthSlider.value, 10);
    batchList.innerHTML = '';

    for (let i = 0; i < count; i++) {
      const pw = generatePassword(len);
      const item = document.createElement('div');
      item.className = 'batch-item';
      item.innerHTML = `
        <span>${pw}</span>
        <button class="batch-item__copy" data-pw="${pw}">Copy</button>
      `;
      batchList.appendChild(item);
    }

    // Attach copy handlers
    batchList.querySelectorAll('.batch-item__copy').forEach(btn => {
      btn.addEventListener('click', async () => {
        await copyToClipboard(btn.dataset.pw);
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = 'Copy'; }, 1200);
      });
    });

    // Animate
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!prefersReduced) {
      gsap.fromTo(batchList.children, {
        opacity: 0,
        filter: 'blur(6px)',
      }, {
        opacity: 1,
        filter: 'blur(0px)',
        duration: 0.35,
        stagger: 0.05,
        ease: 'power2.out',
      });
    }
  });

  /* ---------- History (localStorage) ---------- */
  function loadHistory() {
    try {
      const raw = localStorage.getItem(HISTORY_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  function saveHistory(history) {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  }

  function addToHistory(pw) {
    const history = loadHistory();
    history.unshift({
      password: pw,
      time: new Date().toLocaleTimeString(),
    });
    if (history.length > MAX_HISTORY) history.length = MAX_HISTORY;
    saveHistory(history);
    renderHistory();
  }

  function renderHistory() {
    const history = loadHistory();
    historyList.innerHTML = '';

    if (history.length === 0) {
      const empty = document.createElement('p');
      empty.className = 'history-empty';
      empty.textContent = 'No passwords generated yet';
      historyList.appendChild(empty);
      return;
    }

    history.forEach(item => {
      const row = document.createElement('div');
      row.className = 'history-item';
      row.innerHTML = `
        <span class="history-item__pw">${item.password}</span>
        <span class="history-item__time">${item.time}</span>
        <button class="history-item__copy" data-pw="${item.password}">Copy</button>
      `;
      historyList.appendChild(row);
    });

    historyList.querySelectorAll('.history-item__copy').forEach(btn => {
      btn.addEventListener('click', async () => {
        await copyToClipboard(btn.dataset.pw);
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = 'Copy'; }, 1200);
      });
    });
  }

  clearHistoryBtn.addEventListener('click', () => {
    localStorage.removeItem(HISTORY_KEY);
    renderHistory();
  });

  /* ---------- GSAP Animations ---------- */
  function initAnimations() {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) {
      document.querySelectorAll('.gen-panel').forEach(p => {
        p.style.opacity = '1';
        p.style.filter = 'none';
      });
      return;
    }

    gsap.registerPlugin(ScrollTrigger);

    // Hero entrance
    gsap.fromTo('.hero__label', {
      opacity: 0, y: -10,
    }, {
      opacity: 1, y: 0,
      duration: 0.5,
      ease: 'power2.out',
    });

    gsap.fromTo('.hero__heading', {
      opacity: 0, filter: 'blur(8px)',
    }, {
      opacity: 1, filter: 'blur(0px)',
      duration: 0.7,
      delay: 0.15,
      ease: 'power2.out',
    });

    gsap.fromTo('#heroPasswordBox', {
      opacity: 0, filter: 'blur(8px)',
    }, {
      opacity: 1, filter: 'blur(0px)',
      duration: 0.6,
      delay: 0.3,
      ease: 'power2.out',
    });

    gsap.fromTo('.strength-bar', {
      opacity: 0,
    }, {
      opacity: 1,
      duration: 0.4,
      delay: 0.5,
      ease: 'power2.out',
    });

    // Panels: D13 blur entrance
    document.querySelectorAll('.main-col > .gen-panel').forEach((panel, i) => {
      gsap.fromTo(panel, {
        opacity: 0,
        filter: 'blur(8px)',
      }, {
        opacity: 1,
        filter: 'blur(0px)',
        duration: 0.6,
        delay: 0.1 * i,
        ease: 'power2.out',
        scrollTrigger: {
          trigger: panel,
          start: 'top 85%',
          once: true,
        },
      });
    });
  }

  /* ---------- Init ---------- */
  function init() {
    renderHistory();
    initAnimations();
    // Auto-generate first password
    doGenerate();
  }

  init();
})();
