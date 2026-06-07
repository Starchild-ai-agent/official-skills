/* ============================================================
   Unit Converter — script.js
   Skeleton: A11 Centered · Hover: C1 translateY(-3px)
   Entrance: D5 opacity · Hero: H15 Interactive
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Unit Data ---------- */
  const UNITS = {
    length: {
      label: 'Length',
      units: {
        m: { name: 'Meter', factor: 1 },
        km: { name: 'Kilometer', factor: 1000 },
        cm: { name: 'Centimeter', factor: 0.01 },
        mm: { name: 'Millimeter', factor: 0.001 },
        mi: { name: 'Mile', factor: 1609.344 },
        yd: { name: 'Yard', factor: 0.9144 },
        ft: { name: 'Foot', factor: 0.3048 },
        in: { name: 'Inch', factor: 0.0254 },
      },
      quick: ['km→mi', 'cm→in', 'ft→m', 'm→yd'],
    },
    weight: {
      label: 'Weight',
      units: {
        kg: { name: 'Kilogram', factor: 1 },
        g: { name: 'Gram', factor: 0.001 },
        mg: { name: 'Milligram', factor: 0.000001 },
        lb: { name: 'Pound', factor: 0.453592 },
        oz: { name: 'Ounce', factor: 0.0283495 },
        t: { name: 'Metric Ton', factor: 1000 },
      },
      quick: ['kg→lb', 'lb→kg', 'oz→g', 'g→oz'],
    },
    temperature: {
      label: 'Temperature',
      units: {
        c: { name: 'Celsius' },
        f: { name: 'Fahrenheit' },
        k: { name: 'Kelvin' },
      },
      quick: ['c→f', 'f→c', 'c→k', 'k→c'],
    },
    currency: {
      label: 'Currency',
      units: {
        usd: { name: 'US Dollar', rate: 1 },
        eur: { name: 'Euro', rate: 0.92 },
        gbp: { name: 'British Pound', rate: 0.79 },
        jpy: { name: 'Japanese Yen', rate: 149.5 },
        cny: { name: 'Chinese Yuan', rate: 7.24 },
        krw: { name: 'Korean Won', rate: 1320 },
        btc: { name: 'Bitcoin', rate: 0.0000156 },
      },
      quick: ['usd→eur', 'usd→cny', 'eur→gbp', 'usd→jpy'],
    },
    data: {
      label: 'Data',
      units: {
        b: { name: 'Byte', factor: 1 },
        kb: { name: 'Kilobyte', factor: 1024 },
        mb: { name: 'Megabyte', factor: 1048576 },
        gb: { name: 'Gigabyte', factor: 1073741824 },
        tb: { name: 'Terabyte', factor: 1099511627776 },
        bit: { name: 'Bit', factor: 0.125 },
      },
      quick: ['gb→mb', 'mb→kb', 'tb→gb', 'gb→tb'],
    },
  };

  let currentCategory = 'length';
  let history = JSON.parse(localStorage.getItem('uc_history') || '[]');

  /* ---------- DOM ---------- */
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);

  const fromValue = $('#fromValue');
  const toValue = $('#toValue');
  const fromUnit = $('#fromUnit');
  const toUnit = $('#toUnit');
  const swapBtn = $('#swapBtn');
  const quickUnits = $('#quickUnits');
  const historyList = $('#historyList');
  const clearHistory = $('#clearHistory');
  const themeToggle = $('#themeToggle');
  const catBtns = $$('.cat-btn');

  /* ---------- Theme ---------- */
  const savedTheme = localStorage.getItem('uc_theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);

  themeToggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('uc_theme', next);
  });

  /* ---------- Category Switch ---------- */
  catBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      catBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      currentCategory = btn.dataset.cat;
      populateUnits();
      convert();
    });
  });

  /* ---------- Populate Units ---------- */
  function populateUnits() {
    const cat = UNITS[currentCategory];
    fromUnit.innerHTML = '';
    toUnit.innerHTML = '';
    const keys = Object.keys(cat.units);
    keys.forEach((k) => {
      const opt1 = new Option(cat.units[k].name + ' (' + k + ')', k);
      const opt2 = new Option(cat.units[k].name + ' (' + k + ')', k);
      fromUnit.add(opt1);
      toUnit.add(opt2);
    });
    if (keys.length > 1) toUnit.selectedIndex = 1;

    quickUnits.innerHTML = '';
    (cat.quick || []).forEach((q) => {
      const btn = document.createElement('button');
      btn.className = 'quick-btn';
      btn.textContent = q;
      btn.addEventListener('click', () => {
        const parts = q.split('→');
        fromUnit.value = parts[0];
        toUnit.value = parts[1];
        convert();
      });
      quickUnits.appendChild(btn);
    });
  }

  /* ---------- Conversion ---------- */
  function convertTemperature(val, from, to) {
    let celsius;
    if (from === 'c') celsius = val;
    else if (from === 'f') celsius = (val - 32) * (5 / 9);
    else celsius = val - 273.15;

    if (to === 'c') return celsius;
    if (to === 'f') return celsius * (9 / 5) + 32;
    return celsius + 273.15;
  }

  function convert() {
    const val = parseFloat(fromValue.value);
    if (isNaN(val)) {
      toValue.value = '';
      return;
    }

    const cat = UNITS[currentCategory];
    const from = fromUnit.value;
    const to = toUnit.value;
    let result;

    if (currentCategory === 'temperature') {
      result = convertTemperature(val, from, to);
    } else if (currentCategory === 'currency') {
      const fromRate = cat.units[from].rate;
      const toRate = cat.units[to].rate;
      result = (val / fromRate) * toRate;
    } else {
      const fromFactor = cat.units[from].factor;
      const toFactor = cat.units[to].factor;
      result = (val * fromFactor) / toFactor;
    }

    var formatted;
    if (result < 0.01 && result > 0) {
      formatted = result.toExponential(4);
    } else {
      formatted = parseFloat(result.toPrecision(8)).toString();
    }
    toValue.value = formatted;

    addHistory(val, from, formatted, to);
  }

  /* ---------- History ---------- */
  function addHistory(fromVal, fromU, toVal, toU) {
    var entry = { from: fromVal + ' ' + fromU, to: toVal + ' ' + toU, ts: Date.now() };
    history.unshift(entry);
    if (history.length > 20) history.pop();
    localStorage.setItem('uc_history', JSON.stringify(history));
    renderHistory();
  }

  function renderHistory() {
    if (history.length === 0) {
      historyList.innerHTML = '<li class="history__empty">No conversions yet</li>';
      return;
    }
    historyList.innerHTML = history
      .slice(0, 10)
      .map(function (h) {
        return '<li class="history__item"><span>' + h.from + '</span><span class="history__item-result">= ' + h.to + '</span></li>';
      })
      .join('');
  }

  clearHistory.addEventListener('click', function () {
    history = [];
    localStorage.setItem('uc_history', JSON.stringify(history));
    renderHistory();
  });

  /* ---------- Swap ---------- */
  swapBtn.addEventListener('click', function () {
    var tmpUnit = fromUnit.value;
    fromUnit.value = toUnit.value;
    toUnit.value = tmpUnit;
    convert();
  });

  /* ---------- Event Listeners ---------- */
  fromValue.addEventListener('input', convert);
  fromUnit.addEventListener('change', convert);
  toUnit.addEventListener('change', convert);

  /* ---------- Init ---------- */
  populateUnits();
  renderHistory();
  convert();

  /* ---------- GSAP Entrance ---------- */
  if (typeof gsap !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);

    var mm = gsap.matchMedia();
    mm.add('(prefers-reduced-motion: no-preference)', function () {
      gsap.from('.hero__badge', { opacity: 0, duration: 0.6, ease: 'power2.out' });
      gsap.from('.hero__title', { opacity: 0, duration: 0.8, delay: 0.1, ease: 'power2.out' });
      gsap.from('.hero__subtitle', { opacity: 0, duration: 0.8, delay: 0.2, ease: 'power2.out' });
      gsap.from('.categories', { opacity: 0, duration: 0.6, delay: 0.3, ease: 'power2.out' });
      gsap.from('.converter', { opacity: 0, duration: 0.8, delay: 0.4, ease: 'power2.out' });
      gsap.from('.history', {
        opacity: 0,
        duration: 0.8,
        scrollTrigger: { trigger: '.history', start: 'top 85%' },
        ease: 'power2.out',
      });
    });
  }
})();
