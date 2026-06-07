/* ============================================================
   Pomodoro Timer — script.js
   ============================================================ */
;(function () {
  'use strict';

  /* ---------- Theme Toggle ---------- */
  const themeToggle = document.getElementById('themeToggle');
  const savedTheme = localStorage.getItem('pomodoro-theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);

  themeToggle.addEventListener('click', () => {
    const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('pomodoro-theme', next);
  });

  /* ---------- Settings ---------- */
  const DEFAULTS = { work: 25, short: 5, long: 15, cycles: 4 };
  let settings = JSON.parse(localStorage.getItem('pomodoro-settings')) || { ...DEFAULTS };

  const settingsOverlay = document.getElementById('settingsOverlay');
  const btnSettings = document.getElementById('btnSettings');
  const settingsClose = document.getElementById('settingsClose');
  const settingsSave = document.getElementById('settingsSave');

  btnSettings.addEventListener('click', () => {
    document.getElementById('settingWork').value = settings.work;
    document.getElementById('settingShort').value = settings.short;
    document.getElementById('settingLong').value = settings.long;
    document.getElementById('settingCycles').value = settings.cycles;
    settingsOverlay.classList.add('open');
  });

  settingsClose.addEventListener('click', () => settingsOverlay.classList.remove('open'));
  settingsOverlay.addEventListener('click', (e) => {
    if (e.target === settingsOverlay) settingsOverlay.classList.remove('open');
  });

  settingsSave.addEventListener('click', () => {
    settings.work = Math.max(1, Math.min(90, parseInt(document.getElementById('settingWork').value) || 25));
    settings.short = Math.max(1, Math.min(30, parseInt(document.getElementById('settingShort').value) || 5));
    settings.long = Math.max(1, Math.min(60, parseInt(document.getElementById('settingLong').value) || 15));
    settings.cycles = Math.max(2, Math.min(10, parseInt(document.getElementById('settingCycles').value) || 4));
    localStorage.setItem('pomodoro-settings', JSON.stringify(settings));
    settingsOverlay.classList.remove('open');
    resetTimer();
  });

  /* ---------- Timer State ---------- */
  let currentMode = 'work'; // 'work' | 'short' | 'long'
  let totalSeconds = settings.work * 60;
  let remainingSeconds = totalSeconds;
  let isRunning = false;
  let intervalId = null;
  let completedPomodoros = 0;
  let pomodoroCount = 0; // count within cycle

  // Today stats
  const todayKey = () => `pomodoro-stats-${new Date().toISOString().slice(0, 10)}`;
  let todayStats = JSON.parse(localStorage.getItem(todayKey())) || { pomodoros: 0, focusMinutes: 0, tasksDone: 0 };

  function saveTodayStats() {
    localStorage.setItem(todayKey(), JSON.stringify(todayStats));
    updateStatsUI();
  }

  function updateStatsUI() {
    document.getElementById('statPomodoros').textContent = todayStats.pomodoros;
    const mins = todayStats.focusMinutes;
    document.getElementById('statFocusTime').textContent = mins >= 60 ? `${Math.floor(mins / 60)}h ${mins % 60}m` : `${mins}m`;
    document.getElementById('statTasks').textContent = todayStats.tasksDone;
  }

  /* ---------- Canvas Drawing ---------- */
  const canvas = document.getElementById('timerCanvas');
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;

  function setupCanvas() {
    const wrapper = canvas.parentElement;
    const size = wrapper.clientWidth;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = size + 'px';
    canvas.style.height = size + 'px';
    ctx.scale(dpr, dpr);
  }

  function drawTimer() {
    const size = canvas.clientWidth;
    const cx = size / 2;
    const cy = size / 2;
    const radius = cx - 16;
    const lineWidth = 8;
    const progress = totalSeconds > 0 ? (totalSeconds - remainingSeconds) / totalSeconds : 0;

    ctx.clearRect(0, 0, size, size);

    // Background ring
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--color-border').trim();
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Progress ring
    if (progress > 0) {
      const startAngle = -Math.PI / 2;
      const endAngle = startAngle + (Math.PI * 2 * progress);
      ctx.beginPath();
      ctx.arc(cx, cy, radius, startAngle, endAngle);
      ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--color-accent').trim();
      ctx.lineWidth = lineWidth;
      ctx.lineCap = 'round';
      ctx.stroke();
    }
  }

  function updateTimerDisplay() {
    const mins = Math.floor(remainingSeconds / 60);
    const secs = remainingSeconds % 60;
    document.getElementById('timerTime').textContent =
      String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');

    const labels = { work: 'FOCUS', short: 'SHORT BREAK', long: 'LONG BREAK' };
    document.getElementById('timerLabel').textContent = labels[currentMode];

    // Update page title
    document.title = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')} — Pomodoro`;

    drawTimer();
  }

  /* ---------- Timer Controls ---------- */
  const btnStart = document.getElementById('btnStart');
  const btnPause = document.getElementById('btnPause');
  const btnReset = document.getElementById('btnReset');
  const btnSkip = document.getElementById('btnSkip');

  function startTimer() {
    if (isRunning) return;
    isRunning = true;
    btnStart.style.display = 'none';
    btnPause.style.display = '';

    intervalId = setInterval(() => {
      remainingSeconds--;
      if (remainingSeconds <= 0) {
        remainingSeconds = 0;
        clearInterval(intervalId);
        isRunning = false;
        btnStart.style.display = '';
        btnPause.style.display = 'none';
        playAlarm();
        onTimerComplete();
      }
      updateTimerDisplay();
    }, 1000);
  }

  function pauseTimer() {
    if (!isRunning) return;
    isRunning = false;
    clearInterval(intervalId);
    btnStart.style.display = '';
    btnPause.style.display = 'none';
  }

  function resetTimer() {
    pauseTimer();
    const durations = { work: settings.work, short: settings.short, long: settings.long };
    totalSeconds = durations[currentMode] * 60;
    remainingSeconds = totalSeconds;
    updateTimerDisplay();
  }

  function skipTimer() {
    pauseTimer();
    onTimerComplete();
  }

  function onTimerComplete() {
    if (currentMode === 'work') {
      todayStats.pomodoros++;
      todayStats.focusMinutes += settings.work;
      pomodoroCount++;
      saveTodayStats();

      if (pomodoroCount >= settings.cycles) {
        pomodoroCount = 0;
        switchMode('long');
      } else {
        switchMode('short');
      }
    } else {
      switchMode('work');
    }
  }

  function switchMode(mode) {
    currentMode = mode;
    // Update tab UI
    document.querySelectorAll('.mode-tab').forEach(tab => {
      tab.classList.toggle('active', tab.dataset.mode === mode);
    });
    resetTimer();
  }

  btnStart.addEventListener('click', startTimer);
  btnPause.addEventListener('click', pauseTimer);
  btnReset.addEventListener('click', resetTimer);
  btnSkip.addEventListener('click', skipTimer);

  // Mode tab clicks
  document.querySelectorAll('.mode-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      switchMode(tab.dataset.mode);
    });
  });

  /* ---------- Web Audio Alarm ---------- */
  function playAlarm() {
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const notes = [880, 1100, 880, 1100];
      notes.forEach((freq, i) => {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = 'sine';
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.3, audioCtx.currentTime + i * 0.2);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + i * 0.2 + 0.18);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start(audioCtx.currentTime + i * 0.2);
        osc.stop(audioCtx.currentTime + i * 0.2 + 0.2);
      });
    } catch (e) {
      // Audio not supported
    }
  }

  /* ---------- Task List ---------- */
  let tasks = JSON.parse(localStorage.getItem('pomodoro-tasks')) || [];

  function saveTasks() {
    localStorage.setItem('pomodoro-tasks', JSON.stringify(tasks));
  }

  function renderTasks() {
    const list = document.getElementById('taskList');
    const empty = document.getElementById('taskEmpty');
    list.innerHTML = '';

    if (tasks.length === 0) {
      empty.classList.remove('hidden');
      return;
    }
    empty.classList.add('hidden');

    tasks.forEach((task, index) => {
      const li = document.createElement('li');
      li.className = 'task-item' + (task.done ? ' completed' : '');

      const checkbox = document.createElement('button');
      checkbox.className = 'task-checkbox';
      checkbox.setAttribute('aria-label', task.done ? 'Mark incomplete' : 'Mark complete');
      checkbox.addEventListener('click', () => {
        tasks[index].done = !tasks[index].done;
        if (tasks[index].done) {
          todayStats.tasksDone++;
          saveTodayStats();
        }
        saveTasks();
        renderTasks();
      });

      const text = document.createElement('span');
      text.className = 'task-text';
      text.textContent = task.text;

      const del = document.createElement('button');
      del.className = 'task-delete';
      del.textContent = '×';
      del.setAttribute('aria-label', 'Delete task');
      del.addEventListener('click', () => {
        tasks.splice(index, 1);
        saveTasks();
        renderTasks();
      });

      li.appendChild(checkbox);
      li.appendChild(text);
      li.appendChild(del);
      list.appendChild(li);
    });
  }

  document.getElementById('taskForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const input = document.getElementById('taskInput');
    const text = input.value.trim();
    if (!text) return;
    tasks.push({ text, done: false });
    saveTasks();
    renderTasks();
    input.value = '';
  });

  /* ---------- GSAP Animations (D5 opacity only) ---------- */
  function initAnimations() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      document.querySelectorAll('[data-animate]').forEach(el => el.classList.add('is-visible'));
      return;
    }

    gsap.registerPlugin(ScrollTrigger);

    document.querySelectorAll('[data-animate="fade"]').forEach(el => {
      gsap.fromTo(el,
        { opacity: 0 },
        {
          opacity: 1,
          duration: 0.8,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: el,
            start: 'top 85%',
            once: true,
            onEnter: () => el.classList.add('is-visible'),
          },
        }
      );
    });
  }

  /* ---------- Resize Handler ---------- */
  let resizeTimeout;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
      setupCanvas();
      drawTimer();
    }, 150);
  });

  /* ---------- Init ---------- */
  setupCanvas();
  updateTimerDisplay();
  updateStatsUI();
  renderTasks();
  initAnimations();
})();
