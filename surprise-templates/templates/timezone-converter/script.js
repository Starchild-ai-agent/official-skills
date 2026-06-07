/* ============================================================
   Timezone Converter — script.js
   Pure frontend · Intl.DateTimeFormat API
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Constants ---------- */
  const STORAGE_KEY = 'tz-converter-zones';
  const QUICK_ZONES = [
    { label: 'New York', tz: 'America/New_York' },
    { label: 'London',   tz: 'Europe/London' },
    { label: 'Tokyo',    tz: 'Asia/Tokyo' },
    { label: 'Shanghai', tz: 'Asia/Shanghai' },
    { label: 'Sydney',   tz: 'Australia/Sydney' },
    { label: 'Dubai',    tz: 'Asia/Dubai' },
    { label: 'Berlin',   tz: 'Europe/Berlin' },
    { label: 'LA',       tz: 'America/Los_Angeles' },
  ];

  const ALL_TIMEZONES = Intl.supportedValuesOf
    ? Intl.supportedValuesOf('timeZone')
    : [
        'America/New_York','America/Chicago','America/Denver','America/Los_Angeles',
        'America/Anchorage','Pacific/Honolulu','America/Sao_Paulo','America/Argentina/Buenos_Aires',
        'Europe/London','Europe/Berlin','Europe/Paris','Europe/Moscow',
        'Asia/Dubai','Asia/Kolkata','Asia/Shanghai','Asia/Tokyo',
        'Asia/Seoul','Asia/Singapore','Australia/Sydney','Pacific/Auckland',
      ];

  /* ---------- State ---------- */
  let selectedZones = loadZones();

  /* ---------- DOM refs ---------- */
  const tzSelect       = document.getElementById('tzSelect');
  const addTzBtn       = document.getElementById('addTzBtn');
  const tzQuick        = document.getElementById('tzQuick');
  const tzGridInner    = document.getElementById('tzGridInner');
  const tzEmpty        = document.getElementById('tzEmpty');
  const diffFrom       = document.getElementById('diffFrom');
  const diffTo         = document.getElementById('diffTo');
  const diffResult     = document.getElementById('diffResult');
  const meetingTime    = document.getElementById('meetingTime');
  const meetingSourceTz = document.getElementById('meetingSourceTz');
  const meetingResults = document.getElementById('meetingResults');
  const heroDigital    = document.getElementById('heroDigital');
  const themeToggle    = document.getElementById('themeToggle');
  const clockCanvas    = document.getElementById('analogClock');

  /* ---------- Theme ---------- */
  function initTheme() {
    const saved = localStorage.getItem('tz-theme');
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
    localStorage.setItem('tz-theme', next);
  });

  initTheme();

  /* ---------- Populate selects ---------- */
  function populateSelect(selectEl, includeEmpty) {
    if (includeEmpty) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'Select a timezone…';
      selectEl.appendChild(opt);
    }
    ALL_TIMEZONES.forEach(tz => {
      const opt = document.createElement('option');
      opt.value = tz;
      opt.textContent = tz.replace(/_/g, ' ');
      selectEl.appendChild(opt);
    });
  }

  populateSelect(tzSelect, true);
  populateSelect(diffFrom, true);
  populateSelect(diffTo, true);
  populateSelect(meetingSourceTz, false);

  /* ---------- Quick buttons ---------- */
  QUICK_ZONES.forEach(q => {
    const btn = document.createElement('button');
    btn.className = 'tz-quick__btn';
    btn.textContent = q.label;
    btn.addEventListener('click', () => addZone(q.tz));
    tzQuick.appendChild(btn);
  });

  /* ---------- Add / Remove zones ---------- */
  addTzBtn.addEventListener('click', () => {
    const val = tzSelect.value;
    if (val) addZone(val);
  });

  function addZone(tz) {
    if (selectedZones.includes(tz)) return;
    selectedZones.push(tz);
    saveZones();
    renderGrid();
    updateMeetingPlanner();
  }

  function removeZone(tz) {
    selectedZones = selectedZones.filter(z => z !== tz);
    saveZones();
    renderGrid();
    updateMeetingPlanner();
  }

  /* ---------- Persistence ---------- */
  function loadZones() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : ['America/New_York', 'Europe/London', 'Asia/Tokyo'];
    } catch {
      return ['America/New_York', 'Europe/London', 'Asia/Tokyo'];
    }
  }

  function saveZones() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(selectedZones));
  }

  /* ---------- Render timezone grid ---------- */
  function renderGrid() {
    tzGridInner.innerHTML = '';
    if (selectedZones.length === 0) {
      tzEmpty.classList.remove('tz-empty--hidden');
      return;
    }
    tzEmpty.classList.add('tz-empty--hidden');

    selectedZones.forEach(tz => {
      const card = document.createElement('div');
      card.className = 'tz-grid-card';
      card.dataset.tz = tz;

      const cityName = tz.split('/').pop().replace(/_/g, ' ');
      const abbr = getTimezoneAbbr(tz);
      const { time, date } = getFormattedTime(tz);

      card.innerHTML = `
        <button class="tz-grid-card__remove" data-tz="${tz}" title="Remove">&times;</button>
        <div class="tz-grid-card__name">${cityName}</div>
        <div class="tz-grid-card__abbr">${abbr}</div>
        <div class="tz-grid-card__time">${time}</div>
        <div class="tz-grid-card__date">${date}</div>
      `;

      card.querySelector('.tz-grid-card__remove').addEventListener('click', (e) => {
        e.stopPropagation();
        removeZone(tz);
      });

      tzGridInner.appendChild(card);
    });

    // Animate new cards
    animateCards();
  }

  function getTimezoneAbbr(tz) {
    try {
      const parts = new Intl.DateTimeFormat('en-US', {
        timeZone: tz,
        timeZoneName: 'short',
      }).formatToParts(new Date());
      const tzPart = parts.find(p => p.type === 'timeZoneName');
      return tzPart ? tzPart.value : '';
    } catch {
      return '';
    }
  }

  function getFormattedTime(tz) {
    const now = new Date();
    const time = new Intl.DateTimeFormat('en-US', {
      timeZone: tz,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(now);

    const date = new Intl.DateTimeFormat('en-US', {
      timeZone: tz,
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    }).format(now);

    return { time, date };
  }

  /* ---------- Update grid times (live) ---------- */
  function updateGridTimes() {
    const cards = tzGridInner.querySelectorAll('.tz-grid-card');
    cards.forEach(card => {
      const tz = card.dataset.tz;
      if (!tz) return;
      const { time, date } = getFormattedTime(tz);
      const timeEl = card.querySelector('.tz-grid-card__time');
      const dateEl = card.querySelector('.tz-grid-card__date');
      if (timeEl) timeEl.textContent = time;
      if (dateEl) dateEl.textContent = date;
    });
  }

  /* ---------- Hero digital clock ---------- */
  function updateHeroDigital() {
    const now = new Date();
    const h = String(now.getHours()).padStart(2, '0');
    const m = String(now.getMinutes()).padStart(2, '0');
    const s = String(now.getSeconds()).padStart(2, '0');
    heroDigital.textContent = `${h}:${m}:${s}`;
  }

  /* ---------- Analog Clock (Canvas) ---------- */
  function drawAnalogClock() {
    const canvas = clockCanvas;
    const dpr = window.devicePixelRatio || 1;
    const displaySize = Math.min(canvas.parentElement.clientWidth, 280);
    canvas.style.width = displaySize + 'px';
    canvas.style.height = displaySize + 'px';
    canvas.width = displaySize * dpr;
    canvas.height = displaySize * dpr;

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const cx = displaySize / 2;
    const cy = displaySize / 2;
    const r = displaySize / 2 - 10;

    const styles = getComputedStyle(document.documentElement);
    const faceBg = styles.getPropertyValue('--clock-face').trim();
    const markColor = styles.getPropertyValue('--clock-marks').trim();
    const handColor = styles.getPropertyValue('--clock-hands').trim();
    const accentColor = styles.getPropertyValue('--clock-accent').trim();

    // Clear
    ctx.clearRect(0, 0, displaySize, displaySize);

    // Face
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = faceBg;
    ctx.fill();
    ctx.strokeStyle = markColor;
    ctx.lineWidth = 2;
    ctx.stroke();

    // Hour marks
    for (let i = 0; i < 12; i++) {
      const angle = (i * Math.PI) / 6 - Math.PI / 2;
      const inner = r - 18;
      const outer = r - 6;
      ctx.beginPath();
      ctx.moveTo(cx + inner * Math.cos(angle), cy + inner * Math.sin(angle));
      ctx.lineTo(cx + outer * Math.cos(angle), cy + outer * Math.sin(angle));
      ctx.strokeStyle = markColor;
      ctx.lineWidth = i % 3 === 0 ? 3 : 1.5;
      ctx.stroke();
    }

    // Minute marks
    for (let i = 0; i < 60; i++) {
      if (i % 5 === 0) continue;
      const angle = (i * Math.PI) / 30 - Math.PI / 2;
      const inner = r - 10;
      const outer = r - 6;
      ctx.beginPath();
      ctx.moveTo(cx + inner * Math.cos(angle), cy + inner * Math.sin(angle));
      ctx.lineTo(cx + outer * Math.cos(angle), cy + outer * Math.sin(angle));
      ctx.strokeStyle = markColor;
      ctx.lineWidth = 0.5;
      ctx.globalAlpha = 0.4;
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    const now = new Date();
    const h = now.getHours() % 12;
    const m = now.getMinutes();
    const s = now.getSeconds();
    const ms = now.getMilliseconds();

    // Hour hand
    const hAngle = ((h + m / 60) * Math.PI) / 6 - Math.PI / 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + (r * 0.5) * Math.cos(hAngle), cy + (r * 0.5) * Math.sin(hAngle));
    ctx.strokeStyle = handColor;
    ctx.lineWidth = 4;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Minute hand
    const mAngle = ((m + s / 60) * Math.PI) / 30 - Math.PI / 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + (r * 0.7) * Math.cos(mAngle), cy + (r * 0.7) * Math.sin(mAngle));
    ctx.strokeStyle = handColor;
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Second hand
    const sAngle = ((s + ms / 1000) * Math.PI) / 30 - Math.PI / 2;
    ctx.beginPath();
    ctx.moveTo(cx - 15 * Math.cos(sAngle), cy - 15 * Math.sin(sAngle));
    ctx.lineTo(cx + (r * 0.8) * Math.cos(sAngle), cy + (r * 0.8) * Math.sin(sAngle));
    ctx.strokeStyle = accentColor;
    ctx.lineWidth = 1.2;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Center dot
    ctx.beginPath();
    ctx.arc(cx, cy, 4, 0, Math.PI * 2);
    ctx.fillStyle = accentColor;
    ctx.fill();
  }

  /* ---------- Time Difference Calculator ---------- */
  function getUtcOffset(tz) {
    const now = new Date();
    const utcStr = now.toLocaleString('en-US', { timeZone: 'UTC' });
    const tzStr = now.toLocaleString('en-US', { timeZone: tz });
    const utcDate = new Date(utcStr);
    const tzDate = new Date(tzStr);
    return (tzDate - utcDate) / (1000 * 60); // minutes
  }

  function updateDiffCalc() {
    const from = diffFrom.value;
    const to = diffTo.value;
    if (!from || !to) {
      diffResult.textContent = 'Select two timezones';
      return;
    }
    const fromOffset = getUtcOffset(from);
    const toOffset = getUtcOffset(to);
    const diffMinutes = toOffset - fromOffset;
    const hours = Math.floor(Math.abs(diffMinutes) / 60);
    const mins = Math.abs(diffMinutes) % 60;
    const sign = diffMinutes >= 0 ? '+' : '-';
    const fromCity = from.split('/').pop().replace(/_/g, ' ');
    const toCity = to.split('/').pop().replace(/_/g, ' ');
    let text = `${toCity} is ${sign}${hours}h`;
    if (mins > 0) text += ` ${mins}m`;
    text += ` from ${fromCity}`;
    diffResult.textContent = text;
  }

  diffFrom.addEventListener('change', updateDiffCalc);
  diffTo.addEventListener('change', updateDiffCalc);

  /* ---------- Meeting Planner ---------- */
  function updateMeetingPlanner() {
    meetingResults.innerHTML = '';
    const timeVal = meetingTime.value;
    const sourceTz = meetingSourceTz.value;
    if (!timeVal || !sourceTz || selectedZones.length === 0) return;

    const [hh, mm] = timeVal.split(':').map(Number);

    // Create a date in the source timezone
    const now = new Date();
    const sourceStr = now.toLocaleDateString('en-CA', { timeZone: sourceTz }); // YYYY-MM-DD
    const sourceDate = new Date(`${sourceStr}T${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}:00`);

    // Adjust for source timezone offset
    const sourceOffset = getUtcOffset(sourceTz);
    const localOffset = now.getTimezoneOffset() * -1; // local offset in minutes
    const adjustMs = (localOffset - sourceOffset) * 60 * 1000;
    const meetingUtc = new Date(sourceDate.getTime() + adjustMs);

    selectedZones.forEach(tz => {
      const converted = new Intl.DateTimeFormat('en-US', {
        timeZone: tz,
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }).format(meetingUtc);

      const convertedHour = parseInt(converted.split(':')[0], 10);
      const cityName = tz.split('/').pop().replace(/_/g, ' ');

      const row = document.createElement('div');
      row.className = 'meeting-row';

      // Mark off-hours and sleep hours
      if (convertedHour < 7 || convertedHour >= 22) {
        row.classList.add('meeting-row--sleep');
      } else if (convertedHour < 9 || convertedHour >= 18) {
        row.classList.add('meeting-row--off-hours');
      }

      row.innerHTML = `
        <span class="meeting-row__tz">${cityName}</span>
        <span class="meeting-row__time">${converted}</span>
      `;
      meetingResults.appendChild(row);
    });
  }

  meetingTime.addEventListener('input', updateMeetingPlanner);
  meetingSourceTz.addEventListener('change', updateMeetingPlanner);

  /* ---------- GSAP Animations ---------- */
  function animateCards() {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) {
      document.querySelectorAll('.panel').forEach(p => {
        p.style.opacity = '1';
        p.style.transform = 'none';
      });
      return;
    }

    gsap.registerPlugin(ScrollTrigger);

    // Hero entrance
    gsap.fromTo('.hero__clock-wrap', {
      scale: 0.95,
      opacity: 0,
    }, {
      scale: 1,
      opacity: 1,
      duration: 0.8,
      ease: 'power2.out',
    });

    gsap.fromTo('.hero__text', {
      y: 20,
      opacity: 0,
    }, {
      y: 0,
      opacity: 1,
      duration: 0.7,
      delay: 0.2,
      ease: 'power2.out',
    });

    // Panels: D9 scale(0.95) entrance
    document.querySelectorAll('.panel').forEach((panel, i) => {
      gsap.fromTo(panel, {
        scale: 0.95,
        opacity: 0,
      }, {
        scale: 1,
        opacity: 1,
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

    // Grid cards stagger
    const gridCards = document.querySelectorAll('.tz-grid-card');
    if (gridCards.length > 0) {
      gsap.fromTo(gridCards, {
        scale: 0.95,
        opacity: 0,
      }, {
        scale: 1,
        opacity: 1,
        duration: 0.4,
        stagger: 0.06,
        ease: 'power2.out',
      });
    }
  }

  /* ---------- Main tick loop ---------- */
  function tick() {
    drawAnalogClock();
    updateHeroDigital();
    updateGridTimes();
    requestAnimationFrame(tick);
  }

  /* ---------- Init ---------- */
  function init() {
    renderGrid();
    updateMeetingPlanner();
    tick();
  }

  init();
})();
