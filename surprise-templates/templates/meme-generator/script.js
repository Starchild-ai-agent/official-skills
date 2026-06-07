/* ============================================================
   Meme Generator — script.js
   Skeleton: A11 Centered · Hover: C11 底部阴影
   Entrance: D12 交替方向 · Hero: H15 Interactive
   ============================================================ */
(function () {
  'use strict';
  var $ = function (s) { return document.querySelector(s); };
  var $$ = function (s) { return document.querySelectorAll(s); };

  /* ---------- Meme Templates ---------- */
  var TEMPLATES = [
    { id: 'drake', name: 'Drake', emoji: '🤔', bg: '#f0d0a0', topPos: 0.25, bottomPos: 0.75 },
    { id: 'distracted', name: 'Distracted', emoji: '👀', bg: '#c0d8e8', topPos: 0.15, bottomPos: 0.85 },
    { id: 'expanding', name: 'Expanding Brain', emoji: '🧠', bg: '#d0c0e0', topPos: 0.2, bottomPos: 0.8 },
    { id: 'change', name: 'Change My Mind', emoji: '☕', bg: '#a8d8a0', topPos: 0.15, bottomPos: 0.75 },
    { id: 'buttons', name: 'Two Buttons', emoji: '😰', bg: '#e8c0c0', topPos: 0.2, bottomPos: 0.8 },
    { id: 'stonks', name: 'Stonks', emoji: '📈', bg: '#b0e0b0', topPos: 0.15, bottomPos: 0.85 }
  ];

  var currentTemplate = TEMPLATES[0];
  var canvas = $('#memeCanvas');
  var ctx = canvas.getContext('2d');

  /* ---------- Theme ---------- */
  var savedTheme = localStorage.getItem('mg_theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  $('#themeToggle').addEventListener('click', function () {
    var cur = document.documentElement.getAttribute('data-theme');
    var nxt = cur === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', nxt);
    localStorage.setItem('mg_theme', nxt);
  });

  /* ---------- Render Templates ---------- */
  function renderTemplates() {
    var grid = $('#templateGrid');
    grid.innerHTML = TEMPLATES.map(function (t, i) {
      var cls = t.id === currentTemplate.id ? ' active' : '';
      return '<div class="template-card' + cls + '" data-idx="' + i + '">' +
        '<div class="template-card__preview" style="background:' + t.bg + '">' + t.emoji + '</div>' +
        '<div class="template-card__name">' + t.name + '</div>' +
        '</div>';
    }).join('');

    grid.querySelectorAll('.template-card').forEach(function (card) {
      card.addEventListener('click', function () {
        currentTemplate = TEMPLATES[parseInt(card.dataset.idx)];
        renderTemplates();
        renderMeme();
      });
    });
  }

  /* ---------- Render Meme ---------- */
  function renderMeme() {
    var topText = ($('#topText').value || '').toUpperCase();
    var bottomText = ($('#bottomText').value || '').toUpperCase();
    var fontSize = parseInt($('#fontSize').value) || 36;
    var textColor = $('#textColor').value;
    var strokeColor = $('#strokeColor').value;
    var strokeWidth = parseInt($('#strokeWidth').value) || 3;

    var w = canvas.width;
    var h = canvas.height;

    // Background
    ctx.fillStyle = currentTemplate.bg;
    ctx.fillRect(0, 0, w, h);

    // Template emoji (large centered)
    ctx.font = '120px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(currentTemplate.emoji, w / 2, h / 2);

    // Decorative pattern
    ctx.fillStyle = 'rgba(0,0,0,0.03)';
    for (var i = 0; i < w; i += 20) {
      for (var j = 0; j < h; j += 20) {
        if ((i + j) % 40 === 0) ctx.fillRect(i, j, 10, 10);
      }
    }

    // Text rendering function
    function drawText(text, yPos) {
      if (!text) return;
      ctx.font = 'bold ' + fontSize + 'px "Impact", "Nunito", sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = textColor;
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = strokeWidth;
      ctx.lineJoin = 'round';

      var x = w / 2;
      var y = h * yPos;

      if (strokeWidth > 0) ctx.strokeText(text, x, y);
      ctx.fillText(text, x, y);
    }

    drawText(topText, currentTemplate.topPos);
    drawText(bottomText, currentTemplate.bottomPos);
  }

  /* ---------- Events ---------- */
  $('#topText').addEventListener('input', renderMeme);
  $('#bottomText').addEventListener('input', renderMeme);
  $('#fontSize').addEventListener('input', renderMeme);
  $('#textColor').addEventListener('input', renderMeme);
  $('#strokeColor').addEventListener('input', renderMeme);
  $('#strokeWidth').addEventListener('input', renderMeme);

  /* ---------- Download ---------- */
  $('#downloadBtn').addEventListener('click', function () {
    var link = document.createElement('a');
    link.download = 'meme-' + currentTemplate.id + '.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
  });

  /* ---------- Init ---------- */
  renderTemplates();
  renderMeme();

  /* ---------- GSAP ---------- */
  if (typeof gsap !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
    var mm = gsap.matchMedia();
    mm.add('(prefers-reduced-motion: no-preference)', function () {
      gsap.from('.hero__emoji', { x: -30, opacity: 0, duration: 0.5, ease: 'power2.out' });
      gsap.from('.hero__title', { x: 30, opacity: 0, duration: 0.5, delay: 0.1, ease: 'power2.out' });
      gsap.from('.hero__sub', { x: -30, opacity: 0, duration: 0.5, delay: 0.2, ease: 'power2.out' });
      gsap.from('.template-card', {
        y: 20, opacity: 0, duration: 0.4, stagger: { each: 0.06, from: 'random' },
        delay: 0.3, ease: 'power2.out'
      });
      gsap.from('.editor__canvas-wrap', {
        x: 30, opacity: 0, duration: 0.6, ease: 'power2.out',
        scrollTrigger: { trigger: '.editor', start: 'top 85%' }
      });
      gsap.from('.editor__controls', {
        x: -30, opacity: 0, duration: 0.6, delay: 0.1, ease: 'power2.out',
        scrollTrigger: { trigger: '.editor', start: 'top 85%' }
      });
    });
  }
})();
