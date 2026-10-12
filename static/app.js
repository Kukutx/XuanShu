'use strict';
// Vanilla JS, no third-party client dependencies or remote analytics.
const $ = sel => document.querySelector(sel);
const result = $('#result');
const form = $('#birth-form');
const tabs = [...document.querySelectorAll('.tab')];
const commonTabs = new Set(['chat','today','date-scan','consult','bazi','qimen','ziwei','transform','dayun','calendar','pair','group','decision','rule-matrix','report']);
// Search alternative terminology without transmitting the user's query.
const toolKeywords = {
  chat:'对话 聊天 ai chat 问答 记忆 人生事件 life path 回溯 多语言 english',
  consult:'咨询 agent 事业 工作 感情 婚姻 关系 问答 career advice',
  bazi:'八字 四柱 生辰 干支 命盘',
  qimen:'奇门 遁甲 九宫 择时 事件',
  ziwei:'紫微 星曜 宫位 命盘',
  professional:'紫微 专业 iztro 大限 流年 流月 流日 流时',
  'qimen-audit':'奇门 核验 参考盘',
  transform:'四化 飞化 年干',
  annual:'流年 年运 年度',
  time:'太阳时 经度 时差',
  dayun:'八字 大运 起运',
  boundaries:'出生时间 时辰 边界',
  officers:'择日 建除 十二值日',
  'date-scan':'择日 择时 吉日 候选 搬家 开业 奇门 建除',
  timeline:'年份 运势 轨迹',
  decision:'方案 对比 权重 决策',
  calendar:'农历 日历 节气 日期',
  pair:'合盘 双人 伴侣 关系',
  group:'多人 家人 家庭 团队 朋友 关系 三合 生肖 family team group',
  quality:'质量 核查 误差',
  'rule-matrix':'规则 流派 差异 换日 子时 闰月 太阳时 夏令时 对照 敏感 rules school',
  reading:'传统 符号 分析',
  deep:'证据 来源 文献 规则',
  report:'报告 综述 markdown',
  integration:'mcp claude chatgpt codex plugin 接入 配置',
  json:'json 数据 导出 开发',
};
let expandedTools = false;
function updateToolNavigation() {
  const term = $('#tool-search').value.trim().toLocaleLowerCase();
  let visible = 0;
  let matched = 0;
  tabs.forEach(tab => {
    const allowed = expandedTools || !!term || commonTabs.has(tab.dataset.tab);
    const content = (tab.textContent + ' ' + (toolKeywords[tab.dataset.tab] || '')).toLocaleLowerCase();
    const matches = !term || content.includes(term);
    if (term && matches) matched++;
    // Preserve the active view until the user intentionally selects another.
    tab.hidden = !(tab.dataset.tab === active || (allowed && matches));
    if (!tab.hidden) visible++;
  });
  // A group heading is shown only while at least one of its tools is.
  document.querySelectorAll('.tab-group').forEach(label => {
    let node = label.nextElementSibling, shown = false;
    while (node && !node.classList.contains('tab-group')) {if (node.classList.contains('tab') && !node.hidden) shown = true; node = node.nextElementSibling;}
    label.hidden = !shown;
  });
  // Counts sit between their own text nodes so 当前 / 项 translate as whole entries.
  $('#tool-visible-count').replaceChildren(...(term
    ? (matched ? ['找到 ', String(matched), ' 项（当前页面保留）'] : ['没有匹配项，请尝试八字、择时、MCP 等关键词'])
    : ['当前 ', visible + '/' + tabs.length, ' 项']));
  $('#tool-toggle-all').textContent = expandedTools ? '收起高级功能' : `展开全部 ${tabs.length} 项`;
  $('#tool-toggle-all').setAttribute('aria-expanded', String(expandedTools));
}
$('#tool-toggle-all').addEventListener('click', () => {expandedTools = !expandedTools; updateToolNavigation();});
$('#tool-search').addEventListener('input', updateToolNavigation);
$('#tool-search').addEventListener('keydown',event=>{
  if(event.key==='Escape'){event.currentTarget.value='';updateToolNavigation();}
});
const profileKey = 'xuanshu-profiles-v2';
// Read existing pre-rename local profiles once; keep the original as a safe fallback.
const legacyProfileKey = 'oriental-astro-profiles-v2';
try {
  if (localStorage.getItem(profileKey) === null) {
    const previous = localStorage.getItem(legacyProfileKey);
    if (previous !== null) {
      const profiles = JSON.parse(previous);
      if (Array.isArray(profiles) && profiles.length <= 20) {
        localStorage.setItem(profileKey, JSON.stringify(profiles));
      }
    }
  }
} catch (_) { /* Storage may be unavailable; leave previous data untouched. */ }
let active = 'chat';
let current = null;
let consultResult = null;
let consultCursor = null;
let consultAdvancedOpen = false;
let consultDraft = {question:'',intent:'auto', useBirth:false, usePartner:false, partnerDate:'', lunarYear:'', candidateDates:'', facts:'', includeReport:false};
let qimenResult = null;
let qimenFingerprint = null;
let currentHourUnknown = false;  // the chart was generated with "不知道出生时辰" ticked
let hourCandidates = null;       // {key, rows}: the same birth day cast at each of the twelve double hours
// Qimen is cast for the moment of a question or event, which is usually now, not the birth time.
let qimenMoment = {mode: 'now', custom: ''};
let professionalResult = null;
let referenceAuditResult = null;
const localToday = () => {
  const now = new Date();
  return [now.getFullYear(), String(now.getMonth()+1).padStart(2,'0'), String(now.getDate()).padStart(2,'0')].join('-');
};
let professionalTargetDraft = localToday();
let currentInput = null;
let selectedPalace = '命宫';
// Time layer drawn on the Zi Wei board: natal only, one ten-year major limit, or one lunar year.
let ziweiLayer = {mode: 'natal', decade: null, year: null, date: null};
// Month and day layers come from the engine (斗君 needs the lunar calendar), one date at a time.
// While a new date loads, the previous result keeps the step buttons usable (and focused).
let horoscopeResult = null, horoscopeKey = null, horoscopeError = '', horoscopeResultKey = null;
let calendarResult = null;
let pairResult = null;
let pairZiweiResult = null;
let pairKey = null;  // the request the pair result belongs to
let pairChatBlock = null;  // the text of the last pair draft put into the chat input, so a newer one replaces it
let annualResult = null;
let timeResult = null;
let reportResult = null;
let deepResult = null;
let deepDraft = {focus_palace: '命宫', lunar_year: '', question: ''};
let windowResult = null;
let lunarInverseResult = null;
let qualityResult = null;
let officerResult = null;
let timelineResult = null;
let decisionResult = null;
let dayunResult = null;
let boundaryResult = null;
let dayunDraft = {periods: 10, direction_override: ''};
let boundaryDraft = {uncertainty_minutes: 60};
let qualityMinutesDraft = 15;
let reportDraft = {lunar_year: null, include_time_audit: false, include_deep_evidence:true,
  include_dayun:false, dayun_direction_override:'', birth_boundary_minutes:''};
let windowDraft = {radius: 30, spacing: 10};
let lunarInverseDraft = {lunar_year:2024,lunar_month:1,lunar_day:1,is_leap_month:false};
let annualDraft = 2026;
let calendarDraft = {start_date: localToday(), days: 14};
let officerDraft = {start_date:localToday(),days:30,officer:''};
let timelineDraft = {start_lunar_year:2024,years:10,focus_palace:''};
let decisionDraft = {question:'比较两种实现方案',criteria:[{name:'交付速度',weight:2},{name:'维护成本',weight:3}], options:[{name:'方案 A',ratings:[4,2]},{name:'方案 B',ratings:[3,5]}]};
let pairDraft = {birth_datetime: '2001-01-01T12:00', timezone: 'Asia/Shanghai', gender: 'unspecified', year: new Date().getFullYear()};
// The year of the pair's luck and year-pillar view; a newer request makes older replies stale, as on the group page.
// While 比较两人命盘 runs, a year switch only changes the year asked for: the run's reply then fetches that year.
let pairYearTicket = 0, pairYearPending = false, pairYearError = '', pairRunning = false, pairRunError = '';
// A year typed in a year field but not yet entered, by page, so it survives a re-render.
let luckYearTyped = {};
// The button under a pointer that is still down; cleared after its click has run.
let pressedButton = null;
document.addEventListener('pointerdown', e => {pressedButton = e.target instanceof Element ? e.target.closest('button') : null;}, true);
document.addEventListener('pointerup', () => {setTimeout(() => {pressedButton = null;});}, true);
document.addEventListener('pointercancel', () => {pressedButton = null;}, true);
// A typed year that is a valid year, taken (and cleared) by a run that starts before it was entered.
function takeTypedYear(prefix) {
  const typed = luckYearTyped[prefix], value = Number(typed);
  luckYearTyped[prefix] = null;
  return typed != null && typed !== '' && Number.isInteger(value) && value >= 1901 && value <= 2099 ? value : null;
}
const nameMap = {year: '年柱', month: '月柱', day: '日柱', hour: '时柱'};
function elt(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}
function append(parent, tag, cls, text) {
  const node = elt(tag, cls, text);
  parent.append(node);
  return node;
}
function clear() {result.replaceChildren();}
function title(parent, heading, detail = '') {
  const box = append(parent, 'div', 'result-intro');
  append(box, 'h3', null, heading);
  append(box, 'span', null, detail);
}
function note(parent, text) {append(parent, 'p', 'disclaimer', text);}
function meta(parent, items) {
  const el = append(parent, 'div', 'meta-tags');
  items.forEach(item => append(el, 'span', null, item));
}
function rules(parent, items) {
  const container = append(parent, 'div', 'rule-bar');
  items.forEach(x => {
    const box = append(container, 'div', 'rule-box');
    append(box, 'small', null, x.label);
    append(box, 'strong', null, x.value);
    if (x.detail) append(box, 'em', null, x.detail);
  });
}
function readInput() {
  return {
    birth_datetime: $('#birth_datetime').value,
    timezone: $('#timezone').value,
    gender: $('#gender').value,
    late_zi_day_rollover: $('#late_zi_day_rollover').checked,
    leap_month_second_half_as_next: $('#leap_month_second_half_as_next').checked,
    time_mode: $('#time_mode').value,
    longitude: $('#longitude').value.trim() === '' ? null : Number($('#longitude').value),
  };
}
function setInput(data) {
  for (const name of ['birth_datetime', 'timezone', 'gender']) {
    const control = $('#' + name);
    if (typeof data[name] === 'string') {
      control.value = data[name];
    }
  }
  $('#late_zi_day_rollover').checked = !!data.late_zi_day_rollover;
  $('#leap_month_second_half_as_next').checked = data.leap_month_second_half_as_next !== false;
  $('#time_mode').value = data.time_mode || 'clock';
  $('#longitude').value = data.longitude ?? '';
  updateGeoControls();
  updateDemoBirthWarning();
  updateStaleBirthNotice();
}
async function postJSON(path, body, signal) {
  const token = $('#api_token').value;
  const response = await fetch(path, {
    method: 'POST',
    headers: {'Content-Type': 'application/json', ...(token ? {'Authorization': 'Bearer ' + token} : {})},
    body: JSON.stringify(body), signal,
  });
  let data;
  try {data=await response.json();}
  catch (_) {throw new Error(`服务返回了无法解析的响应（HTTP ${response.status}），请检查服务地址或代理配置`);}
  if (!response.ok) {
    const message=data?.detail;
    const detail=typeof message==='string' ? message : (Array.isArray(message) ? message.map(x=>x.msg).join('; ') : JSON.stringify(message || data));
    if(response.status===401)throw new Error('请检查 API 访问令牌（401）：'+detail);
    if(response.status===403)throw new Error('访问被拒绝（403），请检查服务来源与权限：'+detail);
    throw new Error(`HTTP ${response.status}：${detail}`);
  }
  return data;
}
const browserZone = () => {try {return Intl.DateTimeFormat().resolvedOptions().timeZone || '';} catch (_) {return '';}};
function localMinute(date = new Date()) {
  const pad = n => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
// "Now" and a chosen time use this device's clock and time zone; "birth" reuses every birth-panel rule.
function qimenMomentInput() {
  const base = readInput();
  if (qimenMoment.mode === 'birth') return base;
  const when = qimenMoment.mode === 'custom' && qimenMoment.custom ? qimenMoment.custom : localMinute();
  return {...base, birth_datetime: when, timezone: browserZone() || base.timezone, time_mode: 'clock', longitude: null};
}
function renderQimen() {
  if (qimenResult && qimenFingerprint && qimenFingerprint !== JSON.stringify(readInput())) qimenResult = null;
  title(result, '奇门遁甲 · 时家拆补转盘', '九宫 · 三元局数 · 地盘 / 天盘 / 暗干 / 门 / 星 / 神');
  append(result, 'p', 'info-inline', '奇门按事情发生或提问的时刻起局，默认取此刻。不是出生预测；本模块仅实现一套明确的时家拆补转盘配置。');
  const row = append(result, 'div', 'inline-control');
  const modeLabel = append(row, 'label', null, '起局时刻');
  const mode = append(modeLabel, 'select'); mode.id = 'qimen-moment';
  [['now', '此刻'], ['custom', '指定时间'], ['birth', '出生时间']].forEach(([value, text]) => {const op = append(mode, 'option', null, text); op.value = value;});
  mode.value = qimenMoment.mode;
  mode.addEventListener('change', () => {qimenMoment.mode = mode.value; qimenResult = null; qimenFingerprint = null; render();});
  if (qimenMoment.mode === 'custom') {
    const whenLabel = append(row, 'label', null, '日期与时间');
    const when = append(whenLabel, 'input'); when.type = 'datetime-local'; when.id = 'qimen-when';
    when.value = qimenMoment.custom || localMinute();
    when.addEventListener('change', () => {qimenMoment.custom = when.value; if (qimenResult) {qimenResult = null; render();}});
  }
  const run = append(row, 'button', null, '排布九宫'); run.id='qimen-run'; run.type='button';
  append(result, 'small', 'field-help', qimenMoment.mode === 'birth' ? '沿用出生资料里的时区、真太阳时和换日规则。' : '按本机时区 ' + (browserZone() || readInput().timezone) + ' 的钟表时间起局。');
  if (qimenMoment.mode === 'birth' && $('#hour_unknown').checked) append(result, 'p', 'inline-msg', '出生时辰不详：12:00 只是占位，用它起出的奇门盘没有意义。');
  const message = append(result, 'p', 'inline-msg');
  run.addEventListener('click', async () => {
    run.disabled=true; message.className = 'inline-msg progress'; message.textContent='正在起局…';
    try { const input = qimenMomentInput();
      const chart = await postJSON('/api/qimen', {moment:input});
      qimenResult=chart; qimenFingerprint = qimenMoment.mode === 'birth' ? JSON.stringify(input) : null; render(); }
    catch(e) { message.className = 'inline-msg'; message.textContent='奇门排盘失败：'+e.message; }
    finally { run.disabled=false; }
  });
  if (!qimenResult) return;
  const q=qimenResult;
  meta(result,[(q.instant || '').replace('T', ' ').slice(0, 16), q.solar_term, q.dun + q.bureau + '局', q.yuan, '日 ' + q.day_pillar, '时 ' + q.hour_pillar].filter(Boolean));
  rules(result,[
    {label:'旬首 / 六仪', value:q.xun_head + ' · ' + q.xun_instrument},
    {label:'值符星及宫位', value:q.zhi_fu_star, detail:'宫 ' + q.zhi_fu_palace},
    {label:'值使门及宫位', value:q.zhi_shi_door, detail:'宫 ' + q.zhi_shi_palace},
    {label:'空亡地支', value:q.void_branches.join('、')},
  ]);
  const board=append(result,'div','qimen-board');
  const order=[4,9,2,3,5,7,8,1,6];
  order.forEach(n=>{
    const p=q.palaces.find(x=>x.number===n);
    const zhifu=p.number===q.zhi_fu_palace, zhishi=p.number===q.zhi_shi_palace;
    const cell=append(board,'div','qimen-cell' + (n===5?' center':'') + (p.void?' empty':'') + (zhifu?' zhifu':'') + (zhishi?' zhishi':''));
    append(cell,'strong',null,`${n} · ${p.trigram}宫 · ${p.direction}`);
    // Traditional reading order: deity over star over door, heaven stem over earth stem.
    const grid=append(cell,'div','qimen-grid');
    const pair=(label,name,stemLabel,stem)=>{
      const left=append(grid,'div','q-name'); append(left,'span','q-label',label); left.append(name || '—');
      const right=append(grid,'div','q-stem'); if(stemLabel){append(right,'span','q-label',stemLabel); right.append(stem);}
    };
    pair('八神',p.deity,'天干',p.heaven_stem);
    pair('九星',p.star,'暗干',p.dark_stem);
    pair('八门',p.door,'地干',p.earth_stem);
    const tags=append(cell,'div','qimen-tags');
    if(zhifu) append(tags,'span','qimen-tag','值符');
    if(zhishi) append(tags,'span','qimen-tag','值使');
    if(p.void) append(tags,'small','qimen-tag void','旬空');
    if(p.center_lodged_here) append(tags,'small','qimen-tag','中宫寄宫');
  });
  q.limitations.forEach(x=>note(result,x));
}
function renderProfessionalZiwei() {
  title(result, '专业紫微 · iztro-py（可选）', '本命全盘与运限 · 第三方独立引擎，不替换原生子集');
  note(result, '仅本机显式安装 xuanshu[professional] 后可使用。第三方引擎的流派、星曜与当前子集可能不同，不会隐式混合数据。');
  const row=append(result,'div','inline-control');
  const label=append(row,'label',null,'目标日期（流年 / 流月 / 流日）');
  const date=append(label,'input'); date.type='date'; date.id='professional-target';date.value=professionalTargetDraft;
  const run=append(row,'button',null,'计算专业盘');run.id='professional-run';run.type='button';
  const message=append(result,'p','inline-msg');
  run.addEventListener('click', async()=>{
    run.disabled=true;
    try {
      professionalTargetDraft=date.value;
      professionalResult=await postJSON('/api/ziwei-professional', {birth:readInput(),target_date:professionalTargetDraft || null});
      render();
    } catch(e){message.textContent='专业引擎暂不可用：'+e.message;}
    finally{run.disabled=false;}
  });
  if(!professionalResult)return;
  meta(result,[professionalResult.provider,professionalResult.effective_calendar_date, '时辰序号 '+professionalResult.time_index]);
  append(result,'pre','json-code',JSON.stringify(professionalResult,null,2));
  professionalResult.notes.forEach(x=>note(result,x));
}
function renderQimenAudit() {
  title(result,'奇门外部参考盘逐宫核验','只比较用户提供的字段，不把缺失字段计入通过');
  note(result,'把独立排盘结果整理为 JSON，包含 reference_source、reference_school、root_fields 和 palaces。每个宫使用 number=1…9；其余只填写需要对照的字段。');
  const field=append(result,'textarea','json-code');field.id='qimen-audit-input';field.rows=8;
  field.placeholder=JSON.stringify({reference_source:'公开参考盘链接',reference_school:'时家拆补转盘',root_fields:{bureau:3},palaces:[{number:1,star:'天蓬'}]},null,2);
  const run=append(result,'button','tiny-button','核验参考盘');run.id='qimen-audit-run';run.type='button';
  const message=append(result,'p','inline-msg');
  run.addEventListener('click',async()=>{
    run.disabled=true;
    try {
      const ref=JSON.parse(field.value);
      referenceAuditResult=await postJSON('/api/qimen-reference-audit',{moment:readInput(),...ref});
      render();
    } catch(e){message.textContent='核验失败：'+e.message;}
    finally{run.disabled=false;}
  });
  if(!referenceAuditResult)return;
  const a=referenceAuditResult;
  meta(result,[`${a.matching}/${a.compared} 字段一致`, a.matches?'全部提供字段一致':'存在差异',a.reference_school]);
  if(a.mismatches.length)append(result,'pre','json-code',JSON.stringify(a.mismatches,null,2));
  a.notes.forEach(x=>note(result,x));
}
// Five phases → CSS class; the colours live in style.css for both themes.
const ELEMENT_CLASS = {'木':'wood','火':'fire','土':'earth','金':'metal','水':'water'};
const elementClass = name => ELEMENT_CLASS[name] ? 'el-' + ELEMENT_CLASS[name] : '';
function elementBars(parent, primary, secondary) {
  const total = Object.values(primary).reduce((a, b) => a + b, 0) || 1;
  const totalSecondary = secondary ? (Object.values(secondary).reduce((a, b) => a + b, 0) || 1) : 1;
  const bars = append(parent, 'div', 'element-bars');
  ['木','火','土','金','水'].forEach(name => {
    const row = append(bars, 'div', 'element-bar');
    append(row, 'b', elementClass(name), name);
    const track = append(row, 'div', 'element-track');
    track.setAttribute('role', 'img');
    track.setAttribute('aria-label', name + ' ' + (primary[name] || 0) + (secondary ? '；藏干 ' + (secondary[name] || 0) : ''));
    if (secondary) append(track, 'span', 'element-fill secondary bg-' + ELEMENT_CLASS[name]).style.width = Math.round((secondary[name] || 0) / totalSecondary * 100) + '%';
    append(track, 'span', 'element-fill bg-' + ELEMENT_CLASS[name]).style.width = Math.round((primary[name] || 0) / total * 100) + '%';
    append(row, 'small', null, (primary[name] || 0) + ' 个' + (secondary ? ' · 藏 ' + (secondary[name] || 0) : ''));
  });
  if (secondary) {
    const legend = append(parent, 'div', 'element-legend');
    const a = append(legend, 'span'); append(a, 'i'); a.append('明干 + 地支本气');
    const b2 = append(legend, 'span'); append(b2, 'i', 'secondary'); b2.append('藏干（不加权）');
  }
}
// Decade (大运) and annual (流年) pillars on one strip. A year opens the Zi Wei year layer for the same year.
const STEM_ELEMENTS = '木木火火土土金金水水', BRANCH_ELEMENTS = '水土木木土火火土金金土水', PHASES = '木火土金水';
const TEN_GODS = [['比肩', '劫财'], ['食神', '伤官'], ['偏财', '正财'], ['七杀', '正官'], ['偏印', '正印']];
function tenGodOf(dayStem, stem) {
  const d = STEM_ORDER.indexOf(dayStem), o = STEM_ORDER.indexOf(stem);
  const delta = (PHASES.indexOf(STEM_ELEMENTS[o]) - PHASES.indexOf(STEM_ELEMENTS[d]) + 5) % 5;
  return TEN_GODS[delta][d % 2 === o % 2 ? 0 : 1];
}
const yearPillarOf = year => {const i = ((year - 1984) % 60 + 60) % 60; return STEM_ORDER[i % 10] + BRANCH_ORDER[i % 12];};
const stemClass = stem => elementClass(STEM_ELEMENTS[STEM_ORDER.indexOf(stem)]);
const branchClass = branch => elementClass(BRANCH_ELEMENTS[BRANCH_ORDER.indexOf(branch)]);
let luckData = null, luckKey = null, luckPending = false, luckDecade = null;
const luckKeyNow = () => JSON.stringify([currentInput, currentHourUnknown]);
function ensureLuck() {
  const key = luckKeyNow();
  if (luckKey === key || luckPending) return;
  luckPending = true;
  // Without the hour, relations with the (placeholder) hour pillar are left out.
  postJSON('/api/dayun', {birth: currentInput, periods: 9, include_years: true, hour_unknown: currentHourUnknown})
    .then(data => {luckData = data;}).catch(() => {luckData = null;})
    .finally(() => {
      luckPending = false; luckKey = key; luckDecade = null; if (active === 'bazi') render();
      const dialog = $('#share-dialog'); if (dialog && dialog.open && shareRefresh) shareRefresh();  // the text chart lists the decades
    });
}
// A luck or year pillar against the natal chart. In the cells, short marks in chart notation (冲月: clashes the
// month branch; 合 刑 害 likewise, 同 for the same branch; 日空 年空 for the voids); the full text in the caption and title.
const natalMarkList = n => n.branch_relations.flatMap(r => r.labels.map(l => [(l === '同支' ? l.charAt(0) : l.slice(-1)) + nameMap[r.pillar].charAt(0), LINK_CLASS[l] || 'same']))
  .concat(n.void_of.map(v => [v === 'day' ? '日空' : '年空', 'void']));
function natalMarks(parent, n) {
  const marks = natalMarkList(n);
  if (!marks.length) return;
  const line = append(parent, 'span', 'luck-marks'); line.setAttribute('data-no-i18n', '');
  marks.forEach(([text, kind]) => append(line, 'span', 'luck-mark link-' + kind, text));
}
function natalText(n) {
  const parts = ['星运 ' + n.growth_stage, '自坐 ' + n.self_stage, '纳音 ' + n.na_yin];
  n.void_of.forEach(v => parts.push(v === 'day' ? '落日空' : '落年空'));
  n.stem_relations.forEach(r => parts.push(nameMap[r.pillar] + r.stem + '：' + r.labels.map(l => l === '相冲' ? n.pillar[0] + r.stem + l : l).join('·')));
  n.branch_relations.forEach(r => parts.push(nameMap[r.pillar] + r.branch + '：' + n.pillar[1] + r.branch + r.labels.join('·')));
  n.branch_groups.forEach(g => parts.push(g.branches + (g.kind === '三合' ? '三合局' : '三会方') + '（' + g.element + '）'));
  if ((n.shensha || []).length) parts.push(['神煞', n.shensha.map(x => x.name).join('、')].join(' '));
  return parts.join(' · ');
}
function renderLuckStrip(parent, b) {
  const box = append(parent, 'section', 'luck');
  append(box, 'h4', 'subheading', '大运与流年');
  if (currentInput.gender === 'unspecified') {append(box, 'p', 'field-help', '在出生资料里选择性别后，按年干阴阳和性别排出大运顺逆。'); return;}
  if (luckKey !== luckKeyNow()) {ensureLuck(); append(box, 'p', 'field-help', '正在排大运…'); return;}
  if (!luckData) {append(box, 'p', 'inline-msg', '大运暂时排不出来，可以在「大运干支」里单独计算。'); return;}
  // 虚龄 counts from the lunar birth year, which is the previous civil year for births before the new year.
  const birthYear = b.lunar_date.year, thisYear = new Date().getFullYear();
  const decades = luckData.periods.map(d => ({...d, from: Number(d.approx_start_local.slice(0, 4)), to: Number(d.approx_end_local_exclusive.slice(0, 4))}));
  const now = decades.findIndex(d => thisYear >= d.from && thisYear < d.to);
  if (luckDecade === null) luckDecade = Math.max(now, 0);
  const strip = append(box, 'div', 'luck-strip');
  decades.forEach((d, i) => {
    const btn = append(strip, 'button', 'luck-cell luck-decade' + (i === luckDecade ? ' active' : '') + (i === now ? ' now' : ''));
    btn.type = 'button'; btn.id = 'luck-decade-' + i; btn.setAttribute('aria-pressed', String(i === luckDecade));
    append(btn, 'small', 'luck-god', tenGodOf(b.day_master, d.pillar[0]));
    append(btn, 'b', 'luck-char ' + stemClass(d.pillar[0]), d.pillar[0]);
    append(btn, 'b', 'luck-char ' + branchClass(d.pillar[1]), d.pillar[1]);
    if (d.natal_interactions) append(btn, 'small', 'luck-stage', d.natal_interactions.growth_stage);
    append(btn, 'small', null, d.from + '–' + (d.to - 1));
    const age = append(btn, 'small', 'luck-age'); age.append('起运'); age.append(' ' + Math.round(d.approx_start_age_years));
    if (d.natal_interactions) {natalMarks(btn, d.natal_interactions); btn.title = natalText(d.natal_interactions);}
    btn.addEventListener('click', () => {luckDecade = i; render();});
  });
  const d = decades[luckDecade];
  append(box, 'p', 'luck-caption', `${d.pillar} 大运 · ${d.from}–${d.to - 1}`);
  if (d.natal_interactions) append(box, 'p', 'luck-natal', natalText(d.natal_interactions));
  const years = append(box, 'div', 'luck-years');
  const yearInfo = new Map((d.years || []).map(x => [x.year, x]));
  for (let y = d.from; y < d.to; y++) {
    const pillar = yearPillarOf(y), info = yearInfo.get(y);
    const btn = append(years, 'button', 'luck-cell luck-year' + (y === thisYear ? ' now' : ''));
    btn.type = 'button'; btn.id = 'luck-year-' + y;
    const supported = y >= 1901 && y <= 2099;
    btn.title = supported ? '在紫微盘打开 ' + y + ' 年流年层' : '超出 1901–2099 的计算范围';
    append(btn, 'small', null, String(y));
    const chars = append(btn, 'span', 'luck-pair');
    append(chars, 'b', stemClass(pillar[0]), pillar[0]); append(chars, 'b', branchClass(pillar[1]), pillar[1]);
    append(btn, 'small', 'luck-god', tenGodOf(b.day_master, pillar[0]));
    const age = append(btn, 'small', 'luck-age'); age.append('虚龄'); age.append(' ' + (y - birthYear + 1));
    if (info) {append(btn, 'small', 'luck-stage', info.growth_stage); natalMarks(btn, info); btn.title = y + ' ' + pillar + ' · ' + natalText(info) + ' · ' + btn.title;}
    if (!supported) {btn.disabled = true; continue;}
    btn.addEventListener('click', () => {
      ziweiLayer = {mode: 'year', decade: null, year: y, date: null};
      activateTab(tabs.find(t => t.dataset.tab === 'ziwei'));
      announce('紫微盘已切到 ' + y + ' 年流年层');
    });
  }
  append(box, 'p', 'field-help', '十神按日主看天干，下面的小字是日主在该支的星运。格子底部是与原局地支的关系：冲月是与月柱六冲，合、刑、害同理，同是同支；日空、年空是落在日柱或年柱的旬空。所选大运的天干关系、三合三会和神煞写在上方一行，流年的写在悬停说明里。只列关系与标签，不判断吉凶。交运年份由三日折一岁换算，是近似值；流年以立春换年。点流年会在紫微盘打开同一年的流年层。');
}
// Relations between the four pillars as brackets from the centre of one pillar to the centre of another, stems above
// the pillars and branches below; the shortest brackets sit next to the pillars. Every bracket carries its label.
const PILLAR_KEYS = ['year', 'month', 'day', 'hour'];
function pillarLinks(parent, links, below) {
  if (!links.length) return null;
  const rows = [];
  links.map(l => ({...l})).sort((a, b) => (a.to - a.from) - (b.to - b.from) || a.from - b.from).forEach(l => {
    let row = rows.find(r => r.every(o => l.to < o.from || l.from > o.to));
    if (!row) rows.push(row = []);
    row.push(l);
  });
  const box = append(parent, 'div', 'pillar-links' + (below ? ' below' : ''));
  box.setAttribute('aria-label', below ? '地支关系' : '天干关系');
  (below ? rows : [...rows].reverse()).forEach(row => {
    const line = append(box, 'div', 'pillar-link-row');
    row.forEach(l => {
      const item = append(line, 'div', 'pillar-link link-' + l.kind);
      item.style.gridColumn = `${l.from + 1} / ${l.to + 2}`;
      item.style.setProperty('--n', String(l.to - l.from + 1));
      append(item, 'span', 'pillar-link-arc');
      append(item, 'span', 'pillar-link-label', l.label);
    });
  });
  return box;
}
function baziLinks(b) {
  const at = key => PILLAR_KEYS.indexOf(key);
  const stems = (b.stem_relations || []).filter(x => x.labels.length).map(x => ({from: at(x.a), to: at(x.b), pillars: [x.a, x.b],
    kind: x.labels[0] === '相冲' ? 'clash' : 'combine', label: x.labels.map(l => l === '相冲' ? x.stems.replace('/', '') + '相冲' : l).join('·')}));
  const branches = b.branch_relations.filter(x => x.labels.length).map(x => ({from: at(x.a), to: at(x.b), pillars: [x.a, x.b],
    kind: LINK_CLASS[x.labels[0]] || 'same', label: x.branches.replace('/', '') + x.labels.join('·')}))
    .concat((b.branch_groups || []).map(g => {
      const columns = g.pillars.map(at);
      return {from: Math.min(...columns), to: Math.max(...columns), kind: 'group', pillars: g.pillars, branches: g.branches,
        label: g.branches + (g.kind === '三合' ? '三合局' : '三会方') + '（' + g.element + '）'};
    }));
  return {stems, branches};
}
function renderBazi(b) {
  title(result, '四柱命式', '太阳节令 · 藏干十神 · 纳音 · 星运 · 空亡');
  const links = baziLinks(b);
  pillarLinks(result, links.stems, false);
  const grid = append(result, 'div', 'pillar-grid');
  for (const [key, p] of Object.entries(b.pillars)) {
    const box = append(grid, 'div', 'pillar' + (key === 'day' ? ' day-master' : ''));
    if (key === 'day') append(box, 'span', 'pillar-badge', '日主');
    append(box, 'div', 'pillar-head', nameMap[key]);
    append(box, 'div', 'pillar-god', p.ten_god_of_stem);
    append(box, 'div', 'pillar-stem ' + elementClass(p.stem_element), p.stem);
    const branch = append(box, 'div', 'pillar-branch ' + elementClass(p.branch_element), p.branch);
    // A branch inside the day pillar's or the year pillar's 旬空 is marked on the branch itself.
    if ((p.void_of || []).length) {
      const mark = append(branch, 'span', 'void-mark', p.void_of.map(k => k === 'day' ? '日空' : '年空').join('·'));
      mark.title = p.void_of.map(k => k === 'day' ? '落在日柱旬空' : '落在年柱旬空').join('；');
    }
    append(box, 'div', 'pillar-sub', p.stem_element + ' / ' + p.branch_element);
    const hidden = append(box, 'div', 'pillar-hidden');
    hidden.setAttribute('aria-label', '藏干');
    p.hidden_stems.forEach(h => {
      const row = append(hidden, 'span', 'hidden-stem');
      append(row, 'b', elementClass(h.element), h.stem); row.append(h.ten_god);
    });
    if (p.growth_stage) {
      const stage = append(box, 'div', 'pillar-stage');
      append(stage, 'span', 'pillar-stage-label', '星运'); append(stage, 'b', null, p.growth_stage);
      append(stage, 'span', 'pillar-stage-label', '自坐'); append(stage, 'b', null, p.self_stage);
      const empty = append(box, 'div', 'pillar-stage');
      append(empty, 'span', 'pillar-stage-label', '空亡'); append(empty, 'b', null, p.xun_kong);
    }
    append(box, 'div', 'pillar-nayin', '纳音：' + p.na_yin);
    const sha = append(box, 'div', 'pillar-shensha');
    append(sha, 'span', 'pillar-stage-label', '神煞');
    // A noon placeholder is not a real hour pillar, so it carries no stars either.
    if (key === 'hour' && currentHourUnknown) append(sha, 'span', 'muted', '时辰不详');
    else if (shenshaUnsettled(b)) append(sha, 'span', 'muted', '随时辰而定');
    else if (!(p.shensha || []).length) append(sha, 'span', 'muted', '—');
    else p.shensha.forEach(x => {const tag = append(sha, 'span', 'shensha-tag', x.name); tag.title = shenshaBasis(x);});
  }
  pillarLinks(result, links.branches, true);
  renderLuckStrip(result, b);
  append(result, 'h4', 'subheading', '明干 + 地支本气 · 五行数量');
  const five = append(result, 'div', 'five-row');
  Object.entries(b.surface_five_elements).forEach(([name, value]) => {
    const item = append(five, 'div', 'five-box');
    append(item, 'strong', elementClass(name), String(value)); append(item, 'span', null, name);
  });
  append(result, 'h4', 'subheading', '五行分布');
  elementBars(result, b.surface_five_elements, b.hidden_stem_elements_unweighted);
  append(result, 'h4', 'subheading', '地支关系标签与藏干统计');
  const relationBox = append(result, 'div', 'relationship-grid');
  (b.stem_relations || []).filter(x => x.labels.length).forEach(x => append(relationBox, 'div', 'symbol-tag', `${nameMap[x.a]}·${nameMap[x.b]} ${x.stems} ${x.labels.join(' / ')}`));
  b.branch_relations.filter(x => x.labels.length).forEach(x => append(relationBox, 'div', 'symbol-tag', `${nameMap[x.a]}·${nameMap[x.b]} ${x.branches} ${x.labels.join(' / ')}`));
  (b.branch_groups || []).forEach(g => append(relationBox, 'div', 'symbol-tag', `${g.pillars.map(k => nameMap[k]).join('·')} ${g.branches} ${g.kind}（${g.element}）`));
  if (!relationBox.childElementCount) append(relationBox, 'p', 'info-inline', '当前四柱无所列特定关系标签');
  append(result, 'p', 'info-inline', '星运是日主在各柱地支的十二长生，自坐是各柱天干在本柱地支的十二长生（阳干顺行、阴干逆行，火土同宫）；空亡是各柱所在旬余下的两个地支，地支上的「日空」「年空」表示它落在日柱或年柱的旬空里。');
  renderShenshaRules(result, b);
  const cnt = Object.entries(b.hidden_stem_elements_unweighted || {}).map(([n,v]) => `${n}${v}`).join(' · ');
  append(result, 'p', 'info-inline', '藏干元素出现次数（不加权）：' + cnt);
  meta(result, [
    `日主 ${b.day_master} · ${b.day_master_element}`,
    `农历 ${b.lunar_date.year}年${b.lunar_date.is_leap_month ? '闰' : ''}${b.lunar_date.month}月${b.lunar_date.day}日`,
    `换日 ${b.rules.day_boundary}`,
    `时制 ${b.time_basis.mode} · 偏移 ${b.time_basis.effective_shift_minutes.toFixed(1)} 分钟`,
  ]);
  rules(result, [
    {label: '上一节令', value: b.jie_boundaries.previous.name, detail: b.jie_boundaries.previous.instant.replace('T', ' ')},
    {label: '下一节令', value: b.jie_boundaries.next.name, detail: b.jie_boundaries.next.instant.replace('T', ' ')},
  ]);
  note(result, '藏干顺序为传统本气、中气、余气；计数仅统计明干和地支本气，不判断喜忌、旺衰与命运。颜色只标示五行归属。');
}
// 神煞: which natal values place a star on a pillar, and a table of the rule and source of each star the chart shows.
const SHENSHA_BASIS = {day_stem: '日干', year_stem: '年干', day_branch: '日支', year_branch: '年支', month_branch: '月支', day_pillar: '日柱'};
const shenshaBasis = star => '查法起点：' + star.by.map(x => SHENSHA_BASIS[x.basis] + ' ' + x.value).join('、');
// With the hour unknown, a jie inside the birth day can change the year and month pillars, and the 23:00 day change
// or a solar-time shift can move the day pillar; the stars those pillars place are then not settled either.
function shenshaUnsettled(b) {
  if (!currentHourUnknown) return false;
  const day = currentInput.birth_datetime.slice(0, 10);
  return [b.jie_boundaries.previous, b.jie_boundaries.next].some(j => j.instant.slice(0, 10) === day)
    || Boolean(currentInput.late_zi_day_rollover) || Math.abs(b.time_basis.effective_shift_minutes || 0) > 0;
}
function shenshaPillars(b) {
  const keys = currentHourUnknown ? PILLAR_KEYS.slice(0, 3) : PILLAR_KEYS;
  return keys.flatMap(k => (b.pillars[k].shensha || []).map(x => ({...x, pillar: k})));
}
function renderShenshaRules(parent, b) {
  const found = shenshaPillars(b);
  append(parent, 'h4', 'subheading', '神煞与查法出处');
  if (shenshaUnsettled(b)) {
    append(parent, 'p', 'info-inline', '出生时辰不详，而出生当天交节、按 23:00 换日或按太阳时换算，年柱、月柱或日柱可能随时辰变化，神煞也随之不同，这里不列；确定时辰后再看。');
    return;
  }
  if (!found.length) {append(parent, 'p', 'info-inline', currentHourUnknown ? '已知的年、月、日三柱没有所收十六种神煞。' : '四柱没有所收十六种神煞。'); return;}
  const table = append(append(parent, 'div', 'table-wrap'), 'table', 'data-table shensha-table'); table.id = 'shensha-rules';
  const head = append(append(table, 'thead'), 'tr');
  ['神煞', '所在', '查法', '出处'].forEach(x => append(head, 'th', null, x));
  const body = append(table, 'tbody');
  (b.shensha_rules || []).filter(r => found.some(x => x.name === r.name)).forEach(r => {
    const tr = append(body, 'tr');
    append(tr, 'td', 'shensha-name', r.name);
    const where = append(tr, 'td');
    // One pillar per line, so no list separator needs translating.
    found.filter(x => x.name === r.name).forEach(x => {
      const item = append(where, 'span', 'shensha-where', nameMap[x.pillar] + b.pillars[x.pillar].text); item.title = shenshaBasis(x);
    });
    append(tr, 'td', null, r.rule);
    append(tr, 'td', 'muted', r.source);
  });
  append(parent, 'p', 'info-inline', '神煞是传统标签：只收能在古籍里查到安法的十六种，以日干、年干、年支、日支、月支查四柱，时柱不作查法起点；同一种神煞各家表格不尽相同（如阴干是否有羊刃），这里按所列出处。只列名称，不断吉凶。');
}
function findPalace(z, name) {return z.palaces.find(item => item.name === name) || z.palaces.find(item => item.is_ming);}
// Transformations listed in the palace panel. On the Zi Wei board each one is a button: pointing at it or focusing it
// brings out its curve and the two palaces it joins, and a click keeps it highlighted.
let flyPinned = null;
function flyHighlight(focus) {
  const board = document.getElementById('ziwei-board');
  if (!board) return;
  board.classList.toggle('fly-focus', Boolean(focus));
  board.querySelectorAll('.ziwei-lines path.fly').forEach(p => p.classList.toggle('is-hot', Boolean(focus) && p.dataset.key === focus.key));
  board.querySelectorAll('.palace').forEach(n => n.classList.toggle('fly-end', Boolean(focus) && [focus.from, focus.to].includes(n.id)));
}
function flyList(block, cls, label, items, interactive) {
  const line = append(block, 'p', cls);
  if (!interactive || !items.length) {line.textContent = label + (items.map(x => x.text).join('；') || '—'); return line;}
  line.append(label);
  const list = append(line, 'span', 'fly-list');
  items.forEach(x => {
    const focus = {key: x.key, from: 'palace-' + x.from, to: 'palace-' + x.to};
    const item = append(list, 'button', 'fly-item fly-tone-' + (HUA_CLASS[x.type] || 'lu'), x.text); item.type = 'button';
    item.dataset.key = x.key; item.setAttribute('aria-pressed', String(Boolean(flyPinned) && flyPinned.key === x.key));
    item.addEventListener('pointerenter', () => flyHighlight(focus));
    item.addEventListener('focus', () => flyHighlight(focus));
    item.addEventListener('pointerleave', () => flyHighlight(flyPinned));
    item.addEventListener('blur', () => flyHighlight(flyPinned));
    item.addEventListener('click', () => {
      flyPinned = flyPinned && flyPinned.key === x.key ? null : {...focus, palace: selectedPalace, mode: ziweiLayer.mode};
      block.querySelectorAll('.fly-item').forEach(b => b.setAttribute('aria-pressed', String(Boolean(flyPinned) && b.dataset.key === flyPinned.key)));
      flyHighlight(flyPinned || focus);
    });
  });
  return line;
}
function renderPalacePanel(parent, palace, layer, interactive = false) {
  const block = append(parent, 'div', 'palace-panel');
  append(block, 'h4', null, `${palace.name} · ${palace.stem}${palace.branch}`);
  const z = current && current.ziwei, index = currentPalaceIndex(palace);
  const at = name => z ? z.palaces.findIndex(p => p.name === name) : -1;
  if (layer) {
    append(block, 'p', 'layer-line', `${layer.label}：本宫为${LAYER_NAMES[layer.mode]}${layer.layerName(currentPalaceIndex(palace))}`);
    // When the layer's curves coincide with this palace's own, they are drawn once, under the palace's keys.
    const own = z && !layerFlying(z, palace, layer) && palace.name === z.palaces[layer.anchor].name;
    flyList(block, 'layer-line', `${LAYER_NAMES[layer.mode]}四化（${layer.stem}干）：`, layer.hua.map(t => ({text: `${t.star}${t.type}→${t.target_palace}`,
      key: (own ? 'out|' : 'layer|') + t.star + t.type, from: layer.anchor, to: at(t.target_palace), type: t.type})), interactive);
    const flow = (layer.flow || []).filter(f => f.index === index).map(f => f.name);
    if (layer.flow) append(block, 'p', 'layer-line', `${LAYER_NAMES[layer.mode]}流曜：` + (flow.join('、') || '—'));
    if (layer.twelve) append(block, 'p', 'layer-line', `流年岁前：${layer.twelve[index][0]}；流年将前：${layer.twelve[index][1]}`);
  }
  append(block, 'p', null, '主星：' + (palace.main_stars.map(star => withBrightness(palace, star)).join('、') || '空宫（未安十四主星）'));
  append(block, 'p', null, '辅星：' + (palace.auxiliary_stars.map(star => withBrightness(palace, star)).join('、') || '—'));
  append(block, 'p', null, '生年四化：' + (palace.birth_year_transformations.map(t => `${t.star}${t.type}`).join('、') || '此宫无生年四化标记'));
  flyList(block, 'fly-out', '宫干飞化：', palace.palace_flying_transformations.map(t => ({text: `${t.star}${t.type}→${t.target_palace}${t.self_transform ? '（自化）' : ''}`,
    key: 'out|' + t.star + t.type, from: index, to: at(t.target_palace), type: t.type})), interactive);
  // The reverse view: which other palaces' stems transform a star sitting here.
  const incoming = z ? z.palaces.filter(p => p.name !== palace.name).flatMap(p => p.palace_flying_transformations
    .filter(t => t.target_palace === palace.name).map(t => ({text: `${p.name}（${p.stem}干）${t.star}${t.type}`,
      key: `in|${p.name}|${t.star}${t.type}`, from: z.palaces.indexOf(p), to: index, type: t.type}))) : [];
  if (incoming.length) flyList(block, 'fly-in', '飞入本宫：', incoming, interactive);
  else append(block, 'p', 'fly-in', '飞入本宫：').append('无其他宫位的宫干四化飞入');
  if (palace.three_harmonies_and_opposite) {
    const link = palace.three_harmonies_and_opposite;
    append(block, 'p', null, '三方四正：' + link.trine.map(x => `${x.palace}·${x.branch}`).join('、') + '；对宫 ' + link.opposite.palace + '·' + link.opposite.branch);
  }
}
// Birth-year transformation → badge class (禄 / 权 / 科 / 忌).
const HUA_CLASS = {'化禄':'lu','化权':'quan','化科':'ke','化忌':'ji'};
const LAYER_NAMES = {decade: '大限', small_limit: '小限', year: '流年', month: '流月', day: '流日'};
// Layer transformations get an outlined badge with a 限 / 年 prefix, so they are
// told apart from birth-year ones by shape and text, not by colour alone.
function currentPalaceIndex(palace) {return current && current.ziwei ? current.ziwei.palaces.indexOf(palace) : -1;}
function huaBadge(parent, type, layer) {
  const prefix = layer ? LAYER_NAMES[layer].slice(-1) : '';
  const badge = append(parent, 'span', 'hua hua-' + (HUA_CLASS[type] || 'lu') + (layer ? ' layer' : ''), prefix + type.replace('化', ''));
  badge.title = (layer ? LAYER_NAMES[layer] : '生年') + type;
  return badge;
}
// Star brightness 庙旺得利平不陷 after the star name. The level is drawn by CSS from data-level, so each
// language shows its own short form (平 alone already means a day officer elsewhere in the interface).
const BRIGHT_LEVELS = '庙旺得利平不陷';
const BRIGHT_CLASS = Object.fromEntries([...BRIGHT_LEVELS].map((level, i) => [level, ['miao', 'wang', 'de', 'li', 'ping', 'bu', 'xian'][i]]));
function brightMark(parent, level) {
  if (!BRIGHT_CLASS[level]) return null;
  const mark = append(parent, 'span', 'bright bright-' + BRIGHT_CLASS[level]);
  mark.dataset.level = level; mark.title = '亮度：' + level;
  return mark;
}
function withBrightness(palace, star) {
  const level = (palace.star_brightness || {})[star];
  return level ? `${star}（${level}）` : star;
}
// Grid cell (row, column) of each palace index on the traditional 4×4 board.
const ZIWEI_CELLS = {5:[1,1], 6:[1,2], 7:[1,3], 8:[1,4], 4:[2,1], 9:[2,4], 3:[3,1], 10:[3,4], 2:[4,1], 1:[4,2], 0:[4,3], 11:[4,4]};
function ziweiLines(board, z, selected, live) {
  const link = selected && selected.three_harmonies_and_opposite;
  if (!link) return;
  const svgNS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(svgNS, 'svg');
  svg.setAttribute('class', 'ziwei-lines'); svg.setAttribute('viewBox', '0 0 400 400');
  svg.setAttribute('preserveAspectRatio', 'none'); svg.setAttribute('aria-hidden', 'true');
  const centre = name => {
    const index = z.palaces.findIndex(p => p.name === name);
    const cell = ZIWEI_CELLS[index];
    return cell ? [(cell[1] - .5) * 100, (cell[0] - .5) * 100] : null;
  };
  const from = centre(selected.name);
  const targets = [...link.trine.map(x => [x.palace, 'trine']), [link.opposite.palace, 'opposite']];
  const points = [from, ...link.trine.map(x => centre(x.palace))];
  const line = (a, b, cls) => {
    if (!a || !b) return;
    const el = document.createElementNS(svgNS, 'line');
    el.setAttribute('x1', a[0]); el.setAttribute('y1', a[1]); el.setAttribute('x2', b[0]); el.setAttribute('y2', b[1]);
    if (cls) el.setAttribute('class', cls);
    svg.append(el);
  };
  // The three harmonies form a triangle; the opposite palace gets its own line.
  line(points[0], points[1]); line(points[1], points[2]); line(points[2], points[0]);
  targets.filter(x => x[1] === 'opposite').forEach(x => line(from, centre(x[0]), 'opposite'));
  // Stem transformations fly to the palaces holding those stars. Each curve bows towards the middle of the
  // board, so it shows between the cells, and ends at the edge of the target cell.
  const curve = (startName, t, i, kind) => {
    const layer = kind === 'layer';
    const start = centre(startName), to = centre(t.target_palace);
    if (!start || !to || t.target_palace === startName) return;  // a transformation in its own palace stays a badge
    const mid = [(start[0] + to[0]) / 2, (start[1] + to[1]) / 2];
    const pull = [200 - mid[0], 200 - mid[1]];
    const length = Math.hypot(pull[0], pull[1]) || 1;
    const spread = (i - 1.5) * 9 + (layer ? 4.5 : 0);  // curves to one palace stay apart
    const control = [mid[0] + pull[0] * .7 - pull[1] / length * spread, mid[1] + pull[1] * .7 + pull[0] / length * spread];
    const edge = (point, toward) => {
      const d = [toward[0] - point[0], toward[1] - point[1]], scale = 44 / (Math.max(Math.abs(d[0]), Math.abs(d[1])) || 1);
      return [point[0] + d[0] * scale, point[1] + d[1] * scale];
    };
    const a = edge(start, control), b = edge(to, control);
    const path = document.createElementNS(svgNS, 'path');
    path.setAttribute('d', `M${a[0]} ${a[1]} Q${control[0]} ${control[1]} ${b[0]} ${b[1]}`);
    path.setAttribute('class', 'fly fly-' + (HUA_CLASS[t.type] || 'lu') + (kind === 'out' ? '' : ' ' + kind));
    path.dataset.key = kind === 'in' ? `in|${startName}|${t.star}${t.type}` : `${kind}|${t.star}${t.type}`;
    svg.append(path);
  };
  if (showFlying) {
    selected.palace_flying_transformations.forEach((t, i) => curve(selected.name, t, i, 'out'));
    // On a time layer, that layer's four transformations start from the layer's Life palace, dotted.
    if (layerFlying(z, selected, live)) live.hua.forEach((t, i) => curve(z.palaces[live.anchor].name, t, i, 'layer'));
    // Transformations flying in from other palaces stay hidden until their entry in the palace panel is pointed at.
    z.palaces.filter(p => p.name !== selected.name).forEach(p => p.palace_flying_transformations
      .filter(t => t.target_palace === selected.name).forEach((t, i) => curve(p.name, t, i, 'in')));
  }
  board.prepend(svg);
}
// Stars that carry more than one transformation across the birth year and the layers in force that moment: the
// decade inside a year, and the decade, year and month above a month or a day. Only the combination is listed.
function huaOverlaps(z, live) {
  const stemHua = stem => (z.palaces.find(p => p.stem === stem) || {palace_flying_transformations: []}).palace_flying_transformations;
  const sets = [['生年', z.birth_year_transformations]];
  if (live.mode === 'decade') sets.push(['大限', live.hua]);
  else if (live.mode === 'year') {
    // The decade needs the birth hour; with the hour unknown it is left out, as the decade layer itself is.
    if (live.currentDecade && !currentHourUnknown) sets.push(['大限', stemHua(live.currentDecade.stem)]);
    sets.push(['流年', live.hua]);
  } else if (live.horoscope && live.horoscope.layers) {
    const order = ['decade', 'year', 'month', 'day'];
    order.slice(0, order.indexOf(live.mode) + 1).forEach(key => {
      const item = live.horoscope.layers[key];
      if (item && item.available) sets.push([LAYER_NAMES[key], item.transformations]);
    });
  }
  const byStar = new Map();
  sets.forEach(([label, list]) => list.forEach(t => {
    if (!byStar.has(t.star)) byStar.set(t.star, []);
    byStar.get(t.star).push(label + t.type);
  }));
  return [...byStar].filter(([, list]) => list.length > 1).map(([star, list]) => ({star, list}));
}
// The layer's own curves, unless they would repeat the selected palace's: the layer Life palace with the layer stem.
function layerFlying(z, selected, live) {
  if (!showFlying || !live || !live.hua.length) return false;
  return !(selected.name === z.palaces[live.anchor].name && selected.stem === live.stem);
}
// Arrow keys move the selection to the palace in that direction; across the empty middle they reach the far side.
const ZIWEI_STEPS = {ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1]};
function ziweiNeighbour(index, key) {
  const step = ZIWEI_STEPS[key];
  if (!step) return null;
  let [row, col] = ZIWEI_CELLS[index];
  for (;;) {
    row += step[0]; col += step[1];
    if (row < 1 || row > 4 || col < 1 || col > 4) return null;
    const found = Object.keys(ZIWEI_CELLS).find(k => ZIWEI_CELLS[k][0] === row && ZIWEI_CELLS[k][1] === col);
    if (found !== undefined) return Number(found);
  }
}
// Badge text in the palace a transformation flies into; a self-transformation stays in its own palace.
const FLY_MARKS = {'化禄': ['禄入', '自化禄'], '化权': ['权入', '自化权'], '化科': ['科入', '自化科'], '化忌': ['忌入', '自化忌']};
let showFlying = true;
const STEM_ORDER = '甲乙丙丁戊己庚辛壬癸', BRANCH_ORDER = '子丑寅卯辰巳午未申酉戌亥';
// Today's lunar year comes from the calendar engine, so the default 流年 changes on the real Chinese New Year.
let todayLunarYear = null, todayLunarPending = false;
function ensureTodayLunarYear() {
  if (todayLunarYear !== null || todayLunarPending) return;
  todayLunarPending = true;
  postJSON('/api/calendar', {start_date: localToday(), days: 1}).then(data => {
    todayLunarYear = data.days[0].lunar.year;
    if (active === 'ziwei' && ziweiLayer.mode === 'year' && ziweiLayer.year === null) render();
  }).catch(() => { /* keep the estimate below */ }).finally(() => {todayLunarPending = false;});
}
function defaultLunarYear() {
  if (todayLunarYear !== null) return todayLunarYear;
  const today = new Date();  // estimate until the engine answers: New Year falls between 21 January and 20 February
  return today.getFullYear() - (today.getMonth() === 0 || (today.getMonth() === 1 && today.getDate() < 20) ? 1 : 0);
}
// Everything a layer needs comes from the natal chart itself: palace i sits on
// branch i, every heavenly stem owns at least one palace (五虎遁), and that
// palace's flying transformations are the stem's 四化 with their positions.
// 流曜 of the decade and year layers from the layer's stem and branch, with the tables app/ziwei_horoscope.py uses
// (the browser smoke test compares the two); the month and day layers take theirs from the server.
const FLOW_NAMES = {decade: ['运魁', '运钺', '运昌', '运曲', '运禄', '运羊', '运陀', '运马', '运鸾', '运喜'],
  year: ['流魁', '流钺', '流昌', '流曲', '流禄', '流羊', '流陀', '流马', '流鸾', '流喜']};
function flowStars(stem, branch, mode) {
  const s = STEM_ORDER.indexOf(stem), b = BRANCH_ORDER.indexOf(branch);
  const lu = [2, 3, 5, 6, 5, 6, 8, 9, 11, 0][s], luan = (15 - b) % 12;
  const kuiYue = [[1, 7], [0, 8], [11, 9], [11, 9], [1, 7], [0, 8], [1, 7], [6, 2], [3, 5], [3, 5]][s];
  const changQu = [[5, 9], [6, 8], [8, 6], [9, 5], [8, 6], [9, 5], [11, 3], [0, 2], [2, 0], [3, 11]][s];
  const places = [...kuiYue, ...changQu, lu, (lu + 1) % 12, (lu + 11) % 12, [2, 11, 8, 5][b % 4], luan, (luan + 6) % 12];
  const stars = FLOW_NAMES[mode].map((name, i) => ({name, index: places[i]}));
  if (mode === 'year') stars.push({name: '年解', index: (22 - b) % 12});
  return stars;
}
// 流年岁前 from the year branch and 将前 from its triad's 将星, as [岁前, 将前] per branch.
const SUIQIAN_NAMES = ['岁建', '晦气', '丧门', '贯索', '官符', '小耗', '大耗', '龙德', '白虎', '天德', '吊客', '病符'];
const JIANGQIAN_NAMES = ['将星', '攀鞍', '岁驿', '息神', '华盖', '劫煞', '灾煞', '天煞', '指背', '咸池', '月煞', '亡神'];
function yearTwelve(branch) {
  const b = BRANCH_ORDER.indexOf(branch), star = [0, 9, 6, 3][b % 4];
  return Array.from({length: 12}, (_, i) => [SUIQIAN_NAMES[(i - b + 12) % 12], JIANGQIAN_NAMES[(i - star + 12) % 12]]);
}
function ziweiLayerInfo(z) {
  const mode = ziweiLayer.mode;
  if (mode === 'natal') return null;
  const mingIndex = z.palaces.findIndex(p => p.is_ming);
  const names = Array.from({length: 12}, (_, k) => z.palaces[(mingIndex - k + 12) % 12].name);
  const birthYear = z.lunar_date && z.lunar_date.year;
  const year = Math.min(2099, Math.max(1901, ziweiLayer.year || defaultLunarYear()));
  const age = birthYear ? year - birthYear + 1 : null;
  const decades = z.palaces.filter(p => p.decade).sort((a, b) => a.decade.start_age - b.decade.start_age);
  const currentDecade = age ? decades.find(p => age >= p.decade.start_age && age <= p.decade.end_age) || null : null;
  const smallLimit = age ? z.palaces.find(p => (p.small_limit_nominal_ages || []).includes(age)) || null : null;
  let anchor, stem, label, flow, twelve = null;
  if (mode === 'month' || mode === 'day') {
    if (currentHourUnknown) return {mode, unavailable: '流月、流日按出生时辰定斗君；时辰不详时无法确定。'};
    const h = ziweiHoroscope();
    if (h.error) return {mode, unavailable: '运限计算失败：' + h.error};
    if (h.pending) return {mode, pending: true, unavailable: '正在计算运限…', horoscope: h.stale || null};
    const item = h.layers[mode];
    if (!item.available) return {mode, horoscope: h, unavailable: item.reason};
    const at = BRANCH_ORDER.indexOf(item.ming_branch);
    const stemOwner = z.palaces.find(p => p.stem === item.stem);
    const marks = ['decade', 'year'].concat(mode === 'day' ? ['month'] : []).filter(key => h.layers[key].available)
      .map(key => ({index: BRANCH_ORDER.indexOf(h.layers[key].ming_branch), text: LAYER_NAMES[key]}));
    return {mode, anchor: at, stem: item.stem, label: item.label, horoscope: h, marks, age: h.nominal_age,
      flow: item.stars.map(f => ({name: f.name, index: BRANCH_ORDER.indexOf(f.branch)})),
      hua: stemOwner ? stemOwner.palace_flying_transformations : [], layerName: index => names[(at - index + 12) % 12]};
  }
  if (mode === 'decade') {
    if (currentHourUnknown) return {mode, unavailable: '大限从命宫起，需要出生时辰；时辰不详时无法确定。'};
    if (!decades.length) return {mode, unavailable: '大限需要性别来定顺行或逆行，请在出生资料里选择性别后重新生成命盘。'};
    const start = ziweiLayer.decade !== null ? ziweiLayer.decade : (currentDecade || decades[0]).decade.start_age;
    const palace = decades.find(p => p.decade.start_age === start) || decades[0];
    anchor = z.palaces.indexOf(palace); stem = palace.stem; flow = flowStars(palace.stem, palace.branch, 'decade');
    label = `大限 ${palace.decade.start_age}–${palace.decade.end_age} 岁 · ${palace.stem}${palace.branch}`;
  } else {
    stem = STEM_ORDER[((year - 4) % 10 + 10) % 10];
    const branch = BRANCH_ORDER[((year - 4) % 12 + 12) % 12];
    anchor = BRANCH_ORDER.indexOf(branch); flow = flowStars(stem, branch, 'year'); twelve = yearTwelve(branch);
    label = `${year} ${stem}${branch}年` + (age && age > 0 ? ` · 虚岁 ${age}` : '');
  }
  const stemPalace = z.palaces.find(p => p.stem === stem);
  return {mode, anchor, stem, label, year, age, decades, currentDecade, smallLimit, flow, twelve,
    hua: stemPalace ? stemPalace.palace_flying_transformations : [],
    layerName: index => names[(anchor - index + 12) % 12]};
}
function ziweiHoroscope() {
  const request = {birth: currentInput, target_date: ziweiLayer.date || localToday(), hour_unknown: currentHourUnknown};
  const key = JSON.stringify(request);
  if (horoscopeKey !== key) {
    horoscopeKey = key; horoscopeError = '';
    postJSON('/api/ziwei-horoscope', request)
      .then(data => {
        if (horoscopeKey !== key) return;
        horoscopeResult = data; horoscopeResultKey = key;
        // The highlighted palace follows the new layer's 命宫 once it is known.
        const item = data.layers[ziweiLayer.mode];
        if (item && item.available && current) selectedPalace = current.ziwei.palaces[BRANCH_ORDER.indexOf(item.ming_branch)].name;
      })
      .catch(err => {if (horoscopeKey === key) horoscopeError = err.message;})
      .finally(() => {if (horoscopeKey === key && active === 'ziwei') render();});
  }
  if (horoscopeError) return {error: horoscopeError};
  return horoscopeResultKey === key ? horoscopeResult : {pending: true, stale: horoscopeResult};
}
// Every layer in force on the chosen date, one line each: where its 命宫 sits and its stem's 四化.
function renderHoroscopeStack(h) {
  const stack = append(result, 'div', 'layer-stack'); stack.id = 'ziwei-layer-stack';
  append(stack, 'h4', null, '这一天的运限');
  ['decade', 'small_limit', 'year', 'month', 'day'].forEach(key => {
    const item = h.layers[key];
    const row = append(stack, 'div', 'layer-stack-row' + (key === ziweiLayer.mode ? ' active' : ''));
    append(row, 'b', null, LAYER_NAMES[key]);
    if (!item.available) {append(row, 'span', 'muted', item.reason); return;}
    if (item.ming_natal_palace) texts(append(row, 'span'), '命宫在', ' ' + item.ming_branch, ' · ', '本命', ' ' + item.ming_natal_palace);
    else texts(append(row, 'span'), '命宫在', ' ' + item.ming_branch);
    const hua = append(row, 'span', 'layer-stack-hua');
    hua.append(item.stem + '：');
    item.transformations.forEach(t => {const s = append(hua, 'span'); s.append(t.star); huaBadge(s, t.type, key);});
  });
}
// Every layer in force, side by side: what each layer calls each palace and which of its 四化 land there.
// Month and day layers come from the horoscope engine; the decade and year layers from the chart itself.
function layerColumns(z, live) {
  const ming = z.palaces.findIndex(p => p.is_ming);
  const names = Array.from({length: 12}, (_, k) => z.palaces[(ming - k + 12) % 12].name);
  const hua = stem => {
    const owner = z.palaces.find(p => p.stem === stem);  // a stem's 四化 do not depend on which palace carries it
    return owner ? owner.palace_flying_transformations.map(t => ({type: t.type, star: t.star, index: BRANCH_ORDER.indexOf(t.target_branch)})) : [];
  };
  const layer = (key, anchor, stem) => ({key, label: LAYER_NAMES[key], anchor, name: index => names[(anchor - index + 12) % 12], hua: hua(stem)});
  const columns = [{key: 'natal', label: '本命', anchor: ming, name: index => z.palaces[index].name,
    hua: z.palaces.flatMap((p, index) => p.birth_year_transformations.map(t => ({type: t.type, star: t.star, index})))}];
  if (live.horoscope) {
    ['decade', 'small_limit', 'year', 'month', 'day'].forEach(key => {
      const item = live.horoscope.layers[key];
      if (item && item.available) columns.push(layer(key, BRANCH_ORDER.indexOf(item.ming_branch), item.stem));
    });
  } else if (live.mode === 'decade') {
    columns.push(layer('decade', live.anchor, live.stem));
  } else {
    if (live.currentDecade) columns.push(layer('decade', z.palaces.indexOf(live.currentDecade), live.currentDecade.stem));
    if (live.smallLimit) columns.push(layer('small_limit', z.palaces.indexOf(live.smallLimit), live.smallLimit.stem));
    columns.push(layer('year', live.anchor, live.stem));
  }
  return columns;
}
function renderLayerTable(z, live) {
  // Palace names and star positions move with the hour, so the table needs a known birth hour.
  if (currentHourUnknown) {append(result, 'p', 'field-help', '时辰不详时，各宫名称和星曜位置会随时辰变化，不列各层宫位对照表。'); return;}
  const columns = layerColumns(z, live);
  const ming = z.palaces.findIndex(p => p.is_ming);
  const rows = Array.from({length: 12}, (_, k) => (ming - k + 12) % 12);  // natal order from 命宫
  const box = append(result, 'details', 'layer-table-box'); box.id = 'ziwei-layer-table';
  const summary = append(box, 'summary');
  append(summary, 'b', null, '各层宫位对照表'); append(summary, 'span', 'muted', live.label);
  append(box, 'p', 'field-help', '每一行是盘上的同一个宫位：各列写它在这一层叫什么宫，以及这一层的四化有哪几颗落在这里；高亮的格子是各层的命宫。点行首的干支，盘上就选中那一宫。');
  const table = append(append(box, 'div', 'table-wrap'), 'table', 'data-table layer-table');
  const head = append(append(table, 'thead'), 'tr');
  append(head, 'th', null, '宫干支').scope = 'col';
  columns.forEach(c => {append(head, 'th', c.key === live.mode ? 'active' : null, c.label).scope = 'col';});
  const body = append(table, 'tbody');
  const cellHua = (c, index) => c.hua.filter(t => t.index === index);
  rows.forEach(index => {
    const p = z.palaces[index], chosen = p.name === selectedPalace;
    const tr = append(body, 'tr', chosen ? 'selected' : null);
    const th = append(tr, 'th'); th.scope = 'row';
    const pick = append(th, 'button', 'layer-table-pick', p.stem + p.branch); pick.type = 'button'; pick.id = 'layer-table-pick-' + index;
    pick.setAttribute('aria-pressed', String(chosen)); pick.title = p.name;
    pick.addEventListener('click', () => {selectedPalace = p.name; render();});
    columns.forEach(c => {
      const td = append(tr, 'td', [c.anchor === index ? 'layer-ming' : '', c.key === live.mode ? 'active' : ''].join(' ').trim() || null);
      append(td, 'span', 'layer-table-name', c.name(index).replace(/宫$/, ''));
      cellHua(c, index).forEach(t => {
        const item = append(td, 'span', 'layer-table-hua'); item.append(t.star);
        const badge = append(item, 'span', 'hua hua-' + (HUA_CLASS[t.type] || 'lu') + (c.key === 'natal' ? '' : ' layer'), t.type.replace('化', ''));
        badge.title = (c.key === 'natal' ? '生年' : c.label) + t.type;
      });
    });
  });
  // Tab-separated, so it pastes into a spreadsheet as a table, in the interface language.
  const copy = append(box, 'button', 'tiny-button', '复制表格'); copy.type = 'button'; copy.id = 'ziwei-layer-table-copy';
  copy.addEventListener('click', async () => {
    const T = text => typeof translateText === 'function' ? translateText(text) : text;
    const lines = [['宫干支'].concat(columns.map(c => c.label))].concat(rows.map(index => [z.palaces[index].stem + z.palaces[index].branch]
      .concat(columns.map(c => [c.name(index)].concat(cellHua(c, index).map(t => t.star + t.type)).join(' ')))));
    const tsv = lines.map(cells => cells.map(T).join('\t')).join('\n');
    try {await navigator.clipboard.writeText(tsv); copy.textContent = '已复制表格';}
    catch (_) {copy.textContent = '复制失败，请手动选中表格';}
  });
}
function setZiweiLayer(z, change) {
  Object.assign(ziweiLayer, change);
  const info = ziweiLayerInfo(z);
  // The highlighted palace follows the layer's own 命宫, so the 三方四正 lines move with it.
  const anchor = info && !info.unavailable ? z.palaces[info.anchor] : z.palaces.find(p => p.is_ming);
  if (anchor) selectedPalace = anchor.name;
  render();
}
function renderZiweiLayerBar(z, layer) {
  const bar = append(result, 'div', 'layer-bar');
  const modes = append(bar, 'div', 'layer-modes');
  modes.setAttribute('role', 'group'); modes.setAttribute('aria-label', '运限层');
  [['natal', '本命'], ['decade', '大限'], ['year', '流年'], ['month', '流月'], ['day', '流日']].forEach(([mode, text]) => {
    const button = append(modes, 'button', 'layer-btn' + (ziweiLayer.mode === mode ? ' active' : ''), text);
    button.type = 'button'; button.id = 'ziwei-layer-' + mode;
    button.setAttribute('aria-pressed', String(ziweiLayer.mode === mode));
    button.addEventListener('click', () => setZiweiLayer(z, {mode}));
  });
  if (!layer) {append(bar, 'small', 'layer-hint', '切到大限、流年、流月或流日，宫名、四化和三方四正会按那一层重新标注。'); return;}
  if (layer.mode === 'month' || layer.mode === 'day') {renderDateLayerStep(bar, z, layer); return;}
  if (layer.unavailable) {append(bar, 'small', 'layer-hint', layer.unavailable); return;}
  const step = append(bar, 'div', 'layer-step');
  const move = delta => {
    if (layer.mode === 'decade') {
      const list = layer.decades;
      const index = list.indexOf(z.palaces[layer.anchor]);
      const next = list[Math.min(list.length - 1, Math.max(0, index + delta))];
      setZiweiLayer(z, {decade: next.decade.start_age});
    } else setZiweiLayer(z, {year: Math.min(2099, Math.max(1901, layer.year + delta))});
  };
  const prev = append(step, 'button', 'tiny-button', '‹'); prev.type = 'button'; prev.id = 'ziwei-layer-prev';
  prev.setAttribute('aria-label', layer.mode === 'decade' ? '上一个大限' : '上一年');
  prev.disabled = layer.mode === 'decade' ? layer.decades.indexOf(z.palaces[layer.anchor]) <= 0 : layer.year <= 1901;
  prev.addEventListener('click', () => move(-1));
  append(step, 'b', 'layer-label', layer.label);
  const next = append(step, 'button', 'tiny-button', '›'); next.type = 'button'; next.id = 'ziwei-layer-next';
  next.setAttribute('aria-label', layer.mode === 'decade' ? '下一个大限' : '下一年');
  next.disabled = layer.mode === 'decade' ? layer.decades.indexOf(z.palaces[layer.anchor]) >= layer.decades.length - 1 : layer.year >= 2099;
  next.addEventListener('click', () => move(1));
  const now = append(step, 'button', 'tiny-button', layer.mode === 'decade' ? '当前大限' : '今年'); now.type = 'button'; now.id = 'ziwei-layer-now';
  now.addEventListener('click', () => setZiweiLayer(z, layer.mode === 'decade' ? {decade: null, year: null} : {year: null}));
}
// 流月 / 流日: pick any date, step by the engine's month segments or by one day.
function renderDateLayerStep(bar, z, layer) {
  const step = append(bar, 'div', 'layer-step');
  const nav = layer.horoscope ? layer.horoscope.navigation : null;
  const month = layer.mode === 'month';
  const target = (month ? ['previous_month', 'next_month'] : ['previous_day', 'next_day']).map(key => nav && nav[key]);
  const birthDay = currentInput.birth_datetime.slice(0, 10);
  const prev = append(step, 'button', 'tiny-button', '‹'); prev.type = 'button'; prev.id = 'ziwei-layer-prev';
  prev.setAttribute('aria-label', month ? '上一个流月' : '前一天');
  prev.disabled = !target[0] || target[0] < birthDay;
  prev.addEventListener('click', () => setZiweiLayer(z, {date: target[0]}));
  const picker = append(step, 'input', 'layer-date'); picker.type = 'date'; picker.id = 'ziwei-layer-date';
  picker.setAttribute('aria-label', month ? '流月日期' : '流日日期');
  picker.min = birthDay > '1901-02-19' ? birthDay : '1901-02-19'; picker.max = '2099-12-31';
  picker.value = ziweiLayer.date || localToday();
  picker.addEventListener('change', () => {if (picker.value) setZiweiLayer(z, {date: picker.value});});
  const next = append(step, 'button', 'tiny-button', '›'); next.type = 'button'; next.id = 'ziwei-layer-next';
  next.setAttribute('aria-label', month ? '下一个流月' : '后一天');
  next.disabled = !target[1];
  next.addEventListener('click', () => setZiweiLayer(z, {date: target[1]}));
  const now = append(step, 'button', 'tiny-button', month ? '本月' : '今天'); now.type = 'button'; now.id = 'ziwei-layer-now';
  now.addEventListener('click', () => setZiweiLayer(z, {date: null}));
  if (layer.unavailable) append(bar, 'small', 'layer-hint', layer.unavailable);
  else append(bar, 'b', 'layer-label', layer.label);
}
function renderZiwei(z) {
  title(result, '紫微十二宫', '点击宫位：高亮三方四正并查看宫干飞化；上方切换本命、大限、流年、流月、流日');
  meta(result, [`命宫 ${z.ming_palace}`, `身宫 ${z.shen_palace}`, z.five_elements_bureau, `命主 ${z.ming_master}`, `身主 ${z.shen_master}`, z.transformation_school]);
  ensureTodayLunarYear();
  const layer = ziweiLayerInfo(z);
  renderZiweiLayerBar(z, layer);
  if (layer && layer.horoscope && !layer.pending) renderHoroscopeStack(layer.horoscope);
  const live = layer && !layer.unavailable ? layer : null;
  const stacked = new Map(live ? huaOverlaps(z, live).map(o => [o.star, o.list]) : []);
  const selected = findPalace(z, selectedPalace);
  const related = new Set();
  if (selected.three_harmonies_and_opposite) {
    selected.three_harmonies_and_opposite.trine.forEach(x => related.add(x.palace));
    related.add(selected.three_harmonies_and_opposite.opposite.palace);
  }
  const wrap = append(result, 'div', 'ziwei-wrap');
  append(wrap, 'p', 'ziwei-scroll-hint', '← 左右滑动查看完整十二宫 →');
  const board = append(wrap, 'div', 'ziwei-board' + (live ? ' layered' : ''));
  board.id = 'ziwei-board';
  z.palaces.forEach((p, index) => {
    const node = append(board, 'button', 'palace palace-btn' + (p.is_ming ? ' ming' : '') + (p.is_shen ? ' shen' : '')
      + (selected.name === p.name ? ' selected' : '') + (related.has(p.name) ? ' sanfang' : '') + (live && index === live.anchor ? ' layer-anchor' : ''));
    node.type = 'button'; node.id = 'palace-' + index;
    node.style.gridRow = String(ZIWEI_CELLS[index][0]);
    node.style.gridColumn = String(ZIWEI_CELLS[index][1]);
    node.setAttribute('aria-label', `查看${p.name}飞化`);
    node.setAttribute('aria-pressed', String(selected.name === p.name));
    // One tab stop for the board: Tab reaches the selected palace and the arrow keys move between palaces.
    node.tabIndex = selected.name === p.name ? 0 : -1;
    node.setAttribute('aria-keyshortcuts', 'ArrowUp ArrowDown ArrowLeft ArrowRight');
    const head = append(node, 'div', 'palace-head');
    append(head, 'b', null, p.name.replace('宫', '')); append(head, 'span', 'palace-ganzhi', p.stem + p.branch);
    if (live) {
      const tag = append(node, 'div', 'palace-layer');
      append(tag, 'span', null, LAYER_NAMES[live.mode]); tag.append('·'); append(tag, 'span', null, live.layerName(index).replace('宫', ''));
    }
    const holders = {};
    const layerHua = star => {
      if (!live) return;
      live.hua.filter(t => t.star === star).forEach(t => huaBadge(holders[star], t.type, live.mode));
      if (stacked.has(star)) {holders[star].classList.add('hua-stack'); holders[star].title = '四化叠加：' + stacked.get(star).join('、');}
    };
    const stars = append(node, 'div', 'star-primary');
    if (!p.main_stars.length) append(stars, 'span', 'star', '—');
    const bright = p.star_brightness || {};
    p.main_stars.forEach(star => {
      holders[star] = append(stars, 'span', 'star', star);
      brightMark(holders[star], bright[star]);
      p.birth_year_transformations.filter(t => t.star === star).forEach(t => huaBadge(holders[star], t.type));
      layerHua(star);
    });
    const aux = append(node, 'div', 'star-secondary');
    p.auxiliary_stars.forEach((star, i) => {
      if (i) aux.append(' · ');
      holders[star] = append(aux, 'span', 'star', star);
      brightMark(holders[star], bright[star]);
      p.birth_year_transformations.filter(t => t.star === star).forEach(t => huaBadge(holders[star], t.type));
      layerHua(star);
    });
    // The layer's own 流曜, outlined like its 四化: 禄 and the 羊陀 pair get their own colours.
    const flow = live && live.flow ? live.flow.filter(f => f.index === index) : [];
    if (flow.length) {
      const line = append(node, 'div', 'star-flow');
      flow.forEach(f => append(line, 'span', 'flow-star' + (/[禄]$/.test(f.name) ? ' flow-lu' : /[羊陀]$/.test(f.name) ? ' flow-sha' : ''), f.name));
    }
    const cycles = p.natal_cycles || {};
    // On the 流年 layer that year's 岁前 takes the place of the natal one.
    const suiqian = live && live.twelve ? live.twelve[index][0] : cycles.natal_suiqian;
    // 长生 and 博士 need a gender; 岁前 follows the year branch alone, so it shows either way.
    const gendered = [cycles.changsheng, cycles.boshi].filter(Boolean);
    if (gendered.length || suiqian) {
      const line = append(node, 'div', 'palace-cycles', gendered.join(' · '));
      if (suiqian) {if (gendered.length) line.append(' · '); append(line, 'span', live && live.twelve ? 'layer-cycle' : null, suiqian);}
    }
    const foot = append(node, 'div', 'palace-foot');
    const marks = append(foot, 'span');
    if (p.is_ming) append(marks, 'span', 'palace-mark', '命');
    if (p.is_shen) append(marks, 'span', 'palace-mark shen-mark', '身');
    if (live && live.mode === 'year' && live.currentDecade === p) append(marks, 'span', 'palace-mark layer-mark', '大限');
    if (live && live.mode === 'year' && live.smallLimit === p) append(marks, 'span', 'palace-mark layer-mark', '小限');
    if (live && live.marks) live.marks.filter(m => m.index === index).forEach(m => append(marks, 'span', 'palace-mark layer-mark', m.text));
    if (showFlying) selected.palace_flying_transformations.filter(t => t.target_palace === p.name).forEach(t => {
      const mark = elt('span', 'palace-mark fly-mark fly-' + (HUA_CLASS[t.type] || 'lu'), FLY_MARKS[t.type][t.self_transform ? 1 : 0]);
      mark.title = `${selected.name}：${t.star}${t.type}→${p.name}${t.self_transform ? '（自化）' : ''}`;
      marks.append(mark);
    });
    if (p.decade) append(foot, 'span', 'decade', `${p.decade.start_age}–${p.decade.end_age}岁`);
    if (p.small_limit_nominal_ages) node.title = '小限虚岁：' + p.small_limit_nominal_ages.slice(0, 6).join('、') + '…';
    node.addEventListener('click', () => {selectedPalace = p.name; render();});
    node.addEventListener('keydown', event => {
      const next = ziweiNeighbour(index, event.key);
      if (next === null) return;
      event.preventDefault();
      selectedPalace = z.palaces[next].name; render();
      // On a narrow screen the board scrolls sideways: bring the new palace into view without jumping the page.
      const target = document.getElementById('palace-' + next);
      if (target) {target.focus({preventScroll: true}); target.scrollIntoView({block: 'nearest', inline: 'nearest'});}
    });
  });
  ziweiLines(board, z, selected, live);
  const center = append(board, 'div', 'board-center see-through');
  append(center, 'div', 'center-symbol', '☯');
  append(center, 'div', 'center-title', '紫 微 斗 数');
  append(center, 'div', 'center-sub', z.year_pillar + ' · ' + z.five_elements_bureau);
  append(center, 'div', 'center-sub', `命主 ${z.ming_master} · 身主 ${z.shen_master}`);
  append(center, 'div', 'center-sub', `${z.star_counts.main} 主星 · ${z.star_counts.auxiliary} 辅星 · 生年四化`);
  if (live) append(center, 'div', 'center-layer', live.label + ' · ' + live.stem + '干四化');
  const legend = append(result, 'div', 'hua-legend');
  ['化禄', '化权', '化科', '化忌'].forEach(type => {const s = append(legend, 'span'); huaBadge(s, type); s.append(' ' + type);});
  if (live) {const s = append(legend, 'span'); huaBadge(s, '化禄', live.mode); s.append(' 描边：' + LAYER_NAMES[live.mode] + '四化');}
  const brightLegend = append(legend, 'span', 'bright-legend');
  brightMark(brightLegend, BRIGHT_LEVELS[0]); append(brightLegend, 'span', null, '亮度：庙旺得利平不陷，由强到弱');
  const tri = append(legend, 'span', 'legend-lines', '虚线：所选宫位的三方；实线：对宫');
  tri.style.marginLeft = 'auto';
  const fly = append(legend, 'button', 'filter-chip fly-toggle', '飞化连线'); fly.type = 'button'; fly.id = 'ziwei-fly-toggle';
  fly.setAttribute('aria-pressed', String(showFlying));
  fly.title = '彩色曲线：所选宫位的宫干四化飞入哪一宫';
  if (layerFlying(z, selected, live)) append(legend, 'span', 'legend-lines', '点线：' + LAYER_NAMES[live.mode] + '四化飞入的宫位');
  fly.addEventListener('click', () => {showFlying = !showFlying; if (!showFlying) flyPinned = null; render();});
  if (live) {
    const line = append(result, 'p', 'hua-overlap');
    append(line, 'span', 'hua-overlap-label', '四化叠加：');
    const overlaps = huaOverlaps(z, live);
    if (!overlaps.length) line.append('生年与各层四化没有两项落在同一颗星');
    overlaps.forEach(o => {
      const item = append(line, 'span', 'hua-overlap-item');
      append(item, 'b', null, o.star); item.append('（' + o.list.join('、') + '）');
    });
  }
  // A highlight kept from a click lasts while the same palace and layer stay selected.
  if (flyPinned && (!showFlying || flyPinned.palace !== selected.name || flyPinned.mode !== ziweiLayer.mode)) flyPinned = null;
  renderPalacePanel(result, selected, live, showFlying);  // with the curves hidden the entries are plain text
  if (flyPinned && !result.querySelector('.fly-item[aria-pressed="true"]')) flyPinned = null;
  flyHighlight(flyPinned);
  if (live) renderLayerTable(z, live);
  if (live) note(result, '运限层按公开的传统规则标注：大限按五行局起运、阳男阴女顺行，四化取大限宫干；流年命宫取当年地支所在宫，四化取年干；小限按虚岁；流月按斗君（从流年命宫逆数到生月、再顺数到生时为正月）逐月顺行，四化取月干；流日从流月命宫起初一逐日顺行，四化取日干。各层按本层干支安魁钺昌曲禄羊陀马鸾喜十颗流曜（大限称运曜），流年另安年解，并以当年地支起岁前、将前十二神。不预测具体事件。');
  note(result, `部分排盘：现含 ${z.star_counts.main} 主星与 ${z.star_counts.auxiliary} 颗选定辅/杂曜、四组十二神（部分依性别）、主星与昌曲火铃羊陀的庙旺利陷、运限流曜及经度时制选择；不含全流派。所有展示均不等于命运预测。`);
}
function renderTransform(z) {
  title(result, '生年四化 / 宫干飞化', '《全书》系公开十干四化表 · 流派差异需核对');
  const cards = append(result, 'div', 'transform-grid');
  z.birth_year_transformations.forEach(item => {
    const box = append(cards, 'div', 'transform-card hua-card-' + (HUA_CLASS[item.type] || 'lu'));
    const type = append(box, 'div', 'transform-type'); huaBadge(type, item.type); type.append(' ' + item.type);
    append(box, 'div', 'transform-star', item.star);
    append(box, 'div', 'transform-palace', item.palace_name + ' · ' + item.palace);
  });
  append(result, 'h4', 'subheading', '十二宫宫干飞化查询');
  const row = append(result, 'div', 'inline-control');
  const label = append(row, 'label', null, '选择宫位');
  const picker = append(label, 'select', null);
  z.palaces.forEach(p => {const opt = append(picker, 'option', null, p.name + ' · ' + p.stem + p.branch); opt.value = p.name;});
  picker.value = selectedPalace;
  picker.addEventListener('change', () => {selectedPalace = picker.value; render();});
  renderPalacePanel(result, findPalace(z, selectedPalace));
  note(result, '四化是星曜的传统标识，不是新增星曜；宫干飞化仅列出四化星所在宫，尚未实施完整飞星断法。');
}
function renderReading(reading) {
  title(result, '透明的文化解释', '计算字段 → 传统标签 → 适用范围');
  const ul = append(result, 'ul', 'reading-list');
  reading.points.forEach(x => append(ul, 'li', null, x));
  append(result, 'h4', 'subheading', '规则限制');
  reading.limitations.forEach(x => append(result, 'div', 'feature-note', x));
}
function createInput(labelText, type, value, parent) {
  const label = append(parent, 'label', null, labelText);
  const control = append(label, 'input');
  control.type = type; control.value = value;
  return control;
}
// Solar terms (and, if asked, the four principal moon phases) for one year as an ICS file. The fetch carries
// the optional API token, so the file is saved through a blob rather than a plain link.
const icsHref = (year, moon) => '/api/solar-terms/' + year + '.ics' + (moon ? '?moon=true' : '');
async function downloadIcs(year, moon, message) {
  const token = $('#api_token').value;
  try {
    const reply = await fetch(icsHref(year, moon), {headers: token ? {'Authorization': 'Bearer ' + token} : {}});
    if (!reply.ok) throw new Error('HTTP ' + reply.status);
    const url = URL.createObjectURL(await reply.blob());
    const link = elt('a'); link.href = url; link.download = (moon ? 'solar-terms-moon-' : 'solar-terms-') + year + '.ics';
    document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 2000);
  } catch (e) {message.textContent = '下载失败：' + e.message;}
}
function renderCalendar() {
  title(result, '农历 · 干支日历', '一至三十一日 · 以中国标准时间计算');
  const row = append(result, 'div', 'inline-control');
  const start = createInput('开始日期', 'date', calendarDraft.start_date, row);
  start.min = '1901-01-01'; start.max = '2099-12-31'; start.id = 'calendar_start';
  const dayLabel = append(row, 'label', null, '查询天数');
  const count = append(dayLabel, 'select'); count.id = 'calendar_days';
  [7, 14, 21, 31].forEach(value => {const opt = append(count, 'option', null, value + ' 天'); opt.value = String(value);});
  count.value = String(calendarDraft.days);
  const run = append(row, 'button', null, '查询日历'); run.type = 'button'; run.id = 'calendar-run';
  const ics = append(row, 'a', 'tiny-button', '全年节气 ICS 日历下载');
  const moonIcs = append(row, 'a', 'tiny-button', '节气与月相 ICS'); moonIcs.id = 'calendar-moon-ics';
  const year = () => (start.value || calendarDraft.start_date).slice(0, 4);
  const setLinks = () => {ics.href = icsHref(year(), false); moonIcs.href = icsHref(year(), true);};
  setLinks();
  start.addEventListener('change', () => {if (start.value) setLinks();});
  ics.addEventListener('click', event => {event.preventDefault(); downloadIcs(year(), false, message);});
  moonIcs.addEventListener('click', event => {event.preventDefault(); downloadIcs(year(), true, message);});
  const message = append(result, 'p', 'inline-msg');
  run.addEventListener('click', async () => {
    if (!start.value) {message.textContent = '请选择有效日期'; return;}
    calendarDraft = {start_date: start.value, days: Number(count.value)};
    run.disabled = true; message.textContent = '';
    try {calendarResult = await postJSON('/api/calendar', calendarDraft); render();}
    catch (err) {message.textContent = '查询失败：' + err.message;}
    finally {run.disabled = false;}
  });
  renderLunarInverseSection();
  if (!calendarResult) {
    append(result, 'p', 'info-inline', '点击「查询日历」查看农历、日柱与当日节气时间。此功能不提供吉凶宜忌。');
    return;
  }
  const wrap = append(result, 'div', 'table-wrap');
  const table = append(wrap, 'table', 'data-table');
  const head = append(table, 'thead');
  const hr = append(head, 'tr');
  ['公历日期', '星期', '农历', '日干支', '节气（北京时间）'].forEach(text => append(hr, 'th', null, text));
  const body = append(table, 'tbody');
  calendarResult.days.forEach(d => {
    const tr = append(body, 'tr');
    append(tr, 'td', null, d.date);
    append(tr, 'td', null, '星期' + d.weekday);
    append(tr, 'td', null, `${d.lunar.year}年${d.lunar.is_leap_month ? '闰' : ''}${d.lunar.month}月${d.lunar.day}日`);
    append(tr, 'td', 'pillar-cell', d.day_pillar);
    append(tr, 'td', null, d.solar_terms.map(t => t.name + ' ' + t.time_china.substring(11,16)).join(' · ') || '—');
  });
  note(result, calendarResult.notes.join(' '));
}
function renderDayOfficers() {
  title(result,'建除十二值日','节令月支 × 日支 · 仅传统标签，不给吉凶或宜忌结论');
  const row=append(result,'div','inline-control');
  const start=createInput('查询起始日（北京时间）','date',officerDraft.start_date,row);
  start.id='officer-date';start.min='1901-01-01';start.max='2099-12-31';
  const count=append(append(row,'label',null,'查询长度'),'select');count.id='officer-days';
  [7,14,30,60,90].forEach(x=>{const op=append(count,'option',null,`${x} 天`);op.value=String(x);});count.value=String(officerDraft.days);
  const select=append(append(row,'label',null,'筛选值日'),'select');select.id='officer-filter';
  for(const value of ['','建','除','满','平','定','执','破','危','成','收','开','闭']){
    const op=append(select,'option',null,value||'全部');op.value=value;
  } select.value=officerDraft.officer;
  const run=append(row,'button',null,'查询值日');run.id='officer-run';run.type='button';
  const msg=append(result,'p','inline-msg');
  run.addEventListener('click',async()=>{
    officerDraft={start_date:start.value,days:Number(count.value),officer:select.value};
    run.disabled=true;msg.textContent='';
    try{officerResult=await postJSON('/api/day-officers',{start_date:officerDraft.start_date,days:officerDraft.days,filter_officers:officerDraft.officer?[officerDraft.officer]:[]});render();}
    catch(e){msg.textContent='查询失败：'+e.message;}
    finally{run.disabled=false;}
  });
  if(!officerResult){append(result,'p','info-inline','查询按北京时间正午取值；跨交节的日期会显式标记。');return;}
  meta(result,[`范围 ${officerResult.range_start}`,`已返回 ${officerResult.days.length} 日`,'不对日期好坏打分']);
  const table=append(append(result,'div','table-wrap'),'table','data-table');
  const hr=append(append(table,'thead'),'tr');
  ['公历日','日干支','正午月建','十二值日','节令切换日'].forEach(x=>append(hr,'th',null,x));
  const body=append(table,'tbody');
  officerResult.days.forEach(d=>{
    const tr=append(body,'tr');
    [d.date,d.day_pillar,d.month_branch_at_noon,d.officer,d.jie_boundary_on_date?'是 · 日内可能变化':'—'].forEach(x=>append(tr,'td',null,x));
  });
  if(!officerResult.days.length)append(result,'p','feature-note','查询范围内未找到所筛选的标签。');
  officerResult.limitations.forEach(x=>note(result,x));
}
let dateScanResult = null;
let dateScanFingerprint = null;
// The scan depends on the birth fields (natal filter) and the zone (hour charts).
function dateScanStamp(natal, hours) {
  return JSON.stringify({birth: natal ? readInput() : null, timezone: hours ? $('#timezone').value : null});
}
function dateScanStale() {
  return !!dateScanResult && dateScanFingerprint !== dateScanStamp(dateScanResult.criteria.exclude_natal_clash, dateScanResult.criteria.hours.length > 0);
}
// No criteria are preselected: every exclusion is the user's own choice.
let dateScanDraft = {start_date: localToday(), days: 30, include:[], exclude:[], skipJie:false, natal:false, hours:''};
function renderDateScan() {
  title(result,'择日择时','按你选的传统条件筛选候选日，可附加每个候选日指定时刻的时家奇门盘 · 按日期排列，不打吉凶分');
  const row=append(result,'div','inline-control');
  const start=createInput('起始日','date',dateScanDraft.start_date,row);start.id='scan-date';start.min='1901-01-01';start.max='2099-12-31';
  const count=append(append(row,'label',null,'扫描天数'),'select');count.id='scan-days';
  [7,14,30,60,93].forEach(x=>{const op=append(count,'option',null,`${x} 天`);op.value=String(x);});count.value=String(dateScanDraft.days);
  const hours=createInput('候选时刻（选填，逗号分隔，如 09:00,15:00）','text',dateScanDraft.hours,row);hours.id='scan-hours';hours.maxLength=40;
  const officers=['建','除','满','平','定','执','破','危','成','收','开','闭'];
  const pick=(label,key,id)=>{
    const box=append(result,'div','consult-shortcuts');box.id=id;append(box,'small','small-text',label);
    officers.forEach(o=>{const l=append(box,'label','check-line');const c=append(l,'input');c.type='checkbox';c.value=o;c.checked=dateScanDraft[key].includes(o);l.append(' '+o);});
    return box;
  };
  const inc=pick('只保留这些值日（不选=不限）','include','scan-include');
  const exc=pick('排除这些值日','exclude','scan-exclude');
  const opts=append(result,'div','consult-shortcuts');
  const jl=append(opts,'label','check-line');const jie=append(jl,'input');jie.type='checkbox';jie.id='scan-skip-jie';jie.checked=dateScanDraft.skipJie;jl.append(' 排除交节当天');
  const nl=append(opts,'label','check-line');const natal=append(nl,'input');natal.type='checkbox';natal.id='scan-natal';natal.checked=dateScanDraft.natal;nl.append(' 排除与本命年支、日支相冲的日子');
  const run=append(opts,'button',null,'扫描候选日');run.id='scan-run';run.type='button';
  const msg=append(result,'p','inline-msg');
  run.addEventListener('click',async()=>{
    const checked=box=>[...box.querySelectorAll('input:checked')].map(x=>x.value);
    dateScanDraft={start_date:start.value,days:Number(count.value),include:checked(inc),exclude:checked(exc),skipJie:jie.checked,natal:natal.checked,hours:hours.value};
    const payload={start_date:dateScanDraft.start_date,days:dateScanDraft.days,include_officers:dateScanDraft.include,exclude_officers:dateScanDraft.exclude,
      exclude_jie_boundary_days:dateScanDraft.skipJie,hours:dateScanDraft.hours.split(/[,，\s]+/).filter(Boolean),timezone:$('#timezone').value};
    if(dateScanDraft.natal){payload.birth=readInput();if(payload.birth.longitude===null)delete payload.birth.longitude;payload.exclude_natal_clash=true;}
    run.disabled=true;msg.textContent='';
    const stamp=dateScanStamp(dateScanDraft.natal,payload.hours.length>0);
    try{dateScanResult=await postJSON('/api/date-scan',payload);dateScanFingerprint=stamp;render();}
    catch(e){msg.textContent='扫描失败：'+e.message;}
    finally{run.disabled=false;}
  });
  if(dateScanStale()){dateScanResult=null;dateScanFingerprint=null;append(result,'p','info-inline','出生参数或时区已更改，旧的扫描结果已清除，请重新扫描。');return;}
  if(!dateScanResult){append(result,'p','info-inline','先选条件再扫描。结果只是传统标签筛选，最终取舍以现实安排为准。');return;}
  const ex=dateScanResult.excluded_counts;
  meta(result,[`候选 ${dateScanResult.candidates.length} 日`,`排除：值日 ${ex.officer_not_included+ex.officer_excluded} · 交节 ${ex.jie_boundary} · 相冲 ${ex.natal_clash}`,dateScanResult.truncated?'结果已达上限':'按日期排列']);
  const table=append(append(result,'div','table-wrap'),'table','data-table');
  const hr=append(append(table,'thead'),'tr');
  ['公历日','农历','日干支','值日','本命相冲','时家奇门'].forEach(x=>append(hr,'th',null,x));
  const body=append(table,'tbody');
  dateScanResult.candidates.forEach(c=>{
    const tr=append(body,'tr');
    const lunar=c.lunar_date.year+'年'+(c.lunar_date.is_leap_month?'闰':'')+c.lunar_date.month+'月'+c.lunar_date.day+'日';
    const clash=c.natal_clashes.map(x=>x.day_branch+'冲'+x.natal_branch).join('、')||'—';
    const qimen=c.hour_charts.map(h=>`${h.local_time} ${h.dun}${h.bureau}局 值符${h.zhi_fu_star} 值使${h.zhi_shi_door}`).join('；')||'—';
    [c.date,lunar,c.day_pillar,c.officer,clash,qimen].forEach(x=>append(tr,'td',null,x));
  });
  if(!dateScanResult.candidates.length)append(result,'p','feature-note','没有满足全部条件的日子，可以放宽条件或延长扫描天数。');
  dateScanResult.limitations.forEach(x=>note(result,x));
}
function renderTimeline() {
  title(result,'连续农历年四化对照','本命盘固定，叠加多个命名农历年的天干四化标签');
  if(!current){append(result,'p','info-inline','请先生成命盘。');return;}
  const row=append(result,'div','inline-control');
  const start=createInput('起始农历年','number',String(timelineDraft.start_lunar_year),row);start.id='timeline-start';start.min='1901';start.max='2099';
  const years=append(append(row,'label',null,'对照年数'),'select');years.id='timeline-years';
  [3,5,10,20,30].forEach(x=>{const op=append(years,'option',null,x+' 年');op.value=String(x);});years.value=String(timelineDraft.years);
  const focus=append(append(row,'label',null,'关注宫位'),'select');focus.id='timeline-focus';
  const all=append(focus,'option',null,'全部十二宫');all.value='';
  current.ziwei.palaces.forEach(p=>{const op=append(focus,'option',null,p.name);op.value=p.name;});focus.value=timelineDraft.focus_palace;
  const run=append(row,'button',null,'生成年度轨迹');run.id='timeline-run';run.type='button';
  const msg=append(result,'p','inline-msg');
  run.addEventListener('click',async()=>{
    timelineDraft={start_lunar_year:Number(start.value),years:Number(years.value),focus_palace:focus.value};
    run.disabled=true;msg.textContent='';
    try{timelineResult=await postJSON('/api/annual-timeline',{birth:readInput(),start_lunar_year:timelineDraft.start_lunar_year,years:timelineDraft.years,focus_palace:timelineDraft.focus_palace||null});render();}
    catch(e){msg.textContent='查询失败：'+e.message;}
    finally{run.disabled=false;}
  });
  if(!timelineResult){append(result,'p','info-inline','选择起始农历年和年数，可按本命宫位查看每年的四化标记。');return;}
  meta(result,[`起始 ${timelineResult.start_lunar_year}`,`对照 ${timelineResult.years} 年`,timelineResult.school]);
  const table=append(append(result,'div','table-wrap'),'table','data-table');
  const head=append(append(table,'thead'),'tr');
  ['农历年','化禄','化权','化科','化忌',...(timelineDraft.focus_palace?['所选宫位']:[])].forEach(t=>append(head,'th',null,t));
  const tbody=append(table,'tbody');
  timelineResult.entries.forEach(year=>{
    const row=append(tbody,'tr'); append(row,'td',null,year.lunar_year+' · '+year.year_pillar);
    year.transformations.forEach(t=>append(row,'td',null,t.star+' → '+t.natal_palace));
    if(timelineDraft.focus_palace)append(row,'td',null,year.focus_hits.map(t=>t.star+t.type).join(' · ')||'—');
  });
  timelineResult.limitations.forEach(x=>note(result,x));
}
function numericEntry(input) { return input.value.trim() === '' ? NaN : Number(input.value); }
function readDecisionDraft() {
  const question=$('#decision-question')?.value.trim()||'';
  const criteria=[...result.querySelectorAll('.criterion-edit')].map(node=>({name:node.querySelector('.criterion-name').value.trim(),weight:numericEntry(node.querySelector('.criterion-weight'))}));
  const options=[...result.querySelectorAll('.option-edit')].map(node=>({name:node.querySelector('.option-name').value.trim(),ratings:[...node.querySelectorAll('.option-rating')].map(numericEntry)}));
  return {question,criteria,options};
}
function renderDecision() {
  title(result,'透明方案决策矩阵','权重归一化 · 逐项贡献 · 剔除单项敏感性 · 无命理加权');
  append(result,'p','info-inline','这里的分数均为你自己输入的主观假设，不能代表客观成功率。');
  const question=createInput('你要比较什么？','text',decisionDraft.question,result);question.id='decision-question';question.maxLength=300;
  append(result,'h4','subheading','评价维度（权重必须大于零）');
  decisionDraft.criteria.forEach((c,i)=>{
    const row=append(result,'div','inline-control criterion-edit');
    createInput('指标 '+(i+1),'text',c.name,row).className='criterion-name';
    const w=createInput('权重','number',String(c.weight),row);w.className='criterion-weight';w.min='.01';w.max='100';w.step='.01';
    const remove=append(row,'button','tiny-button remove-criterion','移除指标');remove.type='button';remove.disabled=decisionDraft.criteria.length<=1;
    remove.addEventListener('click',()=>{const draft=readDecisionDraft();if(draft.criteria.length<=1)return;draft.criteria.splice(i,1);draft.options.forEach(opt=>opt.ratings.splice(i,1));decisionDraft=draft;decisionResult=null;render();});
  });
  const addCriterion=append(result,'button','tiny-button','+ 增加指标');addCriterion.id='decision-add-criterion';addCriterion.type='button';
  addCriterion.addEventListener('click',()=>{
    const draft=readDecisionDraft(); if(draft.criteria.length>=8)return;
    draft.criteria.push({name:'新指标'+(draft.criteria.length+1),weight:1});draft.options.forEach(x=>x.ratings.push(3));
    decisionDraft=draft;decisionResult=null;render();
  });
  append(result,'h4','subheading','备选方案（每项输入 0–5 的评分）');
  decisionDraft.options.forEach((o,i)=>{
    const row=append(result,'div','inline-control option-edit');
    createInput('方案 '+(i+1),'text',o.name,row).className='option-name';
    decisionDraft.criteria.forEach((c,j)=>{
      const score=createInput(c.name,'number',String(o.ratings[j]??3),row);
      score.className='option-rating';score.min='0';score.max='5';score.step='.5';
    });
    const remove=append(row,'button','tiny-button remove-option','移除方案');remove.type='button';remove.disabled=decisionDraft.options.length<=2;
    remove.addEventListener('click',()=>{const draft=readDecisionDraft();if(draft.options.length<=2)return;draft.options.splice(i,1);decisionDraft=draft;decisionResult=null;render();});
  });
  const controls=append(result,'div','inline-control');
  const addOption=append(controls,'button',null,'+ 增加方案');addOption.id='decision-add-option';addOption.type='button';
  addOption.addEventListener('click',()=>{
    const draft=readDecisionDraft();if(draft.options.length>=8)return;
    draft.options.push({name:'新方案 '+(draft.options.length+1),ratings:draft.criteria.map(()=>3)});
    decisionDraft=draft;decisionResult=null;render();
  });
  const run=append(controls,'button',null,'比较方案');run.id='decision-run';run.type='button';
  const msg=append(result,'p','inline-msg');
  run.addEventListener('click',async()=>{
    decisionDraft=readDecisionDraft();
    const data={question:decisionDraft.question,criteria:decisionDraft.criteria,
      options:decisionDraft.options.map(o=>({name:o.name,ratings:Object.fromEntries(decisionDraft.criteria.map((c,j)=>[c.name,o.ratings[j]]))}))};
    run.disabled=true;msg.textContent='';
    try{decisionResult=await postJSON('/api/decision-matrix',data);render();}
    catch(e){msg.textContent='比较失败：'+e.message;}
    finally{run.disabled=false;}
  });
  if(!decisionResult)return;
  append(result,'h4','subheading','按用户权重计算的方案得分');
  const table=append(append(result,'div','table-wrap'),'table','data-table');
  const hr=append(append(table,'thead'),'tr');['方案','主观加权分数（0–5）','分数来源'].forEach(x=>append(hr,'th',null,x));
  const body=append(table,'tbody');
  decisionResult.ranked_options.forEach(o=>{
    const tr=append(body,'tr');append(tr,'td','user-text',o.name);
    append(tr,'td',null,String(o.score));
    append(tr,'td','user-text',o.contributions.map(c=>`${c.criterion} ${c.rating}×${(100*c.normalized_weight).toFixed(0)}%`).join(' + '));
  });
  append(result,'h4','subheading','单指标剔除敏感性');
  decisionResult.leave_one_out_sensitivity.forEach(x=>append(result,'div','feature-note',
    `去掉「${x.omitted_criterion}」后首位：${x.leaders_without_it.join('、')}${x.leader_changed?' · 结果变化':' · 不变'}`));
  decisionResult.limitations.forEach(x=>note(result,x));
}
// Rule sensitivity matrix: the current chart recomputed under each common rule choice, cell by cell.
let ruleMatrixResult = null, ruleMatrixKey = null, ruleMatrixError = '', ruleMatrixOnlyDiff = false;
function renderRuleMatrix() {
  title(result, '规则差异对照', '同一份出生资料换用各家常见规则重排 · 看哪些字段会变');
  const request = {birth: currentInput, hour_unknown: currentHourUnknown};
  const key = JSON.stringify(request);
  if (ruleMatrixKey !== key) {
    ruleMatrixKey = key; ruleMatrixResult = null; ruleMatrixError = '';
    postJSON('/api/rule-matrix', request)
      .then(data => {if (ruleMatrixKey === key) ruleMatrixResult = data;})
      .catch(err => {if (ruleMatrixKey === key) ruleMatrixError = err.message;})
      .finally(() => {if (active === 'rule-matrix') render();});
  }
  if (ruleMatrixError) {append(result, 'p', 'inline-msg', '对照失败：' + ruleMatrixError); return;}
  if (!ruleMatrixResult) {append(result, 'p', 'field-help', '正在按各种规则重新排盘…'); return;}
  const m = ruleMatrixResult, s = m.summary;
  const cards = append(result, 'div', 'rule-summary');
  const same = append(cards, 'div', 'rule-card');
  texts(append(same, 'strong', 'rule-big'), String(s.identical_variants), ' / ', String(s.variants));
  append(same, 'small', null, '种不同规则下结果与当前完全相同');
  const stable = append(cards, 'div', 'rule-card');
  append(stable, 'small', null, '不受规则影响');
  const stableChips = append(stable, 'div', 'rule-chips');
  if (!s.stable_fields.length) append(stableChips, 'span', 'muted', '—');
  s.stable_fields.forEach(name => append(stableChips, 'span', 'relation-chip rel-harmony', name));
  const moving = append(cards, 'div', 'rule-card');
  append(moving, 'small', null, '会随规则变化');
  const movingChips = append(moving, 'div', 'rule-chips');
  if (!s.sensitive_fields.length) append(movingChips, 'span', 'muted', '—');
  s.sensitive_fields.forEach(f => {
    const chip = texts(append(movingChips, 'span', 'relation-chip rel-clash'), f.label, ' ', String(f.changed_by.length));
    chip.title = f.changed_by.join('\n');
  });
  m.hints.forEach(text => append(result, 'div', 'feature-note', text));
  const controls = append(result, 'div', 'inline-control');
  const toggle = append(controls, 'label', 'check-line');
  const only = append(toggle, 'input'); only.type = 'checkbox'; only.id = 'rule-only-diff'; only.checked = ruleMatrixOnlyDiff;
  toggle.append('只看结果不同的方案');
  only.addEventListener('change', () => {ruleMatrixOnlyDiff = only.checked; render();});
  const wrap = append(result, 'div', 'table-wrap');
  const table = append(wrap, 'table', 'data-table rule-matrix'); table.id = 'rule-matrix';
  const head = append(append(table, 'thead'), 'tr');
  append(head, 'th', null, '规则方案'); append(head, 'th', null, '换算后时间');
  m.fields.forEach(f => append(head, 'th', null, f.label));
  append(head, 'th', null, '');
  const body = append(table, 'tbody');
  m.rows.forEach((row, i) => {
    if (ruleMatrixOnlyDiff && !row.is_baseline && !row.differs.length) return;
    const tr = append(body, 'tr', row.is_baseline ? 'is-baseline' : (row.differs.length ? 'has-diff' : 'is-same'));
    append(tr, 'th', null, row.label);
    append(tr, 'td', 'rule-time', row.effective_reading.replace('T', ' '));
    m.fields.forEach(f => {
      const changed = row.differs.includes(f.key);
      if (row.is_baseline || changed) append(tr, 'td', changed ? 'cell-diff' : null, row.values[f.key]);
      else append(append(tr, 'td'), 'span', 'muted', '＝');
    });
    const action = append(tr, 'td');
    if (!row.is_baseline && row.differs.length && row.applicable) {
      const apply = append(action, 'button', 'tiny-button', '套用'); apply.type = 'button'; apply.id = 'rule-apply-' + i;
      apply.addEventListener('click', () => {setInput(row.settings); form.requestSubmit(); setFeedback('已套用：' + row.label);});
    } else if (!row.is_baseline && row.differs.length) append(action, 'small', 'muted', '需手动改时间');
  });
  append(result, 'p', 'field-help', '“＝”表示与当前设置相同；标色的格子是换用这条规则后不同的结果。套用会把这条规则写进出生资料并重新排盘。扣除夏令时改的是出生时间本身的读法，不能直接套用；确认出生记录用的是夏令时后，请手动改出生时间。');
  m.notes.forEach(text => note(result, text));
}
// Group relations: two to eight charts from the current form, local profiles and members added here.
// Members added on this page live only in memory; nothing is stored.
let groupResult = null, groupKey = null, groupResultKeys = [], groupChatBlock = null;
// The year of the luck and year-pillar view. A newer request (another year, or 对照关系) makes older replies stale.
// A 对照关系 run waiting for its reply keeps its members here: switching the year meanwhile asks for those
// members, not the ones of the result shown.
let groupYearTicket = 0, groupYearPending = false, groupYearError = '', groupRun = null, groupRunError = '';
// Member notes stay on this page: the current chart's and temporary members' are never stored, a saved
// profile's only after 「保存到档案」. Notes never go to the server; only the chat draft the user sends carries them.
let groupDraft = {useCurrent: true, currentLabel: '我', currentNote: {key: '', text: ''}, profiles: [], profileNotes: {}, extras: [], filter: 'all', focus: null,
  extra: {label: '', birth_datetime: '1990-01-01T12:00', timezone: 'Asia/Shanghai', gender: 'unspecified', hour_unknown: false},
  year: new Date().getFullYear()};
const NOTE_MAX = 120;
function profileNote(entry) {return entry && typeof entry.note === 'string' ? entry.note.slice(0, NOTE_MAX) : '';}
function saveProfileNote(id, note) {
  const profiles = loadProfiles(), entry = profiles.find(x => x.id === id);
  if (!entry) return false;
  const text = note.trim().slice(0, NOTE_MAX);
  if (text) entry.note = text; else delete entry.note;
  localStorage.setItem(profileKey, JSON.stringify(profiles));
  return true;
}
// The current chart's note belongs to that birth: generating another chart starts with an empty note.
function currentNoteKey() {return 'current:' + JSON.stringify([birthOf(currentInput || {}), currentHourUnknown]);}
// One key per member, in the same order as groupMembers(), so notes follow the member rather than the position.
function groupMemberKeys() {
  const saved = loadProfiles();
  return [...(groupDraft.useCurrent && currentInput ? [currentNoteKey()] : []),
    ...groupDraft.profiles.filter(id => saved.some(x => x.id === id)).map(id => 'profile:' + id),
    ...groupDraft.extras.map(x => 'extra:' + x.id)];
}
function groupNote(key) {
  if (key.startsWith('current:')) return groupDraft.currentNote.key === key ? groupDraft.currentNote.text.trim() : '';
  if (key.startsWith('profile:')) {
    const id = key.slice(8);
    return (groupDraft.profileNotes[id] ?? profileNote(loadProfiles().find(x => x.id === id))).trim();
  }
  const extra = groupDraft.extras.find(x => 'extra:' + x.id === key);
  return extra ? (extra.note || '').trim() : '';
}
function noteInput(parent, value, label, onInput) {
  const input = append(parent, 'input', 'group-note user-text');
  input.type = 'text'; input.maxLength = NOTE_MAX; input.value = value;
  input.placeholder = '备注（选填）'; input.setAttribute('aria-label', label + '的备注');
  input.addEventListener('input', () => onInput(input.value));
  return input;
}
const GROUP_LINKS = [['all', '全部'], ['combine', '天干五合'], ['六合', '六合'], ['六冲', '六冲'], ['六害', '六害'], ['相刑', '相刑'], ['同支', '同支']];
const LINK_CLASS = {'六合': 'harmony', '六冲': 'clash', '六害': 'harm', '相刑': 'punish', '同支': 'same', combine: 'combine'};
const GENDER_TEXT = {male: '男', female: '女'};
const BIRTH_KEYS = ['birth_datetime', 'timezone', 'gender', 'late_zi_day_rollover', 'leap_month_second_half_as_next', 'time_mode', 'longitude'];
function birthOf(data) {
  const birth = {};
  BIRTH_KEYS.forEach(key => {if (data[key] !== undefined) birth[key] = data[key];});
  return birth;
}
function groupMembers() {
  const members = [], saved = loadProfiles();
  if (groupDraft.useCurrent && currentInput) members.push({label: groupDraft.currentLabel.trim() || '我', birth: birthOf(currentInput), hour_unknown: currentHourUnknown});
  groupDraft.profiles.forEach(id => {
    const entry = saved.find(x => x.id === id);
    if (entry) members.push({label: entry.label.trim().slice(0, 50) || '档案', birth: birthOf(entry.data), hour_unknown: entry.hour_unknown === true});
  });
  groupDraft.extras.forEach(x => members.push({label: x.label, hour_unknown: x.hour_unknown,
    birth: {birth_datetime: x.birth_datetime, timezone: x.timezone, ...(x.gender && x.gender !== 'unspecified' ? {gender: x.gender} : {})}}));
  // Labels must be distinct: a repeated one gets the first number that no other final label uses.
  const used = new Set();
  members.forEach(m => {
    let label = m.label;
    for (let n = 2; used.has(label); n++) {const suffix = ' (' + n + ')'; label = m.label.slice(0, 50 - suffix.length) + suffix;}
    used.add(label); m.label = label;
  });
  return members;
}
function pairOf(g, i, j) {return g.pairs.find(p => (p.a === i && p.b === j) || (p.a === j && p.b === i));}
function pairHas(p, type) {
  if (type === 'all') return p.branch_links.length > 0 || !!p.day_stems.combination;
  if (type === 'combine') return !!p.day_stems.combination;
  return p.label_counts[type] > 0;
}
function pairCount(p, type) {
  // Every label counts: one branch link can carry two (寅/巳 is both 六害 and 相刑).
  if (type === 'all') return Object.values(p.label_counts).reduce((a, b) => a + b, 0) + (p.day_stems.combination ? 1 : 0);
  if (type === 'combine') return p.day_stems.combination ? 1 : 0;
  return p.label_counts[type];
}
// Plain-text copies of the relation pages, laid out for chats and notes. Names the user typed are wrapped in
// private-use marks while the text is built, so the 繁體 conversion skips them and the padding measures them.
const NAME_OPEN = '', NAME_CLOSE = '';
const asName = label => NAME_OPEN + label + NAME_CLOSE;
const textWidth = text => [...text.replace(/[]/g, '')].reduce((n, ch) => n + (ch.codePointAt(0) > 0xFF ? 2 : 1), 0);
// Columns padded with full-width spaces (two half-width units each), which keeps CJK columns aligned.
function textColumns(rows) {
  const widths = rows[0].map((_, i) => Math.max(...rows.map(row => textWidth(row[i]))) + 2);
  return rows.map(row => row.map((cell, i) => {
    if (i === row.length - 1) return cell;
    const gap = widths[i] - textWidth(cell);
    return cell + '　'.repeat(Math.floor(gap / 2)) + (gap % 2 ? ' ' : '');
  }).join('').trimEnd());
}
function finishText(lines) {
  const traditional = typeof uiLang !== 'undefined' && uiLang === 'zh-TW' && typeof toTraditional === 'function';
  return lines.join('\n').split(/([^]*)/)
    .map(part => part.startsWith(NAME_OPEN) ? part.slice(1, -1) : traditional ? toTraditional(part) : part).join('');
}
const TEXT_FOOTER = ['传统文化符号，未经科学预测效力验证，不作医疗、投资、法律等决策依据。', 'XuanShu · 开源 · 确定性计算，可复现'];
function downloadBlob(blob, name) {
  const url = URL.createObjectURL(blob); const a = elt('a'); a.href = url; a.download = name;
  document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 2000);
}
// Copy a preview's text. Without clipboard access the preview opens with its text selected for a keyboard copy.
async function copyPre(pre, button, done) {
  try {await navigator.clipboard.writeText(pre.textContent); button.textContent = done;}
  catch (_) {
    const fold = pre.closest('details'); if (fold) fold.open = true;
    const range = document.createRange(); range.selectNodeContents(pre);
    const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range);
    button.textContent = '已选中文字，请按 Ctrl+C 复制';
  }
}
// Copy and download buttons with a folded preview. The text is rebuilt on every click and when the
// interface language changes, so it always matches what the page shows.
function textExport(parent, id, makeText, fileName) {
  const box = append(parent, 'div', 'text-export'); box.id = id;
  const actions = append(box, 'div', 'text-export-actions');
  const copy = append(actions, 'button', 'tiny-button', '复制成文字'); copy.type = 'button'; copy.id = id + '-copy';
  const save = append(actions, 'button', 'tiny-button', '下载 TXT'); save.type = 'button'; save.id = id + '-download';
  append(actions, 'small', 'muted', '通行的中文命盘写法，不含出生日期、时间和备注');
  const fold = append(box, 'details', 'text-export-preview');
  append(fold, 'summary', null, '预览文字').id = id + '-summary';
  // Named by the (translated) summary: the translator leaves pre elements and their attributes alone.
  const pre = append(fold, 'pre', 'share-text'); pre.id = id + '-text'; pre.tabIndex = 0; pre.setAttribute('aria-labelledby', id + '-summary');
  box.xsFill = () => {pre.textContent = makeText(); copy.textContent = '复制成文字';};
  box.xsFill();
  copy.addEventListener('click', () => {box.xsFill(); copyPre(pre, copy, '已复制');});
  save.addEventListener('click', () => {box.xsFill(); downloadBlob(new Blob([pre.textContent + '\n'], {type: 'text/plain;charset=utf-8'}), fileName);});
  return box;
}
document.addEventListener('xuanshu-language', () => document.querySelectorAll('.text-export').forEach(box => box.xsFill && box.xsFill()));
// A labelled branch link across two charts: 年申—年巳 六合、相刑 (the first person's pillar first).
const linkText = link => nameMap[link.a_pillar].charAt(0) + link.a_branch + '—' + nameMap[link.b_pillar].charAt(0) + link.b_branch + ' ' + link.labels.join('、');
const UNKNOWN_PILLAR_NOTE = '？：这一柱不参与比较（时辰不详；年、月、日柱则是时辰不详且出生当天交节或换日）。';
function pillarRows(people) {
  return textColumns([['', ...PILLAR_KEYS.map(k => nameMap[k]), '日主', '生肖'],
    ...people.map(([name, p]) => [name, ...PILLAR_KEYS.map(k => p.pillars[k] || '？'),
      p.day_master ? p.day_master + p.day_master_element : '？', p.zodiac || '？'])]);
}
function groupText(g) {
  const gap = '　', lines = ['玄枢 · 多人关系对照', '', '【四柱】'];
  lines.push(...pillarRows(g.members.map(m => [asName(m.label), m])));
  if (g.members.some(m => PILLAR_KEYS.some(k => !m.pillars[k]))) lines.push(UNKNOWN_PILLAR_NOTE);
  lines.push('', '【日干十神】从每一行的人看各列的人');
  lines.push(...textColumns([['', ...g.members.map(m => asName(m.label))], ...g.members.map((m, i) => [asName(m.label),
    ...g.members.map((_, j) => {
      if (i === j) return '—';
      const p = pairOf(g, i, j);
      return (p.a === i ? p.day_stems.a_sees_b : p.day_stems.b_sees_a) || '？';
    })])]));
  lines.push('', '【两两关系】');
  g.pairs.forEach(p => {
    const a = asName(p.a_label), b = asName(p.b_label);
    const stems = [a + ' → ' + b + ' ' + (p.day_stems.a_sees_b || '？'), b + ' → ' + a + ' ' + (p.day_stems.b_sees_a || '？')];
    if (p.day_stems.combination) stems.push(p.day_stems.combination);
    lines.push(a + ' ↔ ' + b, gap + '日干：' + stems.join('，'),
      gap + '生肖：' + (p.zodiac.a || '？') + ' / ' + (p.zodiac.b || '？') + (p.zodiac.labels.length ? ' ' + p.zodiac.labels.join('、') : ''),
      gap + '地支' + '（' + a + '—' + b + '）：' + (p.branch_links.map(linkText).join('；') || '无标记'));
  });
  lines.push('', '【三合】');
  if (!g.triads.length) lines.push('没有成员的年支或日支凑齐申子辰、亥卯未、寅午戌、巳酉丑。');
  g.triads.forEach(x => lines.push(x.pillar_label + '：' + x.triad + ' ' + x.element + gap + x.members.map(m => asName(m.label) + '（' + m.branch + '）').join('、')));
  const totals = g.element_overview.surface_totals, masters = g.element_overview.day_masters;
  lines.push('', '【五行】', '表面合计：' + PHASES.split('').map(e => e + ' ' + totals[e]).join(gap) + '（四柱天干地支，不含藏干）',
    '日主：' + PHASES.split('').filter(e => masters[e].length).map(e => e + ' ' + masters[e].map(asName).join('、')).join('；'));
  if (g.year_view) lines.push('', ...groupYearText(g.year_view, 'group'));
  lines.push('', ...g.notes, ...TEXT_FOOTER);
  return finishText(lines);
}
// The luck and year-pillar section of the text copy.
function luckText(l) {
  if (l.status === 'not_started') return '未起运，' + (l.start_year || (l.start_years || []).join(' 或 ')) + ' 年起运';
  if (l.status === 'beyond') return '超出所排的十二步大运';
  const starts = l.start_year ? [l.start_year] : l.start_years || [];
  return l.pillar + (l.ten_god ? ' ' + l.ten_god : '') + (starts.length ? '，' + starts.join(' 或 ') + ' 年交运' : '');
}
function groupYearText(v, prefix) {
  const gap = '　', lines = ['【' + v.year + ' ' + v.year_pillar + '年 · 大运流年】十神以各人日主看天干'];
  v.members.forEach(m => {
    const who = asName(m.label) + '（' + (GENDER_TEXT[m.gender] || '性别未填') + (m.status === 'born' ? '，' + m.age + ' 岁' : '') + '）';
    if (m.status === 'not_born') {lines.push(who + gap + '这一年尚未出生'); return;}
    const l = m.luck;
    const luck = l.status === 'needs_gender' ? '未填性别，不排大运' : l.status === 'uncertain_pillars' ? '月柱不定，大运无法确定'
      : l.status === 'depends_on_hour' ? l.options.map(luckText).join(' 或 ') + '（随时辰而定）' : luckText(l);
    const n = m.year_reading;
    const reading = n ? n.ten_god_of_stem + (yearReadingParts(n).length ? '：' + yearReadingParts(n).join('；') : '')
      + ((n.shensha || []).length ? '；神煞 ' + n.shensha.map(x => x.name).join('、') : '') : '原局有不定的柱，不比较';
    lines.push(who, gap + '大运：' + luck, gap + '流年：' + reading);
  });
  const marked = v.luck_pairs.filter(p => p.branch_labels.length || p.stem_combination);
  lines.push('大运之间：' + (marked.map(p => asName(p.a_label) + ' ' + p.a_pillar + ' ↔ ' + asName(p.b_label) + ' ' + p.b_pillar + ' '
    + [p.stem_combination, ...p.branch_labels].filter(Boolean).join('、')).join('；') || '无标记'));
  // The same fifteen years as the timeline on the page.
  const start = luckWindowFor(prefix, v.year), end = start + LUCK_SPAN - 1;
  if ((v.luck_timeline || []).length) lines.push('大运时间轴（' + start + '–' + end + '）：');
  (v.luck_timeline || []).forEach(row => lines.push(gap + asName(row.label) + '：' + luckSpanText(row, start, end)));
  return lines;
}
// One member's luck periods that touch the years start..end, for the text export.
function luckSpanText(row, start, end) {
  if (row.status === 'needs_gender') return '未填性别，不排大运';
  if (row.status !== 'ok') return '月柱不定，大运无法确定';
  if (row.born_year > end) return '尚未出生';
  const from = Math.max(start, row.born_year), parts = [], last = row.periods[row.periods.length - 1];
  if (row.periods.length && from < row.periods[0].start_years[0]) parts.push('未起运');
  const shown = row.periods.filter(p => p.end_years[p.end_years.length - 1] >= from && p.start_years[0] <= end);
  shown.forEach(p => parts.push(p.pillar + (p.ten_god ? ' ' + p.ten_god : '') + ' ' + p.start_years.join('/') + '–' + p.end_years.join('/')));
  // The years after the twelfth period are not left unmarked.
  if (last && end > last.end_years[last.end_years.length - 1]) parts.push('已排完');
  return parts.join(' → ') + (shown.some(p => p.start_years.length > 1 || p.end_years.length > 1) ? '（时辰不详，交运年有两种可能）' : '');
}
function renderGroup() {
  title(result, '多人关系', '家人、团队或朋友的四柱并排 · 只标传统标签，不打分');
  append(result, 'p', 'info-inline', '从当前命盘、本机档案和在这里临时添加的成员中选 2 到 8 人。临时成员只留在本页，刷新后消失；服务器不保存。');
  const picker = append(result, 'div', 'group-picker');
  const current = append(picker, 'div', 'group-option');
  const currentBox = append(append(current, 'label', 'check-line'), 'input'); currentBox.type = 'checkbox'; currentBox.id = 'group-current';
  currentBox.checked = groupDraft.useCurrent && !!currentInput; currentBox.disabled = !currentInput;
  currentBox.parentNode.append(currentInput ? '当前命盘' : '当前命盘（先生成命盘）');
  const currentLabel = append(current, 'input', 'group-label user-text'); currentLabel.id = 'group-current-label'; currentLabel.hidden = !currentInput;
  currentLabel.maxLength = 50; currentLabel.value = groupDraft.currentLabel; currentLabel.setAttribute('aria-label', '当前命盘的称呼');
  currentBox.addEventListener('change', () => {groupDraft.useCurrent = currentBox.checked; render();});
  currentLabel.addEventListener('input', () => {groupDraft.currentLabel = currentLabel.value;});
  if (currentBox.checked) noteInput(current, groupDraft.currentNote.key === currentNoteKey() ? groupDraft.currentNote.text : '', '当前命盘',
    value => {groupDraft.currentNote = {key: currentNoteKey(), text: value};}).id = 'group-current-note';
  const saved = loadProfiles();
  groupDraft.profiles = groupDraft.profiles.filter(id => saved.some(x => x.id === id));
  if (saved.length) {
    append(picker, 'h4', 'subheading', '本机档案');
    const list = append(picker, 'div', 'group-profiles');
    saved.forEach(entry => {
      const item = append(list, 'div', 'group-profile-item');
      const row = append(item, 'label', 'check-line group-profile');
      const box = append(row, 'input'); box.type = 'checkbox'; box.value = entry.id; box.id = 'group-profile-' + entry.id;
      box.checked = groupDraft.profiles.includes(entry.id);
      append(row, 'span', 'user-text', entry.label);
      append(row, 'small', 'muted', String(entry.data.birth_datetime || '').replace('T', ' '));
      box.addEventListener('change', () => {
        groupDraft.profiles = box.checked ? [...groupDraft.profiles, entry.id] : groupDraft.profiles.filter(id => id !== entry.id);
        render();
      });
      const savedNote = profileNote(entry);
      if (!box.checked && !savedNote) return;
      item.classList.add('has-note');
      const editor = append(item, 'div', 'group-note-row');
      const input = noteInput(editor, groupDraft.profileNotes[entry.id] ?? savedNote, entry.label, value => {groupDraft.profileNotes[entry.id] = value;});
      input.id = 'group-note-' + entry.id;
      const save = append(editor, 'button', 'tiny-button', '保存到档案'); save.type = 'button'; save.id = 'group-note-save-' + entry.id;
      const message = append(editor, 'small', 'muted');
      message.setAttribute('role', 'status');
      save.addEventListener('click', () => {
        try {
          saveProfileNote(entry.id, input.value); delete groupDraft.profileNotes[entry.id];
          message.textContent = input.value.trim() ? '备注已保存在本机浏览器' : '备注已从档案删除';
        } catch (_) {message.textContent = '保存失败：浏览器存储不可用';}
      });
      if (savedNote) {
        const clearButton = append(editor, 'button', 'tiny-button', '删除备注'); clearButton.type = 'button'; clearButton.id = 'group-note-clear-' + entry.id;
        clearButton.addEventListener('click', () => {
          try {saveProfileNote(entry.id, ''); delete groupDraft.profileNotes[entry.id]; render();}
          catch (_) {message.textContent = '删除失败：浏览器存储不可用';}
        });
      }
    });
    append(picker, 'p', 'field-help', '备注只用于这一页和带进 AI 对话的草稿，不发给服务器；档案成员的备注点「保存到档案」后才存进本机浏览器，随档案一起删除和加密备份。');
  } else {
    append(picker, 'p', 'field-help', '还没有本机档案。在出生资料下方保存档案后，可以在这里勾选。');
  }
  append(picker, 'h4', 'subheading', '临时添加');
  groupDraft.extras.forEach((x, index) => {
    const row = append(picker, 'div', 'group-extra');
    append(row, 'span', 'user-text', x.label);
    append(row, 'small', 'muted', x.birth_datetime.replace('T', ' ') + ' · ' + x.timezone);
    if (GENDER_TEXT[x.gender]) append(row, 'small', 'muted', GENDER_TEXT[x.gender]);
    if (x.hour_unknown) append(row, 'small', 'muted', '时辰不详');
    noteInput(row, x.note || '', x.label, value => {x.note = value;}).id = 'group-extra-note-' + index;
    const remove = append(row, 'button', 'tiny-button', '移除'); remove.type = 'button';
    remove.addEventListener('click', () => {groupDraft.extras.splice(index, 1); render();});
  });
  const add = append(picker, 'div', 'inline-control group-add');
  const draft = groupDraft.extra;
  const nameInput = createInput('称呼', 'text', draft.label, add); nameInput.id = 'group-extra-label'; nameInput.maxLength = 50;
  nameInput.className = 'user-text'; nameInput.placeholder = '例如：妈妈';
  const when = createInput('公历出生日期与时间', 'datetime-local', draft.birth_datetime, add);
  when.id = 'group-extra-datetime'; when.min = '1901-01-01T00:00'; when.max = '2099-12-31T23:59';
  const zoneLabel = append(add, 'label', null, '时区');
  const zone = append(zoneLabel, 'select'); zone.id = 'group-extra-timezone';
  [...$('#timezone').options].forEach(opt => {const option = append(zone, 'option', null, opt.textContent); option.value = opt.value;});
  zone.value = draft.timezone;
  const genderLabel = append(add, 'label', null, '性别（排大运用）');
  const gender = append(genderLabel, 'select'); gender.id = 'group-extra-gender';
  [['unspecified', '未填'], ['male', '男'], ['female', '女']].forEach(([value, text]) => {append(gender, 'option', null, text).value = value;});
  gender.value = draft.gender;
  const unknownRow = append(add, 'label', 'check-line');
  const unknown = append(unknownRow, 'input'); unknown.type = 'checkbox'; unknown.id = 'group-extra-unknown'; unknown.checked = draft.hour_unknown;
  unknownRow.append('不知道出生时辰');
  const addButton = append(add, 'button', 'tiny-button', '添加成员'); addButton.type = 'button'; addButton.id = 'group-extra-add';
  const addError = append(picker, 'p', 'inline-msg');
  nameInput.addEventListener('input', () => {draft.label = nameInput.value;});
  when.addEventListener('input', () => {draft.birth_datetime = when.value;});
  zone.addEventListener('change', () => {draft.timezone = zone.value;});
  gender.addEventListener('change', () => {draft.gender = gender.value;});
  unknown.addEventListener('change', () => {draft.hour_unknown = unknown.checked;});
  addButton.addEventListener('click', () => {
    const label = nameInput.value.trim();
    if (!label) {addError.textContent = '先填写称呼'; return;}
    if (!when.value) {addError.textContent = '请填写出生时间'; return;}
    if (groupMembers().length >= 8) {addError.textContent = '最多 8 人'; return;}
    groupDraft.extras.push({id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6), label,
      birth_datetime: when.value, timezone: zone.value, gender: gender.value, hour_unknown: unknown.checked, note: ''});
    groupDraft.extra = {...draft, label: ''};
    render();
  });
  const members = groupMembers();
  const runRow = append(result, 'div', 'inline-control group-run');
  const count = append(runRow, 'span', 'group-count');
  texts(count, '已选 ', members.length + ' / 8', ' 人');
  const run = append(runRow, 'button', null, '对照关系'); run.type = 'button'; run.id = 'group-run';
  run.disabled = members.length < 2 || members.length > 8;
  const error = append(result, 'p', 'inline-msg');
  if (members.length > 8) error.textContent = '最多 8 人，请取消一些勾选';
  else if (groupRunError) error.textContent = groupRunError;
  run.addEventListener('click', async () => {
    // Read the selection again: a label typed since the last render is not in `members` yet.
    // The note keys are taken with it, so a change made while the request runs cannot shift the notes.
    const chosen = groupMembers(), keys = groupMemberKeys();
    if (chosen.length < 2 || chosen.length > 8) {error.textContent = '请选 2 到 8 人'; return;}
    run.disabled = true; error.textContent = ''; groupRunError = '';
    groupDraft.year = takeTypedYear('group') ?? groupDraft.year;
    const ticket = ++groupYearTicket;
    groupRun = {chosen, keys};
    try {
      const reply = await postJSON('/api/group-relations', {members: chosen, year: groupDraft.year});
      if (ticket !== groupYearTicket) return;
      groupResult = reply; groupKey = JSON.stringify(chosen); groupResultKeys = keys; groupDraft.focus = null;
      groupRun = null; groupYearPending = false; groupYearError = '';
    } catch (err) {
      if (ticket !== groupYearTicket) return;
      groupRun = null; groupYearPending = false; groupRunError = '对照失败：' + err.message;
    }
    if (active === 'group') render();
  });
  if (!groupResult) return;
  if (groupKey !== JSON.stringify(members)) append(result, 'p', 'feature-note', '成员已改变，下面仍是上一次的结果；点「对照关系」更新。');
  renderGroupResult(groupResult);
}
// One person as a line of a chat draft. It carries the person's own rule choices, so the model's tool call
// reproduces the result shown; birth data goes to the model only when the user sends the message.
function chatBirthLine(label, birth, hourUnknown, note) {
  const tr = text => typeof translateText === 'function' ? translateText(text) : text;
  const rules = [];
  if (birth.late_zi_day_rollover) rules.push(tr('23:00 换日'));
  if (birth.leap_month_second_half_as_next === false) rules.push(tr('闰月整月按本月'));
  if (birth.time_mode === 'mean_solar') rules.push(tr('平太阳时') + ' ' + tr('经度') + ' ' + birth.longitude);
  if (birth.time_mode === 'apparent_solar') rules.push(tr('真太阳时') + ' ' + tr('经度') + ' ' + birth.longitude);
  const gender = GENDER_TEXT[birth.gender];
  return ['- ' + label, birth.birth_datetime.slice(0, 10) + ' ' + (hourUnknown ? tr('时辰不详') : birth.birth_datetime.slice(11, 16)),
    birth.timezone, ...(gender ? [tr(gender)] : []), ...rules, ...(note ? [tr('备注：') + note] : [])].join(' · ');
}
// The members of a group result as a chat question.
function groupChatDraft(g, inputs) {
  const tr = text => typeof translateText === 'function' ? translateText(text) : text;
  const lines = g.members.map((m, i) => {
    const birth = (inputs[i] || {}).birth || {};
    // The note is the user's own words about this member, shown in the draft before anything is sent.
    const note = groupNote(groupResultKeys[i] || '').replace(/\s+/g, ' ');
    return chatBirthLine(m.label, {...birth, birth_datetime: m.birth_datetime, timezone: m.timezone}, m.hour_unknown, note);
  });
  const ask = [tr('请结合多人关系对照，帮我看看下面几位之间的关系，只解释传统标签的含义，不要打分。')];
  if (g.year_view) ask.push(tr('也请对照这一年的大运流年：') + g.year_view.year);
  // The current chart is the one the chat already uses; everyone else is another person.
  const others = g.members.filter((m, i) => !(groupResultKeys[i] || '').startsWith('current:')).map(m => m.birth_datetime.slice(0, 10));
  return {text: [...ask, ...lines].join('\n'), others};
}
// Puts a draft into the chat input and opens the chat. Anything the user had typed stays; clicking again does not
// add the same people twice, and the page's earlier block, while still in the input as it was put there, is replaced
// (another year, edited notes or corrected birth data). others are the birth dates of the people other than the user:
// a message with any of them waits for the consent tick, however the lines around them were edited.
function sendDraftToChat(draft, others, block) {
  chatThirdPartyBirths = [...new Set([...chatThirdPartyBirths, ...others])];
  if (block && chatDraft.includes(block)) chatDraft = chatDraft.replace(block, () => draft);
  else if (!chatDraft.includes(draft)) chatDraft = chatDraft.trim() ? chatDraft.trimEnd() + '\n\n' + draft : draft;
  activateTab(tabs.find(t => t.dataset.tab === 'chat'));
  const box = $('#chat-input'); if (box) {box.focus(); box.setSelectionRange(box.value.length, box.value.length);}
  return draft;
}
// A year typed but not entered when 带进 AI 对话 is clicked: that year is loaded first and the draft follows it.
let askAfterYear = null;
function askWithTypedYear(prefix, shown, change) {
  const typed = takeTypedYear(prefix);
  if (typed === null || typed === shown) return false;
  askAfterYear = prefix; change(typed);
  return true;
}
function askAfterYearLoaded(prefix, ok) {
  if (askAfterYear !== prefix) return;
  askAfterYear = null;
  if (ok && active === prefix) {const button = $('#' + prefix + '-ask-ai'); if (button && !button.disabled) button.click();}
}
// The 带进 AI 对话 button with its hint; it is off until the chat service is configured, and while another year or
// a new comparison is loading (the draft would carry the year still shown).
function chatAskButton(id, page, readyText, offText, busy) {
  const ask = append(result, 'div', 'group-ask');
  const button = append(ask, 'button', 'tiny-button', '带进 AI 对话'); button.type = 'button'; button.id = id;
  // The chat status is normally read by the chat tab; a page opened straight here asks for it.
  if (chatStatus === null) {chatStatus = {pending: true}; fetchChatStatus().then(() => {if (active === page) render();});}
  const ready = Boolean(chatStatus && chatStatus.enabled === true);
  button.disabled = !ready || busy;
  append(ask, 'small', 'muted', chatStatus.pending ? '正在检查对话服务…' : ready ? readyText : offText);
  return button;
}
function renderGroupResult(g) {
  const askButton = chatAskButton('group-ask-ai', 'group', '把成员的出生资料放进对话输入框，你确认后再发送；发送前需在对话设置里勾选已获对方同意。',
    'AI 对话尚未启用，配置语言模型后可以把这些成员带进对话。', groupYearPending || Boolean(groupRun));
  askButton.addEventListener('click', () => {
    if (askWithTypedYear('group', g.year_view && g.year_view.year, groupYear)) return;
    const {text: draft, others} = groupChatDraft(g, JSON.parse(groupKey || '[]'));
    groupChatBlock = sendDraftToChat(draft, others, groupChatBlock);
  });
  textExport(result, 'group-text', () => groupText(g), 'xuanshu-group.txt');
  const cards = append(result, 'div', 'group-members');
  g.members.forEach((m, i) => {
    const card = append(cards, 'article', 'group-member');
    if (groupDraft.focus === i) card.classList.add('is-focus');
    const head = append(card, 'div', 'group-member-head');
    append(head, 'span', 'group-dot ' + (m.day_master ? 'bg-' + ELEMENT_CLASS[m.day_master_element] : 'dot-unknown'));
    append(head, 'strong', 'user-text', m.label);
    const note = groupNote(groupResultKeys[i] || '');
    if (note) append(card, 'p', 'group-note-text user-text', note);
    const sub = append(card, 'small', 'muted');
    texts(sub, m.pillars.year ? ANIMAL_YEARS[BRANCH_ORDER.indexOf(m.pillars.year[1])] : '生肖不定', ' · ', '日主', ' ' + (m.day_master ? m.day_master + m.day_master_element : '?'));
    if (m.uncertain_pillars.length) append(card, 'small', 'group-uncertain', '时辰不详且当天交节或换日：带 ? 的柱不参与比较');
    const pillars = append(card, 'div', 'group-pillars');
    ['year', 'month', 'day', 'hour'].forEach(key => {
      const cell = append(pillars, 'span', 'group-pillar');
      append(cell, 'small', null, nameMap[key]);
      const text = m.pillars[key];
      if (text) {append(cell, 'b', stemClass(text[0]), text[0]); append(cell, 'b', branchClass(text[1]), text[1]);}
      else append(cell, 'b', 'muted', '?');
    });
  });

  append(result, 'h4', 'subheading', '关系图');
  const filters = append(result, 'div', 'group-filters');
  filters.setAttribute('role', 'group'); filters.setAttribute('aria-label', '按标签筛选关系线');
  GROUP_LINKS.forEach(([key, label], k) => {
    const chip = append(filters, 'button', 'filter-chip' + (key === 'all' ? '' : ' link-' + LINK_CLASS[key]), label);
    chip.type = 'button'; chip.dataset.filter = key; chip.id = 'group-filter-' + k; chip.setAttribute('aria-pressed', String(groupDraft.filter === key));
    chip.addEventListener('click', () => {groupDraft.filter = key; render();});
  });
  groupGraph(result, g);
  append(result, 'p', 'field-help', '线上的数字是该标签（或全部标签）的条数；点成员只看与他相关的线，点线打开这一对的明细。');

  append(result, 'h4', 'subheading', '日干十神（行看列）');
  const wrap = append(result, 'div', 'table-wrap');
  const table = append(wrap, 'table', 'data-table group-matrix'); table.id = 'group-matrix';
  const hr = append(append(table, 'thead'), 'tr');
  append(hr, 'th', null, '从此人看 → 对方');
  g.members.forEach(m => append(hr, 'th', 'user-text', m.label));
  const body = append(table, 'tbody');
  g.members.forEach((m, i) => {
    const tr = append(body, 'tr');
    if (groupDraft.focus === i) tr.classList.add('is-focus');
    append(tr, 'th', 'user-text', m.label);
    g.members.forEach((_, j) => {
      const td = append(tr, 'td');
      if (i === j) {append(td, 'span', 'muted', '—'); return;}
      const p = pairOf(g, i, j);
      append(td, 'span', p.day_stems.a_sees_b ? null : 'muted', (p.a === i ? p.day_stems.a_sees_b : p.day_stems.b_sees_a) || '?');
      if (p.day_stems.combination) append(td, 'small', 'relation-chip rel-harmony', p.day_stems.combination);
    });
  });

  append(result, 'h4', 'subheading', '两两明细');
  const list = append(result, 'div', 'group-pairs');
  g.pairs.forEach(p => {
    const item = append(list, 'details', 'group-pair'); item.id = `group-pair-${p.a}-${p.b}`;
    const summary = append(item, 'summary');
    append(summary, 'strong', 'user-text', p.a_label);
    summary.append(' ↔ ');
    append(summary, 'strong', 'user-text', p.b_label);
    const tags = append(summary, 'span', 'group-tags');
    if (p.day_stems.combination) append(tags, 'span', 'relation-chip link-combine', p.day_stems.combination);
    Object.entries(p.label_counts).forEach(([type, n]) => {
      if (n) texts(append(tags, 'span', 'relation-chip link-' + LINK_CLASS[type]), type, ' ', String(n));
    });
    if (!p.branch_links.length && !p.day_stems.combination) append(tags, 'span', 'muted', '无标记');
    const facts = append(item, 'div', 'meta-tags');
    const stems = append(facts, 'span');
    append(stems, 'span', 'user-text', p.a_label); stems.append(' → ');
    append(stems, 'span', 'user-text', p.b_label); texts(stems, '：', p.day_stems.a_sees_b || '?');
    const back = append(facts, 'span');
    append(back, 'span', 'user-text', p.b_label); back.append(' → ');
    append(back, 'span', 'user-text', p.a_label); texts(back, '：', p.day_stems.b_sees_a || '?');
    const zodiac = append(facts, 'span');
    texts(zodiac, '生肖', ' ' + (p.zodiac.a || '?') + ' / ' + (p.zodiac.b || '?'));
    p.zodiac.labels.forEach(x => zodiac.append(' · ', x));
    branchLinkTable(item, p.a_label, p.b_label, p.branch_links);
  });

  append(result, 'h4', 'subheading', '三合');
  if (!g.triads.length) append(result, 'p', 'field-help', '没有成员的年支或日支凑齐申子辰、亥卯未、寅午戌、巳酉丑。');
  g.triads.forEach(x => {
    const row = append(result, 'div', 'feature-note group-triad');
    texts(row, x.pillar_label, '：', x.triad, ' · ', x.element, ' · ');
    x.members.forEach((m, k) => {
      if (k) row.append('、');
      append(row, 'span', 'user-text', m.label);
      row.append('（' + m.branch + '）');
    });
  });

  append(result, 'h4', 'subheading', '五行分布');
  const totals = g.element_overview.surface_totals, max = Math.max(1, ...Object.values(totals));
  const grid = append(result, 'div', 'group-elements');
  PHASES.split('').forEach(element => {
    const row = append(grid, 'div', 'group-element');
    append(row, 'b', elementClass(element), element);
    const bar = append(row, 'span', 'group-bar');
    const fill = append(bar, 'span', 'bg-' + ELEMENT_CLASS[element]); fill.style.width = (totals[element] / max * 100) + '%';
    append(row, 'span', 'group-total', String(totals[element]));
    const who = append(row, 'span', 'group-who');
    const masters = g.element_overview.day_masters[element];
    if (!masters.length) append(who, 'span', 'muted', '—');
    masters.forEach((label, k) => {if (k) who.append('、'); append(who, 'span', 'user-text', label);});
  });
  append(result, 'p', 'field-help', '条形是全体成员四柱天干地支的表面五行合计（不含藏干）；右侧是日主属该五行的成员。');
  groupYearSection(g);
  g.notes.forEach(x => note(result, x));
}
// Another year for the same members: the members of the result shown, not the selection being edited, or
// those of a 对照关系 run still waiting for its reply (this request replaces that run's).
async function groupYear(year) {
  const show = () => {if (active === 'group') render();};
  const pendingRun = groupRun;
  if (!groupKey && !pendingRun) return;
  luckYearTyped.group = null;
  if (!pendingRun && groupResult && groupResult.year_view && groupResult.year_view.year === year && !groupYearPending) {
    if (groupYearError) {groupYearError = ''; show();}
    return;
  }
  if (!(Number.isInteger(year) && year >= 1901 && year <= 2099)) {groupYearError = '年份要在 1901 到 2099 之间'; show(); return;}
  const ticket = ++groupYearTicket;
  groupDraft.year = year; groupYearPending = true; groupYearError = ''; show();
  try {
    const reply = await postJSON('/api/group-relations', {members: pendingRun ? pendingRun.chosen : JSON.parse(groupKey), year});
    if (ticket !== groupYearTicket) return;
    groupResult = reply;
    if (pendingRun) {groupKey = JSON.stringify(pendingRun.chosen); groupResultKeys = pendingRun.keys; groupDraft.focus = null;}
  } catch (err) {
    if (ticket !== groupYearTicket) return;
    groupYearError = '换年失败：' + err.message;
    // The next 对照关系 asks for the year still shown, not the one that failed.
    if (groupResult && groupResult.year_view) groupDraft.year = groupResult.year_view.year;
  }
  groupRun = null; groupYearPending = false;
  if (active === 'group') render();
  askAfterYearLoaded('group', !groupYearError);
}
// The year pillar against one member's chart in chart notation, for the text copy: 年午 同支、相刑, 年丙 相冲,
// 补成寅午戌三合局, 落日空.
const yearReadingParts = n => [...n.branch_relations.map(r => nameMap[r.pillar].charAt(0) + r.branch + ' ' + r.labels.join('、')),
  ...n.stem_relations.map(r => nameMap[r.pillar].charAt(0) + r.stem + ' ' + r.labels.join('、')),
  ...n.branch_groups.map(x => '补成' + x.branches + (x.kind === '三合' ? '三合局' : '三会方')),
  ...n.void_of.map(v => v === 'day' ? '落日空' : '落年空')];
// One luck case in a card row: the pillar, its ten god and the year it begins in.
function luckLine(parent, l, prefix) {
  const row = append(parent, 'div', 'group-year-row');
  append(row, 'span', 'pillar-stage-label', prefix);
  if (l.status === 'not_started') {
    const begins = l.start_year ? [l.start_year] : l.start_years || [];
    const line = append(row, 'span', 'muted');
    texts(line, '未起运', ' · ', '起运年', ' ' + begins.join(' / '));
    if (begins.length > 1) texts(line, ' ', '（随时辰而定）');
    return row;
  }
  if (l.status === 'beyond') {append(row, 'span', 'muted', '超出所排的十二步大运'); return row;}
  const pillar = append(row, 'span', 'group-year-pillar');
  append(pillar, 'b', stemClass(l.pillar[0]), l.pillar[0]); append(pillar, 'b', branchClass(l.pillar[1]), l.pillar[1]);
  if (l.ten_god) append(row, 'span', 'group-year-god', l.ten_god);
  const when = append(row, 'small', 'muted');
  const starts = l.start_year ? [l.start_year] : l.start_years || [];
  if (starts.length) texts(when, '交运年', ' ' + starts.join(' / '));
  if (starts.length > 1) texts(when, ' ', '（随时辰而定）');
  if (l.changes_this_year) append(row, 'span', 'luck-change', '当年交运');
  return row;
}
function groupYearSection(g) {
  const v = g.year_view;
  luckYearSection(v, {prefix: 'group', year: groupYearPending || groupRun || !v ? groupDraft.year : v.year, pending: groupYearPending, error: groupYearError,
    people: g.members, change: groupYear, rerun: '点「对照关系」重新计算后可以看这一部分。'});
}
// The first year shown on each luck timeline, kept while the open year stays inside the fifteen years.
// luckTimelineYear is the open year the window was last placed for: moving the window by hand is kept until
// another year is opened.
const luckTimelineStart = {}, luckTimelineYear = {};
const LUCK_SPAN = 15, LUCK_LAST_START = 2099 - LUCK_SPAN + 1;
function luckWindow(year, start) {
  if (start === undefined || year < start || year >= start + LUCK_SPAN) start = year - 4;
  return Math.max(1901, Math.min(LUCK_LAST_START, start));
}
function luckWindowFor(prefix, year) {
  if (luckTimelineYear[prefix] !== year || luckTimelineStart[prefix] === undefined) {
    luckTimelineStart[prefix] = luckWindow(year, luckTimelineStart[prefix]); luckTimelineYear[prefix] = year;
  }
  return luckTimelineStart[prefix];
}
// What one member's luck is in a year: a period, a change that depends on the unknown hour, before the first
// period, or not yet born.
function luckAt(row, year) {
  if (year < row.born_year) return {kind: 'unborn'};
  const periods = row.periods;
  for (let k = 0; k < periods.length; k++) {
    const p = periods[k], starts = p.start_years;
    if (starts.length > 1 && year >= starts[0] && year < starts[starts.length - 1]) return {kind: 'maybe', before: periods[k - 1] || null, after: p};
    if (year >= starts[starts.length - 1] && year <= p.end_years[0]) return {kind: 'period', period: p, first: year === starts[starts.length - 1]};
  }
  if (periods.length && year < periods[0].start_years[0]) return {kind: 'not_started'};
  // With an unknown hour the twelfth period may end a year later: that year is still in it or past the list.
  const last = periods[periods.length - 1];
  if (last && year > last.end_years[0] && year <= last.end_years[last.end_years.length - 1]) return {kind: 'maybe', before: last, after: null};
  return {kind: 'beyond'};
}
// Each member's luck periods across fifteen years, so the changes line up at a glance; a year opens its cards.
function luckTimeline(box, v, prefix, change) {
  const rows = v.luck_timeline || [];
  if (!rows.length) return;
  append(box, 'h4', 'subheading', '大运时间轴');
  const wrap = append(box, 'div', 'luck-timeline-box'); wrap.id = prefix + '-timeline';
  const draw = () => {
    wrap.replaceChildren();
    const start = luckWindowFor(prefix, v.year);
    const years = Array.from({length: LUCK_SPAN}, (_, k) => start + k);
    const nav = append(wrap, 'div', 'inline-control luck-timeline-nav');
    const back = append(nav, 'button', 'tiny-button', '‹ 早五年'); back.type = 'button'; back.id = prefix + '-timeline-back';
    const forward = append(nav, 'button', 'tiny-button', '晚五年 ›'); forward.type = 'button'; forward.id = prefix + '-timeline-forward';
    texts(append(nav, 'span', 'muted luck-timeline-range'), years[0] + '–' + years[years.length - 1]);
    back.disabled = start <= 1901; forward.disabled = start >= LUCK_LAST_START;
    // Moving the window keeps the open year; it only shows other years, so nothing is requested. Focus stays on
    // the button pressed, or moves to the other one when the window reached the end of the range.
    const shift = step => {
      luckTimelineStart[prefix] = Math.max(1901, Math.min(LUCK_LAST_START, start + step)); draw();
      const [pressed, other] = (step < 0 ? ['-timeline-back', '-timeline-forward'] : ['-timeline-forward', '-timeline-back']).map(id => wrap.querySelector('#' + prefix + id));
      (pressed.disabled ? other : pressed).focus();
      const copy = document.getElementById(prefix + '-text');  // the text preview lists the same years
      if (copy && copy.xsFill) copy.xsFill();
    };
    back.addEventListener('click', () => shift(-5));
    forward.addEventListener('click', () => shift(5));
    const table = append(append(wrap, 'div', 'table-wrap luck-timeline-wrap'), 'table', 'luck-timeline');
    const head = append(append(table, 'thead'), 'tr');
    append(head, 'th', 'luck-timeline-who', '成员').scope = 'col';
    years.forEach(year => {
      const th = append(head, 'th', year === v.year ? 'tl-selected' : null); th.scope = 'col';
      const pick = append(th, 'button', 'tl-year', String(year)); pick.type = 'button'; pick.id = prefix + '-timeline-year-' + year;
      pick.setAttribute('aria-pressed', String(year === v.year));
      pick.addEventListener('click', () => change(year));
    });
    const body = append(table, 'tbody');
    rows.forEach(row => {
      const tr = append(body, 'tr');
      const who = append(tr, 'th', 'luck-timeline-who user-text', row.label); who.scope = 'row';
      if (row.status !== 'ok') {
        const td = append(tr, 'td', 'tl-cell tl-note', row.status === 'needs_gender' ? '未填性别，不排大运' : '时辰不详且当天交节，大运无法确定');
        td.colSpan = LUCK_SPAN; return;
      }
      // A label sits in the first cell of a run and may run on over the following cells of the same run, so long
      // translated ten-god names keep every year column the same width.
      const same = (a, b) => a.kind === b.kind && a.period === b.period;
      const label = (td, k, at) => {
        let run = 1;
        while (k + run < years.length && same(luckAt(row, years[k + run]), at)) run++;
        const box = append(td, 'span', 'tl-label'); box.style.width = `calc(${run * 100}% + ${run * 2 - 10}px)`;
        return box;
      };
      years.forEach((year, k) => {
        const at = luckAt(row, year), td = append(tr, 'td', 'tl-cell');
        if (year === v.year) td.classList.add('tl-selected');
        td.addEventListener('click', () => change(year));
        if (at.kind === 'unborn') {td.classList.add('tl-empty'); td.title = '尚未出生'; return;}
        if (at.kind === 'not_started' || at.kind === 'beyond') {
          td.classList.add('tl-empty');
          td.title = at.kind === 'not_started' ? '未起运' : '已排完';
          if (k === 0 || luckAt(row, year - 1).kind !== at.kind) append(label(td, k, at), 'small', 'tl-god', at.kind === 'not_started' ? '未起运' : '已排完');
          return;
        }
        if (at.kind === 'maybe') {
          td.classList.add('tl-maybe'); append(td, 'small', null, '?');
          td.title = (at.before ? at.before.pillar : '未起运') + ' / ' + (at.after ? at.after.pillar : '已排完') + ' · 时辰不详，交运年随时辰而定';
          return;
        }
        const p = at.period;
        td.classList.add('tl-' + ELEMENT_CLASS[STEM_ELEMENTS[STEM_ORDER.indexOf(p.pillar[0])]]);
        if (at.first) td.classList.add('tl-change');
        td.title = p.pillar + (p.ten_god ? ' ' + p.ten_god : '') + ' · ' + p.start_years.join('/') + '–' + p.end_years.join('/');
        // The pillar is written where a period begins, and again at the left edge for one already running.
        if (at.first || k === 0 || luckAt(row, year - 1).kind !== 'period') {
          const box = label(td, k, at), cell = append(box, 'span', 'tl-pillar');
          append(cell, 'b', stemClass(p.pillar[0]), p.pillar[0]); append(cell, 'b', branchClass(p.pillar[1]), p.pillar[1]);
          if (p.ten_god) append(box, 'small', 'tl-god', p.ten_god);
        }
      });
    });
  };
  draw();
  append(box, 'p', 'field-help', '一行一人、一格一年：颜色是大运天干的五行，粗边是交运的那一年，「?」是时辰不详时可能交运的年份。点年份或格子就切到那一年。');
}
// Each person's luck pillar and the year pillar of one year, with a year switcher; shared by the group and pair pages.
// people[i] carries the day master of v.members[i] for the card's colour dot.
// shownYear is the year the controls count from: the one asked for while a request runs, else the one shown.
function luckYearSection(v, {prefix, year: shownYear, pending, error, people, change, rerun}) {
  const box = append(result, 'section', 'group-year'); box.id = prefix + '-year';
  append(box, 'h4', 'subheading', '大运流年对照');
  const nav = append(box, 'div', 'inline-control group-year-nav');
  const year = shownYear;
  const prev = append(nav, 'button', 'tiny-button', '‹ 上一年'); prev.type = 'button'; prev.id = prefix + '-year-prev';
  const label = append(nav, 'label', 'group-year-label', '公历年');
  const input = append(label, 'input'); input.type = 'number'; input.id = prefix + '-year-input';
  input.min = '1901'; input.max = '2099'; input.step = '1'; input.value = luckYearTyped[prefix] ?? String(year); input.inputMode = 'numeric';
  const next = append(nav, 'button', 'tiny-button', '下一年 ›'); next.type = 'button'; next.id = prefix + '-year-next';
  const today = append(nav, 'button', 'tiny-button', '今年'); today.type = 'button'; today.id = prefix + '-year-today';
  prev.disabled = year <= 1901; next.disabled = year >= 2099;
  // A step that reaches 1901 or 2099 disables the button it was made with; keyboard focus moves to the year field.
  prev.dataset.focusFallback = next.dataset.focusFallback = prefix + '-year-input';
  // A year typed but not entered yet is where the steps count from.
  prev.addEventListener('click', () => change((takeTypedYear(prefix) ?? year) - 1));
  next.addEventListener('click', () => change((takeTypedYear(prefix) ?? year) + 1));
  today.addEventListener('click', () => change(new Date().getFullYear()));
  // Rendering removes this field, and a removed field that still holds a typed value fires another change as it
  // loses focus; running the request after the event keeps that second render from starting inside the first.
  // A field removed by that render (or by a reply arriving while the user types) is not a request.
  input.addEventListener('input', () => {luckYearTyped[prefix] = input.value;});
  // A button pressed as the field loses focus (对照关系, 下一年…) acts on its own: committing the typed year here
  // would redraw the page between press and release and swallow that click. The run buttons take the typed year.
  input.addEventListener('change', () => {
    const value = Number(input.value);
    setTimeout(() => {if (input.isConnected && !pressedButton) {luckYearTyped[prefix] = null; change(value);}});
  });
  const status = append(nav, 'span', 'group-year-status muted'); status.setAttribute('role', 'status');
  if (pending) status.textContent = '正在换年…';
  if (error) append(box, 'p', 'inline-msg', error);
  if (!v) {append(box, 'p', 'field-help', rerun); return;}
  const head = append(box, 'p', 'group-year-title');
  texts(head, String(v.year) + ' ', '流年', ' ');
  append(head, 'b', stemClass(v.year_pillar[0]), v.year_pillar[0]); append(head, 'b', branchClass(v.year_pillar[1]), v.year_pillar[1]);
  texts(head, ' · ', ANIMAL_YEARS[BRANCH_ORDER.indexOf(v.year_pillar[1])]);
  append(box, 'p', 'field-help', '每张卡片是这一年里此人所在的大运和流年：十神以本人日主看天干；流年下面的小字是与本人原局地支的关系（冲月是与月柱六冲，合、刑、害同理，同是同支；日空、年空是落在旬空），悬停可看全文。年龄是这一年里满的周岁。');
  luckTimeline(box, v, prefix, change);
  const cards = append(box, 'div', 'group-year-cards');
  v.members.forEach((m, i) => {
    const card = append(cards, 'article', 'group-year-card'); card.id = prefix + '-year-card-' + i;
    const member = people[i];
    const top = append(card, 'div', 'group-member-head');
    append(top, 'span', 'group-dot ' + (member.day_master ? 'bg-' + ELEMENT_CLASS[member.day_master_element] : 'dot-unknown'));
    append(top, 'strong', 'user-text', m.label);
    const sub = append(top, 'small', 'muted');
    texts(sub, GENDER_TEXT[m.gender] || '性别未填');
    if (m.status === 'not_born') {append(card, 'p', 'muted', '这一年尚未出生'); return;}
    texts(sub, ' · ', '年龄', ' ' + m.age);
    const l = m.luck;
    if (l.status === 'needs_gender') append(append(card, 'div', 'group-year-row'), 'span', 'muted', '未填性别，不排大运');
    else if (l.status === 'uncertain_pillars') append(append(card, 'div', 'group-year-row'), 'span', 'group-uncertain', '时辰不详且当天交节，月柱不定，大运无法确定');
    else if (l.status === 'depends_on_hour') {
      l.options.forEach((option, k) => luckLine(card, option, k ? '或' : '大运'));
      append(card, 'small', 'group-uncertain', '时辰不详：出生当天早晚不同，大运也不同');
    } else luckLine(card, l, '大运');
    const n = m.year_reading;
    const yearRow = append(card, 'div', 'group-year-row');
    append(yearRow, 'span', 'pillar-stage-label', '流年');
    if (!n) {append(yearRow, 'span', 'muted', '原局有不定的柱，不与流年比较'); return;}
    append(yearRow, 'span', 'group-year-god', n.ten_god_of_stem);
    yearRow.title = natalText(n);
    natalMarks(yearRow, n);
    if (!natalMarkList(n).length && !n.branch_groups.length) append(yearRow, 'small', 'muted', '与原局地支无冲合');
    // Words in separate text nodes, so each translates on its own: 月柱 辛 丙辛合水, 补成 巳午未 三会方.
    if (n.stem_relations.length || n.branch_groups.length) {
      const more = append(card, 'div', 'group-year-extra');
      n.stem_relations.forEach(r => texts(append(more, 'span', 'relation-chip'), nameMap[r.pillar], ' ' + r.stem + ' ', r.labels.join('、')));
      n.branch_groups.forEach(x => texts(append(more, 'span', 'relation-chip'), '补成', ' ' + x.branches + ' ', x.kind === '三合' ? '三合局' : '三会方'));
    }
    if ((n.shensha || []).length) {
      const sha = append(card, 'div', 'pillar-shensha');
      append(sha, 'span', 'pillar-stage-label', '神煞');
      n.shensha.forEach(x => {const tag = append(sha, 'span', 'shensha-tag', x.name); tag.title = shenshaBasis(x);});
    }
  });
  append(box, 'h4', 'subheading', '大运之间');
  const marked = v.luck_pairs.filter(p => p.branch_labels.length || p.stem_combination);
  const list = append(box, 'div', 'group-year-links'); list.id = prefix + '-year-links';
  marked.forEach(p => {
    const row = append(list, 'div', 'group-year-link');
    [[p.a_label, p.a_pillar], [p.b_label, p.b_pillar]].forEach(([who, pillar], k) => {
      if (k) row.append(' ↔ ');
      append(row, 'strong', 'user-text', who);
      const cell = append(row, 'span', 'group-year-pillar');
      append(cell, 'b', stemClass(pillar[0]), pillar[0]); append(cell, 'b', branchClass(pillar[1]), pillar[1]);
    });
    const tags = append(row, 'span', 'group-tags');
    if (p.stem_combination) append(tags, 'span', 'relation-chip link-combine', p.stem_combination);
    p.branch_labels.forEach(x => append(tags, 'span', 'relation-chip link-' + LINK_CLASS[x], x));
  });
  if (!v.luck_pairs.length) append(list, 'p', 'field-help', '这一年少于两位成员排出了大运，没有可比较的大运。');
  else if (!marked.length) append(list, 'p', 'field-help', '这一年成员的大运之间没有天干五合或地支冲合刑害。');
  if (v.members.some(m => m.status === 'born' && !m.luck.pillar)) append(box, 'p', 'field-help', '未填性别、未起运或大运随时辰而定的成员不参与大运之间的比较。');
  v.notes.forEach(x => note(box, x));
}
// Every labelled branch link between two charts, one row per pair of pillars.
function branchLinkTable(parent, aLabel, bLabel, links) {
  if (!links.length) return null;
  const t = append(append(parent, 'div', 'table-wrap'), 'table', 'data-table');
  const h = append(append(t, 'thead'), 'tr');
  append(h, 'th', 'user-text', aLabel); append(h, 'th', null, '地支');
  append(h, 'th', 'user-text', bLabel); append(h, 'th', null, '地支'); append(h, 'th', null, '标签');
  const tb = append(t, 'tbody');
  links.forEach(link => {
    const tr = append(tb, 'tr');
    append(tr, 'td', null, link.a_label); append(append(tr, 'td'), 'b', branchClass(link.a_branch), link.a_branch);
    append(tr, 'td', null, link.b_label); append(append(tr, 'td'), 'b', branchClass(link.b_branch), link.b_branch);
    const tags = append(tr, 'td');
    link.labels.forEach(x => append(tags, 'span', 'relation-chip link-' + LINK_CLASS[x], x));
  });
  return t;
}
function groupGraph(parent, g) {
  const n = g.members.length, size = 360, c = size / 2, radius = n === 2 ? 110 : 128;
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${size} ${size}`); svg.setAttribute('class', 'group-graph'); svg.id = 'group-graph';
  svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', '成员关系图');
  const at = i => {
    const angle = -Math.PI / 2 + 2 * Math.PI * i / n + (n === 2 ? Math.PI / 2 : 0);
    return [c + radius * Math.cos(angle), c + radius * Math.sin(angle)];
  };
  const make = (tag, attrs, parentNode = svg) => {
    const node = document.createElementNS(SVG_NS, tag);
    Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
    parentNode.append(node);
    return node;
  };
  const filter = groupDraft.filter, focus = groupDraft.focus;
  g.pairs.forEach(p => {
    const [x1, y1] = at(p.a), [x2, y2] = at(p.b);
    const has = pairHas(p, filter), touches = focus === null || p.a === focus || p.b === focus;
    const types = Object.keys(LINK_CLASS).filter(type => type === 'combine' ? !!p.day_stems.combination : p.label_counts[type] > 0);
    const edge = make('g', {class: 'group-edge' + (has && touches ? '' : ' is-dim') + types.map(type => ' link-' + LINK_CLASS[type]).join('')});
    edge.dataset.pair = p.a + '-' + p.b;
    make('line', {x1, y1, x2, y2, class: 'edge-line' + (filter !== 'all' ? ' link-' + LINK_CLASS[filter] : ''), 'stroke-width': has ? 1.5 + Math.min(pairCount(p, filter), 6) * 0.5 : 1}, edge);
    make('line', {x1, y1, x2, y2, class: 'edge-hit'}, edge);
    const count = pairCount(p, filter);
    if (has) {
      const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
      make('circle', {cx: mx, cy: my, r: 9, class: 'edge-badge'}, edge);
      const label = make('text', {x: mx, y: my + 4, 'text-anchor': 'middle', class: 'edge-count'}, edge);
      label.textContent = String(count);
    }
    const tip = make('title', {}, edge);
    tip.textContent = p.a_label + ' ↔ ' + p.b_label;
    edge.addEventListener('click', () => {
      const item = document.getElementById(`group-pair-${p.a}-${p.b}`);
      if (item) {item.open = true; item.scrollIntoView({block: 'center', behavior: 'smooth'});}
    });
  });
  g.members.forEach((m, i) => {
    const [x, y] = at(i);
    const node = make('g', {id: 'group-node-' + i, class: 'group-node' + (focus === i ? ' is-focus' : ''), tabindex: 0, role: 'button',
      'aria-pressed': String(focus === i), 'aria-label': m.label});
    make('circle', {cx: x, cy: y, r: 27, class: 'node-disc ' + (m.day_master ? 'node-' + ELEMENT_CLASS[m.day_master_element] : 'node-unknown')}, node);
    const stem = make('text', {x, y: y + 6, 'text-anchor': 'middle', class: 'node-stem'}, node);
    stem.textContent = m.day_master || '?';
    const name = make('text', {x, y: y + (y > c ? 46 : -36), 'text-anchor': 'middle', class: 'node-name user-text'}, node);
    name.textContent = m.label.length > 6 ? m.label.slice(0, 6) + '…' : m.label;
    const toggle = () => {groupDraft.focus = groupDraft.focus === i ? null : i; render();};
    node.addEventListener('click', toggle);
    node.addEventListener('keydown', event => {if (event.key === 'Enter' || event.key === ' ') {event.preventDefault(); toggle();}});
  });
  append(parent, 'div', 'group-graph-wrap').append(svg);
}
// Reverse lookup: four pillars -> every matching birth interval in 1901–2099.
const JIAZI = Array.from({length: 60}, (_, i) => STEM_ORDER[i % 10] + BRANCH_ORDER[i % 12]);
let pillarDraft = null, pillarResult = null;
// Today card: calendar facts for this moment on the device clock; with a chart, the traditional labels against it.
const deviceZone = () => {try {return Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Shanghai';} catch (_) {return 'Asia/Shanghai';}};
// The device reading with its UTC offset, so a repeated daylight-saving hour still names one instant.
function localMoment() {
  const n = new Date(), pad = x => String(x).padStart(2, '0'), off = -n.getTimezoneOffset();
  const zone = (off < 0 ? '-' : '+') + pad(Math.floor(Math.abs(off) / 60)) + ':' + pad(Math.abs(off) % 60);
  return localToday() + 'T' + pad(n.getHours()) + ':' + pad(n.getMinutes()) + zone;
}
let todayData = null, todayKey = null, todayPending = false, todayError = '', todayBirthSkipped = false;
function todayRequest() {
  const body = {moment: localMoment(), timezone: deviceZone()};
  if (current && currentInput) body.birth = currentInput;
  return body;
}
function ensureToday(then) {
  const body = todayRequest(), key = JSON.stringify(body);
  if (todayKey === key || todayPending) return;
  todayPending = true;
  fetchAlmanac(body, true)
    .then(({result, birthSkipped}) => {todayData = result; todayError = ''; todayBirthSkipped = birthSkipped;})
    .catch(err => {todayData = null; todayError = err.message;})
    .finally(() => {todayPending = false; todayKey = key; renderTodayChip(); if (then) then();});
}
// The natal comparison is optional (a chart born after the moment is rejected), and an unrecognised
// device zone may fall back to China time: either way the plain card still shows.
async function fetchAlmanac(body, zoneFallback) {
  const tries = [body];
  if (body.birth) {const {birth, ...plain} = body; tries.push(plain);}
  if (zoneFallback && body.timezone !== 'Asia/Shanghai') tries.push(...tries.map(data => ({...data, timezone: 'Asia/Shanghai'})));
  let last = null;
  for (const data of tries) {
    try {return {result: await postJSON('/api/daily-almanac', data), birthSkipped: !!body.birth && !data.birth};}
    catch (err) {last = err;}
  }
  throw last;
}
// Another date and time picked on the card. It reuses the zone the live card already resolved, so a time
// that does not exist there (a skipped daylight-saving hour) is reported rather than moved to China time.
let todayPick = null, pickData = null, pickKey = null, pickPending = false, pickError = '', pickBirthSkipped = false;
function pickRequest() {
  const body = {moment: todayPick.date + 'T' + todayPick.time, timezone: todayData ? todayData.timezone : deviceZone()};
  if (current && currentInput) body.birth = currentInput;
  return body;
}
function shiftDate(day, days) {
  const [y, m, d] = day.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d + days)).toISOString().slice(0, 10);
}
function todayPicker(parent) {
  const bar = append(parent, 'div', 'inline-control today-picker');
  const date = createInput('日期', 'date', todayPick ? todayPick.date : localToday(), bar);
  date.id = 'today-date'; date.min = '1901-01-01'; date.max = '2099-12-31';
  const time = createInput('时间', 'time', todayPick ? todayPick.time : localMoment().slice(11, 16), bar);
  time.id = 'today-time';
  const pick = (day, clock) => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || day < '1901-01-01' || day > '2099-12-31' || !clock) return;
    todayPick = {date: day, time: clock}; render();
  };
  const nav = append(bar, 'div', 'today-nav');
  [['today-prev', '前一天', -1], ['today-next', '后一天', 1]].forEach(([id, label, days]) => {
    const button = append(nav, 'button', 'tiny-button', label); button.type = 'button'; button.id = id;
    button.addEventListener('click', () => pick(shiftDate(date.value || localToday(), days), time.value || '12:00'));
  });
  if (todayPick) {
    const now = append(nav, 'button', 'tiny-button', '回到此刻'); now.type = 'button'; now.id = 'today-now';
    now.addEventListener('click', () => {todayPick = null; render();});
  }
  date.addEventListener('change', () => pick(date.value, time.value || '12:00'));
  time.addEventListener('change', () => pick(date.value || localToday(), time.value));
}
// A page left open keeps the card current: refetch once the device clock reaches a new hour (the hour
// pillar and, at midnight, the date change) and whenever the page becomes visible again.
function refreshTodayIfStale() {
  if (document.hidden || todayPending || !todayKey) return;
  if (JSON.parse(todayKey).moment.slice(0, 13) === localMoment().slice(0, 13)) return;
  ensureToday(() => {if (active === 'today') render();});
}
setInterval(refreshTodayIfStale, 60000);
document.addEventListener('visibilitychange', refreshTodayIfStale);
const SVG_NS = 'http://www.w3.org/2000/svg';
function moonIcon(parent, moon, size = 56) {
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', '0 0 48 48'); svg.setAttribute('width', size); svg.setAttribute('height', size);
  svg.setAttribute('class', 'moon-icon'); svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', moon.phase + ' ' + Math.round(moon.illuminated_fraction * 100) + '%');
  const disc = document.createElementNS(SVG_NS, 'circle');
  disc.setAttribute('cx', 24); disc.setAttribute('cy', 24); disc.setAttribute('r', 20); disc.setAttribute('class', 'moon-dark');
  svg.append(disc);
  const angle = moon.elongation_degrees * Math.PI / 180, r = 20, rx = Math.abs(Math.cos(angle)) * r;
  if (moon.illuminated_fraction > 0.004) {
    // Northern-hemisphere view: the lit limb is on the right while waxing. The terminator is a half ellipse.
    const crescent = Math.cos(angle) > 0;
    const outer = moon.waxing ? 1 : 0, inner = moon.waxing ? (crescent ? 0 : 1) : (crescent ? 1 : 0);
    const lit = document.createElementNS(SVG_NS, 'path');
    lit.setAttribute('d', `M24 4 A${r} ${r} 0 0 ${outer} 24 44 A${rx.toFixed(2)} ${r} 0 0 ${inner} 24 4 Z`);
    lit.setAttribute('class', 'moon-lit');
    svg.append(lit);
  }
  parent.append(svg);
  return svg;
}
const clockOf = iso => iso.slice(5, 10).replace('-', '/') + ' ' + iso.slice(11, 16);
const WEEKDAY_NAMES = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'];
const ANIMAL_YEARS = ['鼠年', '牛年', '虎年', '兔年', '龙年', '蛇年', '马年', '羊年', '猴年', '鸡年', '狗年', '猪年'];
// Numbers sit in their own text node so the units around them translate as whole entries.
function texts(parent, ...parts) {parts.forEach(part => parent.append(String(part))); return parent;}
function renderToday() {
  title(result, '今日历法', todayPick ? '所选时刻 · 历法事实 · 不打吉凶分' : '本机时间 · 历法事实 · 不打吉凶分');
  todayPicker(result);
  let t, skipped;
  if (todayPick) {
    const body = pickRequest(), key = JSON.stringify(body);
    if (pickKey !== key) {
      if (!pickPending) {
        pickPending = true;
        fetchAlmanac(body, false)
          .then(({result: data, birthSkipped}) => {pickData = data; pickError = ''; pickBirthSkipped = birthSkipped;})
          .catch(err => {pickData = null; pickError = err.message;})
          .finally(() => {pickPending = false; pickKey = key; if (active === 'today') render();});
      }
      append(result, 'p', 'field-help', '正在计算所选时刻的四柱、节气和月相…');
      return;
    }
    if (!pickData) {append(result, 'p', 'inline-msg', '所选时刻算不出来：' + pickError); return;}
    t = pickData; skipped = pickBirthSkipped;
  } else {
    if (todayKey !== JSON.stringify(todayRequest())) {
      ensureToday(() => {if (active === 'today') render();});
      if (!todayData) {append(result, 'p', 'field-help', '正在计算今天的四柱、节气和月相…'); return;}
    }
    if (!todayData) {append(result, 'p', 'inline-msg', '今日历法暂时算不出来：' + todayError); return;}
    t = todayData; skipped = todayBirthSkipped;
  }
  const day = todayPick ? '当天' : '今天';
  const hero = append(result, 'section', 'today-hero');
  const date = append(hero, 'div', 'today-date');
  texts(append(date, 'small'), t.date.replace(/-/g, '/'), ' · ', WEEKDAY_NAMES['一二三四五六日'.indexOf(t.weekday)]);
  append(date, 'strong', 'today-lunar', t.lunar.label);
  texts(append(date, 'span', 'today-year'), t.pillars.year, ' · ', ANIMAL_YEARS[BRANCH_ORDER.indexOf(t.pillars.year[1])]);
  const grid = append(hero, 'div', 'today-pillars');
  for (const key of ['year', 'month', 'day', 'hour']) {
    const p = t.pillars[key];
    const box = append(grid, 'div', 'today-pillar' + (key === 'day' ? ' today-day' : ''));
    append(box, 'small', null, nameMap[key]);
    append(box, 'b', stemClass(p[0]), p[0]);
    append(box, 'b', branchClass(p[1]), p[1]);
  }
  const moonBox = append(hero, 'div', 'today-moon');
  moonIcon(moonBox, t.moon);
  const moonText = append(moonBox, 'div');
  append(moonText, 'strong', null, t.moon.phase);
  texts(append(moonText, 'small'), '照亮', ' ' + Math.round(t.moon.illuminated_fraction * 100) + '%');
  texts(append(moonText, 'small'), '下次满月', ' ' + clockOf(t.moon.next_full_moon));
  texts(append(moonText, 'small'), '下次新月', ' ' + clockOf(t.moon.next_new_moon));

  const term = append(result, 'section', 'today-term');
  const now = append(term, 'div', 'today-term-now');
  append(now, 'strong', null, t.solar_term.current.name);
  texts(append(now, 'small'), '已入节', ' ' + t.solar_term.current.day_number, ' 天', ' · ', '交节', ' ' + clockOf(t.solar_term.current.start));
  const track = append(term, 'div', 'today-term-track');
  track.setAttribute('role', 'progressbar'); track.setAttribute('aria-valuemin', '0'); track.setAttribute('aria-valuemax', '100');
  track.setAttribute('aria-valuenow', String(Math.round(t.solar_term.progress * 100)));
  track.setAttribute('aria-label', t.solar_term.current.name + ' → ' + t.solar_term.next.name);
  append(track, 'span', 'today-term-fill').style.width = Math.round(t.solar_term.progress * 100) + '%';
  const next = append(term, 'div', 'today-term-next');
  append(next, 'strong', null, t.solar_term.next.name);
  const until = append(next, 'small');
  if (t.solar_term.next.days_until) texts(until, String(t.solar_term.next.days_until), ' 天后'); else texts(until, day);
  texts(until, ' · ', '交节', ' ' + clockOf(t.solar_term.next.start));

  const facts = append(result, 'div', 'meta-tags today-facts');
  texts(append(facts, 'span'), '建除值日', ' ' + t.day_officer.officer);
  if (t.day_officer.jie_boundary_on_date) append(facts, 'span', null, todayPick ? '当天交节，节令前后值日不同' : '今天交节，节令前后值日不同');
  texts(append(facts, 'span'), '农历本月', ' ' + t.lunar.month_days, ' 天');
  append(facts, 'span', null, t.timezone);
  const year = t.date.slice(0, 4);
  const ics = append(facts, 'a', 'today-ics', '下载本年节气与月相日历（ICS）'); ics.href = icsHref(year, true); ics.id = 'today-ics';
  const icsMessage = append(result, 'p', 'inline-msg');
  ics.addEventListener('click', event => {event.preventDefault(); downloadIcs(year, true, icsMessage);});

  append(result, 'h4', 'subheading', '与我的命盘');
  if (!t.personal && skipped) {
    append(result, 'p', 'field-help', '当前命盘的出生时间晚于此刻，不列个人对照。');
  } else if (!t.personal) {
    const empty = append(result, 'div', 'today-empty');
    append(empty, 'p', 'field-help', '生成命盘后，这里会列出今天四柱对日主的十神，以及与本命四支的六冲、六合、同支。');
    const go = append(empty, 'button', 'tiny-button', '用当前出生资料生成命盘'); go.type = 'button'; go.id = 'today-generate';
    go.addEventListener('click', () => form.requestSubmit());
  } else {
    const me = t.personal;
    const tags = [`日主 ${me.day_master}`, `虚岁 ${me.nominal_age}`];
    if (me.decade_period && me.decade_period.pillar) tags.push(`大运 ${me.decade_period.pillar}（${me.decade_period.stem_ten_god}）`);
    else if (me.decade_period) tags.push('尚未起运');
    else tags.push('选择性别后显示大运');
    meta(result, tags);
    const wrap = append(result, 'div', 'table-wrap');
    const table = append(wrap, 'table', 'data-table today-table');
    const head = append(append(table, 'thead'), 'tr');
    ['', todayPick ? '当日' : '今日', '天干十神', '地支与本命'].forEach(text => append(head, 'th', null, text));
    const body = append(table, 'tbody');
    me.today_against_natal.forEach(row => {
      const tr = append(body, 'tr');
      append(tr, 'th', null, nameMap[row.pillar_of]);
      const cell = append(tr, 'td', 'pillar-cell');
      append(cell, 'b', stemClass(row.pillar[0]), row.pillar[0]); append(cell, 'b', branchClass(row.pillar[1]), row.pillar[1]);
      append(tr, 'td', null, row.stem_ten_god);
      const rel = append(tr, 'td');
      if (!row.branch_relations.length) append(rel, 'span', 'muted', '—');
      row.branch_relations.forEach(x => {
        const chip = append(rel, 'span', 'relation-chip rel-' + {'六冲': 'clash', '六合': 'harmony', '同支': 'same'}[x.type]);
        texts(chip, x.type, ' · ', x.with, ' ' + x.natal_branch);
      });
    });
  }
  t.limitations.forEach(text => note(result, text));
}
// A one-line today summary in the page header; it opens the full card.
function renderTodayChip() {
  const chip = $('#today-chip');
  if (!chip || !todayData) return;
  const t = todayData;
  chip.replaceChildren();
  append(chip, 'span', 'today-chip-label', '今日');
  moonIcon(chip, t.moon, 16);
  texts(chip, t.lunar.label, ' · ', t.pillars.day, ' · ', t.solar_term.current.name);
  chip.hidden = false;
}
function renderPillarSearch() {
  title(result, '四柱反查出生时间', '给出四柱，列出 1901–2099 年间所有对得上的出生时段');
  append(result, 'p', 'info-inline', '时区、时制和经度沿用出生资料；边界用和排盘相同的计算逐秒校准。');
  if (!pillarDraft) {
    const p = current ? current.bazi.pillars : null;
    pillarDraft = {year: p ? p.year.text : JIAZI[0], month: p ? p.month.text : JIAZI[2], day: p ? p.day.text : JIAZI[0], hour: p ? p.hour.text : '',
      start_year: 1901, end_year: 2099, late_zi_day_rollover: readInput().late_zi_day_rollover};
  }
  const row = append(result, 'div', 'inline-control pillar-pickers');
  const pickers = {};
  [['year', '年柱'], ['month', '月柱'], ['day', '日柱'], ['hour', '时柱（可不选）']].forEach(([key, label]) => {
    const wrap = append(row, 'label', null, label);
    const select = append(wrap, 'select'); select.id = 'pillar-' + key;
    if (key === 'hour') {const op = append(select, 'option', null, '不限'); op.value = '';}
    JIAZI.forEach(text => {const op = append(select, 'option', null, text); op.value = text;});
    select.value = pillarDraft[key];
    pickers[key] = select;
  });
  const options = append(result, 'div', 'inline-control');
  const from = createInput('起始年', 'number', String(pillarDraft.start_year), options); from.id = 'pillar-from'; from.min = '1901'; from.max = '2099';
  const to = createInput('结束年', 'number', String(pillarDraft.end_year), options); to.id = 'pillar-to'; to.min = '1901'; to.max = '2099';
  const lateLine = append(options, 'label', 'check-line');
  const late = append(lateLine, 'input'); late.type = 'checkbox'; late.id = 'pillar-late-zi'; late.checked = pillarDraft.late_zi_day_rollover;
  lateLine.append(' 23:00 换日（早晚子时）');
  const actions = append(result, 'div', 'inline-control');
  if (current) {
    const mine = append(actions, 'button', 'tiny-button', '填入当前命盘的四柱'); mine.type = 'button'; mine.id = 'pillar-mine';
    mine.addEventListener('click', () => {pillarDraft = null; pillarResult = null; render();});
  }
  const run = append(actions, 'button', null, '反查'); run.type = 'button'; run.id = 'pillar-search-run';
  const message = append(result, 'p', 'inline-msg');
  run.addEventListener('click', async () => {
    pillarDraft = {year: pickers.year.value, month: pickers.month.value, day: pickers.day.value, hour: pickers.hour.value,
      start_year: Number(from.value), end_year: Number(to.value), late_zi_day_rollover: late.checked};
    const input = readInput();
    const body = {year: pillarDraft.year, month: pillarDraft.month, day: pillarDraft.day, hour: pillarDraft.hour || null,
      timezone: input.timezone, time_mode: input.time_mode, longitude: input.longitude,
      late_zi_day_rollover: pillarDraft.late_zi_day_rollover, start_year: pillarDraft.start_year, end_year: pillarDraft.end_year};
    run.disabled = true; message.className = 'inline-msg progress'; message.textContent = '正在逐年反查…';
    try {pillarResult = await postJSON('/api/pillars-to-dates', body); render(); announce('四柱反查完成：' + pillarResult.count + ' 个时段');}
    catch (e) {pillarResult = null; message.className = 'inline-msg'; message.textContent = '反查失败：' + e.message;}
    finally {run.disabled = false;}
  });
  if (!pillarResult) return;
  const r = pillarResult;
  r.impossible_combination.forEach(x => append(result, 'p', 'inline-msg', x));
  meta(result, [`${r.pillars.year} ${r.pillars.month} ${r.pillars.day} ${r.pillars.hour || ''}`.trim(), `${r.count} 个时段`,
    `${r.range.start_year}–${r.range.end_year}`, `换日 ${r.rules.day_boundary}`, r.timezone]);
  if (!r.count && !r.impossible_combination.length) append(result, 'p', 'info-inline', '这段年份里没有对得上的时间。可以放宽年份，或切换换日规则再试。');
  if (r.count) {
    const table = append(append(result, 'div', 'table-wrap'), 'table', 'data-table');
    const head = append(append(table, 'thead'), 'tr');
    ['起（含）', '止（不含）', '时长', '农历', ''].forEach(x => append(head, 'th', null, x));
    const body = append(table, 'tbody');
    r.matches.forEach((m, i) => {
      const tr = append(body, 'tr');
      append(tr, 'td', null, m.start.slice(0, 19).replace('T', ' '));
      append(tr, 'td', null, m.end_exclusive.slice(0, 19).replace('T', ' '));
      append(tr, 'td', null, m.duration_minutes >= 120 ? (m.duration_minutes / 60).toFixed(1) + ' 小时' : m.duration_minutes + ' 分钟');
      append(tr, 'td', null, `${m.lunar_date.year}年${m.lunar_date.is_leap_month ? '闰' : ''}${m.lunar_date.month}月${m.lunar_date.day}日`);
      const cell = append(tr, 'td');
      if (!m.suggested_local) {append(cell, 'small', 'field-help', '整段落在夏令时重复或跳过的钟点，请手动填写'); return;}
      const use = append(cell, 'button', 'tiny-button', '用这个时间排盘'); use.type = 'button'; use.id = 'pillar-use-' + i;
      use.addEventListener('click', () => {
        $('#birth_datetime').value = m.suggested_local; $('#late_zi_day_rollover').checked = r.rules.day_boundary === '23:00';
        $('#hour_unknown').checked = !r.pillars.hour; updateHourUnknown(); updateStaleBirthNotice();
        activateTab(tabs.find(t => t.dataset.tab === 'bazi'));
        form.requestSubmit();
      });
    });
    if (r.truncated) note(result, '结果较多，只列出前 40 个时段。');
  }
  r.limitations.forEach(x => note(result, x));
}

// Paste a chart from other software and compare it with XuanShu field by field.
let importDraft = '', importResult = null;
function renderImportCheck() {
  title(result, '外部命盘导入核对', '粘贴其他软件排出的命盘，逐项比对，并找出对方用的规则');
  append(result, 'p', 'info-inline', '按出生资料里的信息排出玄枢的盘再比较。粘贴的内容只用于本次核对，服务器不保存。');
  append(result, 'p', 'field-help', '支持简体或繁体的命盘文字；没识别到的部分会略过。');
  const area = append(result, 'textarea', 'import-text'); area.id = 'import-text'; area.rows = 8; area.maxLength = 6000;
  area.setAttribute('data-no-i18n', '');  // the example shows the Chinese formats the parser reads
  area.placeholder = '例如：\n乾造 庚辰 甲申 丙午 庚寅\n命宫在午，身宫在官禄，木三局，命主破军，身主文昌\n官禄宫：廉贞利 天府庙\n太阳化禄 武曲化权 太阴化科 天同化忌';
  area.value = importDraft;
  area.addEventListener('input', () => {importDraft = area.value;});
  const actions = append(result, 'div', 'inline-control');
  const run = append(actions, 'button', null, '核对'); run.type = 'button'; run.id = 'import-check-run';
  const message = append(result, 'p', 'inline-msg');
  run.addEventListener('click', async () => {
    if (!area.value.trim()) {message.textContent = '先粘贴命盘文字。'; return;}
    run.disabled = true; message.className = 'inline-msg progress'; message.textContent = '正在比对…';
    try {importResult = await postJSON('/api/chart-import-check', {birth: readInput(), text: area.value}); render();
      announce(`核对完成：${importResult.summary.matched} 项一致，${importResult.summary.mismatched} 项不同`);}
    catch (e) {importResult = null; message.className = 'inline-msg'; message.textContent = '核对失败：' + e.message;}
    finally {run.disabled = false;}
  });
  if (!importResult) return;
  const r = importResult;
  if (!r.recognized_count) {
    append(result, 'p', 'inline-msg', '没有识别到可以比对的字段。支持的写法：');
    const list = append(result, 'ul', 'plain-list'); r.accepted_formats.forEach(x => append(list, 'li', null, x));
    return;
  }
  meta(result, [`已识别字段 ${r.recognized_count}`, `一致 ${r.summary.matched}`, `不同 ${r.summary.mismatched}`]);
  if (r.reproducing_variants.length) {
    const box = append(result, 'div', 'import-verdict ok');
    append(box, 'b', null, '改用下面的规则后，粘贴的命盘与玄枢完全一致：');
    if (r.fields.some(f => !f.match && f.key.startsWith('ziwei.brightness'))) append(box, 'small', 'muted', '星曜亮度的差异来自亮度表，不计入。');
    r.variants.filter(v => !v.mismatched).slice(0, 3).forEach((v, i) => {
      const line = append(box, 'div', 'import-variant');
      append(line, 'span', null, v.label);
      // A different reading of the birth time itself (daylight saving) is not applied automatically.
      const base = readInput();
      if (v.settings.birth_datetime !== base.birth_datetime || (v.settings.timezone || 'Asia/Shanghai') !== base.timezone) {
        append(line, 'small', 'muted', '需手动改时间'); return;
      }
      const apply = append(line, 'button', 'tiny-button', '套用到出生资料'); apply.type = 'button'; apply.id = 'import-apply-' + i;
      apply.addEventListener('click', () => {setInput(v.settings); importResult = null; form.requestSubmit(); setFeedback('已套用：' + v.label);});
    });
  } else if (!r.summary.mismatched) {
    append(result, 'div', 'import-verdict ok', '识别到的字段全部一致。');
  }
  const table = append(append(result, 'div', 'table-wrap'), 'table', 'data-table import-table');
  const head = append(append(table, 'thead'), 'tr');
  ['项目', '粘贴的命盘', '玄枢', '结果'].forEach(x => append(head, 'th', null, x));
  const body = append(table, 'tbody');
  r.fields.forEach(f => {
    const tr = append(body, 'tr', f.match ? null : 'mismatch');
    append(tr, 'td', null, f.label); append(tr, 'td', null, f.theirs); append(tr, 'td', null, f.ours || '—');
    append(tr, 'td', 'import-result ' + (f.match ? 'same' : 'diff'), f.match ? '✓ 一致' : '✗ 不同');
  });
  if (r.possible_causes.length) {
    append(result, 'h4', 'subheading', '可能的原因');
    const list = append(result, 'ul', 'plain-list'); r.possible_causes.forEach(x => append(list, 'li', null, x));
  }
  const near = r.variants.filter(v => v.mismatched).slice(0, 4);
  if (near.length && !r.reproducing_variants.length) {
    append(result, 'h4', 'subheading', '换成其他规则后仍不一致的项目');
    const t2 = append(append(result, 'div', 'table-wrap'), 'table', 'data-table');
    const h2 = append(append(t2, 'thead'), 'tr'); ['规则', '仍不一致'].forEach(x => append(h2, 'th', null, x));
    const b2 = append(t2, 'tbody');
    near.forEach(v => {const tr = append(b2, 'tr'); append(tr, 'td', null, v.label); append(tr, 'td', null, v.mismatched_fields.join('、'));});
  }
  r.limitations.forEach(x => note(result, x));
}
function renderLunarInverseSection(){
  append(result,'h4','subheading','农历 → 公历反查（支持闰月）');
  const row=append(result,'div','inline-control');
  const y=createInput('农历年份','number',String(lunarInverseDraft.lunar_year),row);y.min='1901';y.max='2099';
  const m=createInput('农历月份','number',String(lunarInverseDraft.lunar_month),row);m.min='1';m.max='12';
  const d=createInput('农历日期','number',String(lunarInverseDraft.lunar_day),row);d.min='1';d.max='30';
  const check=append(row,'label',null,'闰月');const leap=append(check,'input');leap.type='checkbox';leap.checked=lunarInverseDraft.is_leap_month;
  const go=append(row,'button',null,'换算公历');go.type='button';go.id='lunar-inverse-run';
  const error=append(result,'p','inline-msg');
  go.addEventListener('click',async()=>{
    lunarInverseDraft={lunar_year:Number(y.value),lunar_month:Number(m.value),lunar_day:Number(d.value),is_leap_month:leap.checked};
    go.disabled=true;error.textContent='';
    try {lunarInverseResult=await postJSON('/api/lunar-to-gregorian',lunarInverseDraft);render();}
    catch(e) {lunarInverseResult=null;error.textContent='换算失败：'+e.message;}
    finally {go.disabled=false;}
  });
  if(lunarInverseResult) append(result,'div','feature-note',
      `公历 ${lunarInverseResult.gregorian_date} · ${lunarInverseResult.lunar_date.is_leap_month?'闰':''}${lunarInverseResult.lunar_date.month}月${lunarInverseResult.lunar_date.day}日`);
}
function pairText() {
  const r = pairResult, z = pairZiweiResult;
  const lines = ['玄枢 · 双人合盘对照', '', '【四柱】', ...pillarRows([['A', r.person_a], ['B', r.person_b]])];
  if ([r.person_a, r.person_b].some(p => PILLAR_KEYS.some(k => !p.pillars[k]))) lines.push(UNKNOWN_PILLAR_NOTE);
  const stems = ['A → B ' + (r.day_stems.a_sees_b || '？'), 'B → A ' + (r.day_stems.b_sees_a || '？')];
  if (r.day_stems.combination) stems.push(r.day_stems.combination);
  lines.push('日干：' + stems.join('，'),
    '生肖：' + (r.zodiac.a || '？') + ' / ' + (r.zodiac.b || '？') + (r.zodiac.labels.length ? ' ' + r.zodiac.labels.join('、') : ''),
    '地支' + '（A—B）：' + (r.branch_links.map(linkText).join('；') || '无标记'));
  if (z) {
    const land = z.ming_shen_landings;
    const where = x => x.palace_in_other_chart + '（' + [x.branch, ...(x.main_stars_there.length ? [x.main_stars_there.join('、')] : [])].join(' · ') + '）';
    lines.push('', '【紫微宫位叠盘】', `A 命宫落在 B 的${where(land.person_a_ming_in_b)}`, `B 命宫落在 A 的${where(land.person_b_ming_in_a)}`,
      `A 身宫落在 B 的${where(land.person_a_shen_in_b)}`, `B 身宫落在 A 的${where(land.person_b_shen_in_a)}`);
    lines.push(...textColumns([['地支', 'A 宫位', 'A 主星', 'B 宫位', 'B 主星'], ...z.palace_grid.map(row => [row.branch,
      row.person_a_palace, row.person_a_main_stars.join('、') || '—', row.person_b_palace, row.person_b_main_stars.join('、') || '—'])]));
    lines.push('四化入对方盘：');
    [['A → B', z.transformations_a_into_b], ['B → A', z.transformations_b_into_a]].forEach(([label, rows]) => lines.push('　' + `${label}（${rows[0].source_year_stem}年干）` + '：'
      + rows.map(t => t.star + t.type + ' ' + (t.target_palace ? t.target_palace + '（' + t.target_branch + '）' : '对方盘未安此星')).join('；')));
  } else lines.push('', PAIR_ZIWEI_NEEDS_HOURS);
  if (r.year_view) lines.push('', ...groupYearText(r.year_view, 'pair'));
  lines.push('', ...r.notes, ...(z ? z.limitations : []), ...TEXT_FOOTER);
  return finishText(lines);
}
const PAIR_ZIWEI_NEEDS_HOURS = '紫微宫位叠盘需要两人的出生时辰，有一方时辰不详时不列出。';
// A placeholder noon is not a birth hour: the hour pillar is left out, and Zi Wei needs both hours.
function pairBody() {
  const b = pairDraft.hour_unknown && pairDraft.birth_datetime ? pairDraft.birth_datetime.slice(0, 10) + 'T12:00' : pairDraft.birth_datetime;
  return {person_a: readInput(), person_b: {birth_datetime: b, timezone: pairDraft.timezone, gender: pairDraft.gender || 'unspecified'},
    person_a_hour_unknown: $('#hour_unknown').checked, person_b_hour_unknown: !!pairDraft.hour_unknown};
}
function renderPair() {
  title(result, '双人合盘对照', '八字四柱对照 + 紫微宫位叠盘 · 只做结构对照，不评分关系好坏');
  append(result, 'p', 'info-inline', 'A 使用出生资料里的信息；B 在下方单独填写。对照数据不会自动保存。');
  const row = append(result, 'div', 'inline-control');
  const date = createInput('B · 公历出生日期与时间', 'datetime-local', pairDraft.birth_datetime, row);
  date.id = 'pair_datetime'; date.min = '1901-01-01T00:00'; date.max = '2099-12-31T23:59';
  const label = append(row, 'label', null, 'B · 时区');
  const zone = append(label, 'select'); zone.id = 'pair_timezone';
  [...$('#timezone').options].forEach(opt => {const option = append(zone, 'option', null, opt.textContent); option.value = opt.value;});
  zone.value = pairDraft.timezone;
  const genderLabel = append(row, 'label', null, 'B · 性别（排大运用）');
  const gender = append(genderLabel, 'select'); gender.id = 'pair_gender';
  [['unspecified', '未填'], ['male', '男'], ['female', '女']].forEach(([value, text]) => {append(gender, 'option', null, text).value = value;});
  gender.value = pairDraft.gender || 'unspecified';
  const unknownRow = append(row, 'label', 'check-line');
  const unknown = append(unknownRow, 'input'); unknown.type = 'checkbox'; unknown.id = 'pair_hour_unknown'; unknown.checked = !!pairDraft.hour_unknown;
  unknownRow.append('B 不知道出生时辰');
  // B's details survive a visit to another tab, like the other drafts on the page.
  date.addEventListener('input', () => {pairDraft.birth_datetime = date.value;});
  zone.addEventListener('change', () => {pairDraft.timezone = zone.value;});
  gender.addEventListener('change', () => {pairDraft.gender = gender.value;});
  unknown.addEventListener('change', () => {
    pairDraft.hour_unknown = unknown.checked;
    if (unknown.checked && date.value) pairDraft.birth_datetime = date.value = date.value.slice(0, 10) + 'T12:00';
  });
  const run = append(row, 'button', null, '比较两人命盘'); run.type = 'button'; run.id = 'pair-run';
  run.disabled = pairRunning;
  const error = append(result, 'p', 'inline-msg', pairRunError);
  run.addEventListener('click', async () => {
    pairDraft = {birth_datetime: date.value, timezone: zone.value, gender: gender.value, hour_unknown: unknown.checked, year: pairDraft.year};
    if (!pairDraft.birth_datetime) {error.textContent = '请填写 B 的出生时间'; return;}
    run.disabled = true; error.textContent = ''; pairRunError = '';
    pairDraft.year = takeTypedYear('pair') ?? pairDraft.year;
    const ticket = ++pairYearTicket;
    pairRunning = true;
    try {
      const body = pairBody(), key = JSON.stringify(body);
      const skipZiwei = body.person_a_hour_unknown || body.person_b_hour_unknown;
      // Only the BaZi comparison takes the year; the Zi Wei overlay has no year view.
      const [reply, ziwei] = await Promise.all([postJSON('/api/pair', {...body, year: pairDraft.year}), skipZiwei ? null : postJSON('/api/ziwei-pair', body)]);
      if (ticket !== pairYearTicket) return;
      pairResult = reply; pairZiweiResult = ziwei; pairKey = key; pairRunning = false; pairYearError = '';
      // The year was switched while this ran: fetch that year for the new pair.
      if (reply.year_view && reply.year_view.year !== pairDraft.year) {pairYearPending = false; pairYear(pairDraft.year); return;}
      pairYearPending = false;
    } catch (err) {
      if (ticket !== pairYearTicket) return;
      pairRunning = false; pairYearPending = false; pairRunError = '比较失败：' + err.message;
    }
    if (active === 'pair') render();
  });
  if (!pairResult) return;
  if (pairKey !== JSON.stringify(pairBody())) append(result, 'p', 'feature-note', 'A 或 B 的资料已改变，下面仍是上一次的结果；点「比较两人命盘」更新。');
  const r = pairResult;
  meta(result, [`A 日主 ${r.person_a.day_master || '?'}`, `B 日主 ${r.person_b.day_master || '?'}`, '不提供匹配分数']);
  // The day-stem ten god both ways, the five combination and the zodiac pair, as on the group page.
  const facts = append(result, 'div', 'meta-tags pair-facts'); facts.id = 'pair-facts';
  texts(append(facts, 'span'), 'A → B', '：', r.day_stems.a_sees_b || '?');
  texts(append(facts, 'span'), 'B → A', '：', r.day_stems.b_sees_a || '?');
  if (r.day_stems.combination) append(facts, 'span', 'relation-chip link-combine', r.day_stems.combination);
  const zodiac = append(facts, 'span');
  texts(zodiac, '生肖', ' ' + (r.zodiac.a || '?') + ' / ' + (r.zodiac.b || '?'));
  r.zodiac.labels.forEach(x => zodiac.append(' · ', x));
  const askButton = chatAskButton('pair-ask-ai', 'pair', '把两人的出生资料放进对话输入框，你确认后再发送；发送前需在对话设置里勾选已获对方同意。',
    'AI 对话尚未启用，配置语言模型后可以把两人带进对话。', pairYearPending || pairRunning);
  askButton.addEventListener('click', () => {
    if (askWithTypedYear('pair', r.year_view && r.year_view.year, pairYear)) return;
    const {text: draft, others} = pairChatDraft(r, JSON.parse(pairKey || '{}'));
    pairChatBlock = sendDraftToChat(draft, others, pairChatBlock);
  });
  textExport(result, 'pair-text', pairText, 'xuanshu-pair.txt');
  const table = append(append(result, 'div', 'table-wrap'), 'table', 'data-table'); table.id = 'pair-pillars';
  const hr = append(append(table, 'thead'), 'tr');
  ['位置', 'A 四柱', 'B 四柱', '同位地支'].forEach(text => append(hr, 'th', null, text));
  const tbody = append(table, 'tbody');
  r.comparisons.forEach(row => {
    const tr = append(tbody, 'tr');
    append(tr, 'td', null, row.label);
    append(tr, 'td', row.person_a ? null : 'muted', row.person_a || '?');
    append(tr, 'td', row.person_b ? null : 'muted', row.person_b || '?');
    const tags = append(tr, 'td');
    if (row.labels.length) row.labels.forEach(x => append(tags, 'span', 'relation-chip link-' + LINK_CLASS[x], x));
    else append(tags, 'span', 'muted', row.person_a && row.person_b ? '无标记' : row.branch_relation);
  });
  append(result, 'h4', 'subheading', '四柱地支两两关系');
  const counts = append(result, 'div', 'group-tags');
  Object.entries(r.label_counts).forEach(([type, n]) => {if (n) texts(append(counts, 'span', 'relation-chip link-' + LINK_CLASS[type]), type, ' ', String(n));});
  if (!branchLinkTable(result, 'A', 'B', r.branch_links)) append(counts, 'span', 'muted', '无标记');
  else append(result, 'p', 'field-help', '每一行是 A 的一柱地支与 B 的一柱地支，包括不同位置的柱：同支、六合、六冲、六害、相刑。');
  luckYearSection(r.year_view, {prefix: 'pair', year: pairYearPending || pairRunning || !r.year_view ? pairDraft.year : r.year_view.year,
    pending: pairYearPending, error: pairYearError,
    people: [r.person_a, r.person_b], change: pairYear, rerun: '点「比较两人命盘」重新计算后可以看这一部分。'});
  r.notes.forEach(x => note(result, x));
  if (pairZiweiResult) renderZiweiPair(pairZiweiResult);
  else append(result, 'p', 'feature-note', PAIR_ZIWEI_NEEDS_HOURS);
}
// The two people of a pair result as a chat question, from the request the result belongs to.
function pairChatDraft(r, body) {
  const tr = text => typeof translateText === 'function' ? translateText(text) : text;
  const lines = [chatBirthLine('A', body.person_a, body.person_a_hour_unknown), chatBirthLine('B', body.person_b, body.person_b_hour_unknown)];
  const ask = [tr('请结合双人对照，帮我看看下面两位之间的关系，只解释传统标签的含义，不要打分。')];
  if (r.year_view) ask.push(tr('也请对照这一年的大运流年：') + r.year_view.year);
  // A is the current chart, which the chat already uses; B is the other person.
  return {text: [...ask, ...lines].join('\n'), others: [body.person_b.birth_datetime.slice(0, 10)]};
}
// Another year for the same two people: the request of the result shown, not the form being edited. While
// 比较两人命盘 runs, only the year asked for changes; that run's reply fetches it for the new pair.
async function pairYear(year) {
  // Called from a run's reply too, so another tab being open is not redrawn (it would lose what is typed there).
  const show = () => {if (active === 'pair') render();};
  if (!pairKey && !pairRunning) return;
  luckYearTyped.pair = null;
  if (!pairRunning && pairResult && pairResult.year_view && pairResult.year_view.year === year && !pairYearPending) {
    if (pairYearError) {pairYearError = ''; show();}
    return;
  }
  if (!(Number.isInteger(year) && year >= 1901 && year <= 2099)) {pairYearError = '年份要在 1901 到 2099 之间'; show(); return;}
  if (pairRunning) {pairDraft.year = year; pairYearPending = true; pairYearError = ''; show(); return;}
  const ticket = ++pairYearTicket;
  pairDraft.year = year; pairYearPending = true; pairYearError = ''; show();
  try {
    const reply = await postJSON('/api/pair', {...JSON.parse(pairKey), year});
    if (ticket !== pairYearTicket) return;
    pairResult = reply;
  } catch (err) {
    if (ticket !== pairYearTicket) return;
    pairYearError = '换年失败：' + err.message;
    // The next 比较两人命盘 asks for the year still shown, not the one that failed.
    if (pairResult && pairResult.year_view) pairDraft.year = pairResult.year_view.year;
  }
  pairYearPending = false;
  if (active === 'pair') render();
  askAfterYearLoaded('pair', !pairYearError);
}
function renderZiweiPair(z) {
  append(result, 'h4', 'subheading', '紫微宫位叠盘');
  const land = z.ming_shen_landings;
  const where = x => `${x.palace_in_other_chart}（${x.branch}${x.main_stars_there.length ? ' · ' + x.main_stars_there.join('、') : ''}）`;
  meta(result, [`A 命宫落在 B 的${where(land.person_a_ming_in_b)}`, `B 命宫落在 A 的${where(land.person_b_ming_in_a)}`,
    `A 身宫落在 B 的${where(land.person_a_shen_in_b)}`, `B 身宫落在 A 的${where(land.person_b_shen_in_a)}`]);
  const grid = append(append(result, 'div', 'table-wrap'), 'table', 'data-table'); grid.id = 'ziwei-pair-grid';
  const gh = append(append(grid, 'thead'), 'tr');
  ['地支', 'A 宫位', 'A 主星', 'B 宫位', 'B 主星'].forEach(text => append(gh, 'th', null, text));
  const gb = append(grid, 'tbody');
  z.palace_grid.forEach(r => {
    const tr = append(gb, 'tr');
    [r.branch, r.person_a_palace, r.person_a_main_stars.join('、') || '—', r.person_b_palace, r.person_b_main_stars.join('、') || '—']
      .forEach(text => append(tr, 'td', null, text));
  });
  const tt = append(append(result, 'div', 'table-wrap'), 'table', 'data-table'); tt.id = 'ziwei-pair-transformations';
  const th = append(append(tt, 'thead'), 'tr');
  ['方向', '四化', '星曜', '落入对方宫位'].forEach(text => append(th, 'th', null, text));
  const tb = append(tt, 'tbody');
  [['A → B', z.transformations_a_into_b], ['B → A', z.transformations_b_into_a]].forEach(([label, rows]) => rows.forEach(t => {
    const tr = append(tb, 'tr');
    [`${label}（${t.source_year_stem}年干）`, t.type, t.star, t.target_palace ? `${t.target_palace} · ${t.target_branch}` : '对方盘未安此星']
      .forEach(text => append(tr, 'td', null, text));
  }));
  z.limitations.forEach(x => note(result, x));
}
function renderAnnual() {
  title(result, '指定农历年干四化', '与本命四化分开显示 · 仅为星曜位置叠加');
  if (!current) {append(result, 'p', 'info-inline', '请先生成出生盘。'); return;}
  const row = append(result, 'div', 'inline-control');
  const year = createInput('目标农历纪年（1901–2099）', 'number', String(annualDraft), row);
  year.min='1901'; year.max='2099'; year.id='annual-year';
  const button = append(row, 'button', null, '查询年干四化'); button.type='button'; button.id='annual-run';
  const error = append(result, 'p', 'inline-msg');
  button.addEventListener('click', async () => {
    annualDraft = Number(year.value);
    button.disabled=true;
    try {annualResult=await postJSON('/api/annual',{birth:readInput(),lunar_year:annualDraft}); render();}
    catch(e) {error.textContent='查询失败：'+e.message;}
    finally {button.disabled=false;}
  });
  if (!annualResult) {append(result,'p','info-inline','选择目标农历年，查看其干四化在本命盘星曜中的位置。'); return;}
  meta(result,[`农历纪年 ${annualResult.lunar_year}`,`年干支 ${annualResult.year_pillar}`, annualResult.school]);
  const cards=append(result,'div','transform-grid');
  annualResult.transformations.forEach(t=>{
    const c=append(cards,'div','transform-card');
    append(c,'div','transform-type',t.type);append(c,'div','transform-star',t.star);
    append(c,'div','transform-palace',t.natal_palace+' · '+t.natal_branch);
  });
  annualResult.limitations.forEach(t=>note(result,t));
}
function renderBirthWindowSection(){
  append(result,'h4','subheading','出生时间误差采样 · 不确定时刻对照');
  append(result,'p','info-inline','以出生资料里的时间为中心，在前后误差区间中离散采样，列出实际出现的不同八字和命身宫。采样点之间仍可能存在未检测到的差异。');
  const row=append(result,'div','inline-control');
  const radius=createInput('前后误差（分钟）','number',String(windowDraft.radius),row);radius.min='5';radius.max='120';
  const spacing=createInput('采样间隔（分钟）','number',String(windowDraft.spacing),row);spacing.min='5';spacing.max='60';
  const go=append(row,'button',null,'采样计算');go.type='button';go.id='window-run';
  const msg=append(result,'p','inline-msg');
  go.addEventListener('click',async()=>{
    windowDraft={radius:Number(radius.value),spacing:Number(spacing.value)};
    go.disabled=true;msg.textContent='';
    try {windowResult=await postJSON('/api/birth-window',{birth:readInput(),uncertainty_minutes:windowDraft.radius,sample_every_minutes:windowDraft.spacing});render();}
    catch(e){windowResult=null;msg.textContent='采样失败：'+e.message;}
    finally{go.disabled=false;}
  });
  if(!windowResult)return;
  meta(result,[`采样点 ${windowResult.sample_count}`,`观测到 ${windowResult.variant_count} 种结构`]);
  const table=append(append(result,'div','table-wrap'),'table','data-table');
  const tr=append(append(table,'thead'),'tr');
  ['四柱（年/月/日/时）','命身宫','观测样本范围','样本数'].forEach(t=>append(tr,'th',null,t));
  const body=append(table,'tbody');
  windowResult.variants.forEach(v=>{
    const row=append(body,'tr');
    append(row,'td',null,Object.values(v.pillars).join(' / '));
    append(row,'td',null,v.ming_palace+'/'+v.shen_palace);
    append(row,'td',null,v.first_sample_local.replace('T',' ')+' → '+v.last_sample_local.replace('T',' '));
    append(row,'td',null,v.sample_count);
  });
  windowResult.limitations.forEach(t=>note(result,t));
}
function renderTimeAudit() {
  title(result,'出生时间与经度审计','比较三种时制 / 相同天文瞬间');
  const inp=readInput();
  append(result,'p','info-inline','填写出生地经度后，计算钟表时间、地方平太阳时、真太阳时的四柱与命身宫差异。');
  const row=append(result,'div','inline-control');
  const run=append(row,'button',null,'计算时制对照');run.id='time-run';run.type='button';
  const error=append(result,'p','inline-msg');
  run.addEventListener('click',async()=>{
    if(readInput().longitude===null){error.textContent='请先在出生资料里填写出生地经度。';return;}
    run.disabled=true;
    try{timeResult=await postJSON('/api/time-audit',{birth:readInput()});render();}
    catch(e){error.textContent='计算失败：'+e.message;}
    finally{run.disabled=false;}
  });
  renderBirthWindowSection();
  if(!timeResult){append(result,'p','info-inline','不会自动保存出生资料或经度；审计结果包含具体时差与命盘差异。');return;}
  const wrap=append(result,'div','table-wrap'); const table=append(wrap,'table','data-table');
  const tr=append(append(table,'thead'),'tr');
  ['时基','有效当地时间','相对钟表偏移','四柱','命宫 / 身宫'].forEach(t=>append(tr,'th',null,t));
  const body=append(table,'tbody');
  timeResult.choices.forEach(t=>{
    const row=append(body,'tr');
    append(row,'td',null,({clock:'钟表时间',mean_solar:'平太阳时',apparent_solar:'真太阳时'})[t.mode]);
    append(row,'td',null,t.effective_reading.replace('T',' '));
    append(row,'td',null,t.shift_minutes.toFixed(2)+' 分钟');
    append(row,'td',null,Object.values(t.pillars).join(' / '));
    append(row,'td',null,t.ming_palace+' / '+t.shen_palace);
  });
  title(result,'规则敏感性比较','固定出生参数，仅切换时制');
  const choose=append(result,'div','inline-control');
  const label=append(choose,'label',null,'作为对照的时制');
  const select=append(label,'select');select.id='rule-alt-mode';
  [['clock','钟表时间'],['mean_solar','平太阳时'],['apparent_solar','真太阳时']].forEach(([mode,name])=>{let o=append(select,'option',null,name);o.value=mode;});
  const compare=append(choose,'button',null,'执行规则差异对照');compare.id='compare-rules';compare.type='button';
  const msg=append(result,'p','inline-msg');
  compare.addEventListener('click',async()=>{
    compare.disabled=true;
    try{
      const orig=readInput();const alt={...orig,time_mode:select.value};
      const out=await postJSON('/api/rules-compare',{original:orig,alternative:alt});
      msg.textContent='变化的四柱：'+(out.differences.pillars.map(k=>nameMap[k]).join('、')||'无')+
        '；命宫：'+(out.differences.ming?'变化':'不变')+'；身宫：'+(out.differences.shen?'变化':'不变')+'。';
    }catch(e){msg.textContent=e.message;}finally{compare.disabled=false;}
  });
  timeResult.warnings.forEach(t=>note(result,t));
}
function renderQualityAudit() {
  title(result, '出生记录与排盘质量审计', '节令 / 时辰 / 公历日界 / 远期历法不确定性');
  append(result, 'p', 'info-inline', '本工具只标记数据与计算边界，不替代权威历书或完整紫微流派审查。');
  const control = append(result, 'div', 'inline-control');
  const minutes = createInput('边界敏感窗口（分钟）', 'number', '15', control);
  minutes.min = '1'; minutes.max = '1440'; minutes.id = 'quality-minutes'; minutes.value = String(qualityMinutesDraft);
  const run = append(control, 'button', null, '核验输入与边界'); run.type = 'button'; run.id = 'quality-run';
  const msg = append(result, 'p', 'inline-msg');
  run.addEventListener('click', async () => {
    run.disabled = true; msg.textContent = '';
    try {
      const value = Number(minutes.value);
      qualityMinutesDraft = value;
      qualityResult = await postJSON('/api/quality-audit', {birth:readInput(), boundary_window_minutes:value});
      render();
    } catch(e) {msg.textContent = '核验失败：' + e.message;}
    finally {run.disabled = false;}
  });
  if (!qualityResult) {append(result, 'p', 'info-inline', '选择核验后列出实测四柱、日期、节令距离和需要复核的输入假设。');return;}
  const q = qualityResult;
  meta(result,[q.review_needed?'存在需人工核对的边界':'未发现当前规则已知边界问题',
      '有效时间 '+q.calculation_snapshot.effective_traditional_time.replace('T',' '),
      '年/月/日/时 '+Object.values(q.calculation_snapshot.bazi_pillars).join('/')]);
  rules(result,[
    {label:'距上一节令',value:q.calculation_snapshot.minutes_since_previous_jie.toFixed(1)+' 分'},
    {label:'距下一节令',value:q.calculation_snapshot.minutes_until_next_jie.toFixed(1)+' 分'},
    {label:'距时辰交界',value:q.calculation_snapshot.minutes_to_nearest_hour_boundary.toFixed(1)+' 分'},
    {label:'距换日交界',value:q.calculation_snapshot.minutes_to_day_boundary.toFixed(1)+' 分'},
  ]);
  if(q.calculation_snapshot.china_reference_lunar_date &&
     q.calculation_snapshot.china_reference_gregorian_date !== q.calculation_snapshot.local_effective_gregorian_date){
    const chinese=q.calculation_snapshot.china_reference_lunar_date;
    append(result,'div','feature-note',
      '时区日界对照：出生地有效日期 '+q.calculation_snapshot.local_effective_gregorian_date+
      '；同一瞬间北京日期 '+q.calculation_snapshot.china_reference_gregorian_date+
      '（农历 '+chinese.year+'年'+chinese.month+'月'+chinese.day+'日）。这不自动改变原命盘。');
  }
  const box = append(result,'div','reading-list');
  if(!q.flags.length) append(box,'p','info-inline','没有触发本工具已知边界标记；不代表专业命盘获得认证。');
  q.flags.forEach(f => {
    const entry = append(box,'section','report-section');
    append(entry,'h4','subheading',(f.severity==='review'?'需要复核':'背景信息')+' · '+f.code);
    append(entry,'p',null,f.detail);
    if(f.reference){const a=append(entry,'a',null,'打开参考来源 ↗');a.href=f.reference;a.target='_blank';a.rel='noopener noreferrer';}
  });
  q.limitations.forEach(x=>note(result,x));
}
function renderDeep() {
  title(result, '深度证据 · 跨体系结构审计', '确切计算字段 · 公开规则链接 · 内部反证检查');
  append(result,'p','info-inline','本页面不调用大模型预测，只展示八字、部分紫微的可计算结构与规则差异。方法参考链接不能代表对这张盘的外部验算。');
  if(!current){append(result,'p','info-inline','请先生成出生盘。');return;}
  const bar=append(result,'div','inline-control');
  const palaceLabel=append(bar,'label',null,'关注宫位');
  const palace=append(palaceLabel,'select');palace.id='deep-palace';
  ['命宫','兄弟宫','夫妻宫','子女宫','财帛宫','疾厄宫','迁移宫','仆役宫','官禄宫','田宅宫','福德宫','父母宫'].forEach(name=>{
    const opt=append(palace,'option',null,name);opt.value=name;
  });palace.value=deepDraft.focus_palace;
  const year=createInput('可选农历年份','number',deepDraft.lunar_year,bar);year.id='deep-year';year.min='1901';year.max='2099';
  const question=createInput('研究问题（可选，最多 200 字）','text',deepDraft.question,bar);question.id='deep-question';question.maxLength=200;
  const run=append(bar,'button',null,'执行证据分析');run.type='button';run.id='deep-run';
  const msg=append(result,'p','inline-msg');
  run.addEventListener('click',async()=>{
    const y=year.value.trim();
    if(y && (!/^[0-9]{4}$/.test(y)||Number(y)<1901||Number(y)>2099)){msg.textContent='农历年份必须是 1901–2099';return;}
    deepDraft={focus_palace:palace.value,lunar_year:y,question:question.value.trim()};
    run.disabled=true;msg.textContent='';
    try{
      deepResult=await postJSON('/api/deep-review',{birth:readInput(),focus_palace:deepDraft.focus_palace,
        lunar_year:y?Number(y):null, question:deepDraft.question||null,include_quality:true});
      render();
    }catch(e){msg.textContent='分析失败：'+e.message;}
    finally{run.disabled=false;}
  });
  if(!deepResult)return;
  meta(result,[`关注 ${deepResult.focus_palace}`,`${deepResult.findings.length} 组可追溯观察`,`${deepResult.checks.filter(c=>c.passed).length}/${deepResult.checks.length} 条内部一致性检查`]);
  deepResult.findings.forEach(f=>{
    const panel=append(result,'section','report-section');
    append(panel,'h4','subheading',f.title);
    append(panel,'p','feature-note',f.observation);
    const paths=append(panel,'div','small-text');
    append(paths,'strong',null,'计算字段：');
    append(paths,'span',null,f.evidence.map(x=>x.path).join(' · '));
    append(panel,'p','disclaimer','适用边界：'+f.limit);
    append(panel,'p','feature-note','规则 ID：'+f.rule_ids.join('、'));
  });
  append(result,'h4','subheading','内部一致性核查（不等于外部准确率认证）');
  deepResult.checks.forEach(c=>append(result,'p','feature-note',(c.passed?'✓':'⚠')+' '+c.meaning));
  append(result,'h4','subheading','参考来源与适用范围');
  deepResult.references.forEach(ref=>{
    const row=append(result,'p','feature-note');
    append(row,'strong',null,ref.title+'：');
    if(ref.reference.startsWith('https://')){
      const a=append(row,'a',null,'查看公开方法文档');a.href=ref.reference;a.target='_blank';a.rel='noopener noreferrer';
    } else append(row,'span',null,ref.reference);
    append(row,'span',null,' · '+ref.scope);
  });
  const save=append(result,'button','tiny-button','导出带证据的 Markdown ↓');save.type='button';save.id='deep-download';
  save.addEventListener('click',()=>{
    const blob=new Blob([deepResult.markdown],{type:'text/markdown;charset=utf-8'});
    const url=URL.createObjectURL(blob);const a=elt('a');a.href=url;a.download='xuanshu-evidence.md';
    document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);
  });
  deepResult.limitations.forEach(text=>note(result,text));
}

function renderReport() {
  title(result, '可追溯综合报告', '独立八字、紫微计算 → 可选年干四化和太阳时审计 → Markdown');
  if (!current) {append(result,'p','info-inline','请先生成出生盘，再生成综合报告。');return;}
  const formRow = append(result, 'div', 'inline-control');
  const year = createInput('叠加农历年（留空不叠加）', 'number', reportDraft.lunar_year === null ? '' : String(reportDraft.lunar_year), formRow);
  year.min = '1901';year.max='2099';year.id='report-year';
  const label=append(formRow,'label',null,'同时运行三种时制审计');
  const audit=append(label,'input');audit.type='checkbox';audit.id='report-audit'; audit.checked = reportDraft.include_time_audit;
  const dylabel=append(formRow,'label',null,'同时加入十年干支大运');
  const dy=append(dylabel,'input');dy.type='checkbox';dy.id='report-dayun';dy.checked=reportDraft.include_dayun;
  const evidenceLabel=append(formRow,'label',null,'加入证据溯源与跨体系规则复核');
  const evidenceBox=append(evidenceLabel,'input');evidenceBox.type='checkbox';evidenceBox.id='report-deep';evidenceBox.checked=reportDraft.include_deep_evidence;
  const dyselectlabel=append(formRow,'label',null,'大运方向（默认自动）');
  const dyselect=append(dyselectlabel,'select');dyselect.id='report-dayun-direction';
  [['','自动'],['forward','顺排'],['reverse','逆排']].forEach(([v,t])=>{const op=append(dyselect,'option',null,t);op.value=v;});dyselect.value=reportDraft.dayun_direction_override;
  const bd=createInput('临界地图（±分钟；留空不包含）','number',String(reportDraft.birth_boundary_minutes),formRow);
  bd.id='report-boundary-radius';bd.min='1';bd.max='120';
  const go=append(formRow,'button',null,'生成综合报告');go.type='button';go.id='report-run';
  const error=append(result,'p','inline-msg');
  go.addEventListener('click',async()=>{
    if (audit.checked && readInput().longitude===null){error.textContent='时制审计必须填写出生地经度。';return;}
    const value=year.value.trim();
    const lunar_year=value===''?null:Number(value);
    const boundary_minutes=bd.value.trim()===''?null:Number(bd.value);
    if(boundary_minutes!==null && (!Number.isInteger(boundary_minutes)||boundary_minutes<1||boundary_minutes>120)){
      error.textContent='临界地图分钟数必须为1–120整数';return;
    }
    if(dy.checked && readInput().gender==='unspecified' && !dyselect.value){error.textContent='大运方向需要指定性别或手动顺逆';return;}
    reportDraft={lunar_year,include_time_audit:audit.checked,include_dayun:dy.checked,include_deep_evidence:evidenceBox.checked,
      dayun_direction_override:dyselect.value,birth_boundary_minutes:bd.value.trim()};
    go.disabled=true;error.textContent='';
    try {reportResult=await postJSON('/api/report',{birth:readInput(),lunar_year,
      include_time_audit:audit.checked,include_dayun:dy.checked,include_deep_evidence:evidenceBox.checked,
      dayun_direction_override:dyselect.value||null,birth_boundary_minutes:boundary_minutes});render();}
    catch(e){error.textContent='生成失败：'+e.message;}
    finally{go.disabled=false;}
  });
  if(!reportResult){append(result,'p','info-inline','该报告由确定性规则工具编排生成，展示各步骤来源，不调用外部大语言模型，也不保存到服务器。');return;}
  meta(result,[reportResult.system,reportResult.version,`${reportResult.tool_trace.length} 次计算步骤`]);
  reportResult.sections.forEach(section=>{
    const panel=append(result,'section','report-section');
    append(panel,'h4','subheading',section.title);
    const ul=append(panel,'ul','reading-list');
    section.facts.forEach(f=>append(ul,'li',null,f));
    append(panel,'p','feature-note','计算来源：'+section.provenance);
  });
  const download=append(result,'button','tiny-button','下载 Markdown 报告 ↓');download.type='button';download.id='report-download';
  download.addEventListener('click',()=>{
    const blob=new Blob([reportResult.markdown],{type:'text/markdown;charset=utf-8'});
    const url=URL.createObjectURL(blob);const a=elt('a');a.href=url;a.download='xuanshu-report.md';
    document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);
  });
  reportResult.limitations.forEach(x=>note(result,x));
}
function renderDayun() {
  title(result, '八字大运十年干支', '年干阴阳 + 性别或手动顺逆 · 十二节令 · 三日折一岁');
  append(result, 'p', 'info-inline', '只计算传统干支和名义起运年龄，公历时间为均值年近似，绝非对人生事件的预测。');
  if (!current) {append(result, 'p', 'info-inline', '请先生成出生盘。'); return;}
  const row=append(result,'div','inline-control');
  const periods=createInput('显示运柱数量（1–12）','number',String(dayunDraft.periods),row);
  periods.id='dayun-periods';periods.min='1';periods.max='12';
  const label=append(row,'label',null,'顺逆方向（默认年干/性别）');
  const direction=append(label,'select');direction.id='dayun-direction';
  [['','按传统规则自动'],['forward','手动顺排'],['reverse','手动逆排']].forEach(([key,val])=>{const op=append(direction,'option',null,val);op.value=key;});
  direction.value=dayunDraft.direction_override;
  const run=append(row,'button',null,'计算大运');run.id='dayun-run';run.type='button';
  const error=append(result,'p','inline-msg');
  run.addEventListener('click', async()=>{
    const count=Number(periods.value);if(!Number.isInteger(count)||count<1||count>12){error.textContent='显示数量必须是1–12的整数';return;}
    dayunDraft={periods:count,direction_override:direction.value};
    if(readInput().gender==='unspecified' && !direction.value){error.textContent='性别未指定时需要手动选择顺逆。';return;}
    run.disabled=true;error.textContent='';
    try{dayunResult=await postJSON('/api/dayun',{birth:readInput(),periods:count,direction_override:direction.value||null});render();}
    catch(e){error.textContent='计算失败：'+e.message;}finally{run.disabled=false;}
  });
  if(!dayunResult)return;
  const d=dayunResult;
  meta(result,[`年柱 ${d.natal_year_pillar}`,`月柱 ${d.natal_month_pillar}`,`方向 ${d.direction==='forward'?'顺排':'逆排'}`,`起运约 ${d.start_age_traditional_parts.years}岁 ${d.start_age_traditional_parts.months}月`]);
  rules(result,[
    {label:'所选节令',value:d.nearest_jie_used.name,detail:d.nearest_jie_used.instant},
    {label:'出生距节',value:d.birth_to_jie_days+' 日'},
    {label:'投影起始时间',value:d.approx_first_start_local.replace('T',' ')},
  ]);
  const table=append(append(result,'div','table-wrap'),'table','data-table');
  const head=append(append(table,'thead'),'tr');['次序','十年干支','名义起始年龄','近似起始公历','神煞'].forEach(x=>append(head,'th',null,x));
  const body=append(table,'tbody');
  d.periods.forEach(x=>{const tr=append(body,'tr');append(tr,'td',null,x.sequence);append(tr,'td',null,x.pillar);append(tr,'td',null,x.approx_start_age_years.toFixed(2));append(tr,'td',null,x.approx_start_local.replace('T',' '));append(tr,'td',null,(x.natal_interactions.shensha||[]).map(s=>s.name).join('、')||'—');});
  d.limitations.forEach(x=>note(result,x));
}
function renderBirthBoundaries(){
  title(result,'出生时刻临界地图','模型边界自动分段 · 精度约1秒 · 与抽样不同');
  append(result,'p','info-inline','识别时辰、日界、节令和时区变更。仅保证当前已实现规则的数值分段，不保证所有流派的专业命盘。');
  if(!current){append(result,'p','info-inline','请先生成出生盘。');return;}
  const row=append(result,'div','inline-control');
  const radius=createInput('出生时间前后误差（分钟）','number',String(boundaryDraft.uncertainty_minutes),row);
  radius.id='boundary-radius';radius.min='1';radius.max='120';
  const run=append(row,'button',null,'定位临界时刻');run.id='boundary-run';run.type='button';
  const error=append(result,'p','inline-msg');
  run.addEventListener('click', async()=>{
    const value=Number(radius.value);if(!Number.isInteger(value)||value<1||value>120){error.textContent='误差范围必须是1–120的整数';return;}
    boundaryDraft={uncertainty_minutes:value};run.disabled=true;error.textContent='';
    try{boundaryResult=await postJSON('/api/birth-boundaries',{birth:readInput(),uncertainty_minutes:value});render();}
    catch(e){error.textContent='查询失败：'+e.message;}finally{run.disabled=false;}
  });
  if(!boundaryResult)return;
  const d=boundaryResult;
  meta(result,[`检测区间 ±${d.uncertainty_minutes}分钟`,`${d.boundaries.length}个边界`,`${d.segments.length}个区间`]);
  append(result,'h4','subheading','检出的规则切换点');
  if(!d.boundaries.length)append(result,'p','info-inline','当前模型在此检查范围内未检出时辰、日界、节令或时区变更。');
  d.boundaries.forEach(b=>append(result,'div','feature-note',`${b.local.replace('T',' ')} · ${b.types.join(' / ')}`));
  append(result,'h4','subheading','各区间代表命盘');
  const table=append(append(result,'div','table-wrap'),'table','data-table');
  const hr=append(append(table,'thead'),'tr');['UTC 区间起点','代表本地时刻','四柱','紫微命/身宫'].forEach(x=>append(hr,'th',null,x));
  const body=append(table,'tbody');
  d.segments.forEach(x=>{const tr=append(body,'tr');append(tr,'td',null,x.start_utc_inclusive.replace('T',' '));append(tr,'td',null,x.sample_local.replace('T',' '));append(tr,'td',null,Object.values(x.bazi_pillars).join(' / '));append(tr,'td',null,x.ziwei_ming_palace+'/'+x.ziwei_shen_palace);});
  d.limitations.forEach(x=>note(result,x));
}
function renderIntegration() {
  title(result,'Agent 接入中心','统一 MCP 服务 / 计算 Tool / 方法资源');
  append(result,'p','info-inline','本项目兼容 MCP 2026-07-28 和旧版 2025 协议的 stdio / Streamable HTTP；本地 Web 运行不等于已上线公网或已登记到 ChatGPT/Claude。');
  rules(result,[
    {label:'MCP 工具',value:'25 Tools',detail:'八字 / 紫微 / 历法 / 双盘 / 时间审计 / 年干四化'},
    {label:'规则资源',value:'17 Resources',detail:'方法规则、隐私和限制说明'},
    {label:'Agent Skills',value:'18 Skills',detail:'放在源码 skills/ 目录'},
    {label:'提示模板',value:'15 Prompts',detail:'可复用计算工作流'},
  ]);
  append(result,'h4','subheading','本地 HTTP 端点');
  const origin = location.origin==='null' ? 'http://127.0.0.1:8000' : location.origin;
  append(result,'pre','json-code','POST '+origin+'/mcp\nGET  '+origin+'/docs\nGET  '+origin+'/api/capabilities');
  append(result,'h4','subheading','Claude / Codex stdio 示例');
  const windows = /Windows/i.test(navigator.userAgent);
  const projectPath=windows ? 'C:\\path\\to\\xuanshu' : '/path/to/xuanshu';
  const pythonPath=windows ? projectPath+'\\.venv\\Scripts\\python.exe' : projectPath+'/.venv/bin/python';
  const snippet=JSON.stringify({mcpServers:{xuanshu:{command:pythonPath,args:['-m','app.stdio'],env:{PYTHONPATH:projectPath}}}},null,2);
  append(result,'pre','json-code',snippet);
  const copy=append(result,'button','tiny-button','复制 Claude / Codex 本地配置');
  copy.type='button';copy.id='integration-copy';
  copy.addEventListener('click',async()=>{
    try{
      await navigator.clipboard.writeText(snippet);
      copy.textContent='已复制，记得替换项目实际路径';
    }catch(e){copy.textContent='无法自动复制，请手动选中上面的配置文本';}
  });
  append(result,'p','small-text','将配置中的占位路径替换成你自己的项目路径。运行 Python 的虚拟环境必须先安装项目依赖。');
  append(result,'div','feature-note','公网接入必须单独部署 HTTPS、配置安全令牌/宿主支持的鉴权方式，并由用户在宿主平台进行连接授权。当前尚未自动注册插件。');
}
function jsonData() {
  return {birth_hour_unknown:currentHourUnknown, pillar_search:pillarResult, chart_import_check:importResult, date_scan:dateScanResult, consultation:consultResult, qimen:qimenResult, qimen_reference_audit:referenceAuditResult,ziwei_professional:professionalResult, ziwei_horoscope:horoscopeResult, bazi_dayun:dayunResult, birth_boundaries:boundaryResult, day_officers:officerResult, annual_timeline:timelineResult, decision_matrix:decisionResult, chart: current, calendar: calendarResult, lunar_inverse: lunarInverseResult, pair: pairResult, ziwei_pair: pairZiweiResult, group_relations: groupResult, rule_matrix: ruleMatrixResult, annual: annualResult, time_audit: timeResult, birth_window: windowResult, report: reportResult, quality_audit: qualityResult};
}
function renderConsultation() {
  title(result, '问题驱动咨询工作流', '真实执行工具 · 保留证据来源 · 不在服务器保存对话');
  note(result, '这是确定性工具编排，不是自主 LLM。不会根据传统命盘给出人生成功率或虚构事件。');
  const area=append(result,'div','result-card');
  const label=append(area,'label',null,'你现在想研究什么问题？'); label.htmlFor='consult-question';
  const question=append(area,'textarea');question.id='consult-question'; question.rows=3;
  question.maxLength=600;question.value=consultDraft.question;
  const shortcuts=append(area,'div','consult-shortcuts');
  append(shortcuts,'span','small-text','常见咨询问题：');
  const examples=[
    ['本命概览','natal','请按传统八字和紫微规则整理我的本命结构，并标明计算依据。'],
    ['年度事业','career',`${new Date().getFullYear()+1} 年我的事业选择可从哪些传统结构和现实约束分析？`],
    ['双人关系','relationship','请比较两个人的传统命盘结构，列出共同点与差异。'],
    ['候选择时','timing','我有几个候选时间，请比较传统择时标签和现实限制。'],
    ['方案对照','decision','请比较几个真实可行的方案，列出不同权重下的优缺点。']
  ];
  examples.forEach(([label,value,example])=>{
    const item=append(shortcuts,'button','tiny-button',label);item.type='button';
    item.addEventListener('click',()=>{
      question.value=example;
      intent.value=value;
      consultDraft.question=example;
      consultDraft.intent=value;
      question.focus();
    });
  });
  const controls=append(area,'div','inline-control');
  const intentLabel=append(controls,'label',null,'问题场景');
  const intent=append(intentLabel,'select');intent.id='consult-intent';
  [['auto','自动识别'],['natal','本命分析'],['career','事业/年度'],['relationship','双人关系'],['timing','多时刻查询'],['decision','方案比较'],['rules','规则分歧']].forEach(([value,text])=>{const opt=append(intent,'option',null,text);opt.value=value;});
  intent.value=consultDraft.intent;
  const year=createInput('农历年（选填）','number',consultDraft.lunarYear,controls);year.id='consult-year';year.min='1901';year.max='2099';
  const bl=append(controls,'label',null,'本次允许使用出生资料');
  const birthCheck=append(bl,'input');birthCheck.type='checkbox';birthCheck.id='consult-use-birth';birthCheck.checked=consultDraft.useBirth;
  const advanced=append(area,'details','consult-advanced');advanced.id='consult-advanced';advanced.open=consultAdvancedOpen;
  append(advanced,'summary',null,'更多咨询选项：合盘、候选日期、现实条件和完整报告');
  advanced.addEventListener('toggle',()=>{consultAdvancedOpen=advanced.open;});
  const advancedControls=append(advanced,'div','inline-control');
  const partnerLabel=append(advancedControls,'label',null,'使用第二人出生资料（自愿）');
  const partnerCheck=append(partnerLabel,'input');partnerCheck.type='checkbox';partnerCheck.id='consult-use-partner';partnerCheck.checked=consultDraft.usePartner;
  const partnerDate=createInput('第二人时间（当地）','datetime-local',consultDraft.partnerDate,advancedControls);partnerDate.id='consult-partner-date';
  const candidateLabel=append(advancedControls,'label',null,'多个候选时刻：每行一个 ISO 本地时间（最多5个）');
  const candidates=append(candidateLabel,'textarea');candidates.rows=2;candidates.id='consult-candidates';candidates.value=consultDraft.candidateDates;
  const factLabel=append(advancedControls,'label',null,'现实条件或目标（选填；每行一条，最多8条；仅本次使用）');
  const facts=append(factLabel,'textarea');facts.rows=3;facts.id='consult-real-world-facts';facts.value=consultDraft.facts;
  const fullLabel=append(advancedControls,'label',null,'同时生成完整技术报告');
  const full=append(fullLabel,'input');full.type='checkbox';full.id='consult-full-report';full.checked=consultDraft.includeReport;
  // Preserve unsent edits while switching tools; only in-memory, never uploaded.
  const preserveDraft=()=>{
    consultDraft={
      question:question.value, intent:intent.value, useBirth:birthCheck.checked,
      usePartner:partnerCheck.checked,partnerDate:partnerDate.value,
      lunarYear:year.value,candidateDates:candidates.value,
      facts:facts.value,includeReport:full.checked
    };
  };
  [question,intent,year,birthCheck,partnerCheck,partnerDate,candidates,facts,full].forEach(control=>{
    control.addEventListener('input',preserveDraft);
    control.addEventListener('change',preserveDraft);
  });
  const launch=append(area,'button','primary-btn','执行咨询工作流');launch.type='button';launch.id='consult-run';
  const feedback=append(area,'p','inline-msg');feedback.id='consult-feedback';
  launch.addEventListener('click', async()=>{
    consultDraft={question:question.value,intent:intent.value,useBirth:birthCheck.checked,usePartner:partnerCheck.checked,partnerDate:partnerDate.value,lunarYear:year.value,candidateDates:candidates.value,facts:facts.value,includeReport:full.checked};
    if(!question.value.trim()){feedback.textContent='请输入具体问题';return;}
    const payload={question:question.value,intent:intent.value};
    if(birthCheck.checked)payload.birth=readInput();
    if(partnerCheck.checked){if(!birthCheck.checked||!partnerDate.value){feedback.textContent='合盘需要勾选使用出生资料，并填写第二人的当地出生时间';return;}
      payload.partner={birth_datetime:partnerDate.value,timezone:$('#timezone').value,gender:'unspecified'};payload.partner_authorized=true;
    }
    if(year.value.trim())payload.lunar_year=Number(year.value);
    if(candidates.value.trim()){
      const values=candidates.value.split('\n').map(x=>x.trim()).filter(Boolean);
      if(values.length>5){feedback.textContent='候选时刻最多5个';return;}
      payload.candidate_times=values.map(v=>({birth_datetime:v,timezone:$('#timezone').value}));
    }
    if(facts.value.trim()){const items=facts.value.split('\n').map(v=>v.trim()).filter(Boolean);
      if(items.length>8||items.some(x=>x.length>220)){feedback.textContent='现实条件最多8条，每条不超过220字';return;}
      payload.real_world_facts=items.map(statement=>({category:'constraint',statement}));
    }
    if(full.checked&&birthCheck.checked)payload.include_full_report=true;
    if(consultCursor)payload.continuation=consultCursor;
    launch.disabled=true; feedback.textContent='正在按问题调用计算工具…';
    try{consultResult=await postJSON('/api/consultation',payload);consultCursor=consultResult.continuation;render();}
    catch(e){feedback.textContent='执行失败：'+e.message;}
    finally{launch.disabled=false;}
  });
  if(!consultResult)return;
  meta(result,['场景 '+consultResult.intent,'状态 '+consultResult.status,consultResult.tool_trace.length+' 步实算','服务器不保存本次资料']);
  append(result,'h4','subheading','执行轨迹');
  consultResult.tool_trace.forEach(x=>{const row=append(result,'p','feature-note');append(row,'strong',null,x.step+'. '+x.tool+'：');append(row,'span',null,x.purpose);});
  if(consultResult.missing_inputs.length){append(result,'h4','subheading','需要补充');consultResult.missing_inputs.forEach(x=>append(result,'p','disclaimer',x.field+' · '+x.reason));}
  append(result,'h4','subheading','可核验观察');
  consultResult.observations.forEach(x=>{const row=append(result,'section','report-section');append(row,'p','feature-note',x.text);append(row,'p','small-text','来源：'+x.tool+' · '+x.path);if(x.limit)append(row,'p','disclaimer',x.limit);});
  const copyBtn=append(result,'button','tiny-button','复制咨询报告 Markdown');copyBtn.type='button';copyBtn.id='consult-copy-markdown';
  copyBtn.addEventListener('click',async()=>{
    try {await navigator.clipboard.writeText(consultResult.markdown);copyBtn.textContent='已复制报告';}
    catch (_) {copyBtn.textContent='复制失败，请使用旁边的下载功能';}
  });
  const exportBtn=append(result,'button','tiny-button','导出咨询报告 Markdown ↓');exportBtn.type='button';
  exportBtn.addEventListener('click',()=>{const blob=new Blob([consultResult.markdown],{type:'text/markdown;charset=utf-8'});const url=URL.createObjectURL(blob);const a=elt('a');a.href=url;a.download='xuanshu-consultation.md';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);});
  consultResult.limitations.forEach(x=>note(result,x));
}

function renderJson() {
  const h = append(result, 'div', 'code-header');
  append(h, 'h3', null, '结构化 JSON · 可供 MCP / REST 读取');
  const btn = append(h, 'button', 'tiny-button', '复制 JSON'); btn.type = 'button';
  btn.addEventListener('click', () => navigator.clipboard.writeText(JSON.stringify(jsonData(), null, 2))
    .then(() => {btn.textContent = '已复制';}).catch(() => {btn.textContent = '复制失败';}));
  append(result, 'pre', 'json-code', JSON.stringify(jsonData(), null, 2));
}
// Rebuilding the result area must not lose the user's place: keyboard focus,
// caret position and which collapsible sections were open survive a re-render.
function render() {
  const focused = result.contains(document.activeElement) ? document.activeElement : null;
  const focusId = focused && focused.id;
  const caret = focusId && typeof focused.selectionStart === 'number' ? [focused.selectionStart, focused.selectionEnd] : null;
  const detailKey = d => d.id || (d.querySelector('summary') || {}).textContent || '';
  const openState = new Map([...result.querySelectorAll('details')].map(d => [detailKey(d), d.open]));
  renderView();
  result.querySelectorAll('details').forEach(d => {const key = detailKey(d); if (openState.has(key)) d.open = openState.get(key);});
  if (focusId && !result.contains(document.activeElement)) {
    let again = document.getElementById(focusId);
    if (again && again.disabled && again.dataset.focusFallback) again = document.getElementById(again.dataset.focusFallback);
    if (again && !again.disabled) {
      again.focus({preventScroll: true});
      if (caret && again.setSelectionRange) try {again.setSelectionRange(caret[0], caret[1]);} catch (_) { /* not a text field */ }
    }
  }
}
function renderView() {
  clear();
  if (active === 'chat') return renderChat();
  if (active === 'consult') return renderConsultation();
  if (active === 'qimen') return renderQimen();
  if (active === 'professional') return renderProfessionalZiwei();
  if (active === 'qimen-audit') return renderQimenAudit();
  if (active === 'dayun') return renderDayun();
  if (active === 'boundaries') return renderBirthBoundaries();
  if (active === 'calendar') return renderCalendar();
  if (active === 'officers') return renderDayOfficers();
  if (active === 'date-scan') return renderDateScan();
  if (active === 'timeline') return renderTimeline();
  if (active === 'decision') return renderDecision();
  if (active === 'pair') return renderPair();
  if (active === 'group') return renderGroup();
  if (active === 'integration') return renderIntegration();
  if (active === 'time') return renderTimeAudit();
  if (active === 'annual') return renderAnnual();
  if (active === 'quality') return renderQualityAudit();
  if (active === 'report') return renderReport();
  if (active === 'deep') return renderDeep();
  if (active === 'pillar-search') return renderPillarSearch();
  if (active === 'import-check') return renderImportCheck();
  if (active === 'today') return renderToday();
  if (!current) {
    const empty = append(result, 'div', 'empty-state');
    append(empty, 'div', 'empty-orbit', '☯');
    append(empty, 'h3', null, '历法可核验，规则可追溯');
    append(empty, 'p', null, '确认出生资料后生成命盘，八字、紫微和四化会一起算好。');
    const go = append(empty, 'button', 'tiny-button', '用当前出生资料生成命盘'); go.type = 'button'; go.id = 'empty-generate';
    go.addEventListener('click', () => form.requestSubmit());
    return;
  }
  if (active === 'rule-matrix') return renderRuleMatrix();
  if (currentHourUnknown && (active === 'bazi' || active === 'ziwei')) renderHourUnknown(result);
  if (active === 'bazi') renderBazi(current.bazi);
  else if (active === 'ziwei') renderZiwei(current.ziwei);
  else if (active === 'transform') renderTransform(current.ziwei);
  else if (active === 'reading') renderReading(current.reading);
  else renderJson();
}
// The URL identifies only the selected tool; it never stores a birth date.
function tabFromHash() {
  const match = /^#tool=([a-z-]+)$/.exec(location.hash);
  return match ? tabs.find(tab => tab.dataset.tab === match[1]) : null;
}
tabs.forEach(tab => {tab.id = 'tab-' + tab.dataset.tab; tab.setAttribute('aria-controls', 'result');});
function activateTab(tab, updateUrl = true) {
  if (!tab) return;
  active = tab.dataset.tab;
  result.setAttribute('aria-labelledby', tab.id);
  tabs.forEach(other => {
    const selected = other === tab;
    other.classList.toggle('active', selected);
    other.setAttribute('aria-selected', String(selected));
    other.tabIndex = selected ? 0 : -1;
  });
  if (updateUrl && /^https?:$/.test(location.protocol)) {
    history.replaceState(null, '', '#tool=' + active);
  }
  updateToolNavigation();
  render();
}
tabs.forEach(tab => tab.addEventListener('click', () => activateTab(tab)));
$('#workspace-tabs').addEventListener('keydown', event => {
  if (!['ArrowRight','ArrowLeft','Home','End'].includes(event.key) || !event.target.classList.contains('tab')) return;
  event.preventDefault();
  const available = tabs.filter(tab => !tab.hidden);
  const index = available.indexOf(event.target);
  if (index < 0 || !available.length) return;
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? available.length-1
    : (index + (event.key === 'ArrowRight' ? 1 : -1) + available.length) % available.length;
  activateTab(available[next]);
  available[next].focus();
});
document.addEventListener('keydown', event => {
  if ((event.ctrlKey || event.metaKey) && !event.altKey && event.key.toLowerCase() === 'k' && event.target.tagName !== 'TEXTAREA') {
    event.preventDefault();
    $('#tool-search').focus();
    $('#tool-search').select();
  }
});
window.addEventListener('hashchange', () => {
  const tab = tabFromHash();
  if (tab && tab.dataset.tab !== active) activateTab(tab, false);
});
// Keep old results visible for reference, but mark them as stale and
// disable export when the user edits any birth parameter.
function updateStaleBirthNotice() {
  const fingerprint=JSON.stringify(readInput());
  const outdatedChart=!!currentInput && fingerprint !== JSON.stringify(currentInput);
  const outdatedQimen=!!qimenResult && !!qimenFingerprint && fingerprint !== qimenFingerprint;
  const outdated=outdatedChart || outdatedQimen || dateScanStale();
  $('#stale-birth-warning').hidden = !outdated;
  if (outdated) {
    $('#result-subtitle').textContent = '出生资料已更改：旧命盘需要重新生成';
    $('#download-json').disabled = true;
  } else if (currentInput) {
    $('#result-subtitle').textContent = currentInput.birth_datetime.replace('T',' ') + ' · ' + currentInput.timezone;
    $('#download-json').disabled = false;
  }
}
for (const type of ['input','change']) {
  form.addEventListener(type, event => {
    if (event.target.id !== 'api_token') updateStaleBirthNotice();
  });
}
form.addEventListener('submit', async event => {
  event.preventDefault();
  const run = $('#run-btn'); const error = $('#error');
  error.hidden = true; run.disabled = true; run.querySelector('span').textContent = '正在计算…';
  const data = readInput();
  try {
    const [chart, reading] = await Promise.all([
      postJSON('/api/combined', data), postJSON('/api/analyze', data),
    ]);
    current = {...chart, reading}; currentInput = data;
    consultResult=null;consultCursor=null;
    pairResult = null; pairZiweiResult = null; annualResult = null; timelineResult=null; timeResult = null; windowResult = null; reportResult = null; deepResult=null; qualityResult = null;
    dayunResult=null;boundaryResult=null;qimenResult=null;qimenFingerprint=null;professionalResult=null;referenceAuditResult=null;
    ruleMatrixResult = null; ruleMatrixKey = ''; ruleMatrixError = ''; groupResult = null; groupKey = null;
    // A group reply still on its way belongs to the previous chart.
    ++groupYearTicket; groupYearPending = false; groupYearError = ''; groupRun = null; groupRunError = ''; luckYearTyped = {};
    ++pairYearTicket; pairYearPending = false; pairYearError = ''; pairRunning = false; pairRunError = '';
    horoscopeResult = null; horoscopeKey = null; horoscopeError = ''; horoscopeResultKey = null;
    selectedPalace = '命宫'; ziweiLayer.decade = null; currentHourUnknown = $('#hour_unknown').checked;
    $('#result-subtitle').textContent = data.birth_datetime.replace('T',' ') + ' · ' + data.timezone;
    $('#download-json').disabled = false;
    updateStaleBirthNotice();
    if (active === 'chat' && event.submitter && event.submitter.id === 'run-btn') activateTab(tabs.find(t => t.dataset.tab === 'bazi'));
    else render();
    announce('命盘已生成：' + data.birth_datetime.replace('T', ' '));
    if (compactScreen && compactScreen.matches) {setBirthPanelCollapsed(true); $('#workspace').scrollIntoView({block: 'start'});}
  } catch (err) {error.textContent = '计算失败：' + err.message; error.hidden = false;}
  finally {run.disabled = false; run.querySelector('span').textContent = '生成命盘';}
});
$('#download-json').addEventListener('click', () => {
  if (!current || (currentInput && JSON.stringify(readInput()) !== JSON.stringify(currentInput))) return;
  const blob = new Blob([JSON.stringify(jsonData(), null, 2)], {type: 'application/json;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  const anchor = elt('a'); anchor.href = url; anchor.download = 'xuanshu-' + currentInput.birth_datetime.slice(0,10) + '.json';
  document.body.append(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
});
function loadProfiles() {
  try {
    const data = JSON.parse(localStorage.getItem(profileKey) || '[]');
    return Array.isArray(data) ? data.filter(x => x && typeof x.id === 'string' && typeof x.label === 'string' && x.data && typeof x.data === 'object').slice(0,20) : [];
  } catch (_) {return [];}
}
function setFeedback(text) {$('#profile-feedback').textContent = text;}
function showProfiles() {
  const select = $('#profiles'); const currentID = select.value;
  select.replaceChildren();
  const list = loadProfiles();
  if (!list.length) {const op = append(select, 'option', null, '暂无本地档案'); op.value = ''; return;}
  list.forEach(x => {const op = append(select, 'option', 'user-text', x.label); op.value = x.id;});
  if (list.some(x => x.id === currentID)) select.value = currentID;
}
$('#save-profile').addEventListener('click', () => {
  const label = $('#profile_name').value.trim();
  if (!label) {setFeedback('先填写档案标签'); return;}
  const profiles = loadProfiles();
  if (profiles.length >= 20) {setFeedback('最多保存 20 条，请先删除旧档案'); return;}
  const id = Date.now().toString(36) + '-' + Math.random().toString(36).slice(2,10);
  profiles.push({id, label, data: readInput(), hour_unknown: $('#hour_unknown').checked});
  try {localStorage.setItem(profileKey, JSON.stringify(profiles)); showProfiles(); $('#profiles').value = id; setFeedback('仅保存在当前浏览器。');}
  catch (_) {setFeedback('保存失败：当前浏览器无法使用本地存储');}
});
$('#load-profile').addEventListener('click', () => {
  const entry = loadProfiles().find(x => x.id === $('#profiles').value);
  if (!entry) {setFeedback('请选择有效档案'); return;}
  setInput(entry.data); $('#hour_unknown').checked = entry.hour_unknown === true; updateHourUnknown();
  setFeedback('已载入档案，正在计算。'); form.requestSubmit();
});
$('#remove-profile').addEventListener('click', () => {
  const chosen = $('#profiles').value;
  if (!chosen) {setFeedback('请选择要删除的档案'); return;}
  if (!confirm('删除所选档案？它在本机保存的对话、记忆和人生事件也会一起删除。')) return;
  try {localStorage.setItem(profileKey, JSON.stringify(loadProfiles().filter(x => x.id !== chosen))); showProfiles(); purgeChatStores(); setFeedback('已从本机浏览器删除所选档案及其对话、记忆和人生事件。'); if (active === 'chat') render();}
  catch (_) {setFeedback('删除失败：浏览器存储不可用');}
});
showProfiles();

// Unknown birth hour: cast the same day once per double hour and show what changes.
const HOUR_SAMPLES = [['早子', '00:30'], ['丑', '02:00'], ['寅', '04:00'], ['卯', '06:00'], ['辰', '08:00'], ['巳', '10:00'],
  ['午', '12:00'], ['未', '14:00'], ['申', '16:00'], ['酉', '18:00'], ['戌', '20:00'], ['亥', '22:00'], ['晚子', '23:30']];
// Clock time whose effective (solar-time) reading is `time` on `day`; shift is effective minus clock, in minutes.
function clockFor(day, time, shift) {
  const [y, m, d] = day.split('-').map(Number), [hh, mm] = time.split(':').map(Number);
  const at = new Date(Date.UTC(y, m - 1, d, hh, mm) - Math.round(shift) * 60000);
  const pad = n => String(n).padStart(2, '0');
  return `${at.getUTCFullYear()}-${pad(at.getUTCMonth() + 1)}-${pad(at.getUTCDate())}T${pad(at.getUTCHours())}:${pad(at.getUTCMinutes())}`;
}
async function loadHourCandidates(key) {
  const base = currentInput;
  const day = base.birth_datetime.slice(0, 10);
  const shift = (current.bazi.time_basis && current.bazi.time_basis.effective_shift_minutes) || 0;
  const rows = await Promise.all(HOUR_SAMPLES.map(async ([label, time]) => {
    const when = clockFor(day, time, shift);
    const chart = await postJSON('/api/combined', {...base, birth_datetime: when});
    const z = chart.ziwei, b = chart.bazi;
    const ming = z.palaces.find(p => p.is_ming);
    // Label each row from the hour the engine actually assigned, not from the sample.
    const branch = b.pillars.hour.branch;
    const name = branch === '子' ? (label === '晚子' ? '晚子' : '早子') : branch;
    return {label: name, time: when.slice(0, 10) === day ? when.slice(11) : when.replace('T', ' '), pillars: b.pillars,
      ming: z.ming_palace, shen: z.shen_palace, bureau: z.five_elements_bureau, ming_stars: ming ? ming.main_stars : []};
  }));
  hourCandidates = {key, rows};
}
function renderHourUnknown(parent) {
  const box = append(parent, 'section', 'hour-unknown');
  append(box, 'h4', null, '时辰不详：哪些部分不受时辰影响');
  const key = JSON.stringify(currentInput);
  if (!hourCandidates || hourCandidates.key !== key) {
    append(box, 'p', 'field-help', '下面的命盘按 12:00 占位。比较十二个时辰，可以看出哪些柱位和宫位在整天里都不变，哪些需要先确定时辰。');
    const run = append(box, 'button', 'tiny-button', '比较十二个时辰'); run.type = 'button'; run.id = 'hour-compare';
    const message = append(box, 'p', 'inline-msg');
    run.addEventListener('click', async () => {
      run.disabled = true; message.className = 'inline-msg progress'; message.textContent = '正在逐个时辰排盘…';
      try {await loadHourCandidates(key); render(); announce('十二时辰对照已生成');}
      catch (e) {message.className = 'inline-msg'; message.textContent = '比较失败：' + e.message; run.disabled = false;}
    });
    return;
  }
  const rows = hourCandidates.rows;
  const stable = append(box, 'div', 'stable-list');
  [['year', '年柱'], ['month', '月柱'], ['day', '日柱']].forEach(([key, name]) => {
    const values = [...new Set(rows.map(r => r.pillars[key].stem + r.pillars[key].branch))];
    append(stable, 'span', 'stable-tag ' + (values.length === 1 ? 'stable' : 'changing'),
      name + ' ' + values.join(' / ') + (values.length === 1 ? ' · 全天不变' : ' · 随时辰变化'));
  });
  const bureaus = [...new Set(rows.map(r => r.bureau))];
  append(stable, 'span', 'stable-tag changing', '时柱、紫微命宫 · 随时辰变化');
  append(stable, 'span', 'stable-tag ' + (bureaus.length === 1 ? 'stable' : 'changing'), '五行局 ' + bureaus.join(' / ') + (bureaus.length === 1 ? ' · 全天不变' : ' · 随时辰变化'));
  const table = append(append(box, 'div', 'table-wrap'), 'table', 'data-table');
  const head = append(append(table, 'thead'), 'tr');
  ['时辰', '钟表时间', '时柱', '日柱', '紫微命宫', '命宫主星', '身宫', '五行局'].forEach(x => append(head, 'th', null, x));
  const body = append(table, 'tbody');
  rows.forEach(r => {
    const tr = append(body, 'tr');
    [r.label, r.time, r.pillars.hour.stem + r.pillars.hour.branch, r.pillars.day.stem + r.pillars.day.branch, r.ming,
      r.ming_stars.join('、') || '空宫', r.shen, r.bureau].forEach((x, i) => append(tr, 'td', i === 2 ? 'pillar-cell' : null, x));
  });
  append(box, 'p', 'field-help', '想缩小范围，可以在「AI 对话」里讲几件确定发生过的大事，或用「生时边界地图」查看精确的切换时刻。');
}
const LUNAR_MONTHS = ['正月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '冬月', '腊月'];
const LUNAR_DAYS = ['初一','初二','初三','初四','初五','初六','初七','初八','初九','初十','十一','十二','十三','十四','十五',
  '十六','十七','十八','十九','二十','廿一','廿二','廿三','廿四','廿五','廿六','廿七','廿八','廿九','三十'];
const LUNAR_HOURS = [['', '时辰不详'], ['00:30', '早子时 00–01'], ['02:00', '丑时 01–03'], ['04:00', '寅时 03–05'], ['06:00', '卯时 05–07'],
  ['08:00', '辰时 07–09'], ['10:00', '巳时 09–11'], ['12:00', '午时 11–13'], ['14:00', '未时 13–15'], ['16:00', '申时 15–17'],
  ['18:00', '酉时 17–19'], ['20:00', '戌时 19–21'], ['22:00', '亥时 21–23'], ['23:30', '晚子时 23–24']];
function fillSelect(select, items) {
  items.forEach(([value, text]) => {const op = append(select, 'option', null, text); op.value = value;});
}
fillSelect($('#lunar_month'), LUNAR_MONTHS.map((name, i) => [String(i + 1), name]));
fillSelect($('#lunar_day'), LUNAR_DAYS.map((name, i) => [String(i + 1), name]));
fillSelect($('#lunar_hour'), LUNAR_HOURS);
$('#lunar_hour').value = '12:00';
$('#lunar-fill').addEventListener('click', async () => {
  const message = $('#lunar-msg'); const button = $('#lunar-fill');
  const request = {lunar_year: Number($('#lunar_year').value), lunar_month: Number($('#lunar_month').value),
    lunar_day: Number($('#lunar_day').value), is_leap_month: $('#lunar_leap').checked};
  button.disabled = true; message.className = 'inline-msg progress'; message.textContent = '正在换算…';
  try {
    const data = await postJSON('/api/lunar-to-gregorian', request);
    const hour = $('#lunar_hour').value;
    $('#birth_datetime').value = data.gregorian_date + 'T' + (hour || '12:00');
    $('#hour_unknown').checked = !hour;
    updateHourUnknown(); updateDemoBirthWarning(); updateBirthSummary(); updateStaleBirthNotice();
    message.className = 'inline-msg ok';
    message.textContent = '已填入公历 ' + data.gregorian_date + (hour ? ' ' + hour : '（时辰不详，按 12:00 占位）') + '，点「生成命盘」计算。';
  } catch (e) {message.className = 'inline-msg'; message.textContent = '换算失败：' + e.message;}
  finally {button.disabled = false;}
});
function updateHourUnknown() {$('#hour-unknown-help').hidden = !$('#hour_unknown').checked;}
$('#hour_unknown').addEventListener('change', () => {
  const box = $('#birth_datetime');
  if ($('#hour_unknown').checked && box.value) box.value = box.value.slice(0, 10) + 'T12:00';
  updateHourUnknown(); updateBirthSummary(); updateStaleBirthNotice();
});

// Solar-time modes need a longitude; keep the rules panel open and summarised so
// a non-default rule is never hidden from view.
function updateGeoControls(){
  const mode=$('#time_mode').value;
  $('#longitude').required=mode!=='clock';
  const panel=$('#advanced-rules');
  panel.classList.toggle('solar-active',mode!=='clock');
  if(mode!=='clock')panel.open=true;
  const parts=[{clock:'当地钟表时间',mean_solar:'平太阳时',apparent_solar:'真太阳时'}[mode]];
  if($('#late_zi_day_rollover').checked)parts.push('23:00 换日');
  parts.push($('#leap_month_second_half_as_next').checked?'闰月顺延':'闰月不顺延');
  $('#advanced-rules-summary').textContent=parts.join(' · ');
  updateBirthSummary();
}
for(const id of ['#time_mode','#late_zi_day_rollover','#leap_month_second_half_as_next'])$(id).addEventListener('change',updateGeoControls);
// Small screens: the form folds into a one-line summary so the workspace is reachable.
const genderLabels={male:'男',female:'女',unspecified:'不指定顺逆'};
function updateBirthSummary(){
  const input=readInput();
  const city=$('#birth_city').value ? $('#birth_city').selectedOptions[0].textContent+' · ' : '';
  const when=$('#hour_unknown').checked?input.birth_datetime.slice(0,10)+' · 时辰不详':input.birth_datetime.replace('T',' ');
  $('#birth-summary-text').textContent=when+' · '+city+input.timezone+' · '+(genderLabels[input.gender]||input.gender);
}
function setBirthPanelCollapsed(collapsed){
  $('#input-panel').classList.toggle('collapsed',collapsed);
  const toggle=$('#birth-summary-toggle');
  toggle.textContent=collapsed?'修改出生信息':'收起';
  toggle.setAttribute('aria-expanded',String(!collapsed));
}
$('#birth-summary-toggle').addEventListener('click',()=>{
  const collapsed=!$('#input-panel').classList.contains('collapsed');
  setBirthPanelCollapsed(collapsed);
  if(!collapsed)$('#birth_datetime').focus();
});
for(const type of ['input','change'])form.addEventListener(type,updateBirthSummary);
const compactScreen=window.matchMedia?window.matchMedia('(max-width: 860px)'):null;
setBirthPanelCollapsed(!!(compactScreen&&compactScreen.matches));
updateGeoControls();
$('#print-view').addEventListener('click',()=>window.print());

// Share card: a PNG drawn on a local canvas, or the same chart as text. Nothing is
// uploaded; birth date, time and gender stay off unless the user ticks them.
const shareOptions = {date: false, time: false, gender: false, bazi: true, ziwei: true};
let shareView = 'image', shareRefresh = null;
// A language whose table was still loading when the dialog opened redraws the card and the text chart.
document.addEventListener('xuanshu-language', () => {const dialog = $('#share-dialog'); if (dialog && dialog.open && shareRefresh) shareRefresh();});
const GENDER_CHART = {male: '乾造', female: '坤造'};
const PALACE_ORDER = ['命宫', '兄弟宫', '夫妻宫', '子女宫', '财帛宫', '疾厄宫', '迁移宫', '仆役宫', '官禄宫', '田宅宫', '福德宫', '父母宫'];
// The text chart uses the notation other chart software prints (labelled pillars, 命宫在…,
// 宫名：主星亮度), so it pastes into notes and chats and back into 外部命盘导入核对.
function shareChartText() {
  const b = current.bazi, z = current.ziwei, gap = '　';
  const lines = ['玄枢命盘 · 本地确定性计算'];
  const facts = [];
  if (shareOptions.date) facts.push(currentInput.birth_datetime.slice(0, 10));
  if (shareOptions.time && !currentHourUnknown) facts.push(currentInput.birth_datetime.slice(11, 16) + '（' + currentInput.timezone + '）');
  const gender = shareOptions.gender ? GENDER_CHART[currentInput.gender] : '';
  if (gender) facts.push(gender);
  if (currentHourUnknown) facts.push('时辰不详');
  if (facts.length) lines.push(facts.join(gap));
  if (shareOptions.bazi) {
    // A noon placeholder is not a real hour pillar, so nothing derived from it is listed.
    const keys = currentHourUnknown ? PILLAR_KEYS.slice(0, 3) : PILLAR_KEYS;
    const rows = [['干支', p => p.text], ['十神', p => p.ten_god_of_stem], ['藏干', p => p.hidden_stems.map(h => h.stem).join('')],
      ['纳音', p => p.na_yin], ['星运', p => p.growth_stage], ['自坐', p => p.self_stage], ['旬空', p => p.xun_kong]]
      .map(([label, value]) => [label + '：', PILLAR_KEYS.map(k => keys.includes(k) ? value(b.pillars[k]) : '—')]);
    rows.unshift(['　　　', PILLAR_KEYS.map(k => nameMap[k])]);
    // A table under 年柱 月柱 日柱 时柱; full-width padding keeps the columns aligned in any CJK font.
    const widths = PILLAR_KEYS.map((_, i) => Math.max(...rows.map(([, cells]) => cells[i].length)));
    lines.push('', '【四柱八字】');
    rows.forEach(([label, cells]) => lines.push(label + cells.map((c, i) => i < 3 ? c.padEnd(widths[i], '　') : c).join(gap)));
    const voids = keys.filter(k => (b.pillars[k].void_of || []).length)
      .map(k => nameMap[k] + b.pillars[k].branch + '（' + b.pillars[k].void_of.map(v => v === 'day' ? '日空' : '年空').join('、') + '）');
    lines.push('空亡：' + (voids.join('，') || '四柱地支不落日空、年空'), '日主：' + b.day_master + b.day_master_element);
    // Each relation names its pillars (年月 = year and month), since the same pair of stems can meet twice.
    const links = baziLinks(b), short = key => nameMap[key].charAt(0);
    // A three-harmony or seasonal group stays when the known pillars complete it by themselves.
    const known = x => x.kind === 'group' ? [...x.branches].every(br => keys.some(k => b.pillars[k].branch === br))
      : x.pillars.every(k => keys.includes(k));
    const listed = items => items.filter(known).sort((x, y) => x.from - y.from || x.to - y.to)
      .map(x => keys.filter(k => x.pillars.includes(k)).map(short).join('') + ' ' + x.label).join(gap);
    if (listed(links.stems)) lines.push('天干关系：' + listed(links.stems));
    if (listed(links.branches)) lines.push('地支关系：' + listed(links.branches));
    const stars = keys.filter(k => (b.pillars[k].shensha || []).length).map(k => nameMap[k] + ' ' + b.pillars[k].shensha.map(x => x.name).join('、'));
    if (shenshaUnsettled(b)) lines.push('神煞：随时辰而定');
    else if (stars.length) lines.push('神煞：' + stars.join('｜'));
    // Luck decades need the gender for their direction; the calendar years would give away the birth year.
    if (gender) {
      if (luckKey !== luckKeyNow()) {ensureLuck(); lines.push('大运：正在排…');}
      else if (luckData) {
        lines.push(['大运', luckData.direction === 'forward' ? '顺排' : '逆排'].join('：'));
        const rows = luckData.periods.map(p => {
          const n = p.natal_interactions;
          const cells = ['起运 ' + String(Math.round(p.approx_start_age_years)).padStart(2, ' '), p.pillar, n.ten_god_of_stem, '星运' + n.growth_stage];
          if (shareOptions.date) cells.push(p.approx_start_local.slice(0, 4) + '–' + (Number(p.approx_end_local_exclusive.slice(0, 4)) - 1));
          return [cells, natalMarkList(n).map(([text]) => text)];
        });
        const width = Math.max(...rows.map(([cells]) => cells[3].length));
        rows.forEach(([cells, marks]) => {cells[3] = cells[3].padEnd(width, '　'); lines.push('　' + cells.concat(marks).join(gap));});
      }
    }
  }
  if (shareOptions.ziwei && currentHourUnknown) lines.push('', '紫微斗数需要出生时辰，时辰不详时不列出。');
  else if (shareOptions.ziwei) {
    const ming = z.palaces.find(p => p.is_ming), shen = z.palaces.find(p => p.is_shen);
    lines.push('', '【紫微斗数】', ['命宫在' + ming.stem + ming.branch, '身宫在' + shen.name, z.five_elements_bureau,
      '命主' + z.ming_master, '身主' + z.shen_master].join('，'));
    lines.push('生年四化：' + z.birth_year_transformations.map(t => t.star + t.type).join(gap));
    const graded = (p, stars) => stars.map(s => s + ((p.star_brightness || {})[s] || '')).join(' ');
    PALACE_ORDER.map(name => z.palaces.find(p => p.name === name)).filter(Boolean).forEach(p => {
      let line = p.name + '（' + [p.stem + p.branch].concat(p.is_shen ? ['身宫'] : []).join('，') + '）：' + (graded(p, p.main_stars) || '空宫');
      if (p.auxiliary_stars.length) line += '｜' + graded(p, p.auxiliary_stars);
      // Decade direction follows gender, so the ages are listed only when gender is shown.
      if (gender && p.decade) line += '｜' + '大限' + ' ' + p.decade.start_age + '–' + p.decade.end_age;
      lines.push(line);
    });
    // The copied text leaves the page, so it carries the engine's limits with it.
    lines.push('注：紫微为部分排盘，含十四主星与选定的辅星、杂曜，不是全流派专业盘；四化表与亮度表因流派而异。');
  }
  const modes = {clock: '钟表时间', mean_solar: '平太阳时', apparent_solar: '真太阳时'};
  lines.push('', '排盘规则：' + [currentInput.late_zi_day_rollover ? '23:00 换日' : '00:00 换日',
    currentInput.leap_month_second_half_as_next ? '闰月后半月按下月' : '闰月整月按本月',
    modes[currentInput.time_mode] || modes.clock].join(gap));
  lines.push('传统文化符号，未经科学预测效力验证，不作医疗、投资、法律等决策依据。', 'XuanShu · 开源 · 确定性计算，可复现');
  const text = lines.join('\n');
  return typeof uiLang !== 'undefined' && uiLang === 'zh-TW' && typeof toTraditional === 'function' ? toTraditional(text) : text;
}
function drawShareCard(canvas) {
  const T = text => typeof translateText === 'function' ? translateText(text) : text;
  const css = getComputedStyle(document.documentElement);
  const token = name => css.getPropertyValue(name).trim();
  const W = 1080, PAD = 72;
  const b = current.bazi, z = current.ziwei;
  const ziwei = shareOptions.ziwei && !currentHourUnknown;  // palaces depend on the hour
  const H = 400 + (shareOptions.bazi ? 420 : 0) + (ziwei ? 480 : 0);
  canvas.width = W; canvas.height = H;
  const g = canvas.getContext('2d');
  const sans = "'Noto Sans SC','PingFang SC','Microsoft YaHei',sans-serif", serif = "'Noto Serif SC','Songti SC','STSong',serif";
  g.fillStyle = token('--panel'); g.fillRect(0, 0, W, H);
  const glow = g.createRadialGradient(W * .85, 0, 0, W * .85, 0, W * .9);
  glow.addColorStop(0, token('--accent-soft')); glow.addColorStop(1, 'transparent');
  g.fillStyle = glow; g.fillRect(0, 0, W, H);
  g.strokeStyle = token('--accent-line'); g.lineWidth = 2; g.strokeRect(24, 24, W - 48, H - 48);
  const text = (value, x, y, size, color, font = sans, align = 'left', weight = '400', maxWidth = W - PAD - x) => {
    g.font = `${weight} ${size}px ${font}`;
    while (size > 12 && g.measureText(value).width > maxWidth) {size -= 1; g.font = `${weight} ${size}px ${font}`;}
    g.fillStyle = color; g.textAlign = align; g.fillText(value, x, y);
  };
  text('玄枢', PAD, 132, 56, token('--gold'), serif, 'left', '600');
  text('XUANSHU', PAD + 128, 128, 22, token('--gold'), sans, 'left', '600');
  text(T('命盘卡片 · 本地确定性计算'), W - PAD, 128, 24, token('--muted'), sans, 'right', '400', W - PAD * 2 - 330);
  const facts = [];
  if (shareOptions.date) facts.push(currentInput.birth_datetime.slice(0, 10));
  if (shareOptions.time && !currentHourUnknown) facts.push(currentInput.birth_datetime.slice(11, 16) + ' ' + currentInput.timezone);
  if (shareOptions.gender && GENDER_CHART[currentInput.gender]) facts.push(T(GENDER_CHART[currentInput.gender]));
  if (currentHourUnknown) facts.push(T('时辰不详'));
  else facts.push(T(z.five_elements_bureau), T('命主') + ' ' + T(z.ming_master), T('身主') + ' ' + T(z.shen_master));
  text(facts.join('  ·  '), PAD, 196, 26, token('--text2'));
  let y = 250;
  const color = element => token('--' + (ELEMENT_CLASS[element] || 'gold'));
  if (shareOptions.bazi) {
    text(T('四柱八字'), PAD, y + 34, 28, token('--gold2'), sans, 'left', '600');
    const colW = (W - PAD * 2) / 4;
    [['year', '年柱'], ['month', '月柱'], ['day', '日柱'], ['hour', '时柱']].forEach(([key, label], i) => {
      const p = b.pillars[key], cx = PAD + colW * i + colW / 2;
      const hidden = key === 'hour' && currentHourUnknown;  // a noon placeholder is not a real hour pillar
      g.fillStyle = token('--panel2'); g.strokeStyle = key === 'day' ? token('--gold') : token('--border');
      g.lineWidth = key === 'day' ? 3 : 1.5;
      g.beginPath(); (g.roundRect ? g.roundRect.bind(g) : g.rect.bind(g))(PAD + colW * i + 8, y + 60, colW - 16, 300, 14); g.fill(); g.stroke();
      text(T(label), cx, y + 100, 22, token('--muted'), sans, 'center', '400', colW - 28);
      text(hidden ? T('时辰不详') : T(p.ten_god_of_stem), cx, y + 136, 22, token('--gold'), sans, 'center', '400', colW - 28);
      text(hidden ? '?' : p.stem, cx, y + 224, 82, hidden ? token('--faint') : color(p.stem_element), serif, 'center', '600');
      text(hidden ? '?' : p.branch, cx, y + 318, 82, hidden ? token('--faint') : color(p.branch_element), serif, 'center', '600');
    });
    y += 420;
  }
  if (ziwei) {
    text(T('紫微斗数'), PAD, y + 34, 28, token('--gold2'), sans, 'left', '600');
    const ming = z.palaces.find(p => p.is_ming), shen = z.palaces.find(p => p.is_shen);
    const stars = palace => palace.main_stars.map(star => {
      const level = (palace.star_brightness || {})[star];
      return T(star) + (level ? T('（' + level + '）') : '');
    }).join(' ') || T('空宫');
    const rows = [
      [T('命宫'), ming.stem + ming.branch + '  ' + stars(ming)],
      [T('身宫'), shen.stem + shen.branch + '  ' + T(shen.name) + '  ' + stars(shen)],
      [T('生年四化'), z.birth_year_transformations.map(t => T(t.star) + ' ' + T(t.type))],
      [T('五行局'), T(z.five_elements_bureau) + '  ·  ' + b.day_master + ' ' + T('日主')],
    ];
    let ry = y + 92;
    rows.forEach(([label, value]) => {
      text(label, PAD, ry, 20, token('--muted'));
      // A list that would not fit on one line at a readable size continues on a second line.
      let lines = Array.isArray(value) ? [value.join('  ·  ')] : [value];
      g.font = `600 26px ${serif}`;
      if (Array.isArray(value) && g.measureText(lines[0]).width > W - PAD * 2) {
        const half = Math.ceil(value.length / 2);
        lines = [value.slice(0, half).join('  ·  '), value.slice(half).join('  ·  ')];
      }
      lines.forEach((line, n) => text(line, PAD, ry + 38 + n * 40, 32, token('--text'), serif, 'left', '600'));
      ry += 84 + (lines.length - 1) * 40;
    });
    y += 480;
  }
  g.strokeStyle = token('--border'); g.lineWidth = 1; g.beginPath(); g.moveTo(PAD, H - 140); g.lineTo(W - PAD, H - 140); g.stroke();
  text(T('传统文化符号，未经科学预测效力验证，不作医疗、投资、法律等决策依据。'), PAD, H - 96, 22, token('--muted'));
  text('XuanShu · open source · deterministic, reproducible', PAD, H - 58, 22, token('--gold'));
}
function openShareCard() {
  if (!current) {form.requestSubmit(); return;}
  let dialog = $('#share-dialog');
  if (!dialog) {
    dialog = elt('dialog', 'share-dialog'); dialog.id = 'share-dialog';
    dialog.setAttribute('aria-labelledby', 'share-title');
    document.body.append(dialog);
  }
  dialog.replaceChildren();
  const head = append(dialog, 'div', 'share-head');
  append(head, 'h3', null, '分享卡片').id = 'share-title';
  const close = append(head, 'button', 'tiny-button', '关闭'); close.type = 'button'; close.id = 'share-close';
  close.addEventListener('click', () => dialog.close());
  const views = append(dialog, 'div', 'share-views');
  views.setAttribute('role', 'group'); views.setAttribute('aria-label', '分享格式');
  const viewButtons = [['image', '图片卡片'], ['text', '文字盘']].map(([key, label]) => {
    const chip = append(views, 'button', 'filter-chip', label); chip.type = 'button'; chip.id = 'share-view-' + key; chip.dataset.view = key;
    chip.addEventListener('click', () => {shareView = key; refresh();});
    return chip;
  });
  const options = append(dialog, 'div', 'share-options');
  const canvas = append(dialog, 'canvas', 'share-canvas'); canvas.id = 'share-canvas';
  canvas.setAttribute('role', 'img'); canvas.setAttribute('aria-label', '命盘卡片预览');
  const textBox = append(dialog, 'pre', 'share-text'); textBox.id = 'share-text'; textBox.tabIndex = 0;
  textBox.setAttribute('aria-labelledby', 'share-view-text');
  const gendered = Boolean(GENDER_CHART[currentInput.gender]);
  [['date', '显示出生日期'], ['time', '显示出生时间与时区'], ['gender', '显示乾造 / 坤造'], ['bazi', '四柱八字'], ['ziwei', '紫微命盘']].forEach(([key, label]) => {
    const line = append(options, 'label', 'check-line');
    const box = append(line, 'input'); box.type = 'checkbox'; box.id = 'share-' + key; box.checked = shareOptions[key];
    if ((currentHourUnknown && (key === 'ziwei' || key === 'time')) || (key === 'gender' && !gendered)) {box.checked = false; box.disabled = true;}
    line.append(' ' + label);
    box.addEventListener('change', () => {shareOptions[key] = box.checked; refresh();});
  });
  const help = append(dialog, 'p', 'field-help');
  const actions = append(dialog, 'div', 'profile-actions share-actions');
  const save = append(actions, 'button', 'primary-btn', '下载 PNG'); save.type = 'button'; save.id = 'share-download';
  save.addEventListener('click', () => canvas.toBlob(blob => {if (blob) downloadBlob(blob, 'xuanshu-card.png');}, 'image/png'));
  // The system share sheet (phones, some desktops). The PNG is prepared ahead of the click,
  // because browsers allow navigator.share only while the click still counts as a user gesture.
  let cardFile = null, cardVersion = 0;
  const systemShare = typeof navigator.share === 'function' && typeof navigator.canShare === 'function';
  const share = systemShare ? append(actions, 'button', 'tiny-button', '分享到…') : null;
  if (share) {
    share.type = 'button'; share.id = 'share-system';
    share.addEventListener('click', async () => {
      const file = cardFile;
      if (!file || !navigator.canShare({files: [file]})) {share.textContent = '此浏览器不能分享图片，请下载 PNG'; return;}
      try {await navigator.share({files: [file], title: '玄枢命盘'});}
      catch (e) {if (e.name !== 'AbortError') share.textContent = '分享失败，请下载 PNG';}
    });
  }
  const copy = append(actions, 'button', 'primary-btn', '复制文字盘'); copy.type = 'button'; copy.id = 'share-copy-text';
  copy.addEventListener('click', () => copyPre(textBox, copy, '已复制文字盘'));
  const saveText = append(actions, 'button', 'tiny-button', '下载 TXT'); saveText.type = 'button'; saveText.id = 'share-download-text';
  saveText.addEventListener('click', () => downloadBlob(new Blob([textBox.textContent + '\n'], {type: 'text/plain;charset=utf-8'}), 'xuanshu-chart.txt'));
  function refresh() {
    const image = shareView === 'image';
    viewButtons.forEach(chip => chip.setAttribute('aria-pressed', String(chip.dataset.view === shareView)));
    canvas.hidden = !image; textBox.hidden = image;
    save.hidden = !image; if (share) share.hidden = !image;
    copy.hidden = image; saveText.hidden = image;
    copy.textContent = '复制文字盘'; if (share) share.textContent = '分享到…';
    help.textContent = image
      ? '卡片只在这台设备上生成，不上传。注意：四柱本身大致能反推出生日期与时辰（约 60 年一轮），介意的话只保留紫微部分。'
      : '文字盘用通行的命盘写法，可以贴到笔记、聊天或其他排盘软件，也能粘回「外部命盘导入核对」逐项比对。大限年龄会透露性别，只在勾选乾造 / 坤造时列出。';
    drawShareCard(canvas);
    textBox.textContent = shareChartText();
    if (share) {
      const version = ++cardVersion; cardFile = null; share.disabled = true;
      canvas.toBlob(blob => {
        if (!blob || version !== cardVersion) return;
        cardFile = new File([blob], 'xuanshu-card.png', {type: 'image/png'}); share.disabled = false;
      }, 'image/png');
    }
  }
  shareRefresh = refresh;
  refresh();
  if (dialog.showModal) dialog.showModal(); else dialog.setAttribute('open', '');
}
$('#share-card').addEventListener('click', openShareCard);

// Calculation cross-check: the summary that scripts/eval_crosscheck.py writes.
const CROSSCHECK_FIELDS = {lunar: '农历日期', day: '日柱', year: '年柱', month: '月柱', hour: '时柱',
  growth_stage: '日主十二长生（星运）', xun_kong: '四柱旬空',
  jie_month: '交节前后月柱', jie_year: '立春前后年柱', solar_terms: '节气时刻', moon_phases: '月相时刻',
  ming: '命宫', shen: '身宫', bureau: '五行局', stars: '十四主星落宫', transformations: '生年四化',
  other_stars: '其余辅星、杂曜落宫', cycles: '长生、博士、岁前、将前十二神', brightness: '主星与昌曲、火铃、羊陀庙旺利陷',
  natal: '原局四柱神煞', fortune: '大运流年干支神煞'};
const CROSSCHECK_FLOW_FIELDS = {flow_decade: '大限流曜', flow_year: '流年流曜（含年解）', flow_month: '流月流曜',
  flow_day: '流日流曜', flow_hour: '流时流曜', year_twelve: '流年岁前、将前十二神'};
const CROSSCHECK_CAUSES = {
  forecast: '朔离午夜太近，取决于 ΔT 预报，现在无法确定哪边对。',
  old_almanac: '只有 lunardate 不同；旧历书的算法容易把这样的朔算到午夜另一侧。',
  table: '只有 lunardate 不同；这份表的月份长度与天象不符。',
  unexplained: '尚未解释。'};
const CROSSCHECK_FIXES = {beijing_meridian: '1914、1916、1920 年各有一个月，初一原来比三家参考晚一天：民国初年按北京地方平时（东经 116°25′）编历，已改正。',
  ziwei_star_tables: '紫微辅星对照 iztro 时查出两张安星表有误：辛年天魁、天钺互换，封诰逆行。已按所引规则改正（辛年天魁在午、天钺在寅；封诰从寅宫起子时顺行），重跑后全部辅星一致。'};
const CROSSCHECK_REPORT = 'https://github.com/Kukutx/XuanShu/blob/master/docs/evals/README.md';
let crosscheckData = null;
function crosscheckTable(parent, columns, rows, cells) {
  const table = append(append(parent, 'div', 'table-wrap'), 'table', 'data-table crosscheck-table');
  const head = append(append(table, 'thead'), 'tr');
  columns.forEach(name => append(head, 'th', null, name));
  const body = append(table, 'tbody');
  rows.forEach(row => {
    const tr = append(body, 'tr', row.mismatches ? 'has-diff' : null);
    cells(row).forEach(([text, cls]) => append(tr, 'td', cls || null, text));
  });
  return table;
}
function countRows(parent, rows, labels = CROSSCHECK_FIELDS) {
  return crosscheckTable(parent, ['对照项', '参考库', '核对数', '不一致', '一致率'], rows, row => [
    [labels[row.field]], [row.reference, 'mono'], [row.checked.toLocaleString('en-US'), 'num'],
    [String(row.mismatches), 'num'], [(100 * (row.checked - row.mismatches) / row.checked).toFixed(3) + '%', 'num']]);
}
function renderCrosscheck(dialog) {
  const d = crosscheckData;
  append(dialog, 'p', null, '玄枢把农历、四柱、神煞、节气、月相和紫微排盘与独立的开源库逐项对照。脚本、固定版本的参考库和原始数据都在仓库里，任何人都能重跑。');
  texts(append(dialog, 'p', 'field-help'), '评测日期', ' ' + d.generated + ' · ', '年份', ' ' + d.years.join('–') + ' · ',
    Object.entries(d.references).map(([name, version]) => name + ' ' + version).join(', '));
  append(dialog, 'h4', null, '逐日对照（每天正午）');
  countRows(dialog, d.daily);
  append(dialog, 'h4', null, '节气与月相时刻（秒）');
  crosscheckTable(dialog, ['对照项', '参考库', '年份', '平均差', '95% 分位', '最大差'], d.instants, row => [
    [CROSSCHECK_FIELDS[row.field]], [row.reference, 'mono'], [row.period, 'mono'],
    [String(row.mean_abs_seconds), 'num'], [String(row.p95_abs_seconds), 'num'], [String(row.max_abs_seconds), 'num']]);
  append(dialog, 'p', 'field-help', '2025 年以后各库用各自的地球自转差（ΔT）预报，差距随年份变大；只有离交节或午夜只差几分钟时才会影响结果。');
  const zw = d.ziwei;
  append(dialog, 'h4', null, '紫微斗数对照');
  texts(append(dialog, 'p', 'field-help'), '随机出生时刻', ' ' + zw.births.toLocaleString('en-US'));
  countRows(dialog, zw.rows);
  texts(append(dialog, 'p', 'field-help'), '23:00 以后出生', ' · ', '默认 23:00 不换日，与 iztro 的“早子时”一致', ' ' + (zw.late_zi_same_day.checked - zw.late_zi_same_day.mismatches) + '/' + zw.late_zi_same_day.checked + ' · ',
    '选择「23:00 换日」后与 iztro 的“晚子时”一致', ' ' + (zw.late_zi_next_day.checked - zw.late_zi_next_day.mismatches) + '/' + zw.late_zi_next_day.checked);
  if (zw.late_zi_month_kept) texts(append(dialog, 'p', 'field-help'), '另有', ' ' + zw.late_zi_month_kept + ' ',
    '个出生在月末最后一天或闰月后半月：iztro 晚子时只把日数加一、不进月，玄枢按次日完整的农历日期排，这是规则不同，不是计算错误。');
  if (d.horoscope) {
    append(dialog, 'h4', null, '紫微运限对照');
    texts(append(dialog, 'p', 'field-help'), '随机出生与目标时刻', ' ' + d.horoscope.pairs.toLocaleString('en-US'));
    countRows(dialog, d.horoscope.rows.map(row => ({...row, reference: 'iztro_py'})), {...LAYER_NAMES, month: '流月（斗君）', hour: '流时'});
    if (d.horoscope.flow_rows) countRows(dialog, d.horoscope.flow_rows.map(row => ({...row, reference: 'iztro'})), CROSSCHECK_FLOW_FIELDS);
    if (d.horoscope.calendar_differs && !d.horoscope.unexplained) append(dialog, 'p', 'field-help', '流日、流时的少数差异都落在玄枢与 lunar_python 农历日期不同的月份（iztro 的农历取自 lunar_python），日数差一天，宫位就差一宫。');
    if (d.horoscope.unexplained) texts(append(dialog, 'p', 'field-help'), '另有', ' ' + d.horoscope.unexplained + ' ', '处运限差异尚未解释，清单见完整报告。');
  }
  if (d.shensha) {
    append(dialog, 'h4', null, '八字神煞对照');
    texts(append(dialog, 'p', 'field-help'), '共', ' ' + d.shensha.charts.toLocaleString('en-US') + ' ', '张盘（每天一张）', ' · ', '十六种神煞逐柱比较');
    countRows(dialog, ['natal', 'fortune'].map(field => ({field, reference: '@soul-atelier/bazi', ...d.shensha[field]})));
    append(dialog, 'p', 'field-help', '参考库给阴干也排羊刃、孤辰寡宿兼以日支查、大运流年也标魁罡，与玄枢所引规则不同，这几处不比较。');
  }
  append(dialog, 'h4', null, '仍有差异的月份');
  const list = append(dialog, 'ul', 'crosscheck-list'); list.id = 'crosscheck-differences';
  if (!d.differences.length) append(list, 'li', 'muted', '—');
  d.differences.forEach(item => {
    const li = append(list, 'li');
    texts(append(li, 'strong'), item.first + ' – ' + item.last);
    texts(li, ' · ' + item.references.join(', ') + ' · ', '朔离午夜', ' ' + item.minutes_from_midnight + ' ', '分钟', ' · ', CROSSCHECK_CAUSES[item.cause] || CROSSCHECK_CAUSES.unexplained);
  });
  if (d.fixes.length) {
    append(dialog, 'h4', null, '评测带来的修正');
    const fixes = append(dialog, 'ul', 'crosscheck-list');
    d.fixes.forEach(fix => append(fixes, 'li', null, CROSSCHECK_FIXES[fix.cause] || fix.months.join(', ')));
  }
  append(dialog, 'p', 'field-help', '这只核验计算是否正确，不评价命理解读是否应验。');
  const link = append(dialog, 'a', 'docs-link', '完整报告与重跑方法 ↗');
  link.href = CROSSCHECK_REPORT; link.target = '_blank'; link.rel = 'noopener';
}
async function openCrosscheck() {
  let dialog = $('#crosscheck-dialog');
  if (!dialog) {
    dialog = elt('dialog', 'share-dialog crosscheck-dialog'); dialog.id = 'crosscheck-dialog';
    dialog.setAttribute('aria-labelledby', 'crosscheck-title');
    document.body.append(dialog);
  }
  const draw = (fill) => {
    dialog.replaceChildren();
    const head = append(dialog, 'div', 'share-head');
    append(head, 'h3', null, '计算交叉核验').id = 'crosscheck-title';
    const close = append(head, 'button', 'tiny-button', '关闭'); close.type = 'button'; close.id = 'crosscheck-close';
    close.addEventListener('click', () => dialog.close());
    fill();
  };
  if (crosscheckData) draw(() => renderCrosscheck(dialog));
  else draw(() => append(dialog, 'p', 'field-help', '正在读取评测结果…'));
  if (!dialog.open) {if (dialog.showModal) dialog.showModal(); else dialog.setAttribute('open', '');}
  if (crosscheckData) return;
  try {
    const response = await fetch('/static/crosscheck-summary.json');
    if (!response.ok) throw new Error('HTTP ' + response.status);
    crosscheckData = await response.json();
  } catch (err) {
    draw(() => append(dialog, 'p', 'inline-msg', '读取评测结果失败：' + err.message));
    return;
  }
  draw(() => renderCrosscheck(dialog));
}
$('#crosscheck-open').addEventListener('click', openCrosscheck);
$('#crosscheck-footer').addEventListener('click', openCrosscheck);

// The demonstration date must remain explicitly identified until changed.
function updateDemoBirthWarning() {
  $('#demo-birth-warning').hidden = $('#birth_datetime').value !== '2000-08-16T04:00';
}
$('#birth_datetime').addEventListener('input',updateDemoBirthWarning);
updateDemoBirthWarning();
// Restore a tool-only URL without exposing sensitive input in the address bar.
const initialTab=tabFromHash();
activateTab(initialTab || tabs.find(t => t.dataset.tab === active), false);
$('#today-chip').addEventListener('click', () => {
  activateTab(tabs.find(t => t.dataset.tab === 'today'));
  $('#workspace').scrollIntoView({block: 'start', behavior: 'smooth'});
});
if (active !== 'today') ensureToday();
