const $ = (sel, root=document) => root.querySelector(sel);
const $$ = (sel, root=document) => [...root.querySelectorAll(sel)];

const demoClimate = {
  temp: {label:'평균기온 (°C)', title:'연도별 평균기온 추이', data:[12.1,12.4,12.0,12.8,13.0,12.7,13.2,13.5,13.7,14.0]},
  rain: {label:'강수량 (mm)', title:'연도별 강수량 추이', data:[1320,1450,1180,1510,1390,1280,1610,1430,1550,1490]},
  heat: {label:'폭염일수 (일)', title:'연도별 폭염일수 추이', data:[8,10,7,12,11,9,14,16,13,18]},
  tropical: {label:'열대야일수 (일)', title:'연도별 열대야일수 추이', data:[6,7,8,9,7,10,12,11,14,15]}
};
const years = ['2016','2017','2018','2019','2020','2021','2022','2023','2024','2025'];
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

const regionTemps = {'서울특별시':'18.5°C','부산광역시':'20.1°C','대구광역시':'19.8°C','광주광역시':'19.2°C','대전광역시':'18.9°C','제주특별자치도':'21.0°C'};
function setRegion(region) {
  $('#regionSelect').value = region;
  $('#climateRegion').value = region;
  $('#homeRegionLabel').textContent = `${region} · 예시`;
  $('#temperature').textContent = regionTemps[region] || '자료 연동 전';
  $$('.chip').forEach(b => b.classList.toggle('selected', b.dataset.region === region));
}
$('#regionSelect').addEventListener('change', e => setRegion(e.target.value));
$$('.chip').forEach(b => b.addEventListener('click', () => setRegion(b.dataset.region)));

function renderClimateChart() {
  const ctx = $('#climateChart');
  if (!ctx || !window.Chart) return;
  const key = $('#metricSelect').value;
  const metric = demoClimate[key];
  const period = Number($('#periodSelect').value);
  const labels = years.slice(-period);
  const values = metric.data.slice(-period);
  $('#chartTitle').textContent = metric.title;
  $('#chartLegend').textContent = `${metric.label} · 예시`;
  if (climateChart) climateChart.destroy();
  climateChart = new Chart(ctx, {
    type:'line',
    data:{labels,datasets:[{label:metric.label,data:values,borderColor:'#2176ee',backgroundColor:'rgba(33,118,238,.12)',fill:true,tension:.32,pointRadius:3,pointBackgroundColor:'#2176ee'}]},
    options:{responsive:true,interaction:{intersect:false,mode:'index'},plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>`${c.dataset.label}: ${c.parsed.y.toLocaleString()}`}}},scales:{y:{beginAtZero:key!=='temp',grid:{color:'#edf2f8'}},x:{grid:{display:false}}}}
  });
}
$('#metricSelect').addEventListener('change', renderClimateChart);
$('#periodSelect').addEventListener('change', renderClimateChart);
$('#climateRegion').addEventListener('change', e => { setRegion(e.target.value); });

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
    points.forEach(p => L.circleMarker([p[0],p[1]],{radius:8,color:p[4],fillColor:p[4],fillOpacity:.8,weight:2}).addTo(map)
      .bindPopup(`<b>${p[2]}</b><br><small>시연용 마커 · 실제 위험 위치 아님</small><br><button onclick="window.openIssue(${p[3]})">상세 보기</button>`));
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
$$('.filter-chip').forEach(btn => btn.addEventListener('click', () => {
  $$('.filter-chip').forEach(b => b.classList.toggle('active', b === btn));
  const filter = btn.dataset.filter;
  $$('.issue-detail-card').forEach(card => {
    const id = card.dataset.issue;
    const category = ({1:'heat',2:'flood',3:'green',4:'people'})[id];
    card.classList.toggle('hidden', filter !== 'all' && category !== filter);
  });
}));

function filterPolicies() {
  const q = $('#policySearch').value.trim().toLowerCase();
  const cat = $('#policyCategory').value;
  let count = 0;
  $$('.policy-card').forEach(card => {
    const visible = (cat === 'all' || card.dataset.category === cat) && (card.dataset.search + ' ' + card.innerText).toLowerCase().includes(q);
    card.classList.toggle('hidden', !visible);
    if (visible) count++;
  });
  $('#policyEmpty').classList.toggle('hidden', count > 0);
}
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
  if (!ctx || !window.Chart) return;
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
