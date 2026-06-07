/* ml-tracker — E11 — ML Experiment Tracker */
(function(){
  'use strict';

  /* ── Chart instances & helpers (hoisted for rebuildCharts) ── */
  let lossChart,radarChart;
  const root=document.documentElement;
  const isDark=()=>root.getAttribute('data-theme')==='dark';
  const gridColor=()=>isDark()?'rgba(255,255,255,.06)':'rgba(0,0,0,.06)';
  const textColor=()=>isDark()?'#a1a1aa':'#52525b';
  const accentColor=()=>isDark()?'#f472b6':'#ec4899';

  /* ── Theme Toggle ── */
  const toggle=document.getElementById('themeToggle');
  function setTheme(t){
    root.setAttribute('data-theme',t);
    toggle.textContent=t==='dark'?'🌙':'☀️';
    localStorage.setItem('ml-tracker-theme',t);
    rebuildCharts();
  }
  toggle.addEventListener('click',()=>setTheme(root.getAttribute('data-theme')==='dark'?'light':'dark'));
  const saved=localStorage.getItem('ml-tracker-theme');
  if(saved)setTheme(saved);
  else if(!matchMedia('(prefers-color-scheme:dark)').matches)setTheme('light');

  /* ── Mock Experiment Data ── */
  const experiments=[
    {id:'EXP-001',model:'ResNet-50',dataset:'ImageNet',accuracy:0.924,loss:0.218,status:'complete',duration:'4h 12m'},
    {id:'EXP-002',model:'ViT-B/16',dataset:'ImageNet',accuracy:0.938,loss:0.185,status:'complete',duration:'6h 45m'},
    {id:'EXP-003',model:'BERT-Large',dataset:'SQuAD 2.0',accuracy:0.891,loss:0.312,status:'complete',duration:'8h 20m'},
    {id:'EXP-004',model:'GPT-Neo 1.3B',dataset:'OpenWebText',accuracy:0.856,loss:0.445,status:'running',duration:'12h 30m+'},
    {id:'EXP-005',model:'EfficientNet-B4',dataset:'CIFAR-100',accuracy:0.912,loss:0.247,status:'complete',duration:'2h 55m'},
    {id:'EXP-006',model:'Whisper-Medium',dataset:'LibriSpeech',accuracy:0.945,loss:0.162,status:'complete',duration:'5h 10m'},
    {id:'EXP-007',model:'CLIP ViT-L/14',dataset:'LAION-400M',accuracy:0.872,loss:0.378,status:'running',duration:'18h 45m+'},
    {id:'EXP-008',model:'LLaMA-7B',dataset:'RedPajama',accuracy:0.834,loss:0.502,status:'queued',duration:'—'},
    {id:'EXP-009',model:'Stable Diffusion',dataset:'LAION-5B',accuracy:0.0,loss:0.089,status:'failed',duration:'3h 22m'},
    {id:'EXP-010',model:'DINOv2-G',dataset:'LVD-142M',accuracy:0.951,loss:0.142,status:'complete',duration:'24h 15m'}
  ];

  /* ── Stats Bar ── */
  const bestExp=experiments.filter(e=>e.accuracy>0).reduce((a,b)=>a.accuracy>b.accuracy?a:b);
  const avgAcc=experiments.filter(e=>e.accuracy>0).reduce((s,e)=>s+e.accuracy,0)/experiments.filter(e=>e.accuracy>0).length;
  const running=experiments.filter(e=>e.status==='running').length;

  document.getElementById('statTotal').textContent=experiments.length;
  document.getElementById('statBest').textContent=bestExp.model;
  document.getElementById('statAvgAcc').textContent=(avgAcc*100).toFixed(1)+'%';
  document.getElementById('statRunning').textContent=running;

  /* ── Render Experiment Table ── */
  const tbody=document.getElementById('expTableBody');
  const bestAcc=bestExp.accuracy;
  experiments.forEach(exp=>{
    const tr=document.createElement('tr');
    tr.className='experiment-row';
    const accClass=exp.accuracy===bestAcc&&exp.accuracy>0?'metric-best':'';
    const statusClass='status--'+exp.status;
    tr.innerHTML=`
      <td>${exp.id}</td>
      <td>${exp.model}</td>
      <td>${exp.dataset}</td>
      <td class="${accClass}">${exp.accuracy>0?(exp.accuracy*100).toFixed(1)+'%':'N/A'}</td>
      <td>${exp.loss.toFixed(3)}</td>
      <td><span class="status ${statusClass}">${exp.status}</span></td>
      <td>${exp.duration}</td>
    `;
    tbody.appendChild(tr);
  });

  /* ── Charts ── */
  function rebuildCharts(){
    /* Loss vs Epoch */
    const lossCtx=document.getElementById('lossChart').getContext('2d');
    if(lossChart)lossChart.destroy();
    const epochs=Array.from({length:50},(_, i)=>i+1);
    lossChart=new Chart(lossCtx,{
      type:'line',
      data:{
        labels:epochs,
        datasets:[
          {label:'ResNet-50',data:epochs.map(e=>0.9*Math.exp(-0.06*e)+0.2+Math.random()*0.02),borderColor:accentColor(),backgroundColor:'transparent',tension:0.3,pointRadius:0,borderWidth:2},
          {label:'ViT-B/16',data:epochs.map(e=>0.85*Math.exp(-0.07*e)+0.18+Math.random()*0.015),borderColor:isDark()?'#facc15':'#d97706',backgroundColor:'transparent',tension:0.3,pointRadius:0,borderWidth:2,borderDash:[4,4]},
          {label:'DINOv2-G',data:epochs.map(e=>0.8*Math.exp(-0.08*e)+0.14+Math.random()*0.01),borderColor:isDark()?'#4ade80':'#16a34a',backgroundColor:'transparent',tension:0.3,pointRadius:0,borderWidth:2}
        ]
      },
      options:{
        responsive:true,maintainAspectRatio:false,
        plugins:{legend:{labels:{color:textColor(),font:{family:'Azeret Mono',size:11}}}},
        scales:{
          x:{title:{display:true,text:'Epoch',color:textColor(),font:{family:'Azeret Mono',size:11}},grid:{color:gridColor()},ticks:{color:textColor(),font:{family:'Azeret Mono',size:10},maxTicksLimit:10}},
          y:{title:{display:true,text:'Loss',color:textColor(),font:{family:'Azeret Mono',size:11}},grid:{color:gridColor()},ticks:{color:textColor(),font:{family:'Azeret Mono',size:10}}}
        }
      }
    });

    /* Radar Chart */
    const radarCtx=document.getElementById('radarChart').getContext('2d');
    if(radarChart)radarChart.destroy();
    radarChart=new Chart(radarCtx,{
      type:'radar',
      data:{
        labels:['Accuracy','Speed','Memory','Scalability','Robustness','Interpretability'],
        datasets:[
          {label:'ResNet-50',data:[92,85,78,70,80,65],borderColor:accentColor(),backgroundColor:isDark()?'rgba(244,114,182,.12)':'rgba(236,72,153,.1)',pointRadius:3},
          {label:'ViT-B/16',data:[94,72,65,88,85,60],borderColor:isDark()?'#facc15':'#d97706',backgroundColor:isDark()?'rgba(250,204,21,.08)':'rgba(217,119,6,.06)',pointRadius:3},
          {label:'DINOv2-G',data:[95,60,55,92,90,70],borderColor:isDark()?'#4ade80':'#16a34a',backgroundColor:isDark()?'rgba(74,222,128,.08)':'rgba(22,163,74,.06)',pointRadius:3}
        ]
      },
      options:{
        responsive:true,maintainAspectRatio:false,
        plugins:{legend:{labels:{color:textColor(),font:{family:'Azeret Mono',size:11}}}},
        scales:{
          r:{
            grid:{color:gridColor()},
            angleLines:{color:gridColor()},
            pointLabels:{color:textColor(),font:{family:'Lexend',size:11}},
            ticks:{display:false},
            suggestedMin:0,suggestedMax:100
          }
        }
      }
    });
  }
  rebuildCharts();

  /* ── Papers ── */
  const papers=[
    {title:'Attention Is All You Need',authors:'Vaswani et al., 2017',venue:'NeurIPS',abstract:'We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.'},
    {title:'An Image is Worth 16x16 Words',authors:'Dosovitskiy et al., 2021',venue:'ICLR',abstract:'We show that a pure transformer applied directly to sequences of image patches can perform very well on image classification tasks.'},
    {title:'DINOv2: Learning Robust Visual Features',authors:'Oquab et al., 2024',venue:'TMLR',abstract:'We revisit existing approaches and combine different techniques to scale self-supervised pre-training in terms of data and model size.'},
    {title:'Scaling Data-Constrained Language Models',authors:'Muennighoff et al., 2024',venue:'NeurIPS',abstract:'We investigate scaling language models in data-constrained regimes, finding that training for multiple epochs with careful regularization can match single-epoch performance.'},
    {title:'FlashAttention-2: Faster Attention',authors:'Dao, 2023',venue:'ICLR',abstract:'We propose FlashAttention-2, with better parallelism and work partitioning to achieve 2x speedup over FlashAttention.'}
  ];

  const papersList=document.getElementById('papersList');
  papers.forEach(p=>{
    const card=document.createElement('div');
    card.className='paper-card';
    card.innerHTML=`
      <div class="paper-card__title">${p.title}</div>
      <div class="paper-card__meta">${p.authors} · ${p.venue}</div>
      <div class="paper-card__abstract">${p.abstract}</div>
    `;
    papersList.appendChild(card);
  });

  /* ── GitHub Repos (API call with fallback) ── */
  const reposGrid=document.getElementById('reposGrid');
  const fallbackRepos=[
    {name:'pytorch/pytorch',description:'Tensors and Dynamic neural networks in Python with strong GPU acceleration',stars:82400,language:'Python'},
    {name:'huggingface/transformers',description:'State-of-the-art Machine Learning for PyTorch, TensorFlow, and JAX',stars:136000,language:'Python'},
    {name:'openai/whisper',description:'Robust Speech Recognition via Large-Scale Weak Supervision',stars:72000,language:'Python'},
    {name:'facebookresearch/dinov2',description:'PyTorch code and models for DINOv2 self-supervised learning method',stars:9200,language:'Python'},
    {name:'vllm-project/vllm',description:'A high-throughput and memory-efficient inference engine for LLMs',stars:38000,language:'Python'},
    {name:'mlflow/mlflow',description:'Open source platform for the machine learning lifecycle',stars:19000,language:'Python'}
  ];

  function renderRepos(repos){
    reposGrid.innerHTML='';
    repos.forEach(r=>{
      const card=document.createElement('div');
      card.className='repo-card';
      const stars=typeof r.stars==='number'?r.stars:r.stargazers_count||0;
      const name=r.full_name||r.name;
      const desc=r.description||'No description';
      const lang=r.language||'—';
      card.innerHTML=`
        <div class="repo-card__name">${name}</div>
        <div class="repo-card__desc">${desc}</div>
        <div class="repo-card__stats">
          <span>★ ${stars>=1000?(stars/1000).toFixed(1)+'k':stars}</span>
          <span>${lang}</span>
        </div>
      `;
      reposGrid.appendChild(card);
    });
  }

  const ghUser='{{GITHUB_USERNAME}}';
  if(ghUser&&!ghUser.startsWith('{{')){
    fetch('https://api.github.com/search/repositories?q=machine+learning+language:python&sort=stars&per_page=6')
      .then(r=>r.json())
      .then(d=>{if(d.items)renderRepos(d.items);else renderRepos(fallbackRepos)})
      .catch(()=>renderRepos(fallbackRepos));
  }else{
    renderRepos(fallbackRepos);
  }

  /* ── GSAP Animations ── */
  gsap.registerPlugin(ScrollTrigger);
  const prefersReduced=matchMedia('(prefers-reduced-motion:reduce)').matches;

  if(!prefersReduced){
    /* Stats bar */
    gsap.from('.stats-bar__item',{opacity:0,y:-20,duration:0.5,stagger:0.1,ease:'power2.out'});

    /* Experiment rows — D3 translateX(30px) */
    gsap.utils.toArray('.experiment-row').forEach((row,i)=>{
      gsap.to(row,{
        opacity:1,x:0,duration:0.4,delay:i*0.05,ease:'power2.out',
        scrollTrigger:{trigger:row,start:'top 95%',toggleActions:'play none none none'}
      });
    });

    /* Chart panels */
    gsap.utils.toArray('.chart-panel').forEach(el=>{
      gsap.from(el,{opacity:0,y:30,duration:0.5,ease:'power2.out',
        scrollTrigger:{trigger:el,start:'top 90%'}
      });
    });

    /* Paper cards */
    gsap.utils.toArray('.paper-card').forEach((el,i)=>{
      gsap.from(el,{opacity:0,x:30,duration:0.4,delay:i*0.08,ease:'power2.out',
        scrollTrigger:{trigger:el,start:'top 92%'}
      });
    });

    /* Repo cards */
    gsap.utils.toArray('.repo-card').forEach((el,i)=>{
      gsap.from(el,{opacity:0,scale:0.95,duration:0.4,delay:i*0.06,ease:'power2.out',
        scrollTrigger:{trigger:el,start:'top 92%'}
      });
    });
  }else{
    document.querySelectorAll('.experiment-row').forEach(r=>{r.style.opacity=1;r.style.transform='none'});
  }
})();
