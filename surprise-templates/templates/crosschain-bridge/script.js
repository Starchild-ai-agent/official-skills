/* crosschain-bridge — E12 — Cross-Chain Bridge Optimizer */
(function(){
  'use strict';

  /* ── Theme Toggle ── */
  const toggle=document.getElementById('themeToggle');
  const root=document.documentElement;
  function setTheme(t){
    root.setAttribute('data-theme',t);
    toggle.textContent=t==='dark'?'🌙':'☀️';
    localStorage.setItem('xchain-theme',t);
    rebuildChart();
  }
  toggle.addEventListener('click',()=>setTheme(root.getAttribute('data-theme')==='dark'?'light':'dark'));
  const saved=localStorage.getItem('xchain-theme');
  if(saved)setTheme(saved);
  else if(matchMedia('(prefers-color-scheme:dark)').matches)setTheme('dark');

  /* ── Chain Data ── */
  const chains={
    ethereum:{name:'Ethereum',icon:'E',color:'#627eea'},
    polygon:{name:'Polygon',icon:'P',color:'#8247e5'},
    arbitrum:{name:'Arbitrum',icon:'A',color:'#28a0f0'},
    optimism:{name:'Optimism',icon:'O',color:'#ff0420'},
    bsc:{name:'BNB Chain',icon:'B',color:'#f0b90b'},
    avalanche:{name:'Avalanche',icon:'Av',color:'#e84142'},
    base:{name:'Base',icon:'Ba',color:'#0052ff'}
  };

  /* ── Bridge Route Data ── */
  const bridges=[
    {name:'Stargate',fee:2.45,time:'2-5 min',safety:92,maxAmount:'$500K',speed:3},
    {name:'Across',fee:1.80,time:'1-3 min',safety:88,maxAmount:'$250K',speed:2},
    {name:'Hop Protocol',fee:3.10,time:'5-15 min',safety:85,maxAmount:'$100K',speed:10},
    {name:'Wormhole',fee:2.90,time:'3-8 min',safety:78,maxAmount:'$1M',speed:5},
    {name:'Synapse',fee:2.20,time:'3-10 min',safety:82,maxAmount:'$200K',speed:6},
    {name:'Celer cBridge',fee:1.95,time:'5-20 min',safety:80,maxAmount:'$150K',speed:12},
    {name:'Multichain',fee:3.50,time:'10-30 min',safety:70,maxAmount:'$500K',speed:20},
    {name:'LayerZero',fee:1.60,time:'1-2 min',safety:90,maxAmount:'$300K',speed:1.5}
  ];

  /* Sort by fee (best first) */
  const sortedBridges=[...bridges].sort((a,b)=>a.fee-b.fee);
  const bestBridge=sortedBridges[0];

  /* ── Hero Chain Selectors ── */
  const sourceSelect=document.getElementById('sourceSelect');
  const targetSelect=document.getElementById('targetSelect');
  const sourceIcon=document.getElementById('sourceIcon');
  const sourceName=document.getElementById('sourceName');
  const targetIcon=document.getElementById('targetIcon');
  const targetName=document.getElementById('targetName');

  function updateHero(){
    const s=chains[sourceSelect.value];
    const t=chains[targetSelect.value];
    sourceIcon.textContent=s.icon;
    sourceName.textContent=s.name;
    targetIcon.textContent=t.icon;
    targetName.textContent=t.name;
    sourceIcon.style.borderColor=s.color;
    sourceIcon.style.color=s.color;
    targetIcon.style.borderColor=t.color;
    targetIcon.style.color=t.color;
  }
  sourceSelect.addEventListener('change',updateHero);
  targetSelect.addEventListener('change',updateHero);
  updateHero();

  /* ── Render Route Table ── */
  const routeBody=document.getElementById('routeTableBody');
  sortedBridges.forEach(b=>{
    const tr=document.createElement('tr');
    const isBest=b.name===bestBridge.name;
    if(isBest)tr.classList.add('best-route');
    tr.innerHTML=`
      <td>
        <strong>${b.name}</strong>
        ${isBest?'<span class="best-badge">Best</span>':''}
      </td>
      <td style="font-family:var(--font-data);font-weight:600">$${b.fee.toFixed(2)}</td>
      <td>${b.time}</td>
      <td>
        <div class="safety-bar">
          <div class="safety-bar__track"><div class="safety-bar__fill" style="width:${b.safety}%"></div></div>
          <span class="safety-bar__text">${b.safety}/100</span>
        </div>
      </td>
      <td style="font-family:var(--font-data)">${b.maxAmount}</td>
      <td><button style="padding:4px 12px;border-radius:4px;border:1px solid var(--accent);background:transparent;color:var(--accent);font-size:.78rem;font-weight:600;cursor:pointer;font-family:var(--font-body)">Use</button></td>
    `;
    routeBody.appendChild(tr);
  });

  /* ── Fee Comparison Chart ── */
  const isDark=()=>root.getAttribute('data-theme')==='dark';
  const gridColor=()=>isDark()?'rgba(255,255,255,.06)':'rgba(0,0,0,.06)';
  const textColor=()=>isDark()?'#9ca3b4':'#5a6275';
  const accentColor=()=>isDark()?'#fb923c':'#ea580c';

  let feeChart;
  function rebuildChart(){
    const ctx=document.getElementById('feeChart').getContext('2d');
    if(feeChart)feeChart.destroy();
    const colors=sortedBridges.map(b=>b.name===bestBridge.name?accentColor():(isDark()?'rgba(255,255,255,.15)':'rgba(0,0,0,.1)'));
    const borderColors=sortedBridges.map(b=>b.name===bestBridge.name?accentColor():(isDark()?'rgba(255,255,255,.25)':'rgba(0,0,0,.2)'));

    feeChart=new Chart(ctx,{
      type:'bar',
      data:{
        labels:sortedBridges.map(b=>b.name),
        datasets:[{
          label:'Fee (USD)',
          data:sortedBridges.map(b=>b.fee),
          backgroundColor:colors,
          borderColor:borderColors,
          borderWidth:1,
          borderRadius:4
        }]
      },
      options:{
        responsive:true,maintainAspectRatio:false,
        indexAxis:'y',
        plugins:{
          legend:{display:false},
          tooltip:{
            callbacks:{
              label:ctx=>'$'+ctx.parsed.x.toFixed(2)
            }
          }
        },
        scales:{
          x:{grid:{color:gridColor()},ticks:{color:textColor(),font:{family:'JetBrains Mono',size:11},callback:v=>'$'+v}},
          y:{grid:{display:false},ticks:{color:textColor(),font:{family:'Karla',size:12}}}
        }
      }
    });
  }
  rebuildChart();

  /* ── Recommended Routes ── */
  const recGrid=document.getElementById('recGrid');
  const recommendations=[
    {bridge:sortedBridges[0],tag:'Cheapest',tagClass:'bridge-panel__tag--best'},
    {bridge:[...bridges].sort((a,b)=>a.speed-b.speed)[0],tag:'Fastest',tagClass:'bridge-panel__tag--fast'},
    {bridge:[...bridges].sort((a,b)=>b.safety-a.safety)[0],tag:'Safest',tagClass:'bridge-panel__tag--fast'}
  ];

  recommendations.forEach(rec=>{
    const panel=document.createElement('div');
    panel.className='bridge-panel'+(rec.tag==='Cheapest'?' bridge-panel--best':'');
    panel.innerHTML=`
      <div class="bridge-panel__header">
        <span class="bridge-panel__name">${rec.bridge.name}</span>
        <span class="bridge-panel__tag ${rec.tagClass}">${rec.tag}</span>
      </div>
      <div class="bridge-panel__stats">
        <div>
          <div class="bridge-panel__stat-value">$${rec.bridge.fee.toFixed(2)}</div>
          <div class="bridge-panel__stat-label">Fee</div>
        </div>
        <div>
          <div class="bridge-panel__stat-value">${rec.bridge.time}</div>
          <div class="bridge-panel__stat-label">Est. Time</div>
        </div>
        <div>
          <div class="bridge-panel__stat-value">${rec.bridge.safety}/100</div>
          <div class="bridge-panel__stat-label">Safety</div>
        </div>
      </div>
    `;
    recGrid.appendChild(panel);
  });

  /* ── Bridge History ── */
  const historyData=[
    {route:'ETH → ARB',bridge:'Stargate',amount:'1.5 ETH',status:'success',date:'2 hours ago'},
    {route:'ARB → OP',bridge:'Across',amount:'2,400 USDC',status:'success',date:'1 day ago'},
    {route:'ETH → POLY',bridge:'Hop Protocol',amount:'0.8 ETH',status:'success',date:'3 days ago'},
    {route:'BSC → ETH',bridge:'Wormhole',amount:'500 USDT',status:'pending',date:'5 min ago'},
    {route:'AVAX → ARB',bridge:'Synapse',amount:'120 AVAX',status:'success',date:'1 week ago'},
    {route:'ETH → BASE',bridge:'LayerZero',amount:'3.2 ETH',status:'success',date:'2 weeks ago'}
  ];

  const historyList=document.getElementById('historyList');
  historyData.forEach(h=>{
    const item=document.createElement('div');
    item.className='history-item';
    const statusClass=h.status==='success'?'history-item__status--success':'history-item__status--pending';
    item.innerHTML=`
      <span class="history-item__route">${h.route}</span>
      <span class="history-item__bridge">${h.bridge} · ${h.date}</span>
      <span class="history-item__amount">${h.amount}</span>
      <span class="history-item__status ${statusClass}">${h.status}</span>
    `;
    historyList.appendChild(item);
  });

  /* ── GSAP Animations ── */
  gsap.registerPlugin(ScrollTrigger);
  const prefersReduced=matchMedia('(prefers-reduced-motion:reduce)').matches;

  if(!prefersReduced){
    /* Hero panels */
    gsap.from('.hero__panel--source',{opacity:0,x:-40,duration:0.6,ease:'power2.out'});
    gsap.from('.hero__panel--target',{opacity:0,x:40,duration:0.6,ease:'power2.out'});
    gsap.from('.hero__divider',{opacity:0,scale:0.8,duration:0.5,delay:0.2,ease:'back.out(1.4)'});

    /* Route table rows — D8 translateX(40px) */
    gsap.utils.toArray('.route-table tbody tr').forEach((tr,i)=>{
      gsap.to(tr,{
        opacity:1,x:0,duration:0.4,delay:i*0.06,ease:'power2.out',
        scrollTrigger:{trigger:tr,start:'top 95%',toggleActions:'play none none none'}
      });
    });

    /* Bridge panels */
    gsap.utils.toArray('.bridge-panel').forEach((el,i)=>{
      gsap.from(el,{opacity:0,y:30,duration:0.5,delay:i*0.1,ease:'power2.out',
        scrollTrigger:{trigger:el,start:'top 90%'}
      });
    });

    /* History items */
    gsap.utils.toArray('.history-item').forEach((el,i)=>{
      gsap.from(el,{opacity:0,x:30,duration:0.4,delay:i*0.06,ease:'power2.out',
        scrollTrigger:{trigger:el,start:'top 94%'}
      });
    });

    /* Chart container */
    gsap.from('.chart-container',{opacity:0,y:20,duration:0.5,ease:'power2.out',
      scrollTrigger:{trigger:'.chart-container',start:'top 90%'}
    });
  }else{
    document.querySelectorAll('.route-table tbody tr').forEach(tr=>{tr.style.opacity=1;tr.style.transform='none'});
  }
})();
