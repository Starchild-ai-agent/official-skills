/* ============================================================
   AI Research Digest — script.js
   Mock data · GSAP 3 + ScrollTrigger
   ============================================================ */
(function () {
  'use strict';
  gsap.registerPlugin(ScrollTrigger);
  var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var CATEGORIES = [
    { id: 'all', name: 'All Papers', count: 12 },
    { id: 'nlp', name: 'NLP', count: 4 },
    { id: 'cv', name: 'Computer Vision', count: 3 },
    { id: 'rl', name: 'Reinforcement Learning', count: 2 },
    { id: 'multimodal', name: 'Multimodal', count: 3 }
  ];

  var PAPERS = [
    { title: 'Scaling Laws for Neural Language Models: Beyond Chinchilla', abstract: 'We revisit compute-optimal training and find that data quality scaling laws diverge from Chinchilla predictions at the 1T parameter scale. New efficiency frontiers emerge with mixture-of-experts architectures.', authors: 'Chen et al.', date: 'Jun 2025', category: 'nlp' },
    { title: 'DINOv3: Self-Supervised Vision Transformers with Adaptive Masking', abstract: 'Building on DINOv2, we introduce adaptive masking strategies that improve downstream task performance by 12% on ImageNet-1K while reducing pre-training compute by 30%.', authors: 'Oquab et al.', date: 'May 2025', category: 'cv' },
    { title: 'Constitutional AI 2.0: Scalable Alignment Through Debate', abstract: 'We extend constitutional AI with multi-agent debate protocols, achieving RLHF-level alignment with 5x less human feedback. The approach scales to 100B+ parameter models.', authors: 'Bai et al.', date: 'Jun 2025', category: 'nlp' },
    { title: 'World Models for Robotic Manipulation: A Unified Framework', abstract: 'We present a unified world model architecture that enables zero-shot transfer of manipulation skills across robot embodiments, achieving 89% success rate on 50 diverse tasks.', authors: 'Brohan et al.', date: 'May 2025', category: 'rl' },
    { title: 'Gemini Ultra 2: Natively Multimodal Reasoning', abstract: 'We introduce Gemini Ultra 2 with native multimodal chain-of-thought reasoning. The model achieves SOTA on 15 benchmarks spanning text, image, video, and audio understanding.', authors: 'Google DeepMind', date: 'Jun 2025', category: 'multimodal' },
    { title: 'Efficient Attention: Linear Complexity Transformers at Scale', abstract: 'We propose a new attention mechanism achieving O(n) complexity while maintaining 98% of standard attention quality. Enables 1M+ context windows on consumer hardware.', authors: 'Dao et al.', date: 'May 2025', category: 'nlp' },
    { title: 'SegmentAnything 2: Real-Time Video Segmentation', abstract: 'SAM2 extends zero-shot segmentation to video with temporal consistency. Processes 4K video at 30fps with state-of-the-art accuracy on DAVIS and YouTube-VOS benchmarks.', authors: 'Kirillov et al.', date: 'Jun 2025', category: 'cv' },
    { title: 'RLHF Without Human Feedback: Self-Play Alignment', abstract: 'We demonstrate that language models can align themselves through self-play, eliminating the need for human preference data. Results match RLHF on TruthfulQA and HHH benchmarks.', authors: 'Burns et al.', date: 'May 2025', category: 'rl' },
    { title: 'Unified Vision-Language Planning for Embodied Agents', abstract: 'A single model that can see, reason, and act in both simulated and real environments. Achieves 73% success on ALFRED benchmark without task-specific fine-tuning.', authors: 'Reed et al.', date: 'Jun 2025', category: 'multimodal' },
    { title: '3D Scene Understanding from Single Images with Diffusion Models', abstract: 'We leverage diffusion model priors for monocular 3D scene reconstruction, achieving photorealistic novel view synthesis from a single input image.', authors: 'Liu et al.', date: 'May 2025', category: 'cv' },
    { title: 'Sparse Mixture of Experts at 10T Scale', abstract: 'We train a 10 trillion parameter sparse MoE model with only 200B active parameters per token. The model achieves new SOTA on MMLU, HellaSwag, and ARC benchmarks.', authors: 'Fedus et al.', date: 'Jun 2025', category: 'nlp' },
    { title: 'AudioPalm 2: Universal Audio Understanding and Generation', abstract: 'A single model for speech recognition, translation, synthesis, and music generation. Supports 100+ languages with near-human quality on MOS evaluations.', authors: 'Rubenstein et al.', date: 'Jun 2025', category: 'multimodal' }
  ];

  var MODELS = [
    { name: 'GPT-5', org: 'OpenAI', date: 'Jun 2025' },
    { name: 'Claude 4', org: 'Anthropic', date: 'May 2025' },
    { name: 'Gemini Ultra 2', org: 'Google', date: 'Jun 2025' },
    { name: 'Llama 4', org: 'Meta', date: 'May 2025' },
    { name: 'Mistral Large 3', org: 'Mistral AI', date: 'Jun 2025' }
  ];

  var activeCategory = 'all';
  var $ = function (sel) { return document.querySelector(sel); };

  function initTheme() {
    var saved = localStorage.getItem('ai-research-theme');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  }
  initTheme();
  $('#theme-toggle').addEventListener('click', function () {
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
    localStorage.setItem('ai-research-theme', isDark ? 'light' : 'dark');
  });

  function renderSidebar() {
    var list = $('#sidebar-list');
    list.innerHTML = CATEGORIES.map(function (c) {
      return '<div class="sidebar__item ' + (c.id === activeCategory ? 'active' : '') + '" data-cat="' + c.id + '">' + c.name + '<span class="sidebar__item-count">' + c.count + '</span></div>';
    }).join('');
    list.querySelectorAll('.sidebar__item').forEach(function (item) {
      item.addEventListener('click', function () {
        activeCategory = item.dataset.cat;
        renderSidebar();
        renderPapers();
      });
    });
  }

  function renderModels() {
    var el = $('#model-list');
    el.innerHTML = MODELS.map(function (m) {
      return '<div class="model-item"><div class="model-item__name">' + m.name + '</div><div class="model-item__org">' + m.org + '</div><div class="model-item__date">' + m.date + '</div></div>';
    }).join('');
  }

  function renderPapers() {
    var items = activeCategory === 'all' ? PAPERS : PAPERS.filter(function (p) { return p.category === activeCategory; });
    var grid = $('#paper-grid');
    grid.innerHTML = items.map(function (p) {
      return '<div class="paper-card"><div class="paper-card__category">' + p.category.toUpperCase() + '</div><div class="paper-card__title">' + p.title + '</div><div class="paper-card__abstract">' + p.abstract + '</div><div class="paper-card__meta"><span class="paper-card__authors">' + p.authors + '</span><span class="paper-card__date">' + p.date + '</span></div></div>';
    }).join('');

    if (!prefersReducedMotion) {
      gsap.from('.paper-card', { opacity: 0, y: 20, duration: 0.4, stagger: 0.06, ease: 'power3.out', clearProps: 'opacity,transform' });
    }
  }

  function initAnimations() {
    if (prefersReducedMotion) return;
    var heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl.from('.hero__label', { opacity: 0, y: 20, duration: 0.5 })
      .from('.hero__title', { opacity: 0, y: 30, duration: 0.7 }, '-=0.3')
      .from('.hero__subtitle', { opacity: 0, y: 20, duration: 0.5 }, '-=0.3');

    gsap.from('.sidebar__item', {
      scrollTrigger: { trigger: '#main', start: 'top 80%', once: true },
      opacity: 0, x: -20, duration: 0.3, stagger: 0.05, ease: 'power3.out'
    });
    gsap.from('.model-item', {
      scrollTrigger: { trigger: '#main', start: 'top 70%', once: true },
      opacity: 0, x: -20, duration: 0.3, stagger: 0.06, ease: 'power3.out'
    });
  }

  function init() {
    renderSidebar();
    renderModels();
    renderPapers();
    initAnimations();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
