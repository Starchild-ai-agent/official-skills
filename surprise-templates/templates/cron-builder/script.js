/* ============================================
 * Cron Expression Builder — D30
 * Pure frontend, no API calls
 * ============================================ */

(function () {
  'use strict';

  /* ---------- Theme Toggle ---------- */
  const themeToggle = document.getElementById('themeToggle');
  const root = document.documentElement;

  function setTheme(t) {
    root.setAttribute('data-theme', t);
    localStorage.setItem('cron-theme', t);
  }

  themeToggle.addEventListener('click', () => {
    setTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  });

  const saved = localStorage.getItem('cron-theme');
  if (saved) setTheme(saved);

  /* ---------- State ---------- */
  const state = {
    minute: { type: 'every', value: 0, end: 59, step: 5 },
    hour: { type: 'every', value: 0, end: 23, step: 2 },
    day: { type: 'every', value: 1, end: 31, step: 2 },
    month: { type: 'every', value: 1, end: 12 },
    weekday: { type: 'every', selected: [], start: 0, end: 6 }
  };

  /* ---------- DOM refs ---------- */
  const cronDisplay = document.getElementById('cronDisplay');
  const cronReadable = document.getElementById('cronReadable');
  const copyBtn = document.getElementById('copyBtn');
  const execTableBody = document.getElementById('execTableBody');

  /* ---------- Field type selectors ---------- */
  const fields = ['minute', 'hour', 'day', 'month', 'weekday'];

  fields.forEach(field => {
    const typeSelect = document.getElementById(field + 'Type');
    if (!typeSelect) return;

    typeSelect.addEventListener('change', () => {
      state[field].type = typeSelect.value;
      updateFieldVisibility(field);
      buildExpression();
    });

    // Value inputs
    const valueEl = document.getElementById(field + 'Value');
    const endEl = document.getElementById(field + 'End');
    const stepEl = document.getElementById(field + 'Step');

    if (valueEl) {
      valueEl.addEventListener('input', () => {
        state[field].value = parseInt(valueEl.value) || 0;
        buildExpression();
      });
    }
    if (endEl) {
      endEl.addEventListener('input', () => {
        state[field].end = parseInt(endEl.value) || 0;
        buildExpression();
      });
    }
    if (stepEl) {
      stepEl.addEventListener('input', () => {
        state[field].step = parseInt(stepEl.value) || 1;
        buildExpression();
      });
    }
  });

  /* ---------- Weekday buttons ---------- */
  const weekdayBtns = document.querySelectorAll('.weekday-btn');
  weekdayBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const day = parseInt(btn.dataset.day);
      const idx = state.weekday.selected.indexOf(day);
      if (idx >= 0) {
        state.weekday.selected.splice(idx, 1);
        btn.classList.remove('active');
      } else {
        state.weekday.selected.push(day);
        btn.classList.add('active');
      }
      state.weekday.selected.sort();
      buildExpression();
    });
  });

  /* Weekday range inputs */
  const weekdayStart = document.getElementById('weekdayStart');
  const weekdayEndEl = document.getElementById('weekdayEnd');
  if (weekdayStart) {
    weekdayStart.addEventListener('change', () => {
      state.weekday.start = parseInt(weekdayStart.value);
      buildExpression();
    });
  }
  if (weekdayEndEl) {
    weekdayEndEl.addEventListener('change', () => {
      state.weekday.end = parseInt(weekdayEndEl.value);
      buildExpression();
    });
  }

  /* ---------- Field visibility ---------- */
  function updateFieldVisibility(field) {
    const type = state[field].type;

    if (field === 'weekday') {
      const grid = document.getElementById('weekdayGrid');
      const range = document.getElementById('weekdayRange');
      if (grid) grid.classList.toggle('field-hidden', type !== 'specific');
      if (range) range.classList.toggle('field-hidden', type !== 'range');
      return;
    }

    const valueEl = document.getElementById(field + 'Value');
    const endEl = document.getElementById(field + 'End');
    const stepEl = document.getElementById(field + 'Step');

    if (valueEl) valueEl.classList.toggle('field-hidden', type === 'every');
    if (endEl) endEl.classList.toggle('field-hidden', type !== 'range');
    if (stepEl) stepEl.classList.toggle('field-hidden', type !== 'step');
  }

  /* ---------- Build expression ---------- */
  function buildFieldPart(field) {
    const s = state[field];
    switch (s.type) {
      case 'every': return '*';
      case 'specific':
        if (field === 'weekday') {
          return s.selected.length > 0 ? s.selected.join(',') : '*';
        }
        return String(s.value);
      case 'range':
        if (field === 'weekday') {
          return s.start + '-' + s.end;
        }
        return s.value + '-' + s.end;
      case 'step':
        return '*/' + s.step;
      default: return '*';
    }
  }

  function buildExpression() {
    const parts = [
      buildFieldPart('minute'),
      buildFieldPart('hour'),
      buildFieldPart('day'),
      buildFieldPart('month'),
      buildFieldPart('weekday')
    ];
    const expr = parts.join(' ');
    cronDisplay.textContent = expr;
    cronReadable.textContent = toReadable(parts);
    computeNextExecutions(parts);
    highlightActivePreset(expr);
  }

  /* ---------- Human readable ---------- */
  const MONTHS = ['', 'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'];
  const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  function toReadable(parts) {
    const [min, hr, dom, mon, dow] = parts;
    let desc = '';

    // Minute
    if (min === '*') {
      desc = 'Every minute';
    } else if (min.startsWith('*/')) {
      desc = 'Every ' + min.slice(2) + ' minutes';
    } else if (min.includes('-')) {
      desc = 'Minutes ' + min;
    } else {
      desc = 'At minute ' + min;
    }

    // Hour
    if (hr !== '*') {
      if (hr.startsWith('*/')) {
        desc += ', every ' + hr.slice(2) + ' hours';
      } else if (hr.includes('-')) {
        desc += ', hours ' + hr;
      } else {
        const h = parseInt(hr);
        const m = min === '*' ? 0 : (min.startsWith('*/') ? 0 : parseInt(min) || 0);
        const ampm = h >= 12 ? 'PM' : 'AM';
        const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
        desc = 'At ' + h12 + ':' + String(m).padStart(2, '0') + ' ' + ampm;
      }
    }

    // Day of month
    if (dom !== '*') {
      if (dom.startsWith('*/')) {
        desc += ', every ' + dom.slice(2) + ' days';
      } else if (dom.includes('-')) {
        desc += ', days ' + dom;
      } else {
        desc += ', on day ' + dom;
      }
    }

    // Month
    if (mon !== '*') {
      if (mon.includes('-')) {
        const [ms, me] = mon.split('-').map(Number);
        desc += ', ' + (MONTHS[ms] || ms) + ' to ' + (MONTHS[me] || me);
      } else {
        const mv = parseInt(mon);
        desc += ', in ' + (MONTHS[mv] || mon);
      }
    }

    // Day of week
    if (dow !== '*') {
      if (dow.includes('-')) {
        const [ds, de] = dow.split('-').map(Number);
        desc += ', ' + (DAYS[ds] || ds) + ' through ' + (DAYS[de] || de);
      } else if (dow.includes(',')) {
        const dayNames = dow.split(',').map(d => DAYS[parseInt(d)] || d);
        desc += ', on ' + dayNames.join(', ');
      } else {
        const dv = parseInt(dow);
        desc += ', on ' + (DAYS[dv] || dow);
      }
    }

    return desc;
  }

  /* ---------- Next executions ---------- */
  function computeNextExecutions(parts) {
    const [minP, hrP, domP, monP, dowP] = parts;
    const results = [];
    const now = new Date();
    let cursor = new Date(now.getTime() + 60000);
    cursor.setSeconds(0, 0);

    let iterations = 0;
    const maxIter = 525600; // 1 year of minutes

    while (results.length < 10 && iterations < maxIter) {
      iterations++;
      const m = cursor.getMinutes();
      const h = cursor.getHours();
      const d = cursor.getDate();
      const mo = cursor.getMonth() + 1;
      const dw = cursor.getDay();

      if (matchField(minP, m) && matchField(hrP, h) &&
          matchField(domP, d) && matchField(monP, mo) &&
          matchField(dowP, dw)) {
        results.push(new Date(cursor));
      }

      cursor = new Date(cursor.getTime() + 60000);
    }

    renderExecutions(results, now);
  }

  function matchField(pattern, value) {
    if (pattern === '*') return true;
    if (pattern.startsWith('*/')) {
      const step = parseInt(pattern.slice(2));
      return value % step === 0;
    }
    if (pattern.includes('-')) {
      const [start, end] = pattern.split('-').map(Number);
      return value >= start && value <= end;
    }
    if (pattern.includes(',')) {
      return pattern.split(',').map(Number).includes(value);
    }
    return parseInt(pattern) === value;
  }

  function renderExecutions(dates, now) {
    execTableBody.innerHTML = '';
    dates.forEach((d, i) => {
      const tr = document.createElement('tr');
      const diff = d - now;
      const relStr = formatRelative(diff);
      tr.innerHTML = `
        <td class="exec-num">${i + 1}</td>
        <td class="exec-date">${d.toLocaleDateString('en-US', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })}</td>
        <td class="exec-time">${d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })}</td>
        <td class="exec-relative">${relStr}</td>
      `;
      execTableBody.appendChild(tr);
    });
  }

  function formatRelative(ms) {
    const mins = Math.floor(ms / 60000);
    if (mins < 60) return 'in ' + mins + ' min';
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return 'in ' + hrs + 'h ' + (mins % 60) + 'm';
    const days = Math.floor(hrs / 24);
    if (days < 30) return 'in ' + days + ' day' + (days > 1 ? 's' : '');
    const months = Math.floor(days / 30);
    return 'in ~' + months + ' month' + (months > 1 ? 's' : '');
  }

  /* ---------- Presets ---------- */
  const presetBtns = document.querySelectorAll('.preset-btn');
  presetBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const cron = btn.dataset.cron;
      applyPreset(cron);
    });
  });

  function applyPreset(expr) {
    const parts = expr.split(' ');
    if (parts.length !== 5) return;

    // Reset state
    const fieldNames = ['minute', 'hour', 'day', 'month', 'weekday'];
    parts.forEach((part, i) => {
      const field = fieldNames[i];
      const typeSelect = document.getElementById(field + 'Type');

      if (part === '*') {
        state[field].type = 'every';
        if (typeSelect) typeSelect.value = 'every';
      } else if (part.startsWith('*/')) {
        state[field].type = 'step';
        state[field].step = parseInt(part.slice(2));
        if (typeSelect) typeSelect.value = 'step';
        const stepEl = document.getElementById(field + 'Step');
        if (stepEl) stepEl.value = state[field].step;
      } else if (part.includes('-')) {
        state[field].type = 'range';
        if (typeSelect) typeSelect.value = 'range';
        const [s, e] = part.split('-').map(Number);
        if (field === 'weekday') {
          state[field].start = s;
          state[field].end = e;
          const ws = document.getElementById('weekdayStart');
          const we = document.getElementById('weekdayEnd');
          if (ws) ws.value = s;
          if (we) we.value = e;
        } else {
          state[field].value = s;
          state[field].end = e;
          const ve = document.getElementById(field + 'Value');
          const ee = document.getElementById(field + 'End');
          if (ve) ve.value = s;
          if (ee) ee.value = e;
        }
      } else if (part.includes(',')) {
        if (field === 'weekday') {
          state[field].type = 'specific';
          state[field].selected = part.split(',').map(Number);
          if (typeSelect) typeSelect.value = 'specific';
          weekdayBtns.forEach(b => {
            const d = parseInt(b.dataset.day);
            b.classList.toggle('active', state[field].selected.includes(d));
          });
        } else {
          state[field].type = 'specific';
          state[field].value = parseInt(part.split(',')[0]);
          if (typeSelect) typeSelect.value = 'specific';
          const ve = document.getElementById(field + 'Value');
          if (ve) ve.value = state[field].value;
        }
      } else {
        state[field].type = 'specific';
        if (field === 'weekday') {
          state[field].selected = [parseInt(part)];
          if (typeSelect) typeSelect.value = 'specific';
          weekdayBtns.forEach(b => {
            const d = parseInt(b.dataset.day);
            b.classList.toggle('active', state[field].selected.includes(d));
          });
        } else {
          state[field].value = parseInt(part);
          if (typeSelect) typeSelect.value = 'specific';
          const ve = document.getElementById(field + 'Value');
          if (ve) ve.value = state[field].value;
        }
      }

      updateFieldVisibility(field);
    });

    buildExpression();
  }

  function highlightActivePreset(expr) {
    presetBtns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.cron === expr);
    });
  }

  /* ---------- Copy ---------- */
  copyBtn.addEventListener('click', () => {
    const text = cronDisplay.textContent;
    navigator.clipboard.writeText(text).then(() => {
      copyBtn.textContent = 'Copied!';
      copyBtn.classList.add('copied');
      setTimeout(() => {
        copyBtn.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          Copy Expression
        `;
        copyBtn.classList.remove('copied');
      }, 2000);
    });
  });

  /* ---------- GSAP Animations ---------- */
  gsap.registerPlugin(ScrollTrigger);

  const mm = gsap.matchMedia();
  mm.add('(prefers-reduced-motion: no-preference)', () => {
    // D4: stagger top-to-bottom
    gsap.from('.hero-interactive .hero-inner > *', {
      y: -30,
      opacity: 0,
      duration: 0.6,
      stagger: 0.12,
      ease: 'power2.out'
    });

    gsap.from('.preset-btn', {
      y: -20,
      opacity: 0,
      duration: 0.4,
      stagger: 0.06,
      ease: 'power2.out',
      scrollTrigger: {
        trigger: '.presets-section',
        start: 'top 85%'
      }
    });

    gsap.from('.field-group', {
      y: -25,
      opacity: 0,
      duration: 0.5,
      stagger: 0.1,
      ease: 'power2.out',
      scrollTrigger: {
        trigger: '.builder-section',
        start: 'top 80%'
      }
    });

    gsap.from('.executions-section', {
      y: -20,
      opacity: 0,
      duration: 0.6,
      ease: 'power2.out',
      scrollTrigger: {
        trigger: '.executions-section',
        start: 'top 85%'
      }
    });
  });

  /* ---------- Init ---------- */
  fields.forEach(f => updateFieldVisibility(f));
  buildExpression();

})();
