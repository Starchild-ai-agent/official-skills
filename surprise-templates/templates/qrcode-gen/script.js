/* ============================================================
   QR Code Generator — script.js
   Pure frontend · qrcode.js library
   ============================================================ */

(function () {
  'use strict';

  /* ---------- DOM refs ---------- */
  const presetTabs   = document.querySelectorAll('.preset-tab');
  const inputUrl     = document.getElementById('inputUrl');
  const inputText    = document.getElementById('inputText');
  const inputWifi    = document.getElementById('inputWifi');
  const inputVcard   = document.getElementById('inputVcard');
  const qrUrl        = document.getElementById('qrUrl');
  const qrText       = document.getElementById('qrText');
  const wifiSsid     = document.getElementById('wifiSsid');
  const wifiPass     = document.getElementById('wifiPass');
  const wifiEnc      = document.getElementById('wifiEnc');
  const vcardName    = document.getElementById('vcardName');
  const vcardPhone   = document.getElementById('vcardPhone');
  const vcardEmail   = document.getElementById('vcardEmail');
  const vcardOrg     = document.getElementById('vcardOrg');
  const qrFgColor    = document.getElementById('qrFgColor');
  const qrBgColor    = document.getElementById('qrBgColor');
  const fgHex        = document.getElementById('fgHex');
  const bgHex        = document.getElementById('bgHex');
  const qrEcc        = document.getElementById('qrEcc');
  const qrSize       = document.getElementById('qrSize');
  const qrCanvas     = document.getElementById('qrCanvas');
  const qrDataCode   = document.getElementById('qrDataCode');
  const downloadBtn  = document.getElementById('downloadBtn');
  const themeToggle  = document.getElementById('themeToggle');

  /* ---------- State ---------- */
  let currentPreset = 'url';
  let debounceTimer = null;

  /* ---------- Theme ---------- */
  function initTheme() {
    const saved = localStorage.getItem('qr-theme');
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
    localStorage.setItem('qr-theme', next);
  });

  initTheme();

  /* ---------- Preset Tabs ---------- */
  const inputGroups = { url: inputUrl, text: inputText, wifi: inputWifi, vcard: inputVcard };

  presetTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const preset = tab.dataset.preset;
      currentPreset = preset;

      // Update active tab
      presetTabs.forEach(t => t.classList.remove('preset-tab--active'));
      tab.classList.add('preset-tab--active');

      // Show/hide input groups
      Object.entries(inputGroups).forEach(([key, el]) => {
        if (key === preset) {
          el.classList.remove('input-group--hidden');
        } else {
          el.classList.add('input-group--hidden');
        }
      });

      generateQR();
    });
  });

  /* ---------- Build QR data string ---------- */
  function getQRData() {
    switch (currentPreset) {
      case 'url':
        return qrUrl.value || 'https://example.com';

      case 'text':
        return qrText.value || 'Hello World';

      case 'wifi': {
        const ssid = wifiSsid.value || 'MyNetwork';
        const pass = wifiPass.value || '';
        const enc = wifiEnc.value;
        return `WIFI:T:${enc};S:${ssid};P:${pass};;`;
      }

      case 'vcard': {
        const name = vcardName.value || 'John Doe';
        const phone = vcardPhone.value || '';
        const email = vcardEmail.value || '';
        const org = vcardOrg.value || '';
        const parts = name.split(' ');
        const lastName = parts.length > 1 ? parts.pop() : '';
        const firstName = parts.join(' ');
        let vcard = 'BEGIN:VCARD\nVERSION:3.0\n';
        vcard += `N:${lastName};${firstName};;;\n`;
        vcard += `FN:${name}\n`;
        if (org) vcard += `ORG:${org}\n`;
        if (phone) vcard += `TEL:${phone}\n`;
        if (email) vcard += `EMAIL:${email}\n`;
        vcard += 'END:VCARD';
        return vcard;
      }

      default:
        return 'https://example.com';
    }
  }

  /* ---------- Generate QR Code ---------- */
  function generateQR() {
    const data = getQRData();
    const size = parseInt(qrSize.value, 10);
    const fg = qrFgColor.value;
    const bg = qrBgColor.value;

    const eccMap = { L: 0, M: 1, Q: 2, H: 3 };
    const errorCorrectionLevel = qrEcc.value;

    // Update data preview
    qrDataCode.textContent = data;

    // Use QRCode library to render to canvas
    if (typeof QRCode === 'undefined') {
      qrDataCode.textContent = 'QRCode library not loaded';
      return;
    }

    QRCode.toCanvas(qrCanvas, data, {
      width: size,
      margin: 2,
      color: {
        dark: fg,
        light: bg,
      },
      errorCorrectionLevel: errorCorrectionLevel,
    }, function (error) {
      if (error) {
        console.error('QR generation error:', error);
        qrDataCode.textContent = 'Error generating QR code';
      }
    });
  }

  /* ---------- Debounced generation ---------- */
  function debouncedGenerate() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(generateQR, 250);
  }

  /* ---------- Input listeners ---------- */
  // URL
  qrUrl.addEventListener('input', debouncedGenerate);

  // Text
  qrText.addEventListener('input', debouncedGenerate);

  // WiFi
  wifiSsid.addEventListener('input', debouncedGenerate);
  wifiPass.addEventListener('input', debouncedGenerate);
  wifiEnc.addEventListener('change', debouncedGenerate);

  // vCard
  vcardName.addEventListener('input', debouncedGenerate);
  vcardPhone.addEventListener('input', debouncedGenerate);
  vcardEmail.addEventListener('input', debouncedGenerate);
  vcardOrg.addEventListener('input', debouncedGenerate);

  // Style options
  qrFgColor.addEventListener('input', () => {
    fgHex.textContent = qrFgColor.value;
    debouncedGenerate();
  });

  qrBgColor.addEventListener('input', () => {
    bgHex.textContent = qrBgColor.value;
    debouncedGenerate();
  });

  qrEcc.addEventListener('change', generateQR);
  qrSize.addEventListener('change', generateQR);

  /* ---------- Download ---------- */
  downloadBtn.addEventListener('click', () => {
    const link = document.createElement('a');
    link.download = 'qrcode.png';
    link.href = qrCanvas.toDataURL('image/png');
    link.click();
  });

  /* ---------- GSAP Animations ---------- */
  function initAnimations() {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) {
      document.querySelectorAll('.qr-panel').forEach(p => {
        p.style.opacity = '1';
        p.style.transform = 'none';
      });
      return;
    }

    gsap.registerPlugin(ScrollTrigger);

    // Hero entrance
    gsap.fromTo('.hero__heading', {
      opacity: 0, y: 30,
    }, {
      opacity: 1, y: 0,
      duration: 0.7,
      ease: 'power2.out',
    });

    gsap.fromTo('.hero__sub', {
      opacity: 0, y: 20,
    }, {
      opacity: 1, y: 0,
      duration: 0.6,
      delay: 0.15,
      ease: 'power2.out',
    });

    // Left panels: D1 translateY(40px) stagger
    const leftPanels = document.querySelectorAll('.split__left .qr-panel');
    leftPanels.forEach((panel, i) => {
      gsap.fromTo(panel, {
        opacity: 0,
        y: 40,
      }, {
        opacity: 1,
        y: 0,
        duration: 0.6,
        delay: 0.1 + 0.12 * i,
        ease: 'power2.out',
        scrollTrigger: {
          trigger: panel,
          start: 'top 88%',
          once: true,
        },
      });
    });

    // Right preview panel
    gsap.fromTo('.qr-preview-panel', {
      opacity: 0,
      y: 40,
    }, {
      opacity: 1,
      y: 0,
      duration: 0.7,
      delay: 0.3,
      ease: 'power2.out',
    });
  }

  /* ---------- Persist last settings ---------- */
  function saveSettings() {
    const settings = {
      preset: currentPreset,
      url: qrUrl.value,
      text: qrText.value,
      wifiSsid: wifiSsid.value,
      wifiPass: wifiPass.value,
      wifiEnc: wifiEnc.value,
      vcardName: vcardName.value,
      vcardPhone: vcardPhone.value,
      vcardEmail: vcardEmail.value,
      vcardOrg: vcardOrg.value,
      fgColor: qrFgColor.value,
      bgColor: qrBgColor.value,
      ecc: qrEcc.value,
      size: qrSize.value,
    };
    localStorage.setItem('qr-gen-settings', JSON.stringify(settings));
  }

  function loadSettings() {
    try {
      const raw = localStorage.getItem('qr-gen-settings');
      if (!raw) return;
      const s = JSON.parse(raw);

      if (s.preset) {
        currentPreset = s.preset;
        presetTabs.forEach(t => {
          t.classList.toggle('preset-tab--active', t.dataset.preset === s.preset);
        });
        Object.entries(inputGroups).forEach(([key, el]) => {
          el.classList.toggle('input-group--hidden', key !== s.preset);
        });
      }

      if (s.url) qrUrl.value = s.url;
      if (s.text) qrText.value = s.text;
      if (s.wifiSsid) wifiSsid.value = s.wifiSsid;
      if (s.wifiPass) wifiPass.value = s.wifiPass;
      if (s.wifiEnc) wifiEnc.value = s.wifiEnc;
      if (s.vcardName) vcardName.value = s.vcardName;
      if (s.vcardPhone) vcardPhone.value = s.vcardPhone;
      if (s.vcardEmail) vcardEmail.value = s.vcardEmail;
      if (s.vcardOrg) vcardOrg.value = s.vcardOrg;
      if (s.fgColor) { qrFgColor.value = s.fgColor; fgHex.textContent = s.fgColor; }
      if (s.bgColor) { qrBgColor.value = s.bgColor; bgHex.textContent = s.bgColor; }
      if (s.ecc) qrEcc.value = s.ecc;
      if (s.size) qrSize.value = s.size;
    } catch {
      // ignore
    }
  }

  // Save on any change
  document.querySelectorAll('input, select, textarea').forEach(el => {
    el.addEventListener('change', saveSettings);
    el.addEventListener('input', saveSettings);
  });

  /* ---------- Init ---------- */
  function init() {
    loadSettings();
    generateQR();
    initAnimations();
  }

  // Wait for QRCode library to load
  if (typeof QRCode !== 'undefined') {
    init();
  } else {
    window.addEventListener('load', init);
  }
})();
