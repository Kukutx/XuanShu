'use strict';
// Vanilla JS, no third-party client dependencies or remote analytics.
const $ = sel => document.querySelector(sel);
const result = $('#result');
const form = $('#birth-form');
const tabs = [...document.querySelectorAll('.tab')];
const commonTabs = new Set(['chat','date-scan','consult','bazi','qimen','ziwei','professional','calendar','pair','decision','report']);
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
  quality:'质量 核查 误差',
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
  $('#tool-visible-count').textContent = term
    ? (matched ? ('找到 ' + matched + ' 项（当前页面保留）') : '没有匹配项，请尝试八字、择时、MCP 等关键词')
    : ('当前 ' + visible + '/' + tabs.length + ' 项');
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
let professionalResult = null;
let referenceAuditResult = null;
const localToday = () => {
  const now = new Date();
  return [now.getFullYear(), String(now.getMonth()+1).padStart(2,'0'), String(now.getDate()).padStart(2,'0')].join('-');
};
let professionalTargetDraft = localToday();
let currentInput = null;
let selectedPalace = '命宫';
let calendarResult = null;
let pairResult = null;
let pairZiweiResult = null;
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
let pairDraft = {birth_datetime: '2001-01-01T12:00', timezone: 'Asia/Shanghai', gender: 'unspecified'};
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
async function postJSON(path, body) {
  const token = $('#api_token').value;
  const response = await fetch(path, {
    method: 'POST',
    headers: {'Content-Type': 'application/json', ...(token ? {'Authorization': 'Bearer ' + token} : {})},
    body: JSON.stringify(body),
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
function renderQimen() {
  if (qimenResult && qimenFingerprint !== JSON.stringify(readInput())) qimenResult = null;
  title(result, '奇门遁甲 · 时家拆补转盘', '九宫 · 三元局数 · 地盘 / 天盘 / 暗干 / 门 / 星 / 神');
  append(result, 'p', 'info-inline', '使用左侧指定日期与时间作为排盘瞬间。不是出生预测；本模块仅实现一套明确的时家拆补转盘配置。');
  const row = append(result, 'div', 'inline-control');
  const run = append(row, 'button', null, '排布九宫'); run.id='qimen-run'; run.type='button';
  const message = append(result, 'p', 'inline-msg');
  run.addEventListener('click', async () => {
    run.disabled=true; message.textContent='';
    try { const input = readInput(); const stamp = JSON.stringify(input);
      const chart = await postJSON('/api/qimen', {moment:input});
      qimenResult=chart; qimenFingerprint=stamp; render(); }
    catch(e) { message.textContent='奇门排盘失败：'+e.message; }
    finally { run.disabled=false; }
  });
  if (!qimenResult) return;
  const q=qimenResult;
  meta(result,[q.solar_term, q.dun + q.bureau + '局', q.yuan, '日 ' + q.day_pillar, '时 ' + q.hour_pillar]);
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
    const cell=append(board,'div','qimen-cell' + (n===5?' center':'') + (p.void?' empty':'') );
    append(cell,'strong',null,`${n} · ${p.trigram}宫 · ${p.direction}`);
    append(cell,'div',null,`地干 ${p.earth_stem}　天干 ${p.heaven_stem}`);
    append(cell,'div',null,`暗干 ${p.dark_stem}`);
    append(cell,'div',null,`九星 ${p.star}`);
    append(cell,'div',null,`八门 ${p.door || '—'}`);
    append(cell,'div',null,`八神 ${p.deity || '—'}`);
    if(p.void) append(cell,'small',null,'旬空');
    if(p.center_lodged_here) append(cell,'small',null,'中宫寄宫');
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
function renderBazi(b) {
  title(result, '四柱命式', '太阳节令 · 藏干十神 · 纳音');
  const grid = append(result, 'div', 'pillar-grid');
  for (const [key, p] of Object.entries(b.pillars)) {
    const box = append(grid, 'div', 'pillar');
    append(box, 'div', 'pillar-head', nameMap[key]);
    append(box, 'div', 'pillar-stem', p.stem);
    append(box, 'div', 'pillar-branch', p.branch);
    append(box, 'div', 'pillar-sub', p.stem_element + ' / ' + p.branch_element);
    append(box, 'div', 'pillar-god', p.ten_god_of_stem);
    append(box, 'div', 'pillar-hidden', '藏干：' + p.hidden_stems.map(h => h.stem + '·' + h.ten_god).join(' '));
    append(box, 'div', 'pillar-nayin', '纳音：' + p.na_yin);
  }
  append(result, 'h4', 'subheading', '明干 + 地支本气 · 五行数量');
  const five = append(result, 'div', 'five-row');
  Object.entries(b.surface_five_elements).forEach(([name, value]) => {
    const item = append(five, 'div', 'five-box');
    append(item, 'strong', null, String(value)); append(item, 'span', null, name);
  });
  append(result, 'h4', 'subheading', '地支关系标签与藏干统计');
  const relationBox = append(result, 'div', 'relationship-grid');
  b.branch_relations.filter(x => x.labels.length).forEach(x => append(relationBox, 'div', 'symbol-tag', `${nameMap[x.a]}·${nameMap[x.b]} ${x.branches} ${x.labels.join(' / ')}`));
  if (!relationBox.childElementCount) append(relationBox, 'p', 'info-inline', '当前四柱无所列特定关系标签');
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
  note(result, '藏干顺序为传统本气、中气、余气；计数仅统计明干和地支本气，不判断喜忌、旺衰与命运。');
}
function findPalace(z, name) {return z.palaces.find(item => item.name === name) || z.palaces.find(item => item.is_ming);}
function renderPalacePanel(parent, palace) {
  const block = append(parent, 'div', 'palace-panel');
  append(block, 'h4', null, `${palace.name} · ${palace.stem}${palace.branch}`);
  append(block, 'p', null, '主星：' + (palace.main_stars.join('、') || '空宫（未安十四主星）'));
  append(block, 'p', null, '辅星：' + (palace.auxiliary_stars.join('、') || '—'));
  append(block, 'p', null, '生年四化：' + (palace.birth_year_transformations.map(t => `${t.star}${t.type}`).join('、') || '此宫无生年四化标记'));
  append(block, 'p', null, '宫干飞化：' + palace.palace_flying_transformations.map(t => `${t.star}${t.type}→${t.target_palace}${t.self_transform ? '（自化）' : ''}`).join('；'));
  if (palace.three_harmonies_and_opposite) {
    const link = palace.three_harmonies_and_opposite;
    append(block, 'p', null, '三方四正：' + link.trine.map(x => `${x.palace}·${x.branch}`).join('、') + '；对宫 ' + link.opposite.palace + '·' + link.opposite.branch);
  }
}
function renderZiwei(z) {
  title(result, '紫微十二宫', '点击任意宫位查看宫干飞化');
  meta(result, [`命宫 ${z.ming_palace}`, `身宫 ${z.shen_palace}`, z.five_elements_bureau, z.transformation_school]);
  const board = append(result, 'div', 'ziwei-board');
  const cells = {5:[1,1], 6:[1,2], 7:[1,3], 8:[1,4], 4:[2,1], 9:[2,4], 3:[3,1], 10:[3,4], 2:[4,1], 1:[4,2], 0:[4,3], 11:[4,4]};
  z.palaces.forEach((p, index) => {
    const node = append(board, 'button', 'palace palace-btn' + (p.is_ming ? ' ming' : '') + (p.is_shen ? ' shen' : '') + (selectedPalace === p.name ? ' selected' : ''));
    node.type = 'button';
    node.style.gridRow = String(cells[index][0]);
    node.style.gridColumn = String(cells[index][1]);
    node.setAttribute('aria-label', `查看${p.name}飞化`);
    const head = append(node, 'div', 'palace-head');
    append(head, 'b', null, p.name.replace('宫', '')); append(head, 'span', null, p.stem + p.branch);
    append(node, 'div', 'star-primary', p.main_stars.join(' · ') || '—');
    append(node, 'div', 'star-secondary', p.auxiliary_stars.join(' · '));
    const tag = p.birth_year_transformations.map(t => t.star + t.type).join(' · ');
    if (tag) append(node, 'div', 'star-label', tag);
    append(node, 'div', 'palace-foot', (p.is_ming ? '命 ' : '') + (p.is_shen ? '身 ' : '') + (p.decade ? `${p.decade.start_age}–${p.decade.end_age}岁` : ''));
    node.addEventListener('click', () => {selectedPalace = p.name; render();});
  });
  const center = append(board, 'div', 'board-center');
  append(center, 'div', 'center-symbol', '☯');
  append(center, 'div', 'center-title', '紫 微 斗 数');
  append(center, 'div', 'center-sub', z.year_pillar + ' · ' + z.five_elements_bureau);
  append(center, 'div', 'center-sub', `${z.star_counts.main} 主星 · ${z.star_counts.auxiliary} 辅星 · 生年四化`);
  renderPalacePanel(result, findPalace(z, selectedPalace));
  note(result, `部分排盘：现含 ${z.star_counts.main} 主星与 ${z.star_counts.auxiliary} 颗选定辅/杂曜、四组十二神（部分依性别）及经度时制选择；不含全流派与完整流年。所有展示均不等于命运预测。`);
}
function renderTransform(z) {
  title(result, '生年四化 / 宫干飞化', '《全书》系公开十干四化表 · 流派差异需核对');
  const cards = append(result, 'div', 'transform-grid');
  z.birth_year_transformations.forEach(item => {
    const box = append(cards, 'div', 'transform-card');
    append(box, 'div', 'transform-type', item.type);
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
  ics.href = '/api/solar-terms/' + calendarDraft.start_date.slice(0,4) + '.ics';
  start.addEventListener('change', () => {if (start.value) ics.href='/api/solar-terms/'+start.value.slice(0,4)+'.ics';});
  ics.addEventListener('click', async event => {
    event.preventDefault();
    const token = $('#api_token').value;
    try {
      const reply = await fetch(ics.href, {headers:token ? {'Authorization':'Bearer '+token} : {}});
      if (!reply.ok) throw new Error('HTTP ' + reply.status);
      const url=URL.createObjectURL(await reply.blob());
      const link=elt('a');link.href=url;link.download='solar-terms-'+(start.value || calendarDraft.start_date).slice(0,4)+'.ics';
      document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);
    }catch(e){message.textContent='下载失败：'+e.message;}
  });
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
    append(tr, 'td', null, d.day_pillar).style.color = '#e3c392';
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
  const nl=append(opts,'label','check-line');const natal=append(nl,'input');natal.type='checkbox';natal.id='scan-natal';natal.checked=dateScanDraft.natal;nl.append(' 排除与左侧本命年支、日支相冲的日子');
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
  if(!current){append(result,'p','info-inline','请先在左侧生成命盘。');return;}
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
    const tr=append(body,'tr');append(tr,'td',null,o.name);
    append(tr,'td',null,String(o.score));
    append(tr,'td',null,o.contributions.map(c=>`${c.criterion} ${c.rating}×${(100*c.normalized_weight).toFixed(0)}%`).join(' + '));
  });
  append(result,'h4','subheading','单指标剔除敏感性');
  decisionResult.leave_one_out_sensitivity.forEach(x=>append(result,'div','feature-note',
    `去掉「${x.omitted_criterion}」后首位：${x.leaders_without_it.join('、')}${x.leader_changed?' · 结果变化':' · 不变'}`));
  decisionResult.limitations.forEach(x=>note(result,x));
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
function renderPair() {
  title(result, '双人合盘对照', '八字四柱对照 + 紫微宫位叠盘 · 只做结构对照，不评分关系好坏');
  append(result, 'p', 'info-inline', 'A 使用左侧出生信息；B 在下方单独填写。对照数据不会自动保存。');
  const row = append(result, 'div', 'inline-control');
  const date = createInput('B · 公历出生日期与时间', 'datetime-local', pairDraft.birth_datetime, row);
  date.id = 'pair_datetime'; date.min = '1901-01-01T00:00'; date.max = '2099-12-31T23:59';
  const label = append(row, 'label', null, 'B · 时区');
  const zone = append(label, 'select'); zone.id = 'pair_timezone';
  [...$('#timezone').options].forEach(opt => {const option = append(zone, 'option', null, opt.textContent); option.value = opt.value;});
  zone.value = pairDraft.timezone;
  const run = append(row, 'button', null, '比较两人命盘'); run.type = 'button'; run.id = 'pair-run';
  const error = append(result, 'p', 'inline-msg');
  run.addEventListener('click', async () => {
    pairDraft = {birth_datetime: date.value, timezone: zone.value, gender: 'unspecified'};
    if (!pairDraft.birth_datetime) {error.textContent = '请填写 B 的出生时间'; return;}
    run.disabled = true; error.textContent = '';
    try {
      const body = {person_a: readInput(), person_b: pairDraft};
      [pairResult, pairZiweiResult] = await Promise.all([postJSON('/api/pair', body), postJSON('/api/ziwei-pair', body)]);
      render();
    } catch (err) {error.textContent = '比较失败：' + err.message;}
    finally {run.disabled = false;}
  });
  if (!pairResult) return;
  meta(result, [`A 日主 ${pairResult.person_a.day_master}`, `B 日主 ${pairResult.person_b.day_master}`, '不提供匹配分数']);
  const table = append(append(result, 'div', 'table-wrap'), 'table', 'data-table');
  const hr = append(append(table, 'thead'), 'tr');
  ['位置', 'A 四柱', 'B 四柱', '地支关系'].forEach(text => append(hr, 'th', null, text));
  const tbody = append(table, 'tbody');
  pairResult.comparisons.forEach(row => {
    const tr = append(tbody, 'tr');
    append(tr, 'td', null, row.label);
    append(tr, 'td', null, row.person_a);
    append(tr, 'td', null, row.person_b);
    append(tr, 'td', null, row.branch_relation);
  });
  note(result, pairResult.notes.join(' '));
  if (pairZiweiResult) renderZiweiPair(pairZiweiResult);
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
  append(result,'p','info-inline','以左侧时间为中心，在前后误差区间中离散采样，列出实际出现的不同八字和命身宫。采样点之间仍可能存在未检测到的差异。');
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
    if(readInput().longitude===null){error.textContent='请先在左侧填写出生地经度。';return;}
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
  const head=append(append(table,'thead'),'tr');['次序','十年干支','名义起始年龄','近似起始公历'].forEach(x=>append(head,'th',null,x));
  const body=append(table,'tbody');
  d.periods.forEach(x=>{const tr=append(body,'tr');append(tr,'td',null,x.sequence);append(tr,'td',null,x.pillar);append(tr,'td',null,x.approx_start_age_years.toFixed(2));append(tr,'td',null,x.approx_start_local.replace('T',' '));});
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
  return {date_scan:dateScanResult, consultation:consultResult, qimen:qimenResult, qimen_reference_audit:referenceAuditResult,ziwei_professional:professionalResult, bazi_dayun:dayunResult, birth_boundaries:boundaryResult, day_officers:officerResult, annual_timeline:timelineResult, decision_matrix:decisionResult, chart: current, calendar: calendarResult, lunar_inverse: lunarInverseResult, pair: pairResult, ziwei_pair: pairZiweiResult, annual: annualResult, time_audit: timeResult, birth_window: windowResult, report: reportResult, quality_audit: qualityResult};
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
  const bl=append(controls,'label',null,'本次允许使用左侧出生资料');
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
    if(partnerCheck.checked){if(!birthCheck.checked||!partnerDate.value){feedback.textContent='合盘需要勾选左侧出生资料，并填写第二人的当地出生时间';return;}
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
function render() {
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
  if (active === 'integration') return renderIntegration();
  if (active === 'time') return renderTimeAudit();
  if (active === 'annual') return renderAnnual();
  if (active === 'quality') return renderQualityAudit();
  if (active === 'report') return renderReport();
  if (active === 'deep') return renderDeep();
  if (!current) {
    const empty = append(result, 'div', 'empty-state');
    append(empty, 'div', 'empty-orbit', '☯');
    append(empty, 'h3', null, '历法可核验，规则可追溯');
    append(empty, 'p', null, '点击左侧「生成命盘」开始计算');
    return;
  }
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
function activateTab(tab, updateUrl = true) {
  if (!tab) return;
  active = tab.dataset.tab;
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
  if ((event.ctrlKey || event.metaKey) && !event.altKey && event.key.toLowerCase() === 'k') {
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
    selectedPalace = '命宫';
    $('#result-subtitle').textContent = data.birth_datetime.replace('T',' ') + ' · ' + data.timezone;
    $('#download-json').disabled = false;
    updateStaleBirthNotice();
    render();
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
  list.forEach(x => {const op = append(select, 'option', null, x.label); op.value = x.id;});
  if (list.some(x => x.id === currentID)) select.value = currentID;
}
$('#save-profile').addEventListener('click', () => {
  const label = $('#profile_name').value.trim();
  if (!label) {setFeedback('先填写档案标签'); return;}
  const profiles = loadProfiles();
  if (profiles.length >= 20) {setFeedback('最多保存 20 条，请先删除旧档案'); return;}
  const id = Date.now().toString(36) + '-' + Math.random().toString(36).slice(2,10);
  profiles.push({id, label, data: readInput()});
  try {localStorage.setItem(profileKey, JSON.stringify(profiles)); showProfiles(); $('#profiles').value = id; setFeedback('仅保存在当前浏览器。');}
  catch (_) {setFeedback('保存失败：当前浏览器无法使用本地存储');}
});
$('#load-profile').addEventListener('click', () => {
  const entry = loadProfiles().find(x => x.id === $('#profiles').value);
  if (!entry) {setFeedback('请选择有效档案'); return;}
  setInput(entry.data); setFeedback('已载入档案，正在计算。'); form.requestSubmit();
});
$('#remove-profile').addEventListener('click', () => {
  const chosen = $('#profiles').value;
  if (!chosen) {setFeedback('请选择要删除的档案'); return;}
  try {localStorage.setItem(profileKey, JSON.stringify(loadProfiles().filter(x => x.id !== chosen))); showProfiles(); purgeChatStores(); setFeedback('已从本机浏览器删除所选档案及其对话、记忆和人生事件。'); if (active === 'chat') render();}
  catch (_) {setFeedback('删除失败：浏览器存储不可用');}
});
showProfiles();

function updateGeoControls(){const mode=$('#time_mode').value;$('#longitude').required=mode!=='clock';$('#longitude').closest('.location-panel').classList.toggle('solar-active',mode!=='clock');}
$('#time_mode').addEventListener('change',updateGeoControls);updateGeoControls();

// The demonstration date must remain explicitly identified until changed.
function updateDemoBirthWarning() {
  $('#demo-birth-warning').hidden = $('#birth_datetime').value !== '2000-08-16T04:00';
}
$('#birth_datetime').addEventListener('input',updateDemoBirthWarning);
updateDemoBirthWarning();
// Restore a tool-only URL without exposing sensitive input in the address bar.
const initialTab=tabFromHash();
if (initialTab) activateTab(initialTab, false);
else {updateToolNavigation(); render();}
