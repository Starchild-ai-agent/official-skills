/* ============================================================
   Crypto Knowledge Quiz — script.js
   Skeleton: A11 Centered · Hover: C20 scale(1.03)
   Entrance: D14 fade+scale(0.9) · Hero: H15 Interactive
   ============================================================ */
(function () {
  'use strict';
  var $ = function (s) { return document.querySelector(s); };

  var QUESTIONS = [
    { q: 'What is the maximum supply of Bitcoin?', a: ['21 million', '100 million', '18 million', 'Unlimited'], c: 0 },
    { q: 'Who created Bitcoin?', a: ['Satoshi Nakamoto', 'Vitalik Buterin', 'Charlie Lee', 'Nick Szabo'], c: 0 },
    { q: 'What consensus mechanism does Ethereum use after The Merge?', a: ['Proof of Stake', 'Proof of Work', 'Delegated PoS', 'Proof of Authority'], c: 0 },
    { q: 'What does DeFi stand for?', a: ['Decentralized Finance', 'Digital Finance', 'Distributed Finance', 'Defined Finance'], c: 0 },
    { q: 'What is a smart contract?', a: ['Self-executing code on blockchain', 'A legal document', 'A type of wallet', 'A mining algorithm'], c: 0 },
    { q: 'What does NFT stand for?', a: ['Non-Fungible Token', 'New Financial Technology', 'Network File Transfer', 'Non-Fixed Token'], c: 0 },
    { q: 'What is gas in Ethereum?', a: ['Transaction fee unit', 'A type of token', 'Mining reward', 'Network speed'], c: 0 },
    { q: 'What is a blockchain fork?', a: ['A protocol split', 'A wallet backup', 'A mining pool', 'A token burn'], c: 0 },
    { q: 'What is the smallest unit of Bitcoin called?', a: ['Satoshi', 'Wei', 'Gwei', 'Finney'], c: 0 },
    { q: 'What does HODL mean in crypto?', a: ['Hold On for Dear Life', 'High Order Digital Ledger', 'Hash Output Data Link', 'Hybrid On-chain DeFi Layer'], c: 0 },
    { q: 'What is a DAO?', a: ['Decentralized Autonomous Organization', 'Digital Asset Offering', 'Distributed Application Output', 'Data Access Object'], c: 0 },
    { q: 'What blockchain does Solana use?', a: ['Proof of History + PoS', 'Proof of Work', 'Proof of Authority', 'Proof of Burn'], c: 0 },
    { q: 'What is yield farming?', a: ['Earning rewards by providing liquidity', 'Mining cryptocurrency', 'Buying low selling high', 'Staking governance tokens'], c: 0 },
    { q: 'What is an AMM?', a: ['Automated Market Maker', 'Advanced Mining Machine', 'Asset Management Module', 'Automated Minting Mechanism'], c: 0 },
    { q: 'What is impermanent loss?', a: ['Loss from providing liquidity vs holding', 'Permanent loss of funds', 'Transaction fee loss', 'Slippage cost'], c: 0 },
    { q: 'What is a seed phrase?', a: ['Recovery words for a wallet', 'A mining password', 'A smart contract key', 'A token symbol'], c: 0 },
    { q: 'What is TVL in DeFi?', a: ['Total Value Locked', 'Token Verification Layer', 'Transaction Volume Limit', 'Trust Validation Logic'], c: 0 },
    { q: 'What is a DEX?', a: ['Decentralized Exchange', 'Digital Exchange', 'Distributed Execution', 'Data Exchange'], c: 0 },
    { q: 'What is staking?', a: ['Locking tokens to earn rewards', 'Selling tokens at a loss', 'Creating new tokens', 'Burning tokens'], c: 0 },
    { q: 'What is a Layer 2 solution?', a: ['Scaling solution built on top of L1', 'A new blockchain', 'A wallet type', 'A consensus mechanism'], c: 0 },
    { q: 'What is a liquidity pool?', a: ['Token pairs locked in a smart contract', 'A mining pool', 'A centralized exchange', 'A wallet balance'], c: 0 },
    { q: 'What is a flash loan?', a: ['Uncollateralized loan repaid in one tx', 'A fast bank transfer', 'A small loan', 'A staking reward'], c: 0 },
    { q: 'What is EIP-1559?', a: ['Ethereum fee burning mechanism', 'A new token standard', 'A mining algorithm', 'A wallet protocol'], c: 0 },
    { q: 'What is a wrapped token?', a: ['Token pegged to another on a different chain', 'An encrypted token', 'A governance token', 'A burned token'], c: 0 },
    { q: 'What is a rug pull?', a: ['Developers abandoning a project with funds', 'A market correction', 'A mining difficulty increase', 'A token upgrade'], c: 0 },
    { q: 'What is the ERC-20 standard?', a: ['Fungible token standard on Ethereum', 'NFT standard', 'Wallet standard', 'Mining standard'], c: 0 },
    { q: 'What is a validator?', a: ['Node that verifies transactions in PoS', 'A wallet address', 'A token holder', 'A smart contract'], c: 0 },
    { q: 'What is slippage?', a: ['Price difference between expected and executed', 'A type of fee', 'A mining reward', 'A wallet error'], c: 0 },
    { q: 'What is a cold wallet?', a: ['Offline storage for crypto', 'A hot wallet', 'A mining rig', 'A DeFi protocol'], c: 0 },
    { q: 'What is a bridge in crypto?', a: ['Protocol connecting different blockchains', 'A mining pool', 'A wallet feature', 'A token type'], c: 0 }
  ];

  var NUM_QUESTIONS = 10;
  var quizQuestions = [];
  var currentIdx = 0;
  var score = 0;
  var highScore = parseInt(localStorage.getItem('cq_high') || '0');

  $('#highScore').textContent = highScore;

  /* ---------- Theme ---------- */
  var savedTheme = localStorage.getItem('cq_theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  $('#themeToggle').addEventListener('click', function () {
    var cur = document.documentElement.getAttribute('data-theme');
    var nxt = cur === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', nxt);
    localStorage.setItem('cq_theme', nxt);
  });

  /* ---------- Shuffle ---------- */
  function shuffle(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
    }
    return a;
  }

  /* ---------- Start ---------- */
  function startQuiz() {
    quizQuestions = shuffle(QUESTIONS).slice(0, NUM_QUESTIONS);
    currentIdx = 0;
    score = 0;
    $('#currentScore').textContent = '0';
    $('#startScreen').style.display = 'none';
    $('#resultScreen').style.display = 'none';
    $('#quizScreen').style.display = 'block';
    showQuestion();
  }

  function showQuestion() {
    var q = quizQuestions[currentIdx];
    $('#questionCount').textContent = (currentIdx + 1) + ' / ' + NUM_QUESTIONS;
    $('#progressFill').style.width = ((currentIdx / NUM_QUESTIONS) * 100) + '%';
    $('#questionText').textContent = q.q;

    var opts = $('#options');
    opts.innerHTML = '';
    q.a.forEach(function (ans, i) {
      var btn = document.createElement('button');
      btn.className = 'option-btn';
      btn.textContent = ans;
      btn.addEventListener('click', function () { selectAnswer(i); });
      opts.appendChild(btn);
    });

    if (typeof gsap !== 'undefined') {
      var mm = gsap.matchMedia();
      mm.add('(prefers-reduced-motion: no-preference)', function () {
        gsap.from('.question-card', { scale: 0.9, opacity: 0, duration: 0.4, ease: 'power2.out' });
        gsap.from('.option-btn', { scale: 0.9, opacity: 0, duration: 0.3, stagger: 0.06, delay: 0.1, ease: 'power2.out' });
      });
    }
  }

  function selectAnswer(idx) {
    var q = quizQuestions[currentIdx];
    var btns = document.querySelectorAll('.option-btn');
    btns.forEach(function (b, i) {
      b.classList.add('option-btn--disabled');
      if (i === q.c) b.classList.add('option-btn--correct');
      if (i === idx && idx !== q.c) b.classList.add('option-btn--wrong');
    });

    if (idx === q.c) {
      score++;
      $('#currentScore').textContent = score;
    }

    setTimeout(function () {
      currentIdx++;
      if (currentIdx < NUM_QUESTIONS) {
        showQuestion();
      } else {
        showResult();
      }
    }, 1200);
  }

  /* ---------- Result ---------- */
  function showResult() {
    $('#quizScreen').style.display = 'none';
    $('#resultScreen').style.display = 'block';
    $('#finalScore').textContent = score;
    $('#totalQuestions').textContent = NUM_QUESTIONS;

    var pct = (score / NUM_QUESTIONS) * 100;
    var grade, emoji, title, msg;
    if (pct >= 90) { grade = 'A+'; emoji = '🏆'; title = 'Crypto Master!'; msg = 'You really know your stuff!'; }
    else if (pct >= 70) { grade = 'B+'; emoji = '🌟'; title = 'Well Done!'; msg = 'Solid knowledge of crypto fundamentals.'; }
    else if (pct >= 50) { grade = 'C'; emoji = '📚'; title = 'Not Bad!'; msg = 'Keep learning and you will improve.'; }
    else { grade = 'D'; emoji = '💪'; title = 'Keep Going!'; msg = 'There is always more to learn in crypto.'; }

    $('#resultEmoji').textContent = emoji;
    $('#resultTitle').textContent = title;
    $('#resultGrade').textContent = grade;
    $('#resultMsg').textContent = msg;

    if (score > highScore) {
      highScore = score;
      localStorage.setItem('cq_high', String(highScore));
      $('#highScore').textContent = highScore;
    }

    if (typeof gsap !== 'undefined') {
      var mm = gsap.matchMedia();
      mm.add('(prefers-reduced-motion: no-preference)', function () {
        gsap.from('.result__emoji', { scale: 0.5, opacity: 0, duration: 0.5, ease: 'back.out(1.7)' });
        gsap.from('.result__title', { scale: 0.9, opacity: 0, duration: 0.4, delay: 0.1, ease: 'power2.out' });
        gsap.from('.result__grade', { scale: 0.9, opacity: 0, duration: 0.4, delay: 0.2, ease: 'power2.out' });
      });
    }
  }

  /* ---------- Events ---------- */
  $('#startBtn').addEventListener('click', startQuiz);
  $('#retryBtn').addEventListener('click', startQuiz);

  /* ---------- GSAP Init ---------- */
  if (typeof gsap !== 'undefined') {
    var mm = gsap.matchMedia();
    mm.add('(prefers-reduced-motion: no-preference)', function () {
      gsap.from('.hero__emoji', { scale: 0.5, opacity: 0, duration: 0.5, ease: 'back.out(1.7)' });
      gsap.from('.hero__title', { scale: 0.9, opacity: 0, duration: 0.4, delay: 0.1, ease: 'power2.out' });
      gsap.from('.hero__sub', { scale: 0.9, opacity: 0, duration: 0.4, delay: 0.2, ease: 'power2.out' });
      gsap.from('.hero__stats', { scale: 0.9, opacity: 0, duration: 0.4, delay: 0.3, ease: 'power2.out' });
      gsap.from('.btn--start', { scale: 0.9, opacity: 0, duration: 0.4, delay: 0.4, ease: 'power2.out' });
    });
  }
})();