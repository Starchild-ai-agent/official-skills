/* ============================================================
   CSS Animation Playground — script.js

   Pure frontend functionality — no external APIs required.
   Real-time CSS animation preview with property controls,
   preset library, and custom keyframes editor.

   Skeleton: A5 Vertical Stacked Panels
   Entry:   D3 translateX(30px) from right
   Animation: GSAP 3 + ScrollTrigger (CDN)
   ============================================================ */

(function () {
  'use strict';

  /* ---------- Register GSAP Plugins ---------- */
  gsap.registerPlugin(ScrollTrigger);

  /* ---------- Reduced Motion Check ---------- */
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Configuration ---------- */
  const CONFIG = {
    heroImageUrl: (() => {
      const raw = '{{HERO_IMAGE_URL}}';
      if (raw.startsWith('{{')) return '';
      return raw;
    })(),
  };

  /* ============================================================
     ANIMATION PRESETS
     ============================================================ */
  const PRESETS = [
    {
      name: 'Bounce',
      icon: '⬆',
      keyframes: `@keyframes playground-anim {
  0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-60px); }
  60% { transform: translateY(-30px); }
}`,
    },
    {
      name: 'Fade In',
      icon: '👁',
      keyframes: `@keyframes playground-anim {
  0% { opacity: 0; }
  100% { opacity: 1; }
}`,
    },
    {
      name: 'Slide Right',
      icon: '➡',
      keyframes: `@keyframes playground-anim {
  0% { transform: translateX(-100px); opacity: 0; }
  100% { transform: translateX(0); opacity: 1; }
}`,
    },
    {
      name: 'Slide Up',
      icon: '⬆',
      keyframes: `@keyframes playground-anim {
  0% { transform: translateY(80px); opacity: 0; }
  100% { transform: translateY(0); opacity: 1; }
}`,
    },
    {
      name: 'Rotate',
      icon: '🔄',
      keyframes: `@keyframes playground-anim {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}`,
    },
    {
      name: 'Scale',
      icon: '🔍',
      keyframes: `@keyframes playground-anim {
  0% { transform: scale(0); }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); }
}`,
    },
    {
      name: 'Shake',
      icon: '📳',
      keyframes: `@keyframes playground-anim {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-8px); }
  20%, 40%, 60%, 80% { transform: translateX(8px); }
}`,
    },
    {
      name: 'Pulse',
      icon: '💓',
      keyframes: `@keyframes playground-anim {
  0% { transform: scale(1); }
  50% { transform: scale(1.15); }
  100% { transform: scale(1); }
}`,
    },
    {
      name: 'Flip',
      icon: '🪙',
      keyframes: `@keyframes playground-anim {
  0% { transform: perspective(400px) rotateY(0); }
  100% { transform: perspective(400px) rotateY(360deg); }
}`,
    },
    {
      name: 'Swing',
      icon: '🎪',
      keyframes: `@keyframes playground-anim {
  20% { transform: rotate(15deg); }
  40% { transform: rotate(-10deg); }
  60% { transform: rotate(5deg); }
  80% { transform: rotate(-5deg); }
  100% { transform: rotate(0deg); }
}`,
    },
    {
      name: 'Jello',
      icon: '🍮',
      keyframes: `@keyframes playground-anim {
  0%, 100% { transform: skewX(0deg) skewY(0deg); }
  11.1% { transform: skewX(-12.5deg) skewY(-12.5deg); }
  22.2% { transform: skewX(6.25deg) skewY(6.25deg); }
  33.3% { transform: skewX(-3.125deg) skewY(-3.125deg); }
  44.4% { transform: skewX(1.5625deg) skewY(1.5625deg); }
  55.5% { transform: skewX(-0.78deg) skewY(-0.78deg); }
  66.6% { transform: skewX(0.39deg) skewY(0.39deg); }
}`,
    },
    {
      name: 'Zoom In',
      icon: '🔎',
      keyframes: `@keyframes playground-anim {
  0% { transform: scale(0.3); opacity: 0; }
  50% { opacity: 1; }
  100% { transform: scale(1); }
}`,
    },
  ];

  /* ============================================================
     DOM REFERENCES
     ============================================================ */
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => [...document.querySelectorAll(sel)];

  const els = {
    themeToggle: $('#theme-toggle'),
    heroTime: $('#hero-time'),
    heroBgImage: $('.hero__bg-image'),
    injectedStyle: $('#injected-style'),
    previewElement: $('#preview-element'),
    btnReplay: $('#btn-replay'),
    btnPause: $('#btn-pause'),
    btnReset: $('#btn-reset'),
    ctrlDuration: $('#ctrl-duration'),
    ctrlDelay: $('#ctrl-delay'),
    ctrlTiming: $('#ctrl-timing'),
    ctrlIterations: $('#ctrl-iterations'),
    ctrlInfinite: $('#ctrl-infinite'),
    ctrlDirection: $('#ctrl-direction'),
    ctrlFill: $('#ctrl-fill'),
    valDuration: $('#val-duration'),
    valDelay: $('#val-delay'),
    valIterations: $('#val-iterations'),
    presetsGrid: $('#presets-grid'),
    codeOutput: $('#code-output'),
    codeCopyBtn: $('#code-copy-btn'),
    keyframesEditor: $('#keyframes-editor'),
    btnApplyCustom: $('#btn-apply-custom'),
  };

  /* ---------- State ---------- */
  let currentPresetIndex = 0;
  let currentKeyframes = PRESETS[0].keyframes;
  let isPaused = false;

  /* ============================================================
     THEME MANAGEMENT
     ============================================================ */
  function initTheme() {
    const saved = localStorage.getItem('css-playground-theme');
    if (saved) {
      document.documentElement.setAttribute('data-theme', saved);
    } else {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('css-playground-theme', next);
  }

  /* ============================================================
     HERO CLOCK
     ============================================================ */
  function updateClock() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    const dateStr = now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    els.heroTime.textContent = `${dateStr} ${timeStr}`;
    els.heroTime.setAttribute('datetime', now.toISOString());
  }

  /* ============================================================
     HERO BACKGROUND IMAGE
     ============================================================ */
  function initHeroImage() {
    if (CONFIG.heroImageUrl && els.heroBgImage) {
      els.heroBgImage.style.backgroundImage = `url('${CONFIG.heroImageUrl}')`;
      els.heroBgImage.style.backgroundSize = 'cover';
      els.heroBgImage.style.backgroundPosition = 'center';
      els.heroBgImage.style.opacity = '0.10';
    }
  }

  /* ============================================================
     ANIMATION ENGINE
     ============================================================ */

  function getAnimationProps() {
    const duration = parseFloat(els.ctrlDuration.value);
    const delay = parseFloat(els.ctrlDelay.value);
    const timing = els.ctrlTiming.value;
    const iterations = els.ctrlInfinite.checked ? 'infinite' : parseInt(els.ctrlIterations.value);
    const direction = els.ctrlDirection.value;
    const fill = els.ctrlFill.value;

    return { duration, delay, timing, iterations, direction, fill };
  }

  function buildAnimationCSS() {
    const props = getAnimationProps();
    return `playground-anim ${props.duration}s ${props.timing} ${props.delay}s ${props.iterations} ${props.direction} ${props.fill}`;
  }

  function applyAnimation() {
    els.injectedStyle.textContent = currentKeyframes;
    els.previewElement.style.animation = 'none';
    void els.previewElement.offsetWidth;
    els.previewElement.style.animation = buildAnimationCSS();
    els.previewElement.style.animationPlayState = isPaused ? 'paused' : 'running';
  }

  function replayAnimation() {
    isPaused = false;
    els.btnPause.textContent = 'Pause';
    applyAnimation();
  }

  function togglePause() {
    isPaused = !isPaused;
    els.btnPause.textContent = isPaused ? 'Resume' : 'Pause';
    els.previewElement.style.animationPlayState = isPaused ? 'paused' : 'running';
  }

  function resetAnimation() {
    isPaused = false;
    els.btnPause.textContent = 'Pause';
    els.previewElement.style.animation = 'none';
  }

  function updateCodeOutput() {
    const props = getAnimationProps();
    const animationLine = `animation: playground-anim ${props.duration}s ${props.timing} ${props.delay}s ${props.iterations} ${props.direction} ${props.fill};`;

    const code = `/* Animation */
.element {
  ${animationLine}
}

/* Keyframes */
${currentKeyframes}`;

    els.codeOutput.textContent = code;
  }

  /* ============================================================
     PRESETS RENDERING
     ============================================================ */
  function renderPresets() {
    els.presetsGrid.innerHTML = '';

    PRESETS.forEach((preset, i) => {
      const card = document.createElement('div');
      card.className = `preset-card${i === currentPresetIndex ? ' active' : ''}`;
      card.innerHTML = `
        <div class="preset-card__icon">${preset.icon}</div>
        <div class="preset-card__name">${preset.name}</div>
      `;
      card.addEventListener('click', () => {
        currentPresetIndex = i;
        currentKeyframes = preset.keyframes;
        els.keyframesEditor.value = preset.keyframes;

        $$('.preset-card').forEach((c, ci) => {
          c.classList.toggle('active', ci === i);
        });

        applyAnimation();
        updateCodeOutput();
      });
      els.presetsGrid.appendChild(card);
    });
  }

  /* ============================================================
     GSAP ANIMATIONS — D3: translateX(30px) from right
     ============================================================ */
  function initAnimations() {
    if (prefersReducedMotion) return;

    /* Hero entrance */
    const heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl
      .from('.hero__status-bar', { x: 30, opacity: 0, duration: 0.6 })
      .from('.hero__title', { x: 30, opacity: 0, duration: 0.7 }, '-=0.3')
      .from('.hero__subtitle', { x: 30, opacity: 0, duration: 0.5 }, '-=0.4')
      .from('.hero__preview-stage', { x: 30, opacity: 0, duration: 0.6 }, '-=0.3');

    /* D3: Each playground-panel slides from right */
    const panels = $$('.playground-panel');
    panels.forEach(panel => {
      gsap.from(panel, {
        scrollTrigger: {
          trigger: panel,
          start: 'top 85%',
          toggleActions: 'play none none none',
        },
        x: 30,
        opacity: 0,
        duration: 0.7,
        ease: 'power2.out',
      });
    });

    /* Preset cards stagger — also from right */
    gsap.from('.preset-card', {
      scrollTrigger: {
        trigger: '#section-presets',
        start: 'top 80%',
        toggleActions: 'play none none none',
      },
      x: 30,
      opacity: 0,
      duration: 0.5,
      stagger: 0.05,
      ease: 'power2.out',
    });
  }

  /* ============================================================
     EVENT LISTENERS
     ============================================================ */
  function bindEvents() {
    els.themeToggle.addEventListener('click', toggleTheme);

    els.btnReplay.addEventListener('click', replayAnimation);
    els.btnPause.addEventListener('click', togglePause);
    els.btnReset.addEventListener('click', resetAnimation);

    els.ctrlDuration.addEventListener('input', () => {
      els.valDuration.textContent = `${els.ctrlDuration.value}s`;
      applyAnimation();
      updateCodeOutput();
    });
    els.ctrlDelay.addEventListener('input', () => {
      els.valDelay.textContent = `${els.ctrlDelay.value}s`;
      applyAnimation();
      updateCodeOutput();
    });
    els.ctrlIterations.addEventListener('input', () => {
      els.valIterations.textContent = els.ctrlIterations.value;
      applyAnimation();
      updateCodeOutput();
    });

    els.ctrlTiming.addEventListener('change', () => {
      applyAnimation();
      updateCodeOutput();
    });
    els.ctrlDirection.addEventListener('change', () => {
      applyAnimation();
      updateCodeOutput();
    });
    els.ctrlFill.addEventListener('change', () => {
      applyAnimation();
      updateCodeOutput();
    });

    els.ctrlInfinite.addEventListener('change', () => {
      els.ctrlIterations.disabled = els.ctrlInfinite.checked;
      applyAnimation();
      updateCodeOutput();
    });

    els.codeCopyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(els.codeOutput.textContent).then(() => {
        els.codeCopyBtn.textContent = 'Copied!';
        els.codeCopyBtn.classList.add('copied');
        setTimeout(() => {
          els.codeCopyBtn.textContent = 'Copy';
          els.codeCopyBtn.classList.remove('copied');
        }, 1500);
      });
    });

    els.btnApplyCustom.addEventListener('click', () => {
      const customCode = els.keyframesEditor.value.trim();
      if (!customCode) return;

      const normalized = customCode.replace(
        /@keyframes\s+[\w-]+/g,
        '@keyframes playground-anim'
      );

      currentKeyframes = normalized;

      $$('.preset-card').forEach(c => c.classList.remove('active'));
      currentPresetIndex = -1;

      applyAnimation();
      updateCodeOutput();

      document.getElementById('preview-stage').scrollIntoView({ behavior: 'smooth' });
    });
  }

  /* ============================================================
     INIT
     ============================================================ */
  function init() {
    initTheme();
    initHeroImage();
    updateClock();
    setInterval(updateClock, 1000);

    els.keyframesEditor.value = PRESETS[0].keyframes;

    renderPresets();
    applyAnimation();
    updateCodeOutput();
    bindEvents();

    requestAnimationFrame(() => {
      initAnimations();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
