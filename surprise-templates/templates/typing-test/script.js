/* ============================================
 * Typing Speed Test — D26
 * Pure frontend, localStorage persistence
 * ============================================ */

(function () {
  'use strict';

  /* ---------- Text Pools ---------- */
  const TEXT_POOLS = {
    text: [
      'The quick brown fox jumps over the lazy dog near the riverbank while the sun sets behind the mountains casting golden light across the valley below',
      'Programming is the art of telling another human what one wants the computer to do and the beauty lies in the simplicity of well written code',
      'Every great developer you know got there by solving problems they were unqualified to solve until they actually did it and learned from the process',
      'The best way to predict the future is to invent it and the best way to invent it is to start building something meaningful today',
      'In the middle of difficulty lies opportunity and those who embrace challenges with determination often discover their greatest strengths along the way',
      'Technology is best when it brings people together and creates connections that would otherwise be impossible across vast distances and different cultures',
    ],
    code: [
      'function fibonacci(n) { if (n <= 1) return n; return fibonacci(n - 1) + fibonacci(n - 2); }',
      'const arr = [1, 2, 3, 4, 5]; const sum = arr.reduce((acc, val) => acc + val, 0); console.log(sum);',
      'class Node { constructor(val) { this.val = val; this.next = null; } } let head = new Node(1);',
      'async function fetchData(url) { const res = await fetch(url); const data = await res.json(); return data; }',
      'const map = new Map(); map.set("key", "value"); for (const [k, v] of map) { console.log(k, v); }',
    ],
    numbers: [
      '3141 5926 5358 9793 2384 6264 3383 2795 0288 4197 1693 9937 5105 8209 7494 4592',
      '2718 2818 2845 9045 2353 6028 7471 3526 6249 7757 2470 9369 9959 5749 6696 7627',
      '1618 0339 8874 9894 8482 0458 6834 3656 3811 7720 3091 7980 5762 8621 3544 8623',
      '1414 2135 6237 3095 0488 0168 8724 2096 9807 8569 6718 7537 6948 0731 7667 9737',
    ],
  };

  /* ---------- DOM ---------- */
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);

  const textDisplay = $('#textDisplay');
  const typingInput = $('#typingInput');
  const restartBtn = $('#restartBtn');
  const themeToggle = $('#themeToggle');
  const historyList = $('#historyList');

  /* ---------- State ---------- */
  let currentText = '';
  let currentMode = 'text';
  let selectedTime = 15;
  let timer = null;
  let startTime = null;
  let elapsed = 0;
  let isRunning = false;
  let isFinished = false;
  let correctChars = 0;
  let totalTyped = 0;
  let charIndex = 0;

  /* ---------- Theme ---------- */
  function initTheme() {
    const saved = localStorage.getItem('typing-test-theme');
    if (saved) {
      document.documentElement.setAttribute('data-theme', saved);
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  }

  themeToggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('typing-test-theme', next);
  });

  /* ---------- Text Generation ---------- */
  function getRandomText(mode) {
    const pool = TEXT_POOLS[mode] || TEXT_POOLS.text;
    const shuffled = [...pool].sort(() => Math.random() - 0.5);
    let result = shuffled.join(' ');
    // Ensure enough text for long tests
    while (result.length < 600) {
      result += ' ' + pool[Math.floor(Math.random() * pool.length)];
    }
    return result;
  }

  /* ---------- Render Text ---------- */
  function renderText() {
    textDisplay.innerHTML = '';
    for (let i = 0; i < currentText.length; i++) {
      const span = document.createElement('span');
      span.className = 'char' + (i === 0 ? ' current' : '');
      span.textContent = currentText[i];
      textDisplay.appendChild(span);
    }
  }

  /* ---------- Update Stats ---------- */
  function updateStats() {
    const wpm = elapsed > 0 ? Math.round((correctChars / 5) / (elapsed / 60)) : 0;
    const accuracy = totalTyped > 0 ? Math.round((correctChars / totalTyped) * 100) : 100;

    $('#statWpm .stat-value').textContent = wpm;
    $('#statAccuracy .stat-value').textContent = accuracy;
    $('#statTime .stat-value').textContent = Math.floor(elapsed);
    $('#statChars .stat-value').textContent = correctChars;
  }

  /* ---------- Timer ---------- */
  function startTimer() {
    if (isRunning) return;
    isRunning = true;
    startTime = Date.now();
    timer = setInterval(() => {
      elapsed = (Date.now() - startTime) / 1000;
      updateStats();
      if (elapsed >= selectedTime) {
        finishTest();
      }
    }, 100);
  }

  function finishTest() {
    isRunning = false;
    isFinished = true;
    clearInterval(timer);
    typingInput.disabled = true;
    elapsed = selectedTime;
    updateStats();
    saveResult();
    renderHistory();
  }

  /* ---------- Input Handler ---------- */
  function handleInput() {
    if (isFinished) return;
    if (!isRunning) startTimer();

    const inputVal = typingInput.value;
    const chars = $$('.char');
    charIndex = inputVal.length;
    correctChars = 0;
    totalTyped = inputVal.length;

    for (let i = 0; i < currentText.length; i++) {
      const charEl = chars[i];
      if (!charEl) break;
      charEl.classList.remove('correct', 'incorrect', 'current');

      if (i < inputVal.length) {
        if (inputVal[i] === currentText[i]) {
          charEl.classList.add('correct');
          correctChars++;
        } else {
          charEl.classList.add('incorrect');
        }
      } else if (i === inputVal.length) {
        charEl.classList.add('current');
      }
    }

    // Auto-scroll text display if needed
    if (chars[charIndex]) {
      chars[charIndex].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }

    // If typed all text, finish
    if (inputVal.length >= currentText.length) {
      finishTest();
    }

    updateStats();
  }

  typingInput.addEventListener('input', handleInput);

  /* ---------- Controls ---------- */
  $$('.time-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      $$('.time-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      selectedTime = parseInt(btn.dataset.time, 10);
      resetTest();
    });
  });

  $$('.mode-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      $$('.mode-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      currentMode = btn.dataset.mode;
      resetTest();
    });
  });

  restartBtn.addEventListener('click', resetTest);

  /* ---------- Reset ---------- */
  function resetTest() {
    clearInterval(timer);
    isRunning = false;
    isFinished = false;
    elapsed = 0;
    correctChars = 0;
    totalTyped = 0;
    charIndex = 0;
    startTime = null;
    typingInput.value = '';
    typingInput.disabled = false;
    currentText = getRandomText(currentMode);
    renderText();
    updateStats();
    typingInput.focus();
  }

  /* ---------- History (localStorage) ---------- */
  function getHistory() {
    try {
      return JSON.parse(localStorage.getItem('typing-test-history') || '[]');
    } catch {
      return [];
    }
  }

  function saveResult() {
    const wpm = elapsed > 0 ? Math.round((correctChars / 5) / (elapsed / 60)) : 0;
    const accuracy = totalTyped > 0 ? Math.round((correctChars / totalTyped) * 100) : 100;
    const history = getHistory();
    history.push({
      wpm,
      accuracy,
      mode: currentMode,
      time: selectedTime,
      date: new Date().toISOString(),
    });
    // Keep last 50
    if (history.length > 50) history.splice(0, history.length - 50);
    localStorage.setItem('typing-test-history', JSON.stringify(history));
  }

  function renderHistory() {
    const history = getHistory();
    historyList.innerHTML = '';

    if (history.length === 0) {
      historyList.innerHTML = '<p style="color:var(--text-muted);font-size:0.85rem;">No history yet. Complete a test to see results.</p>';
      return;
    }

    const recent = history.slice(-10).reverse();
    recent.forEach((item) => {
      const div = document.createElement('div');
      div.className = 'history-item';
      const d = new Date(item.date);
      div.innerHTML = `
        <span>${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        <span class="hi-wpm">${item.wpm} WPM</span>
        <span class="hi-acc">${item.accuracy}%</span>
        <span class="hi-mode">${item.mode} · ${item.time}s</span>
      `;
      historyList.appendChild(div);
    });

    renderChart(history);
  }

  /* ---------- Chart ---------- */
  let chartInstance = null;

  function renderChart(history) {
    const ctx = document.getElementById('historyChart');
    if (!ctx) return;

    if (chartInstance) chartInstance.destroy();

    const last20 = history.slice(-20);
    const labels = last20.map((_, i) => `#${history.length - last20.length + i + 1}`);
    const wpmData = last20.map((h) => h.wpm);
    const accData = last20.map((h) => h.accuracy);

    const accentColor = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim();
    const correctColor = getComputedStyle(document.documentElement).getPropertyValue('--correct').trim();

    chartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'WPM',
            data: wpmData,
            borderColor: accentColor,
            backgroundColor: accentColor + '22',
            fill: true,
            tension: 0.3,
            pointRadius: 3,
            pointHoverRadius: 5,
          },
          {
            label: 'Accuracy %',
            data: accData,
            borderColor: correctColor,
            backgroundColor: 'transparent',
            borderDash: [4, 4],
            tension: 0.3,
            pointRadius: 2,
            pointHoverRadius: 4,
            yAxisID: 'y1',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            labels: {
              color: getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim(),
              font: { family: "'Figtree', sans-serif", size: 12 },
            },
          },
        },
        scales: {
          x: {
            ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim(), font: { size: 10 } },
            grid: { display: false },
          },
          y: {
            position: 'left',
            title: { display: true, text: 'WPM', color: accentColor, font: { size: 11 } },
            ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim() },
            grid: { color: getComputedStyle(document.documentElement).getPropertyValue('--border-light').trim() },
          },
          y1: {
            position: 'right',
            min: 0,
            max: 100,
            title: { display: true, text: 'Accuracy', color: correctColor, font: { size: 11 } },
            ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim() },
            grid: { display: false },
          },
        },
      },
    });
  }

  /* ---------- GSAP Entrance ---------- */
  function initAnimations() {
    gsap.registerPlugin(ScrollTrigger);

    gsap.to('.hero-section', {
      opacity: 1,
      scale: 1,
      duration: 0.7,
      ease: 'power2.out',
      delay: 0.15,
    });

    gsap.to('.history-section', {
      opacity: 1,
      scale: 1,
      duration: 0.6,
      ease: 'power2.out',
      scrollTrigger: {
        trigger: '.history-section',
        start: 'top 85%',
      },
    });

    gsap.from('.stat-card', {
      y: 16,
      opacity: 0,
      duration: 0.5,
      stagger: 0.08,
      ease: 'power2.out',
      delay: 0.4,
    });
  }

  /* ---------- Init ---------- */
  initTheme();
  resetTest();
  renderHistory();
  initAnimations();
})();
