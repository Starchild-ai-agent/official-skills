/* ============================================================
   Habit Tracker — script.js
   ============================================================ */
;(function () {
  'use strict';

  /* ---------- Theme Toggle ---------- */
  const themeToggle = document.getElementById('themeToggle');
  const savedTheme = localStorage.getItem('habit-theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);

  themeToggle.addEventListener('click', () => {
    const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('habit-theme', next);
    renderWeeklyChart();
  });

  /* ---------- Date Helpers ---------- */
  function dateKey(d) {
    return d.toISOString().slice(0, 10);
  }

  function getWeekDates() {
    const today = new Date();
    const dayOfWeek = today.getDay();
    const monday = new Date(today);
    monday.setDate(today.getDate() - ((dayOfWeek + 6) % 7));
    const dates = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(monday);
      d.setDate(monday.getDate() + i);
      dates.push(d);
    }
    return dates;
  }

  function getMonthDates() {
    const today = new Date();
    const year = today.getFullYear();
    const month = today.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    // Pad to start on Monday
    const startPad = (firstDay.getDay() + 6) % 7;
    const dates = [];
    for (let i = -startPad; i <= lastDay.getDate() - 1; i++) {
      const d = new Date(year, month, i + 1);
      dates.push(d);
    }
    // Pad to complete last week
    while (dates.length % 7 !== 0) {
      const last = new Date(dates[dates.length - 1]);
      last.setDate(last.getDate() + 1);
      dates.push(last);
    }
    return dates;
  }

  const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  /* ---------- Data Store ---------- */
  let habits = JSON.parse(localStorage.getItem('habit-data')) || [];

  function saveHabits() {
    localStorage.setItem('habit-data', JSON.stringify(habits));
  }

  /* ---------- Render Day Labels ---------- */
  function renderDayLabels() {
    const container = document.getElementById('dayLabels');
    const weekDates = getWeekDates();
    const todayStr = dateKey(new Date());

    container.innerHTML = '<span class="day-label"></span>'; // spacer for habit info column
    weekDates.forEach((d, i) => {
      const label = document.createElement('span');
      label.className = 'day-label' + (dateKey(d) === todayStr ? ' today' : '');
      label.textContent = DAY_NAMES[i];
      container.appendChild(label);
    });
  }

  /* ---------- Render Habit List ---------- */
  function renderHabits() {
    const list = document.getElementById('habitList');
    const empty = document.getElementById('emptyState');
    list.innerHTML = '';

    if (habits.length === 0) {
      empty.classList.remove('hidden');
      updateHeroStats();
      return;
    }
    empty.classList.add('hidden');

    const weekDates = getWeekDates();
    const todayStr = dateKey(new Date());

    habits.forEach((habit, hIndex) => {
      const row = document.createElement('div');
      row.className = 'habit-row';
      row.setAttribute('data-animate', 'alt');

      // Habit info
      const info = document.createElement('div');
      info.className = 'habit-info';
      info.innerHTML = `
        <span class="habit-icon">${habit.icon}</span>
        <div>
          <div class="habit-name">${habit.name}</div>
          <div class="habit-streak">🔥 ${calcStreak(habit)} day streak</div>
        </div>
      `;
      row.appendChild(info);

      // Day cells
      weekDates.forEach(d => {
        const dk = dateKey(d);
        const cell = document.createElement('button');
        cell.className = 'day-cell' + (habit.checks && habit.checks[dk] ? ' checked' : '');
        cell.setAttribute('aria-label', `${habit.name} - ${dk}`);
        cell.addEventListener('click', () => {
          if (!habit.checks) habit.checks = {};
          habit.checks[dk] = !habit.checks[dk];
          saveHabits();
          renderHabits();
          renderHeatmap();
          renderWeeklyChart();
        });
        row.appendChild(cell);
      });

      // Delete button
      const del = document.createElement('button');
      del.className = 'habit-delete';
      del.textContent = '×';
      del.setAttribute('aria-label', 'Delete habit');
      del.addEventListener('click', () => {
        habits.splice(hIndex, 1);
        saveHabits();
        renderHabits();
        renderHeatmap();
        renderWeeklyChart();
      });
      row.appendChild(del);

      list.appendChild(row);
    });

    updateHeroStats();
    animateNewRows();
  }

  function calcStreak(habit) {
    if (!habit.checks) return 0;
    let streak = 0;
    const d = new Date();
    while (true) {
      const dk = dateKey(d);
      if (habit.checks[dk]) {
        streak++;
        d.setDate(d.getDate() - 1);
      } else {
        break;
      }
    }
    return streak;
  }

  /* ---------- Hero Stats ---------- */
  function updateHeroStats() {
    document.getElementById('totalHabits').textContent = habits.length;

    const todayStr = dateKey(new Date());
    let checked = 0;
    habits.forEach(h => {
      if (h.checks && h.checks[todayStr]) checked++;
    });
    const rate = habits.length > 0 ? Math.round((checked / habits.length) * 100) : 0;
    document.getElementById('todayRate').textContent = rate + '%';

    let best = 0;
    habits.forEach(h => {
      const s = calcStreak(h);
      if (s > best) best = s;
    });
    document.getElementById('bestStreak').textContent = best;
  }

  /* ---------- Add Habit ---------- */
  document.getElementById('addForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const input = document.getElementById('habitInput');
    const icon = document.getElementById('habitIcon').value;
    const name = input.value.trim();
    if (!name) return;
    habits.push({ name, icon, checks: {} });
    saveHabits();
    renderHabits();
    renderHeatmap();
    renderWeeklyChart();
    input.value = '';
  });

  /* ---------- Heatmap ---------- */
  function renderHeatmap() {
    const grid = document.getElementById('heatmapGrid');
    grid.innerHTML = '';
    const monthDates = getMonthDates();
    const today = new Date();
    const currentMonth = today.getMonth();

    monthDates.forEach(d => {
      const dk = dateKey(d);
      let count = 0;
      habits.forEach(h => {
        if (h.checks && h.checks[dk]) count++;
      });
      const maxLevel = Math.min(5, habits.length > 0 ? Math.ceil((count / habits.length) * 5) : 0);

      const cell = document.createElement('div');
      cell.className = 'heatmap-cell';
      cell.setAttribute('data-level', String(maxLevel));
      cell.title = `${dk}: ${count}/${habits.length}`;

      if (d.getMonth() !== currentMonth) {
        cell.style.opacity = '0.03';
      }

      grid.appendChild(cell);
    });
  }

  /* ---------- Weekly Chart ---------- */
  let chartInstance = null;

  function renderWeeklyChart() {
    const canvas = document.getElementById('weeklyChart');
    const weekDates = getWeekDates();
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    const labels = weekDates.map((d, i) => DAY_NAMES[i]);
    const data = weekDates.map(d => {
      const dk = dateKey(d);
      let count = 0;
      habits.forEach(h => {
        if (h.checks && h.checks[dk]) count++;
      });
      return count;
    });

    if (chartInstance) chartInstance.destroy();

    chartInstance = new Chart(canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Habits Completed',
          data,
          backgroundColor: isDark ? 'rgba(52, 211, 153, 0.6)' : 'rgba(4, 120, 87, 0.6)',
          borderColor: isDark ? '#34d399' : '#047857',
          borderWidth: 1,
          borderRadius: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              stepSize: 1,
              color: isDark ? '#8aaa98' : '#5a7a6a',
              font: { family: "'Source Code Pro', monospace", size: 11 },
            },
            grid: { color: isDark ? 'rgba(46,74,60,0.4)' : 'rgba(200,221,210,0.6)' },
          },
          x: {
            ticks: {
              color: isDark ? '#8aaa98' : '#5a7a6a',
              font: { family: "'Source Code Pro', monospace", size: 11 },
            },
            grid: { display: false },
          },
        },
      },
    });
  }

  /* ---------- GSAP Animations (D12 alternating) ---------- */
  function animateNewRows() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      document.querySelectorAll('[data-animate]').forEach(el => {
        el.style.opacity = '1';
      });
      return;
    }

    gsap.registerPlugin(ScrollTrigger);

    document.querySelectorAll('[data-animate="alt"]').forEach((el, i) => {
      const xOffset = i % 2 === 0 ? -30 : 30;
      gsap.fromTo(el,
        { opacity: 0, x: xOffset },
        {
          opacity: 1,
          x: 0,
          duration: 0.5,
          delay: i * 0.08,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: el,
            start: 'top 90%',
            once: true,
          },
        }
      );
    });
  }

  function initAnimations() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      document.querySelectorAll('[data-animate]').forEach(el => {
        el.style.opacity = '1';
      });
      return;
    }

    gsap.registerPlugin(ScrollTrigger);

    // Animate non-row elements
    const sections = document.querySelectorAll('.hero-bar, .add-section, .heatmap-section, .chart-section');
    sections.forEach((el, i) => {
      const xOffset = i % 2 === 0 ? -30 : 30;
      gsap.fromTo(el,
        { opacity: 0, x: xOffset },
        {
          opacity: 1,
          x: 0,
          duration: 0.6,
          delay: i * 0.1,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: el,
            start: 'top 90%',
            once: true,
          },
        }
      );
    });
  }

  /* ---------- Init ---------- */
  renderDayLabels();
  renderHabits();
  renderHeatmap();
  renderWeeklyChart();
  initAnimations();
})();
