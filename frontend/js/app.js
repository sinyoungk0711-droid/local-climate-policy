const $ = (sel, root=document) => root.querySelector(sel);
const $$ = (sel, root=document) => [...root.querySelectorAll(sel)];

const metricFallback = {
  temp: {label:'평균기온 (°C)', title:'연도별 평균기온 추이'},
  rain: {label:'강수량 (mm)', title:'연도별 강수량 추이'},
  heat: {label:'폭염일수 (일)', title:'연도별 폭염일수 추이'},
  tropical: {label:'열대야일수 (일)', title:'연도별 열대야일수 추이'}
};
let climateChart = null;
let impactChart = null;
let map = null;
let mapInitialized = false;

function showScreen(name) {
  $$('.screen').forEach(el => el.classList.toggle('active', el.id === `screen-${name}`));
  $$('.nav-link').forEach(el => el.classList.toggle('active', el.dataset.screen === name || (name === 'detail' && el.dataset.screen === 'issues') || (name === 'impact' && el.dataset.screen === 'policies')));
  $('.main-nav').classList.remove('open');
  if (name === 'issues') setTimeout(initMap, 80);
  if (name === 'climate') setTimeout(renderClimateChart, 80);
  if (name === 'impact') setTimeout(renderImpactChart, 80);
  window.scrollTo({top:0,behavior:'smooth'});
}
$$('[data-screen]').forEach(el => el.addEventListener('click', () => showScreen(el.dataset.screen)));
$('#mobileMenu').addEventListener('click', () => $('.main-nav').classList.toggle('open'));
$('#focusSearch').addEventListener('click', () => { showScreen('policies'); $('#policySearch').focus(); });

function setRegion(region) {
  $('#regionSelect').value = region;
  $('#climateRegion').value = region;
  $('#homeRegionLabel').textContent = region + ' · 기상청 자료';
  $('#temperature').textContent = '실제 자료는 기후 분석에서 조회';
  $$('.chip').forEach(b => b.classList.toggle('selected', b.dataset.region === region));
}
$$('.chip').forEach(b => b.addEventListener('click', () => setRegion(b.dataset.region)));

async function renderClimateChart() {
  const ctx = $('#climateChart');
  if (!ctx) return;
  if (!window.Chart) {
    const note = ctx.parentElement.querySelector('.chart-load-note') || document.createElement('p');
    note.className = 'chart-load-note footnote';
    note.textContent = '그래프 라이브러리를 불러오지 못했습니다. 인터넷 연결을 확인한 뒤 새로고침해 주세요.';
    if (!note.parentElement) ctx.insertAdjacentElement('afterend', note);
    return;
  }
  const key = $('#metricSelect').value, metric = metricFallback[key];
  const period = Number($('#periodSelect').value);
  const region = $('#climateRegion').value || $('#regionSelect').value || '서울특별시';
  const codes = {'서울특별시':'11','부산광역시':'26','대구광역시':'27','광주광역시':'29','대전광역시':'30','제주특별자치도':'50'};
  const endYear = new Date().getFullYear() - 1, startYear = endYear - period + 1;
  $('#chartTitle').textContent = metric.title;
  $('#chartLegend').textContent = metric.label + ' · 기상청 ASOS / MySQL';
  try {
    const url = 'http://127.0.0.1:8000/api/climate?region_code=' + encodeURIComponent(codes[region] || '11') + '&metric=' + key + '&start_year=' + startYear + '&end_year=' + endYear;
    const response = await fetch(url), data = await response.json();
    if (!response.ok) throw new Error(data.detail || '기후 API 요청 실패');
    const items = data.items || [], labels = items.map(x => String(x.year)), values = items.map(x => x.value);
    const note = ctx.parentElement.querySelector('.chart-load-note') || document.createElement('p');
    note.className = 'chart-load-note footnote'; note.textContent = data.notice || '';
    if (!note.parentElement) ctx.insertAdjacentElement('afterend', note);
    if (climateChart) climateChart.destroy();
    climateChart = new Chart(ctx, {type:'line',data:{labels:labels,datasets:[{label:metric.label,data:values,borderColor:'#2176ee',backgroundColor:'rgba(33,118,238,.12)',fill:true,tension:.32,spanGaps:false,pointRadius:3}]},
      options:{responsive:true,interaction:{intersect:false,mode:'index'},plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>c.parsed.y == null ? '자료 없음' : c.dataset.label + ': ' + c.parsed.y.toLocaleString()}}},scales:{y:{beginAtZero:key!=='temp',grid:{color:'#edf2f8'}},x:{grid:{display:false}}}}});
  } catch (error) {
    if (climateChart) { climateChart.destroy(); climateChart = null; }
    const note = ctx.parentElement.querySelector('.chart-load-note') || document.createElement('p');
    note.className = 'chart-load-note footnote';
    note.textContent = '실제 기후 자료를 불러오지 못했습니다: ' + error.message + '. FastAPI·MySQL·공식 API 설정을 확인하세요.';
    if (!note.parentElement) ctx.insertAdjacentElement('afterend', note);
  }
}
$('#metricSelect').addEventListener('change', renderClimateChart);
$('#periodSelect').addEventListener('change', renderClimateChart);
$('#climateRegion').addEventListener('change', e => { setRegion(e.target.value); renderClimateChart(); });
$('#regionSelect').addEventListener('change', e => { setRegion(e.target.value); renderClimateChart(); });

const issueInfo = {
  1:{title:'도심 폭염·열섬 문제',subtitle:'기온, 녹지, 토지이용 자료를 함께 확인해야 합니다.',category:'폭염·도시환경'},
  2:{title:'집중호우·침수 문제',subtitle:'강수량, 침수 이력, 배수시설 자료를 확인해야 합니다.',category:'재난안전'},
  3:{title:'생활권 녹지 접근성',subtitle:'공원 위치와 주민 접근성을 분석할 수 있습니다.',category:'환경·녹지'},
  4:{title:'기후 취약계층',subtitle:'인구·복지 통계와 기후 위험을 함께 살펴봅니다.',category:'기후적응'}
};
$$('[data-issue]').forEach(el => el.addEventListener('click', () => {
  const info = issueInfo[el.dataset.issue] || issueInfo[1];
  $('#issueDetailTitle').textContent = info.title;
  $('#issueDetailSubtitle').textContent = info.subtitle;
  $('#issueCategory').textContent = info.category;
  showScreen('detail');
}));

function initMap() {
  const node = $('#issueMap');
  if (!node || !window.L) {
    if (node) node.innerHTML = '<div style="padding:24px">지도를 불러오려면 인터넷 연결이 필요합니다.</div>';
    return;
  }
  if (!mapInitialized) {
    map = L.map(node).setView([37.5665,126.9780], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
    const points = [
      [37.5665,126.9780,'도심 폭염·열섬',1,'#ef5350'],
      [37.5512,126.9882,'집중호우·침수',2,'#2788ef'],
      [37.5796,126.9770,'생활권 녹지',3,'#18a56d'],
      [37.5245,127.0276,'기후 취약계층',4,'#8b5bd6'],
      [37.5700,127.0200,'도심 폭염·열섬',1,'#ef5350'],
      [37.5450,126.9500,'집중호우·침수',2,'#2788ef']
    ];
    issueMarkers = points.map(p => {
      const category = ({1:'heat',2:'flood',3:'green',4:'people'})[p[3]];
      const marker = L.circleMarker([p[0],p[1]],{radius:8,color:p[4],fillColor:p[4],fillOpacity:.8,weight:2}).addTo(map)
        .bindPopup(`<b>${p[2]}</b><br><small>시연용 마커 · 실제 위험 위치 아님</small><br><button onclick="window.openIssue(${p[3]})">상세 보기</button>`);
      return {marker, category};
    });
    applyIssueFilter(activeIssueFilter);
    mapInitialized = true;
  } else {
    setTimeout(() => map.invalidateSize(), 100);
  }
}
window.openIssue = id => {
  const info = issueInfo[id] || issueInfo[1];
  $('#issueDetailTitle').textContent = info.title;
  $('#issueDetailSubtitle').textContent = info.subtitle;
  $('#issueCategory').textContent = info.category;
  showScreen('detail');
};
let activeIssueFilter = 'all';
let issueMarkers = [];
function applyIssueFilter(filter) {
  activeIssueFilter = filter;
  $$('.filter-chip').forEach(b => b.classList.toggle('active', b.dataset.filter === filter));
  $$('.issue-detail-card').forEach(card => {
    const category = ({1:'heat',2:'flood',3:'green',4:'people'})[card.dataset.issue];
    card.classList.toggle('hidden', filter !== 'all' && category !== filter);
  });
  issueMarkers.forEach(({marker, category}) => {
    const visible = filter === 'all' || category === filter;
    marker.setStyle({opacity: visible ? 1 : 0, fillOpacity: visible ? 0.8 : 0});
    if (visible) marker.addTo(map);
    else marker.remove();
  });
}
$$('.filter-chip').forEach(btn => btn.addEventListener('click', () => applyIssueFilter(btn.dataset.filter)));

function filterPolicies() {
  const q = $('#policySearch').value.trim().toLowerCase();
  const cat = $('#policyCategory').value;
  const region = $('#policyRegion').value;
  let count = 0;
  $$('.policy-card').forEach(card => {
    // Demo policy cards have no verified region assignment. Do not present them as region-specific.
    const regionMatch = region === '전체 지역' || card.dataset.region === region;
    const visible = regionMatch &&
      (cat === 'all' || card.dataset.category === cat) &&
      (card.dataset.search + ' ' + card.innerText).toLowerCase().includes(q);
    card.classList.toggle('hidden', !visible);
    if (visible) count++;
  });
  $('#policyEmpty').classList.toggle('hidden', count > 0);
  $('#policyEmpty').textContent = region !== '전체 지역' && count === 0
    ? '선택한 지역에 연결된 검증된 정책 자료가 없습니다. 현재 정책 카드는 지역 미지정 예시입니다.'
    : '검색 결과가 없습니다. 검색어나 분야를 바꿔보세요.';
}
$('#policyRegion').addEventListener('change', filterPolicies);
$('#policySearch').addEventListener('input', filterPolicies);
$('#policyCategory').addEventListener('change', filterPolicies);
$$('.policy-impact').forEach(btn => btn.addEventListener('click', () => {
  $('#impactPolicy').value = btn.dataset.policy;
  showScreen('impact');
  renderImpactTable();
}));

const impactSamples = {
  green:{temp:[34.2,32.8],green:[18,24],shelter:[35,52],flood:[15,9]},
  heat:{temp:[34.5,33.9],green:[18,19],shelter:[35,52],flood:[15,14]},
  flood:{temp:[34.2,34.0],green:[18,18],shelter:[35,38],flood:[15,9]}
};
const metricNames = {temp:['평균기온','°C'],green:['녹지 면적 비율','%'],shelter:['쉼터 수','곳'],flood:['침수 신고 건수','건']};
function renderImpactTable() {
  const policy = $('#impactPolicy').value;
  const metric = $('#impactMetric').value;
  const values = impactSamples[policy][metric];
  const diff = values[1]-values[0];
  const pct = values[0] === 0 ? null : diff/values[0]*100;
  const [name,unit] = metricNames[metric];
  $('#impactTableBody').innerHTML = `<tr><td>${name} (${unit})</td><td>${values[0]} ${unit}</td><td>${values[1]} ${unit}</td><td>${diff>0?'+':''}${Number(diff.toFixed(2))} ${unit}</td><td>${pct===null?'계산 불가':`${pct>0?'+':''}${pct.toFixed(1)}%`}</td></tr>`;
  renderImpactChart();
}
function renderImpactChart() {
  const ctx = $('#impactChart');
  if (!ctx) return;
  if (!window.Chart) {
    const note = ctx.parentElement.querySelector('.chart-load-note') || document.createElement('p');
    note.className = 'chart-load-note footnote';
    note.textContent = '그래프 라이브러리를 불러오지 못했습니다. 인터넷 연결을 확인한 뒤 페이지를 새로고침해 주세요.';
    if (!note.parentElement) ctx.insertAdjacentElement('afterend', note);
    return;
  }
  const oldNote = ctx.parentElement.querySelector('.chart-load-note');
  if (oldNote) oldNote.remove();
  const metric = $('#impactMetric').value;
  const values = impactSamples[$('#impactPolicy').value][metric];
  if (impactChart) impactChart.destroy();
  impactChart = new Chart(ctx,{type:'bar',data:{labels:['시행 전 (예시)','시행 후 (예시)'],datasets:[{label:metricNames[metric][0],data:values,backgroundColor:['#a9bfdc','#27b57a'],borderRadius:8,maxBarThickness:90}]},options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,grid:{color:'#edf2f8'}},x:{grid:{display:false}}}}});
}
$('#impactPolicy').addEventListener('change', renderImpactTable);
$('#impactMetric').addEventListener('change', renderImpactTable);

$('#suggestionForm').addEventListener('submit', e => {
  e.preventDefault();
  const category = $('#suggestionCategory').value;
  const region = $('#suggestionRegion').value;
  const description = $('#suggestionDescription').value.trim();
  const file = $('#suggestionPhoto').files[0];
  const message = $('#formMessage');
  if (!category || !region || description.length < 10) {
    message.textContent = '문제 유형, 지역을 선택하고 제안 내용을 10자 이상 입력해 주세요.';
    message.classList.remove('hidden');
    message.style.background = '#fff0ef';
    message.style.color = '#b93838';
    return;
  }
  if (file && !['image/png','image/jpeg','image/webp'].includes(file.type)) {
    message.textContent = 'PNG, JPG, WEBP 이미지 파일만 선택할 수 있습니다.';
    message.classList.remove('hidden');
    return;
  }
  message.style.background = '#e9f8ef'; message.style.color = '#16764f';
  message.textContent = '입력 검증 완료. 이 프로토타입은 서버에 저장하거나 행정기관에 접수하지 않습니다.';
  message.classList.remove('hidden');
  const preview = $('#submissionPreview');
  preview.classList.remove('hidden');
  preview.innerHTML = `<h2>제안 내용 미리보기</h2><p><b>문제 유형:</b> ${escapeHtml(category)}</p><p><b>지역:</b> ${escapeHtml(region)}</p><p><b>장소:</b> ${escapeHtml($('#suggestionPlace').value || '미입력')}</p><p><b>제안:</b> ${escapeHtml(description)}</p><p class="footnote">시연용 미리보기입니다. 새로고침하면 사라집니다.</p>`;
});
function escapeHtml(s) { return s.replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }

setRegion('서울특별시');
renderClimateChart();
renderImpactTable();

// Evidence-based newsroom workflow; API keys remain on the server.
const nw = {facts:false,draft:false,compare:false,review:false,approved:false};
const ne = id => document.getElementById(id);
const nfields = ['newsTopic','newsRegion','newsAudience','newsFormat','newsFacts','newsSources','newsHeadline','newsArticle','editorNotes'];
function nmsg(id,text,kind='info'){const e=ne(id);if(e){e.textContent=text;e.className='inline-message '+kind;}}
function nprogress(){
 const topic=!!ne('newsTopic').value.trim(), vals=[topic,nw.facts,nw.draft,nw.compare,nw.review,nw.approved];
 [['stateTopic',vals[0]],['stateFacts',vals[1]],['stateDraft',vals[2]],['stateCompare',vals[3]],['stateReview',vals[4]],['stateApprove',vals[5]]].forEach(([id,ok])=>{ne(id).textContent=ok?'완료':'대기';ne(id).classList.toggle('done',ok);});
 $$('.workflow-step').forEach(s=>{const i=Number(s.dataset.stage)-1;s.classList.toggle('complete',!!vals[i]);s.classList.toggle('active',!vals[i]&&(i===0||vals.slice(0,i).every(Boolean)));});
 ne('newsStatus').textContent=nw.approved?'최종 승인':nw.review?'검수 완료':nw.draft?'초안 작성':nw.facts?'자료 확인':topic?'작성 중':'작성 중';
}
function ncollect(){return Object.fromEntries(nfields.map(id=>[id,ne(id)?.value||'']));}
function nsave(show=true){try{localStorage.setItem('localClimateNewsDraft',JSON.stringify({fields:ncollect(),state:nw,savedAt:new Date().toISOString()}));if(show)nmsg('approvalMessage','현재 브라우저에 임시 저장했습니다. 서버에는 저장되지 않습니다.','success');}catch(e){nmsg('approvalMessage','브라우저 임시 저장에 실패했습니다.','error');}}
function nrestore(){try{const s=JSON.parse(localStorage.getItem('localClimateNewsDraft')||'null');if(!s)return;nfields.forEach(id=>{if(typeof s.fields?.[id]==='string')ne(id).value=s.fields[id];});Object.assign(nw,s.state||{});}catch(e){console.warn('임시 초안을 읽지 못했습니다.',e);}}
ne('goFacts')?.addEventListener('click',()=>{if(!ne('newsTopic').value.trim()){nmsg('factMessage','기사 주제를 먼저 입력해 주세요.','error');ne('newsTopic').focus();return;}ne('newsFactsPanel').scrollIntoView({behavior:'smooth'});ne('newsFacts').focus();nprogress();});
ne('saveNewsDraft')?.addEventListener('click',()=>nsave());
ne('loadClimateFacts')?.addEventListener('click',async()=>{
 const b=ne('loadClimateFacts'); b.disabled=true; b.textContent='MySQL 자료 조회 중…';
 const regionNames={'서울특별시':'11','부산광역시':'26','대구광역시':'27','광주광역시':'29','대전광역시':'30','제주특별자치도':'50'};
 const year=Number(prompt('Fact Sheet 기준 연도를 입력하세요.',String(new Date().getFullYear()-1)));
 if(!Number.isInteger(year)||year<1900||year>2100){b.disabled=false;b.textContent='MySQL 기후자료로 Fact Sheet 만들기';return;}
 try{
  const url='http://127.0.0.1:8000/api/news/facts?region_code='+encodeURIComponent(regionNames[ne('newsRegion').value]||'11')+'&year='+year;
  const r=await fetch(url),data=await r.json(); if(!r.ok)throw new Error(data.detail||'자료 조회 실패');
  ne('newsFacts').value=data.facts; ne('newsSources').value=(data.sources||[]).join('\n');
  ['checkSource','checkDate','checkNumbers'].forEach(id=>ne(id).checked=false);
  nw.facts=false;nw.draft=false;nw.compare=false;nw.review=false;nw.approved=false;
  nmsg('factMessage',data.notice+' 확인란은 원문 확인 후 직접 체크하세요.','success');nprogress();
 }catch(e){nmsg('factMessage','Fact Sheet 생성 실패: '+e.message,'error');}
 finally{b.disabled=false;b.textContent='MySQL 기후자료로 Fact Sheet 만들기';}
});
ne('validateFacts')?.addEventListener('click',()=>{
 const facts=ne('newsFacts').value.trim(),urls=ne('newsSources').value.split(/\n+/).map(x=>x.trim()).filter(Boolean);
 const urlok=urls.length&&urls.every(x=>{try{return ['http:','https:'].includes(new URL(x).protocol);}catch(e){return false;}});
 if(!ne('newsTopic').value.trim())return nmsg('factMessage','기사 주제를 입력해 주세요.','error');
 if(facts.length<40)return nmsg('factMessage','핵심 사실·수치·기간을 40자 이상 입력해 주세요.','error');
 if(!urlok)return nmsg('factMessage','올바른 HTTP/HTTPS 원자료 URL을 한 개 이상 입력해 주세요.','error');
 if(!['checkSource','checkDate','checkNumbers'].every(id=>ne(id).checked))return nmsg('factMessage','출처·기준일/단위·수치 대조 확인란을 모두 체크해 주세요.','error');
 nw.facts=true;nw.draft=false;nw.compare=false;nw.review=false;nw.approved=false;
 nmsg('factMessage','입력 및 사용자 확인 체크를 통과했습니다. 자동 사실검증이 완료된 것은 아닙니다.','success');nprogress();
});
ne('generateNews')?.addEventListener('click',async()=>{
 if(!nw.facts)return nmsg('factMessage','먼저 Fact Sheet 확인을 완료해 주세요.','error');
 const b=ne('generateNews');b.disabled=true;b.textContent='기사 생성 중…';nmsg('factMessage','FastAPI 서버에 기사 초안을 요청합니다.');
 try{
  const r=await fetch('http://127.0.0.1:8000/api/news/draft',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({topic:ne('newsTopic').value.trim(),region:ne('newsRegion').value,audience:ne('newsAudience').value,format:ne('newsFormat').value,facts:ne('newsFacts').value.trim(),sources:ne('newsSources').value.split(/\n+/).map(x=>x.trim()).filter(Boolean)})});
  const data=await r.json();if(!r.ok)throw new Error(data.detail||data.error||'API 요청 실패');
  ne('newsHeadline').value=data.headline||ne('newsTopic').value.trim();ne('newsArticle').value=data.article||data.draft||'';
  if(!ne('newsArticle').value)throw new Error('응답에 기사 본문이 없습니다.');
  nw.draft=true;nw.compare=false;nw.review=false;nw.approved=false;nmsg('factMessage','AI 초안이 생성되었습니다. 원자료와 직접 대조해 주세요.','success');ne('newsArticle').scrollIntoView({behavior:'smooth'});nsave(false);nprogress();
 }catch(e){nmsg('factMessage','기사 생성 실패: '+e.message+'. FastAPI 실행과 OPENAI_API_KEY 설정을 확인하세요.','error');}
 finally{b.disabled=false;b.textContent='OpenAI로 기사 초안 생성';}
});
ne('compareNews')?.addEventListener('click',()=>{if(!ne('newsArticle').value.trim())return nmsg('reviewMessage','먼저 기사 초안을 작성해 주세요.','error');ne('comparisonChecks').classList.remove('hidden');ne('comparisonChecks').scrollIntoView({behavior:'smooth'});});
$$('.comparison-check').forEach(c=>c.addEventListener('change',()=>{nw.compare=$$('.comparison-check').every(x=>x.checked);if(!nw.compare){nw.review=false;nw.approved=false;}else nmsg('reviewMessage','체크리스트 완료 표시입니다. 편집자가 실제 원문 대조를 수행해야 합니다.','success');nprogress();}));
ne('markReviewed')?.addEventListener('click',()=>{if(!ne('newsHeadline').value.trim()||!ne('newsArticle').value.trim())return nmsg('reviewMessage','제목과 본문을 먼저 작성해 주세요.','error');if(!nw.compare){ne('comparisonChecks').classList.remove('hidden');return nmsg('reviewMessage','원자료 대조 체크리스트를 모두 완료해 주세요.','error');}nw.review=true;nw.approved=false;nmsg('reviewMessage','사람 검수 완료로 표시했습니다. 최종 승인 전까지 게시 확정본이 아닙니다.','success');nprogress();nsave(false);});
ne('approveNews')?.addEventListener('click',()=>{if(!nw.review)return nmsg('approvalMessage','원자료 대조와 사람 검수를 먼저 완료해 주세요.','error');if(!ne('editorApproval').checked)return nmsg('approvalMessage','최종 승인 확인란을 체크해 주세요.','error');nw.approved=true;nprogress();nmsg('approvalMessage','최종 승인 상태입니다. 실제 게시 및 서버 이력 저장은 실행하지 않습니다.','success');nsave(false);});
ne('exportNews')?.addEventListener('click',()=>{const blob=new Blob([JSON.stringify({exportedAt:new Date().toISOString(),fields:ncollect(),workflow:nw,notice:'브라우저에서 내보낸 검수 기록이며 서버 게시 이력이 아닙니다.'},null,2)],{type:'application/json;charset=utf-8'});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='local-climate-news-review.json';a.click();URL.revokeObjectURL(url);});
ne('resetNews')?.addEventListener('click',()=>{if(!confirm('현재 기사 작업을 초기화할까요?'))return;nfields.forEach(id=>{if(ne(id))ne(id).value='';});['checkSource','checkDate','checkNumbers','editorApproval'].forEach(id=>ne(id).checked=false);$$('.comparison-check').forEach(c=>c.checked=false);ne('comparisonChecks').classList.add('hidden');Object.keys(nw).forEach(k=>nw[k]=false);localStorage.removeItem('localClimateNewsDraft');['factMessage','reviewMessage','approvalMessage'].forEach(id=>nmsg(id,''));nprogress();});
nfields.forEach(id=>ne(id)?.addEventListener('input',()=>{if(['newsFacts','newsSources','newsTopic'].includes(id)){nw.facts=false;nw.draft=false;nw.compare=false;nw.review=false;nw.approved=false;}if(['newsHeadline','newsArticle'].includes(id)){nw.review=false;nw.approved=false;}nprogress();}));
nrestore();nprogress();


// Account registration and login (FastAPI + MySQL)
const AUTH_API = 'http://127.0.0.1:8000/api/auth';
const AUTH_TOKEN_KEY = 'localClimateSessionToken';
const authOverlay = $('#authOverlay');
let authMode = 'login';
let authToken = sessionStorage.getItem(AUTH_TOKEN_KEY) || '';
let authUser = null;

function authMessage(message, kind='') {
  const el = $('#authMessage');
  if (!el) return;
  el.textContent = message;
  el.className = 'auth-message' + (kind ? ' ' + kind : '');
}
function setAuthMode(mode) {
  authMode = mode;
  const signup = mode === 'signup';
  $('#authTitle').textContent = signup ? '회원가입' : '로그인';
  $('#authDescription').textContent = signup ? '이메일과 닉네임을 등록해 계정을 만드세요.' : '계정에 로그인하고 서비스를 이용하세요.';
  $('#displayNameField').classList.toggle('hidden', !signup);
  $('#passwordHint').classList.toggle('hidden', !signup);
  $('#authDisplayName').required = signup;
  $('#authPassword').autocomplete = signup ? 'new-password' : 'current-password';
  $('#authSubmit').textContent = signup ? '회원가입' : '로그인';
  $('#authSwitchText').innerHTML = signup ? '이미 계정이 있으신가요? <button type="button" id="switchLogin">로그인</button>' : '계정이 없으신가요? <button type="button" id="switchSignup">회원가입</button>';
  authMessage('');
  const switchButton = signup ? $('#switchLogin') : $('#switchSignup');
  switchButton?.addEventListener('click', () => setAuthMode(signup ? 'login' : 'signup'));
}
function openAuth(mode='login') {
  setAuthMode(mode);
  authOverlay.classList.remove('hidden');
  setTimeout(() => (mode === 'signup' ? $('#authDisplayName') : $('#authEmail')).focus(), 0);
}
function closeAuth() {
  authOverlay.classList.add('hidden');
  $('#authForm').reset();
  authMessage('');
}
function renderAuthState() {
  const loggedIn = Boolean(authUser);
  $('#openLogin').classList.toggle('hidden', loggedIn);
  $('#openSignup').classList.toggle('hidden', loggedIn);
  $('#logoutButton').classList.toggle('hidden', !loggedIn);
  $('#authUser').classList.toggle('hidden', !loggedIn);
  $('#authUser').textContent = loggedIn ? authUser.display_name + ' 님' : '';
  $('#authUser').title = loggedIn ? authUser.email : '';
}
async function authRequest(path, body) {
  let response;
  try {
    response = await fetch(AUTH_API + path, {
      method: body ? 'POST' : 'GET',
      headers: {'Content-Type':'application/json', ...(authToken ? {'Authorization':'Bearer '+authToken} : {})},
      ...(body ? {body:JSON.stringify(body)} : {})
    });
  } catch {
    throw new Error('API 서버에 연결할 수 없습니다. FastAPI가 실행 중인지 확인하세요.');
  }
  let data = {};
  try { data = await response.json(); } catch {}
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '요청을 처리하지 못했습니다.');
  return data;
}
function applyAuth(data) {
  authToken = data.access_token;
  authUser = data.user;
  sessionStorage.setItem(AUTH_TOKEN_KEY, authToken);
  renderAuthState();
}
$('#openLogin').addEventListener('click', () => openAuth('login'));
$('#openSignup').addEventListener('click', () => openAuth('signup'));
$('#closeAuth').addEventListener('click', closeAuth);
authOverlay.addEventListener('click', e => { if (e.target === authOverlay) closeAuth(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape' && !authOverlay.classList.contains('hidden')) closeAuth(); });
$('#authForm').addEventListener('submit', async e => {
  e.preventDefault();
  const button = $('#authSubmit');
  button.disabled = true;
  authMessage(authMode === 'signup' ? '계정을 생성하고 있습니다…' : '로그인 중…');
  const payload = {email:$('#authEmail').value.trim(), password:$('#authPassword').value};
  if (authMode === 'signup') payload.display_name = $('#authDisplayName').value.trim();
  try {
    const data = await authRequest(authMode === 'signup' ? '/register' : '/login', payload);
    applyAuth(data);
    authMessage(authMode === 'signup' ? '회원가입이 완료되었습니다.' : '로그인되었습니다.', 'success');
    setTimeout(closeAuth, 450);
  } catch (error) {
    authMessage(error.message, 'error');
  } finally {
    button.disabled = false;
  }
});
$('#logoutButton').addEventListener('click', async () => {
  try { if (authToken) await authRequest('/logout', {}); } catch {}
  sessionStorage.removeItem(AUTH_TOKEN_KEY);
  authToken = '';
  authUser = null;
  renderAuthState();
});
async function restoreAuthSession() {
  if (!authToken) { renderAuthState(); return; }
  try {
    const data = await authRequest('/me');
    authUser = data.user;
  } catch {
    sessionStorage.removeItem(AUTH_TOKEN_KEY);
    authToken = '';
    authUser = null;
  }
  renderAuthState();
}
renderAuthState();
restoreAuthSession();
