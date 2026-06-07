/* ============================================================
   Thread Ideas Generator — script.js
   Mock data · GSAP 3 + ScrollTrigger
   ============================================================ */

(function () {
  'use strict';

  gsap.registerPlugin(ScrollTrigger);
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Mock Data ---------- */
  const TOPICS = [
    { id: 'crypto', name: 'Crypto', icon: '\u20bf', count: 6 },
    { id: 'ai', name: 'AI / ML', icon: '\ud83e\udd16', count: 5 },
    { id: 'marketing', name: 'Marketing', icon: '\ud83d\udce3', count: 4 },
    { id: 'startup', name: 'Startups', icon: '\ud83d\ude80', count: 5 },
    { id: 'productivity', name: 'Productivity', icon: '\u26a1', count: 3 },
    { id: 'finance', name: 'Finance', icon: '\ud83d\udcb0', count: 4 },
    { id: 'design', name: 'Design', icon: '\ud83c\udfa8', count: 3 },
    { id: 'career', name: 'Career', icon: '\ud83d\udcc8', count: 4 },
  ];

  const THREAD_TEMPLATES = {
    crypto: {
      hook: "I've spent 500+ hours studying on-chain data.\n\nHere are 7 wallet patterns that predict price moves before they happen \ud83e\uddf5\ud83d\udc47",
      body: [
        "1/ Whale Accumulation Zones\n\nWhen wallets holding 1000+ ETH start accumulating during a dip, it historically precedes a 20-40% rally within 30 days.\n\nKey metric: watch for 3+ consecutive days of net inflows.",
        "2/ Smart Money Rotation\n\nTrack wallets that were early to AAVE, UNI, and SOL. When they move into a new protocol, pay attention.\n\nUse Arkham or Nansen to label and track these wallets.",
        "3/ Exchange Outflow Spikes\n\nMassive exchange outflows = people moving to self-custody = bullish signal.\n\nLook for outflows exceeding 2x the 30-day average.",
        "4/ Stablecoin Supply on Exchanges\n\nRising stablecoin balances on exchanges = dry powder ready to buy.\n\nThis metric called the bottom in March 2023 with 85% accuracy.",
        "5/ NFT Blue Chip Floor Correlation\n\nWhen blue chip NFT floors drop 50%+ while ETH is flat, it often signals a broader risk-off move coming in 2-4 weeks."
      ],
      cta: "If you found this useful:\n\n1. Follow me for daily on-chain insights\n2. RT the first tweet to help others\n3. Drop a fire emoji if you want Part 2\n\nI share alpha like this every week."
    },
    ai: {
      hook: "GPT-5 is coming and most people aren't ready.\n\nHere are 10 AI skills that will be worth $100k+ in 2025 \ud83e\uddf5",
      body: [
        "1/ Prompt Engineering (Advanced)\n\nNot basic prompting \u2014 chain-of-thought, few-shot learning, and system prompt architecture.\n\nCompanies are paying $150-300k for senior prompt engineers.",
        "2/ Fine-tuning and RAG Systems\n\nKnowing how to fine-tune models on custom data and build Retrieval-Augmented Generation pipelines.\n\nThis is the #1 requested skill in AI job postings right now.",
        "3/ AI Agent Development\n\nBuilding autonomous agents that can use tools, make decisions, and complete multi-step tasks.\n\nFrameworks: LangChain, CrewAI, AutoGen.",
        "4/ Evaluation and Testing\n\nHow do you know if your AI system is actually good? Building eval frameworks is a massive gap in most teams."
      ],
      cta: "The AI revolution is just starting.\n\nFollow me for daily AI career insights.\nRT tweet 1 to share with your network.\n\nWhat AI skill are you learning? Reply below."
    },
    marketing: {
      hook: "I grew from 0 to 50K followers in 6 months.\n\nHere's my exact content strategy (no paid ads) \ud83e\uddf5",
      body: [
        "1/ The 3-1-1 Content Formula\n\nFor every 5 posts:\n- 3 educational threads\n- 1 personal story\n- 1 hot take / opinion\n\nThis ratio keeps your audience learning AND emotionally connected.",
        "2/ Hook Templates That Work\n\n- \"I spent X hours doing Y. Here's what I learned:\"\n- \"Most people think X. They're wrong. Here's why:\"\n- \"X things I wish I knew before Y:\"\n\nSave these. Use them. They convert.",
        "3/ The Engagement Loop\n\nPost then reply to every comment in first hour then quote tweet your own thread with a key insight then pin the thread.\n\nThis 4-step loop 3x'd my impressions."
      ],
      cta: "Want more growth strategies?\n\n1. Follow for daily tips\n2. RT the first tweet\n3. Reply with your biggest content challenge\n\nI read every reply."
    },
    startup: {
      hook: "I've reviewed 200+ pitch decks this year.\n\n90% make the same 7 mistakes. Here's how to fix them \ud83e\uddf5",
      body: [
        "1/ Leading with the Solution\n\nInvestors don't care about your product first. They care about the PROBLEM.\n\nStart with: How big is the pain? Who feels it? Why hasn't it been solved?",
        "2/ TAM/SAM/SOM Fantasy\n\n\"It's a $500B market\" means nothing.\n\nShow your bottoms-up calculation: X customers x Y price x Z frequency = realistic market size.",
        "3/ No Clear Business Model\n\nIf slide 8 is the first time you mention revenue, you've lost them.\n\nShow unit economics by slide 4-5. CAC, LTV, payback period.",
        "4/ Ignoring Competition\n\n\"We have no competitors\" = red flag.\n\nEvery problem has alternatives. Show you understand the landscape and why you win."
      ],
      cta: "Building a startup? I share fundraising insights weekly.\n\nFollow + RT to help other founders.\n\nDM me your deck for a free 5-min review (first 10 only)."
    },
    productivity: {
      hook: "I work 4 hours a day and outperform people working 12.\n\nHere's my system (stolen from neuroscience research) \ud83e\uddf5",
      body: [
        "1/ The 90-Minute Focus Block\n\nYour brain works in 90-minute ultradian cycles. Work WITH this rhythm, not against it.\n\n90 min deep work, 20 min break, repeat. Max 3 blocks per day.",
        "2/ The 2-Minute Capture Rule\n\nAny thought, task, or idea that pops up: capture it in under 2 minutes, then return to focus.\n\nTool: a single plain text file. Nothing fancy.",
        "3/ Energy Management > Time Management\n\nTrack your energy for 1 week. When are you sharpest? That's when you do creative work.\n\nAdmin, emails, meetings = low energy slots."
      ],
      cta: "Productivity is a skill, not a talent.\n\nFollow for more systems that actually work.\nRT tweet 1 to help someone who needs this."
    },
    finance: {
      hook: "I turned $5K into $180K in 3 years using boring investments.\n\nNo day trading. No crypto gambling. Just math. \ud83e\uddf5",
      body: [
        "1/ The Power of Dollar-Cost Averaging\n\n$500/month into S&P 500 for 3 years.\n\nEven through the 2022 crash, DCA smoothed my entry and I caught the recovery.",
        "2/ The 3-Fund Portfolio\n\n60% US Total Market (VTI)\n30% International (VXUS)\n10% Bonds (BND)\n\nRebalance quarterly. That's it. Outperforms 90% of active managers.",
        "3/ Tax-Loss Harvesting\n\nSelling losers to offset gains saved me $4,200 in taxes last year.\n\nMost people leave this money on the table.",
        "4/ The Emergency Fund Ladder\n\n1 month in checking, 2 months in HYSA (5%+), 3 months in T-bills.\n\nYour emergency fund should ALSO be working for you."
      ],
      cta: "Wealth building is simple (not easy).\n\nFollow for weekly finance threads.\nRT to help someone start their journey.\n\nWhat's your #1 money question?"
    },
    design: {
      hook: "I've designed 100+ landing pages.\n\nHere are 8 design principles that convert 2-3x better \ud83e\uddf5",
      body: [
        "1/ Visual Hierarchy = Conversion Hierarchy\n\nThe eye should flow: Headline, Value prop, Social proof, CTA.\n\nIf your CTA isn't the most visually prominent element, you're losing conversions.",
        "2/ White Space Is Not Wasted Space\n\nEvery premium brand uses generous spacing. It signals quality and confidence.\n\nRule: if it feels like too much space, it's probably just right.",
        "3/ One CTA Per Section\n\nMultiple CTAs create decision paralysis. Each section should drive ONE action.\n\nPrimary CTA: high contrast. Secondary: ghost button or text link."
      ],
      cta: "Design is a business skill.\n\nFollow for weekly design breakdowns.\nRT to help a fellow designer.\n\nDrop your landing page below for a free roast."
    },
    career: {
      hook: "I went from $45K to $250K salary in 4 years.\n\nNo MBA. No connections. Just these 9 career moves \ud83e\uddf5",
      body: [
        "1/ The Skills Stack Strategy\n\nDon't be the best at one thing. Be top 20% at 3 complementary skills.\n\nMy stack: coding + writing + data analysis = rare and valuable combination.",
        "2/ The 2-Year Rule\n\nStay at least 2 years (learn deeply), leave before 4 (avoid stagnation).\n\nEach strategic move should come with a 20-30% salary bump.",
        "3/ Build in Public\n\nShare what you're learning on Twitter/LinkedIn. This creates inbound opportunities.\n\nMy last 3 job offers came from people who followed my content.",
        "4/ Negotiate Everything\n\nBase salary, signing bonus, equity, remote days, learning budget.\n\nMost people leave $10-30K on the table by not negotiating."
      ],
      cta: "Your career is your biggest asset.\n\nFollow for weekly career strategies.\nRT to help someone level up.\n\nWhat's your biggest career challenge right now?"
    }
  };

  const HOOKS = [
    { category: 'Curiosity Gap', formula: '"I spent X hours doing Y. Here\'s what I learned:"', example: 'I spent 200 hours analyzing top Twitter accounts. Here\'s what they all have in common:' },
    { category: 'Contrarian', formula: '"Most people think X. They\'re wrong."', example: 'Most people think you need a large following to go viral. They\'re wrong.' },
    { category: 'List Promise', formula: '"X things I wish I knew before Y"', example: '7 things I wish I knew before starting my startup' },
    { category: 'Story Hook', formula: '"X years ago, I was Y. Today I\'m Z."', example: '3 years ago, I was broke. Today I run a 7-figure business.' },
    { category: 'Data Hook', formula: '"I analyzed X data points. Here\'s what the data says:"', example: 'I analyzed 10,000 viral tweets. Here\'s what the data says:' },
    { category: 'Challenge', formula: '"Stop doing X. Start doing Y instead."', example: 'Stop writing 1 tweet a day. Start writing 5 threads a week instead.' },
    { category: 'Authority', formula: '"After X years of Y, here are my top lessons:"', example: 'After 8 years of investing, here are my top 10 lessons:' },
    { category: 'FOMO', formula: '"X is changing everything. Most people don\'t see it yet."', example: 'AI agents are changing everything. Most people don\'t see it yet.' },
  ];

  const TIPS = [
    { title: 'Start with the Hook', desc: 'Your first tweet determines if anyone reads the rest. Spend 50% of your writing time on the hook.' },
    { title: 'One Idea Per Tweet', desc: 'Each tweet in your thread should contain exactly one clear idea. If you need two tweets for one point, split it.' },
    { title: 'Use Line Breaks', desc: 'Short paragraphs and line breaks make tweets scannable. Nobody reads walls of text on Twitter.' },
    { title: 'End with a CTA', desc: 'Always tell people what to do next: follow, RT, reply, or click a link. Don\'t leave them hanging.' },
    { title: 'Optimal Length: 5-12 Tweets', desc: 'Too short lacks value. Too long loses attention. The sweet spot is 5-12 tweets for most topics.' },
    { title: 'Add Visuals', desc: 'Threads with images or screenshots get 2-3x more engagement. Add at least one visual per thread.' },
  ];

  let selectedTopic = 'crypto';
  let isPreviewMode = false;

  /* ---------- DOM ---------- */
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  /* ---------- Theme Toggle ---------- */
  const themeToggle = $('#theme-toggle');
  function initTheme() {
    const saved = localStorage.getItem('thread-ideas-theme');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  }
  initTheme();
  themeToggle.addEventListener('click', () => {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
    localStorage.setItem('thread-ideas-theme', isDark ? 'light' : 'dark');
  });

  /* ---------- Toast ---------- */
  function showToast(msg) {
    const toast = $('#toast');
    toast.textContent = msg;
    toast.classList.add('visible');
    setTimeout(() => toast.classList.remove('visible'), 2200);
  }

  /* ---------- Render Topics ---------- */
  function renderTopics() {
    const grid = $('#topic-grid');
    grid.innerHTML = TOPICS.map(t => `
      <div class="topic-card ${t.id === selectedTopic ? 'active' : ''}" data-topic="${t.id}">
        <div class="topic-card__icon">${t.icon}</div>
        <div class="topic-card__name">${t.name}</div>
        <div class="topic-card__count">${t.count} templates</div>
      </div>
    `).join('');

    grid.querySelectorAll('.topic-card').forEach(card => {
      card.addEventListener('click', () => {
        selectedTopic = card.dataset.topic;
        renderTopics();
        renderThread();
      });
    });
  }

  /* ---------- Render Thread ---------- */
  function renderThread() {
    const template = THREAD_TEMPLATES[selectedTopic];
    if (!template) return;

    const preview = $('#thread-preview');
    const allTweets = [
      { type: 'HOOK', content: template.hook },
      ...template.body.map(b => ({ type: 'BODY', content: b })),
      { type: 'CTA', content: template.cta }
    ];

    preview.innerHTML = allTweets.map((tweet, i) => {
      const charCount = tweet.content.length;
      const isOver = charCount > 280;
      const typeClass = tweet.type === 'HOOK' ? 'tweet-card--hook' : tweet.type === 'CTA' ? 'tweet-card--cta' : '';
      return `
        <div class="tweet-card ${typeClass}" data-index="${i}">
          <div class="tweet-card__header">
            <span class="tweet-card__type">${tweet.type}</span>
            <span class="tweet-card__number">${i + 1}/${allTweets.length}</span>
          </div>
          <div class="tweet-card__content">${tweet.content}</div>
          <div class="tweet-card__chars ${isOver ? 'tweet-card__chars--over' : ''}">${charCount}/280</div>
        </div>
      `;
    }).join('');

    const totalChars = allTweets.reduce((sum, t) => sum + t.content.length, 0);
    $('#char-count').textContent = totalChars;
    $('#tweet-count').textContent = allTweets.length;

    if (!prefersReducedMotion) {
      gsap.from('.tweet-card', {
        opacity: 0,
        scale: 0.9,
        duration: 0.5,
        stagger: 0.08,
        ease: 'power3.out',
        clearProps: 'transform,opacity'
      });
    }
  }

  /* ---------- Render Hooks ---------- */
  function renderHooks() {
    const grid = $('#hook-grid');
    grid.innerHTML = HOOKS.map(h => `
      <div class="hook-card">
        <div class="hook-card__category">${h.category}</div>
        <div class="hook-card__formula">${h.formula}</div>
        <div class="hook-card__example">${h.example}</div>
      </div>
    `).join('');
  }

  /* ---------- Render Tips ---------- */
  function renderTips() {
    const grid = $('#tips-grid');
    grid.innerHTML = TIPS.map((t, i) => `
      <div class="tip-card">
        <div class="tip-card__number">${String(i + 1).padStart(2, '0')}</div>
        <div class="tip-card__title">${t.title}</div>
        <div class="tip-card__desc">${t.desc}</div>
      </div>
    `).join('');
  }

  /* ---------- Controls ---------- */
  function initControls() {
    $('#btn-generate').addEventListener('click', () => {
      const keys = Object.keys(THREAD_TEMPLATES);
      const randomTopic = keys[Math.floor(Math.random() * keys.length)];
      selectedTopic = randomTopic;
      renderTopics();
      renderThread();
      showToast('New thread generated!');
    });

    $('#btn-preview').addEventListener('click', () => {
      isPreviewMode = !isPreviewMode;
      $('#btn-preview').textContent = isPreviewMode ? 'Edit Mode' : 'Preview Mode';
      showToast(isPreviewMode ? 'Preview mode on' : 'Edit mode on');
    });

    $('#btn-copy').addEventListener('click', () => {
      const template = THREAD_TEMPLATES[selectedTopic];
      if (!template) return;
      const allText = [template.hook, ...template.body, template.cta].join('\n\n---\n\n');
      navigator.clipboard.writeText(allText).then(() => {
        showToast('Thread copied to clipboard!');
      }).catch(() => {
        showToast('Copy failed');
      });
    });
  }

  /* ---------- GSAP Animations ---------- */
  function initAnimations() {
    if (prefersReducedMotion) return;

    /* Hero entrance — D14 fade+scale(0.9) */
    const heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    heroTl
      .from('.hero__label', { opacity: 0, scale: 0.9, duration: 0.5 })
      .from('.hero__title', { opacity: 0, scale: 0.9, duration: 0.7 }, '-=0.3')
      .from('.hero__subtitle', { opacity: 0, scale: 0.9, duration: 0.5 }, '-=0.3')
      .from('.hero__stat', { opacity: 0, scale: 0.9, duration: 0.4, stagger: 0.1 }, '-=0.2');

    /* Section scroll reveals */
    $$('.section').forEach(section => {
      gsap.from(section.querySelector('.section__title'), {
        scrollTrigger: { trigger: section, start: 'top 85%', once: true },
        opacity: 0, scale: 0.9, duration: 0.6, ease: 'power3.out'
      });
    });

    /* Hook cards stagger */
    gsap.from('.hook-card', {
      scrollTrigger: { trigger: '#hook-library', start: 'top 80%', once: true },
      opacity: 0, scale: 0.9, duration: 0.5, stagger: 0.06, ease: 'power3.out'
    });

    /* Tip cards stagger */
    gsap.from('.tip-card', {
      scrollTrigger: { trigger: '#tips', start: 'top 80%', once: true },
      opacity: 0, scale: 0.9, duration: 0.5, stagger: 0.06, ease: 'power3.out'
    });
  }

  /* ---------- Init ---------- */
  function init() {
    renderTopics();
    renderThread();
    renderHooks();
    renderTips();
    initControls();
    initAnimations();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
