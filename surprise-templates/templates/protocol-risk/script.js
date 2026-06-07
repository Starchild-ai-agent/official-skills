/* ============================================================
   Protocol Risk Exposure Map — script.js

   APIs: DeFi Llama (TVL) + Simulated risk data
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
    walletAddress: (() => {
      const raw = '{{WALLET_ADDRESS}}';
      if (raw.startsWith('{{')) return '0x742d...4a2e';
      return raw;
    })(),
    maxRetries: 2,
    retryBaseDelay: 1500,
  };

  const API = {
    tvl: () => 'https://api.llama.fi/protocols',
  };

  /* ---------- Simulated Protocol Risk Data ---------- */
  const PROTOCOLS = [
    {
      name: 'Aave V3',
      chain: 'Ethereum',
      tvl: 12400000000,
      audit: 'Multiple (Trail of Bits, OpenZeppelin)',
      auditStatus: 'pass',
      age: '4+ years',
      ageMonths: 48,
      insurance: 'Nexus Mutual',
      riskLevel: 'low',
      exposure: 45000,
      riskScore: 15,
      checks: [
        { title: 'Smart Contract Audit', status: 'pass', desc: 'Audited by Trail of Bits, OpenZeppelin, SigmaPrime' },
        { title: 'TVL Stability', status: 'pass', desc: 'TVL > $10B, consistent for 12+ months' },
        { title: 'Insurance Coverage', status: 'pass', desc: 'Covered by Nexus Mutual' },
      ],
    },
    {
      name: 'Uniswap V3',
      chain: 'Ethereum',
      tvl: 5200000000,
      audit: 'Multiple audits',
      auditStatus: 'pass',
      age: '3+ years',
      ageMonths: 36,
      insurance: 'None',
      riskLevel: 'low',
      exposure: 32000,
      riskScore: 22,
      checks: [
        { title: 'Smart Contract Audit', status: 'pass', desc: 'Audited by multiple firms' },
        { title: 'TVL Stability', status: 'pass', desc: 'TVL > $5B, battle-tested' },
        { title: 'Insurance Coverage', status: 'warn', desc: 'No direct insurance coverage' },
      ],
    },
    {
      name: 'Lido',
      chain: 'Ethereum',
      tvl: 14800000000,
      audit: 'Quantstamp, MixBytes',
      auditStatus: 'pass',
      age: '3+ years',
      ageMonths: 38,
      insurance: 'Partial (Unslashed)',
      riskLevel: 'medium',
      exposure: 85000,
      riskScore: 35,
      checks: [
        { title: 'Smart Contract Audit', status: 'pass', desc: 'Audited by Quantstamp, MixBytes' },
        { title: 'Centralization Risk', status: 'warn', desc: 'High market share in ETH staking (~30%)' },
        { title: 'Slashing Risk', status: 'warn', desc: 'Validator slashing possible, partial insurance' },
      ],
    },
    {
      name: 'GMX',
      chain: 'Arbitrum',
      tvl: 580000000,
      audit: 'ABDK Consulting',
      auditStatus: 'pass',
      age: '2+ years',
      ageMonths: 28,
      insurance: 'None',
      riskLevel: 'medium',
      exposure: 18000,
      riskScore: 42,
      checks: [
        { title: 'Smart Contract Audit', status: 'pass', desc: 'Audited by ABDK' },
        { title: 'Oracle Dependency', status: 'warn', desc: 'Relies on Chainlink oracles for pricing' },
        { title: 'Insurance Coverage', status: 'fail', desc: 'No insurance coverage available' },
      ],
    },
    {
      name: 'Pendle',
      chain: 'Ethereum',
      tvl: 320000000,
      audit: 'Ackee Blockchain',
      auditStatus: 'pass',
      age: '1.5 years',
      ageMonths: 18,
      insurance: 'None',
      riskLevel: 'high',
      exposure: 12000,
      riskScore: 58,
      checks: [
        { title: 'Smart Contract Audit', status: 'pass', desc: 'Audited by Ackee Blockchain' },
        { title: 'Protocol Maturity', status: 'warn', desc: 'Relatively new, complex yield tokenization' },
        { title: 'Insurance Coverage', status: 'fail', desc: 'No insurance coverage' },
        { title: 'Complexity Risk', status: 'warn', desc: 'Complex PT/YT mechanics increase attack surface' },
      ],
    },
    {
      name: 'NewDeFi Protocol',
      chain: 'Base',
      tvl: 45000000,
      audit: 'Pending',
      auditStatus: 'fail',
      age: '3 months',
      ageMonths: 3,
      insurance: 'None',
      riskLevel: 'critical',
      exposure: 5000,
      riskScore: 82,
      checks: [
        { title: 'Smart Contract Audit', status: 'fail', desc: 'No completed audit' },
        { title: 'Protocol Maturity', status: 'fail', desc: 'Less than 6 months old' },
        { title: 'TVL Stability', status: 'warn', desc: 'TVL < $100M, volatile' },
        { title: 'Insurance Coverage', status: 'fail', desc: 'No insurance coverage' },
        { title: 'Team Doxxed', status: 'fail', desc: 'Anonymous team' },
      ],
    },
  ];

  const MITIGATION_RECOMMENDATIONS = [
    {
      priority: 'high',
      title: 'Exit unaudited protocols',
      desc: 'Move funds from NewDeFi Protocol to audited alternatives. Unaudited contracts carry the highest smart contract risk.',
      impact: 'Reduces portfolio risk score by ~15 points',
    },
    {
      priority: 'high',
      title: 'Add insurance coverage',
      desc: 'Purchase Nexus Mutual or InsurAce coverage for Lido and GMX positions to protect against smart contract exploits.',
      impact: 'Covers $103K in uninsured exposure',
    },
    {
      priority: 'medium',
      title: 'Diversify staking providers',
      desc: 'Reduce Lido concentration by splitting ETH staking across Rocket Pool and Coinbase cbETH to mitigate centralization risk.',
      impact: 'Reduces single-protocol exposure by 40%',
    },
    {
      priority: 'medium',
      title: 'Set position size limits',
      desc: 'Cap any single protocol exposure at 25% of total DeFi portfolio. Current Lido exposure exceeds this threshold.',
      impact: 'Improves risk distribution across protocols',
    },
    {
      priority: 'low',
      title: 'Monitor oracle dependencies',
      desc: 'Set up alerts for Chainlink oracle deviations on GMX. Consider protocols with multiple oracle fallbacks.',
      impact: 'Early warning for oracle-related risks',
    },
    {
      priority: 'low',
      title: 'Review governance proposals',
      desc: 'Actively monitor governance votes for Aave and Uniswap that could affect risk parameters or fee structures.',
      impact: 'Proactive risk management through governance participation',
    },
  ];

  /* ---------- State ---------- */
  let riskDoughnut = null;

  /* ============================================================
     GSAP ANIMATION SYSTEM
     ============================================================ */

  function animateHeroEntrance() {
    if (prefersReducedMotion) {
      gsap.set('.hero__content > *, .hero__score-ring', { opacity: 1 });
      return;
    }
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });
    tl.from('.hero__label', { opacity: 0, x: -50, duration: 0.5 })
      .from('.hero__title', { opacity: 0, x: -50, duration: 0.6 }, '-=0.3')
      .from('.hero__subtitle', { opacity: 0, x: -50, duration: 0.4 }, '-=0.3')
      .from('.hero__wallet', { opacity: 0, x: -50, duration: 0.3 }, '-=0.2')
      .from('.hero__score-ring', { opacity: 0, scale: 0.8, duration: 0.8 }, '-=0.5');
  }

  function animateCardEntrance() {
    if (prefersReducedMotion) {
      gsap.set('[data-animate]', { opacity: 1, x: 0 });
      return;
    }
    gsap.utils.toArray('[data-animate]').forEach((el, i) => {
      gsap.to(el, {
        scrollTrigger: {
          trigger: el,
          start: 'top 88%',
          toggleActions: 'play none none none',
        },
        opacity: 1,
        x: 0,
        duration: 0.6,
        delay: i * 0.08,
        ease: 'power3.out',
      });
    });
  }

  /* ============================================================
     THEME TOGGLE
     ============================================================ */

  function initThemeToggle() {
    const btn = document.getElementById('theme-toggle');
    const stored = localStorage.getItem('protocol-risk-theme');
    if (stored === 'light') document.documentElement.setAttribute('data-theme', 'light');

    btn.addEventListener('click', () => {
      const isLight = document.documentElement.getAttribute('data-theme') === 'light';
      if (isLight) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('protocol-risk-theme', 'dark');
      } else {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('protocol-risk-theme', 'light');
      }
      renderRiskDoughnut();
    });
  }

  /* ============================================================
     RISK SCORE CALCULATION
     ============================================================ */

  function calculateOverallRisk() {
    const totalExposure = PROTOCOLS.reduce((s, p) => s + p.exposure, 0);
    if (totalExposure === 0) return 0;

    const weightedScore = PROTOCOLS.reduce((s, p) => {
      return s + (p.riskScore * p.exposure / totalExposure);
    }, 0);

    return Math.round(weightedScore);
  }

  function getRiskGrade(score) {
    if (score <= 20) return { grade: 'A — Low Risk', color: 'var(--risk-low)' };
    if (score <= 35) return { grade: 'B — Moderate', color: 'var(--risk-medium)' };
    if (score <= 50) return { grade: 'C — Elevated', color: 'var(--risk-high)' };
    if (score <= 70) return { grade: 'D — High Risk', color: 'var(--risk-critical)' };
    return { grade: 'F — Critical', color: 'var(--risk-critical)' };
  }

  /* ============================================================
     RENDER SCORE RING
     ============================================================ */

  function renderScoreRing() {
    const score = calculateOverallRisk();
    const { grade, color } = getRiskGrade(score);

    const ringFill = document.getElementById('score-ring-fill');
    const scoreValue = document.getElementById('score-value');
    const scoreGrade = document.getElementById('score-grade');

    const circumference = 427.26;
    const offset = circumference - (score / 100) * circumference;
    ringFill.style.strokeDashoffset = offset;
    ringFill.style.stroke = color;

    scoreValue.textContent = score;
    scoreValue.style.color = color;
    scoreGrade.textContent = grade;
    scoreGrade.style.color = color;
    scoreGrade.style.background = color.replace(')', ', 0.10)').replace('var(', 'rgba(');

    // Wallet display
    const walletEl = document.getElementById('hero-wallet');
    if (CONFIG.walletAddress) {
      walletEl.textContent = CONFIG.walletAddress;
    }
  }

  /* ============================================================
     RENDER CHECKLIST
     ============================================================ */

  function renderChecklist() {
    const container = document.getElementById('risk-checklist');
    const statusIcons = { pass: '✓', warn: '⚠', fail: '✗' };
    const statusClasses = { pass: 'checklist-item__icon--pass', warn: 'checklist-item__icon--warn', fail: 'checklist-item__icon--fail' };
    const riskBadgeClasses = { low: 'badge--low', medium: 'badge--medium', high: 'badge--high', critical: 'badge--critical' };

    const allChecks = [];
    PROTOCOLS.forEach(protocol => {
      protocol.checks.forEach(check => {
        allChecks.push({
          ...check,
          protocol: protocol.name,
          riskLevel: protocol.riskLevel,
        });
      });
    });

    // Sort: fail first, then warn, then pass
    const order = { fail: 0, warn: 1, pass: 2 };
    allChecks.sort((a, b) => order[a.status] - order[b.status]);

    container.innerHTML = allChecks.map(check => `
      <div class="checklist-item">
        <div class="checklist-item__icon ${statusClasses[check.status]}">${statusIcons[check.status]}</div>
        <div class="checklist-item__body">
          <div class="checklist-item__title">${check.title}</div>
          <div class="checklist-item__desc">${check.desc}</div>
        </div>
        <span class="checklist-item__protocol">${check.protocol}</span>
        <span class="checklist-item__badge ${riskBadgeClasses[check.riskLevel]}">${check.riskLevel.toUpperCase()}</span>
      </div>
    `).join('');
  }

  /* ============================================================
     RENDER EXPOSURE TABLE
     ============================================================ */

  function renderExposureTable() {
    const tbody = document.getElementById('exposure-body');
    const sorted = [...PROTOCOLS].sort((a, b) => b.exposure - a.exposure);

    const riskClasses = {
      low: 'cell-success',
      medium: 'cell-warning',
      high: 'cell-danger',
      critical: 'cell-danger',
    };

    tbody.innerHTML = sorted.map(p => `
      <tr>
        <td><strong>${p.name}</strong></td>
        <td>${p.chain}</td>
        <td>$${formatNumber(p.tvl)}</td>
        <td class="${p.auditStatus === 'pass' ? 'cell-success' : 'cell-danger'}">${p.audit}</td>
        <td>${p.age}</td>
        <td>${p.insurance}</td>
        <td class="${riskClasses[p.riskLevel]}">${p.riskLevel.toUpperCase()}</td>
        <td class="cell-accent">$${p.exposure.toLocaleString()}</td>
      </tr>
    `).join('');
  }

  function formatNumber(num) {
    if (num >= 1e9) return (num / 1e9).toFixed(1) + 'B';
    if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M';
    if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K';
    return num.toString();
  }

  /* ============================================================
     RENDER RISK DOUGHNUT
     ============================================================ */

  function getChartColors() {
    const style = getComputedStyle(document.documentElement);
    return {
      c1: style.getPropertyValue('--chart-1').trim(),
      c2: style.getPropertyValue('--chart-2').trim(),
      c3: style.getPropertyValue('--chart-3').trim(),
      c4: style.getPropertyValue('--chart-4').trim(),
      c5: style.getPropertyValue('--chart-5').trim(),
      c6: style.getPropertyValue('--chart-6').trim(),
      text: style.getPropertyValue('--color-text-secondary').trim(),
      border: style.getPropertyValue('--color-border').trim(),
      bg: style.getPropertyValue('--color-surface').trim(),
    };
  }

  function renderRiskDoughnut() {
    const ctx = document.getElementById('risk-doughnut').getContext('2d');
    const colors = getChartColors();

    const riskCategories = {
      'Low': PROTOCOLS.filter(p => p.riskLevel === 'low').reduce((s, p) => s + p.exposure, 0),
      'Medium': PROTOCOLS.filter(p => p.riskLevel === 'medium').reduce((s, p) => s + p.exposure, 0),
      'High': PROTOCOLS.filter(p => p.riskLevel === 'high').reduce((s, p) => s + p.exposure, 0),
      'Critical': PROTOCOLS.filter(p => p.riskLevel === 'critical').reduce((s, p) => s + p.exposure, 0),
    };

    const riskColors = [colors.c4, colors.c3, colors.c2, colors.c1];

    if (riskDoughnut) riskDoughnut.destroy();

    riskDoughnut = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: Object.keys(riskCategories),
        datasets: [{
          data: Object.values(riskCategories),
          backgroundColor: riskColors.map(c => c + '90'),
          borderColor: riskColors,
          borderWidth: 2,
          hoverOffset: 8,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '65%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: colors.text,
              font: { family: "'Victor Mono', monospace", size: 11 },
              padding: 16,
              usePointStyle: true,
              pointStyleWidth: 10,
            },
          },
          tooltip: {
            backgroundColor: colors.bg,
            titleColor: colors.text,
            bodyColor: colors.text,
            borderColor: colors.border,
            borderWidth: 1,
            callbacks: {
              label: (ctx) => {
                const total = ctx.dataset.data.reduce((s, v) => s + v, 0);
                const pct = ((ctx.parsed / total) * 100).toFixed(1);
                return `${ctx.label}: $${ctx.parsed.toLocaleString()} (${pct}%)`;
              },
            },
          },
        },
      },
    });
  }

  /* ============================================================
     RENDER MITIGATION CARDS
     ============================================================ */

  function renderMitigationCards() {
    const container = document.getElementById('mitigation-cards');

    container.innerHTML = MITIGATION_RECOMMENDATIONS.map(rec => `
      <div class="mitigation-card">
        <div class="mitigation-card__priority mitigation-card__priority--${rec.priority}">${rec.priority} priority</div>
        <div class="mitigation-card__title">${rec.title}</div>
        <div class="mitigation-card__desc">${rec.desc}</div>
        <div class="mitigation-card__impact">Impact: ${rec.impact}</div>
      </div>
    `).join('');
  }

  /* ============================================================
     FETCH TVL DATA (optional enhancement)
     ============================================================ */

  async function fetchTVLData() {
    try {
      const res = await fetch(API.tvl());
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // Update TVL for known protocols
      const protocolMap = {
        'Aave V3': 'aave',
        'Uniswap V3': 'uniswap',
        'Lido': 'lido',
        'GMX': 'gmx',
        'Pendle': 'pendle',
      };

      PROTOCOLS.forEach(p => {
        const slug = protocolMap[p.name];
        if (slug) {
          const found = data.find(d => d.slug === slug);
          if (found && found.tvl) {
            p.tvl = found.tvl;
          }
        }
      });

      // Re-render with updated TVL
      renderExposureTable();
    } catch (err) {
      // Silently use simulated data
    }
  }

  /* ============================================================
     BOOTSTRAP
     ============================================================ */

  function init() {
    initThemeToggle();
    renderScoreRing();
    renderChecklist();
    renderExposureTable();
    renderRiskDoughnut();
    renderMitigationCards();
    animateHeroEntrance();
    animateCardEntrance();
    fetchTVLData();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
