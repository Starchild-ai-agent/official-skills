/* ============================================================
   API Playground — script.js

   Skeleton: A3 Split Screen
   Hover: C15 左侧边框+背景
   Entrance: D7 translateX(-20px)
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var history = [];

  /* ---------- Theme Toggle ---------- */
  var themeToggle = document.getElementById('theme-toggle');
  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('apg-theme', theme);
  }
  themeToggle.addEventListener('click', function () {
    var current = document.documentElement.getAttribute('data-theme') || 'dark';
    setTheme(current === 'dark' ? 'light' : 'dark');
  });
  var savedTheme = localStorage.getItem('apg-theme') ||
    (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  setTheme(savedTheme);

  /* ---------- Tab Switching ---------- */
  document.querySelectorAll('.request-tab').forEach(function (tab) {
    tab.addEventListener('click', function () {
      document.querySelectorAll('.request-tab').forEach(function (t) { t.classList.remove('active'); });
      tab.classList.add('active');
      var target = tab.getAttribute('data-tab');
      document.getElementById('tab-headers').classList.toggle('hidden', target !== 'headers');
      document.getElementById('tab-body').classList.toggle('hidden', target !== 'body');
    });
  });

  /* ---------- Add Header Row ---------- */
  document.getElementById('add-header').addEventListener('click', function () {
    var editor = document.getElementById('headers-editor');
    var row = document.createElement('div');
    row.className = 'kv-row';
    row.innerHTML = '<input class="kv-row__key" type="text" placeholder="Key" />' +
      '<input class="kv-row__value" type="text" placeholder="Value" />' +
      '<button class="kv-row__remove" type="button" aria-label="Remove">&times;</button>';
    editor.appendChild(row);
    row.querySelector('.kv-row__remove').addEventListener('click', function () {
      row.remove();
    });
  });

  /* Remove existing header rows */
  document.querySelectorAll('.kv-row__remove').forEach(function (btn) {
    btn.addEventListener('click', function () {
      btn.closest('.kv-row').remove();
    });
  });

  /* ---------- Collect Headers ---------- */
  function collectHeaders() {
    var headers = {};
    document.querySelectorAll('#headers-editor .kv-row').forEach(function (row) {
      var key = row.querySelector('.kv-row__key').value.trim();
      var val = row.querySelector('.kv-row__value').value.trim();
      if (key) headers[key] = val;
    });
    return headers;
  }

  /* ---------- Send Request ---------- */
  document.getElementById('send-btn').addEventListener('click', sendRequest);

  function sendRequest() {
    var method = document.getElementById('http-method').value;
    var url = document.getElementById('request-url').value.trim();
    if (!url) {
      url = 'https://jsonplaceholder.typicode.com/posts/1';
      document.getElementById('request-url').value = url;
    }

    var headers = collectHeaders();
    var body = null;
    if (method !== 'GET' && method !== 'DELETE') {
      body = document.getElementById('request-body').value.trim() || null;
    }

    var responseBody = document.getElementById('response-body');
    var responseMeta = document.getElementById('response-meta');
    responseBody.textContent = 'Loading...';
    responseMeta.innerHTML = '';

    var startTime = performance.now();

    var fetchOpts = { method: method, headers: headers };
    if (body) fetchOpts.body = body;

    fetch(url, fetchOpts)
      .then(function (res) {
        var elapsed = Math.round(performance.now() - startTime);
        var statusClass = 'response-meta__status--' + Math.floor(res.status / 100) + 'xx';
        responseMeta.innerHTML =
          '<span class="response-meta__status ' + statusClass + '">' + res.status + ' ' + res.statusText + '</span>' +
          '<span class="response-meta__time">' + elapsed + 'ms</span>';

        return res.text().then(function (text) {
          return { status: res.status, statusText: res.statusText, text: text, elapsed: elapsed };
        });
      })
      .then(function (data) {
        try {
          var json = JSON.parse(data.text);
          responseBody.textContent = JSON.stringify(json, null, 2);
        } catch (e) {
          responseBody.textContent = data.text;
        }

        addToHistory(method, url, data.status, data.elapsed);
      })
      .catch(function (err) {
        responseMeta.innerHTML = '<span class="response-meta__status response-meta__status--5xx">Error</span>';
        responseBody.textContent = 'Request failed: ' + err.message;
        addToHistory(method, url, 0, 0);
      });
  }

  /* ---------- History ---------- */
  function addToHistory(method, url, status, elapsed) {
    history.unshift({ method: method, url: url, status: status, elapsed: elapsed, time: new Date() });
    if (history.length > 20) history.pop();
    renderHistory();
  }

  function renderHistory() {
    var list = document.getElementById('history-list');
    if (history.length === 0) {
      list.innerHTML = '<p class="history-empty">No requests yet</p>';
      return;
    }
    var html = '';
    history.forEach(function (item, i) {
      var statusColor = item.status >= 200 && item.status < 300 ? 'color:var(--color-success)' :
        item.status >= 400 ? 'color:var(--color-danger)' : 'color:var(--color-warning)';
      html += '<div class="history-item" data-index="' + i + '">' +
        '<span class="history-item__method history-item__method--' + item.method + '">' + item.method + '</span>' +
        '<span class="history-item__url">' + escapeHtml(item.url) + '</span>' +
        '<span class="history-item__status" style="' + statusColor + '">' + (item.status || 'ERR') + '</span>' +
        '<span class="history-item__time">' + item.elapsed + 'ms</span>' +
        '</div>';
    });
    list.innerHTML = html;

    list.querySelectorAll('.history-item').forEach(function (el) {
      el.addEventListener('click', function () {
        var idx = parseInt(el.getAttribute('data-index'));
        var entry = history[idx];
        if (entry) {
          document.getElementById('http-method').value = entry.method;
          document.getElementById('request-url').value = entry.url;
        }
      });
    });
  }

  /* ---------- Utility ---------- */
  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /* ---------- GSAP Animations (D7 translateX(-20px)) ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    gsap.from('.hero__icon', { opacity: 0, scale: 0.8, duration: 0.5, ease: 'back.out(1.7)' });
    gsap.from('.hero__title', { opacity: 0, x: -20, duration: 0.6, delay: 0.1, ease: 'power3.out' });
    gsap.from('.hero__subtitle', { opacity: 0, x: -20, duration: 0.5, delay: 0.2, ease: 'power3.out' });

    gsap.from('.panel--request', { opacity: 0, x: -20, duration: 0.7, delay: 0.3, ease: 'power2.out' });
    gsap.from('.panel--response', { opacity: 0, x: -20, duration: 0.7, delay: 0.45, ease: 'power2.out' });

    gsap.from('.section--history .section__title', {
      scrollTrigger: { trigger: '.section--history', start: 'top 85%' },
      opacity: 0, x: -20, duration: 0.6, ease: 'power3.out',
    });
  }

  initAnimations();

})();
