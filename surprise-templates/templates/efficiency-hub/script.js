/* efficiency-hub — E15 — Efficiency & Finance Hub */
(function(){
  'use strict';

  /* ── Theme Toggle ── */
  const toggle=document.getElementById('themeToggle');
  const root=document.documentElement;
  function setTheme(t){
    root.setAttribute('data-theme',t);
    toggle.textContent=t==='dark'?'🌙':'☀️';
    localStorage.setItem('efficiency-hub-theme',t);
    rebuildChart();
  }
  toggle.addEventListener('click',()=>setTheme(root.getAttribute('data-theme')==='dark'?'light':'dark'));
  const saved=localStorage.getItem('efficiency-hub-theme');
  if(saved)setTheme(saved);
  else if(matchMedia('(prefers-color-scheme:dark)').matches)setTheme('dark');

  /* ── Greeting ── */
  const now=new Date();
  const hour=now.getHours();
  let greet='Good evening';
  if(hour<12)greet='Good morning';
  else if(hour<18)greet='Good afternoon';
  document.getElementById('greeting').textContent=greet;
  document.getElementById('todayDate').textContent=now.toLocaleDateString('en-US',{
    weekday:'long',year:'numeric',month:'long',day:'numeric'
  });

  /* ── Sidebar Avatar ── */
  const userName=document.querySelector('.sidebar__username')?.textContent||'User';
  const letter=userName.replace(/[{}]/g,'').trim().charAt(0).toUpperCase();
  document.getElementById('sidebarAvatar').textContent=letter||'U';

  /* ── Mock Data ── */
  const scheduleData=[
    {time:'09:00',title:'Team Standup',tag:'meeting'},
    {time:'10:30',title:'Review PR #142',tag:'task'},
    {time:'12:00',title:'Lunch Break',tag:'personal'},
    {time:'14:00',title:'Product Strategy Call',tag:'meeting'},
    {time:'15:30',title:'Deploy v2.4.1',tag:'task'},
    {time:'17:00',title:'Gym Session',tag:'personal'},
    {time:'19:00',title:'Read "Zero to One"',tag:'personal'}
  ];

  const portfolioData=[
    {name:'Bitcoin',symbol:'BTC',holdings:0.45,price:67420,change:2.3},
    {name:'Ethereum',symbol:'ETH',holdings:3.2,price:3580,change:-1.1},
    {name:'Solana',symbol:'SOL',holdings:25,price:172,change:5.8},
    {name:'Chainlink',symbol:'LINK',holdings:150,price:18.4,change:3.2},
    {name:'Arbitrum',symbol:'ARB',holdings:500,price:1.28,change:-0.7}
  ];

  const remindersData=[
    {icon:'📈',text:'BTC price alert: above $68,000',time:'Active'},
    {icon:'📅',text:'Quarterly tax filing deadline',time:'In 3 days'},
    {icon:'🔔',text:'Renew domain: starchild.dev',time:'In 5 days'},
    {icon:'💰',text:'ETH staking rewards claim',time:'Tomorrow'},
    {icon:'📊',text:'Monthly portfolio rebalance',time:'In 7 days'},
    {icon:'🎯',text:'Complete Rust course Module 5',time:'This week'}
  ];

  const summaryData={
    labels:['Tasks Done','Meetings','Focus Hours','Emails','Commits','Alerts'],
    values:[8,4,5.5,12,6,3]
  };

  /* ── Populate Hero Stats ── */
  const pendingTasks=scheduleData.filter(s=>s.tag==='task').length;
  const totalPortfolio=portfolioData.reduce((s,t)=>s+t.holdings*t.price,0);
  const activeAlerts=remindersData.filter(r=>r.time==='Active').length;
  document.getElementById('pendingTasks').textContent=pendingTasks;
  document.getElementById('portfolioValue').textContent='$'+fmt(totalPortfolio);
  document.getElementById('activeAlerts').textContent=activeAlerts;

  /* ── Render Schedule ── */
  function renderSchedule(containerId,limit){
    const ul=document.getElementById(containerId);
    if(!ul)return;
    const items=limit?scheduleData.slice(0,limit):scheduleData;
    ul.innerHTML='';
    items.forEach(s=>{
      const li=document.createElement('li');
      li.className='schedule-item';
      li.innerHTML=`
        <span class="schedule-item__time">${s.time}</span>
        <span class="schedule-item__title">${s.title}</span>
        <span class="schedule-item__tag schedule-item__tag--${s.tag}">${s.tag}</span>
      `;
      ul.appendChild(li);
    });
  }
  renderSchedule('scheduleListMini',4);
  renderSchedule('scheduleListFull');

  /* ── Render Portfolio Mini ── */
  function renderPortfolioMini(){
    const container=document.getElementById('portfolioMini');
    if(!container)return;
    container.innerHTML='';
    portfolioData.slice(0,3).forEach(t=>{
      const val=t.holdings*t.price;
      const changeClass=t.change>=0?'up':'down';
      const changeSign=t.change>=0?'+':'';
      const div=document.createElement('div');
      div.className='portfolio-row';
      div.innerHTML=`
        <span class="portfolio-row__name">${t.name} <span class="portfolio-row__symbol">${t.symbol}</span></span>
        <span class="portfolio-row__value">$${fmt(val)}</span>
        <span class="portfolio-row__change portfolio-row__change--${changeClass}">${changeSign}${t.change}%</span>
      `;
      container.appendChild(div);
    });
  }
  renderPortfolioMini();

  /* ── Render Portfolio Table ── */
  function renderPortfolioTable(){
    const tbody=document.getElementById('portfolioBody');
    if(!tbody)return;
    tbody.innerHTML='';
    portfolioData.forEach(t=>{
      const val=t.holdings*t.price;
      const changeClass=t.change>=0?'up':'down';
      const changeSign=t.change>=0?'+':'';
      const tr=document.createElement('tr');
      tr.innerHTML=`
        <td style="font-weight:600;color:var(--text-primary)">${t.name} (${t.symbol})</td>
        <td>${t.holdings}</td>
        <td>$${fmt(t.price)}</td>
        <td>$${fmt(val)}</td>
        <td class="portfolio-row__change--${changeClass}" style="color:var(--${t.change>=0?'positive':'negative'})">${changeSign}${t.change}%</td>
      `;
      tbody.appendChild(tr);
    });
  }
  renderPortfolioTable();

  /* ── Render Reminders ── */
  function renderReminders(containerId,limit){
    const ul=document.getElementById(containerId);
    if(!ul)return;
    const items=limit?remindersData.slice(0,limit):remindersData;
    ul.innerHTML='';
    items.forEach(r=>{
      const li=document.createElement('li');
      li.className='reminder-item';
      li.innerHTML=`
        <span class="reminder-item__icon">${r.icon}</span>
        <span class="reminder-item__text">${r.text}</span>
        <span class="reminder-item__time">${r.time}</span>
      `;
      ul.appendChild(li);
    });
  }
  renderReminders('reminderListMini',3);
  renderReminders('reminderListFull');

  /* ── Render Quick Stats ── */
  function renderQuickStats(){
    const container=document.getElementById('quickStats');
    if(!container)return;
    const stats=[
      {val:scheduleData.length,label:'Events Today'},
      {val:portfolioData.length,label:'Tokens Tracked'},
      {val:remindersData.length,label:'Active Reminders'},
      {val:'5.5h',label:'Focus Time'}
    ];
    container.innerHTML='';
    stats.forEach(s=>{
      const div=document.createElement('div');
      div.className='quick-stat';
      div.innerHTML=`
        <span class="quick-stat__val">${s.val}</span>
        <span class="quick-stat__label">${s.label}</span>
      `;
      container.appendChild(div);
    });
  }
  renderQuickStats();

  /* ── Sidebar Navigation ── */
  const navLinks=document.querySelectorAll('.sidebar__link');
  const panels=document.querySelectorAll('.panel');
  navLinks.forEach(link=>{
    link.addEventListener('click',()=>{
      const target=link.dataset.panel;
      navLinks.forEach(l=>l.classList.remove('sidebar__link--active'));
      link.classList.add('sidebar__link--active');
      panels.forEach(p=>{
        p.classList.remove('panel--active');
        if(p.id==='panel'+capitalize(target))p.classList.add('panel--active');
      });
      /* Re-animate panels */
      animatePanels();
      if(target==='summary')rebuildChart();
    });
  });

  /* ── Quick Action Buttons ── */
  document.querySelectorAll('.action-btn').forEach(btn=>{
    btn.addEventListener('click',()=>{
      const action=btn.dataset.action;
      const map={
        addEvent:'calendar',
        setReminder:'reminders',
        viewPortfolio:'portfolio',
        priceAlert:'reminders',
        dailyReport:'summary',
        focusMode:'overview'
      };
      const target=map[action]||'overview';
      const navBtn=document.querySelector(`.sidebar__link[data-panel="${target}"]`);
      if(navBtn)navBtn.click();
    });
  });

  /* ── Chart — Daily Summary (Bar) ── */
  let summaryChart;

  function getChartColors(){
    const isDark=root.getAttribute('data-theme')==='dark';
    return{
      text:isDark?'#f0ece6':'#1a1814',
      grid:isDark?'rgba(240,236,230,.06)':'rgba(26,24,20,.05)',
      accent:isDark?'#38bdf8':'#0284c7',
      accentBg:isDark?'rgba(56,189,248,.20)':'rgba(2,132,199,.15)',
      barColors:['#0284c7','#0ea5e9','#38bdf8','#7dd3fc','#bae6fd','#e0f2fe']
    };
  }

  function buildChart(){
    const c=getChartColors();
    const ctx=document.getElementById('summaryChart');
    if(!ctx)return;
    summaryChart=new Chart(ctx.getContext('2d'),{
      type:'bar',
      data:{
        labels:summaryData.labels,
        datasets:[{
          label:'Today',
          data:summaryData.values,
          backgroundColor:c.barColors,
          borderRadius:4,
          borderSkipped:false,
          barPercentage:0.6
        }]
      },
      options:{
        responsive:true,maintainAspectRatio:false,
        scales:{
          x:{ticks:{color:c.text,font:{family:'Karla',size:11}},grid:{display:false}},
          y:{ticks:{color:c.text,font:{family:'IBM Plex Mono',size:10}},grid:{color:c.grid},beginAtZero:true}
        },
        plugins:{
          legend:{display:false},
          tooltip:{
            backgroundColor:root.getAttribute('data-theme')==='dark'?'#262220':'#ffffff',
            titleColor:c.text,bodyColor:c.text,
            borderColor:c.accent,borderWidth:1,
            bodyFont:{family:'IBM Plex Mono'}
          }
        }
      }
    });
  }

  function rebuildChart(){
    if(summaryChart)summaryChart.destroy();
    buildChart();
  }

  buildChart();

  /* ── GSAP Entrance — D4 Stagger Top-to-Bottom ── */
  function animatePanels(){
    if(matchMedia('(prefers-reduced-motion:reduce)').matches){
      document.querySelectorAll('.hub-panel').forEach(el=>{
        el.style.transform='none';el.style.opacity='1';
      });
      return;
    }
    const activePanel=document.querySelector('.panel--active');
    if(!activePanel)return;
    const cards=activePanel.querySelectorAll('.hub-panel');
    cards.forEach(c=>{c.style.opacity='0';c.style.transform='translateY(12px)'});
    gsap.to(cards,{
      y:0,opacity:1,duration:0.45,stagger:0.08,ease:'power2.out',delay:0.1
    });
  }

  if(!matchMedia('(prefers-reduced-motion:reduce)').matches){
    gsap.registerPlugin(ScrollTrigger);
    /* Initial animation */
    gsap.from('.inline-hero',{y:20,opacity:0,duration:0.5,ease:'power2.out',delay:0.1});
    animatePanels();
  }else{
    document.querySelectorAll('.hub-panel').forEach(el=>{
      el.style.transform='none';el.style.opacity='1';
    });
  }

  /* ── Helpers ── */
  function fmt(n){
    if(typeof n==='string')return n;
    if(n>=1e6)return(n/1e6).toFixed(2)+'M';
    if(n>=1e3)return(n/1e3).toFixed(n>=1e4?1:2)+'K';
    return n.toFixed(2);
  }

  function capitalize(s){return s.charAt(0).toUpperCase()+s.slice(1)}

})();
