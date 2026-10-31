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
  let heading = null;
  document.querySelectorAll('#workspace-tabs :is(.tab-group, .tab)').forEach(node => {
    if (node.classList.contains('tab-group')) {heading = node; heading.hidden = true;}
    else if (heading && !node.hidden) heading.hidden = false;
  });
  // Counts sit between their own text nodes so 当前 / 项 translate as whole entries.
  $('#tool-visible-count').replaceChildren(...(term
    ? (matched ? ['找到 ', String(matched), ' 项（当前页面保留）'] : ['没有匹配项，请尝试八字、择时、MCP 等关键词'])
    : ['当前 ', visible + '/' + tabs.length, ' 项']));
  $('#tool-toggle-all').textContent = expandedTools ? '收起高级功能' : `展开全部 ${tabs.length} 项`;
  $('#tool-toggle-all').setAttribute('aria-expanded', String(expandedTools));
}
$('#tool-toggle-all').addEventListener('click', () => {expandedTools = !expandedTools; updateToolNavigation();});
$('#tool-search').addEventListener('input', event => {updateToolNavigation(); if (event.currentTarget.value.trim()) showPalette(); else hidePalette();});
// The finder is also a command palette: what is typed lists the matching tools and page actions under the box;
// ↑ / ↓ choose one, Enter opens or runs it, Esc clears. Actions name the button they press, so nothing new happens.
// What each palette action answers to when typed, in any interface language; matched, never shown.
// # i18n: input vocabulary, not interface text
const PALETTE_KEYS = {
  run: 'run cast chart generate 排盘 重新',
  birth: 'birth edit date time 出生 生日 时间 资料',
  json: 'json export download 下载 数据',
  share: 'share card image png 图片',
  print: 'print pdf 打印',
  theme: 'theme color dark light 深色 浅色 主题 配色',
  shortcuts: 'shortcuts keyboard keys 快捷键 按键 ?',
  crosscheck: 'crosscheck verify check 核验 交叉',
  all: 'all expand more advanced 全部 高级',
  docs: 'api docs openapi rest 文档 接口',
  language: 'language lang 语言 界面',
};
// # i18n: end of input vocabulary
const PALETTE_ACTIONS = [
  {label: '生成命盘', keys: PALETTE_KEYS.run, run: () => $('#run-btn').click(), ok: () => !$('#run-btn').disabled},
  {label: '修改出生信息', keys: PALETTE_KEYS.birth, run: () => focusBirthField('birth_datetime')},
  {label: '导出 JSON ↓', keys: PALETTE_KEYS.json, run: () => $('#download-json').click(), ok: () => !$('#download-json').disabled},
  {label: '分享卡片', keys: PALETTE_KEYS.share, run: () => $('#share-card').click()},
  {label: '打印 / 存为 PDF', keys: PALETTE_KEYS.print, run: () => $('#print-view').click()},
  {label: '切换配色', keys: PALETTE_KEYS.theme, run: () => $('#theme-toggle').click()},
  {label: '键盘快捷键', keys: PALETTE_KEYS.shortcuts, run: () => $('#shortcuts-open').click()},
  {label: '历法与排盘逐日交叉核验', keys: PALETTE_KEYS.crosscheck, run: () => $('#crosscheck-open').click()},
  {label: () => expandedTools ? '收起高级功能' : `展开全部 ${tabs.length} 项`, keys: PALETTE_KEYS.all, run: () => $('#tool-toggle-all').click()},
  {label: 'API 文档 ↗', keys: PALETTE_KEYS.docs, run: () => window.open('/docs', '_blank', 'noopener')},
  ...['zh-CN', 'zh-TW', 'en', 'ja'].map(lang => ({lang, keys: PALETTE_KEYS.language + ' ' + lang,
    run: () => {const select = $('#ui-language'); select.value = lang; select.dispatchEvent(new Event('change'));},
    ok: () => $('#ui-language').value !== lang})),
];
const PALETTE_LIMIT = 14;
let paletteItems = [], paletteIndex = 0;
// Tools opened during this visit, newest first. Kept in memory only, so a reload starts with an empty list.
let recentTools = [];
const RECENT_LIMIT = 6;
// Each tool's group heading, shown beside it in the palette.
const toolGroup = new Map();
{let heading = null; document.querySelectorAll('#workspace-tabs :is(.tab-group, .tab)').forEach(node => {
  if (node.classList.contains('tab-group')) heading = node; else if (heading) toolGroup.set(node, heading);
});}
function paletteLabel(action) {
  if (action.lang) return ['界面语言', '：', (typeof UI_LANGS !== 'undefined' && UI_LANGS[action.lang]) || action.lang];
  return [typeof action.label === 'function' ? action.label() : action.label];
}
function showPalette() {
  const input = $('#tool-search'), list = $('#tool-palette'), term = input.value.trim().toLocaleLowerCase();
  const toolItem = (tab, kind) => ({kind, tool: true, label: [tab.textContent], note: toolGroup.get(tab)?.textContent || '', run: () => {activateTab(tab); tab.focus();}});
  if (!term) {
    // An empty box lists the tools opened before the current one, so going back is two keys away.
    const recent = recentTools.filter(tab => tab.dataset.tab !== active).slice(0, RECENT_LIMIT);
    if (!recent.length) {hidePalette(); return;}
    paletteItems = recent.map(tab => toolItem(tab, '最近打开'));
  } else {
    const tools = tabs.filter(tab => (tab.textContent + ' ' + (toolKeywords[tab.dataset.tab] || '')).toLocaleLowerCase().includes(term))
      .map(tab => toolItem(tab, '功能页'));
    const actions = PALETTE_ACTIONS.filter(a => (!a.ok || a.ok()) && (paletteLabel(a).map(calT).join('') + ' ' + paletteLabel(a).join('') + ' ' + a.keys).toLocaleLowerCase().includes(term))
      .map(a => ({kind: '快捷操作', tool: false, label: paletteLabel(a), note: '', run: a.run}));
    paletteItems = tools.concat(actions).slice(0, PALETTE_LIMIT);
  }
  paletteIndex = 0;
  list.replaceChildren();
  if (!paletteItems.length) {append(list, 'li', 'palette-empty', '没有匹配项，请尝试八字、择时、MCP 等关键词').setAttribute('role', 'presentation');}
  paletteItems.forEach((item, i) => {
    const option = append(list, 'li', 'palette-opt'); option.id = 'palette-opt-' + i; option.setAttribute('role', 'option');
    append(option, 'span', 'palette-kind palette-kind-' + (item.tool ? 'tool' : 'action'), item.kind);
    texts(append(option, 'span', 'palette-label'), ...item.label);
    if (item.note) append(option, 'small', null, item.note);
    option.addEventListener('pointermove', () => {if (paletteIndex !== i) {paletteIndex = i; markPalette();}});
    option.addEventListener('click', () => runPalette(i));
  });
  list.hidden = false; input.setAttribute('aria-expanded', 'true');
  markPalette();
}
function markPalette() {
  const input = $('#tool-search');
  $('#tool-palette').querySelectorAll('.palette-opt').forEach((option, i) => {
    const on = i === paletteIndex;
    option.classList.toggle('is-active', on); option.setAttribute('aria-selected', String(on));
    if (on) {input.setAttribute('aria-activedescendant', option.id); option.scrollIntoView({block: 'nearest'});}
  });
  if (!paletteItems.length) input.removeAttribute('aria-activedescendant');
}
function hidePalette() {
  const input = $('#tool-search'), list = $('#tool-palette');
  list.hidden = true; list.replaceChildren(); paletteItems = [];
  input.setAttribute('aria-expanded', 'false'); input.removeAttribute('aria-activedescendant');
}
function runPalette(i) {
  const item = paletteItems[i];
  if (!item) return;
  // The search is done: the strip shows its usual tools again, then the choice opens or runs.
  $('#tool-search').value = ''; hidePalette(); updateToolNavigation();
  item.run();
}
// A press on the list keeps the focus in the box, so the list stays open until the click lands.
$('#tool-palette').addEventListener('pointerdown', event => event.preventDefault());
$('#tool-search').addEventListener('blur', hidePalette);
$('#tool-search').addEventListener('focus', showPalette);
$('#tool-search').addEventListener('keydown', event => {
  if (event.isComposing) return;
  if (event.key === 'Escape') {event.currentTarget.value = ''; hidePalette(); updateToolNavigation(); return;}
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    if ($('#tool-palette').hidden) showPalette();
    if (!paletteItems.length) return;
    event.preventDefault();
    paletteIndex = (paletteIndex + (event.key === 'ArrowDown' ? 1 : -1) + paletteItems.length) % paletteItems.length;
    markPalette();
  } else if (event.key === 'Enter' && paletteItems.length) {
    event.preventDefault(); runPalette(paletteIndex);
  }
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
let consultRunKey = null;  // the birth input the consultation shown ran on, to offer its pages only for the chart shown
let consultAdvancedOpen = false;
let consultTicket = 0;  // a reply to an older run is dropped when a newer run was started meanwhile
let consultDraft = {question:'',intent:'auto', useBirth:false, usePartner:false, partnerDate:'', lunarYear:'', candidateDates:'', facts:'', includeReport:false};
let qimenResult = null;
let qimenFingerprint = null;
let qimenInput = null, qimenFocus = null, qimenTicket = 0;  // the moment the chart shown was cast for; the control to focus once it draws; the latest cast
let currentHourUnknown = false;  // the chart was generated with "不知道出生时辰" ticked
let hourCandidates = null;       // {key, rows}: the same birth day cast at each of the twelve double hours
// Qimen is cast for the moment of a question or event, which is usually now, not the birth time.
// zone: set when a date-scan chart is opened here (scan: true) or a chart steps to another hour; basis: the birth's
// time basis kept when stepping from the birth moment; lateZi: the day boundary those charts keep (null follows the
// birth panel), so a scan card opens as the same chart and a step keeps the rule of the chart shown.
let qimenMoment = {mode: 'now', custom: '', zone: '', basis: null, lateZi: null, scan: false, birthKey: null};
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
let officerResult = null, officerPending = false, officerError = '';
let timelineResult = null;
let decisionResult = null;
let dayunResult = null;
let boundaryResult = null;
let dayunDraft = {periods: 10, direction_override: ''};
let dayunPick = null;  // the decade shown in detail on the luck-pillar page; null: the one today falls in
let dayunKey = null, dayunPending = false, dayunError = '';  // the request the shown periods belong to
let dayunAxisScroll = null;  // {key, left}: where the luck axis was scrolled to, kept while the same decade is shown
// The month pillars opened under a year ({key, year, pillar, months}), the request out for them ({key, year}, compared by
// identity so a reply to an earlier request is dropped) and its failure ({key, year, text}); the days opened under one of
// those months the same way ({key, year, month, jie, pillar, days}, a request {key, year, month}, a failure with its text).
let dayunMonths = null, dayunMonthsLoad = null, dayunMonthsError = null;
let dayunDays = null, dayunDaysLoad = null, dayunDaysError = null;
// The hours opened under one of those days ({key, date, day_pillar, day_boundary, hours}, a request {key, date}, a failure
// with its text), and the day whose card takes the Tab stop in the grid (the arrow keys move it).
let dayunHours = null, dayunHoursLoad = null, dayunHoursError = null, dayunDayCursor = null;
const FLOW_MONTH_LAST_YEAR = 2099;  // the supported range ends here; a later year's months are not offered
const FLOW_HOUR_LAST_DATE = '2099-12-31';  // and the last day whose hours are worked out
let boundaryDraft = {uncertainty_minutes: 60};
let qualityMinutesDraft = 15;
let qualityRun = null;  // the birth and window the shown audit was asked for
let reportDraft = {lunar_year: null, include_time_audit: false, include_deep_evidence:true,
  include_dayun:false, dayun_direction_override:'', birth_boundary_minutes:''};
let windowDraft = {radius: 30, spacing: 10};
let lunarInverseDraft = null;  // filled with this lunar year's first day when the calendar first shows it
let lunarInverseError = '';
let annualDraft = null;  // today's lunar year, until another one is asked for
let officerDraft = {start_date:localToday(),days:30};
let timelineDraft = {start_lunar_year:null,years:10,focus_palace:''};  // null: today's lunar year
let timelineView = 'matrix';  // the palace-by-year grid, or the list by year
// The example comparison shows in the interface language until anything in it is changed.
const DECISION_EXAMPLE = {question:'比较两种实现方案',criteria:[{name:'交付速度',weight:2},{name:'维护成本',weight:3}], options:[{name:'方案 A',ratings:[4,2]},{name:'方案 B',ratings:[3,5]}]};
let decisionDraft = JSON.parse(JSON.stringify(DECISION_EXAMPLE)), decisionExampleShown = JSON.stringify(DECISION_EXAMPLE);
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
// A hover, focus and tap hint drawn by tips.js in place of the browser's own title tooltip.
function tip(node, text) {
  node.setAttribute('data-tip', String(text));
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
  return container;
}
// Time zones: the common ones first, then every IANA zone the browser knows, by region, each with its offset today.
// A zone still missing (a profile saved in another browser, a search result) is added rather than dropped: a select
// set to a value it does not list goes blank, and the chart then fails with an unknown time zone.
function ensureZone(select, zone) {
  if (zone && ![...select.options].some(o => o.value === zone)) append(select, 'option', null, zone).value = zone;
}
function copyZones(select, zone) {
  select.classList.add('zone-select');
  select.append(...[...$('#timezone').children].map(node => node.cloneNode(true)));
  ensureZone(select, zone);
  if (zone) select.value = zone;
}
// Chromium lists some zones under their old CLDR names; the list shows the current IANA name (the server takes both).
const RENAMED_ZONES = {
  'Africa/Asmera': 'Africa/Asmara', 'America/Buenos_Aires': 'America/Argentina/Buenos_Aires',
  'America/Catamarca': 'America/Argentina/Catamarca', 'America/Coral_Harbour': 'America/Atikokan',
  'America/Cordoba': 'America/Argentina/Cordoba', 'America/Godthab': 'America/Nuuk',
  'America/Indianapolis': 'America/Indiana/Indianapolis', 'America/Jujuy': 'America/Argentina/Jujuy',
  'America/Louisville': 'America/Kentucky/Louisville', 'America/Mendoza': 'America/Argentina/Mendoza',
  'Asia/Calcutta': 'Asia/Kolkata', 'Asia/Katmandu': 'Asia/Kathmandu', 'Asia/Rangoon': 'Asia/Yangon',
  'Asia/Saigon': 'Asia/Ho_Chi_Minh', 'Atlantic/Faeroe': 'Atlantic/Faroe', 'Europe/Kiev': 'Europe/Kyiv',
  'Pacific/Enderbury': 'Pacific/Kanton', 'Pacific/Ponape': 'Pacific/Pohnpei', 'Pacific/Truk': 'Pacific/Chuuk',
};
function fillTimeZones() {
  const tz = $('#timezone');
  let zones = [];
  try {zones = Intl.supportedValuesOf('timeZone');} catch (_) {return;}
  if (!zones.length) return;
  zones = [...new Set(zones.map(zone => RENAMED_ZONES[zone] || zone))].sort();
  // Moving the options out and back loses the selection (the last one moved would stay selected), so keep it.
  const chosen = tz.value, common = elt('optgroup'); common.label = '常用';
  common.append(...tz.children); tz.append(common); tz.value = chosen;
  const listed = new Set([...tz.options].map(o => o.value)), now = new Date(), groups = new Map();
  zones.forEach(zone => {
    if (listed.has(zone)) return;
    const region = zone.includes('/') ? zone.split('/')[0] : 'Etc';
    if (!groups.has(region)) {const group = elt('optgroup'); group.label = region; groups.set(region, group);}
    let offset = '';
    try {offset = new Intl.DateTimeFormat('en-US', {timeZone: zone, timeZoneName: 'shortOffset'}).formatToParts(now).find(part => part.type === 'timeZoneName').value.replace('GMT', 'UTC');}
    catch (_) { /* the zone name alone */ }
    append(groups.get(region), 'option', null, zone.replace(/_/g, ' ') + (offset ? ' · ' + offset : '')).value = zone;
  });
  groups.forEach(group => tz.append(group));
}
fillTimeZones();
// Daylight saving: a clock time in the hour that repeats when the clocks go back happened twice, and one in the hour
// skipped when they go forward never showed on the clock. Either is asked about rather than guessed. The server decides
// (the browser's own zone data can be older than the server's, and they disagreed for New Zealand, Moldova and older
// years): its refusal names the two offsets the clock could have shown, the page asks which one, and the answer is sent
// with the birth time (the server reads an explicit offset as that instant). It is kept only for the clock time and
// zone it was chosen for.
// Old local mean times have offsets with seconds (Riyadh +03:06:52); they are kept, not rounded to the minute.
const offsetText = minutes => {
  const a = Math.round(Math.abs(minutes) * 60), pad = n => String(n).padStart(2, '0');
  return (minutes < 0 ? '-' : '+') + pad(Math.floor(a / 3600)) + ':' + pad(Math.floor(a % 3600 / 60)) + (a % 60 ? ':' + pad(a % 60) : '');
};
const offsetMinutes = text => {const m = /^([+-])(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(text); return m ? (m[1] === '-' ? -1 : 1) * (Number(m[2]) * 60 + Number(m[3]) + Number(m[4] || 0) / 60) : null;};
// The server's refusal of a repeated or skipped clock time, with the two offsets it names (before and after the change).
function serverDstCase(message, local, zone) {
  const m = /(Ambiguous|nonexistent) daylight-saving[^(]*\(UTC offsets ([+-][\d:]+) or ([+-][\d:]+)\)/.exec(message || '');
  const offsets = m ? [offsetMinutes(m[2]), offsetMinutes(m[3])] : [];
  if (!m || offsets.includes(null) || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(local)) return null;
  return {kind: m[1] === 'Ambiguous' ? 'repeat' : 'skip', offsets, local, zone};
}
function chosenOffset() {
  const box = $('#utc_offset');
  return box.value && box.dataset.for === $('#birth_datetime').value + '|' + $('#timezone').value ? box.value : '';
}
function showDstChoice(info) {
  const box = $('#dst-choice'); box.replaceChildren(); box.hidden = false; box.dataset.for = info.local + '|' + info.zone;
  append(box, 'p', 'dst-choice-title', info.kind === 'repeat'
    ? '这个钟表时间在当地拨回时钟时出现了两次，请选按哪一次排盘：'
    : '这个钟表时间在当地拨快时钟时被跳过了，当时的钟表上没有这一刻。请核对出生记录，或选按哪个偏移理解：').id = 'dst-choice-title';
  const row = append(box, 'div', 'dst-choice-actions');
  info.offsets.forEach((off, i) => {
    const button = append(row, 'button', 'tiny-button'); button.type = 'button'; button.id = 'dst-choice-' + i;
    if (info.kind === 'repeat') texts(button, i ? '较晚的一次' : '较早的一次', ' · UTC' + offsetText(off));
    else {
      // A skipped time read with one offset is an instant when the clock already showed the other one, so the clock
      // read the typed time moved by their difference; the date too when that is another day (Samoa skipped 30 December 2011).
      const at = new Date(Date.parse(info.local + ':00Z') + (info.offsets[1 - i] - off) * 60000).toISOString();
      const shown = (at.slice(0, 10) === info.local.slice(0, 10) ? '' : at.slice(0, 10) + ' ') + at.slice(11, 16);
      texts(button, i ? '按拨钟后的偏移' : '按拨钟前的偏移', ' UTC' + offsetText(off) + ' · ', '相当于', ' ' + shown);
    }
    button.addEventListener('click', () => {
      box.hidden = true; box.replaceChildren();
      // The choice was made for one clock time and zone; if either has changed since (a city preset, 时辰不详, a lunar
      // date), the new values are checked afresh instead.
      if ($('#birth_datetime').value !== info.local || $('#timezone').value !== info.zone) {form.requestSubmit(); return;}
      const keep = $('#utc_offset'); keep.value = offsetText(off); keep.dataset.for = info.local + '|' + info.zone;
      form.requestSubmit();
    });
  });
  append(box, 'p', 'field-help', '所选偏移只用于这一个钟表时间，改动出生时间或时区后需要重新选择。');
  $('#dst-choice-0').focus();
}
// The choice belongs to the clock time and zone it was asked for: any edit of the form takes it away.
function hideStaleDstChoice() {
  const box = $('#dst-choice');
  if (!box.hidden && box.dataset.for !== $('#birth_datetime').value + '|' + $('#timezone').value) box.hidden = true;
}
['input', 'change'].forEach(type => form.addEventListener(type, hideStaleDstChoice));
function readInput() {
  return {
    birth_datetime: $('#birth_datetime').value + chosenOffset(),
    timezone: $('#timezone').value,
    gender: $('#gender').value,
    late_zi_day_rollover: $('#late_zi_day_rollover').checked,
    leap_month_second_half_as_next: $('#leap_month_second_half_as_next').checked,
    time_mode: $('#time_mode').value,
    longitude: $('#longitude').value.trim() === '' ? null : Number($('#longitude').value),
  };
}
function setInput(data) {
  // A birth time saved with the offset chosen for a daylight-saving hour puts the offset back beside the clock time.
  const offset = typeof data.birth_datetime === 'string' && /([+-]\d{2}:\d{2}(?::\d{2})?|Z)$/.exec(data.birth_datetime.slice(16));
  if (offset) data = {...data, birth_datetime: data.birth_datetime.slice(0, 16)};
  if (offset && offset[1] === 'Z') offset[1] = '+00:00';
  for (const name of ['birth_datetime', 'timezone', 'gender']) {
    const control = $('#' + name);
    if (typeof data[name] === 'string') {
      if (name === 'timezone') ensureZone(control, data[name]);
      control.value = data[name];
    }
  }
  const keep = $('#utc_offset'); keep.value = offset ? offset[1] : ''; keep.dataset.for = offset ? data.birth_datetime + '|' + data.timezone : '';
  $('#dst-choice').hidden = true;
  $('#late_zi_day_rollover').checked = !!data.late_zi_day_rollover;
  $('#leap_month_second_half_as_next').checked = data.leap_month_second_half_as_next !== false;
  $('#time_mode').value = data.time_mode || 'clock';
  $('#longitude').value = data.longitude ?? '';
  updateGeoControls();
  updateDemoBirthWarning();
  updateStaleBirthNotice();
}
// Server messages a person can act on, in the page's own words; any other message is shown as it comes.
function friendlyError(message) {
  if (/Ambiguous daylight-saving/.test(message)) return '这个钟表时间在当地拨回时钟时出现了两次，需要指明当时的 UTC 偏移。';
  if (/nonexistent daylight-saving/.test(message)) return '这个钟表时间在当地拨快时钟时被跳过了，请核对出生时间。';
  if (/Unknown IANA timezone/.test(message)) return '时区无效或为空，请在时区里重新选择。';
  if (/Supported birth years/.test(message)) return '出生年份需在 1901–2099 之间。';
  return message;
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
    // A message a person can act on replaces the raw one in every form; the raw text stays on the error for callers
    // that read it (the birth form opens its daylight-saving choice from it).
    const friendly=friendlyError(detail), error=new Error(friendly!==detail?friendly:`HTTP ${response.status}：${detail}`);
    error.detail=detail;
    throw error;
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
  const basis = qimenMoment.mode === 'custom' && qimenMoment.basis || {time_mode: 'clock', longitude: null};
  const lateZi = qimenMoment.mode === 'custom' && typeof qimenMoment.lateZi === 'boolean' ? {late_zi_day_rollover: qimenMoment.lateZi} : {};
  return {...base, birth_datetime: when, timezone: (qimenMoment.mode === 'custom' && qimenMoment.zone) || browserZone() || base.timezone, ...basis, ...lateZi};
}
function renderQimen() {
  if (qimenResult && qimenFingerprint && qimenFingerprint !== JSON.stringify(readInput())) qimenResult = null;
  // An hour stepped to from the birth moment keeps the birth zone and solar time only while the birth data stays the same.
  if (qimenMoment.birthKey && qimenMoment.birthKey !== JSON.stringify(readInput())) {
    qimenMoment = {mode: 'birth', custom: '', zone: '', basis: null, lateZi: null, scan: false, birthKey: null}; qimenResult = null; qimenFingerprint = null;
  }
  title(result, '奇门遁甲 · 时家拆补转盘', '九宫 · 三元局数 · 地盘 / 天盘 / 暗干 / 门 / 星 / 神');
  append(result, 'p', 'info-inline', '奇门按事情发生或提问的时刻起局，默认取此刻。不是出生预测；本模块仅实现一套明确的时家拆补转盘配置。');
  const row = append(result, 'div', 'inline-control');
  const modeLabel = append(row, 'label', null, '起局时刻');
  const mode = append(modeLabel, 'select'); mode.id = 'qimen-moment';
  [['now', '此刻'], ['custom', '指定时间'], ['birth', '出生时间']].forEach(([value, text]) => {const op = append(mode, 'option', null, text); op.value = value;});
  mode.value = qimenMoment.mode;
  mode.addEventListener('change', () => {qimenMoment = {...qimenMoment, mode: mode.value, zone: '', basis: null, lateZi: null, scan: false, birthKey: null}; qimenResult = null; qimenFingerprint = null; qimenTicket++; render();});
  if (qimenMoment.mode === 'custom') {
    const whenLabel = append(row, 'label', null, '日期与时间');
    const when = append(whenLabel, 'input'); when.type = 'datetime-local'; when.id = 'qimen-when';
    when.value = qimenMoment.custom || localMinute();
    when.addEventListener('change', () => {qimenMoment.custom = when.value; qimenTicket++; if (qimenResult) {qimenResult = null; render();}});
  }
  const run = append(row, 'button', null, '排布九宫'); run.id='qimen-run'; run.type='button';
  const zone = qimenMoment.mode === 'custom' && qimenMoment.zone, scan = zone && qimenMoment.scan;
  const basis = qimenMoment.mode === 'custom' && qimenMoment.basis;
  if (basis) texts(append(result, 'small', 'field-help'), {mean_solar: '沿用出生资料的平太阳时起局，时区', apparent_solar: '沿用出生资料的真太阳时起局，时区'}[basis.time_mode], ' ', zone);
  else append(result, 'small', 'field-help', qimenMoment.mode === 'birth' ? '沿用出生资料里的时区、真太阳时和换日规则。'
    : (zone ? (scan ? '按择日扫描所用时区 ' : '按时区 ') + zone : '按本机时区 ' + (browserZone() || readInput().timezone)) + ' 的钟表时间起局。');
  if (scan) append(result, 'small', 'field-help', '与择日扫描一致，按 00:00 换日。');
  if (qimenMoment.mode === 'birth' && $('#hour_unknown').checked) append(result, 'p', 'inline-msg', '出生时辰不详：12:00 只是占位，用它起出的奇门盘没有意义。');
  const message = append(result, 'p', 'inline-msg'); message.id = 'qimen-message';
  run.addEventListener('click', () => {
    const input = qimenMomentInput(), birth = qimenMoment.mode === 'birth';
    castQimen(input, {}, () => {qimenFingerprint = birth ? JSON.stringify(input) : null;}, null);
  });
  if (!qimenResult) return;
  const q=qimenResult;
  const palaceLabel = n => {const p = q.palaces.find(x => x.number === n); return p ? n + ' · ' + p.trigram + '宫' : String(n);};
  // Two-character labels, so each translates as a whole word (a lone 日 or 时 inside a phrase does not).
  meta(result,[(q.instant || '').replace('T', ' ').slice(0, 16), q.solar_term, q.dun + q.bureau + '局', q.yuan, '日柱 ' + q.day_pillar, '时柱 ' + q.hour_pillar].filter(Boolean));
  if (q.day_hours && q.day_hours.length) renderQimenDay(q);
  rules(result,[
    {label:'旬首 / 六仪', value:q.xun_head + ' · ' + q.xun_instrument},
    {label:'值符星及宫位', value:q.zhi_fu_star, detail:palaceLabel(q.zhi_fu_palace)},
    {label:'值使门及宫位', value:q.zhi_shi_door, detail:palaceLabel(q.zhi_shi_palace)},
    {label:'空亡地支', value:q.void_branches.join('、')},
  ]);
  append(result, 'p', 'qimen-legend', '每宫右侧一列自上而下：天干、暗干、地干。');
  const board=append(result,'div','qimen-board');
  const order=[4,9,2,3,5,7,8,1,6];
  order.forEach(n=>{
    const p=q.palaces.find(x=>x.number===n);
    const zhifu=p.number===q.zhi_fu_palace, zhishi=p.number===q.zhi_shi_palace;
    const cell=append(board,'div','qimen-cell' + (n===5?' center':'') + (p.void?' empty':'') + (zhifu?' zhifu':'') + (zhishi?' zhishi':''));
    // Palace name and direction as their own words, so each translates whole; the centre reads 中央, not 中.
    const name = append(cell, 'strong'); name.append(n + ' · '); append(name, 'span', null, p.trigram + '宫');
    name.append(' · '); append(name, 'span', null, p.direction === '中' ? '中央' : p.direction);
    // Traditional reading order: deity over star over door, heaven stem over earth stem.
    const grid=append(cell,'div','qimen-grid');
    const pair=(label,name,stemLabel,stem)=>{
      const left=append(grid,'div','q-name'); append(left,'span','q-label',label); left.append(name || '—');
      const right=append(grid,'div','q-stem'); if(stemLabel){append(right,'span','q-label',stemLabel); append(right,'span',stemClass(stem),stem).dataset.noI18n='';}
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
// One cast at a time: the run button, an hour of the day strip and the day arrows all draw through here, and a
// cast overtaken by a later one is dropped. ``done`` records how the chart came about once it has arrived.
async function castQimen(input, extra, done, focusId) {
  const ticket = ++qimenTicket, run = $('#qimen-run');
  if (run) run.disabled = true;
  const box = $('#qimen-message'); if (box) {box.className = 'inline-msg progress'; box.textContent = '正在起局…';}
  try {
    const chart = await postJSON('/api/qimen', {moment: input, include_day_hours: true, ...extra});
    if (ticket !== qimenTicket) return;
    const used = chart.stepped ? {...input, birth_datetime: chart.stepped.moment} : input;
    qimenResult = chart; qimenInput = used; done(used); qimenFocus = focusId; render();
  } catch (e) {
    if (ticket !== qimenTicket) return;
    const msg = $('#qimen-message'); if (msg) {msg.className = 'inline-msg'; msg.textContent = '奇门排盘失败：' + e.message;}
    const b = $('#qimen-run'); if (b) b.disabled = false;
  }
}
// The day of the chart shown, once per double hour: a click casts that hour, the arrows move a day at the same hour.
function renderQimenDay(q) {
  const hours = q.day_hours, day = q.day_hours_date || hours[0].moment.slice(0, 10);
  const solar = !!qimenInput && (qimenInput.time_mode === 'mean_solar' || qimenInput.time_mode === 'apparent_solar');
  const head = append(result, 'div', 'qh-head');
  append(head, 'h4', 'subheading', '当日十二时辰');
  append(head, 'b', 'qh-date', day);
  append(head, 'small', 'muted', '局数、时柱与值符、值使；点时辰起该时辰的盘');
  const nav = append(head, 'div', 'qh-nav');
  [['← 前一天', -1, 'qimen-prev-day', day <= '1901-01-01'], ['后一天 →', 1, 'qimen-next-day', day >= '2099-12-31']].forEach(([label, days, id, edge]) => {
    const b = append(nav, 'button', 'tiny-button', label); b.type = 'button'; b.id = id; b.disabled = edge;
    b.addEventListener('click', () => castQimen(qimenInput, {step_days: days}, follow, id));
  });
  if (q.stepped && !q.stepped.hour_kept) {
    const moved = append(result, 'p', 'field-help ic-missing');
    texts(moved, '这一天的夏令时切换使所选时辰没有能唯一确定的钟表时间，改起最近的时辰：'); append(moved, 'span', null, hourSlotName({label: q.stepped.hour}));
  }
  const strip = append(result, 'div', 'qh-hours'); strip.id = 'qimen-hours';
  strip.setAttribute('role', 'group'); strip.setAttribute('aria-label', '当日各时辰');
  hours.forEach((h, i) => {
    const prev = hours[i - 1], changed = prev && (prev.dun !== h.dun || prev.bureau !== h.bureau);
    const cell = append(strip, 'button', 'qh-hour' + (h.current ? ' is-current' : ''));
    cell.type = 'button'; cell.id = 'qimen-hour-' + h.index;
    if (h.current) cell.setAttribute('aria-current', 'true');
    append(cell, 'span', 'qh-name', hourSlotName(h));
    const gz = append(cell, 'b', 'qh-gz'); gz.dataset.noI18n = '';
    append(gz, 'span', stemClass(h.hour_pillar[0]), h.hour_pillar[0]); append(gz, 'span', branchClass(h.hour_pillar[1]), h.hour_pillar[1]);
    // A clock time on another calendar day (solar time, or late Zi past midnight) carries its date.
    append(cell, 'small', 'qh-clock', (h.moment.slice(0, 10) === day ? '' : h.moment.slice(5, 10).replace('-', '/') + ' ') + h.moment.slice(11, 16));
    append(cell, 'small', 'qh-bureau' + (changed ? ' is-new' : ''), h.dun + h.bureau + '局');
    if (changed) append(cell, 'span', 'visually-hidden', '局数与上一时辰不同');
    texts(append(cell, 'small', 'qh-duty'), h.zhi_fu_star, ' · ', h.zhi_shi_door);
    if (h.current) append(cell, 'small', 'qh-tag', '本盘');
    cell.addEventListener('click', () => castQimen({...qimenInput, birth_datetime: h.moment}, {}, follow, cell.id));
  });
  const help = append(result, 'p', 'field-help qh-help', '局数加粗：与上一时辰不同。');
  if (solar) help.append(' ', '格子里写的是钟表时间，按所选太阳时换算后落在该时辰里。');
  if (q.missing_hours && q.missing_hours.length) {
    const gone = append(result, 'p', 'field-help ic-missing');
    texts(gone, '这天的夏令时切换跳过或重复了一段钟表时间，没有能唯一确定的时刻落在这些时辰里，未列出：');
    enumList(gone, q.missing_hours.map(label => hourSlotName({label})));
  }
  if (qimenFocus) {
    const target = document.getElementById(qimenFocus); qimenFocus = null;
    (target && !target.disabled ? target : strip.querySelector('.is-current') || strip).focus();
  }
  // A cast from here keeps the zone and time basis of the chart shown, so a birth-moment chart steps in its own solar
  // time; only a chart opened from a date scan keeps its own day-change rule, the rest follow the birth panel.
  function follow(used) {
    const scan = qimenMoment.mode === 'custom' && qimenMoment.scan;
    qimenMoment = {mode: 'custom', custom: used.birth_datetime, zone: used.timezone, lateZi: scan ? !!used.late_zi_day_rollover : null, scan,
      basis: used.time_mode === 'clock' ? null : {time_mode: used.time_mode, longitude: used.longitude},
      birthKey: qimenMoment.birthKey || (qimenMoment.mode === 'birth' ? qimenFingerprint : null)};
    qimenFingerprint = null;
  }
}
// The optional iztro-py page: whether the engine is installed (with install steps when it is not), the request
// form, and the result drawn as a board, an item-by-item comparison with XuanShu's own chart, the period layers
// and the provider's raw output. Field names are read in snake_case or camelCase; whatever is not recognised
// stays in the raw output, and branch or stem keys such as "ziEarthly" are shown as their characters.
let professionalSent = null, professionalError = null, professionalTicket = 0, professionalPending = false, professionalOnlyDiff = true, professionalRecheck = false;
let professionalHourDraft = 12;
const PF_BRANCH = {zi: '子', chou: '丑', yin: '寅', mao: '卯', chen: '辰', si: '巳', wu: '午', wei: '未', shen: '申', you: '酉', xu: '戌', hai: '亥'};
const PF_STEM = {jia: '甲', yi: '乙', bing: '丙', ding: '丁', wu: '戊', ji: '己', geng: '庚', xin: '辛', ren: '壬', gui: '癸'};
const PF_INSTALL = 'python -m pip install "iztro-py>=0.1,<1"', PF_INSTALL_SOURCE = 'python -m pip install ".[professional]"';
const PF_LAYERS = [['decadal', '大限'], ['age', '小限'], ['yearly', '流年'], ['monthly', '流月'], ['daily', '流日'], ['hourly', '流时']];
// 禄权科忌 as single characters; they stay characters in every language, like the transformation badges.
const PF_HUA = ['化禄', '化权', '化科', '化忌'].map(t => t.slice(1)), PF_HUA_CLASS = ['lu', 'quan', 'ke', 'ji'];
const pfGet = (o, ...keys) => {if (!o || typeof o !== 'object') return undefined; for (const k of keys) if (o[k] !== undefined && o[k] !== null) return o[k]; return undefined;};
const pfText = v => typeof v === 'string' ? v : typeof v === 'number' ? String(v) : '';
const pfBranch = v => {const s = pfText(v); return BRANCH_ORDER.includes(s) && s.length === 1 ? s : PF_BRANCH[s.replace(/Earthly$/, '')] || '';};
const pfStem = v => {const s = pfText(v); return STEM_ORDER.includes(s) && s.length === 1 ? s : PF_STEM[s.replace(/Heavenly$/, '')] || '';};
const pfCjk = s => /[一-鿿]/.test(pfText(s));
const pfPalaceName = s => pfText(s).replace(/宫$/, '');
// One palace under the names different books use (iztro-py's own aliases): 交友 / 奴仆 for 仆役, 事业 for 官禄.
const PF_PALACE_ALIAS = {交友: '仆役', 奴仆: '仆役', 事业: '官禄'};
const pfSamePalace = (a, b) => (PF_PALACE_ALIAS[a] || a) === (PF_PALACE_ALIAS[b] || b);
// iztro's time index: 0 early Zi (00:00–00:59), 1 丑 … 11 亥, 12 late Zi (23:00–23:59). The server sends 23:00 as
// early Zi on the same day, or as late Zi when the birth uses the 23:00 day change.
const PF_HOURS = ['早子时', '丑时', '寅时', '卯时', '辰时', '巳时', '午时', '未时', '申时', '酉时', '戌时', '亥时', '晚子时'];
const pfHourLabel = (h, nextDay) => String(h).padStart(2, '0') + ':00 · ' + calT(h === 23 ? (nextDay ? '子时（按次日）' : '子时（按当天）') : PF_HOURS[Math.floor((h + 1) / 2)]);
// The Zi-hour rule the server used, shown only when the chart's own hour is 23.
const pfLateZi = r => pfText(pfGet(r.time_basis, 'effective_local_reading')).slice(11, 13) !== '23' ? ''
  : ' · ' + calT(r.late_zi_rule === 'next_day' ? '23:00 换日，按次日排' : '23:00 不换日，按当天排');
const pfStars = (palace, ...keys) => {const list = pfGet(palace, ...keys); return Array.isArray(list) ? list.filter(s => s && typeof s === 'object' && pfText(s.name)) : [];};
// The four transformations as written on a star: 禄, 化禄 or lu.
const pfHua = v => {const s = pfText(v).replace(/^化/, ''); return PF_HUA.includes(s) ? s : PF_HUA[PF_HUA_CLASS.indexOf(s)] || s;};

// The provider's palaces by branch, or null when they cannot be placed.
function pfPalaces(natal) {
  const list = pfGet(natal, 'palaces');
  if (!Array.isArray(list)) return null;
  const byBranch = {};
  list.forEach(p => {const b = pfBranch(pfGet(p, 'earthly_branch', 'earthlyBranch')); if (b && !byBranch[b]) byBranch[b] = p;});
  return Object.keys(byBranch).length === 12 ? byBranch : null;
}
// Item-by-item comparison with the native chart: palace names and stems, the major stars and their brightness,
// the birth-year transformations and where each star both engines place lands. Stars only one engine places are
// counted, not marked as differences.
function pfCompare(byBranch, z) {
  const rows = [], extra = new Set(), missing = new Set();
  const add = (kind, where, native, provider, same = native === provider) => rows.push({kind, where: [].concat(where), native, provider, same});
  const located = {};
  Object.entries(byBranch).forEach(([b, p]) => ['major_stars', 'majorStars', 'minor_stars', 'minorStars', 'adjective_stars', 'adjectiveStars']
    .forEach(k => (Array.isArray(p[k]) ? p[k] : []).forEach(s => {if (s && pfText(s.name) && !located[s.name]) located[s.name] = {branch: b, star: s};})));
  z.palaces.forEach(np => {
    const p = byBranch[np.branch], where = [np.branch, np.name];
    if (pfCjk(pfGet(p, 'name'))) {const ours = pfPalaceName(np.name), theirs = pfPalaceName(pfGet(p, 'name')); add('宫名', where, ours, theirs, pfSamePalace(ours, theirs));}
    const stem = pfStem(pfGet(p, 'heavenly_stem', 'heavenlyStem'));
    if (stem) add('宫干', where, np.stem, stem);
    const major = pfStars(p, 'major_stars', 'majorStars');
    add('主星', where, [...np.main_stars].sort().join('、') || '—', major.map(s => s.name).sort().join('、') || '—');
    major.forEach(s => {
      const theirs = pfText(s.brightness), ours = (np.star_brightness || {})[s.name];
      if (theirs && ours && np.main_stars.includes(s.name)) add('亮度', [...where, s.name], ours, theirs);
    });
  });
  // Birth-year transformations: the star each of 禄权科忌 falls on.
  const ours = Object.fromEntries((z.birth_year_transformations || []).map(t => [t.type.replace(/^化/, ''), t.star]));
  const theirs = {};
  Object.values(located).forEach(({star}) => {const h = pfHua(star.mutagen); if (PF_HUA.includes(h)) theirs[h] = star.name;});
  const nativeBranch = name => (z.palaces.find(np => np.main_stars.includes(name)) || {}).branch || (z.star_positions || {})[name];
  if (Object.keys(theirs).length) PF_HUA.forEach(h => {
    add('生年四化', '化' + h, ours[h] || '—', theirs[h] || '—');
    rows[rows.length - 1].marks = [nativeBranch(ours[h]), (located[theirs[h]] || {}).branch];
  });
  Object.entries(z.star_positions || {}).forEach(([name, branch]) => {
    if (z.palaces.some(np => np.main_stars.includes(name))) return;  // the major stars are compared above
    if (located[name]) add('辅星落宫', name, branch, located[name].branch); else missing.add(name);
  });
  Object.keys(located).forEach(name => {if (!(name in (z.star_positions || {}))) extra.add(name);});
  return {rows, extra: [...extra], missing: [...missing]};
}
// Pieces joined by a separator: a lone branch in its element colour, the rest translated one by one.
function pfPieces(parent, pieces, separator) {
  pieces.forEach((piece, k) => {if (k) parent.append(separator); ganzhiValue(parent, piece);});
  return parent;
}
function pfCopyCommand(parent, command, id, name) {
  const line = append(parent, 'div', 'pf-command');
  const code = append(line, 'code', null, command); code.dataset.noI18n = '';
  const copy = append(line, 'button', 'tiny-button', '复制'); copy.type = 'button'; copy.id = id; copy.dataset.idle = '复制';
  copy.setAttribute('aria-label', name);
  copy.addEventListener('click', () => reportCopy(copy, copy, command, code, '已复制'));
}
// Server replies are in English; the common ones are said in plain words. Kept as pieces (a sentence, then the
// provider's own words), so the sentence follows the interface language when the page is drawn again.
function pfErrorText(message) {
  if (/Optional local provider unavailable/.test(message)) return ['本机没有安装 iztro-py，没有生成任何近似盘。'];
  if (/requires gender/.test(message)) return ['专业引擎按性别定大限顺逆，请先在出生信息里选择男或女。'];
  if (/target_date must be between/.test(message)) return ['目标日期要在 1901 到 2099 年之间。'];
  const failed = /Professional Zi Wei provider calculation failed: (.*)/.exec(message);
  if (failed) return ['专业引擎计算失败，提供方的原话：', failed[1]];
  return ['专业引擎暂不可用：', message];
}
function renderProfessionalZiwei() {
  title(result, '专业紫微 · iztro-py（可选）', '第二套独立引擎的完整星盘与运限 · 与玄枢原生盘逐项对照 · 不混入原生数据');
  ensureCapabilities();
  const ready = capabilities && !capabilitiesError ? capabilities.professional_ziwei_provider_available === true : null;
  const status = append(result, 'section', 'pf-status'); status.id = 'professional-status'; status.tabIndex = -1;
  const head = append(status, 'div', 'pf-status-head');
  const recheck = () => {const b = append(head, 'button', 'tiny-button', '重新检测'); b.type = 'button'; b.id = 'professional-recheck';
    b.disabled = capabilitiesPending; b.addEventListener('click', () => {capabilities = null; professionalRecheck = true; ensureCapabilities(); render(); $('#professional-status').focus();});};
  if (capabilities === null) {status.classList.add('is-wait'); append(head, 'b', null, '正在检测本机是否装有 iztro-py…');}
  else if (capabilitiesError) {
    status.classList.add('is-fail');
    append(head, 'b', null, '无法确认本机是否装有 iztro-py');
    recheck();
    append(status, 'p', 'field-help', calT('读取服务能力失败：') + capabilitiesError + (capabilitiesError === 'HTTP 401' ? calT('，请检查 API 访问令牌。') : '。'));
  } else if (ready) {
    status.classList.add('is-ok');
    append(head, 'b', null, '本机已装有 iztro-py');
    append(head, 'span', 'pf-status-meta', 'MIT 许可证 · 独立于玄枢原生引擎 · 结果单独输出');
  } else {
    status.classList.add('is-missing');
    append(head, 'b', null, '本机还没有安装可选的 iztro-py 引擎');
    recheck();
    append(status, 'p', null, '这一页用第二套独立实现的紫微引擎重排一次，用来逐项核对玄枢的原生盘；不装它，原生功能照常可用。');
    const have = append(status, 'div', 'pf-have');
    append(have, 'b', null, '不装也已经有：');
    const list = append(have, 'ul', 'pf-have-list');
    ['十二宫、十四主星与 44 颗辅星杂曜，主星和六颗辅星的亮度', '生年四化、宫干飞化、四组十二神与虚岁小限', '大限、流年、流月、流日、流时与流曜（紫微页上方切换）'].forEach(t => append(list, 'li', null, t));
    const open = append(have, 'button', 'tiny-button', '打开原生紫微盘'); open.type = 'button'; open.id = 'professional-open-ziwei';
    open.addEventListener('click', () => {const tab = tabs.find(t => t.dataset.tab === 'ziwei'); activateTab(tab); tab.focus({preventScroll: true});});
    const steps = append(status, 'ol', 'pf-steps');
    const one = append(steps, 'li');
    append(one, 'span', null, '在运行玄枢的同一个 Python 环境里安装：');
    pfCopyCommand(one, PF_INSTALL, 'professional-copy-install', '复制安装命令');
    append(one, 'span', 'field-help', '在源码目录里也可以：');
    pfCopyCommand(one, PF_INSTALL_SOURCE, 'professional-copy-source', '复制源码目录里的安装命令');
    append(steps, 'li', null, '装好后点「重新检测」；仍显示未安装时，重启玄枢服务再检测。');
    append(status, 'p', 'field-help', '安装需要联网下载这个包；排盘计算在本机进行，不会把出生资料发给第三方。');
  }
  if (professionalRecheck && capabilities !== null) {professionalRecheck = false; announce(calT(head.querySelector('b').textContent));}

  const input = readInput(), hourUnknown = $('#hour_unknown') && $('#hour_unknown').checked;
  const genderOk = input.gender === 'male' || input.gender === 'female';
  const form = append(result, 'div', 'pf-form');
  const row = append(form, 'div', 'inline-control pf-row');
  const label = append(row, 'label', null, '目标日期（流年 / 流月 / 流日）');
  const date = append(label, 'input'); date.type = 'date'; date.id = 'professional-target'; date.value = professionalTargetDraft; date.min = '1901-01-01'; date.max = '2099-12-31';
  const hourLabel = append(row, 'label', null, '目标时刻（流时）');
  const hour = append(hourLabel, 'select'); hour.id = 'professional-hour';
  for (let h = 0; h < 24; h++) {const o = append(hour, 'option', null, pfHourLabel(h, input.late_zi_day_rollover)); o.value = String(h); o.selected = h === professionalHourDraft;}
  hour.disabled = !professionalTargetDraft;
  const quick = append(row, 'div', 'pf-quick');
  const today = append(quick, 'button', 'tiny-button', '今天'); today.type = 'button'; today.id = 'professional-today';
  const natalOnly = append(quick, 'button', 'tiny-button', '只看本命'); natalOnly.type = 'button'; natalOnly.id = 'professional-natal-only';
  natalOnly.disabled = !professionalTargetDraft;
  date.addEventListener('input', () => {professionalTargetDraft = date.value; hour.disabled = natalOnly.disabled = !date.value;});
  hour.addEventListener('change', () => {professionalHourDraft = Number(hour.value);});
  today.addEventListener('click', () => {professionalTargetDraft = date.value = localToday(); hour.disabled = natalOnly.disabled = false; date.focus();});
  natalOnly.addEventListener('click', () => {professionalTargetDraft = date.value = ''; hour.disabled = natalOnly.disabled = true; date.focus();});
  const run = append(row, 'button', null, professionalPending ? '正在计算…' : '计算专业盘'); run.id = 'professional-run'; run.type = 'button';
  run.disabled = professionalPending || ready === false || !genderOk || hourUnknown;
  if (!genderOk) {
    const guard = append(form, 'p', 'inline-msg pf-guard', '专业引擎按性别定大限顺逆，请先在出生信息里选择男或女。'); guard.id = 'professional-gender';
    const go = append(guard, 'button', 'tiny-button', '去选择性别'); go.type = 'button'; go.id = 'professional-go-gender';
    go.addEventListener('click', () => focusBirthField('gender'));
  } else if (hourUnknown) {
    append(form, 'p', 'inline-msg pf-guard', '出生时辰不详：命宫和十二宫都由时辰决定，按占位时辰排出的专业盘没有意义，请填写出生时辰后再算。').id = 'professional-hour-unknown';
  } else if (ready === false) append(form, 'p', 'field-help', '装好 iztro-py 并重新检测后才能计算。');
  if (professionalError) {const msg = texts(append(form, 'p', 'inline-msg'), ...professionalError); msg.id = 'professional-error'; msg.tabIndex = -1;}
  run.addEventListener('click', async () => {
    professionalPending = true; professionalError = null; render();
    const sent = readInput(), target = professionalTargetDraft || null, ticket = ++professionalTicket;
    let reply = null, error = null;
    try {
      reply = await postJSON('/api/ziwei-professional', {birth: sent, target_date: target, target_hour: professionalHourDraft});
    } catch (e) {
      error = e;
    }
    // A chart cast or cleared meanwhile makes this reply out of date: drop it instead of drawing it over the new state.
    if (ticket !== professionalTicket) return;
    if (error) {
      professionalError = pfErrorText(error.message);
      // A reply saying the engine is missing means the status shown is out of date.
      if (/Optional local provider unavailable/.test(error.message)) capabilities = null;
    } else {professionalResult = reply; professionalSent = sent;}
    professionalPending = false;
    if (active === 'professional') {
      render();
      // Back on the run button, or on the error when the reply has disabled it.
      const back = $('#professional-run');
      if (back && !back.disabled) back.focus(); else if ($('#professional-error')) $('#professional-error').focus();
    }
    announce(calT(professionalError ? '专业盘计算失败' : '专业盘已算好'));
  });
  if (!professionalResult) return;
  renderProfessionalResult(professionalResult);
}
function renderProfessionalResult(r) {
  const natal = r.natal || {}, horoscope = r.horoscope;
  const sameChart = !!current && JSON.stringify(professionalSent) === JSON.stringify(currentInput);
  const stale = JSON.stringify(professionalSent) !== JSON.stringify(readInput());
  const head = append(result, 'section', 'pf-result'); head.id = 'professional-result';
  append(head, 'h3', 'subheading', '专业盘结果');
  if (stale) append(head, 'p', 'info-inline', '出生资料改过了，下面是按改之前的资料算的；点「计算专业盘」重算。').id = 'professional-stale';
  const timeIndex = Number(r.time_index);
  meta(head, [r.provider + ' · ' + r.license, calT('排盘日期') + ' ' + r.effective_calendar_date,
    calT('时辰序号') + ' ' + r.time_index + (Number.isInteger(timeIndex) && PF_HOURS[timeIndex] ? ' · ' + calT(PF_HOURS[timeIndex]) : '') + pfLateZi(r),
    r.target_date ? calT('运限目标') + ' ' + r.target_date : calT('只算本命')]);
  // Basic facts the provider gives, in its own words.
  const facts = [['阳历', 'solar_date', 'solarDate'], ['农历', 'lunar_date', 'lunarDate'], ['四柱', 'chinese_date', 'chineseDate'],
    ['时辰', 'time', 'time'], ['五行局', 'five_elements_class', 'fiveElementsClass'], ['命主', 'soul', 'soul'], ['身主', 'body', 'body'],
    ['命宫地支', 'earthly_branch_of_soul_palace', 'earthlyBranchOfSoulPalace'], ['身宫地支', 'earthly_branch_of_body_palace', 'earthlyBranchOfBodyPalace'],
    ['生肖', 'zodiac', 'zodiac'], ['星座', 'sign', 'sign']]
    .map(([name, a, b]) => [name, pfText(pfGet(natal, a, b))]).filter(([, v]) => v);
  const byBranch = pfPalaces(natal);
  const majorNames = byBranch ? Object.values(byBranch).flatMap(p => pfStars(p, 'major_stars', 'majorStars').map(s => s.name)) : [];
  const comparable = !!byBranch && majorNames.some(pfCjk) && sameChart && !!current.ziwei;
  const c = comparable ? pfCompare(byBranch, current.ziwei) : null, diff = c ? c.rows.filter(x => !x.same) : [];
  const diffBranches = new Set(diff.flatMap(x => [x.where[0], ...(x.kind === '辅星落宫' ? [x.native, x.provider] : x.marks || [])]).filter(b => BRANCH_ORDER.includes(b || '-')));
  const boardWrap = byBranch ? append(head, 'div', 'pf-board-wrap') : null;
  if (boardWrap) {boardWrap.setAttribute('role', 'region'); boardWrap.setAttribute('aria-label', '专业盘十二宫图'); append(boardWrap, 'p', 'ziwei-scroll-hint', '← 左右滑动查看完整十二宫 →');}
  const board = boardWrap ? append(boardWrap, 'div', 'pf-board') : null;
  const factBox = append(board || head, facts.length ? 'dl' : 'div', 'pf-facts'); factBox.id = 'professional-facts';
  if (board) {factBox.style.gridRow = '2 / 4'; factBox.style.gridColumn = '2 / 4';}
  facts.forEach(([name, value]) => {append(factBox, 'dt', null, name); const dd = append(factBox, 'dd', null, pfBranch(value) || value); if (!pfCjk(dd.textContent)) dd.dataset.noI18n = '';});
  if (!facts.length) append(factBox, 'p', 'muted', '提供方没有给出基本信息字段。');
  if (board) {
    board.id = 'professional-board';
    BRANCH_ORDER.split('').forEach((b, index) => {
      const p = byBranch[b];
      const cell = append(board, 'div', 'pf-palace' + (pfGet(p, 'is_body_palace', 'isBodyPalace') ? ' is-shen' : '') + (pfBranch(pfGet(natal, 'earthly_branch_of_soul_palace', 'earthlyBranchOfSoulPalace')) === b ? ' is-ming' : ''));
      cell.id = 'professional-palace-' + b;
      if (diffBranches.has(b)) cell.classList.add('has-diff');
      cell.style.gridRow = String(ZIWEI_CELLS[index][0]); cell.style.gridColumn = String(ZIWEI_CELLS[index][1]);
      const top = append(cell, 'div', 'pf-palace-head');
      const name = append(top, 'b', 'pf-palace-name', pfText(pfGet(p, 'name'))); if (!pfCjk(name.textContent)) name.dataset.noI18n = '';
      if (pfGet(p, 'is_body_palace', 'isBodyPalace')) append(top, 'span', 'pf-tag', '身');
      const gz = append(top, 'span', 'pf-gz'); gz.dataset.noI18n = '';
      const stem = pfStem(pfGet(p, 'heavenly_stem', 'heavenlyStem'));
      if (stem) append(gz, 'span', stemClass(stem), stem);
      append(gz, 'span', branchClass(b), b);
      if (diffBranches.has(b)) {const mark = append(top, 'span', 'pf-diff-mark'); append(mark, 'span', null, '≠').setAttribute('aria-hidden', 'true'); append(mark, 'span', 'visually-hidden', '这一宫有与原生盘不同的项目'); tip(mark, calT('这一宫有与原生盘不同的项目'));}
      const stars = append(cell, 'div', 'pf-stars');
      const star = (s, cls) => {
        const el = append(stars, 'span', cls); const n = append(el, 'span', null, s.name); if (!pfCjk(s.name)) n.dataset.noI18n = '';
        const level = pfText(s.brightness); if (level && !brightMark(el, level)) append(el, 'small', 'pf-bright', level);
        const h = pfHua(s.mutagen); if (PF_HUA.includes(h)) append(el, 'span', 'hua hua-' + PF_HUA_CLASS[PF_HUA.indexOf(h)], h);
      };
      pfStars(p, 'major_stars', 'majorStars').forEach(s => star(s, 'pf-major'));
      pfStars(p, 'minor_stars', 'minorStars').forEach(s => star(s, 'pf-minor'));
      const adjectives = pfStars(p, 'adjective_stars', 'adjectiveStars');
      if (adjectives.length) {const adj = append(cell, 'div', 'pf-adj'); adjectives.forEach((s, k) => {if (k) adj.append(' '); const n = append(adj, 'span', null, s.name); if (!pfCjk(s.name)) n.dataset.noI18n = '';});}
      const decadal = pfGet(p, 'decadal'), range = pfGet(decadal, 'range');
      if (Array.isArray(range) && range.length === 2) texts(append(cell, 'div', 'pf-decadal'), '大限', ' ' + range[0] + '–' + range[1]);
    });
  } else if (Array.isArray(natal.palaces)) append(head, 'p', 'field-help', '提供方的宫位没有可识别的地支字段，无法排成十二宫图；完整内容见下方原始数据。');

  // Item-by-item comparison with XuanShu's own chart.
  const compare = append(result, 'section', 'pf-compare'); compare.id = 'professional-compare';
  append(compare, 'h3', 'subheading', '与玄枢原生盘逐项对照');
  if (!byBranch) append(compare, 'p', 'field-help', '宫位排不出来，无法逐项对照。');
  else if (!majorNames.some(pfCjk)) append(compare, 'p', 'field-help', '提供方输出的星名不是中文（像内部键名），无法与原生盘逐项对照；完整内容见下方原始数据。');
  else if (!sameChart || !current.ziwei) append(compare, 'p', 'field-help', '原生对照要用同一份出生资料：请先用这份资料点「生成命盘」，再计算专业盘。');
  else {
    const sum = append(compare, 'p', 'pf-compare-sum' + (diff.length ? ' has-diff' : ' is-same')); sum.id = 'professional-compare-summary';
    texts(sum, '逐项对照', ' ' + c.rows.length + ' ', '项', ' · ', '一致', ' ' + (c.rows.length - diff.length), ' · ', '不同', ' ' + diff.length);
    if (diffBranches.size) append(compare, 'p', 'field-help', '上方十二宫图里标 ≠ 的宫位有不同的项目。');
    const counts = append(compare, 'p', 'field-help');
    texts(counts, 'iztro-py 独有的星：', String(c.extra.length), ' · ', '原生独有的星：', String(c.missing.length), ' · ', '只有一方安的星不算不同。');
    if (c.extra.length || c.missing.length) {
      const more = append(compare, 'details', 'pf-only'); more.id = 'professional-only-stars';
      append(more, 'summary', null, '只有一方安的星');
      if (c.extra.length) {const p = append(more, 'p'); append(p, 'b', null, 'iztro-py 独有：'); pfPieces(append(p, 'span'), c.extra, '、');}
      if (c.missing.length) {const p = append(more, 'p'); append(p, 'b', null, '原生独有：'); pfPieces(append(p, 'span'), c.missing, '、');}
    }
    const control = append(compare, 'label', 'check-line');
    const only = append(control, 'input'); only.type = 'checkbox'; only.id = 'professional-only-diff'; only.checked = professionalOnlyDiff;
    control.append(calT('只看不同的项目'));
    only.addEventListener('change', () => {professionalOnlyDiff = only.checked; render(); const back = $('#professional-only-diff'); if (back) back.focus();});
    const shown = professionalOnlyDiff ? diff : c.rows;
    if (!shown.length) append(compare, 'p', 'pf-all-same', '全部一致：两套引擎在这些项目上的结果相同。').id = 'professional-all-same';
    else {
      const wrap = append(compare, 'div', 'table-wrap');
      const table = append(wrap, 'table', 'data-table pf-table'); table.id = 'professional-compare-table';
      const tr = append(append(table, 'thead'), 'tr');
      ['项目', '位置', '玄枢原生', 'iztro-py', '结果'].forEach(h => append(tr, 'th', null, h));
      const body = append(table, 'tbody');
      shown.forEach(x => {
        const row = append(body, 'tr', x.same ? 'is-same' : 'is-diff');
        append(row, 'th', null, x.kind);
        pfPieces(append(row, 'td'), x.where, ' · ');
        [x.native, x.provider].forEach(value => {
          const td = append(row, 'td', 'pf-value');
          if (x.kind === '亮度' && brightMark(td, value)) return;
          pfPieces(td, value.split('、'), '、');
        });
        append(row, 'td', x.same ? 'pf-ok' : 'pf-bad', x.same ? '一致' : '不同');
      });
    }
    append(compare, 'p', 'field-help', '两套引擎的流派表不同时结果也会不同（亮度的得、利、平尤其常见）；不同不代表哪一方错了，请对照所学流派的原书判断。');
  }

  // Period layers from the provider's horoscope.
  if (horoscope && typeof horoscope === 'object') {
    const sec = append(result, 'section', 'pf-horoscope'); sec.id = 'professional-horoscope';
    append(sec, 'h3', 'subheading', '运限叠加');
    texts(append(sec, 'p', 'field-help'), '运限目标', ' ' + r.target_date + ' ', pfHourLabel(Number(r.target_hour ?? professionalHourDraft), r.late_zi_rule === 'next_day'));
    const palaceList = Array.isArray(natal.palaces) ? natal.palaces : [];
    const wrap = append(sec, 'div', 'table-wrap');
    const table = append(wrap, 'table', 'data-table pf-table'); table.id = 'professional-horoscope-table';
    const tr = append(append(table, 'thead'), 'tr');
    ['运限', '干支', '命宫落在本命'].forEach(h => append(tr, 'th', null, h));
    PF_HUA.forEach(h => append(tr, 'th', null, h));
    const body = append(table, 'tbody');
    let rows = 0;
    PF_LAYERS.forEach(([key, name]) => {
      const item = horoscope[key];
      if (!item || typeof item !== 'object') return;
      rows++;
      const row = append(body, 'tr');
      append(row, 'th', null, name);
      const stem = pfStem(pfGet(item, 'heavenly_stem', 'heavenlyStem')), branch = pfBranch(pfGet(item, 'earthly_branch', 'earthlyBranch'));
      ganzhiValue(append(row, 'td'), stem && branch ? stem + branch : branch || pfText(pfGet(item, 'name')) || '—');
      const index = pfGet(item, 'index'), home = Number.isInteger(index) ? palaceList[index] : null;
      const at = append(row, 'td');
      if (home) pfPieces(at, [pfBranch(pfGet(home, 'earthly_branch', 'earthlyBranch')), pfText(pfGet(home, 'name'))].filter(Boolean), ' · ');
      else append(at, 'span', 'muted', '—');
      const mutagen = pfGet(item, 'mutagen');
      for (let k = 0; k < 4; k++) {const name = Array.isArray(mutagen) ? pfText(mutagen[k]) : ''; const td = append(row, 'td', null, name || '—'); if (name && !pfCjk(name)) td.dataset.noI18n = '';}
    });
    if (!rows) {table.remove(); append(sec, 'p', 'field-help', '提供方的运限没有可识别的层级字段；完整内容见下方原始数据。');}
  }

  const raw = append(result, 'details', 'pf-raw'); raw.id = 'professional-raw';
  append(raw, 'summary', null, '原始数据（iztro-py 原样输出）');
  const tools = append(raw, 'div', 'pf-raw-tools');
  const copy = append(tools, 'button', 'tiny-button', '复制 JSON'); copy.type = 'button'; copy.id = 'professional-copy-json';
  copy.addEventListener('click', async () => {
    let done = '已复制';
    try {await navigator.clipboard.writeText(JSON.stringify(r, null, 2));} catch (_) {done = '浏览器不让复制，请用「下载 JSON」';}
    copy.textContent = calT(done); announce(calT(done));
  });
  const save = append(tools, 'button', 'tiny-button', '下载 JSON ↓'); save.type = 'button'; save.id = 'professional-download-json';
  save.addEventListener('click', () => jvSave('xuanshu-ziwei-professional.json', r));
  const tree = append(raw, 'div', 'jv-tree'); tree.dataset.noI18n = '';
  raw.addEventListener('toggle', () => {if (raw.open && !tree.childNodes.length) jvNode(tree, null, r, '$', 0, null, null);});
  (r.notes || []).forEach(x => note(result, x));
}
// The reference chart is entered the way it looks: the root fields, then the nine palaces in board order with a select
// per field. Only filled fields are sent and compared; JSON stays available for pasting. The result lays XuanShu's own
// chart for the same moment over the same board and marks every compared field as matching or not.
const QA_STARS = ['天蓬', '天任', '天冲', '天辅', '天英', '天芮', '天柱', '天心', '天禽'];
const QA_DOORS = ['休门', '生门', '伤门', '杜门', '景门', '死门', '惊门', '开门'];
const QA_DEITIES = ['值符', '腾蛇', '太阴', '六合', '白虎', '玄武', '九地', '九天'];
const QA_STEMS = [...'戊己庚辛壬癸丁丙乙'];
const QA_NUMBERS = ['1', '2', '3', '4', '5', '6', '7', '8', '9'];
const QA_TERMS = ['小寒', '大寒', '立春', '雨水', '惊蛰', '春分', '清明', '谷雨', '立夏', '小满', '芒种', '夏至',
  '小暑', '大暑', '立秋', '处暑', '白露', '秋分', '寒露', '霜降', '立冬', '小雪', '大雪', '冬至'];
const QA_ROOT = [['solar_term', '节气', QA_TERMS], ['dun', '阴阳遁', ['阳遁', '阴遁']], ['bureau', '局数', QA_NUMBERS],
  ['yuan', '三元', ['上元', '中元', '下元']], ['day_pillar', '日柱', 'jiazi'], ['hour_pillar', '时柱', 'jiazi'],
  ['xun_head', '旬首', ['甲子', '甲戌', '甲申', '甲午', '甲辰', '甲寅']], ['xun_instrument', '旬首六仪', [...'戊己庚辛壬癸']],
  ['zhi_fu_star', '值符星', QA_STARS], ['zhi_fu_palace', '值符宫', QA_NUMBERS],
  ['zhi_shi_door', '值使门', QA_DOORS], ['zhi_shi_palace', '值使宫', QA_NUMBERS]];
// The board shows deity, star and door beside the heaven, hidden and earth stems, as on the Qimen page.
const QA_CELL = [['deity', '八神', QA_DEITIES], ['heaven_stem', '天干', QA_STEMS], ['star', '九星', QA_STARS],
  ['dark_stem', '暗干', QA_STEMS], ['door', '八门', QA_DOORS], ['earth_stem', '地干', QA_STEMS], ['void', '空亡', [['true', '空亡'], ['false', '不空']]]];
// Fields the form has no select for are kept from pasted JSON and still compared.
const QA_LABELS = {zhi_fu_origin: '值符原宫', zhi_shi_raw_palace: '值使原始落宫', trigram: '卦', direction: '方位', center_lodged_here: '中宫寄宫',
  ...Object.fromEntries([...QA_ROOT, ...QA_CELL].map(([key, label]) => [key, label]))};
const QA_INT = new Set(['bureau', 'zhi_fu_palace', 'zhi_shi_palace', 'zhi_fu_origin', 'zhi_shi_raw_palace']);
const QA_BOOL = new Set(['void', 'center_lodged_here']);
const QA_BOARD = {1: ['坎', '北'], 2: ['坤', '西南'], 3: ['震', '东'], 4: ['巽', '东南'], 5: ['中', '中'], 6: ['乾', '西北'], 7: ['兑', '西'], 8: ['艮', '东北'], 9: ['离', '南']};
const QA_BOOL_TEXT = {void: ['空亡', '不空'], center_lodged_here: ['中宫寄此', '不寄此']};
// Palace number, trigram and direction; the direction is its own text node so a one-character direction is translated whole.
function qaPalaceName(parent, n, trigram, direction) {
  texts(parent, n + ' · ' + trigram + '宫');
  if (n !== 5) texts(parent, ' · ', direction);
  return parent;
}
const qaValueText = (key, value) => value === null || value === undefined ? '—'
  : QA_BOOL.has(key) ? QA_BOOL_TEXT[key][value === true || value === 'true' ? 0 : 1] : String(value);
let qimenAuditDraft = null, referenceAuditChart = null, referenceAuditSent = null;
// One request at a time; a redraw while it runs keeps the button disabled, and a load or clear leaves a note for the next draw.
let qimenAuditPending = false, qimenAuditError = '', qimenAuditLoaded = null, qimenAuditUndo = null, qimenAuditJson = '';
function qimenAuditMoment(d) {
  if (d.mode === 'birth') return readInput();
  // A chosen moment depends only on itself: the birth form's gender or leap-month rule neither changes nor stales it.
  return {birth_datetime: d.custom, timezone: d.zone, gender: 'unspecified', late_zi_day_rollover: d.lateZi,
    leap_month_second_half_as_next: false, time_mode: 'clock', longitude: null};
}
const QA_TIME_MODE = {clock: '钟表时间', mean_solar: '平太阳时', apparent_solar: '真太阳时'};
// Field names the server accepts; anything else is refused when JSON is loaded, before the request.
const QA_ROOT_KEYS = new Set([...QA_ROOT.map(([key]) => key), 'zhi_fu_origin', 'zhi_shi_raw_palace']);
const QA_PALACE_KEYS = new Set([...QA_CELL.map(([key]) => key), 'trigram', 'direction', 'center_lodged_here']);
const qaCellKeys = n => QA_CELL.filter(([key]) => n !== 5 || !['deity', 'door'].includes(key));
// Draft values are the select strings; integers and yes/no fields are converted only for the request.
function qimenAuditPayload(d) {
  const cast = (key, value) => QA_INT.has(key) ? Number(value) : QA_BOOL.has(key) ? value === 'true' : value;
  const root = Object.fromEntries(Object.entries(d.root).filter(([, v]) => v !== '').map(([k, v]) => [k, cast(k, v)]));
  const palaces = Object.keys(d.palaces).map(Number).sort((a, b) => a - b).map(number =>
    ({number, ...Object.fromEntries(Object.entries(d.palaces[number]).filter(([, v]) => v !== '').map(([k, v]) => [k, cast(k, v)]))}))
    .filter(p => Object.keys(p).length > 1);
  return {moment: qimenAuditMoment(d), reference_source: d.source.trim(), reference_school: d.school.trim(), root_fields: root, palaces};
}
const qimenAuditCount = p => Object.keys(p.root_fields).length + p.palaces.reduce((n, x) => n + Object.keys(x).length - 1, 0);
function qaSelect(parent, id, label, options, value, onChange, cls, groupId) {
  const box = append(parent, 'label', cls || 'qr-field');
  append(box, 'span', 'qr-label', label).id = id + '-label';
  const select = append(box, 'select'); select.id = id;
  if (groupId) select.setAttribute('aria-labelledby', groupId + ' ' + id + '-label');
  append(select, 'option', null, '—').value = '';
  if (options === 'jiazi') jiaziOptions(select);
  else options.forEach(x => {const [value, text] = Array.isArray(x) ? x : [x, x]; append(select, 'option', null, text).value = value;});
  select.value = value || '';
  // A value loaded from JSON that is not in the list (another spelling, say) stays visible and compared as written.
  if (value && select.value !== value) {
    const odd = append(select, 'option', null, value + '（JSON）'); odd.value = value; odd.dataset.noI18n = '';
    select.value = value; box.classList.add('is-odd');
  }
  select.addEventListener('change', () => {onChange(select.value); box.classList.toggle('is-set', select.value !== '');});
  box.classList.toggle('is-set', select.value !== '');
  return select;
}
// Fields from JSON without a select of their own, each removable; they are still sent and compared.
function qaExtras(parent, fields, keys, cls) {
  const box = append(parent, 'div', cls);
  texts(box, '另有来自 JSON 的字段：');
  keys.forEach(k => {
    const item = append(box, 'span', 'qr-extra-item');
    texts(item, QA_LABELS[k] || k, ' ', qaValueText(k, fields[k]));
    const remove = append(item, 'button', 'qr-extra-remove'); remove.type = 'button';
    append(remove, 'span', null, '×').setAttribute('aria-hidden', 'true');
    texts(append(remove, 'span', 'visually-hidden'), '移除', ' ', QA_LABELS[k] || k);
    remove.addEventListener('click', () => {delete fields[k]; setTimeout(() => {render(); const next = $('.qr-extra-remove') || $('#qimen-audit-run:not(:disabled)') || $('#qimen-audit-clear'); if (next) next.focus();});});
  });
}
function renderQimenAudit() {
  if (!qimenAuditDraft) {
    const inp = readInput();
    qimenAuditDraft = {mode: 'custom', custom: localMinute(), zone: browserZone() || inp.timezone, lateZi: !!inp.late_zi_day_rollover,
      source: '', school: '', root: {}, palaces: {}};
  }
  const d = qimenAuditDraft;
  title(result, '奇门外部参考盘逐宫核验', '只比较用户提供的字段，不把缺失字段计入通过');
  const setup = append(result, 'div', 'qr-setup');
  // 1. The moment: a chosen clock time in a zone (the usual case for a chart from elsewhere) or the birth moment.
  const when = append(setup, 'section', 'qr-step'); append(when, 'h3', 'qr-step-head', '核对哪个时刻');
  const row = append(when, 'div', 'inline-control');
  const mode = append(append(row, 'label', null, '起局时刻'), 'select'); mode.id = 'qimen-audit-mode';
  [['custom', '指定时间'], ['birth', '出生时间']].forEach(([value, text]) => {append(mode, 'option', null, text).value = value;});
  mode.value = d.mode;
  mode.addEventListener('change', () => {d.mode = mode.value; setTimeout(render);});
  if (d.mode === 'custom') {
    const at = createInput('日期与时间', 'datetime-local', d.custom, row); at.id = 'qimen-audit-when';
    at.addEventListener('input', () => {d.custom = at.value; refreshCount();});
    const zone = append(append(row, 'label', null, '时区'), 'select'); zone.id = 'qimen-audit-zone';
    copyZones(zone, d.zone); zone.addEventListener('change', () => {d.zone = zone.value; refreshCount();});
    const lateLine = append(row, 'label', 'check-line'); const late = append(lateLine, 'input'); late.type = 'checkbox'; late.id = 'qimen-audit-late-zi';
    late.checked = d.lateZi; lateLine.append(' 23:00 换日'); late.addEventListener('change', () => {d.lateZi = late.checked; refreshCount();});
    append(when, 'small', 'field-help', '按这个时区的钟表时间起局。参考盘若把 23:00 以后算作次日，勾选「23:00 换日」。');
  } else {
    append(when, 'small', 'field-help', '沿用出生资料里的时区、真太阳时和换日规则。');
    if ($('#hour_unknown').checked) append(when, 'p', 'inline-msg', '出生时辰不详：12:00 只是占位，用它起出的奇门盘没有意义。');
  }
  // 2. Where the reference came from: the request needs a citation and the school it claims.
  const from = append(setup, 'section', 'qr-step'); append(from, 'h3', 'qr-step-head', '参考盘的来源');
  const fromRow = append(from, 'div', 'inline-control qr-source');
  const source = createInput('参考来源', 'text', d.source, fromRow); source.id = 'qimen-audit-source'; source.maxLength = 512;
  source.placeholder = '书名与页码、软件与版本或公开链接'; source.addEventListener('input', () => {d.source = source.value; refreshCount();});
  const school = createInput('参考流派', 'text', d.school, fromRow); school.id = 'qimen-audit-school'; school.maxLength = 120;
  school.placeholder = '参考盘自称的流派，如 时家拆补转盘、置闰法';
  school.addEventListener('input', () => {d.school = school.value; refreshCount();});
  // 3. The chart itself: root fields, then the palaces in board order (4 9 2 / 3 5 7 / 8 1 6).
  const plate = append(setup, 'section', 'qr-step'); append(plate, 'h3', 'qr-step-head', '参考盘的盘面');
  append(plate, 'small', 'field-help', '照参考盘逐项选择，看不清或参考盘没有的项目留「—」，不参与比较。');
  const root = append(plate, 'div', 'qr-root'); root.id = 'qimen-audit-root-form';
  QA_ROOT.forEach(([key, label, options]) => qaSelect(root, 'qimen-ref-' + key, label, options, d.root[key], v => {d.root[key] = v; refreshCount();}));
  const extraRoot = Object.keys(d.root).filter(k => !QA_ROOT.some(([key]) => key === k) && d.root[k] !== '');
  if (extraRoot.length) qaExtras(plate, d.root, extraRoot, 'field-help qr-extra-root');
  const board = append(plate, 'div', 'qr-board'); board.id = 'qimen-audit-board-form';
  [4, 9, 2, 3, 5, 7, 8, 1, 6].forEach(n => {
    const cell = append(board, 'fieldset', 'qr-cell' + (n === 5 ? ' center' : ''));
    const legend = qaPalaceName(append(cell, 'legend', 'qr-cell-head'), n, ...QA_BOARD[n]); legend.id = `qimen-ref-${n}-legend`;
    const fields = d.palaces[n] || (d.palaces[n] = {});
    const mark = () => cell.classList.toggle('is-filled', Object.values(fields).some(v => v !== ''));
    const grid = append(cell, 'div', 'qr-fields');
    const shown = qaCellKeys(n);
    shown.forEach(([key, label, options]) =>
      qaSelect(grid, `qimen-ref-${n}-${key}`, label, options, fields[key], v => {fields[key] = v; refreshCount(); mark();}, null, legend.id));
    // The centre palace has no deity or door; such values from JSON are listed here with the other extras.
    const extra = Object.keys(fields).filter(k => !shown.some(([key]) => key === k) && fields[k] !== '');
    if (extra.length) qaExtras(cell, fields, extra, 'qr-extra');
    mark();
  });
  // JSON for pasting a reference written elsewhere; it fills the form rather than bypassing it.
  const json = append(setup, 'details', 'qr-json'); json.id = 'qimen-audit-json';
  append(json, 'summary', null, '用 JSON 填写');
  append(json, 'p', 'field-help', '包含 reference_source、reference_school、root_fields 和 palaces，每个宫写 number=1…9 和要对照的字段；可选的 moment 会填入第 1 步的时刻。填入后可在上面的表单里检查。');
  // The example is data to copy, so its values stay as written in every interface language.
  const fieldLabel = append(json, 'label', 'visually-hidden', '参考盘 JSON'); fieldLabel.htmlFor = 'qimen-audit-input';
  const field = append(json, 'textarea', 'json-code'); field.id = 'qimen-audit-input'; field.rows = 8; field.dataset.noI18n = '';
  field.value = qimenAuditJson; field.addEventListener('input', () => {qimenAuditJson = field.value;});
  field.placeholder = JSON.stringify({reference_source: '公开参考盘链接', reference_school: '时家拆补转盘', root_fields: {bureau: 3}, palaces: [{number: 1, star: '天蓬'}]}, null, 2);
  const load = append(json, 'button', 'tiny-button', '填入表单'); load.id = 'qimen-audit-load'; load.type = 'button';
  const loadMsg = append(json, 'p', 'inline-msg'); loadMsg.id = 'qimen-audit-load-msg'; loadMsg.setAttribute('role', 'status');
  if (qimenAuditLoaded) {
    json.open = true;
    loadMsg.className = 'inline-msg ok';
    loadMsg.textContent = qimenAuditLoaded.count === 1 ? calT('已填入 1 项') : calT('已填入') + ' ' + qimenAuditLoaded.count + calT(' 项');
    qimenAuditLoaded.warnings.forEach(w => append(json, 'p', 'inline-msg', w));
    qimenAuditLoaded = null;
  }
  load.addEventListener('click', () => {
    try {
      const fail = text => {throw new Error(calT(text));};
      const ref = JSON.parse(field.value);
      if (!ref || typeof ref !== 'object' || Array.isArray(ref)) fail('需要一个 JSON 对象');
      const unknown = Object.keys(ref).filter(k => !['moment', 'reference_source', 'reference_school', 'root_fields', 'palaces'].includes(k));
      if (unknown.length) throw new Error(calT('不认识的字段') + ' ' + unknown.join(', '));
      // Values are checked as the server would: yes/no fields are true or false, numbers are 1…9.
      const asText = (k, v) => {
        if (QA_BOOL.has(k)) {if (v === true || v === 'true') return 'true'; if (v === false || v === 'false') return 'false'; throw new Error(k + ' ' + calT('需为 true 或 false'));}
        if (QA_INT.has(k)) {if (!/^[1-9]$/.test(String(v).trim())) throw new Error(k + ' ' + calT('需为 1…9 的整数')); return String(Number(v));}
        if (typeof v !== 'string' && typeof v !== 'number') throw new Error(k + ' ' + calT('需为文字'));
        return String(v);
      };
      const next = {...d, root: {}, palaces: {}}, warnings = [];
      if (typeof ref.reference_source === 'string') next.source = ref.reference_source;
      if (typeof ref.reference_school === 'string') next.school = ref.reference_school;
      // A moment in the JSON is the moment to check: it fills step 1 instead of being dropped.
      if (ref.moment !== undefined) {
        const m = ref.moment;
        if (!m || typeof m !== 'object' || typeof m.birth_datetime !== 'string') fail('moment 需含 birth_datetime');
        const local = m.birth_datetime.trim().match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})(?::00(?:\.0+)?)?$/);
        if (!local) fail('moment 的时间需写成不带时区偏移的整分钟，如 2024-02-10T10:00');
        Object.assign(next, {mode: 'custom', custom: local[1] + 'T' + local[2], zone: typeof m.timezone === 'string' ? m.timezone : 'Asia/Shanghai', lateZi: m.late_zi_day_rollover === true});
        if (m.time_mode && m.time_mode !== 'clock') warnings.push(calT('JSON 里的时刻按太阳时排盘；这里按该时区的钟表时间起局，请核对时刻。'));
      }
      if (ref.root_fields !== undefined && (!ref.root_fields || typeof ref.root_fields !== 'object' || Array.isArray(ref.root_fields))) fail('root_fields 需为对象');
      Object.entries(ref.root_fields || {}).forEach(([k, v]) => {
        if (!QA_ROOT_KEYS.has(k)) throw new Error(calT('不认识的字段') + ' ' + k);
        if (v !== null && v !== undefined) next.root[k] = asText(k, v);
      });
      if (ref.palaces !== undefined && !Array.isArray(ref.palaces)) fail('palaces 需为列表');
      (ref.palaces || []).forEach(p => {
        const n = Number(p && p.number);
        if (!Number.isInteger(n) || n < 1 || n > 9) fail('宫位 number 需为 1…9');
        if (next.palaces[n]) throw new Error(calT('宫位重复') + ' ' + n);
        next.palaces[n] = Object.fromEntries(Object.entries(p).filter(([k, v]) => {
          if (k !== 'number' && !QA_PALACE_KEYS.has(k)) throw new Error(calT('不认识的字段') + ' ' + k);
          return k !== 'number' && v !== null && v !== undefined;
        }).map(([k, v]) => [k, asText(k, v)]));
      });
      const count = Object.keys(next.root).length + Object.values(next.palaces).reduce((t, p) => t + Object.keys(p).length, 0);
      qimenAuditDraft = next; qimenAuditLoaded = {count, warnings}; qimenAuditUndo = null;
      setTimeout(() => {render(); const msg = $('#qimen-audit-load-msg'); if (msg) announce(msg.textContent);});
    } catch (e) {loadMsg.className = 'inline-msg'; loadMsg.textContent = calT('无法填入：') + e.message;}
  });
  const runRow = append(setup, 'div', 'qr-run');
  const run = append(runRow, 'button', 'scan-run', '核验参考盘'); run.id = 'qimen-audit-run'; run.type = 'button';
  const count = append(runRow, 'span', 'qr-count'); count.id = 'qimen-audit-count'; count.setAttribute('aria-live', 'polite');
  const clearAll = append(runRow, 'button', 'tiny-button', '清空盘面'); clearAll.id = 'qimen-audit-clear'; clearAll.type = 'button';
  clearAll.addEventListener('click', () => {qimenAuditUndo = {root: d.root, palaces: d.palaces}; d.root = {}; d.palaces = {}; setTimeout(() => {render(); const u = $('#qimen-audit-undo'); if (u) u.focus();});});
  // A clear can be taken back until the board is filled again.
  if (qimenAuditUndo) {
    const undo = append(runRow, 'button', 'tiny-button', '撤销清空'); undo.id = 'qimen-audit-undo'; undo.type = 'button';
    undo.addEventListener('click', () => {Object.assign(d, qimenAuditUndo); qimenAuditUndo = null; setTimeout(() => {render(); $('#qimen-audit-clear').focus();});});
  }
  const message = append(result, 'p', 'inline-msg'); message.id = 'qimen-audit-message'; message.setAttribute('role', 'alert');
  if (qimenAuditPending) {message.className = 'inline-msg progress'; message.textContent = '正在核验…';}
  else if (qimenAuditError) message.textContent = qimenAuditError;
  // The button says what is still missing instead of failing on the server; a result from other inputs says so.
  function refreshCount() {
    const payload = qimenAuditPayload(d), n = qimenAuditCount(payload), stale = $('#qimen-audit-stale');
    if (stale) stale.hidden = referenceAuditSent === JSON.stringify(payload);
    const noTime = d.mode === 'custom' && !d.custom;
    const missing = !n ? '先在盘面上选至少一项' : noTime ? '还需填写日期与时间' : d.source.trim().length < 4 ? '还需填写参考来源（至少 4 个字）' : d.school.trim().length < 2 ? '还需填写参考流派' : '';
    count.textContent = '';
    if (n === 1) texts(count, '将比较 1 项'); else if (n) texts(count, '将比较 ', n, ' 项');
    if (n && missing) count.append(' ');
    if (missing) append(count, 'span', 'qr-missing', missing);
    if (n) qimenAuditUndo = null;
    run.disabled = !!missing || qimenAuditPending;
    run.dataset.focusFallback = !missing || !n ? 'qimen-audit-mode' : noTime ? 'qimen-audit-when' : d.source.trim().length < 4 ? 'qimen-audit-source' : 'qimen-audit-school';
  }
  refreshCount();
  run.addEventListener('click', async () => {
    if (qimenAuditPending) return;
    const payload = qimenAuditPayload(d);
    qimenAuditPending = true; qimenAuditError = ''; run.disabled = true; message.className = 'inline-msg progress'; message.textContent = '正在核验…';
    try {
      const [audit, chart] = await Promise.all([postJSON('/api/qimen-reference-audit', payload), postJSON('/api/qimen', {moment: payload.moment})]);
      referenceAuditResult = {...audit, xsMode: d.mode}; referenceAuditChart = chart; referenceAuditSent = JSON.stringify(payload);
    } catch (e) {qimenAuditError = calT('核验失败：') + e.message;}
    finally {qimenAuditPending = false;}
    if (active !== 'qimen-audit') return;
    render();
    // After a failure the keyboard returns to the button (or the field it needs); after a result, to the result.
    const target = qimenAuditError ? ($('#qimen-audit-run:not(:disabled)') || $('#' + $('#qimen-audit-run').dataset.focusFallback)) : $('#qimen-audit-result');
    if (target) target.focus();
  });
  if (!referenceAuditResult) return;
  renderQimenAuditResult(referenceAuditResult, referenceAuditChart);
  refreshCount();
}
function renderQimenAuditResult(a, chart) {
  const out = append(result, 'section', 'qr-result'); out.id = 'qimen-audit-result'; out.tabIndex = -1;
  out.setAttribute('aria-labelledby', 'qimen-audit-result-title');
  append(out, 'h3', 'subheading', '核验结果').id = 'qimen-audit-result-title';
  const stale = append(out, 'p', 'info-inline', '表单已改动，下面仍是上次核验的结果。'); stale.id = 'qimen-audit-stale'; stale.hidden = true;
  const fields = a.fields || [];
  const summary = append(out, 'div', 'qr-summary' + (a.matches ? ' is-ok' : ' is-diff'));
  const big = append(summary, 'p', 'qr-big'); append(big, 'b', null, String(a.matching)); big.append(' / ' + a.compared);
  append(summary, 'p', 'qr-verdict', a.matches ? '全部提供字段一致' : '存在差异');
  const facts = append(summary, 'div', 'qr-facts');
  const ref = texts(append(facts, 'p'), '参考盘：');
  append(ref, 'span', null, a.reference_school + ' · ' + a.reference_source).dataset.noI18n = '';
  texts(append(facts, 'p'), '玄枢：', a.local_school);
  // The moment checked, with its zone, day-change rule and time system, so a printed result says what it describes.
  const m = a.moment || {};
  const when = texts(append(facts, 'p', 'qr-moment'), '起局时刻：', (m.birth_datetime || '').replace('T', ' ').slice(0, 16), ' · ', m.timezone || '', ' · ', m.late_zi_day_rollover ? '23:00 换日' : '00:00 换日');
  if (m.time_mode && m.time_mode !== 'clock') texts(when, ' · ', QA_TIME_MODE[m.time_mode] || m.time_mode);
  if (chart) texts(append(facts, 'p'), chart.solar_term, ' · ', chart.dun + chart.bureau + '局', ' · ', chart.yuan);
  const wrong = new Set(a.mismatches.map(x => x.field));
  // The plate follows from the bureau: a different dun or bureau explains most palace differences that follow.
  if (wrong.has('dun') || wrong.has('bureau'))
    append(out, 'p', 'feature-note', '参考盘的遁局与玄枢不同：地盘干按局数排布，天盘、星、门、神也随之而定，下面各宫的差异多半由此而来。先核对参考盘的定局方法（如拆补、置闰）和所用节气时刻。');
  const rootRows = fields.filter(x => !x.field.startsWith('palaces.'));
  if (rootRows.length) {
    const table = append(append(out, 'div', 'table-wrap'), 'table', 'data-table qr-root-table'); table.id = 'qimen-audit-root';
    append(table, 'caption', 'visually-hidden', '盘面字段');
    const hr = append(append(table, 'thead'), 'tr');
    ['项目', '参考盘', '玄枢', '结果'].forEach(x => {const th = append(hr, 'th', null, x); th.scope = 'col';});
    const body = append(table, 'tbody');
    rootRows.forEach(x => {
      const tr = append(body, 'tr', x.match ? 'is-ok' : 'is-diff');
      const th = append(tr, 'th', null, QA_LABELS[x.field] || x.field); th.scope = 'row';
      append(tr, 'td', null, qaValueText(x.field, x.reference)); append(tr, 'td', null, qaValueText(x.field, x.ours));
      append(tr, 'td', 'qr-mark ' + (x.match ? 'is-ok' : 'is-diff'), x.match ? '一致' : '不同');
    });
  }
  if (chart) {
    const byPalace = {};
    fields.filter(x => x.field.startsWith('palaces.')).forEach(x => {const [, n, key] = x.field.split('.'); (byPalace[n] = byPalace[n] || {})[key] = x;});
    const board = append(out, 'div', 'qr-board qr-board-result'); board.id = 'qimen-audit-board';
    [4, 9, 2, 3, 5, 7, 8, 1, 6].forEach(n => {
      const p = chart.palaces.find(x => x.number === n), seen = byPalace[n] || {};
      const rows = Object.values(seen), bad = rows.filter(x => !x.match).length;
      const cell = append(board, 'div', 'qr-cell' + (n === 5 ? ' center' : '') + (rows.length ? (bad ? ' is-diff' : ' is-ok') : ' is-none'));
      cell.id = 'qimen-audit-palace-' + n;
      const head = append(cell, 'div', 'qr-cell-head'); qaPalaceName(append(head, 'span'), n, p.trigram, p.direction);
      append(head, 'small', 'qr-cell-score', rows.length ? (bad ? '不同 ' + bad + ' / ' + rows.length : '一致 ' + rows.length + ' / ' + rows.length) : '未对照');
      const list = append(cell, 'dl', 'qr-values');
      const shown = qaCellKeys(n);
      shown.forEach(([key, label]) => {
        const x = seen[key], line = append(list, 'div', 'qr-value' + (x ? (x.match ? ' is-ok' : ' is-diff') : ''));
        append(line, 'dt', null, label);
        const dd = append(line, 'dd');
        const ours = append(dd, 'span', 'qr-ours' + (key.endsWith('_stem') ? ' ' + stemClass(p[key]) : ''), key === 'void' ? (p.void ? '空亡' : '不空') : (p[key] || '—'));
        if (key.endsWith('_stem')) ours.dataset.noI18n = '';
        if (x && x.match) append(dd, 'span', 'qr-mark is-ok', '一致');
        if (x && !x.match) texts(append(dd, 'span', 'qr-mark is-diff'), '参考', ' ', key === 'void' ? (x.reference ? '空亡' : '不空') : qaValueText(key, x.reference));
      });
      Object.values(seen).filter(x => !shown.some(([key]) => x.field.endsWith('.' + key))).forEach(x => {
        const key = x.field.split('.').pop(), line = append(list, 'div', 'qr-value ' + (x.match ? 'is-ok' : 'is-diff'));
        append(line, 'dt', null, QA_LABELS[key] || key);
        const dd = append(line, 'dd'); append(dd, 'span', 'qr-ours', qaValueText(key, x.ours));
        if (x.match) append(dd, 'span', 'qr-mark is-ok', '一致'); else texts(append(dd, 'span', 'qr-mark is-diff'), '参考', ' ', qaValueText(key, x.reference));
      });
    });
    append(out, 'p', 'field-help', '九宫是玄枢按同一时刻排出的盘；你填过的项目标出「一致」或参考盘的写法，没填的项目只作对照，不计入结果。');
  }
  a.notes.forEach(x => note(out, x));
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
    // Each count and word is its own text, so 个 and 藏 translate as words.
    texts(append(row, 'small'), primary[name] || 0, ' 个', ...(secondary ? [' · 藏 ', secondary[name] || 0] : []));
  });
  if (secondary) {
    const legend = append(parent, 'div', 'element-legend');
    const a = append(legend, 'span'); append(a, 'i'); a.append('明干 + 地支本气');
    const b2 = append(legend, 'span'); append(b2, 'i', 'secondary'); b2.append('藏干（不加权）');
  }
}
// 五行生克: the five phases on the 相生 circle (木→火→土→金→水→木) with the 相克 star inside (木→土→水→火→金→木).
// Each node is sized by how many stems and main branch qi of the chart belong to it and names the ten gods it stands
// for from the day master. With the hour unknown the pillars that time could change are not counted, and with the
// day pillar among them there is no day master to name the ten gods from.
const TEN_GOD_GROUPS = [['比劫', '比肩、劫财'], ['食伤', '食神、伤官'], ['财星', '偏财、正财'], ['官杀', '七杀、正官'], ['印星', '偏印、正印']];
const tenGodsOf = members => members.split('、');
let wuxingFocus = null, wuxingChart = null;  // the phase selected, kept while the same chart is shown
function chartElementCounts(b) {
  const unsettled = unsettledPillars(b), keys = PILLAR_KEYS.filter(k => !unsettled.has(k)), master = !unsettled.has('day');
  const surface = {}, hidden = {}, places = {}, hiddenPlaces = {}, gods = {};
  for (const e of PHASES) {surface[e] = 0; hidden[e] = 0; places[e] = []; hiddenPlaces[e] = [];}
  TEN_GOD_GROUPS.forEach(([, members]) => tenGodsOf(members).forEach(god => {gods[god] = [];}));
  const stemAt = {year: '年干', month: '月干', day: '日干', hour: '时干'}, branchAt = {year: '年支', month: '月支', day: '日支', hour: '时支'};
  keys.forEach(key => {
    const p = b.pillars[key];
    surface[p.stem_element] += 1; places[p.stem_element].push(stemAt[key] + p.stem);
    surface[p.branch_element] += 1; places[p.branch_element].push(branchAt[key] + p.branch);
    // The ten gods of the stems (the day stem is the day master itself) and of the hidden stems.
    if (master && gods[p.ten_god_of_stem]) gods[p.ten_god_of_stem].push(stemAt[key] + p.stem);
    p.hidden_stems.forEach(h => {
      const at = h.stem + '（' + branchAt[key] + p.branch + '）';
      hidden[h.element] += 1; hiddenPlaces[h.element].push(at);
      if (master && gods[h.ten_god]) gods[h.ten_god].push(at);
    });
  });
  return {surface, hidden, places, hiddenPlaces, gods, unsettled, master: master ? b.day_master_element : null};
}
function wuxingDiagram(parent, b, counts) {
  const master = counts.master;  // null when the day pillar, and so the day master, depends on the unknown hour
  if (wuxingChart !== b) {wuxingChart = b; wuxingFocus = master || PHASES[0];}
  // The box is a size container, so that the picture and the panel stack whenever the result column is narrow.
  const wrap = append(append(parent, 'div', 'wuxing-box'), 'div', 'wuxing'); wrap.id = 'wuxing';
  // Room on both sides for the captions beside the left and right nodes, which run outwards from them, and above
  // the top node for a two-line 日主 caption.
  const W = 580, H = 410, cx = 260, cy = 220, R = 124;
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', `-30 0 ${W} ${H}`); svg.setAttribute('class', 'wuxing-svg');
  svg.setAttribute('role', 'radiogroup'); svg.setAttribute('aria-label', '五行生克图');
  wrap.append(svg);
  const make = (tag, attrs, parentNode = svg) => {
    const node = document.createElementNS(SVG_NS, tag);
    Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
    parentNode.append(node);
    return node;
  };
  const defs = make('defs', {});
  ['sheng', 'ke'].forEach(kind => {
    const marker = make('marker', {id: 'wx-arrow-' + kind, viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: 'auto-start-reverse'}, defs);
    make('path', {d: 'M0,1 L9,5 L0,9 z', class: 'wx-arrow-' + kind}, marker);
  });
  const angle = i => -Math.PI / 2 + 2 * Math.PI * i / 5;
  const pos = i => [cx + R * Math.cos(angle(i)), cy + R * Math.sin(angle(i))];
  const radius = e => 27 + Math.min(counts.surface[e], 5) * 3.4;
  const group = e => master ? TEN_GOD_GROUPS[(PHASES.indexOf(e) - PHASES.indexOf(master) + 5) % 5] : null;
  // Points on two nodes' rims facing each other, so that the arrows start and end at the discs.
  const ends = (i, j, bend = 0) => {
    const [x1, y1] = pos(i), [x2, y2] = pos(j), dx = x2 - x1, dy = y2 - y1, d = Math.hypot(dx, dy);
    const a = radius(PHASES[i]) + 4, z = radius(PHASES[j]) + 7, tilt = bend * 0.35;
    const ux = dx / d, uy = dy / d, px = -uy, py = ux;  // along the edge and across it
    return [x1 + (ux * Math.cos(tilt) - px * Math.sin(tilt)) * a, y1 + (uy * Math.cos(tilt) - py * Math.sin(tilt)) * a,
      x2 + (-ux * Math.cos(tilt) - px * Math.sin(tilt)) * z, y2 + (-uy * Math.cos(tilt) - py * Math.sin(tilt)) * z];
  };
  const edges = [];
  for (let i = 0; i < 5; i++) {
    // 相生 along the circle, bowed outwards; 相克 across it.
    [[(i + 1) % 5, 'sheng'], [(i + 2) % 5, 'ke']].forEach(([j, kind]) => {
      const edge = make('g', {class: 'wx-edge wx-' + kind});
      edge.dataset.from = PHASES[i]; edge.dataset.to = PHASES[j];
      if (kind === 'sheng') {
        const [x1, y1, x2, y2] = ends(i, j, -1), mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
        const qx = cx + (mx - cx) * 1.22, qy = cy + (my - cy) * 1.22;
        make('path', {d: `M${x1},${y1} Q${qx},${qy} ${x2},${y2}`, 'marker-end': 'url(#wx-arrow-sheng)'}, edge);
      } else {
        const [x1, y1, x2, y2] = ends(i, j);
        make('line', {x1, y1, x2, y2, 'marker-end': 'url(#wx-arrow-ke)'}, edge);
      }
      edges.push(edge);
    });
  }
  // One choice among five: a radio group with a single tab stop that the arrow keys, Home and End move.
  const select = (e, focus) => {
    wuxingFocus = e; show();
    if (focus) wrap.querySelector('#wuxing-' + ELEMENT_CLASS[e]).focus();
  };
  const nodes = PHASES.split('').map((e, i) => {
    const [x, y] = pos(i), r = radius(e), named = group(e);
    // A phase with none of the counted stems and branches gets a dashed rim, never a faded one.
    // The name read out is the phase as a word (translated like any label; no browser tooltip); the panel below says the rest.
    const node = make('g', {class: 'wx-node wx-el-' + ELEMENT_CLASS[e] + (e === master ? ' is-master' : '') + (counts.surface[e] ? '' : ' is-empty'), role: 'radio', id: 'wuxing-' + ELEMENT_CLASS[e], 'aria-label': e});
    node.dataset.element = e;
    make('circle', {cx: x, cy: y, r: r + (e === master ? 10 : 6), class: 'wx-focus-ring'}, node);
    if (e === master) make('circle', {cx: x, cy: y, r: r + 5, class: 'wx-master-ring'}, node);
    make('circle', {cx: x, cy: y, r, class: 'wx-disc'}, node);
    // The phase is drawn as its character in every language, like the pillars; the label carries the word.
    make('text', {x, y: y + 3, 'text-anchor': 'middle', class: 'wx-char ' + elementClass(e), 'data-no-i18n': ''}, node).textContent = e;
    make('text', {x, y: y + 20, 'text-anchor': 'middle', class: 'wx-count'}, node).textContent = String(counts.surface[e]);
    // The ten-god group (and 日主) outside the disc, away from the centre; none without a day master.
    if (named) {
      const out = r + 13, ox = x + Math.cos(angle(i)) * out, oy = y + Math.sin(angle(i)) * out;
      const anchor = Math.cos(angle(i)) > 0.3 ? 'start' : Math.cos(angle(i)) < -0.3 ? 'end' : 'middle';
      const top = Math.sin(angle(i)) < -0.5;
      const lines = e === master ? ['日主', named[0]] : [named[0]];
      const first = top ? oy - 7 - (lines.length - 1) * 20 : oy + (Math.sin(angle(i)) > 0.5 ? 15 : 4) - (lines.length - 1) * 10;
      const caption = make('text', {x: ox, y: first, 'text-anchor': anchor, class: 'wx-group'}, node);
      lines.forEach((text, n) => {const span = make('tspan', {x: ox, dy: n ? 20 : 0}, caption); span.textContent = text;});
    }
    node.addEventListener('click', () => select(e, false));
    node.addEventListener('keydown', event => {
      const k = PHASES.indexOf(e);
      const to = {ArrowRight: k + 1, ArrowDown: k + 1, ArrowLeft: k + 4, ArrowUp: k + 4, Home: 0, End: 4}[event.key];
      if (event.key === 'Enter' || event.key === ' ') {event.preventDefault(); select(e, false);}
      else if (to !== undefined) {event.preventDefault(); select(PHASES[to % 5], true);}
    });
    return node;
  });
  const legend = append(wrap, 'div', 'wuxing-legend');
  [['wx-key-sheng', '相生'], ['wx-key-ke', '相克'], ...(master ? [['wx-key-master', '日主']] : [])]
    .forEach(([cls, text]) => {const item = append(legend, 'span'); append(item, 'i', cls); item.append(text);});
  const detail = append(wrap, 'div', 'wuxing-detail'); detail.id = 'wuxing-detail'; detail.setAttribute('aria-live', 'polite');
  function show() {
    const e = wuxingFocus, k = PHASES.indexOf(e), named = group(e);
    nodes.forEach(node => {
      const on = node.dataset.element === e;
      node.classList.toggle('is-focus', on); node.setAttribute('aria-checked', String(on)); node.setAttribute('tabindex', on ? '0' : '-1');
    });
    edges.forEach(edge => edge.classList.toggle('is-on', edge.dataset.from === e || edge.dataset.to === e));
    detail.replaceChildren();
    const head = append(detail, 'h5');
    append(head, 'b', elementClass(e), e);
    if (named) {append(head, 'span', null, named[0]); append(head, 'small', 'muted', named[1]);}
    if (e === master) append(head, 'span', 'wuxing-master', '日主 ' + b.day_master);
    const line = (label, items) => {
      const row = append(detail, 'p', 'wuxing-line');
      append(row, 'span', 'wuxing-label', label); append(row, 'b', null, String(items.length));
      append(row, 'span', null, items.length ? items.join('、') : '—');
    };
    line('明干与地支本气', counts.places[e]);
    line('藏干', counts.hiddenPlaces[e]);
    if (named) tenGodsOf(named[1]).forEach(god => line(god, counts.gods[god]));
    // Each phase in its own element, so that it is translated as a word.
    const cycle = (label, chain) => {
      const row = append(detail, 'p', 'wuxing-line wuxing-cycle');
      append(row, 'span', 'wuxing-label', label);
      const flow = append(row, 'span', 'wuxing-flow');
      chain.forEach((x, n) => {if (n) flow.append(' → '); append(flow, 'b', elementClass(x), x);});
    };
    cycle('相生', [PHASES[(k + 4) % 5], e, PHASES[(k + 1) % 5]]);
    cycle('相克', [PHASES[(k + 3) % 5], e, PHASES[(k + 2) % 5]]);
  }
  show();
}
// Each person's five phases: how many stems and branches of the known pillars belong to each (no hidden stems; a
// pillar not known is left out), and what each phase is to that person's day master.
function personElements(p) {
  const counts = Object.fromEntries(PHASES.split('').map(e => [e, 0]));
  PILLAR_KEYS.forEach(key => {
    const text = p.pillars[key];
    if (!text) return;
    counts[STEM_ELEMENTS[STEM_ORDER.indexOf(text[0])]] += 1;
    counts[BRANCH_ELEMENTS[BRANCH_ORDER.indexOf(text[1])]] += 1;
  });
  return counts;
}
const tenGodGroupOf = (master, element) => TEN_GOD_GROUPS[(PHASES.indexOf(element) - PHASES.indexOf(master) + 5) % 5][0];
// people: [label, person] pairs. A row per person, a column per phase; the day master's phase is outlined.
function elementMatrix(parent, people, id) {
  const table = append(append(parent, 'div', 'table-wrap'), 'table', 'data-table element-matrix'); table.id = id;
  const head = append(append(table, 'thead'), 'tr');
  append(head, 'th', null, '成员').scope = 'col';
  // The phases stay characters in every language, as in the pillars, so that the five columns fit on a phone.
  // The header's name (title and aria-label) is the translated word, for hover and for screen readers.
  PHASES.split('').forEach(e => {
    const th = append(head, 'th'); th.scope = 'col'; tip(th, e); th.setAttribute('aria-label', e);
    append(th, 'b', elementClass(e), e).dataset.noI18n = '';
  });
  const body = append(table, 'tbody');
  people.forEach(([label, p]) => {
    const tr = append(body, 'tr'), counts = personElements(p);
    const who = append(tr, 'th'); who.scope = 'row'; append(who, 'span', 'user-text', label);
    if (!p.day_master_element) append(who, 'small', 'em-note', '日主未定');
    PHASES.split('').forEach(e => {
      const n = counts[e], master = e === p.day_master_element;
      const td = append(tr, 'td', 'em-cell em-' + ELEMENT_CLASS[e] + ' em-' + Math.min(n, 4) + (master ? ' em-master' : ''));
      append(td, 'b', null, String(n));
      // 日主 and its group on lines of their own, so that a narrow cell never splits a word.
      if (master) {append(td, 'small', null, '日主'); append(td, 'small', null, '比劫');}
      else if (p.day_master_element) append(td, 'small', null, tenGodGroupOf(p.day_master_element, e));
    });
  });
}
const ELEMENT_MATRIX_HELP = '每格是该成员已知各柱的天干地支属这一五行的个数（不含藏干），小字是这一五行对该成员日主而言的十神类别；日主所在的五行加框。时辰不详不计时柱，当天交节或换日而不定的柱也不计；日柱也不定时写「日主未定」，不标十神。';
// The five phases of each person as text rows, for the text copy.
const elementRows = people => textColumns([['', ...PHASES.split('')], ...people.map(([name, p]) => {
  const counts = personElements(p);
  return [name, ...PHASES.split('').map(e => String(counts[e]))];
})]);
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
// A mark is a relation and the natal pillar it is with: 冲月, or 日空 for the day pillar's void. It stays two characters
// in Chinese and Japanese (沖月、害時 in 繁體, 害時 in Japanese) and reads Clash M in English; the translator leaves
// the badges alone, so each keeps its source and is relabelled when the language changes. The words live here rather
// than in the dictionary, where a one-character entry would rename every text that is just 合 or 空.
const MARK_WORDS = {合: 'Combine', 冲: 'Clash', 刑: 'Punish', 害: 'Harm', 同: 'Same', 空: 'Void'};
const MARK_PILLARS = {年: 'Y', 月: 'M', 日: 'D', 时: 'H'};
function markLabel(text) {
  const lang = typeof uiLang === 'undefined' ? 'zh-CN' : uiLang;
  if (lang === 'ja') return text.replace(/时/, '\u6642');  // 時
  if (lang !== 'en') return calT(text);
  const [relation, pillar] = MARK_PILLARS[text[0]] ? [text[1], text[0]] : [text[0], text[1]];
  return MARK_WORDS[relation] + ' ' + MARK_PILLARS[pillar];
}
const calendarMark = text => exportLang() ? markLabel(text) : text;
function natalMarks(parent, n) {
  const marks = natalMarkList(n);
  if (!marks.length) return;
  const line = append(parent, 'span', 'luck-marks'); line.setAttribute('data-no-i18n', '');
  marks.forEach(([text, kind]) => {append(line, 'span', 'luck-mark link-' + kind, markLabel(text)).dataset.mark = text;});
}
document.addEventListener('xuanshu-language', () => document.querySelectorAll('.luck-mark[data-mark]').forEach(mark => {mark.textContent = markLabel(mark.dataset.mark);}));
function natalText(n) {
  const parts = [n.growth_stage && '星运 ' + n.growth_stage, '自坐 ' + n.self_stage, '纳音 ' + n.na_yin].filter(Boolean);
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
    if (d.natal_interactions) {natalMarks(btn, d.natal_interactions); tip(btn, natalText(d.natal_interactions));}
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
    tip(btn, supported ? '在紫微盘打开 ' + y + ' 年流年层' : '超出 1901–2099 的计算范围');
    append(btn, 'small', null, String(y));
    const chars = append(btn, 'span', 'luck-pair');
    append(chars, 'b', stemClass(pillar[0]), pillar[0]); append(chars, 'b', branchClass(pillar[1]), pillar[1]);
    append(btn, 'small', 'luck-god', tenGodOf(b.day_master, pillar[0]));
    const age = append(btn, 'small', 'luck-age'); age.append('虚龄'); age.append(' ' + (y - birthYear + 1));
    if (info) {append(btn, 'small', 'luck-stage', info.growth_stage); natalMarks(btn, info); tip(btn, y + ' ' + pillar + ' · ' + natalText(info) + ' · ' + btn.getAttribute('data-tip'));}
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
      tip(mark, p.void_of.map(k => k === 'day' ? '落在日柱旬空' : '落在年柱旬空').join('；'));
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
    else p.shensha.forEach(x => {const tag = append(sha, 'span', 'shensha-tag', x.name); tip(tag, shenshaBasis(x));});
  }
  pillarLinks(result, links.branches, true);
  renderLuckStrip(result, b);
  const counts = chartElementCounts(b);
  append(result, 'h4', 'subheading', '五行生克');
  wuxingDiagram(result, b, counts);
  append(result, 'p', 'field-help', '外圈箭头是相生，内圈虚线是相克；圆的大小和其中的数字是明干与地支本气的个数，圆外是该五行对日主而言的十神类别。点一个五行看它在四柱里的位置和生克关系，方向键可以逐个切换。');
  if (currentHourUnknown) append(result, 'p', 'field-help', wuxingUnsettledNote(counts.unsettled));
  append(result, 'h4', 'subheading', '五行分布');
  elementBars(result, counts.surface, counts.hidden);
  append(result, 'h4', 'subheading', '地支关系标签与藏干统计');
  const relationBox = append(result, 'div', 'relationship-grid');
  (b.stem_relations || []).filter(x => x.labels.length).forEach(x => append(relationBox, 'div', 'symbol-tag', `${nameMap[x.a]}·${nameMap[x.b]} ${x.stems} ${x.labels.join(' / ')}`));
  b.branch_relations.filter(x => x.labels.length).forEach(x => append(relationBox, 'div', 'symbol-tag', `${nameMap[x.a]}·${nameMap[x.b]} ${x.branches} ${x.labels.join(' / ')}`));
  (b.branch_groups || []).forEach(g => append(relationBox, 'div', 'symbol-tag', `${g.pillars.map(k => nameMap[k]).join('·')} ${g.branches} ${g.kind}（${g.element}）`));
  if (!relationBox.childElementCount) append(relationBox, 'p', 'info-inline', '当前四柱无所列特定关系标签');
  append(result, 'p', 'info-inline', '星运是日主在各柱地支的十二长生，自坐是各柱天干在本柱地支的十二长生（阳干顺行、阴干逆行，火土同宫）；空亡是各柱所在旬余下的两个地支，地支上的「日空」「年空」表示它落在日柱或年柱的旬空里。');
  renderShenshaRules(result, b);
  // From the same pillars as the picture and the bars, so that an unknown hour leaves the same pillars out here too.
  const cnt = PHASES.split('').map(e => `${e}${counts.hidden[e]}`).join(' · ');
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
const SHENSHA_BASIS = {day_stem: '日干', year_stem: '年干', day_branch: '日支', year_branch: '年支', month_branch: '月支', day_pillar: '日柱', year_nayin: '年柱纳音'};
const shenshaBasis = star => '查法起点：' + star.by.map(x => SHENSHA_BASIS[x.basis] + ' ' + x.value).join('、');
// With the hour unknown any time of the birth day is possible, so the noon placeholder's hour pillar is not known;
// a jie inside that day changes the month pillar (立春 the year pillar too), and the 23:00 day change or a solar-time
// shift can move the day pillar. A cautious reading, off the chart alone, of the first-and-last-minute check in app/group.py.
// The UTC offset (minutes east) of a zone at a wall-clock minute of a date, from the browser's zone data.
function zoneOffsetAt(zone, date, minute, guess) {
  try {
    const format = new Intl.DateTimeFormat('en-US', {timeZone: zone, hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'});
    const wallOf = instant => {const p = {}; format.formatToParts(new Date(instant)).forEach(x => {p[x.type] = x.value;}); return Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour % 24, +p.minute);};
    const wall = Date.parse(date + 'T00:00:00Z') + Math.floor(minute) * 60000;
    let offset = guess;
    for (let i = 0; i < 2; i++) offset = (wallOf(wall - offset * 60000) - (wall - offset * 60000)) / 60000;
    return offset;
  } catch (_) {return guess;}
}
// With the hour unknown the chart stands on a placeholder time, and the day the engine counts can still move: a solar
// time ahead of or behind the clock, or the 23:00 day change, can carry the first or last moment of the birth date
// into the day before or after. Day offsets (as the engine counts them: the effective date, plus one from 23:00 with
// the 23:00 change) of the first moment, the placeholder and the last moment. In solar time the shift follows the
// zone offset, so a clock-change day is counted with the offset in force at each end.
function birthDayOffsets(b) {
  const t = currentInput.birth_datetime, date = t.slice(0, 10), here = +t.slice(11, 13) * 60 + +t.slice(14, 16);
  const basis = b.time_basis, shift = basis.effective_shift_minutes || 0, base = basis.civil_utc_offset_minutes || 0;
  const at = minute => {
    const zone = basis.mode === 'clock' ? 0 : base - zoneOffsetAt(currentInput.timezone, date, minute, base);
    const e = minute + shift + zone, d = Math.floor(e / 1440);
    return d + (currentInput.late_zi_day_rollover && e - d * 1440 >= 1380 ? 1 : 0);
  };
  return {first: at(0), here: at(here), last: at(1440 - 1 / 60)};
}
function unsettledPillars(b) {
  const out = new Set();
  if (!currentHourUnknown) return out;
  out.add('hour');
  const day = currentInput.birth_datetime.slice(0, 10);
  [b.jie_boundaries.previous, b.jie_boundaries.next].filter(j => j.instant.slice(0, 10) === day).forEach(j => {
    out.add('month');
    if (j.name === '立春') out.add('year');
  });
  const days = birthDayOffsets(b);
  if (days.first !== days.here || days.last !== days.here) out.add('day');
  return out;
}
// The stars those pillars place are then not settled either.
function shenshaUnsettled(b) {return unsettledPillars(b).size > 1;}
// The four transformations follow the lunar year's stem. With the day depending on the hour, the year is open when
// the day can move across the lunar new year: forward past the end of the twelfth month, or back past the first
// day of the first month, by as many days as the first or last moment of the birth date moves.
function lunarYearOpen(b, z) {
  if (!unsettledPillars(b).has('day')) return false;
  const lunar = z.lunar_date, days = birthDayOffsets(b);
  return (days.last > days.here && lunar.month === 12 && lunar.month_days - lunar.day < days.last - days.here)
    || (days.first < days.here && lunar.month === 1 && !lunar.is_leap_month && lunar.day <= days.here - days.first);
}
// Which pillars the five-phase counts leave out with the hour unknown, as one sentence per case (each translated whole).
function wuxingUnsettledNote(unsettled) {
  const year = unsettled.has('year'), month = unsettled.has('month'), day = unsettled.has('day');
  if (day && year) return '时辰不详：时柱按 12:00 占位；出生当天立春，又按 23:00 换日或按太阳时换算，年柱、月柱、日柱都随时辰而定。这四柱都不计入，日主未定，也不标十神。';
  if (day && month) return '时辰不详：时柱按 12:00 占位；出生当天交节，又按 23:00 换日或按太阳时换算，月柱、日柱随时辰而定。这三柱都不计入，日主未定，也不标十神。';
  if (day) return '时辰不详：时柱按 12:00 占位；按 23:00 换日或按太阳时换算，日柱也随时辰而定。这两柱都不计入，日主未定，也不标十神。';
  if (year) return '时辰不详：时柱按 12:00 占位；出生当天立春，年柱、月柱随时辰而定。这三柱都不计入。';
  if (month) return '时辰不详：时柱按 12:00 占位；出生当天交节，月柱随时辰而定。这两柱都不计入。';
  return '时辰不详，时柱按 12:00 占位，不计入。';
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
  if (!found.length) {append(parent, 'p', 'info-inline', currentHourUnknown ? '已知的年、月、日三柱没有所收二十一种神煞。' : '四柱没有所收二十一种神煞。'); return;}
  const table = append(append(parent, 'div', 'table-wrap'), 'table', 'data-table shensha-table'); table.id = 'shensha-rules';
  const head = append(append(table, 'thead'), 'tr');
  ['神煞', '所在', '查法', '出处'].forEach(x => {append(head, 'th', null, x).scope = 'col';});
  const body = append(table, 'tbody');
  (b.shensha_rules || []).filter(r => found.some(x => x.name === r.name)).forEach(r => {
    const tr = append(body, 'tr');
    append(tr, 'td', 'shensha-name', r.name);
    const where = append(tr, 'td', 'shensha-places');
    // One pillar per line, so no list separator needs translating.
    found.filter(x => x.name === r.name).forEach(x => {
      const item = append(where, 'span', 'shensha-where', nameMap[x.pillar] + b.pillars[x.pillar].text); tip(item, shenshaBasis(x));
    });
    stackLabel(append(tr, 'td', 'dy-fit-cell shensha-rule'), '查法').append(r.rule);
    stackLabel(append(tr, 'td', 'muted shensha-source'), '出处').append(r.source);
  });
  // The rule is a sentence: under 12em it wraps a few characters to a line, so the rows stack instead.
  table.dataset.fitEm = '12';
  stackTable(table);
  append(parent, 'p', 'info-inline', '神煞是传统标签：只收能在古籍里查到安法的二十一种，以日干、年干、年支、日支、月支和年柱纳音查四柱，时柱不作查法起点；同一种神煞各家表格不尽相同（如阴干是否有羊刃、红艳的几干），这里按所列出处。只列名称，不断吉凶。');
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
  // The layer's one-character mark (年, 限) is drawn apart from the glyph: English shows the outlined glyph alone, and
  // the glyph translates by itself (权 is 権 in Japanese).
  const badge = append(parent, 'span', 'hua hua-' + (HUA_CLASS[type] || 'lu') + (layer ? ' layer' : ''));
  if (layer) append(badge, 'span', 'hua-layer-mark', LAYER_NAMES[layer].slice(-1));
  badge.append(type.replace('化', ''));
  tip(badge, (layer ? LAYER_NAMES[layer] : '生年') + type);
  return badge;
}
// Star brightness 庙旺得利平不陷 after the star name. The level is drawn by CSS from data-level, so each
// language shows its own short form (平 alone already means a day officer elsewhere in the interface).
const BRIGHT_LEVELS = '庙旺得利平不陷';
const BRIGHT_CLASS = Object.fromEntries([...BRIGHT_LEVELS].map((level, i) => [level, ['miao', 'wang', 'de', 'li', 'ping', 'bu', 'xian'][i]]));
function brightMark(parent, level) {
  if (!BRIGHT_CLASS[level]) return null;
  const mark = append(parent, 'span', 'bright bright-' + BRIGHT_CLASS[level]);
  mark.dataset.level = level; tip(mark, '亮度：' + level);
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
let todayLunarYear = null, todayLunarPending = false, todayLunarFailed = false;
function ensureTodayLunarYear() {
  if (todayLunarYear !== null || todayLunarPending || todayLunarFailed) return;  // a failed lookup is not retried in a loop
  todayLunarPending = true;
  postJSON('/api/calendar', {start_date: localToday(), days: 1}).then(data => {todayLunarYear = data.days[0].lunar.year;})
    .catch(() => {todayLunarFailed = true;})  // keep the estimate below
    .finally(() => {
      // Redraw only once nothing is pending, so a tool waiting for the year (annual, timeline) can run itself.
      todayLunarPending = false;
      if ((active === 'ziwei' && ziweiLayer.mode === 'year' && ziweiLayer.year === null) || (active === 'calendar' && lunarInverseDraft && lunarInverseDraft.guessed)
        || (active === 'annual' && annualDraft === null) || (active === 'timeline' && timelineDraft.start_lunar_year === null)) render();
    });
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
    pick.setAttribute('aria-pressed', String(chosen)); tip(pick, p.name);
    pick.addEventListener('click', () => {selectedPalace = p.name; render();});
    columns.forEach(c => {
      const td = append(tr, 'td', [c.anchor === index ? 'layer-ming' : '', c.key === live.mode ? 'active' : ''].join(' ').trim() || null);
      append(td, 'span', 'layer-table-name', c.name(index).replace(/宫$/, ''));
      cellHua(c, index).forEach(t => {
        const item = append(td, 'span', 'layer-table-hua'); item.append(t.star);
        const badge = append(item, 'span', 'hua hua-' + (HUA_CLASS[t.type] || 'lu') + (c.key === 'natal' ? '' : ' layer'), t.type.replace('化', ''));
        tip(badge, (c.key === 'natal' ? '生年' : c.label) + t.type);
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
      if (stacked.has(star)) {holders[star].classList.add('hua-stack'); tip(holders[star], '四化叠加：' + stacked.get(star).join('、'));}
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
      // Each name is its own text, so a one-character stage (养, 死) translates as a word.
      const line = append(node, 'div', 'palace-cycles');
      const names = gendered.map(name => [name, null]).concat(suiqian ? [[suiqian, live && live.twelve ? 'layer-cycle' : null]] : []);
      names.forEach(([name, cls], i) => {if (i) line.append(' · '); append(line, 'span', cls, name);});
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
      tip(mark, `${selected.name}：${t.star}${t.type}→${p.name}${t.self_transform ? '（自化）' : ''}`);
      marks.append(mark);
    });
    if (p.decade) append(foot, 'span', 'decade', `${p.decade.start_age}–${p.decade.end_age}岁`);
    if (p.small_limit_nominal_ages) tip(node, '小限虚岁：' + p.small_limit_nominal_ages.slice(0, 6).join('、') + '…');
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
  taijiMark(center, 'center-symbol');
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
  tip(fly, '彩色曲线：所选宫位的宫干四化飞入哪一宫');
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
// 宫干飞化 for the whole chart: each palace's stem and where its four transformations land, as a palace-per-row table
// or as a palace × palace matrix with 自化 on the diagonal. A palace picked in either shows its detail below.
let transformView = 'table';
const HUA_TYPES = ['化禄', '化权', '化科', '化忌'];
function renderTransform(z) {
  title(result, '生年四化 / 宫干飞化', '《全书》系公开十干四化表 · 流派差异需核对');
  // Near the lunar new year an unknown hour can change the year stem itself, and with it every palace stem (五虎遁).
  if (currentHourUnknown && lunarYearOpen(current.bazi, z)) {
    append(result, 'p', 'field-help', '命盘时辰不详，出生当天又在农历年的交界：日子随时辰而定，生年天干可能不同，四化星、各宫宫干和宫干飞化都随时辰而变，暂不列出。');
    note(result, '四化是星曜的传统标识，不是新增星曜；宫干飞化仅列出四化星所在宫，尚未实施完整飞星断法。');
    return;
  }
  if (currentHourUnknown) append(result, 'p', 'field-help', '命盘时辰不详：四化星由生年天干决定，不随时辰变；但它们落在哪一宫、各宫的宫干和宫干飞化都按 12:00 占位时辰排出，会随时辰而变。');
  const cards = append(result, 'div', 'transform-grid');
  z.birth_year_transformations.forEach(item => {
    const box = append(cards, 'div', 'transform-card hua-card-' + (HUA_CLASS[item.type] || 'lu'));
    const type = append(box, 'div', 'transform-type'); huaBadge(type, item.type); type.append(' ' + item.type);
    append(box, 'div', 'transform-star', item.star);
    append(box, 'div', 'transform-palace', item.palace_name + ' · ' + item.palace);
  });
  const order = PALACE_ORDER.map(name => z.palaces.find(p => p.name === name)).filter(Boolean);
  const selected = findPalace(z, selectedPalace).name;
  append(result, 'h4', 'subheading', '十二宫宫干四化总表');
  const tags = append(result, 'div', 'meta-tags');
  append(tags, 'span', null, z.transformation_school);
  texts(append(tags, 'span'), '自化', ' ×', order.reduce((n, p) => n + p.palace_flying_transformations.filter(t => t.self_transform).length, 0));
  const views = append(result, 'div', 'layer-modes fh-views');
  views.setAttribute('role', 'group'); views.setAttribute('aria-label', '显示方式');
  [['table', '按宫列表'], ['matrix', '宫位矩阵']].forEach(([key, name]) => {
    const button = append(views, 'button', 'layer-btn' + (transformView === key ? ' active' : ''), name);
    button.type = 'button'; button.id = 'transform-view-' + key; button.setAttribute('aria-pressed', String(transformView === key));
    button.addEventListener('click', () => {transformView = key; render();});
  });
  const wrap = append(result, 'div', 'fh-wrap');
  const table = append(wrap, 'table', transformView === 'table' ? 'fh-table' : 'fh-matrix'); table.id = 'transform-' + transformView;
  append(table, 'caption', 'visually-hidden', '十二宫宫干四化总表');
  const head = append(append(table, 'thead'), 'tr');
  const corner = append(head, 'th', 'fh-corner', transformView === 'table' ? '宫干支' : '宫干 → 落宫'); corner.scope = 'col';
  // The row header picks the palace shown in the detail below.
  const rowHead = (tr, p, i) => {
    const th = append(tr, 'th', 'fh-palace'); th.scope = 'row';
    const pick = append(th, 'button', 'fh-pick'); pick.type = 'button'; pick.id = 'transform-pick-' + i;
    pick.setAttribute('aria-pressed', String(p.name === selected));
    append(pick, 'span', 'fh-palace-name', p.name);
    const gz = append(pick, 'span', 'fh-gz'); gz.dataset.noI18n = '';
    append(gz, 'span', stemClass(p.stem), p.stem); append(gz, 'span', branchClass(p.branch), p.branch);
    pick.addEventListener('click', () => {selectedPalace = p.name; render();});
  };
  const body = append(table, 'tbody');
  if (transformView === 'table') {
    // The badge's own title says 生年; these are palace-stem transformations, and the header already names the type.
    HUA_TYPES.forEach(type => {const th = append(head, 'th', 'fh-type fh-' + HUA_CLASS[type]); th.scope = 'col'; huaBadge(th, type).removeAttribute('data-tip'); th.append(' ' + type);});
    order.forEach((p, i) => {
      const tr = append(body, 'tr', p.name === selected ? 'is-focus' : null);
      rowHead(tr, p, i);
      HUA_TYPES.forEach(type => {
        const t = p.palace_flying_transformations.find(x => x.type === type), td = append(tr, 'td', 'fh-cell' + (t && t.self_transform ? ' is-self' : ''));
        if (!t) {td.textContent = '—'; return;}
        append(td, 'b', 'fh-star', t.star); append(td, 'span', 'fh-arrow', '→'); append(td, 'span', 'fh-target', t.target_palace || '—');
        if (t.self_transform) append(td, 'small', 'fh-self', '自化');
      });
    });
    append(result, 'p', 'field-help', '一行一宫，按命宫、兄弟宫……父母宫的顺序；每格是该宫宫干化出的星和它所在的宫。星就在本宫时标「自化」。点宫名在下方查看该宫详情。');
  } else {
    order.forEach(q => {
      const th = append(head, 'th', 'fh-col' + (q.name === selected ? ' is-focus' : '')); th.scope = 'col';
      append(th, 'span', 'fh-palace-name', q.name);
      const n = order.reduce((m, p) => m + p.palace_flying_transformations.filter(t => t.target_palace === q.name).length, 0);
      texts(append(th, 'small', 'fh-count'), '×', n);
    });
    order.forEach((p, i) => {
      const tr = append(body, 'tr', p.name === selected ? 'is-focus' : null);
      rowHead(tr, p, i);
      order.forEach(q => {
        const td = append(tr, 'td', (p === q ? 'is-diag' : '') + (q.name === selected ? ' is-focus-col' : ''));
        const here = p.palace_flying_transformations.filter(t => t.target_palace === q.name);
        here.forEach(t => {
          const line = append(td, 'span', 'fh-hua'); tip(huaBadge(line, t.type), `${p.name}（${p.stem}干）${t.star}${t.type}→${q.name}`);
          append(line, 'span', null, t.star);
        });
        if (p === q && here.length) append(td, 'span', 'visually-hidden', '自化');
      });
    });
    append(result, 'p', 'field-help', '一行是宫干所在的宫，一列是四化星所在的宫；对角线上的格子是自化。列头的 ×N 是落入该宫的宫干四化条数。所选宫位的行和列加框。');
  }
  append(result, 'h4', 'subheading', '十二宫宫干飞化查询');
  const row = append(result, 'div', 'inline-control');
  const label = append(row, 'label', null, '选择宫位');
  const picker = append(label, 'select', null);
  order.forEach(p => {const opt = append(picker, 'option', null, p.name + ' · ' + p.stem + p.branch); opt.value = p.name;});
  picker.value = selected;
  picker.addEventListener('change', () => {selectedPalace = picker.value; render();});
  const open = append(row, 'button', 'tiny-button', '在紫微盘上看飞化线'); open.type = 'button'; open.id = 'transform-to-ziwei';
  // The board opens with the flying lines on, whatever was chosen there before, and the keyboard lands on the palace.
  open.addEventListener('click', () => {
    selectedPalace = selected; showFlying = true; flyPinned = null;
    activateTab(tabs.find(t => t.dataset.tab === 'ziwei'));
    const node = $('#palace-' + z.palaces.findIndex(p => p.name === selected));
    if (node) node.focus();
    announce(calT('紫微盘已打开宫干飞化：') + calT(selected));
  });
  renderPalacePanel(result, findPalace(z, selectedPalace));
  note(result, '四化是星曜的传统标识，不是新增星曜；宫干飞化仅列出四化星所在宫，尚未实施完整飞星断法。');
}
// 透明的文化解释: what the chart shows, field by field, in two cards that open the pages with the full detail. With
// the hour unknown nothing that depends on it is stated as known: the pillars the day could change are marked, and
// the Zi Wei palaces, all placed from the hour, are left out.
function renderReading(reading) {
  title(result, '透明的文化解释', '计算字段 → 传统标签 → 适用范围');
  const b = current.bazi, z = current.ziwei, counts = chartElementCounts(b), unsettled = counts.unsettled;
  const grid = append(result, 'div', 'reading-grid');
  const card = (id, heading, tab, label, before) => {
    const box = append(grid, 'section', 'reading-card'); box.id = id;
    const head = append(box, 'div', 'reading-head'); append(head, 'h4', null, heading);
    const go = append(head, 'button', 'reading-go', label); go.type = 'button'; go.id = id + '-open';
    go.addEventListener('click', () => {if (before) before(); openTab(tab);});
    return box;
  };
  // Keyboard focus goes to the tab of the page opened, rather than falling back to the start of the document.
  const openTab = name => {const tab = tabs.find(t => t.dataset.tab === name); activateTab(tab); tab.focus({preventScroll: true});};
  // A labelled row whose value is built from separate nodes, so that fixed words and chart values translate apart.
  const row = (box, label) => {const line = append(box, 'div', 'reading-row'); append(line, 'span', 'reading-label', label); return append(line, 'span', 'reading-value');};
  const bazi = card('reading-bazi', '八字四柱', 'bazi', '打开四柱八字');
  const pillars = append(bazi, 'div', 'reading-pillars');
  PILLAR_KEYS.forEach(key => {
    const cell = append(pillars, 'div', 'reading-pillar' + (key === 'day' && counts.master ? ' is-master' : '')), p = b.pillars[key];
    append(cell, 'small', null, nameMap[key]);
    const text = append(cell, 'b', 'reading-gz'); text.dataset.noI18n = '';
    if (unsettled.has(key)) {text.textContent = '?'; append(cell, 'small', 'muted', key === 'hour' ? '时辰不详' : '随时辰而定');}
    else {append(text, 'span', stemClass(p.stem), p.stem); append(text, 'span', branchClass(p.branch), p.branch);}
  });
  const master = row(bazi, '日主');
  if (counts.master) {append(master, 'b', elementClass(b.day_master_element), b.day_master + ' · ' + b.day_master_element); append(master, 'span', 'muted', '十神都以日主为参照，不是对个人特征的科学判断。');}
  else append(master, 'span', 'muted', '日柱随时辰而定，日主未定，十神暂不标注。');
  const phases = row(bazi, '明干与地支本气');
  // With every pillar open nothing is counted, which reads better said than as five zeros.
  if (PHASES.split('').every(e => !counts.surface[e])) append(phases, 'span', 'muted', '四柱都不计入');
  else PHASES.split('').forEach(e => {const chip = append(phases, 'span', 'reading-chip'); append(chip, 'b', elementClass(e), e); chip.append(' ' + counts.surface[e]);});
  if (currentHourUnknown) append(bazi, 'p', 'field-help', wuxingUnsettledNote(unsettled));
  const ziwei = card('reading-ziwei', '紫微斗数', 'ziwei', '打开紫微斗数', () => {selectedPalace = '命宫';});
  const yearOpen = lunarYearOpen(b, z);
  const hua = (box, withPalace) => {
    const value = row(box, '生年四化');
    if (yearOpen) {
      append(value, 'span', 'muted', '随时辰而定');
      append(box, 'p', 'field-help', '出生当天在农历年的交界，日子随时辰而定，生年天干可能不同，四化星暂不列出。');
      return;
    }
    z.birth_year_transformations.forEach(t => {
      const chip = append(value, 'span', 'reading-chip reading-hua-' + {化禄: 'lu', 化权: 'quan', 化科: 'ke', 化忌: 'ji'}[t.type]);
      append(chip, 'b', null, t.star); append(chip, 'span', null, t.type);
      if (withPalace) append(chip, 'small', null, t.palace_name);
    });
  };
  if (currentHourUnknown) {
    append(ziwei, 'p', 'field-help', yearOpen ? '紫微的命宫、身宫、五行局和十二宫星曜都由出生时辰排定，时辰不详时不列。'
      : '紫微的命宫、身宫、五行局和十二宫星曜都由出生时辰排定，时辰不详时不列；下面只有按农历生年定的四化星和身主。');
    hua(ziwei, false);
    // 身主 follows the lunar year's branch, so it is known whenever the lunar year is.
    if (!yearOpen) append(row(ziwei, '身主'), 'b', null, z.shen_master);
    append(ziwei, 'p', 'field-help', z.transformation_school);
  } else {
    const palace = flag => z.palaces.find(p => p[flag]);
    [['命宫', palace('is_ming')], ['身宫', palace('is_shen')]].forEach(([label, p]) => {
      const value = row(ziwei, label);
      append(value, 'b', null, p.name + ' · ' + p.stem + p.branch);
      if (!p.main_stars.length) append(value, 'span', 'muted', '空宫');
      p.main_stars.forEach(star => {const chip = append(value, 'span', 'reading-chip'); append(chip, 'b', null, star); brightMark(chip, (p.star_brightness || {})[star]);});
    });
    append(row(ziwei, '五行局'), 'b', null, z.five_elements_bureau);
    hua(ziwei, true);
    append(row(ziwei, '命主'), 'b', null, z.ming_master);
    append(row(ziwei, '身主'), 'b', null, z.shen_master);
    append(ziwei, 'p', 'field-help', z.transformation_school);
  }
  // Where to go next from here, among the pages that read this same chart (left out of print, being only buttons).
  const nav = append(result, 'nav', 'reading-nav'); nav.setAttribute('aria-label', '接着看');
  append(nav, 'h4', 'subheading', '接着看');
  const next = append(nav, 'div', 'reading-next');
  [['dayun', '大运十年干支', '十步大运与起运年龄'], ['today', '今日历法', '今天的四柱与命盘的关系'], ['annual', '指定农历年干四化', '今年的四化落在哪些宫'], ['pair', '双人对照', '与另一个人的命盘对照']]
    .filter(([tab]) => !(tab === 'annual' && currentHourUnknown))
    .forEach(([tab, name, what]) => {
      const go = append(next, 'button', 'reading-link'); go.type = 'button'; go.id = 'reading-next-' + tab;
      append(go, 'b', null, name); append(go, 'small', null, what);
      go.addEventListener('click', () => openTab(tab));
    });
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
// The traditional festivals, 三伏 and 数九 can be added as all-day events.
const icsHref = (year, moon, festivals = false) => '/api/solar-terms/' + year + '.ics'
  + (moon || festivals ? '?' + [moon ? 'moon=true' : '', festivals ? 'festivals=true' : ''].filter(Boolean).join('&') : '');
async function downloadIcs(year, moon, message, festivals = false) {
  const token = $('#api_token').value;
  try {
    const reply = await fetch(icsHref(year, moon, festivals), {headers: token ? {'Authorization': 'Bearer ' + token} : {}});
    if (!reply.ok) throw new Error('HTTP ' + reply.status);
    const url = URL.createObjectURL(await reply.blob());
    const link = elt('a'); link.href = url; link.download = 'solar-terms' + (moon ? '-moon' : '') + (festivals ? '-festivals' : '') + '-' + year + '.ics';
    document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 2000);
  } catch (e) {message.textContent = '下载失败：' + e.message;}
}
// Month calendar: one civil month at a time from /api/calendar (a month fits its 31-day range), kept per month so
// going back and forth asks nothing twice. Every cell is a calendar fact: lunar date, day pillar and solar term.
const calendarMonths = {}, calendarPending = new Map();
let calendarMonth = null, calendarSelected = null, calendarFocus = false;
const monthKey = (year, month) => year + '-' + String(month).padStart(2, '0');
const monthLength = (year, month) => new Date(Date.UTC(year, month, 0)).getUTCDate();
// One request per month, shared with the date picker (static/datepicker.js); the promise gives the month's data.
// A month fetched ahead of time (ahead) that fails is not remembered as failed: it is asked for again when shown.
function ensureCalendarMonth(year, month, ahead = false) {
  const key = monthKey(year, month);
  if (calendarMonths[key]) return Promise.resolve(calendarMonths[key]);
  if (calendarPending.has(key)) return calendarPending.get(key);
  const asked = postJSON('/api/calendar', {start_date: key + '-01', days: monthLength(year, month)})
    .then(data => {calendarMonths[key] = data;})
    .catch(err => {if (!calendarMonths[key] && !ahead) calendarMonths[key] = {error: err.message};})
    .finally(() => {
      calendarPending.delete(key);
      if (active !== 'calendar' || !calendarMonth || monthKey(calendarMonth.year, calendarMonth.month) !== key) return;
      // The redraw empties the page first, so whether focus went elsewhere while the month loaded is decided here.
      const focused = document.activeElement;
      if (focused && focused !== document.body && focused.id !== 'calendar-loading') calendarFocus = false;
      render();
    })
    .then(() => calendarMonths[key]);
  calendarPending.set(key, asked);
  return asked;
}
// Shows a month with one day picked; focus follows the pick when it came from the keyboard.
function showCalendarDay(day, focus = false) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || day < '1901-01-01' || day > '2099-12-31') return;
  calendarMonth = {year: Number(day.slice(0, 4)), month: Number(day.slice(5, 7))};
  calendarSelected = day; calendarFocus = focus;
  render();
}
// The twelve jie open the months of the BaZi calendar; the month stem follows the year stem (五虎遁), and 小寒 still
// belongs to the solar year that began at the previous 立春.
const JIE_BRANCH = {'立春': '寅', '惊蛰': '卯', '清明': '辰', '立夏': '巳', '芒种': '午', '小暑': '未',
  '立秋': '申', '白露': '酉', '寒露': '戌', '立冬': '亥', '大雪': '子', '小寒': '丑'};
function jieMonthPillar(term, day) {
  const branch = JIE_BRANCH[term];
  if (!branch) return null;
  const solarYear = Number(day.slice(0, 4)) - (term === '小寒' ? 1 : 0);
  const first = [2, 4, 6, 8, 0][((solarYear - 4) % 10 + 10) % 10 % 5];
  const offset = (BRANCH_ORDER.indexOf(branch) - 2 + 12) % 12;
  return STEM_ORDER[(first + offset) % 10] + branch;
}
const lunarMonthName = lunar => (lunar.is_leap_month ? '闰' : '') + LUNAR_MONTHS[lunar.month - 1];
// Lunar dates and term names written in the interface language here (Day 3 / 3日 / 初三), since the pieces are
// joined without the spaces English needs; the nodes holding them are left alone by the page translator.
const calLang = () => typeof uiLang === 'string' ? uiLang : 'zh-CN';
const calT = text => typeof translateText === 'function' ? translateText(text) : text;
const lunarMonthText = lunar => (lunar.is_leap_month ? calT('闰') + (calLang() === 'en' ? ' ' : '') : '') + calT(LUNAR_MONTHS[lunar.month - 1]);
const lunarDayText = lunar => calT(LUNAR_DAYS[lunar.day - 1]);
const lunarDateText = lunar => lunarMonthText(lunar) + (calLang() === 'en' ? ', ' : '') + lunarDayText(lunar);
// In a day cell English drops the pinyin after a term name: Frost's Descent rather than Frost's Descent (Shuangjiang).
const termText = (name, short) => {const text = calT(name); return short ? text.replace(/\s*\([^)]*\)$/, '') : text;};
const lunarYearPillar = year => STEM_ORDER[((year - 4) % 10 + 10) % 10] + BRANCH_ORDER[((year - 4) % 12 + 12) % 12];
// Festivals, 三伏 and 数九 (each mark from the server names the rule that places it). A day cell has room for about
// two short lines, so marks go by their everyday short names there; the detail below the grid gives the full one.
// The two 小年 keep their region, since they fall on neighbouring days.
const FESTIVAL_SHORT = {'元宵节': '元宵', '上巳节': '上巳', '端午节': '端午', '中元节': '中元', '中秋节': '中秋', '重阳节': '重阳',
  '寒衣节': '寒衣', '下元节': '下元', '腊八节': '腊八'};
// English drops "Festival" (Lantern, Dragon Boat) and uses shorter names where the full one would not fit.
const CELL_EN = {'春节': 'New Year', '除夕': 'NY Eve', '龙抬头': 'Dragon Head', '北方小年': 'Xiaonian (N)', '南方小年': 'Xiaonian (S)',
  '出伏': 'Fu ends', '出九': 'Nines end', '一九': '1st Nine', '二九': '2nd Nine', '三九': '3rd Nine', '四九': '4th Nine', '五九': '5th Nine',
  '六九': '6th Nine', '七九': '7th Nine', '八九': '8th Nine', '九九': '9th Nine'};
function markCellText(name) {
  const lang = calLang();
  if (lang === 'en') return CELL_EN[name] || calT(name).replace(/\s*\([^)]*\)$/, '').replace(/ Festival$/, '');
  // Japanese keeps the Chinese name of the two 小年, and drops a gloss in brackets: 出伏（三伏明け） reads 出伏.
  if (lang === 'ja') return /小年$/.test(name) ? name : calT(name).replace(/（[^）]*）$/, '');
  return calT(FESTIVAL_SHORT[name] || name);
}
const marksOf = d => d.festivals || [];
// A fu period or a nine shows on its first day (and 出伏, 出九 on theirs); on the others it is in the detail.
const seasonStart = m => m.kind !== 'festival' && (m.day === undefined || m.day === 1);
// "Day 3 of 10" in the interface language: a whole phrase per language, filled in, since the Chinese and Japanese
// ones put the numbers inside the words.
const SEASON_DAY = {en: 'day {d} of {n}', ja: '{d}日目（全{n}日）', zh: '第{d}天（共{n}天）'};
const fillDay = (template, m) => template.replace('{d}', m.day).replace('{n}', m.length);
const seasonDayText = m => m.day === undefined ? '' : fillDay(SEASON_DAY[calLang()] || SEASON_DAY.zh, m);
const markText = m => calT(m.name) + (m.day !== undefined ? (calLang() === 'en' ? ', ' : ' ') + seasonDayText(m) : '');
// The words in a day cell: a festival, else the solar term of the day, else a fu period or nine that begins, else the
// month's name on its first day, else the lunar day. A festival on a solar term (春节 on 雨水 in 2015) shows the term on
// a second line, so neither is hidden.
function calendarCellText(d) {
  const festival = marksOf(d).find(m => m.kind === 'festival');
  const term = d.solar_terms.length ? termText(d.solar_terms[0].name, true) : null;
  if (festival) return {text: markCellText(festival.name), kind: 'festival', also: term};
  if (term) return {text: term, kind: 'term'};
  const season = marksOf(d).find(seasonStart);
  if (season) return {text: markCellText(season.name), kind: 'season'};
  // English shortens a leap month to "Leap 6" there (Leap Month 6 in the detail).
  if (d.lunar.day === 1) return {text: calLang() === 'en' && d.lunar.is_leap_month ? 'Leap ' + d.lunar.month : lunarMonthText(d.lunar), kind: 'month'};
  return {text: lunarDayText(d.lunar), kind: 'day'};
}
const CAL_WEEKDAYS = {'zh-CN': [...'一二三四五六日'], 'zh-TW': [...'一二三四五六日'], ja: ['月', '火', '水', '木', '金', '土', '日']};
const CAL_WEEKDAYS_EN = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
// The month before and after the one shown are fetched while the page is idle, so paging shows them at once.
const whenIdle = typeof requestIdleCallback === 'function' ? fn => requestIdleCallback(fn, {timeout: 2000}) : fn => setTimeout(fn, 300);
function prefetchCalendarMonths(year, month) {
  whenIdle(() => [-1, 1].forEach(step => {
    const index = year * 12 + month - 1 + step, y = Math.floor(index / 12), m = index % 12 + 1;
    if (y >= 1901 && y <= 2099) ensureCalendarMonth(y, m, true);
  }));
}
// While a month loads its grid is drawn already, with the Gregorian days, weekends and today in place and a soft
// shimmer where the lunar day and day pillar will be, so the page does not jump when the month arrives.
function calendarSkeleton(year, month, today) {
  const ghost = append(result, 'div', 'cal-skeleton'); ghost.setAttribute('aria-hidden', 'true');
  const bar = (parent, width) => {const b = append(parent, 'span', 'cal-ghost'); b.style.setProperty('--w', width); return b;};
  const head = append(ghost, 'div', 'cal-head');
  append(head, 'h4', 'cal-title', calendarMonthTitle(year, month)).dataset.noI18n = '';
  bar(append(head, 'p', 'cal-span'), '16em');
  const chips = append(head, 'div', 'cal-terms');
  ['9em', '9em'].forEach(width => bar(append(chips, 'span', 'cal-term-chip'), width));
  const table = append(ghost, 'table', 'cal-grid');
  const hr = append(append(table, 'thead'), 'tr'), lang = calLang();
  WEEKDAY_NAMES.forEach((full, i) => {
    append(append(hr, 'th', i > 4 ? 'is-weekend' : null), 'abbr', null, lang === 'en' ? CAL_WEEKDAYS_EN[i] : (CAL_WEEKDAYS[lang] || CAL_WEEKDAYS['zh-CN'])[i]).dataset.noI18n = '';
  });
  const body = append(table, 'tbody'), lead = (new Date(Date.UTC(year, month - 1, 1)).getUTCDay() + 6) % 7, days = monthLength(year, month);
  let row = append(body, 'tr');
  for (let i = 0; i < lead; i++) append(row, 'td', 'cal-blank');
  for (let i = 0; i < days; i++) {
    if ((lead + i) % 7 === 0 && i) row = append(body, 'tr');
    const date = monthKey(year, month) + '-' + String(i + 1).padStart(2, '0');
    const day = append(append(row, 'td', 'cal-cell'), 'div', 'cal-day' + ((lead + i) % 7 > 4 ? ' is-weekend' : '') + (date === today ? ' is-today' : ''));
    append(day, 'span', 'cal-num', String(i + 1));
    bar(append(day, 'span', 'cal-lunar'), '2.6em');
    bar(append(day, 'span', 'cal-gz'), '1.8em');
  }
  while (row.children.length < 7) append(row, 'td', 'cal-blank');
}
function calendarMonthTitle(year, month) {
  if (calLang() === 'en') return new Date(Date.UTC(year, month - 1, 1)).toLocaleDateString('en', {month: 'long', year: 'numeric', timeZone: 'UTC'});
  return year + '年' + month + '月';
}
document.addEventListener('xuanshu-language', () => {if (['calendar', 'today', 'boundaries', 'officers', 'date-scan', 'pillar-search', 'rule-matrix', 'report', 'integration', 'professional', 'time'].includes(active)) render();});
// Each rule once, after the names it places: 一九、二九：冬至当天起每九天为一九…
function calendarRuleLines(data) {
  const names = new Map();
  data.days.forEach(d => marksOf(d).forEach(m => {
    const rule = m.rule + (m.caution ? '（' + m.caution + '）' : '');
    if (!names.has(rule)) names.set(rule, []);
    if (!names.get(rule).includes(m.name)) names.get(rule).push(m.name);
  }));
  return [...names].map(([rule, list]) => list.join('、') + '：' + rule);
}
// One row a day, for the text export and the spreadsheet file alike.
// The file has no title line, so its term column says which clock the times are on, and it has no rule list at the
// end either, so each day carries the rule of its marks and any doubt about them (a 冬至 close to midnight) itself.
const calendarRows = (data, termHead = '节气', withRules = false) => [['公历', '星期', '农历', '日柱', termHead, '节令', ...(withRules ? ['节令推算规则', '节令提醒'] : [])],
  ...data.days.map(d => [d.date, d.weekday,
    lunarMonthName(d.lunar) + LUNAR_DAYS[d.lunar.day - 1], d.day_pillar,
    d.solar_terms.map(t => t.name + ' ' + t.time_china.slice(11, 16)).join('、') || '—',
    marksOf(d).map(m => m.name + (m.day !== undefined ? ' ' + fillDay(SEASON_DAY.zh, m) : '')).join('、') || '—',
    ...(withRules ? [marksOf(d).map(m => m.name + '：' + m.rule).join('；') || '—',
      [...new Set(marksOf(d).map(m => m.caution).filter(Boolean))].join('；') || '—'] : [])])];
// In English and Japanese the calendar's export uses the interface's words, the same the month grid shows (the chart
// exports keep the usual Chinese chart notation). Day pillars stay as characters, as on the grid.
const WEEKDAY_WORDS = {en: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], ja: ['月', '火', '水', '木', '金', '土', '日']};
const exportLang = () => typeof uiLang !== 'undefined' && WEEKDAY_WORDS[uiLang] ? uiLang : null;
const calendarWords = text => exportLang() ? calT(String(text)) : text;
const calendarExportRows = rows => !exportLang() ? rows : rows.map((row, r) => row.map((cell, i) =>
  r && i === 1 && cell.length === 1 && '一二三四五六日'.includes(cell) ? WEEKDAY_WORDS[uiLang]['一二三四五六日'.indexOf(cell)] : i === 3 && r ? cell : calendarWords(cell)));
function calendarText(year, month, data) {
  const lines = [calendarWords('玄枢 · ' + year + '-' + String(month).padStart(2, '0') + ' 农历、日柱、节气与传统节令（中国标准时间）'), ''];
  lines.push(...textColumns(calendarExportRows(calendarRows(data)), exportLang() === 'en'));
  const rules = calendarRuleLines(data).map(calendarWords);
  if (rules.length) lines.push('', calendarWords('【节令推算规则】'), ...rules);
  lines.push('', calendarWords('只列历法事实，不含宜忌或吉凶。'));
  return finishText(lines);
}
function renderCalendar() {
  title(result, '农历 · 干支日历', '月历 · 以中国标准时间计算');
  if (!calendarMonth) {const today = localToday(); calendarMonth = {year: Number(today.slice(0, 4)), month: Number(today.slice(5, 7))}; calendarSelected = today;}
  const {year, month} = calendarMonth, key = monthKey(year, month), today = localToday();
  const nav = append(result, 'div', 'inline-control cal-nav');
  const step = by => {
    const index = year * 12 + month - 1 + by, y = Math.floor(index / 12), m = index % 12 + 1;
    const day = monthKey(y, m) === today.slice(0, 7) ? today : monthKey(y, m) + '-01';
    calendarMonth = {year: y, month: m}; calendarSelected = day; render();
  };
  // On a phone the words beside the arrows and above the two selects are hidden, so the four fit on one line.
  const arrow = (id, mark, words, before) => {
    const button = append(nav, 'button', 'tiny-button cal-step'); button.type = 'button'; button.id = id;
    button.setAttribute('aria-label', words); tip(button, words);
    if (before) append(button, 'span', 'cal-arrow', mark);
    append(button, 'span', 'cal-step-words', words);
    if (!before) append(button, 'span', 'cal-arrow', mark);
    return button;
  };
  const prev = arrow('calendar-prev', '‹', '上个月', true);
  prev.disabled = key <= '1901-01';
  const field = (caption, id, from, to, value) => {
    const label = append(nav, 'label', 'cal-field');
    append(label, 'span', 'cal-caption', caption);
    const box = append(label, 'select'); box.id = id;
    for (let n = from; n <= to; n++) {const option = append(box, 'option', null, String(n)); option.value = String(n);}
    box.value = String(value);
    return box;
  };
  const yearBox = field('公历年份', 'calendar-year', 1901, 2099, year);
  const monthBox = field('公历月份', 'calendar-month', 1, 12, month);
  const next = arrow('calendar-next', '›', '下个月', false);
  next.disabled = key >= '2099-12';
  // A button pressed keeps its focus through the redraw; at either end of the range it passes to the year.
  prev.dataset.focusFallback = next.dataset.focusFallback = 'calendar-year';
  prev.addEventListener('click', () => step(-1));
  next.addEventListener('click', () => step(1));
  const pick = () => {
    const y = Number(yearBox.value), m = Number(monthBox.value);
    calendarMonth = {year: y, month: m}; calendarSelected = monthKey(y, m) === today.slice(0, 7) ? today : monthKey(y, m) + '-01';
    setTimeout(render);  // not inside the change handler: the redraw would remove the select while it reports
  };
  yearBox.addEventListener('change', pick); monthBox.addEventListener('change', pick);
  if (key !== today.slice(0, 7) || calendarSelected !== today) {
    const back = append(nav, 'button', 'tiny-button', '回到今天'); back.type = 'button'; back.id = 'calendar-today';
    back.addEventListener('click', () => showCalendarDay(today, true));
  }
  const links = append(result, 'div', 'cal-links');
  const ics = append(links, 'a', 'tiny-button', '全年节气 ICS 日历下载');
  const moonIcs = append(links, 'a', 'tiny-button', '节气与月相 ICS'); moonIcs.id = 'calendar-moon-ics';
  const festivalIcs = append(links, 'a', 'tiny-button', '节气与传统节令 ICS'); festivalIcs.id = 'calendar-festival-ics';
  tip(festivalIcs, '二十四节气，加上传统节日和三伏、数九各段的第一天（全天事件，附推算规则）');
  ics.href = icsHref(year, false); moonIcs.href = icsHref(year, true); festivalIcs.href = icsHref(year, false, true);
  const message = append(result, 'p', 'inline-msg');
  ics.addEventListener('click', event => {event.preventDefault(); downloadIcs(year, false, message);});
  moonIcs.addEventListener('click', event => {event.preventDefault(); downloadIcs(year, true, message);});
  festivalIcs.addEventListener('click', event => {event.preventDefault(); downloadIcs(year, false, message, true);});
  const data = calendarMonths[key];
  if (!data || data.error) {
    if (!data) {
      ensureCalendarMonth(year, month);
      // While the month loads, keyboard focus waits here, so Page Up / Page Down keep paging instead of scrolling.
      const wait = append(result, 'p', 'field-help', '正在排出这个月的农历、日柱和节气…'); wait.id = 'calendar-loading'; wait.tabIndex = -1;
      wait.addEventListener('keydown', event => {
        if (event.key !== 'PageUp' && event.key !== 'PageDown') return;
        event.preventDefault();
        const index = year * 12 + month - 1 + (event.key === 'PageUp' ? -1 : 1), y = Math.floor(index / 12), m = index % 12 + 1;
        const day = Math.min(Number((calendarSelected || '').slice(8)) || 1, monthLength(y, m));
        showCalendarDay(monthKey(y, m) + '-' + String(day).padStart(2, '0'), true);
      });
      if (calendarFocus) wait.focus();
      calendarSkeleton(year, month, today);
    }
    else {
      append(result, 'p', 'inline-msg', '这个月暂时算不出来：' + data.error);
      const retry = append(result, 'button', 'tiny-button', '重试'); retry.type = 'button'; retry.id = 'calendar-retry';
      retry.addEventListener('click', () => {delete calendarMonths[key]; render();});
    }
    renderLunarInverseSection();
    return;
  }
  calendarResult = data;
  prefetchCalendarMonths(year, month);
  if (!calendarSelected || calendarSelected.slice(0, 7) !== key) calendarSelected = key + '-01';
  // The month at a glance: the lunar months it spans and the solar terms in it, with the month pillar a jie opens.
  const head = append(result, 'div', 'cal-head');
  const name = append(head, 'h4', 'cal-title', calendarMonthTitle(year, month)); name.dataset.noI18n = ''; name.id = 'calendar-title';
  const first = data.days[0].lunar, last = data.days[data.days.length - 1].lunar;
  const span = append(head, 'p', 'cal-span');
  texts(span, '农历', ' ');
  append(span, 'span', null, lunarYearPillar(first.year) + (first.year !== last.year ? '–' + lunarYearPillar(last.year) : '') + ' · '
    + lunarDateText(first) + ' – ' + lunarDateText(last)).dataset.noI18n = '';
  const terms = append(head, 'div', 'cal-terms'); terms.id = 'calendar-terms';
  data.days.forEach(d => d.solar_terms.forEach(t => {
    const chip = append(terms, 'button', 'cal-term-chip' + (JIE_BRANCH[t.name] ? ' is-jie' : '')); chip.type = 'button';
    append(chip, 'b', null, t.name);
    chip.append(' ' + t.time_china.slice(5, 10).replace('-', '/') + ' ' + t.time_china.slice(11, 16));
    const pillar = jieMonthPillar(t.name, d.date);
    if (pillar) {chip.append(' · '); texts(chip, '月柱', ' ', pillar);}
    chip.addEventListener('click', () => showCalendarDay(d.date, true));
  }));
  // The festivals of the month and the fu periods and nines that begin in it, each a way to its day.
  const starts = data.days.flatMap(d => marksOf(d).filter(m => m.kind === 'festival' || seasonStart(m)).map(m => ({d, m})));
  if (starts.length) {
    const row = append(head, 'div', 'cal-terms cal-marks'); row.id = 'calendar-marks';
    starts.forEach(({d, m}) => {
      const chip = append(row, 'button', 'cal-term-chip ' + (m.kind === 'festival' ? 'is-festival' : 'is-season')); chip.type = 'button';
      append(chip, 'b', null, m.name);
      chip.append(' ' + d.date.slice(5).replace('-', '/'));
      chip.addEventListener('click', () => showCalendarDay(d.date, true));
    });
  }
  // The grid: Monday first, a button per day; arrow keys move the pick a day or a week, Page Up / Page Down a month.
  const table = append(result, 'table', 'cal-grid'); table.id = 'calendar-grid';
  table.setAttribute('role', 'grid'); table.setAttribute('aria-labelledby', 'calendar-title');
  const hr = append(append(table, 'thead'), 'tr');
  const lang = calLang();
  WEEKDAY_NAMES.forEach((full, i) => {
    const th = append(hr, 'th', i > 4 ? 'is-weekend' : null); th.scope = 'col'; tip(th, full);
    const short = append(th, 'abbr', null, lang === 'en' ? CAL_WEEKDAYS_EN[i] : (CAL_WEEKDAYS[lang] || CAL_WEEKDAYS['zh-CN'])[i]);
    short.dataset.noI18n = ''; tip(short, calT(full));
  });
  const body = append(table, 'tbody');
  const lead = (new Date(Date.UTC(year, month - 1, 1)).getUTCDay() + 6) % 7;
  let row = append(body, 'tr');
  for (let i = 0; i < lead; i++) append(row, 'td', 'cal-blank');
  const move = (day, by) => showCalendarDay(shiftDate(day, by), true);
  data.days.forEach((d, i) => {
    if ((lead + i) % 7 === 0 && i) row = append(body, 'tr');
    const cell = append(row, 'td', 'cal-cell'); cell.setAttribute('role', 'gridcell');
    const words = calendarCellText(d), weekend = (lead + i) % 7 > 4;
    const button = append(cell, 'button', 'cal-day cal-' + words.kind + (weekend ? ' is-weekend' : '') + (d.date === today ? ' is-today' : '')
      + (d.date === calendarSelected ? ' is-selected' : '')); button.type = 'button'; button.id = 'calendar-day-' + d.date;
    button.tabIndex = d.date === calendarSelected ? 0 : -1; button.dataset.noI18n = '';
    cell.setAttribute('aria-selected', String(d.date === calendarSelected));
    if (d.date === today) button.setAttribute('aria-current', 'date');
    button.setAttribute('aria-label', [d.date, calT('星期' + d.weekday), calT('农历') + ' ' + lunarDateText(d.lunar), calT('日柱') + ' ' + d.day_pillar,
      ...d.solar_terms.map(t => termText(t.name) + ' ' + t.time_china.slice(11, 16)), ...marksOf(d).map(markText)].join(' · '));
    append(button, 'span', 'cal-num', String(Number(d.date.slice(8))));
    append(button, 'span', 'cal-lunar', words.text).dataset.noI18n = '';
    if (words.also) append(button, 'span', 'cal-also', words.also).dataset.noI18n = '';
    const gz = append(button, 'span', 'cal-gz'); gz.dataset.noI18n = '';
    append(gz, 'span', stemClass(d.day_pillar[0]), d.day_pillar[0]); append(gz, 'span', branchClass(d.day_pillar[1]), d.day_pillar[1]);
    button.addEventListener('click', () => showCalendarDay(d.date, document.activeElement === button));
    button.addEventListener('keydown', event => {
      const by = {ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7}[event.key];
      if (by) {event.preventDefault(); move(d.date, by); return;}
      if (event.key === 'Home' || event.key === 'End') {
        event.preventDefault(); move(d.date, event.key === 'Home' ? -((lead + i) % 7) : 6 - (lead + i) % 7); return;
      }
      if (event.key === 'PageUp' || event.key === 'PageDown') {
        event.preventDefault();
        const index = year * 12 + month - 1 + (event.key === 'PageUp' ? -1 : 1), y = Math.floor(index / 12), m = index % 12 + 1;
        showCalendarDay(monthKey(y, m) + '-' + String(Math.min(Number(d.date.slice(8)), monthLength(y, m))).padStart(2, '0'), true);
      }
    });
  });
  while (row.children.length < 7) append(row, 'td', 'cal-blank');
  // Keyboard moves focus with the pick, also after a month that had to load first, unless focus went elsewhere.
  const away = document.activeElement && document.activeElement !== document.body && !result.contains(document.activeElement);
  if (calendarFocus && !away) {calendarFocus = false; const button = $('#calendar-day-' + calendarSelected); if (button) button.focus();}
  calendarFocus = false;
  // The picked day in words, with a way into 今日历法 for its pillars, moon and the labels against the chart.
  const d = data.days.find(x => x.date === calendarSelected) || data.days[0];
  const detail = append(result, 'div', 'cal-detail'); detail.id = 'calendar-detail'; detail.setAttribute('aria-live', 'polite');
  const line = append(detail, 'p', 'cal-detail-date');
  texts(line, d.date, ' · ', '星期' + d.weekday);
  if (d.date === today) line.append(' · ', '今天');
  const facts = append(detail, 'div', 'cal-detail-facts');
  const lunar = append(facts, 'p');
  texts(lunar, '农历', ' ');
  append(lunar, 'span', null, lunarYearPillar(d.lunar.year) + ' · ' + lunarDateText(d.lunar)).dataset.noI18n = '';
  const pillar = append(facts, 'p');
  texts(pillar, '日柱', ' ');
  const big = append(pillar, 'b', 'cal-detail-gz'); big.dataset.noI18n = '';
  append(big, 'span', stemClass(d.day_pillar[0]), d.day_pillar[0]); append(big, 'span', branchClass(d.day_pillar[1]), d.day_pillar[1]);
  d.solar_terms.forEach(t => {
    const term = append(facts, 'p');
    texts(term, '节气', ' ');
    append(term, 'b', null, t.name);
    term.append(' ' + t.time_china.slice(11, 16) + ' ');
    texts(term, '（北京时间）');
    const opens = jieMonthPillar(t.name, d.date);
    if (opens) {term.append(' · '); texts(term, '月柱换为', ' ', opens);}
  });
  // Each festival, fu or nine with the rule that places it; a festival's rule is its lunar date, written here.
  marksOf(d).forEach(m => {
    const line = append(facts, 'p', 'cal-mark cal-mark-' + m.kind);
    texts(line, m.kind === 'festival' ? '节日' : m.kind === 'sanfu' ? '三伏' : '数九', '：');
    append(line, 'b', null, m.name);
    if (m.day !== undefined) append(line, 'span', null, (calLang() === 'en' ? ', ' : ' ') + seasonDayText(m)).dataset.noI18n = '';
    const rule = append(line, 'small', 'cal-mark-rule');
    if (m.kind === 'festival' && m.name !== '除夕') {texts(rule, '农历', ' '); append(rule, 'span', null, lunarDateText(d.lunar)).dataset.noI18n = '';}
    else rule.textContent = m.rule;
    if (m.caution) append(line, 'small', 'cal-mark-caution', m.caution);
  });
  const open = append(detail, 'button', 'tiny-button', current ? '查看这天的四柱、月相和与命盘的关系' : '查看这天的四柱与月相');
  open.type = 'button'; open.id = 'calendar-open-day';
  open.addEventListener('click', () => {todayPick = {date: d.date, time: '12:00'}; activateTab(tabs.find(t => t.dataset.tab === 'today'));});
  textExport(result, 'calendar-text', () => calendarText(year, month, data), 'xuanshu-calendar-' + key + '.txt', '整月的农历、日柱与节气，按中国标准时间',
    () => calendarExportRows(calendarRows(data, '节气（中国标准时间）', true)));
  renderLunarInverseSection();
  note(result, data.notes.join(' '));
}
// 建除值日 as a calendar: a week per row, Monday first, the officer of each day large. Picking an officer marks
// its days and dims the rest (nothing is left out), and a jie day names the other officer of that day.
let officerMark = '', officerView = 'grid';
const DAY_OFFICER_ORDER = [...'建除满平定执破危成收开闭'];
// The noon officer is one of the two on a jie day: the one before the term when it falls after noon, the one after it
// when it falls before. The other one is what the day adds.
function officerJie(d) {
  const j = d.jie_on_date, after = d.officer === j.officer_before;
  return {name: j.name, time: j.time_china.slice(11, 16), after, other: after ? j.officer_after : j.officer_before};
}
// English officer names are a pinyin and a gloss, Po (Destruction); a day cell keeps the pinyin.
const officerShort = o => calLang() === 'en' ? calT(o).replace(/\s*\([^)]*\)$/, '') : o;
// A jie line: compact in a cell (17:52 → 开 after the term, 成 → 04:02 before it), with the words for screen readers.
function officerJieText(parent, d, compact) {
  const jie = officerJie(d);
  if (!compact) {texts(parent, termText(jie.name), ' ', jie.time, ' · ', jie.after ? '节后' : '节前', ' '); append(parent, 'b', null, jie.other); return;}
  tip(parent, termText(jie.name) + ' ' + jie.time);
  const shown = append(parent, 'span', 'of-jie-short'); shown.setAttribute('aria-hidden', 'true'); shown.dataset.noI18n = '';
  append(shown, 'span', 'of-jie-name', termText(jie.name, true));
  const swap = append(shown, 'span', 'of-jie-swap'), other = elt('b', null, officerShort(jie.other));
  tip(other, calT(jie.other));
  if (jie.after) swap.append(jie.time + ' → ', other); else swap.append(other, ' → ' + jie.time);
  officerJieText(append(parent, 'span', 'visually-hidden'), d, false);
}
const weekdayOf = date => (new Date(date + 'T00:00:00Z').getUTCDay() + 6) % 7;
// Monday-first weekday headers shared by the week calendars.
function weekHeader(table) {
  const head = append(append(table, 'thead'), 'tr'), lang = calLang();
  WEEKDAY_NAMES.forEach((full, i) => {
    const th = append(head, 'th', i > 4 ? 'is-weekend' : null); th.scope = 'col';
    const short = append(th, 'abbr', null, lang === 'en' ? CAL_WEEKDAYS_EN[i] : (CAL_WEEKDAYS[lang] || CAL_WEEKDAYS['zh-CN'])[i]);
    short.dataset.noI18n = ''; tip(short, calT(full));
  });
}
// The day number of a week-calendar cell: month/day on the first cell and on the first of a month.
function weekDateLabel(parent, date, first) {
  const [, m, d] = date.split('-').map(Number);
  append(parent, 'span', 'of-date', first || d === 1 ? m + '/' + d : String(d));
}
function renderDayOfficers() {
  title(result,'建除十二值日','节令月支 × 日支 · 仅传统标签，不给吉凶或宜忌结论');
  const row=append(result,'div','inline-control');
  const start=createInput('查询起始日（北京时间）','date',officerDraft.start_date,row);
  start.id='officer-date';start.min='1901-01-01';start.max='2099-12-31';
  const count=append(append(row,'label',null,'查询长度'),'select');count.id='officer-days';
  [7,14,30,60,90].forEach(x=>{const op=texts(append(count,'option'),x,' 天');op.value=String(x);});count.value=String(officerDraft.days);
  keepTyped(start,count);
  const query=()=>{
    const draft=officerDraft;
    officerPending=true;officerError='';
    postJSON('/api/day-officers',{start_date:draft.start_date,days:draft.days,filter_officers:[]})
      .then(data=>{if(officerDraft===draft)officerResult=data;}).catch(e=>{if(officerDraft===draft)officerError='查询失败：'+e.message;})
      .finally(()=>{if(officerDraft===draft){officerPending=false;if(active==='officers')render();}});
  };
  // Nothing here depends on the chart, so the coming days are listed as soon as the tool opens.
  if(!officerResult&&!officerPending&&!officerError)query();
  const run=append(row,'button',null,'查询值日');run.id='officer-run';run.type='button';run.disabled=officerPending;
  append(result,'p','inline-msg',officerError);
  run.addEventListener('click',()=>{
    officerDraft={start_date:start.value,days:Number(count.value)};
    query();render();
  });
  append(result,'p','field-help','查询按北京时间正午取值；交节当天另写交节时刻和另一个值日。');
  if(officerPending)append(result,'p','field-help','正在查询…');
  if(!officerResult){if(officerPending)loadingGhost(result,'month');return;}
  const days = officerResult.days, first = days[0], last = days[days.length - 1];
  if (!days.length) return;
  const tags = append(result, 'div', 'meta-tags');
  texts(append(tags, 'span'), first.date, ' – ', last.date);
  const branches = [...new Set(days.flatMap(d => d.jie_on_date ? [d.month_branch_at_noon, d.jie_on_date.month_branch_after] : [d.month_branch_at_noon]))];
  texts(append(tags, 'span'), '正午月建', ' ', branches.join(' → '));
  append(tags, 'span', null, '不对日期好坏打分');
  // One chip per officer in cycle order with its count in the range; a chip marks its days.
  const legend = append(result, 'div', 'of-legend'); legend.id = 'officer-legend';
  legend.setAttribute('role', 'group'); legend.setAttribute('aria-label', '突出显示值日');
  const counts = {}; days.forEach(d => {counts[d.officer] = (counts[d.officer] || 0) + 1;});
  [''].concat(DAY_OFFICER_ORDER).forEach(o => {
    const chip = append(legend, 'button', 'of-chip' + (officerMark === o ? ' active' : '')); chip.type = 'button';
    chip.id = 'officer-mark-' + (o ? DAY_OFFICER_ORDER.indexOf(o) : 'all'); chip.setAttribute('aria-pressed', String(officerMark === o));
    append(chip, 'b', null, o || '全部');
    if (o) texts(append(chip, 'small'), '×', counts[o] || 0);
    chip.addEventListener('click', () => {officerMark = o; render();});
  });
  const marks = d => officerMark && (d.officer === officerMark || (d.jie_on_date && officerJie(d).other === officerMark));
  if (officerMark) {
    const n = days.filter(marks).length, part = days.filter(d => d.officer !== officerMark && marks(d)).length;
    const line = countText(texts(append(result, 'p', 'of-summary'), '突出显示', ' ', officerMark, ' · '), n, ' 天');
    if (part) {texts(line, ' · ', '其中', ' '); countText(line, part, ' 天'); texts(line, ' ', '只在交节前或交节后');}
  }
  const views = append(result, 'div', 'layer-modes of-views');
  views.setAttribute('role', 'group'); views.setAttribute('aria-label', '显示方式');
  [['grid', '日历'], ['list', '列表']].forEach(([key, name]) => {
    const button = append(views, 'button', 'layer-btn' + (officerView === key ? ' active' : ''), name);
    button.type = 'button'; button.id = 'officer-view-' + key; button.setAttribute('aria-pressed', String(officerView === key));
    button.addEventListener('click', () => {officerView = key; render();});
  });
  const today = localToday();
  // A day marked only for the officer before or after its term: that officer is the marked one, not the noon one.
  const markClass = d => !officerMark ? '' : !marks(d) ? ' is-dim' : d.officer === officerMark ? ' is-mark' : ' is-mark is-mark-jie';
  if (officerView === 'grid') {
    const wrap = append(result, 'div', 'of-wrap');
    const table = append(wrap, 'table', 'of-grid'); table.id = 'officer-grid';
    append(table, 'caption', 'visually-hidden', '建除十二值日');
    weekHeader(table);
    const body = append(table, 'tbody');
    let tr = null;
    const cells = Array(weekdayOf(first.date)).fill(null).concat(days);
    while (cells.length % 7) cells.push(null);
    cells.forEach((d, i) => {
      if (i % 7 === 0) tr = append(body, 'tr');
      if (!d) {append(tr, 'td', 'of-blank'); return;}
      const td = append(tr, 'td', 'of-day' + (d.date === today ? ' is-today' : '') + (d.jie_on_date ? ' is-jie' : '') + markClass(d));
      td.id = 'officer-day-' + d.date;
      weekDateLabel(td, d.date, i === weekdayOf(first.date));
      if (d.date === today) {td.setAttribute('aria-current', 'date'); append(td, 'span', 'visually-hidden', '今天');}
      const gz = append(td, 'b', 'of-gz'); gz.dataset.noI18n = '';
      append(gz, 'span', stemClass(d.day_pillar[0]), d.day_pillar[0]); append(gz, 'span', branchClass(d.day_pillar[1]), d.day_pillar[1]);
      const officer = append(td, 'span', 'of-officer', officerShort(d.officer)); officer.dataset.noI18n = ''; tip(officer, calT(d.officer));
      if (d.jie_on_date) officerJieText(append(td, 'small', 'of-jie'), d, true);
    });
    append(result, 'p', 'field-help', '一行一周，从星期一开始；格子里是日期、日干支和正午的值日，今天的日期填色。交节当天另写节气和交节时刻（北京时间）：「17:52 → 开」是交节后轮到开，「成 → 04:02」是交节前为成。');
  } else {
    const table=append(append(result,'div','table-wrap'),'table','data-table of-list'); table.id = 'officer-list';
    const hr=append(append(table,'thead'),'tr');
    ['公历日','日干支','正午月建','十二值日','交节'].forEach(x=>append(hr,'th',null,x));
    const body=append(table,'tbody');
    days.forEach(d=>{
      const tr=append(body,'tr', markClass(d).trim() || null);
      [d.date,d.day_pillar,d.month_branch_at_noon,d.officer].forEach(x=>append(tr,'td',null,x));
      if (d.date === today) {tr.setAttribute('aria-current', 'date'); append(tr.firstChild, 'small', 'of-today', '今天');}
      const jie = append(tr, 'td');
      if (d.jie_on_date) officerJieText(jie, d, false); else jie.textContent = '—';
    });
  }
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
  [7,14,30,60,93].forEach(x=>{const op=texts(append(count,'option'),x,' 天');op.value=String(x);});count.value=String(dateScanDraft.days);
  const hours=createInput('候选时刻（选填，逗号分隔，如 09:00,15:00）','text',dateScanDraft.hours,row);hours.id='scan-hours';hours.maxLength=40;
  const officers=['建','除','满','平','定','执','破','危','成','收','开','闭'];
  const pick=(label,key,id)=>{
    const box=append(result,'div','consult-shortcuts');box.id=id;append(box,'small','small-text',label);
    officers.forEach(o=>{const l=append(box,'label','check-line');const c=append(l,'input');c.type='checkbox';c.value=o;c.checked=dateScanDraft[key].includes(o);l.append(' '+o);});
    return box;
  };
  const inc=pick('只保留这些值日（不选=不限）','include','scan-include');
  const exc=pick('排除这些值日','exclude','scan-exclude');
  // One officer cannot be both kept and excluded: ticking it on one side clears it on the other.
  [[inc,exc],[exc,inc]].forEach(([from,to])=>from.addEventListener('change',event=>{
    if(event.target.checked){const other=to.querySelector(`input[value="${event.target.value}"]`);if(other)other.checked=false;}
  }));
  const opts=append(result,'div','consult-shortcuts');
  const jl=append(opts,'label','check-line');const jie=append(jl,'input');jie.type='checkbox';jie.id='scan-skip-jie';jie.checked=dateScanDraft.skipJie;jl.append(' 排除交节当天');
  const nl=append(opts,'label','check-line');const natal=append(nl,'input');natal.type='checkbox';natal.id='scan-natal';natal.checked=dateScanDraft.natal;nl.append(' 排除与本命年支、日支相冲的日子');
  const run=append(opts,'button','scan-run','扫描候选日');run.id='scan-run';run.type='button';
  const msg=append(result,'p','inline-msg');
  // The draft follows every edit, so choosing a candidate or switching views keeps what was typed but not yet scanned.
  const checked=box=>[...box.querySelectorAll('input:checked')].map(x=>x.value);
  const sync=()=>{dateScanDraft={start_date:start.value,days:Number(count.value),include:checked(inc),exclude:checked(exc),skipJie:jie.checked,natal:natal.checked,hours:hours.value};};
  [start,hours].forEach(x=>x.addEventListener('input',sync));
  [count,inc,exc,opts].forEach(x=>x.addEventListener('change',sync));
  run.addEventListener('click',async()=>{
    sync();
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
  if(!dateScanResult){
    append(result,'p','info-inline','先选条件再扫描。结果只是传统标签筛选，最终取舍以现实安排为准。');
    emptyPreview(result,run,['公历日与农历','日干支','十二值日','是否与本命相冲','候选时刻的时家奇门盘'],['table']);
    return;
  }
  renderDateScanResult(dateScanResult);
}
// The scan as a week calendar over the whole range: candidates stand out and open their detail (lunar date, clashes,
// the jie and the hour Qimen charts) below; every dropped day says which filter dropped it, and days after a truncated
// scan say they were not scanned. The candidate list stays as the list view.
let dateScanView = 'grid', dateScanPick = '';
const SCAN_REASONS = {officer_not_included: '值日不在保留中', officer_excluded: '排除的值日', jie_boundary: '交节当天', natal_clash: '与本命相冲'};
// Phone-width cells have room for two characters.
const SCAN_REASONS_SHORT = {officer_not_included: '未选', officer_excluded: '排除', jie_boundary: '交节', natal_clash: '相冲'};
function renderDateScanResult(r) {
  const unscanned = r.truncated && r.scanned_through ? Math.max(0, (Date.parse(shiftDate(r.range_start, r.requested_days)) - Date.parse(r.scanned_through)) / 86400000 - 1) : 0;
  meta(result, [`候选 ${r.candidates.length} 日`, r.truncated ? '结果已达上限' : '按日期排列']);
  const legend = append(result, 'div', 'ds-legend'); legend.id = 'scan-legend';
  texts(append(legend, 'span', 'ds-key is-pick'), '候选日', ' ×', r.candidates.length);
  Object.entries(SCAN_REASONS).forEach(([key, name]) => {if (r.excluded_counts[key]) texts(append(legend, 'span', 'ds-key is-out'), name, ' ×', r.excluded_counts[key]);});
  if (unscanned) texts(append(legend, 'span', 'ds-key is-out'), '未扫描', ' ×', unscanned);
  const views = append(result, 'div', 'layer-modes of-views');
  views.setAttribute('role', 'group'); views.setAttribute('aria-label', '显示方式');
  [['grid', '日历'], ['list', '列表']].forEach(([key, name]) => {
    const button = append(views, 'button', 'layer-btn' + (dateScanView === key ? ' active' : ''), name);
    button.type = 'button'; button.id = 'scan-view-' + key; button.setAttribute('aria-pressed', String(dateScanView === key));
    button.addEventListener('click', () => {dateScanView = key; render();});
  });
  // The lunar year by its pillar and the month and day in the interface language, as on the calendar page.
  const lunarText = (parent, c) => {append(parent, 'span', null, lunarYearPillar(c.lunar_date.year) + ' · ' + lunarDateText(c.lunar_date)).dataset.noI18n = '';};
  const clashText = c => c.natal_clashes.map(x => x.day_branch + '冲' + x.natal_branch).join('、');
  const chartLine = h => `${h.dun}${h.bureau}局`;
  if (dateScanView === 'grid') {
    const byDate = new Map(r.candidates.map(c => [c.date, {pick: true, d: c}]).concat(r.excluded_days.map(d => [d.date, {pick: false, d}])));
    if (!byDate.has(dateScanPick) || !byDate.get(dateScanPick).pick) dateScanPick = r.candidates.length ? r.candidates[0].date : '';
    const table = append(append(result, 'div', 'of-wrap'), 'table', 'of-grid ds-grid'); table.id = 'scan-grid';
    append(table, 'caption', 'visually-hidden', '择日择时');
    weekHeader(table);
    const body = append(table, 'tbody'), today = localToday();
    const dates = Array.from({length: r.requested_days}, (_, i) => shiftDate(r.range_start, i));
    const cells = Array(weekdayOf(r.range_start)).fill(null).concat(dates);
    while (cells.length % 7) cells.push(null);
    let tr = null;
    cells.forEach((date, i) => {
      if (i % 7 === 0) tr = append(body, 'tr');
      if (!date) {append(tr, 'td', 'of-blank'); return;}
      const entry = byDate.get(date), first = i === weekdayOf(r.range_start);
      const td = append(tr, 'td', 'of-day ds-day' + (date === today ? ' is-today' : '') + (entry && entry.pick ? ' is-pick' : ' is-dim') + (entry && entry.d.jie_on_date ? ' is-jie' : ''));
      td.id = 'scan-day-' + date;
      if (date === today) td.setAttribute('aria-current', 'date');
      if (!entry) {weekDateLabel(td, date, first); append(td, 'span', 'ds-reason is-unscanned', '未扫描'); return;}
      const d = entry.d, box = entry.pick ? append(td, 'button', 'ds-pick') : td;
      if (entry.pick) {
        box.type = 'button'; box.id = 'scan-pick-' + date; box.setAttribute('aria-pressed', String(date === dateScanPick));
        if (date === dateScanPick) td.classList.add('is-selected');
        box.addEventListener('click', () => {dateScanPick = date; render(); const panel = $('#scan-detail'); if (panel) panel.scrollIntoView({block: 'nearest'});});
      }
      weekDateLabel(box, date, first);
      const gz = append(box, 'b', 'of-gz'); gz.dataset.noI18n = '';
      append(gz, 'span', stemClass(d.day_pillar[0]), d.day_pillar[0]); append(gz, 'span', branchClass(d.day_pillar[1]), d.day_pillar[1]);
      const officer = append(box, 'span', 'of-officer', officerShort(d.officer)); officer.dataset.noI18n = ''; tip(officer, calT(d.officer));
      if (d.jie_on_date) officerJieText(append(box, 'small', 'of-jie'), d, true);
      if (!entry.pick) {
        const why = append(box, 'span', 'ds-reason', SCAN_REASONS[d.reason]);
        if (d.reason === 'natal_clash') why.append(' ' + clashText(d));
        append(box, 'span', 'ds-reason-short', SCAN_REASONS_SHORT[d.reason]);
        return;
      }
      if (d.natal_clashes.length) append(box, 'span', 'ds-clash', clashText(d));
      if (d.hour_charts.length) {
        const hours = append(box, 'span', 'ds-hours');
        d.hour_charts.forEach(h => {const line = texts(append(hours, 'span'), h.local_time, ' '); append(line, 'span', 'ds-hour-bureau', chartLine(h));});
      }
    });
    append(result, 'p', 'field-help', '一行一周，从星期一开始。候选日可以点开，下方列出它的农历、相冲、交节和时家奇门盘；变淡的日子写着把它排除的条件。');
    const pick = r.candidates.find(c => c.date === dateScanPick);
    if (pick) renderDateScanDetail(pick, r, lunarText, clashText, chartLine);
  } else {
    const table = append(append(result, 'div', 'table-wrap'), 'table', 'data-table'); table.id = 'scan-list';
    const hr = append(append(table, 'thead'), 'tr');
    ['公历日', '农历', '日干支', '值日', '本命相冲', '时家奇门'].forEach(x => append(hr, 'th', null, x));
    const body = append(table, 'tbody');
    r.candidates.forEach(c => {
      const tr = append(body, 'tr');
      const qimen = c.hour_charts.map(h => `${h.local_time} ${chartLine(h)} 值符${h.zhi_fu_star} 值使${h.zhi_shi_door}`).join('；') || '—';
      append(tr, 'td', null, c.date); lunarText(append(tr, 'td'), c); append(tr, 'td', null, c.day_pillar);
      const officer = append(tr, 'td', null, c.officer);
      if (c.jie_on_date) officerJieText(append(officer, 'small', 'ds-jie-line'), c, false);
      [clashText(c) || '—', qimen].forEach(x => append(tr, 'td', null, x));
    });
  }
  if (!r.candidates.length) append(result, 'p', 'feature-note', '没有满足全部条件的日子，可以放宽条件或延长扫描天数。');
  if (unscanned) {
    const more = append(result, 'p', 'feature-note', '候选日或时家奇门盘已达上限，后面的日子没有扫描；可以缩短范围、减少候选时刻，或从最后扫描的日子之后再扫一次。');
    const next = shiftDate(r.scanned_through, 1);
    const go = append(more, 'button', 'tiny-button', '从下一天继续扫描'); go.type = 'button'; go.id = 'scan-continue';
    tip(go, next);
    go.addEventListener('click', () => {dateScanDraft = {...dateScanDraft, start_date: next}; render(); const run = $('#scan-run'); if (run) {run.focus(); run.click();}});
  }
  r.limitations.forEach(x => note(result, x));
}
// One candidate in full: the lunar date, pillar, officer and jie, natal clashes, and a card per hour chart that can be
// opened on the Qimen page at the same moment and time zone.
function renderDateScanDetail(c, r, lunarText, clashText, chartLine) {
  const panel = append(result, 'section', 'cal-detail ds-detail'); panel.id = 'scan-detail';
  texts(append(panel, 'h4', 'cal-detail-date'), c.date, ' · ', WEEKDAY_NAMES[weekdayOf(c.date)]);
  const facts = append(panel, 'div', 'cal-detail-facts');
  const fact = (label, ...parts) => texts(append(facts, 'p'), label, ' ', ...parts);
  lunarText(fact('农历'), c);
  const gz = append(fact('日干支'), 'b', 'ds-gz'); gz.dataset.noI18n = '';
  append(gz, 'span', stemClass(c.day_pillar[0]), c.day_pillar[0]); append(gz, 'span', branchClass(c.day_pillar[1]), c.day_pillar[1]);
  const officer = fact('值日', c.officer);
  if (c.jie_on_date) {officer.append(' · '); officerJieText(officer, c, false);}
  if (r.criteria.natal_branches) fact('本命相冲', clashText(c) || '无');
  if (!c.hour_charts.length) {
    append(panel, 'p', 'field-help', '在「候选时刻」里填时刻（如 09:00,15:00），每个候选日都会附上这些时刻的时家奇门盘。');
    return;
  }
  const cards = append(panel, 'div', 'ds-hour-cards');
  c.hour_charts.forEach((h, i) => {
    const card = append(cards, 'div', 'ds-hour-card');
    const head = append(card, 'div', 'ds-hour-head');
    append(head, 'b', null, h.local_time); texts(append(head, 'span'), chartLine(h), ' · ', h.yuan);
    texts(append(card, 'p'), '节气', ' ', h.solar_term, ' · ', '时柱', ' ', h.hour_pillar);
    texts(append(card, 'p'), '值符', ' ', h.zhi_fu_star, ' · ', '宫', ' ', h.zhi_fu_palace);
    texts(append(card, 'p'), '值使', ' ', h.zhi_shi_door, ' · ', '宫', ' ', h.zhi_shi_palace);
    texts(append(card, 'p'), '空亡', ' ', h.void_branches.join('、'));
    const open = append(card, 'button', 'tiny-button', '在奇门页打开'); open.type = 'button'; open.id = 'scan-qimen-' + i;
    open.addEventListener('click', () => {
      qimenMoment = {mode: 'custom', custom: c.date + 'T' + h.local_time, zone: r.criteria.timezone, basis: null, lateZi: false, scan: true}; qimenResult = null; qimenFingerprint = null;
      const tab = tabs.find(t => t.dataset.tab === 'qimen');
      activateTab(tab); tab.focus();
      const run = $('#qimen-run'); if (run) run.click();
    });
  });
}
function timelineList(parent, tl, focusName, nowYear) {
  const table = append(parent, 'table', 'data-table yt-list');
  const head = append(append(table, 'thead'), 'tr');
  ['农历年', '化禄', '化权', '化科', '化忌', ...(focusName ? ['所选宫位'] : [])].forEach(t => append(head, 'th', HUA_CLASS[t] ? 'yt-' + HUA_CLASS[t] : null, t));
  const tbody = append(table, 'tbody');
  tl.entries.forEach(year => {
    const now = year.lunar_year === nowYear, row = append(tbody, 'tr', now ? 'is-now' : null);
    if (now) row.setAttribute('aria-current', 'date');
    const first = append(row, 'td', 'yt-list-year'); texts(first, year.lunar_year, ' ');
    const gz = append(first, 'b', 'yt-gz'); gz.dataset.noI18n = '';
    append(gz, 'span', stemClass(year.year_pillar[0]), year.year_pillar[0]); append(gz, 'span', branchClass(year.year_pillar[1]), year.year_pillar[1]);
    if (now) append(first, 'small', 'yt-now', '今年');
    year.transformations.forEach(t => {
      const td = append(row, 'td', t.natal_palace === focusName ? 'is-focus' : null);
      append(td, 'b', null, t.star); texts(td, ' → ', t.natal_palace);
    });
    if (focusName) append(row, 'td', null, year.focus_hits.map(t => t.star + t.type).join(' · ') || '—');
  });
  return table;
}
function renderTimeline() {
  title(result,'连续农历年四化对照','本命盘固定，叠加多个命名农历年的天干四化标签');
  if(!current){append(result,'p','info-inline','请先生成命盘。');return;}
  const row=append(result,'div','inline-control');
  ensureTodayLunarYear();
  const start=createInput('起始农历年','number',String(timelineDraft.start_lunar_year ?? defaultLunarYear()),row);start.id='timeline-start';start.min='1901';start.max='2099';
  const years=append(append(row,'label',null,'对照年数'),'select');years.id='timeline-years';
  [3,5,10,20,30].forEach(x=>{const op=texts(append(years,'option'),x,' 年');op.value=String(x);});years.value=String(timelineDraft.years);
  const focus=append(append(row,'label',null,'关注宫位'),'select');focus.id='timeline-focus';
  const all=append(focus,'option',null,'全部十二宫');all.value='';
  current.ziwei.palaces.forEach(p=>{const op=append(focus,'option',null,p.name);op.value=p.name;});focus.value=timelineDraft.focus_palace;
  keepTyped(start,years,focus);
  const run=append(row,'button',null,'生成年度轨迹');run.id='timeline-run';run.type='button';
  const msg=append(result,'p','inline-msg');
  run.addEventListener('click',async()=>{
    timelineDraft={start_lunar_year:Number(start.value),years:Number(years.value),focus_palace:focus.value};
    run.disabled=true;msg.textContent='';
    try{const data=await postForChart('/api/annual-timeline',{birth:currentInput,start_lunar_year:timelineDraft.start_lunar_year,years:timelineDraft.years,focus_palace:timelineDraft.focus_palace||null});if(data!==STALE){timelineResult=data;render();}}
    catch(e){msg.textContent='查询失败：'+e.message;}
    finally{run.disabled=false;}
  });
  if(!timelineResult){append(result,'p','info-inline','选择起始农历年和年数，可按本命宫位查看每年的四化标记。');return;}
  const tl = timelineResult, focusName = tl.focus_palace || '';
  const tags = append(result, 'div', 'meta-tags');
  texts(append(tags, 'span'), '农历年', ' ' + tl.start_lunar_year + '–' + (tl.start_lunar_year + tl.years - 1));
  append(tags, 'span', null, tl.school);
  const views = append(result, 'div', 'layer-modes yt-views');
  views.setAttribute('role', 'group'); views.setAttribute('aria-label', '显示方式');
  [['matrix', '宫位矩阵'], ['list', '逐年列表']].forEach(([key, name]) => {
    const button = append(views, 'button', 'layer-btn' + (timelineView === key ? ' active' : ''), name);
    button.type = 'button'; button.id = 'timeline-view-' + key; button.setAttribute('aria-pressed', String(timelineView === key));
    button.addEventListener('click', () => {timelineView = key; render();});
  });
  const nowYear = todayLunarYear;
  if (timelineView === 'matrix') {
    // Palaces down the side in their fixed order, lunar years across: each cell holds the transformations of that
    // year's stem that fall in the palace. A year header opens that year's layer on the Zi Wei chart.
    const palaces = Object.keys(tl.natal_palace_label_counts);
    const wrap = append(result, 'div', 'yt-wrap');
    const table = append(wrap, 'table', 'yt-matrix'); table.id = 'timeline-matrix';
    append(table, 'caption', 'visually-hidden', '本命十二宫逐年所落的流年四化');
    const head = append(append(table, 'thead'), 'tr');
    append(head, 'th', 'yt-corner', '本命宫位').scope = 'col';
    tl.entries.forEach(year => {
      const now = year.lunar_year === nowYear;
      const th = append(head, 'th', 'yt-year-cell' + (now ? ' is-now' : '')); th.scope = 'col';
      const open = append(th, 'button', 'yt-year'); open.type = 'button'; open.id = 'timeline-year-' + year.lunar_year;
      tip(open, '在紫微盘打开 ' + year.lunar_year + ' 年流年层');
      if (now) open.setAttribute('aria-current', 'date');
      append(open, 'small', null, String(year.lunar_year));
      const gz = append(open, 'b', 'yt-gz'); gz.dataset.noI18n = '';
      append(gz, 'span', stemClass(year.year_pillar[0]), year.year_pillar[0]); append(gz, 'span', branchClass(year.year_pillar[1]), year.year_pillar[1]);
      if (now) append(open, 'small', 'yt-now', '今年');
      open.addEventListener('click', () => {
        ziweiLayer = {mode: 'year', decade: null, year: year.lunar_year, date: null};
        activateTab(tabs.find(t => t.dataset.tab === 'ziwei'));
        announce('紫微盘已切到 ' + year.lunar_year + ' 年流年层');
      });
    });
    // The palace column stays put while the years scroll, so a year reached by the keyboard is brought out from under it.
    wrap.addEventListener('focusin', e => {
      const cell = e.target.closest('.yt-year-cell'); if (!cell) return;
      const left = cell.offsetLeft - table.querySelector('.yt-corner').offsetWidth, right = cell.offsetLeft + cell.offsetWidth - wrap.clientWidth;
      if (wrap.scrollLeft > left) wrap.scrollLeft = left; else if (wrap.scrollLeft < right) wrap.scrollLeft = right;
    });
    const body = append(table, 'tbody');
    palaces.forEach(name => {
      const natal = current.ziwei.palaces.find(p => p.name === name);
      const tr = append(body, 'tr', name === focusName ? 'is-focus' : null);
      const th = append(tr, 'th', 'yt-palace'); th.scope = 'row';
      append(th, 'span', 'yt-palace-name', name);
      // Without the birth hour the palaces stand on a 12:00 stand-in, so their stem and branch are left out.
      if (natal && !currentHourUnknown) {const at = append(th, 'small', 'yt-branch', natal.stem + natal.branch); at.dataset.noI18n = '';}
      const count = tl.natal_palace_label_counts[name];
      if (count) texts(append(th, 'small', 'yt-count'), '×', count);
      tl.entries.forEach(year => {
        const td = append(tr, 'td', year.lunar_year === nowYear ? 'is-now' : null);
        year.transformations.filter(t => t.natal_palace === name).forEach(t => {
          const item = append(td, 'span', 'yt-hua');
          tip(huaBadge(item, t.type, 'year'), year.lunar_year + ' ' + year.year_pillar + ' · ' + t.star + t.type);
          append(item, 'span', 'yt-star', t.star);
        });
      });
    });
    const help = append(result, 'p', 'field-help yt-screen');
    append(help, 'span', null, '一列一个农历年，格子里是该年天干的四化星落在本命哪一宫，宫名下的「×」是这些年里落入该宫的次数；点年份在紫微盘打开该年的流年层。');
    if (focusName) append(help, 'span', null, '所选宫位整行加框。');
    // A wide grid cannot fit a printed page, so print carries the same years as the list.
    timelineList(append(result, 'div', 'table-wrap yt-print-list'), tl, focusName, nowYear);
  } else {
    timelineList(append(result, 'div', 'table-wrap'), tl, focusName, nowYear).id = 'timeline-list';
  }
  if (currentHourUnknown) append(result, 'p', 'field-help', '时辰不详：宫位按 12:00 占位时辰排出，落宫会随时辰变化。');
  timelineResult.limitations.forEach(x=>note(result,x));
}
function numericEntry(input) { return input.value.trim() === '' ? NaN : Number(input.value); }
function readDecisionDraft() {
  const question=$('#decision-question')?.value.trim()||'';
  const criteria=[...result.querySelectorAll('.criterion-edit')].map(node=>({name:node.querySelector('.criterion-name').value.trim(),weight:numericEntry(node.querySelector('.criterion-weight'))}));
  const options=[...result.querySelectorAll('.option-edit')].map(node=>({name:node.querySelector('.option-name').value.trim(),ratings:[...node.querySelectorAll('.option-rating')].map(numericEntry)}));
  return {question,criteria,options};
}
// The decision page: a grid of options by criteria. Once compared, edits recompute on their own; only the result
// below the grid is redrawn, so typing keeps its place.
let decisionTicket = 0, decisionTimer = null, decisionAbort = null, decisionAuto = false;
// The request the result shown answers, and why the latest comparison failed: kept so a redraw (another tool and
// back) still marks a result that no longer matches the grid.
let decisionResultKey = null, decisionError = '', decisionPending = false;
// Two decimals, but a small nonzero number keeps two significant figures instead of reading as 0.
const dmNum = (x, digits = 2) => {
  x = Number(x);
  const fixed = Number(x.toFixed(digits));
  return String(fixed === 0 && x !== 0 ? Number(x.toPrecision(2)) : fixed);
};
const dmShare = x => {
  const pct = 100 * x;
  return (pct > 0 && pct < 0.05 ? '< 0.1' : pct < 100 && pct > 99.95 ? '> 99.9' : String(Number(pct.toFixed(1)))) + '%';
};
// Enough decimals that scores which differ never print the same.
function dmDigits(scores) {
  const sorted = [...new Set(scores)].sort((a, b) => a - b);
  for (let d = 2; d < 6; d++) if (sorted.every((x, i) => !i || x.toFixed(d) !== sorted[i - 1].toFixed(d))) return d;
  return 6;
}
// Names typed by the user stay as typed; the 、 between them is its own text node and reads ", " in English.
function dmNames(parent, names) {
  names.forEach((name, i) => {if (i) parent.append('、'); append(parent, 'span', 'user-text', name);});
  return parent;
}
const dmStale = () => !!decisionResult && (!!decisionError || decisionResultKey !== JSON.stringify(decisionRequest(decisionDraft)));
function decisionRequest(draft) {
  return {question: draft.question, criteria: draft.criteria,
    options: draft.options.map(o => ({name: o.name, ratings: Object.fromEntries(draft.criteria.map((c, j) => [c.name, o.ratings[j]]))}))};
}
async function compareDecision(button) {
  clearTimeout(decisionTimer);
  // The draft follows every edit; the grid is read again only while it is on screen (a pending recompute can fire
  // after another tool has opened).
  if (active === 'decision' && $('#decision-grid')) decisionDraft = readDecisionDraft();
  if (decisionAbort) decisionAbort.abort();
  const ticket = ++decisionTicket, abort = decisionAbort = new AbortController();
  const body = decisionRequest(decisionDraft), key = JSON.stringify(body);
  decisionError = ''; decisionPending = true;
  const msg = $('#decision-msg');
  if (msg) msg.textContent = '';
  if (button) button.disabled = true;
  try {
    const data = await postJSON('/api/decision-matrix', body, abort.signal);
    if (ticket !== decisionTicket) return;
    decisionResult = data; decisionResultKey = key; decisionAuto = true;
    const top = data.ranked_options[0];
    announce(calT(data.joint_leaders.length > 1 ? '并列首位' : '首位') + ' ' + data.joint_leaders.join(', ') + ' ' + dmNum(top.score, dmDigits(data.ranked_options.map(o => o.score))) + ' / 5');
    if (active !== 'decision') return;
    const box = $('#decision-output');
    if (box) renderDecisionOutput(box); else render();
  } catch (e) {
    if (ticket !== decisionTicket || e.name === 'AbortError') return;
    decisionError = '比较失败：' + e.message;
    announce(calT(decisionError));
    if (active !== 'decision') return;
    const m = $('#decision-msg'); if (m) m.textContent = decisionError;
    // The last result stays for reference, labelled as no longer matching the grid.
    $('#decision-output')?.classList.add('is-stale');
  } finally {
    if (ticket === decisionTicket) decisionPending = false;
    if (button) button.disabled = false;
  }
}
function renderDecision() {
  if (JSON.stringify(decisionDraft) === decisionExampleShown) {
    decisionDraft = JSON.parse(JSON.stringify(DECISION_EXAMPLE), (key, value) => typeof value === 'string' ? calT(value) : value);
    decisionExampleShown = JSON.stringify(decisionDraft);
  }
  title(result,'透明方案决策矩阵','权重归一化 · 逐项贡献 · 剔除单项敏感性 · 无命理加权');
  append(result,'p','info-inline','这里的分数均为你自己输入的主观假设，不能代表客观成功率。');
  const question=createInput('你要比较什么？','text',decisionDraft.question,result);question.id='decision-question';question.maxLength=300;
  // Structural edits keep what was typed, and recompute at once when a comparison is already showing.
  // Focus moves to the field that took the removed one's place, or to the name of what was added.
  const restructure = (change, focus) => {
    const draft = readDecisionDraft(); if (!change(draft)) return;
    decisionDraft = draft; render();
    const target = document.getElementById(focus(draft));
    if (target) {target.focus(); if (target.select) target.select();}
    if (decisionAuto) compareDecision();
  };
  append(result,'h4','subheading','方案 × 指标');
  append(result,'p','field-help','表头写评价维度和权重（大于零），每行一个方案，格子里填 0–5 的评分。');
  const wrap = append(result, 'div', 'dm-wrap');
  const grid = append(wrap, 'table', 'dm-grid'); grid.id = 'decision-grid';
  append(grid, 'caption', 'visually-hidden', '备选方案在各评价维度上的评分');
  const head = append(append(grid, 'thead'), 'tr');
  append(head, 'th', 'dm-corner', '方案').scope = 'col';
  decisionDraft.criteria.forEach((c, i) => {
    const th = append(head, 'th', 'criterion-edit'); th.scope = 'col';
    const top = append(th, 'div', 'dm-head');
    append(top, 'span', 'dm-swatch dm-c' + i).setAttribute('aria-hidden', 'true');
    const name = append(top, 'input', 'criterion-name'); name.type = 'text'; name.value = c.name; name.maxLength = 40;
    name.id = 'decision-criterion-' + i; name.setAttribute('aria-label', '指标 ' + (i + 1));
    const remove = append(top, 'button', 'tiny-button remove-criterion', '×'); remove.type = 'button';
    tip(remove, '移除指标'); remove.setAttribute('aria-label', '移除指标 ' + (i + 1)); remove.disabled = decisionDraft.criteria.length <= 1;
    remove.addEventListener('click', () => restructure(d => {
      if (d.criteria.length <= 1) return false;
      d.criteria.splice(i, 1); d.options.forEach(o => o.ratings.splice(i, 1)); return true;
    }, d => 'decision-criterion-' + Math.min(i, d.criteria.length - 1)));
    const weightLabel = append(th, 'label', 'dm-weight');
    const weightText = append(weightLabel, 'span', null, '权重'); weightText.id = 'decision-weight-label-' + i;
    const weight = append(weightLabel, 'input', 'criterion-weight'); weight.type = 'number'; weight.value = String(c.weight);
    weight.min = '.01'; weight.max = '100'; weight.step = '.01'; weight.id = 'decision-weight-' + i;
    // Named by the criterion as typed and the word 权重, so each weight is read out as its own.
    weight.setAttribute('aria-labelledby', 'decision-criterion-' + i + ' decision-weight-label-' + i);
  });
  const body = append(grid, 'tbody');
  decisionDraft.options.forEach((o, i) => {
    const tr = append(body, 'tr', 'option-edit');
    const th = append(tr, 'th', 'dm-option'); th.scope = 'row';
    const name = append(th, 'input', 'option-name'); name.type = 'text'; name.value = o.name; name.maxLength = 80;
    name.id = 'decision-option-' + i; name.setAttribute('aria-label', '方案 ' + (i + 1));
    const remove = append(th, 'button', 'tiny-button remove-option', '×'); remove.type = 'button';
    tip(remove, '移除方案'); remove.setAttribute('aria-label', '移除方案 ' + (i + 1)); remove.disabled = decisionDraft.options.length <= 2;
    remove.addEventListener('click', () => restructure(d => {
      if (d.options.length <= 2) return false;
      d.options.splice(i, 1); return true;
    }, d => 'decision-option-' + Math.min(i, d.options.length - 1)));
    decisionDraft.criteria.forEach((c, j) => {
      const score = append(append(tr, 'td'), 'input', 'option-rating'); score.type = 'number';
      score.value = String(o.ratings[j] ?? 3); score.min = '0'; score.max = '5'; score.step = '.5';
      // Named by the option and the criterion as typed, so a renamed row or column is read out as it now stands.
      score.setAttribute('aria-labelledby', 'decision-option-' + i + ' decision-criterion-' + j);
    });
  });
  const controls = append(result, 'div', 'inline-control dm-controls');
  const addCriterion = append(controls, 'button', 'tiny-button', '+ 增加指标'); addCriterion.id = 'decision-add-criterion'; addCriterion.type = 'button';
  addCriterion.disabled = decisionDraft.criteria.length >= 8;
  addCriterion.addEventListener('click', () => restructure(d => {
    if (d.criteria.length >= 8) return false;
    d.criteria.push({name: '新指标' + (d.criteria.length + 1), weight: 1}); d.options.forEach(o => o.ratings.push(3)); return true;
  }, d => 'decision-criterion-' + (d.criteria.length - 1)));
  const addOption = append(controls, 'button', 'tiny-button', '+ 增加方案'); addOption.id = 'decision-add-option'; addOption.type = 'button';
  addOption.disabled = decisionDraft.options.length >= 8;
  addOption.addEventListener('click', () => restructure(d => {
    if (d.options.length >= 8) return false;
    d.options.push({name: '新方案 ' + (d.options.length + 1), ratings: d.criteria.map(() => 3)}); return true;
  }, d => 'decision-option-' + (d.options.length - 1)));
  const run = append(controls, 'button', null, '比较方案'); run.id = 'decision-run'; run.type = 'button';
  run.addEventListener('click', () => compareDecision(run));
  const msg = append(result, 'p', 'inline-msg', decisionError); msg.id = 'decision-msg';
  // Every edit goes into the draft at once, so a redraw keeps what was typed.
  const live = () => {
    decisionDraft = readDecisionDraft();
    if (!decisionAuto) return;
    clearTimeout(decisionTimer); decisionTimer = setTimeout(() => compareDecision(), 450);
  };
  grid.addEventListener('input', live); question.addEventListener('input', live);
  const out = append(result, 'div', 'dm-output'); out.id = 'decision-output';
  if (decisionResult) {
    renderDecisionOutput(out);
    out.classList.toggle('is-stale', dmStale() && !decisionPending);
    // Back on the page with edits that were never compared (the recompute was cut short): compare them now.
    if (decisionAuto && !decisionError && !decisionPending && decisionResultKey !== JSON.stringify(decisionRequest(decisionDraft))) {
      clearTimeout(decisionTimer); decisionTimer = setTimeout(() => {if (active === 'decision') compareDecision();});
    }
  }
}
function renderDecisionOutput(out) {
  out.replaceChildren(); out.classList.remove('is-stale');
  const d = decisionResult, colour = Object.fromEntries(d.criteria.map((c, i) => [c.name, i]));
  // Joint leaders in the order the options are listed, as on the cards below.
  const leaders = d.ranked_options.map(o => o.name).filter(name => d.joint_leaders.includes(name)), top = d.ranked_options[0].score;
  const digits = dmDigits(d.ranked_options.map(o => o.score)), score = x => dmNum(x, digits);
  // The new leader is announced through the page's live region; this line is redrawn with every result.
  const status = append(out, 'p', 'dm-status'); status.id = 'decision-status';
  texts(append(status, 'span'), leaders.length > 1 ? '并列首位' : '首位');
  status.append(' '); dmNames(append(status, 'b'), leaders); status.append(' ');
  texts(append(status, 'span', 'dm-status-score'), score(top), ' / 5');
  append(out, 'p', 'dm-stale-note', '输入改动后还没算出新结果，下面是上一次的比较。');

  append(out, 'h4', 'subheading', '权重占比');
  const bar = append(out, 'div', 'dm-weights'); bar.setAttribute('aria-hidden', 'true');
  d.criteria.forEach(c => {const seg = append(bar, 'span', 'dm-seg dm-c' + colour[c.name]); seg.style.width = 100 * c.normalized_weight + '%';});
  const legend = append(out, 'ul', 'dm-legend');
  d.criteria.forEach(c => {
    const li = append(legend, 'li');
    append(li, 'span', 'dm-swatch dm-c' + colour[c.name]).setAttribute('aria-hidden', 'true');
    append(li, 'span', 'user-text', c.name);
    texts(append(li, 'b'), dmShare(c.normalized_weight));
    texts(append(li, 'small', 'muted'), '权重', ' ', dmNum(c.raw_weight));
  });

  append(out, 'h4', 'subheading', '按用户权重计算的方案得分');
  const list = append(out, 'ol', 'dm-ranks'); list.id = 'decision-ranks';
  d.ranked_options.forEach((o, i) => {
    const rank = 1 + d.ranked_options.filter(x => x.score > o.score).length, lead = leaders.includes(o.name);
    const li = append(list, 'li', 'dm-option-card' + (lead ? ' is-lead' : '')); li.id = 'decision-rank-' + i;
    const line = append(li, 'div', 'dm-line');
    texts(append(line, 'span', 'dm-rank'), rank);
    append(line, 'b', 'dm-name user-text', o.name);
    if (lead) append(line, 'span', 'dm-tag', leaders.length > 1 ? '并列首位' : '首位');
    else texts(append(line, 'span', 'dm-gap muted'), '比首位低', ' ', dmNum(top - o.score, digits));
    append(append(line, 'span', 'dm-score', score(o.score)), 'small', null, ' / 5');
    // The bar runs on the 0–5 scale; each part is one criterion's rating times its share of the weight.
    const track = append(li, 'div', 'dm-track'); track.setAttribute('aria-hidden', 'true'); track.dataset.noI18n = '';  // the tooltips quote typed names
    o.contributions.forEach(c => {
      const seg = append(track, 'span', 'dm-seg dm-c' + colour[c.criterion]); seg.style.width = 100 * c.weighted_contribution / 5 + '%';
      tip(seg, c.criterion + ' ' + c.rating + ' × ' + dmShare(c.normalized_weight) + ' = ' + dmNum(c.weighted_contribution));
    });
    const parts = append(li, 'ul', 'dm-parts');
    o.contributions.forEach(c => {
      const part = append(parts, 'li');
      append(part, 'span', 'dm-swatch dm-c' + colour[c.criterion]).setAttribute('aria-hidden', 'true');
      append(part, 'span', 'user-text', c.criterion);
      texts(append(part, 'span', 'dm-math'), ' ', dmNum(c.rating), ' × ', dmShare(c.normalized_weight), ' = ', dmNum(c.weighted_contribution));
    });
  });

  append(out, 'h4', 'subheading', '首位有多稳');
  const sens = d.leave_one_out_sensitivity, limits = Object.fromEntries((d.weight_thresholds || []).map(x => [x.criterion, x]));
  if (!sens.length) append(out, 'p', 'info-inline', '只有一个指标时，权重不影响排序。');
  else {
    append(out, 'p', 'field-help', leaders.length > 1
      ? '目前有并列首位，只列去掉各指标后的首位，不算权重临界点。'
      : '其他权重不变时，每个指标的权重在区间内变动，首位都不变；越过边界时领先的方案写在箭头后。最后一列是完全去掉该指标后的首位。');
    const table = append(append(out, 'div', 'table-wrap'), 'table', 'data-table dm-sens'); table.id = 'decision-sensitivity';
    append(table, 'caption', 'visually-hidden', '首位有多稳');
    const hr = append(append(table, 'thead'), 'tr');
    const heads = ['当前权重', ...(leaders.length > 1 ? [] : ['首位不变的权重区间']), '去掉此项后首位'];
    ['指标', ...heads].forEach(x => append(hr, 'th', null, x));
    // On a narrow screen the rows stack, and each cell names its column itself.
    const cell = (tr, cls, i) => {const td = append(tr, 'td', cls); append(td, 'span', 'dm-cell-label', heads[i]); return td;};
    const tbody = append(table, 'tbody');
    sens.forEach(x => {
      const c = d.criteria.find(k => k.name === x.omitted_criterion), limit = limits[x.omitted_criterion];
      const tr = append(tbody, 'tr');
      const name = append(tr, 'th', 'dm-sens-name'); name.scope = 'row';
      append(name, 'span', 'dm-swatch dm-c' + colour[c.name]).setAttribute('aria-hidden', 'true');
      append(name, 'span', 'user-text', c.name);
      const now = cell(tr, 'dm-num', 0); texts(now, dmNum(c.raw_weight), ' '); append(now, 'small', 'muted', '(' + dmShare(c.normalized_weight) + ')');
      if (limit) {
        const box = cell(tr, 'dm-range-cell', 1);
        const low = limit.lower, high = limit.upper;
        // The band is the share of the weight over which the leader holds; the mark is the share it has now.
        const range = append(box, 'div', 'dm-range'); range.setAttribute('aria-hidden', 'true');
        const band = append(range, 'span', 'dm-band');
        const from = low ? low.normalized_weight : 0, to = high ? high.normalized_weight : 1;
        band.style.left = 100 * from + '%'; band.style.width = 100 * (to - from) + '%';
        append(range, 'span', 'dm-mark').style.left = 100 * c.normalized_weight + '%';
        const span = append(box, 'div', 'dm-range-text');
        if (!low && !high) append(span, 'span', null, '任意权重下首位都不变');
        else {
          texts(append(span, 'b'), low ? dmNum(low.raw_weight) : '0', ' – ', high ? dmNum(high.raw_weight) : '∞');
          [[low, '<'], [high, '>']].filter(([edge]) => edge).forEach(([edge, sign]) => {
            const row = append(box, 'div', 'dm-edge');
            texts(row, sign, ' ', dmNum(edge.raw_weight), ' (', dmShare(edge.normalized_weight), ') → ');
            dmNames(append(row, 'b'), edge.new_leaders);
          });
        }
      }
      const without = cell(tr, null, heads.length - 1);
      dmNames(append(without, 'span'), x.leaders_without_it);
      append(without, 'span', 'dm-tag' + (x.leader_changed ? ' is-changed' : ''), x.leader_changed ? '首位改变' : '不变');
    });
  }
  d.limitations.forEach(x => note(out, x));
}
// Rule sensitivity matrix: the current chart recomputed under each common rule choice, cell by cell.
let ruleMatrixResult = null, ruleMatrixKey = null, ruleMatrixError = '', ruleMatrixOnlyDiff = false, ruleMatrixFocus = null;
// A sexagenary pair or a lone branch in its element colours; other values as plain text.
// The coloured characters are kept from translation; the rest (宫名, 五行局, stars) is translated as usual.
function ganzhiValue(parent, text) {
  const glyph = (cls, ch) => {append(parent, 'span', cls, ch).dataset.noI18n = '';};
  if (text.length === 2 && STEM_ORDER.includes(text[0]) && BRANCH_ORDER.includes(text[1])) {glyph(stemClass(text[0]), text[0]); glyph(branchClass(text[1]), text[1]); return parent;}
  if (BRANCH_ORDER.includes(text[0]) && (text.length === 1 || text.startsWith(' · ', 1))) {
    glyph(branchClass(text[0]), text[0]);
    if (text.length > 1) {parent.append(' · '); append(parent, 'span', null, text.slice(4));}
    return parent;
  }
  append(parent, 'span', null, text); return parent;
}
// Minutes between two local readings ("YYYY-MM-DDTHH:MM"), read as wall-clock values.
const readingMinutes = (a, b) => Math.round((Date.parse(a + ':00Z') - Date.parse(b + ':00Z')) / 60000);
function ruleShift(parent, row, base) {
  const minutes = readingMinutes(row.effective_reading, base.effective_reading);
  const time = row.effective_reading.slice(0, 10) === base.effective_reading.slice(0, 10) ? row.effective_reading.slice(11, 16) : row.effective_reading.replace('T', ' ');
  append(parent, 'b', 'rm-time', time);
  if (!minutes) {append(parent, 'span', 'muted', '时刻不变'); return;}
  const shift = append(parent, 'span', 'rm-shift');
  shift.append(minutes < 0 ? '−' : '+'); durationText(shift, Math.abs(minutes));
  tip(shift, calT(minutes < 0 ? '比当前设置早' : '比当前设置晚'));
}
function ruleApply(parent, row, id) {
  if (row.is_baseline || !row.differs.length) return;
  if (!row.applicable) {append(parent, 'small', 'muted', '需手动改时间'); return;}
  const apply = append(parent, 'button', 'tiny-button', '套用'); apply.type = 'button'; apply.id = id;
  apply.setAttribute('aria-label', calT('套用') + ' ' + row.label.split(' + ').map(calT).join(' + '));
  apply.addEventListener('click', () => {setInput(row.settings); form.requestSubmit(); setFeedback('已套用：' + row.label);});
}
function renderRuleMatrix() {
  title(result, '规则差异对照', '同一份出生资料换用各家常见规则重排 · 看哪些字段会变');
  const request = {birth: currentInput, hour_unknown: currentHourUnknown};
  const key = JSON.stringify(request);
  if (ruleMatrixKey !== key) {
    ruleMatrixKey = key; ruleMatrixResult = null; ruleMatrixError = ''; ruleMatrixFocus = null;
    postJSON('/api/rule-matrix', request)
      .then(data => {if (ruleMatrixKey === key) ruleMatrixResult = data;})
      .catch(err => {if (ruleMatrixKey === key) ruleMatrixError = err.message;})
      .finally(() => {if (active === 'rule-matrix') render();});
  }
  if (ruleMatrixError) {append(result, 'p', 'inline-msg', '对照失败：' + ruleMatrixError); return;}
  if (!ruleMatrixResult) {append(result, 'p', 'field-help', '正在按各种规则重新排盘…'); loadingGhost(result, 'table'); return;}
  const m = ruleMatrixResult, s = m.summary, base = m.rows[0];
  const fieldLabel = Object.fromEntries(m.fields.map(f => [f.key, f.label]));
  const cards = append(result, 'div', 'rule-summary');
  const same = append(cards, 'div', 'rule-card');
  texts(append(same, 'strong', 'rule-big'), String(s.identical_variants), ' / ', String(s.variants));
  append(same, 'small', null, '种不同规则下结果与当前完全相同');
  const stable = append(cards, 'div', 'rule-card');
  append(stable, 'small', null, '不受规则影响');
  const stableChips = append(stable, 'div', 'rule-chips');
  if (!s.stable_fields.length) append(stableChips, 'span', 'muted', '—');
  const keyOf = Object.fromEntries(m.fields.map(f => [f.label, f.key]));
  s.stable_fields.forEach(name => {
    const chip = append(stableChips, 'span', 'relation-chip rel-harmony rm-stable');
    append(chip, 'span', null, name); ganzhiValue(append(chip, 'b'), base.values[keyOf[name]] || '');
  });
  const moving = append(cards, 'div', 'rule-card');
  append(moving, 'small', null, '会随规则变化');
  const movingChips = append(moving, 'div', 'rule-chips');
  if (!s.sensitive_fields.length) append(movingChips, 'span', 'muted', '—');
  s.sensitive_fields.forEach(f => {
    const chip = texts(append(movingChips, 'a', 'relation-chip rel-clash'), f.label, ' ', String(f.changed_by.length));
    chip.href = '#rm-field-' + f.field.replace('.', '-');
    tip(chip, f.changed_by.join('\n'));
    // The link keeps #tool=rule-matrix in the address, so it scrolls itself and moves focus to the field card.
    chip.addEventListener('click', event => {
      event.preventDefault(); const target = $('#rm-field-' + f.field.replace('.', '-')); if (!target) return;
      target.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start'});
      target.focus({preventScroll: true});
    });
  });
  m.hints.forEach(text => append(result, 'div', 'feature-note', text));
  // One rule at a time: what each common choice alone does to the reading and to the chart.
  const singles = m.rows.map((row, i) => [row, i]).filter(([row]) => !row.is_baseline && !row.label.includes(' + '));
  if (singles.length) {
    append(result, 'h3', 'subheading', '单独换一条规则');
    const grid = append(result, 'div', 'rm-singles'); grid.id = 'rule-singles';
    singles.forEach(([row, i]) => {
      const card = append(grid, 'div', 'rm-single' + (row.differs.length ? ' has-diff' : ''));
      append(card, 'b', 'rm-rule', row.label);
      if (m.hour_unknown) append(card, 'p', 'rm-when', '时辰不详，不列换算后的时刻');
      else ruleShift(append(card, 'p', 'rm-when'), row, base);
      const changes = append(card, 'div', 'rm-changes');
      if (!row.differs.length && m.hour_unknown) texts(append(changes, 'span', 'rm-same'), '参与对照的字段不变', '（', m.fields.map(f => calT(f.label)).join('、'), '）');
      else if (!row.differs.length) append(changes, 'span', 'rm-same', '结果不变');
      row.differs.forEach(k => {
        const chip = append(changes, 'span', 'rm-change');
        append(chip, 'span', null, fieldLabel[k]);
        const arrow = append(chip, 'span', 'rm-arrow');
        ganzhiValue(append(arrow, 'del'), base.values[k]); arrow.append(' → '); ganzhiValue(append(arrow, 'ins'), row.values[k]);
      });
      ruleApply(card, row, 'rule-single-apply-' + i);
    });
  }
  // Each field that moves: every value it takes and which rule choices give it.
  if (s.sensitive_fields.length) {
    append(result, 'h3', 'subheading', '会变的字段有几种结果');
    append(result, 'p', 'field-help rm-fields-hint', '点一个结果，下方表格只突出得出它的规则组合；数字是得出它的方案数，含当前设置。');
    const fields = append(result, 'div', 'rm-fields'); fields.id = 'rule-fields';
    s.sensitive_fields.forEach(f => {
      const card = append(fields, 'section', 'rm-field'); card.id = 'rm-field-' + f.field.replace('.', '-'); card.tabIndex = -1;
      const heading = append(card, 'h4', null, f.label); heading.id = card.id + '-title';
      const groups = new Map();
      m.rows.forEach(row => {const v = row.values[f.field]; if (!groups.has(v)) groups.set(v, []); groups.get(v).push(row);});
      const list = append(card, 'ul', 'rm-values'); list.setAttribute('aria-labelledby', heading.id);
      let index = 0;
      groups.forEach((rows, value) => {
        const item = append(list, 'li');
        const on = ruleMatrixFocus && ruleMatrixFocus.field === f.field && ruleMatrixFocus.value === value;
        const button = append(item, 'button', 'rm-value' + (on ? ' is-on' : '') + (rows.includes(base) ? ' is-base' : '')); button.type = 'button';
        button.id = card.id + '-value-' + index++;
        button.setAttribute('aria-pressed', on ? 'true' : 'false');
        ganzhiValue(append(button, 'b', 'rm-val'), value);
        if (rows.includes(base)) append(button, 'span', 'rm-tag', '当前');
        if (rows.length === 1) append(button, 'small', 'rm-count', '1 种');
        else texts(append(button, 'small', 'rm-count'), rows.length, ' ', '种');
        // The redraw keeps the button's id, so focus comes back to the value just pressed.
        button.addEventListener('click', () => {
          ruleMatrixFocus = on ? null : {field: f.field, value, button: button.id};
          render();
          const again = document.getElementById(button.id); if (again) again.focus();
          if (!on) announce([calT('突出'), calT(f.label), value].join(' ') + ' · ' + (rows.length === 1 ? calT('1 种组合') : rows.length + ' ' + calT('种组合')));
        });
        // Named by the single rules that give it (or the current settings); combinations are only counted.
        const rules = append(item, 'div', 'rm-rules');
        const named = rows.filter(row => row.is_baseline || !row.label.includes(' + '));
        const shown = named.length ? named : rows;
        shown.forEach(row => {
          const chip = append(rules, 'span', 'rm-combo' + (row.is_baseline ? ' is-base' : ''));
          row.label.split(' + ').forEach((part, k) => {if (k) append(chip, 'span', 'rm-plus', '+'); append(chip, 'span', null, part);});
        });
        const more = rows.length - shown.length;
        if (more === 1) append(rules, 'span', 'rm-more', '及另 1 种组合');
        else if (more) texts(append(rules, 'span', 'rm-more'), '及另', ' ', more, ' ', '种组合');
      });
    });
  }
  append(result, 'h3', 'subheading', '全部规则组合');
  const controls = append(result, 'div', 'inline-control');
  const toggle = append(controls, 'label', 'check-line');
  const only = append(toggle, 'input'); only.type = 'checkbox'; only.id = 'rule-only-diff'; only.checked = ruleMatrixOnlyDiff;
  toggle.append('只看结果不同的方案');
  only.addEventListener('change', () => {ruleMatrixOnlyDiff = only.checked; render();});
  if (ruleMatrixFocus) {
    const line = append(controls, 'span', 'rm-focus-note');
    texts(line, '突出', ' ', fieldLabel[ruleMatrixFocus.field], ' ');
    ganzhiValue(append(line, 'b'), ruleMatrixFocus.value);
    const clear = append(line, 'button', 'tiny-button', '取消突出'); clear.type = 'button'; clear.id = 'rule-focus-clear';
    // Clearing removes this button, so focus goes back to the value that was pressed.
    clear.addEventListener('click', () => {
      const pressed = ruleMatrixFocus.button; ruleMatrixFocus = null; render();
      const back = document.getElementById(pressed) || $('#rule-only-diff'); if (back) back.focus();
    });
  }
  const wrap = append(result, 'div', 'table-wrap');
  const table = append(wrap, 'table', 'data-table rule-matrix'); table.id = 'rule-matrix';
  const head = append(append(table, 'thead'), 'tr');
  append(head, 'th', null, '规则方案'); append(head, 'th', null, '换算后时间');
  m.fields.forEach(f => {const th = append(head, 'th', null, f.label); if (ruleMatrixFocus && ruleMatrixFocus.field === f.key) th.className = 'is-focus';});
  append(head, 'th', null, '');
  const body = append(table, 'tbody');
  m.rows.forEach((row, i) => {
    if (ruleMatrixOnlyDiff && !row.is_baseline && !row.differs.length) return;
    const lit = ruleMatrixFocus && row.values[ruleMatrixFocus.field] === ruleMatrixFocus.value;
    const tr = append(body, 'tr', (row.is_baseline ? 'is-baseline' : (row.differs.length ? 'has-diff' : 'is-same'))
      + (ruleMatrixFocus ? (lit ? ' is-lit' : ' is-dim') : ''));
    const name = append(tr, 'th');
    if (row.is_baseline) name.append(row.label);
    else row.label.split(' + ').forEach((part, k) => {if (k) append(name, 'span', 'rm-plus', '+'); append(name, 'span', 'rm-part', part);});
    const time = append(tr, 'td', 'rule-time');
    if (m.hour_unknown) append(time, 'span', 'muted', '时辰不详');
    else if (row.is_baseline) time.append(row.effective_reading.replace('T', ' '));
    else ruleShift(time, row, base);
    m.fields.forEach(f => {
      const changed = row.differs.includes(f.key);
      if (row.is_baseline || changed) ganzhiValue(append(tr, 'td', changed ? 'cell-diff' : null), row.values[f.key]);
      else append(append(tr, 'td'), 'span', 'muted', '＝');
    });
    ruleApply(append(tr, 'td'), row, 'rule-apply-' + i);
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
// The current chart's default name 我 shows in the interface language until it is changed.
let groupLabelShown = '我';
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
  if (groupDraft.useCurrent && currentInput) members.push({label: groupDraft.currentLabel.trim() || calT('我'), birth: birthOf(currentInput), hour_unknown: currentHourUnknown});
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
// Columns padded to line up; English text pads with plain spaces rather than the full-width ones Chinese lines use.
function textColumns(rows, plain = false) {
  const widths = rows[0].map((_, i) => Math.max(...rows.map(row => textWidth(row[i]))) + 2);
  return rows.map(row => row.map((cell, i) => {
    if (i === row.length - 1) return cell;
    const gap = widths[i] - textWidth(cell);
    return cell + (plain ? ' '.repeat(gap) : '　'.repeat(Math.floor(gap / 2)) + (gap % 2 ? ' ' : ''));
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
// A table for spreadsheets (RFC 4180). The byte-order mark makes Excel read the UTF-8 text as such, and a cell a
// spreadsheet would run as a formula is kept as text.
function csvText(rows) {
  const traditional = typeof uiLang !== 'undefined' && uiLang === 'zh-TW' && typeof toTraditional === 'function';
  const cell = value => {
    let text = String(value ?? '');
    if (traditional) text = toTraditional(text);
    if (/^[=+\-@\t\r]/.test(text)) text = "'" + text;
    return /[",\r\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
  };
  return '\ufeff' + rows.map(row => row.map(cell).join(',')).join('\r\n') + '\r\n';
}
// Copy and download buttons with a folded preview. The text is rebuilt on every click and when the
// interface language changes, so it always matches what the page shows.
function textExport(parent, id, makeText, fileName, hint = '通行的中文命盘写法，不含出生日期、时间和备注', makeRows = null) {
  const box = append(parent, 'div', 'text-export'); box.id = id;
  const actions = append(box, 'div', 'text-export-actions');
  const copy = append(actions, 'button', 'tiny-button', '复制成文字'); copy.type = 'button'; copy.id = id + '-copy';
  const save = append(actions, 'button', 'tiny-button', '下载 TXT'); save.type = 'button'; save.id = id + '-download';
  if (makeRows) {
    const sheet = append(actions, 'button', 'tiny-button', '下载 CSV'); sheet.type = 'button'; sheet.id = id + '-csv';
    tip(sheet, '表格文件，可用 Excel、Numbers 或其他电子表格打开');
    sheet.addEventListener('click', () => downloadBlob(new Blob([csvText(makeRows())], {type: 'text/csv;charset=utf-8'}), fileName.replace(/\.txt$/, '.csv')));
  }
  append(actions, 'small', 'muted', hint);
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
    '日主：' + PHASES.split('').filter(e => masters[e].length).map(e => e + ' ' + masters[e].map(asName).join('、')).join('；'),
    '各人（四柱天干地支，不含藏干）：', ...elementRows(g.members.map(m => [asName(m.label), m])));
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
  if (groupDraft.currentLabel === groupLabelShown) groupDraft.currentLabel = groupLabelShown = calT('我');
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
      // The name and its birth time wrap as a pair: the time moves under a name too long to share its line, and only a
      // name wider than the whole line breaks.
      const what = append(row, 'span', 'group-profile-text');
      append(what, 'span', 'user-text', entry.label);
      append(what, 'small', 'muted', String(entry.data.birth_datetime || '').replace('T', ' '));
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
  copyZones(zone, draft.timezone);
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
  if (!groupResult) {emptyPreview(result, run, ['每人四柱与日主', '关系图', '日干十神（行看列）', '两两明细', '选定年份的大运流年'], ['cards', 'table'], Boolean(groupRun)); return;}
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
// A year typed but not entered when 带进 AI 对话 or 生成图片卡片 is clicked: that year is loaded first and the
// button pressed runs again once it is shown.
let askAfterYear = null;
function askWithTypedYear(prefix, shown, change, button = prefix + '-ask-ai') {
  const typed = takeTypedYear(prefix);
  if (typed === null || typed === shown) return false;
  askAfterYear = {prefix, button}; change(typed);
  return true;
}
function askAfterYearLoaded(prefix, ok) {
  if (!askAfterYear || askAfterYear.prefix !== prefix) return;
  const id = askAfterYear.button;
  askAfterYear = null;
  if (ok && active === prefix) {const button = $('#' + id); if (button && !button.disabled) {button.focus(); button.click();}}
}
// 生成图片卡片 next to 带进 AI 对话: the result as a PNG for sharing. Like that button it waits while another year
// or a new comparison loads, and a typed year is loaded first, so the card never shows a year the page has left.
function relationCardButton(after, kind, busy, typedYear) {
  const button = elt('button', 'tiny-button', '生成图片卡片'); button.type = 'button'; button.id = kind + '-card';
  button.disabled = busy;
  after.after(button);
  button.addEventListener('click', () => {if (!typedYear()) openRelationCard(kind);});
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
  relationCardButton(askButton, 'group', groupYearPending || Boolean(groupRun),
    () => askWithTypedYear('group', g.year_view && g.year_view.year, groupYear, 'group-card'));
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
    texts(zodiac, '生肖', ' ', p.zodiac.a || '?', ' / ', p.zodiac.b || '?');
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
  append(result, 'h4', 'subheading', '成员五行');
  elementMatrix(result, g.members.map(m => [m.label, m]), 'group-elements-matrix');
  append(result, 'p', 'field-help', ELEMENT_MATRIX_HELP);
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
// The same window read without moving it, for the image card: drawing it must not change the page.
function luckWindowShown(prefix, year) {
  return luckTimelineYear[prefix] === year && luckTimelineStart[prefix] !== undefined ? luckTimelineStart[prefix]
    : luckWindow(year, luckTimelineStart[prefix]);
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
        if (at.kind === 'unborn') {td.classList.add('tl-empty'); tip(td, '尚未出生'); return;}
        if (at.kind === 'not_started' || at.kind === 'beyond') {
          td.classList.add('tl-empty');
          tip(td, at.kind === 'not_started' ? '未起运' : '已排完');
          if (k === 0 || luckAt(row, year - 1).kind !== at.kind) append(label(td, k, at), 'small', 'tl-god', at.kind === 'not_started' ? '未起运' : '已排完');
          return;
        }
        if (at.kind === 'maybe') {
          td.classList.add('tl-maybe'); append(td, 'small', null, '?');
          tip(td, (at.before ? at.before.pillar : '未起运') + ' / ' + (at.after ? at.after.pillar : '已排完') + ' · 时辰不详，交运年随时辰而定');
          return;
        }
        const p = at.period;
        td.classList.add('tl-' + ELEMENT_CLASS[STEM_ELEMENTS[STEM_ORDER.indexOf(p.pillar[0])]]);
        if (at.first) td.classList.add('tl-change');
        tip(td, p.pillar + (p.ten_god ? ' ' + p.ten_god : '') + ' · ' + p.start_years.join('/') + '–' + p.end_years.join('/'));
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
    tip(yearRow, natalText(n));
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
      n.shensha.forEach(x => {const tag = append(sha, 'span', 'shensha-tag', x.name); tip(tag, shenshaBasis(x));});
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
    tip(edge, p.a_label + ' ↔ ' + p.b_label);
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
  const month = append(nav, 'button', 'tiny-button', '在月历中查看'); month.type = 'button'; month.id = 'today-calendar';
  month.addEventListener('click', () => {
    const typed = date.value, day = /^\d{4}-\d{2}-\d{2}$/.test(typed) && typed >= '1901-01-01' && typed <= '2099-12-31' ? typed : localToday();
    calendarMonth = {year: Number(day.slice(0, 4)), month: Number(day.slice(5, 7))}; calendarSelected = day; calendarFocus = true;
    activateTab(tabs.find(t => t.dataset.tab === 'calendar'));
  });
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
// The 太极 emblem drawn in the theme's gold: the ☯ character comes from whatever font a system has, often a coarse bitmap.
function taijiMark(parent, cls) {
  const box = append(parent, 'div', cls), svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', '0 0 100 100'); svg.setAttribute('aria-hidden', 'true'); svg.setAttribute('class', 'taiji');
  const ring = document.createElementNS(SVG_NS, 'circle'), yin = document.createElementNS(SVG_NS, 'path');
  [['cx', 50], ['cy', 50], ['r', 47], ['fill', 'none'], ['stroke', 'currentColor'], ['stroke-width', 3]].forEach(([k, v]) => ring.setAttribute(k, v));
  // One half and its bulge, with the two eyes as holes in the even-odd fill.
  yin.setAttribute('fill', 'currentColor'); yin.setAttribute('fill-rule', 'evenodd');
  yin.setAttribute('d', 'M50 3A47 47 0 0 1 50 97A23.5 23.5 0 0 1 50 50A23.5 23.5 0 0 0 50 3ZM56 26.5a6 6 0 1 0-12 0a6 6 0 1 0 12 0ZM56 73.5a6 6 0 1 0-12 0a6 6 0 1 0 12 0Z');
  svg.append(ring, yin); box.append(svg);
  return box;
}
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
// Labels listed in a sentence: each label and each 、 is its own text node, so every label translates whole and the
// separator reads ", " in English.
function enumList(parent, labels) {
  const list = append(parent, 'span', 'enum-list');
  labels.forEach((x, i) => {if (i) list.append('、'); append(list, 'span', null, x);});
  return list;
}
// A span of minutes as days, hours and minutes (minutes and seconds under an hour), numbers apart from their units.
function durationText(parent, minutes) {
  const seconds = Math.round(Math.abs(minutes) * 60), total = seconds >= 3600 ? Math.round(seconds / 60) * 60 : seconds;
  const days = Math.floor(total / 86400), hours = Math.floor(total % 86400 / 3600);
  const mins = Math.floor(total % 3600 / 60), secs = total % 60, parts = [];
  if (days) parts.push([days, ' 天']);
  if (hours) parts.push([hours, ' 小时']);
  if (mins || (!days && !hours && !secs)) parts.push([mins, ' 分']);
  if (secs && !days && !hours) parts.push([secs, ' 秒']);
  parts.forEach(([n, unit], i) => {if (i) parent.append(' '); countText(parent, n, unit);});
  return parent;
}
// A count and its unit. One day and one hour are a single text, so English reads "1 day", not "1 days".
const WHOLE_COUNTS = [' 天', ' 小时', ' 岁', ' 个月'];  // '1 天' and the like have whole-string translations (1 day, 1 yr)
function countText(parent, n, unit) {return n === 1 && WHOLE_COUNTS.includes(unit) ? texts(parent, '1' + unit) : texts(parent, n, unit);}
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
      loadingGhost(result, 'cards');
      return;
    }
    if (!pickData) {append(result, 'p', 'inline-msg', '所选时刻算不出来：' + pickError); return;}
    t = pickData; skipped = pickBirthSkipped;
  } else {
    if (todayKey !== JSON.stringify(todayRequest())) {
      ensureToday(() => {if (active === 'today') render();});
      if (!todayData) {append(result, 'p', 'field-help', '正在计算今天的四柱、节气和月相…'); loadingGhost(result, 'cards'); return;}
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
  // The day's festivals, and the fu period or nine it is in with the day of it; each tag takes the focus and shows the
  // rule that places it (a festival's is its lunar date).
  (t.festivals || []).forEach(m => {
    const tag = append(facts, 'span', 'today-mark today-mark-' + m.kind); tag.tabIndex = 0;
    texts(tag, m.name);
    if (m.day !== undefined) append(tag, 'span', null, (calLang() === 'en' ? ', ' : ' ') + seasonDayText(m)).dataset.noI18n = '';
    const rule = m.kind === 'festival' && m.name !== '除夕' ? calT('农历') + ' ' + lunarDateText(t.lunar) : calT(m.rule);
    tip(tag, rule + (m.caution ? calT('；') + calT(m.caution) : ''));
  });
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
    const table = append(wrap, 'table', 'data-table today-table'); table.id = 'today-table';
    const head = append(append(table, 'thead'), 'tr');
    ['', todayPick ? '当日' : '今日', '天干十神', '地支与本命'].forEach(text => {append(head, 'th', null, text).scope = 'col';});
    const body = append(table, 'tbody');
    me.today_against_natal.forEach(row => {
      const tr = append(body, 'tr');
      append(tr, 'th', null, nameMap[row.pillar_of]);
      const cell = append(tr, 'td', 'pillar-cell');
      append(cell, 'b', stemClass(row.pillar[0]), row.pillar[0]); append(cell, 'b', branchClass(row.pillar[1]), row.pillar[1]);
      stackLabel(append(tr, 'td', 'today-god dy-short'), '天干十神').append(row.stem_ten_god);
      const rel = stackLabel(append(tr, 'td', 'today-rel'), '地支与本命');
      if (!row.branch_relations.length) append(rel, 'span', 'muted', '—');
      row.branch_relations.forEach(x => {
        const chip = append(rel, 'span', 'relation-chip rel-' + {'六冲': 'clash', '六合': 'harmony', '同支': 'same'}[x.type]);
        texts(chip, x.type, ' · ', x.with, ' ' + x.natal_branch);
      });
    });
    stackTable(table);
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
// Month and hour stems follow from the year and day stems (五虎遁, 五鼠遁), so only those twelve are offered.
const MONTH_JIE = ['立春', '惊蛰', '清明', '立夏', '芒种', '小暑', '立秋', '白露', '寒露', '立冬', '大雪', '小寒'];
const HOUR_SPANS = ['23–01', '01–03', '03–05', '05–07', '07–09', '09–11', '11–13', '13–15', '15–17', '17–19', '19–21', '21–23'];
const monthPillars = year => [...'寅卯辰巳午未申酉戌亥子丑'].map((b, k) => STEM_ORDER[(2 + 2 * (STEM_ORDER.indexOf(year[0]) % 5) + k) % 10] + b);
const hourPillars = day => [...BRANCH_ORDER].map((b, k) => STEM_ORDER[(2 * (STEM_ORDER.indexOf(day[0]) % 5) + k) % 10] + b);
// The sixty pairs in their six decades (甲子旬 …), so a long list is easier to scan.
function jiaziOptions(select) {
  for (let x = 0; x < 60; x += 10) {
    const group = append(select, 'optgroup'); group.label = JIAZI[x] + '旬';
    JIAZI.slice(x, x + 10).forEach(text => {const op = append(group, 'option', null, text); op.value = text;});
  }
}
function pillarGlyph(parent, text) {
  const glyph = append(parent, 'b', 'ps-glyph'); glyph.dataset.noI18n = '';
  append(glyph, 'span', stemClass(text[0]), text[0]); append(glyph, 'span', branchClass(text[1]), text[1]);
  return glyph;
}
// Whole years of age on a date, for a birth at the start of a match (null when the match is still to come).
function ageOn(birth, today) {
  if (birth > today) return null;
  const [by, bm, bd] = birth.split('-').map(Number), [ty, tm, td] = today.split('-').map(Number);
  return ty - by - (tm < bm || (tm === bm && td < bd) ? 1 : 0);
}
// A match is cast under the time zone and time basis the search used, even if the form was changed since.
function restoreSearchBasis(r) {
  const zone = $('#timezone'), mode = $('#time_mode'), longitude = r.rules.longitude_east_degrees;
  const changed = zone.value !== r.timezone || mode.value !== r.rules.time_mode || (longitude != null && Number($('#longitude').value) !== longitude);
  if (!changed) return;
  ensureZone(zone, r.timezone);
  zone.value = r.timezone; mode.value = r.rules.time_mode;
  if (longitude != null) $('#longitude').value = String(longitude);
  $('#birth_city').value = '';
  updateGeoControls();
}
function renderPillarSearch() {
  title(result, '四柱反查出生时间', '给出四柱，列出 1901–2099 年间所有对得上的出生时段');
  append(result, 'p', 'info-inline', '时区、时制和经度沿用出生资料；边界用和排盘相同的计算逐秒校准。');
  // Pillars filled in from the chart follow a newly cast chart until they are changed by hand.
  const p = current ? current.bazi.pillars : null;
  const chartKey = p ? [p.year.text, p.month.text, p.day.text, currentHourUnknown ? '' : p.hour.text].join(' ') : '';
  if (!pillarDraft || (pillarDraft.fromChart !== undefined && pillarDraft.fromChart !== chartKey)) {
    pillarDraft = {year: p ? p.year.text : JIAZI[0], month: p ? p.month.text : JIAZI[2], day: p ? p.day.text : JIAZI[0],
      hour: p && !currentHourUnknown ? p.hour.text : '', start_year: 1901, end_year: 2099, late_zi_day_rollover: readInput().late_zi_day_rollover,
      fromChart: chartKey};
  }
  const builder = append(result, 'div', 'ps-builder');
  const pickers = {}, previews = {};
  const column = (key, label) => {
    const col = append(builder, 'div', 'ps-col');
    const select = append(append(col, 'label', 'ps-label', label), 'select'); select.id = 'pillar-' + key;
    pickers[key] = select;
    previews[key] = append(col, 'div', 'ps-preview');
    select.setAttribute('aria-describedby', 'pillar-' + key + '-hint');
    return select;
  };
  jiaziOptions(column('year', '年柱'));
  column('month', '月柱');
  jiaziOptions(column('day', '日柱'));
  column('hour', '时柱（可不选）');
  // The month list follows the year stem and the hour list the day stem; a branch already chosen is kept.
  const fill = (select, pillars, keep, blank) => {
    const branch = keep ? keep[1] : null;
    select.replaceChildren();
    if (blank) {const op = append(select, 'option', null, '不限'); op.value = '';}
    pillars.forEach(text => {const op = append(select, 'option', null, text); op.value = text;});
    select.value = keep === '' && blank ? '' : (pillars.find(p => p[1] === branch) || pillars[0]);
  };
  // The large glyph repeats the picked value, so only the line saying where the pillar changes is read out.
  const preview = key => {
    const box = previews[key], value = pickers[key].value;
    box.replaceChildren();
    let hint;
    if (!value) hint = append(box, 'span', 'ps-any', '不限');
    else {
      pillarGlyph(box, value).setAttribute('aria-hidden', 'true');
      if (key === 'month') {
        const k = '寅卯辰巳午未申酉戌亥子丑'.indexOf(value[1]);
        hint = append(box, 'small', null, termText(MONTH_JIE[k], true) + ' – ' + termText(MONTH_JIE[(k + 1) % 12], true));
        hint.dataset.noI18n = '';
      }
      // Under the 00:00 day change the 子 hour of a day is its first and its last hour, not one span from the evening before.
      if (key === 'hour') hint = append(box, 'small', null, value[1] === '子' && !(pickers.late && pickers.late.checked) ? '00–01 · 23–24' : HOUR_SPANS[BRANCH_ORDER.indexOf(value[1])]);
      if (key === 'year') hint = append(box, 'small', null, '立春换年');
      if (key === 'day') hint = append(box, 'small', null, pickers.late && pickers.late.checked ? '23:00 换日' : '00:00 换日');
    }
    hint.id = 'pillar-' + key + '-hint';
  };
  pickers.year.value = pillarDraft.year; pickers.day.value = pillarDraft.day;
  fill(pickers.month, monthPillars(pillarDraft.year), pillarDraft.month, false);
  fill(pickers.hour, hourPillars(pillarDraft.day), pillarDraft.hour, true);
  pickers.year.addEventListener('change', () => {fill(pickers.month, monthPillars(pickers.year.value), pickers.month.value, false); preview('year'); preview('month');});
  pickers.day.addEventListener('change', () => {fill(pickers.hour, hourPillars(pickers.day.value), pickers.hour.value, true); preview('day'); preview('hour');});
  pickers.month.addEventListener('change', () => preview('month'));
  pickers.hour.addEventListener('change', () => preview('hour'));
  // Choices not yet searched survive a re-render (a language switch, another tab and back).
  const keep = () => {
    pillarDraft = {year: pickers.year.value, month: pickers.month.value, day: pickers.day.value, hour: pickers.hour.value,
      start_year: Number(from.value) || pillarDraft.start_year, end_year: Number(to.value) || pillarDraft.end_year, late_zi_day_rollover: late.checked};
  };
  append(result, 'p', 'field-help', '月柱天干由年干定（五虎遁），时柱天干由日干定（五鼠遁），所以月柱、时柱只列能对上的十二个。');
  const options = append(result, 'div', 'inline-control');
  const from = createInput('起始年', 'number', String(pillarDraft.start_year), options); from.id = 'pillar-from'; from.min = '1901'; from.max = '2099';
  const to = createInput('结束年', 'number', String(pillarDraft.end_year), options); to.id = 'pillar-to'; to.min = '1901'; to.max = '2099';
  const lateLine = append(options, 'label', 'check-line');
  const late = append(lateLine, 'input'); late.type = 'checkbox'; late.id = 'pillar-late-zi'; late.checked = pillarDraft.late_zi_day_rollover;
  lateLine.append(' 23:00 换日（早晚子时）');
  pickers.late = late;
  late.addEventListener('change', () => {preview('day'); preview('hour');});
  ['year', 'month', 'day', 'hour'].forEach(preview);
  [pickers.year, pickers.month, pickers.day, pickers.hour, late].forEach(el => el.addEventListener('change', keep));
  [from, to].forEach(el => el.addEventListener('input', keep));
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
    try {pillarResult = await postJSON('/api/pillars-to-dates', body); if (active === 'pillar-search') {render(); announce('四柱反查完成：' + pillarResult.count + ' 个时段');}}
    catch (e) {pillarResult = null; message.className = 'inline-msg'; message.textContent = '反查失败：' + e.message;}
    finally {run.disabled = false;}
  });
  if (!pillarResult) {emptyPreview(result, run, ['对得上的年份分布', '每个时段的起止、时长与农历', '用这个时间排盘'], ['table']); return;}
  const r = pillarResult;
  r.impossible_combination.forEach(x => append(result, 'p', 'inline-msg', x));
  meta(result, [`${r.pillars.year} ${r.pillars.month} ${r.pillars.day} ${r.pillars.hour || ''}`.trim(), `${r.count} 个时段`,
    `${r.range.start_year}–${r.range.end_year}`, `换日 ${r.rules.day_boundary}`, r.timezone]);
  if (!r.count && !r.impossible_combination.length) append(result, 'p', 'info-inline', '这段年份里没有对得上的时间。可以放宽年份，或切换换日规则再试。');
  if (r.count) {
    const today = localToday(), span = Math.max(1, r.range.end_year - r.range.start_year + 1);
    const at = date => {const [y, m, d] = date.split('-').map(Number); return Math.min(1, (y - r.range.start_year + ((m - 1) * 30.6 + d) / 366) / span);};
    // The searched years as one axis: the year pillar comes round every sixty years, so matches gather in a few years.
    const axis = append(result, 'div', 'ps-axis'); axis.id = 'pillar-axis';
    axis.setAttribute('role', 'group'); axis.setAttribute('aria-label', '对得上的年份');
    const track = append(axis, 'div', 'ps-track');
    const thisYear = Number(today.slice(0, 4));
    if (thisYear >= r.range.start_year && thisYear <= r.range.end_year) {
      const now = append(track, 'span', 'ps-now'); now.style.left = 100 * at(today) + '%';
      now.setAttribute('aria-hidden', 'true');
      append(now, 'small', null, '今天');
    }
    const years = new Map();
    r.matches.forEach((m, i) => {const y = m.start.slice(0, 4); if (!years.has(y)) years.set(y, []); years.get(y).push(i);});
    years.forEach((list, y) => {
      // A mark at either end of the range is pinned inside the axis instead of centred on its year.
      const left = 100 * at(r.matches[list[0]].start.slice(0, 10));
      const mark = append(track, 'a', 'ps-mark' + (left < 6 ? ' is-first' : left > 94 ? ' is-last' : '')); mark.href = '#pillar-match-' + list[0];
      mark.style.left = left + '%';
      texts(mark, y); if (list.length > 1) append(mark, 'small', null, '×' + list.length);
      mark.dataset.noI18n = '';
      mark.setAttribute('aria-label', y + ' · ' + (list.length === 1 ? calT('1 个时段') : list.length + ' ' + calT('个时段')));
    });
    const ends = append(axis, 'div', 'ps-ends');
    append(ends, 'span', null, String(r.range.start_year)); append(ends, 'span', null, String(r.range.end_year));
    append(result, 'p', 'field-help', '每个时段含起点、不含止点；止点那一刻已换成别的柱。');
    const list = append(result, 'ol', 'ps-cards'); list.id = 'pillar-matches';
    r.matches.forEach((m, i) => {
      const card = append(list, 'li', 'ps-card'); card.id = 'pillar-match-' + i; card.tabIndex = -1;
      const head = append(card, 'div', 'ps-card-head');
      texts(append(head, 'span', 'ps-index'), i + 1);
      const day = m.start.slice(0, 10), endDay = m.end_exclusive.slice(0, 10);
      append(head, 'b', 'ps-date', day).id = 'pillar-date-' + i;
      append(head, 'span', 'ps-weekday', WEEKDAY_NAMES[weekdayOf(day)]);
      const age = ageOn(day, today);
      if (age === null) append(head, 'span', 'ps-age is-future', '未来日期');
      else texts(append(head, 'span', 'ps-age'), age, ' ', '周岁');
      // Start and end each keep their own UTC offset when a daylight-saving switch falls between them, and the
      // line breaks at the dash rather than running out of the card when the end is on another date.
      const when = append(card, 'p', 'ps-when'); when.id = 'pillar-when-' + i;
      const span = append(when, 'span', 'ps-span');
      const startZone = m.start.slice(19), endZone = m.end_exclusive.slice(19);
      append(span, 'span', 'ps-from', m.start.slice(11, 19));
      if (startZone !== endZone) {span.append(' '); append(span, 'small', 'ps-zone', 'UTC' + startZone);}
      span.append(' – ');
      append(span, 'span', 'ps-to', endDay === day ? m.end_exclusive.slice(11, 19) : m.end_exclusive.slice(0, 19).replace('T', ' '));
      span.append(' '); append(span, 'small', 'ps-zone', 'UTC' + endZone);
      when.dataset.noI18n = '';
      const facts = append(card, 'div', 'ps-facts');
      const fact = (label, ...parts) => texts(append(append(facts, 'p'), 'span', 'muted', label).parentElement, ' ', ...parts);
      durationText(fact('时长'), m.duration_minutes);
      const lunar = append(fact('农历'), 'span', null, lunarYearPillar(m.lunar_date.year) + ' · ' + lunarDateText(m.lunar_date));
      lunar.dataset.noI18n = '';
      if (m.effective_start) fact(r.rules.time_mode === 'apparent_solar' ? '真太阳时' : '平太阳时', m.effective_start.slice(0, 19).replace('T', ' '));
      if (!m.suggested_local) {append(card, 'p', 'field-help', '整段落在夏令时重复或跳过的钟点，请手动填写'); return;}
      const use = append(card, 'button', 'tiny-button', '用这个时间排盘'); use.type = 'button'; use.id = 'pillar-use-' + i;
      use.setAttribute('aria-describedby', 'pillar-date-' + i + ' pillar-when-' + i);
      use.addEventListener('click', () => {
        // The search's own time zone and time basis go back with the time, in case the form changed since.
        $('#birth_datetime').value = m.suggested_local; $('#late_zi_day_rollover').checked = r.rules.day_boundary === '23:00';
        restoreSearchBasis(r);
        $('#hour_unknown').checked = !r.pillars.hour; updateHourUnknown(); updateStaleBirthNotice();
        activateTab(tabs.find(t => t.dataset.tab === 'bazi'));
        form.requestSubmit();
      });
    });
    axis.addEventListener('click', e => {
      const mark = e.target.closest('.ps-mark'); if (!mark) return;
      e.preventDefault(); const card = $(mark.getAttribute('href')); card.scrollIntoView({block: 'nearest'}); card.focus({preventScroll: true});
    });
    if (r.truncated) note(result, '结果较多，只列出前 40 个时段。');
  }
  r.limitations.forEach(x => note(result, x));
}

// Paste a chart from other software and compare it with XuanShu field by field.
let importDraft = '', importResult = null;
// What the last check was run on: the birth sent (applied back with a chosen hour) and whether the hour was a placeholder.
let importBirth = null, importHourUnknown = false, importHourPick = null, importRecheck = false, importFocusAfter = false;
// The birth data was edited after the check: its results, and the rule or hour it offers, belong to the old data.
function importStale() {return !!importResult && !!importBirth && JSON.stringify(readInput()) !== JSON.stringify(importBirth);}
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
    const birth = readInput(), hourUnknown = $('#hour_unknown').checked;
    try {importResult = await postJSON('/api/chart-import-check', {birth, text: area.value}); importBirth = birth; importHourUnknown = hourUnknown; importHourPick = null; render();
      announce(`核对完成：${importResult.summary.matched} 项一致，${importResult.summary.mismatched} 项不同`);
      // After a rule or an hour was applied the button pressed is gone; the new result takes the focus.
      if (importFocusAfter) {
        importFocusAfter = false;
        const target = document.getElementById('import-verdict') || document.querySelector('#import-hours .is-picked') || document.getElementById('import-check-run');
        if (target) target.focus();
      }}
    catch (e) {importResult = null; message.className = 'inline-msg'; message.textContent = '核对失败：' + e.message;}
    finally {run.disabled = false;}
  });
  // After a rule or an hour is applied, the check runs again on the new chart by itself.
  if (importRecheck && !importResult && importDraft.trim() && current && JSON.stringify(readInput()) === JSON.stringify(currentInput)) {
    importRecheck = false;
    setTimeout(() => {if (active === 'import-check' && !run.disabled) run.click();});
  }
  if (!importResult) {emptyPreview(result, run, ['逐项比对', '能让两边一致的规则', '对得上的出生时辰'], ['table']); return;}
  const r = importResult;
  if (!r.recognized_count) {
    append(result, 'p', 'inline-msg', '没有识别到可以比对的字段。支持的写法：');
    const list = append(result, 'ul', 'plain-list'); r.accepted_formats.forEach(x => append(list, 'li', null, x));
    return;
  }
  meta(result, [`已识别字段 ${r.recognized_count}`, `一致 ${r.summary.matched}`, `不同 ${r.summary.mismatched}`]);
  const stale = append(result, 'p', 'info-inline', '出生资料在这次核对之后改过：下面的结果对应改动前的资料，请重新核对。');
  stale.id = 'import-stale'; stale.hidden = !importStale();
  if (r.reproducing_variants.length) {
    const box = append(result, 'div', 'import-verdict ok'); box.id = 'import-verdict'; box.tabIndex = -1;
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
      apply.addEventListener('click', () => {
        if (importStale()) {render(); return;}
        setInput(v.settings); importResult = null; importRecheck = true; importFocusAfter = true; form.requestSubmit(); setFeedback('已套用：' + v.label);
      });
    });
  } else if (!r.summary.mismatched) {
    const box = append(result, 'div', 'import-verdict ok', '识别到的字段全部一致。'); box.id = 'import-verdict'; box.tabIndex = -1;
  }
  if (r.hour_alternatives && r.hour_alternatives.length) renderImportHours(r);
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
    near.forEach(v => {const tr = append(b2, 'tr'); append(tr, 'td', null, v.label); enumList(append(tr, 'td'), v.mismatched_fields);});
  }
  r.limitations.forEach(x => note(result, x));
}
// The same day recomputed once per double hour: a row of hours with how many recognized fields still differ.
const HOUR_SLOT_LABELS = ['早子', ...'丑寅卯辰巳午未申酉戌亥', '晚子'];  // the server's day-hour labels, in the order of LUNAR_HOURS
const hourSlotName = h => {const i = HOUR_SLOT_LABELS.indexOf(h.label); return i < 0 ? h.label : LUNAR_HOURS[i + 1][1].split(' ')[0];};
function renderImportHours(r) {
  const hours = r.hour_alternatives, best = Math.min(...hours.map(h => h.mismatched));
  const nameOf = hourSlotName;
  const mode = importBirth ? importBirth.time_mode : 'clock', solar = mode === 'mean_solar' || mode === 'apparent_solar';
  append(result, 'h4', 'subheading', '换个时辰对照');
  const help = append(result, 'p', 'field-help', '同一天、沿用当前规则，把出生时间换到每个时辰的中间各算一遍（出生时间所在的时辰用出生时间本身），看粘贴的命盘和哪个时辰对得上。格子里的数字是仍不一致的项数，星曜亮度不计。');
  if (solar) help.append(' ', '格子里写的是钟表时间，按所选太阳时换算后落在该时辰里。');
  const matching = hours.filter(h => !h.mismatched), closest = matching.length ? [] : hours.filter(h => h.mismatched === best);
  const verdict = append(result, 'p', 'ic-verdict' + (matching.length ? ' is-ok' : ''));
  if (matching.length) {texts(verdict, '对得上的时辰：'); enumList(verdict, matching.map(nameOf));}
  else {
    texts(verdict, '没有哪个时辰能让识别到的字段全部一致。', ' ', '最接近：');
    enumList(verdict, closest.map(nameOf)); texts(verdict, ' · ', String(best), ' 项不同');
  }
  if (r.missing_hours && r.missing_hours.length) {
    const gone = append(result, 'p', 'field-help ic-missing');
    texts(gone, '这天的夏令时切换跳过或重复了一段钟表时间，没有能唯一确定的出生时间落在这些时辰里，未列出：');
    enumList(gone, r.missing_hours.map(label => nameOf({label})));
  }
  if (!hours.some(h => h.label === importHourPick)) importHourPick = (matching[0] || closest[0]).label;
  const strip = append(result, 'div', 'ic-hours'); strip.id = 'import-hours';
  strip.setAttribute('role', 'group'); strip.setAttribute('aria-label', '各时辰的对照结果');
  const detail = elt('div', 'ic-detail'); detail.id = 'import-hour-detail';
  const baseDate = importBirth ? importBirth.birth_datetime.slice(0, 10) : '';
  const clockOf = h => (h.birth_datetime.slice(0, 10) === baseDate ? '' : h.birth_datetime.slice(5, 10).replace('-', '/') + ' ') + h.birth_datetime.slice(11, 16);
  const cells = hours.map((h, i) => {
    const near = closest.includes(h);
    const cell = append(strip, 'button', 'ic-hour' + (!h.mismatched ? ' is-match' : near ? ' is-best' : '') + (h.current ? ' is-current' : ''));
    cell.type = 'button'; cell.id = 'import-hour-' + i;
    append(cell, 'span', 'ic-name', nameOf(h));
    const gz = append(cell, 'b', 'ic-gz'); gz.dataset.noI18n = '';
    append(gz, 'span', stemClass(h.hour_pillar[0]), h.hour_pillar[0]); append(gz, 'span', branchClass(h.hour_pillar[1]), h.hour_pillar[1]);
    append(cell, 'small', 'ic-clock', clockOf(h));
    const count = append(cell, 'small', 'ic-count');
    if (h.mismatched) texts(count, String(h.mismatched), ' 项不同'); else count.textContent = '全部一致';
    if (near) append(cell, 'small', 'ic-tag ic-near', '最接近');
    if (h.current) append(cell, 'small', 'ic-tag', importHourUnknown ? '占位时间' : '当前时间');
    cell.addEventListener('click', () => {importHourPick = h.label; pick();});
    return cell;
  });
  function pick() {
    const h = hours.find(x => x.label === importHourPick);
    cells.forEach((cell, i) => {const on = hours[i] === h; cell.classList.toggle('is-picked', on); cell.setAttribute('aria-pressed', String(on));});
    detail.replaceChildren();
    const head = append(detail, 'p', 'ic-detail-head');
    append(head, 'b', null, nameOf(h));
    texts(append(head, 'span'), solar ? '钟表时间' : '出生时间', ' ', h.birth_datetime.replace('T', ' '));
    if (solar && h.effective_reading) texts(append(head, 'span'), mode === 'mean_solar' ? '平太阳时' : '真太阳时', ' ', h.effective_reading.slice(11, 16));
    const pillars = append(head, 'span'); texts(pillars, '时柱', ' ');
    const hp = append(pillars, 'b'); hp.dataset.noI18n = ''; hp.textContent = h.hour_pillar;
    texts(pillars, ' · ', '日柱', ' '); const dp = append(pillars, 'b'); dp.dataset.noI18n = ''; dp.textContent = h.day_pillar;
    if (h.mismatched) {const diff = append(detail, 'p', 'ic-detail-diff'); texts(diff, '仍不一致：'); enumList(diff, h.mismatched_fields);}
    else append(detail, 'p', 'ic-detail-ok', '识别到的字段全部一致（星曜亮度不计）。');
    if (h.current && !importHourUnknown) return;
    const use = append(detail, 'button', 'tiny-button', '用这个时间排盘'); use.type = 'button'; use.id = 'import-hour-use';
    use.addEventListener('click', () => {
      if (importStale()) {render(); return;}
      setInput({...importBirth, birth_datetime: h.birth_datetime});
      $('#hour_unknown').checked = false; updateHourUnknown(); updateBirthSummary(); updateStaleBirthNotice();
      importResult = null; importRecheck = true; importFocusAfter = true; form.requestSubmit();
      setFeedback('已改用对照里选的时辰排盘，并重新核对。');
    });
  }
  pick();
  // Filled before it is shown, so only later picks are read out, not the first one alongside the check result.
  result.append(detail); detail.setAttribute('aria-live', 'polite');
}
// Lunar to Gregorian: the date found is picked on the month calendar above.
function renderLunarInverseSection() {
  append(result, 'h4', 'subheading', '农历 → 公历反查（支持闰月）');
  // Until the person edits it, the default year is this lunar year as the calendar engine gives it.
  ensureTodayLunarYear();
  if (!lunarInverseDraft || (lunarInverseDraft.guessed && todayLunarYear !== null)) {
    lunarInverseDraft = {lunar_year: defaultLunarYear(), lunar_month: 1, lunar_day: 1, is_leap_month: false, guessed: todayLunarYear === null};
  }
  const row = append(result, 'div', 'inline-control lunar-inverse');
  const y = createInput('农历年份', 'number', String(lunarInverseDraft.lunar_year), row); y.min = '1901'; y.max = '2099'; y.id = 'lunar-inverse-year';
  const m = append(append(row, 'label', null, '农历月份'), 'select'); m.id = 'lunar-inverse-month';
  fillSelect(m, LUNAR_MONTHS.map((name, i) => [String(i + 1), name])); m.value = String(lunarInverseDraft.lunar_month);
  const d = append(append(row, 'label', null, '农历日期'), 'select'); d.id = 'lunar-inverse-day';
  fillSelect(d, LUNAR_DAYS.map((name, i) => [String(i + 1), name])); d.value = String(lunarInverseDraft.lunar_day);
  const check = append(row, 'label', 'check-line');
  const leap = append(check, 'input'); leap.type = 'checkbox'; leap.id = 'lunar-inverse-leap'; leap.checked = lunarInverseDraft.is_leap_month;
  check.append(' 闰月');
  const go = append(row, 'button', null, '换算公历'); go.type = 'button'; go.id = 'lunar-inverse-run';
  const error = append(result, 'p', 'inline-msg', lunarInverseError);
  // Kept as typed, so a month calendar that finishes loading meanwhile does not reset the fields.
  const keep = () => {lunarInverseDraft = {lunar_year: Number(y.value) || lunarInverseDraft.lunar_year, lunar_month: Number(m.value), lunar_day: Number(d.value), is_leap_month: leap.checked};};
  [y, m, d, leap].forEach(control => control.addEventListener(control === y ? 'input' : 'change', keep));
  go.addEventListener('click', async () => {
    keep(); lunarInverseDraft.lunar_year = Number(y.value);
    go.disabled = true; error.textContent = ''; lunarInverseError = '';
    try {lunarInverseResult = await postJSON('/api/lunar-to-gregorian', lunarInverseDraft); showCalendarDay(lunarInverseResult.gregorian_date);}
    catch (e) {lunarInverseResult = null; lunarInverseError = '换算失败：' + e.message; render();}
    finally {go.disabled = false;}
  });
  if (!lunarInverseResult) return;
  const found = lunarInverseResult.gregorian_date, lunar = lunarInverseResult.lunar_date;
  const box = append(result, 'div', 'feature-note lunar-inverse-result'); box.id = 'lunar-inverse-result';
  texts(box, '农历', ' ');
  append(box, 'span', null, lunarYearPillar(lunar.year) + ' · ' + lunarDateText(lunar)).dataset.noI18n = '';
  box.append(' → ');
  texts(box, '公历', ' ' + found + ' ', WEEKDAY_NAMES[(new Date(found + 'T00:00:00Z').getUTCDay() + 6) % 7]);
  if (calendarSelected === found) {
    box.append(' ');
    const show = append(box, 'button', 'tiny-button', '在月历中查看'); show.type = 'button'; show.id = 'lunar-inverse-show';
    show.addEventListener('click', () => {const day = $('#calendar-day-' + found); if (day) {day.focus(); day.scrollIntoView({block: 'center'});}});
  }
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
  lines.push('', '【五行】四柱天干地支，不含藏干', ...elementRows([['A', r.person_a], ['B', r.person_b]]));
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
  copyZones(zone, pairDraft.timezone);
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
  if (!pairResult) {
    emptyPreview(result, run, ['两人日干互看的十神', '生肖', '四柱同位地支', '地支两两关系', '两人五行', '选定年份的大运流年', '紫微宫位叠盘'], ['table'], pairRunning);
    return;
  }
  if (pairKey !== JSON.stringify(pairBody())) append(result, 'p', 'feature-note', 'A 或 B 的资料已改变，下面仍是上一次的结果；点「比较两人命盘」更新。');
  const r = pairResult;
  meta(result, [`A 日主 ${r.person_a.day_master || '?'}`, `B 日主 ${r.person_b.day_master || '?'}`, '不提供匹配分数']);
  // The day-stem ten god both ways, the five combination and the zodiac pair, as on the group page.
  const facts = append(result, 'div', 'meta-tags pair-facts'); facts.id = 'pair-facts';
  texts(append(facts, 'span'), 'A → B', '：', r.day_stems.a_sees_b || '?');
  texts(append(facts, 'span'), 'B → A', '：', r.day_stems.b_sees_a || '?');
  if (r.day_stems.combination) append(facts, 'span', 'relation-chip link-combine', r.day_stems.combination);
  const zodiac = append(facts, 'span');
  texts(zodiac, '生肖', ' ', r.zodiac.a || '?', ' / ', r.zodiac.b || '?');
  r.zodiac.labels.forEach(x => zodiac.append(' · ', x));
  const askButton = chatAskButton('pair-ask-ai', 'pair', '把两人的出生资料放进对话输入框，你确认后再发送；发送前需在对话设置里勾选已获对方同意。',
    'AI 对话尚未启用，配置语言模型后可以把两人带进对话。', pairYearPending || pairRunning);
  askButton.addEventListener('click', () => {
    if (askWithTypedYear('pair', r.year_view && r.year_view.year, pairYear)) return;
    const {text: draft, others} = pairChatDraft(r, JSON.parse(pairKey || '{}'));
    pairChatBlock = sendDraftToChat(draft, others, pairChatBlock);
  });
  relationCardButton(askButton, 'pair', pairYearPending || pairRunning,
    () => askWithTypedYear('pair', r.year_view && r.year_view.year, pairYear, 'pair-card'));
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
  append(result, 'h4', 'subheading', '两人五行');
  elementMatrix(result, [['A', r.person_a], ['B', r.person_b]], 'pair-elements');
  append(result, 'p', 'field-help', ELEMENT_MATRIX_HELP);
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
// One named lunar year at a time: step through the years, see where that year's stem puts 禄权科忌 among the natal
// palaces beside the birth-year four, and open the full year layer on the Zi Wei board.
let annualFocus = null;  // the control to focus again once the year asked for has drawn
// A badge on this page reads by its full name: the glyph alone says 忌 or 年禄 to a screen reader.
// Where the name is written out beside the badge, the glyph is only drawn.
function quietBadge(parent, type, year) {
  const badge = huaBadge(parent, type, year ? 'year' : undefined);
  tip(badge, (year ? '该年' : '生年') + type); badge.setAttribute('aria-hidden', 'true');
  return badge;
}
function annualBadge(parent, type, year) {
  const badge = quietBadge(parent, type, year);
  append(parent, 'span', 'visually-hidden', badge.getAttribute('data-tip'));
  return badge;
}
function renderAnnual() {
  title(result, '指定农历年干四化', '与本命四化分开显示 · 仅为星曜位置叠加');
  if (!current) {append(result, 'p', 'info-inline', '请先生成出生盘。'); return;}
  ensureTodayLunarYear();
  const row = append(result, 'div', 'inline-control ay-control');
  const prev = append(row, 'button', 'tiny-button', '← 前一年'); prev.type = 'button'; prev.id = 'annual-prev';
  const year = createInput('目标农历纪年（1901–2099）', 'number', String(annualDraft ?? defaultLunarYear()), row);
  year.min = '1901'; year.max = '2099'; year.id = 'annual-year'; keepTyped(year);
  const next = append(row, 'button', 'tiny-button', '后一年 →'); next.type = 'button'; next.id = 'annual-next';
  const button = append(row, 'button', null, '查询年干四化'); button.type = 'button'; button.id = 'annual-run';
  const nowYear = todayLunarYear;
  let now = null;
  if (nowYear !== null && annualResult && annualResult.lunar_year !== nowYear) {
    now = append(row, 'button', 'tiny-button', '回到今年'); now.type = 'button'; now.id = 'annual-now';
  }
  const error = append(result, 'p', 'inline-msg'); error.setAttribute('role', 'alert');
  const typed = () => {const y = numericEntry(year); return Number.isInteger(y) && y >= 1901 && y <= 2099 ? y : null;};
  // A year typed outside 1901–2099 is refused by the arrows too, rather than stepping from the year shown.
  const step = delta => year.value.trim() !== '' && typed() === null ? null : base() + delta;
  const base = () => typed() ?? (annualResult ? annualResult.lunar_year : defaultLunarYear());
  const edges = () => {prev.disabled = base() <= 1901; next.disabled = base() >= 2099;};
  edges(); year.addEventListener('input', edges);
  const run = async (y, focusId) => {
    if (y === null) {error.textContent = '农历纪年须是 1901–2099 之间的整数。'; return;}
    annualDraft = y; year.value = String(y); delete typedValues[year.id]; error.textContent = '';
    [prev, next, button, now].forEach(b => {if (b) b.disabled = true;});
    try {
      // The chart shown, not the form: the board below is drawn from it.
      const data = await postForChart('/api/annual', {birth: currentInput, lunar_year: y});
      // A reply that lands after the reader moved on to another page or control draws quietly and takes no focus.
      if (data !== STALE) {
        annualResult = data;
        if (active === 'annual') {
          const at = document.activeElement;
          annualFocus = focusId && (!at || at === document.body || result.contains(at)) ? focusId : null;
          render(); announce(data.lunar_year + ' ' + data.year_pillar);
        }
      }
    }
    catch (e) {error.textContent = '查询失败：' + e.message;}
    finally {if (prev.isConnected) {button.disabled = false; if (now) now.disabled = false; edges();}}
  };
  // The automatic run on opening presses this button from script, and leaves the keyboard where it was.
  button.addEventListener('click', e => run(typed(), e.isTrusted ? 'annual-run' : null));
  year.addEventListener('keydown', e => {if (e.key === 'Enter') {e.preventDefault(); run(typed(), 'annual-year');}});
  prev.addEventListener('click', () => run(step(-1), 'annual-prev'));
  next.addEventListener('click', () => run(step(1), 'annual-next'));
  if (now) now.addEventListener('click', () => run(nowYear, 'annual-year'));
  if (annualFocus) {
    const target = $('#' + annualFocus); annualFocus = null;
    (target && !target.disabled ? target : year).focus();
  }
  if (!annualResult) {append(result, 'p', 'info-inline', '选择目标农历年，查看其干四化在本命盘星曜中的位置。'); return;}
  const a = annualResult, z = current.ziwei;
  // Near the lunar new year an unknown hour can change the birth-year stem, so the birth-year four are left out.
  const natalOpen = currentHourUnknown && lunarYearOpen(current.bazi, z);
  const head = append(result, 'div', 'ay-head');
  const gz = append(head, 'b', 'ay-gz'); gz.dataset.noI18n = '';
  append(gz, 'span', stemClass(a.year_pillar[0]), a.year_pillar[0]); append(gz, 'span', branchClass(a.year_pillar[1]), a.year_pillar[1]);
  const facts = append(head, 'dl', 'ay-facts');
  const fact = (label, ...parts) => {const box = append(facts, 'div'); append(box, 'dt', null, label); return texts(append(box, 'dd'), ...parts);};
  const yearFact = fact('农历纪年', a.lunar_year);
  if (a.lunar_year === nowYear) {yearFact.append(' '); append(yearFact, 'small', 'ay-now', '今年'); yearFact.setAttribute('aria-current', 'date');}
  const span = a.gregorian_span;
  if (span.end) fact('公历起止', span.start, ' – ', span.end); else fact('公历起始', span.start);
  const branch = fact('年支', a.year_pillar[1]); branch.dataset.noI18n = '';
  fact('年支所在本命宫', a.year_branch_palace);
  append(head, 'span', 'ay-school', a.school);
  const cards = append(result, 'div', 'transform-grid ay-cards');
  a.transformations.forEach(t => {
    const box = append(cards, 'div', 'transform-card ay-card hua-card-' + (HUA_CLASS[t.type] || 'lu'));
    const type = append(box, 'div', 'transform-type'); quietBadge(type, t.type, true); type.append(' ' + t.type);
    append(box, 'div', 'transform-star', t.star);
    append(box, 'div', 'transform-palace', t.natal_palace + ' · ' + t.natal_branch);
    if (t.natal_type && !natalOpen) {
      const same = append(box, 'div', 'ay-natal');
      quietBadge(same, t.natal_type, false); same.append(' '); texts(same, '本命', ' ', t.natal_type);
    }
  });
  // The natal board in miniature: main stars plus any star carrying a transformation, birth-year badges filled and
  // this year's outlined, so the two sets read apart by shape and text.
  const yearHua = new Map(), natalHua = new Map();
  a.transformations.forEach(t => yearHua.set(t.star, t.type));
  if (!natalOpen) a.natal_transformations.forEach(t => natalHua.set(t.star, t.type));
  append(result, 'h4', 'subheading', '本命十二宫上的四化');
  const board = append(result, 'ul', 'ay-board'); board.id = 'annual-board';
  board.setAttribute('role', 'list');  // list-style:none drops the list role in Safari
  board.setAttribute('aria-label', '本命十二宫上的生年四化与该年四化');
  z.palaces.forEach((p, index) => {
    const hits = a.transformations.filter(t => t.natal_palace === p.name);
    const cell = append(board, 'li', 'ay-cell' + (hits.length ? ' has-year' : '') + (p.name === a.year_branch_palace ? ' is-branch' : ''));
    cell.style.gridRow = String(ZIWEI_CELLS[index][0]); cell.style.gridColumn = String(ZIWEI_CELLS[index][1]);
    const top = append(cell, 'div', 'ay-cell-head');
    append(top, 'b', null, p.name.replace('宫', ''));
    // A palace's stem follows the birth-year stem alone, so only an unsettled birth year hides it.
    if (!natalOpen) {const at = append(top, 'small', null, p.stem + p.branch); at.dataset.noI18n = '';}
    const stars = append(cell, 'div', 'ay-stars');
    const shown = [...p.main_stars, ...p.auxiliary_stars.filter(star => yearHua.has(star) || natalHua.has(star))];
    if (!shown.length) append(stars, 'span', 'ay-empty', '—');
    shown.forEach(star => {
      const holder = append(stars, 'span', 'ay-star' + (yearHua.has(star) ? ' is-year' : ''), star);
      if (natalHua.has(star)) annualBadge(holder, natalHua.get(star), false);
      if (yearHua.has(star)) annualBadge(holder, yearHua.get(star), true);
    });
    const marks = [p.is_ming && '命', p.is_shen && '身', p.name === a.year_branch_palace && '年支'].filter(Boolean);
    if (marks.length) {const foot = append(cell, 'div', 'ay-marks'); marks.forEach(m => append(foot, 'span', 'palace-mark' + (m === '年支' ? ' layer-mark' : ''), m));}
  });
  const center = append(board, 'li', 'ay-center'); center.setAttribute('aria-hidden', 'true');
  const big = append(center, 'b', 'ay-gz'); big.dataset.noI18n = '';
  append(big, 'span', stemClass(a.year_pillar[0]), a.year_pillar[0]); append(big, 'span', branchClass(a.year_pillar[1]), a.year_pillar[1]);
  append(center, 'small', null, String(a.lunar_year));
  const sum = append(center, 'div', 'ay-center-hua');
  a.transformations.forEach(t => {const item = append(sum, 'span'); quietBadge(item, t.type, true); append(item, 'span', null, t.star);});
  const legend = append(result, 'p', 'field-help ay-legend');
  if (!natalOpen) {const item = append(legend, 'span'); quietBadge(item, '化禄', false); item.append(' '); append(item, 'span', null, '生年四化');}
  const item = append(legend, 'span'); quietBadge(item, '化禄', true); item.append(' '); append(item, 'span', null, '该年四化');
  append(legend, 'span', null, '加框的宫位有该年四化；「年支」是该年地支所在的本命宫。');
  // The same facts as a table, which is also what a screen reader and a printed page lean on.
  const wrap = append(result, 'div', 'table-wrap');
  const table = append(wrap, 'table', 'data-table ay-table'); table.id = 'annual-table';
  append(table, 'caption', 'visually-hidden', '该年四化逐项对照');
  const th = append(append(table, 'thead'), 'tr');
  ['四化', '星曜', '落本命宫', '该宫主星', ...(natalOpen ? [] : ['本命此星'])].forEach(t => {append(th, 'th', null, t).scope = 'col';});
  const tbody = append(table, 'tbody');
  a.transformations.forEach(t => {
    const tr = append(tbody, 'tr');
    const first = append(tr, 'th'); first.scope = 'row'; quietBadge(first, t.type, true); first.append(' '); append(first, 'span', null, t.type);
    append(tr, 'td', 'ay-row-star', t.star);
    stackLabel(append(tr, 'td'), '落本命宫').append(t.natal_palace + ' · ' + t.natal_branch);
    const palace = z.palaces.find(p => p.name === t.natal_palace);
    const mains = stackLabel(append(tr, 'td', 'dy-fit-cell ay-row-mains'), '该宫主星');
    if (palace && palace.main_stars.length) enumList(mains, palace.main_stars); else mains.append('无主星');
    if (!natalOpen) stackLabel(append(tr, 'td', 'ay-row-natal'), '本命此星').append(t.natal_type || '—');
  });
  // Under 6em the main stars wrap a name to a line.
  table.dataset.fitEm = '6';
  stackTable(table);
  const actions = append(result, 'div', 'ay-actions');
  const layer = append(actions, 'button', 'tiny-button', '在紫微盘打开该年流年层'); layer.type = 'button'; layer.id = 'annual-open-year';
  layer.addEventListener('click', () => {
    ziweiLayer = {mode: 'year', decade: null, year: a.lunar_year, date: null};
    activateTab(tabs.find(t => t.dataset.tab === 'ziwei'));
    // The keyboard lands on the palace of the year's branch, the year's own 命宫 on that layer.
    const node = $('#palace-' + z.palaces.findIndex(p => p.name === a.year_branch_palace));
    if (node) node.focus();
    announce('紫微盘已切到 ' + a.lunar_year + ' 年流年层');
  });
  // The year-by-year matrix starts here with the number of years chosen there, cut down so it does not pass 2099,
  // and shows all twelve palaces rather than a palace filter left from before.
  const fits = n => a.lunar_year + n - 1 <= 2099;
  if (fits(3)) {
    const ten = append(actions, 'button', 'tiny-button', '从这一年起看连续年份'); ten.type = 'button'; ten.id = 'annual-timeline';
    ten.addEventListener('click', () => {
      const want = Number(typedValues['timeline-years'] ?? timelineDraft.years) || 10;
      const years = [30, 20, 10, 5, 3].find(n => n <= want && fits(n)) || 3;
      timelineDraft = {start_lunar_year: a.lunar_year, years, focus_palace: ''}; timelineResult = null;
      ['timeline-start', 'timeline-years', 'timeline-focus'].forEach(id => delete typedValues[id]);
      autoOpened.add('timeline');  // run once below, whether or not the page has opened on this chart before
      const tab = tabs.find(t => t.dataset.tab === 'timeline');
      activateTab(tab); tab.focus();
      const go = $('#timeline-run'); if (go) go.click();
    });
  }
  if (natalOpen) append(result, 'p', 'field-help', '命盘时辰不详，出生当天又在农历年的交界：生年天干可能随时辰不同，生年四化暂不列出。');
  if (currentHourUnknown) append(result, 'p', 'field-help', '时辰不详：宫位按 12:00 占位时辰排出，四化星落在哪一宫会随时辰变化。');
  a.limitations.forEach(t => note(result, t));
}
// Sampling around the birth time of the current chart. It is drawn like the boundary map (a line, the changes, a card
// per structure); the exact moment of each change is the boundary map's job, one click away.
function renderBirthWindowSection(){
  const section = append(result, 'section', 'bw-section'); section.id = 'birth-window';
  section.setAttribute('aria-labelledby', 'birth-window-title');
  append(section, 'h3', 'subheading', '出生时间误差采样').id = 'birth-window-title';
  append(section, 'p', 'info-inline', '以出生时间为中心，在前后误差内每隔几分钟排一次盘，列出出现过的不同四柱、命宫、身宫和五行局。两个采样点之间的切换可能漏掉，精确时刻见「生时边界地图」。');
  const row = append(section, 'div', 'inline-control');
  const radius = createInput('前后误差（分钟）', 'number', String(windowDraft.radius), row); radius.id = 'window-radius'; radius.min = '5'; radius.max = '120'; radius.step = '1';
  const spacing = createInput('采样间隔（分钟）', 'number', String(windowDraft.spacing), row); spacing.id = 'window-spacing'; spacing.min = '5'; spacing.max = '60'; spacing.step = '1';
  keepTyped(radius, spacing);
  const go = append(row, 'button', null, '采样计算'); go.type = 'button'; go.id = 'window-run';
  const msg = append(section, 'p', 'inline-msg'); msg.id = 'window-msg'; msg.setAttribute('role', 'alert');
  go.addEventListener('click', async () => {
    const r = Number(radius.value), s = Number(spacing.value);
    [radius, spacing].forEach(el => el.removeAttribute('aria-invalid'));
    const bad = !Number.isInteger(r) || r < 5 || r > 120 ? radius : !Number.isInteger(s) || s < 5 || s > 60 ? spacing : null;
    if (bad) {bad.setAttribute('aria-invalid', 'true'); msg.textContent = calT(bad === radius ? '前后误差需为 5–120 的整数分钟。' : '采样间隔需为 5–60 的整数分钟。'); bad.focus(); return;}
    windowDraft = {radius: r, spacing: s}; go.disabled = true; msg.textContent = '';
    try {
      const data = await postForChart('/api/birth-window', {birth: currentInput || readInput(), uncertainty_minutes: r, sample_every_minutes: s});
      if (data !== STALE) {windowResult = data; render(); const out = $('#window-summary'); if (out) out.focus();}
    } catch (e) {msg.textContent = calT('采样失败：') + e.message;}
    finally {go.disabled = false;}
  });
  if (currentHourUnknown) append(section, 'p', 'field-help', '时辰不详：这里的出生时间 12:00 只是占位，采样结果不代表真实出生时刻前后的变化。');
  if (!windowResult) return;
  const w = windowResult, R = w.uncertainty_minutes, samples = w.samples;
  const birthSample = samples.find(x => x.offset_minutes === 0) || samples[Math.floor(samples.length / 2)];
  const base = w.variants[birthSample.variant_index - 1], day0 = w.center_local.slice(0, 10);
  const clock = iso => (iso.slice(0, 10) !== day0 ? iso.slice(5, 10).replace('-', '/') + ' ' : '') + iso.slice(11, 16);
  const summary = append(section, 'p', 'bw-summary'); summary.id = 'window-summary'; summary.tabIndex = -1;
  texts(summary, '前后 ', R, ' 分钟内间隔 ', w.sample_every_minutes, ' 分钟采样（另含出生时刻与两端），共 ', w.sample_count, ' 个点：');
  if (w.variant_count === 1) texts(summary, '四柱、命宫、身宫和五行局都不变。');
  else texts(summary, '出现 ', w.variant_count, ' 种结构。');
  // Runs of neighbouring samples with the same structure; between two runs the change happened somewhere in the gap.
  const runs = [];
  samples.forEach(x => {const last = runs[runs.length - 1]; if (last && last.v === x.variant_index) last.to = x; else runs.push({v: x.variant_index, from: x, to: x});});
  const at = off => (off + R) / (2 * R) * 100;
  const line = append(section, 'div', 'bt-line bw-line'); line.id = 'window-line';
  const track = append(line, 'div', 'bt-track'); track.setAttribute('aria-hidden', 'true');
  const bands = append(track, 'div', 'bt-bands');
  runs.forEach((run, i) => {
    const left = at(run.from.offset_minutes), width = Math.max(at(run.to.offset_minutes) - left, 1.5);
    const band = append(bands, 'span', 'bt-seg' + (run.v % 2 ? '' : ' is-alt') + (run.v === birthSample.variant_index ? ' is-birth' : '') + (width < 5 ? ' is-narrow' : ''));
    band.style.left = Math.min(left, 100 - width) + '%'; band.style.width = width + '%';
    append(band, 'span', 'bt-seg-num', String(run.v));
    if (i) {
      const gap = append(bands, 'span', 'bw-gap'), from = at(runs[i - 1].to.offset_minutes);
      gap.style.left = from + '%'; gap.style.width = (left - from) + '%';
    }
  });
  // Dots stay inside the track at both ends.
  samples.forEach(x => {append(track, 'span', 'bw-dot').style.left = `calc(2px + (100% - 4px) * ${at(x.offset_minutes) / 100})`;});
  const changes = runs.slice(1).map((run, i) => ({before: runs[i], after: run}));
  // An 18px badge needs this much of the track before the next one, as on the boundary map.
  const badgeGap = 2000 / Math.max(track.getBoundingClientRect().width, 200), rows = [];
  changes.forEach((c, i) => {
    const left = (at(c.before.to.offset_minutes) + at(c.after.from.offset_minutes)) / 2, tick = append(track, 'span', 'bt-tick bw-tick'); tick.style.left = left + '%';
    let row = rows.findIndex(last => left - last >= badgeGap); if (row < 0) row = rows.length; rows[row] = left;
    append(tick, 'span', 'bt-tick-num' + (row ? ' is-up' + Math.min(row, 2) : ''), String(i + 1));
    if (row) line.classList.add('has-up' + Math.min(row, 2));
  });
  append(track, 'span', 'bt-pin').style.left = at(birthSample.offset_minutes) + '%';
  const axis = append(line, 'div', 'bt-axis');
  append(axis, 'span', null, clock(samples[0].local_time));
  texts(append(axis, 'span', 'bt-axis-birth'), '出生时间', ' ' + clock(birthSample.local_time)).style.left = at(birthSample.offset_minutes) + '%';
  append(axis, 'span', null, clock(samples[samples.length - 1].local_time));
  // What differs between the structures on either side of each gap.
  const diff = (a, b) => {
    const out = PILLAR_KEYS.filter(k => a.pillars[k] !== b.pillars[k]).map(k => [nameMap[k], a.pillars[k], b.pillars[k]]);
    [['命宫', 'ming_palace'], ['身宫', 'shen_palace'], ['五行局', 'five_elements_bureau']].forEach(([label, key]) => {if (a[key] !== b[key]) out.push([label, a[key], b[key]]);});
    return out;
  };
  if (changes.length) {
    append(section, 'h4', 'subheading', '采样之间的切换');
    const list = append(section, 'ol', 'bt-switches'); list.id = 'window-changes';
    changes.forEach((c, i) => {
      const item = append(list, 'li', 'bt-switch');
      append(item, 'span', 'bt-tick-num', String(i + 1));
      const body = append(item, 'div');
      const head = append(body, 'p', 'bt-switch-head');
      append(head, 'b', null, clock(c.before.to.local_time) + ' – ' + clock(c.after.from.local_time));
      append(head, 'span', 'bt-type', '切换在这两个采样点之间');
      const chips = append(body, 'p', 'bt-changes');
      diff(w.variants[c.before.v - 1], w.variants[c.after.v - 1]).forEach(([label, from, to]) => texts(append(chips, 'span', 'bt-change'), label, ' ', from + ' → ' + to));
    });
  }
  append(section, 'h4', 'subheading', '出现过的结构');
  const cards = append(section, 'div', 'bt-cards'); cards.id = 'window-cards';
  w.variants.forEach((v, i) => {
    const isBirth = v === base;
    const card = append(cards, 'section', 'bt-card' + (isBirth ? ' is-birth' : '')); card.id = 'window-variant-' + (i + 1);
    const head = append(card, 'div', 'bt-card-head');
    append(head, 'b', 'bt-card-num', String(i + 1));
    append(head, 'span', 'bt-card-range', v.first_sample_local === v.last_sample_local ? clock(v.first_sample_local) : clock(v.first_sample_local) + ' – ' + clock(v.last_sample_local));
    texts(append(head, 'small', 'muted'), v.sample_count === 1 ? '1 个采样点' : v.sample_count + ' 个采样点');
    if (isBirth) append(head, 'span', 'bt-badge', '含出生时间');
    const pillars = append(card, 'div', 'bt-pillars');
    PILLAR_KEYS.forEach(k => {
      const gz = v.pillars[k], moved = !isBirth && gz !== base.pillars[k];
      const cell = append(pillars, 'span', 'bt-pillar' + (moved ? ' is-changed' : ''));
      append(cell, 'small', null, nameMap[k]);
      const text = append(cell, 'b', 'bt-gz'); text.dataset.noI18n = '';
      append(text, 'span', stemClass(gz[0]), gz[0]); append(text, 'span', branchClass(gz[1]), gz[1]);
      if (moved) append(cell, 'span', 'visually-hidden', '与出生时间不同');
    });
    const ziwei = append(card, 'p', 'bt-ziwei');
    [['ming_palace', '命宫'], ['shen_palace', '身宫'], ['five_elements_bureau', null]].forEach(([key, label]) => {
      const moved = !isBirth && v[key] !== base[key];
      const span = label ? texts(append(ziwei, 'span', 'bt-field' + (moved ? ' is-changed' : '')), label, ' ', v[key]) : texts(append(ziwei, 'span', 'bt-field' + (moved ? ' is-changed' : '')), v[key]);
      if (moved) append(span, 'span', 'visually-hidden', '与出生时间不同');
    });
  });
  // The exact moments: the boundary map with the same error, already run.
  const exact = append(section, 'p', 'field-help bw-exact');
  texts(exact, '采样只能说明切换发生在哪两个点之间。', ' ');
  const open = append(exact, 'button', 'tiny-button', '在生时边界地图上找精确时刻'); open.type = 'button'; open.id = 'window-boundaries';
  open.addEventListener('click', () => {
    boundaryDraft = {uncertainty_minutes: R}; boundaryResult = null; delete typedValues['boundary-radius'];
    autoOpened.add('boundaries');  // run once below, whether or not the page has opened on this chart before
    // The boundary map reads the birth form, so with edits not yet cast it would map another birth than this sampling.
    const edited = JSON.stringify(readInput()) !== JSON.stringify(currentInput);
    activateTab(tabs.find(t => t.dataset.tab === 'boundaries'));
    result.focus({preventScroll: true});
    if (edited) {announce(calT('已打开生时边界地图。出生资料有尚未排盘的修改，重新生成命盘后再定位。')); return;}
    announce(calT('已打开生时边界地图，正在定位'));
    const run = $('#boundary-run'); if (run) run.click();
  });
  w.limitations.forEach(t => note(section, t));
}
// Where each time system's reading falls among the two-hour periods. The hour branch changes at every odd hour
// (23:00, 01:00 …). With the day changing at midnight (the default rule), the day pillar and with it the hour stem
// also change at 00:00, inside 子时; with the day changing at 23:00 the two coincide. A reading a few minutes from
// either changes the chart with a small error in the birth time.
const SHICHEN_NAMES = ['子时', '丑时', '寅时', '卯时', '辰时', '巳时', '午时', '未时', '申时', '酉时', '戌时', '亥时'];
function timeScale(parent, audit, names, lateZi) {
  const clock = audit.choices.find(t => t.mode === 'clock') || audit.choices[0];
  const dayStart = Date.parse(clock.effective_reading.slice(0, 10) + 'T00:00:00Z');
  const minuteOf = t => (Date.parse(t.effective_reading.slice(0, 19) + 'Z') - dayStart) / 60000;
  const periodStart = m => Math.floor((m - 60) / 120) * 120 + 60;
  const periodAt = m => SHICHEN_NAMES[Math.floor(((Math.floor(m / 60) + 1) % 24 + 24) % 24 / 2)];
  const isZi = s => ((s % 1440) + 1440) % 1440 === 1380;
  // Readings are cut to the minute, as on the cards above, so 10:59:31 reads 10:59 and not 11:00.
  const hhmm = m => {const d = ((Math.floor(m) % 1440) + 1440) % 1440; return String(Math.floor(d / 60)).padStart(2, '0') + ':' + String(d % 60).padStart(2, '0');};
  const marks = audit.choices.map((t, i) => {
    const m = minuteOf(t), start = periodStart(m);
    const edges = [start, start + 120].concat(!lateZi && isZi(start) ? [start + 60] : []);
    const boundary = edges.reduce((a, b) => Math.abs(b - m) < Math.abs(a - m) ? b : a);
    return {t, i, m, start, near: Math.abs(boundary - m), boundary, midnight: boundary !== start && boundary !== start + 120};
  });
  // One period of margin on either side, so the nearest boundary is always on the scale.
  const lo = Math.min(...marks.map(x => x.start)) - 120, hi = Math.max(...marks.map(x => x.start)) + 240, at = m => (m - lo) / (hi - lo) * 100;
  const box = append(parent, 'section', 'ts-scale'); box.id = 'time-scale'; box.setAttribute('aria-labelledby', 'time-scale-title');
  append(box, 'h4', 'subheading', '三种时制落在哪个时辰').id = 'time-scale-title';
  const line = append(box, 'div', 'bt-line ts-line');
  const track = append(line, 'div', 'bt-track'); track.setAttribute('aria-hidden', 'true');
  const bands = append(track, 'div', 'bt-bands');
  const usedMark = marks.find(x => x.t.mode === audit.original_time_mode) || marks[0];
  for (let s = lo, k = 0; s < hi; s += 120, k++) {
    // Under the midnight rule 子时 is two bands: late 子 before 00:00 and early 子 after it belong to different days.
    const parts = !lateZi && isZi(s) ? [[s, 60, '晚子'], [s + 60, 60, '早子']] : [[s, 120, periodAt(s)]];
    parts.forEach(([from, length, name]) => {
      const birth = usedMark.m >= from && usedMark.m < from + length;
      const band = append(bands, 'span', 'bt-seg' + (k % 2 ? ' is-alt' : '') + (birth ? ' is-birth' : '') + (length < 120 ? ' ts-half' : '') + (length / (hi - lo) < 0.07 ? ' is-narrow' : ''));
      band.style.left = at(from) + '%'; band.style.width = (length / (hi - lo) * 100) + '%';
      append(band, 'span', 'bt-seg-num', name);
    });
  }
  // A badge that would overlap the one before it moves up a row, as on the boundary map.
  const badgeGap = 2000 / Math.max(track.getBoundingClientRect().width, 200), rows = [];
  [...marks].sort((a, b) => a.m - b.m).forEach(x => {
    const left = at(x.m), tick = append(track, 'span', 'bt-tick ts-tick'); tick.style.left = left + '%';
    let row = rows.findIndex(last => left - last >= badgeGap); if (row < 0) row = rows.length; rows[row] = left;
    append(tick, 'span', 'bt-tick-num' + (row ? ' is-up' + Math.min(row, 2) : ''), String(x.i + 1));
    if (row) line.classList.add('has-up' + Math.min(row, 2));
  });
  const axis = append(line, 'div', 'bt-axis');
  append(axis, 'span', null, hhmm(lo)); append(axis, 'span', null, hhmm(hi));
  // The same facts in words: which period each reading is in and how far the nearest change of period is.
  const list = append(box, 'ol', 'bt-switches ts-list'); list.id = 'time-scale-list';
  marks.forEach(x => {
    const item = append(list, 'li', 'bt-switch' + (x.near < 15 ? ' is-near' : '')); item.id = 'time-scale-' + x.t.mode;
    append(item, 'span', 'bt-tick-num', String(x.i + 1));
    const body = append(item, 'p', 'bt-switch-head');
    append(body, 'b', null, names[x.t.mode]);
    append(body, 'span', 'ts-time', hhmm(x.m));
    append(body, 'span', 'bt-type', periodAt(x.start));
    const gap = append(body, 'span', 'ts-gap');
    durationText(texts(gap, x.midnight ? '最近日界 ' : '最近交界 ', hhmm(x.boundary), ' · '), x.near);
    if (x.t.mode === audit.original_time_mode) append(body, 'span', 'bt-badge', '当前排盘所用');
  });
  const used = marks.find(x => x.t.mode === audit.original_time_mode);
  if (used && used.near < 15) append(box, 'p', 'ts-warn', used.midnight
    ? '当前排盘所用的时间离 00:00 日界不到 15 分钟：按 00:00 换日，出生时间稍有误差，日柱和时干就会改变。'
    : '当前排盘所用的时间离时辰交界不到 15 分钟：出生时间稍有误差，时柱就会换成相邻的时辰。');
  if (currentHourUnknown) append(box, 'p', 'field-help', '时辰不详：钟表时间 12:00 只是占位，这里的时辰和交界不代表真实出生时刻。');
}
// The three clocks side by side. Without a longitude in the birth data, one can be picked here for this page only:
// it never changes the birth data, so the chart and its exports stay as generated.
let timeLongitude = '', timeRun = null;
function renderTimeAudit() {
  title(result,'出生时间与经度审计','比较三种时制 / 相同天文瞬间');
  const inp=readInput(), formLongitude = inp.longitude;
  append(result,'p','info-inline','填写出生地经度后，计算钟表时间、地方平太阳时、真太阳时的四柱与命身宫差异。');
  const row=append(result,'div','inline-control');
  let box = null;
  if (formLongitude === null) {
    const label = append(row, 'label', null, '出生城市（仅用于本页）');
    const city = append(label, 'select'); city.id = 'time-city';
    append(city, 'option', null, '选择城市').value = '';
    // Only cities on the birth time zone's clock, so the clock time keeps its meaning.
    (typeof CITY_PRESETS === 'object' ? CITY_PRESETS : []).forEach(([region, list]) => {
      const group = append(city, 'optgroup'); group.label = region;
      list.filter(c => c[1] === inp.timezone).forEach(([name, , longitude]) => {append(group, 'option', null, name).value = String(longitude);});
      if (!group.children.length) group.remove();
    });
    box = createInput('经度（东经为正）', 'number', timeLongitude, row); box.id = 'time-longitude';
    box.min = '-180'; box.max = '180'; box.step = 'any';
    city.value = [...city.options].some(o => o.value && o.value === timeLongitude) ? timeLongitude : '';
    city.addEventListener('change', () => {box.value = city.value; timeLongitude = city.value; box.removeAttribute('aria-invalid');});
    box.addEventListener('input', () => {timeLongitude = box.value.trim(); box.removeAttribute('aria-invalid'); city.value = [...city.options].some(o => o.value && o.value === timeLongitude) ? timeLongitude : '';});
  }
  const run=append(row,'button',null,'计算时制对照');run.id='time-run';run.type='button';
  const error=append(result,'p','inline-msg'); error.setAttribute('aria-live', 'polite');
  run.addEventListener('click',async()=>{
    const typed = box ? box.value.trim() : '', longitude = formLongitude !== null ? formLongitude : Number(typed);
    if (formLongitude === null && (typed === '' || !Number.isFinite(longitude) || longitude < -180 || longitude > 180)) {
      box.setAttribute('aria-invalid', 'true'); error.textContent = '请选择出生城市或填写经度（-180 到 180）。'; return;
    }
    run.disabled=true; error.textContent='';
    try{
      const birth = {...readInput(), longitude};
      const data = await postForChart('/api/time-audit',{birth});
      if (data !== STALE) {timeResult = data; timeRun = {birth, ownLongitude: formLongitude === null}; render();}
    }
    catch(e){error.textContent='计算失败：'+e.message;}
    finally{run.disabled=false;}
  });
  if (formLongitude === null) append(result, 'p', 'field-help', '出生资料里没有经度：这里选的城市或经度只用于本页对照，不改出生资料，也不保存。');
  if(timeResult) {
    const used = timeRun ? timeRun.birth : {...inp, longitude: timeResult.longitude};
    const where = append(result, 'div', 'meta-tags');
    texts(append(where, 'span'), '出生地经度', ' ' + Math.abs(timeResult.longitude) + '°' + (timeResult.longitude >= 0 ? 'E' : 'W'));
    if (timeRun && timeRun.ownLongitude) append(where, 'span', null, '仅用于本页');
    texts(append(where, 'span'), '时区', ' ' + used.timezone);
    const clock = timeResult.choices.find(t => t.mode === 'clock') || timeResult.choices[0];
    const names = {clock: '钟表时间', mean_solar: '平太阳时', apparent_solar: '真太阳时'};
    const grid = append(result, 'div', 'tb-grid'); grid.id = 'time-cards';
    timeResult.choices.forEach(t => {
      const card = append(grid, 'section', 'tb-card' + (t.mode === timeResult.original_time_mode ? ' is-used' : '')); card.id = 'time-' + t.mode;
      const head = append(card, 'div', 'tb-head');
      append(head, 'h4', null, names[t.mode]);
      if (t.mode === timeResult.original_time_mode) append(head, 'span', 'bt-badge', '当前排盘所用');
      const at = append(card, 'p', 'tb-time');
      append(at, 'b', null, t.effective_reading.slice(11, 19));
      if (t.effective_reading.slice(0, 10) !== clock.effective_reading.slice(0, 10)) append(at, 'small', 'tb-date', t.effective_reading.slice(0, 10));
      const shift = append(card, 'p', 'tb-shift');
      if (t.mode === 'clock') append(shift, 'span', null, '出生地法定钟表时间');
      else {
        if (Math.round(t.shift_minutes * 60) === 0) append(shift, 'span', null, '与钟表时间相同');
        else durationText(texts(shift, t.shift_minutes < 0 ? '比钟表慢' : '比钟表快', ' '), t.shift_minutes);
        // A mean solar shift is the longitude against the zone meridian; the apparent one adds the equation of time.
        const parts = append(card, 'p', 'tb-parts');
        // During daylight saving the clock runs an hour ahead of the zone's standard meridian, shown on its own.
        const signed = n => Math.abs(n) < 0.05 ? '0.0' : (n > 0 ? '+' : '−') + Math.abs(n).toFixed(1);
        const dst = timeResult.dst_minutes || 0;
        const meridian = timeResult.longitude_vs_standard_meridian_minutes ?? t.shift_minutes - (t.equation_of_time_minutes || 0) + dst;
        texts(parts, '经度差', ' ' + signed(meridian), ' 分');
        if (dst) texts(parts, ' · ', '夏令时', ' ' + signed(-dst), ' 分');
        if (t.mode === 'apparent_solar') texts(parts, ' · ', '均时差', ' ' + signed(t.equation_of_time_minutes), ' 分');
      }
      // A changed value is marked in words for screen readers, not only by its colour.
      const changedMark = (el, changed) => {if (changed) append(el, 'span', 'visually-hidden', '与钟表时间不同'); return el;};
      const pillars = append(card, 'div', 'bt-pillars');
      PILLAR_KEYS.forEach(k => {
        const gz = t.pillars[k], changed = t !== clock && gz !== clock.pillars[k];
        const cell = append(pillars, 'span', 'bt-pillar' + (changed ? ' is-changed' : ''));
        append(cell, 'small', null, nameMap[k]);
        const text = append(cell, 'b', 'bt-gz'); text.dataset.noI18n = '';
        append(text, 'span', stemClass(gz[0]), gz[0]); append(text, 'span', branchClass(gz[1]), gz[1]);
        changedMark(cell, changed);
      });
      const ziwei = append(card, 'p', 'bt-ziwei');
      [['命宫', 'ming_palace'], ['身宫', 'shen_palace']].forEach(([name, key]) => {
        const changed = t !== clock && t[key] !== clock[key];
        changedMark(texts(append(ziwei, 'span', 'bt-field' + (changed ? ' is-changed' : '')), name, ' ', t[key]), changed);
      });
      const lunarChanged = t !== clock && lunarDateText(t.lunar_date) !== lunarDateText(clock.lunar_date);
      const lunar = append(card, 'p', 'bt-lunar' + (lunarChanged ? ' is-changed' : ''));
      texts(lunar, '农历', ' '); append(lunar, 'span', null, lunarDateText(t.lunar_date)).dataset.noI18n = '';
      changedMark(lunar, lunarChanged);
    });
    const differ = timeResult.choices.filter(t => t !== clock && (PILLAR_KEYS.some(k => t.pillars[k] !== clock.pillars[k])
      || t.ming_palace !== clock.ming_palace || t.shen_palace !== clock.shen_palace || lunarDateText(t.lunar_date) !== lunarDateText(clock.lunar_date)));
    append(result, 'p', 'field-help', !differ.length ? '三种时制下四柱、命宫、身宫与农历日期都相同。'
      : timeResult.original_time_mode === 'clock' ? '标色的项目和钟表时间不同；换用太阳时会改变这些结果。'
      : '标色的项目和钟表时间不同；当前命盘已按加框的太阳时排盘，改按钟表时间会得到不同结果。');
    timeScale(result, timeResult, names, !!used.late_zi_day_rollover);
    // The three cards already compare the time systems; the other rules are compared on their own page.
    const others = append(result, 'p', 'field-help tb-others');
    texts(others, '23:00 换日、闰月分界等其他规则的影响见「规则差异对照」。', ' ');
    const open = append(others, 'button', 'tiny-button', '打开规则差异对照'); open.type = 'button'; open.id = 'time-open-rules';
    open.addEventListener('click', () => cwOpenPage('rule-matrix', '规则差异对照'));
    timeResult.warnings.forEach(t=>note(result,t));
  } else append(result,'p','info-inline','不会自动保存出生资料或经度；审计结果包含具体时差与命盘差异。');
  renderBirthWindowSection();
}
function renderQualityAudit() {
  title(result, '出生记录与排盘质量审计', '节令 / 时辰 / 公历日界 / 远期历法不确定性');
  append(result, 'p', 'info-inline', '本工具只标记数据与计算边界，不替代权威历书或完整紫微流派审查。');
  const control = append(result, 'div', 'inline-control');
  const minutes = createInput('边界敏感窗口（分钟）', 'number', '15', control);
  minutes.min = '1'; minutes.max = '1440'; minutes.id = 'quality-minutes'; minutes.value = String(qualityMinutesDraft); keepTyped(minutes);
  const run = append(control, 'button', null, '核验输入与边界'); run.type = 'button'; run.id = 'quality-run';
  const msg = append(result, 'p', 'inline-msg');
  run.addEventListener('click', async () => {
    run.disabled = true; msg.textContent = '';
    try {
      const value = Number(minutes.value);
      qualityMinutesDraft = value;
      const input = readInput();
      const data = await postForChart('/api/quality-audit', {birth:input, boundary_window_minutes:value});
      if (data !== STALE) {qualityResult = data; qualityRun = {input, window: value}; render();}
    } catch(e) {msg.textContent = '核验失败：' + e.message;}
    finally {run.disabled = false;}
  });
  if (!qualityResult) {append(result, 'p', 'info-inline', '选择核验后列出实测四柱、日期、节令距离和需要复核的输入假设。');return;}
  const q = qualityResult, snap = q.calculation_snapshot, used = qualityRun || {input: readInput(), window: qualityMinutesDraft};
  const near = used.window, reviews = q.flags.filter(f => f.severity === 'review').length;
  const status = append(result, 'div', 'qa-status ' + (q.review_needed ? 'is-review' : 'is-clear')); status.id = 'quality-status';
  append(status, 'strong', null, q.review_needed ? '存在需人工核对的边界' : '未发现当前规则已知边界问题');
  if (reviews) texts(append(status, 'span'), reviews, ' 项需核对');
  meta(result, ['有效时间 ' + snap.effective_traditional_time.replace('T', ' '), '年/月/日/时 ' + Object.values(snap.bazi_pillars).join('/')]);
  // Where the birth sits between the two jie that bound its month pillar, as on 今日历法.
  const term = append(result, 'section', 'today-term qa-term'); term.id = 'quality-term';
  const side = (cls, jie, label, minutes) => {
    const box = append(term, 'div', cls + (minutes <= near ? ' is-near' : ''));
    append(box, 'strong', null, jie.name);
    durationText(texts(append(box, 'small'), label, ' '), minutes);
    texts(append(box, 'small'), '交节', ' ' + clockOf(jie.instant));
    if (minutes <= near) append(box, 'small', 'qa-near', '在敏感窗口内');
  };
  const since = snap.minutes_since_previous_jie, until = snap.minutes_until_next_jie;
  side('today-term-now', snap.previous_jie, '交节已过', since);
  const track = append(term, 'div', 'today-term-track');
  track.setAttribute('role', 'progressbar'); track.setAttribute('aria-valuemin', '0'); track.setAttribute('aria-valuemax', '100');
  track.setAttribute('aria-valuenow', String(Math.round(since / (since + until) * 100)));
  track.setAttribute('aria-label', snap.previous_jie.name + ' → ' + snap.next_jie.name);
  append(track, 'span', 'today-term-fill').style.width = (since / (since + until) * 100).toFixed(2) + '%';
  side('today-term-next', snap.next_jie, '距交节还有', until);
  // The hour and day boundaries are read on the clock the chart uses (钟表时间, or solar time when chosen).
  const reading = snap.effective_traditional_time, at = Number(reading.slice(11, 13)) * 60 + Number(reading.slice(14, 16)) + Number(reading.slice(17, 19)) / 60;
  const apart = t => Math.min(Math.abs(at - t), 1440 - Math.abs(at - t));
  const nearest = [...Array(12)].map((_, i) => 60 + 120 * i).reduce((best, t) => apart(t) < apart(best) ? t : best);
  const gaps = append(result, 'div', 'qa-gaps');
  const gap = (id, label, minutes, ...what) => {
    const card = append(gaps, 'div', 'qa-gap' + (minutes <= near ? ' is-near' : '')); card.id = id;
    append(card, 'span', 'qa-gap-label', label);
    durationText(append(card, 'b', 'qa-gap-value'), minutes);
    texts(append(card, 'small'), ...what);
    if (minutes <= near) append(card, 'small', 'qa-near', '在敏感窗口内');
  };
  gap('quality-hour', '距时辰交界', snap.minutes_to_nearest_hour_boundary, '有效时刻', ' ' + reading.slice(11, 16), ' · ', '最近的交界', ' ' + String(nearest / 60 % 24).padStart(2, '0') + ':00');
  gap('quality-day', '距换日交界', snap.minutes_to_day_boundary, used.input.late_zi_day_rollover ? '按 23:00 换日' : '按 00:00 换日');
  texts(append(result, 'p', 'field-help qa-window'), '敏感窗口', ' ±' + near, ' 分钟');
  if(snap.china_reference_lunar_date && snap.china_reference_gregorian_date !== snap.lunar_lookup_gregorian_date){
    const chinese=snap.china_reference_lunar_date;
    append(result,'div','feature-note',
      '时区日界对照：出生地有效日期 '+snap.lunar_lookup_gregorian_date+
      '；同一瞬间北京日期 '+snap.china_reference_gregorian_date+
      '（农历 '+chinese.year+'年'+chinese.month+'月'+chinese.day+'日）。这不自动改变原命盘。');
  }
  append(result, 'h4', 'subheading', '核对项');
  const list = append(result, 'div', 'qa-flags'); list.id = 'quality-flags';
  if(!q.flags.length) append(list,'p','info-inline','没有触发本工具已知边界标记；不代表专业命盘获得认证。');
  q.flags.forEach(f => {
    const entry = append(list, 'section', 'qa-flag is-' + f.severity);
    const head = append(entry, 'div', 'qa-flag-head');
    append(head, 'span', 'qa-chip', f.severity === 'review' ? '需要复核' : '背景信息');
    append(head, 'code', 'qa-code', f.code);
    append(entry, 'p', null, f.detail);
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
  keepTyped(palace,year,question);
  const run=append(bar,'button',null,'执行证据分析');run.type='button';run.id='deep-run';
  const msg=append(result,'p','inline-msg');
  run.addEventListener('click',async()=>{
    const y=year.value.trim();
    if(y && (!/^[0-9]{4}$/.test(y)||Number(y)<1901||Number(y)>2099)){msg.textContent='农历年份必须是 1901–2099';return;}
    deepDraft={focus_palace:palace.value,lunar_year:y,question:question.value.trim()};
    run.disabled=true;msg.textContent='';
    try{
      const data=await postForChart('/api/deep-review',{birth:readInput(),focus_palace:deepDraft.focus_palace,
        lunar_year:y?Number(y):null, question:deepDraft.question||null,include_quality:true});
      if(data!==STALE){deepResult=data;render();}
    }catch(e){msg.textContent='分析失败：'+e.message;}
    finally{run.disabled=false;}
  });
  if(!deepResult)return;
  meta(result,[`关注 ${deepResult.focus_palace}`,`${deepResult.findings.length} 组可追溯观察`,`${deepResult.checks.filter(c=>c.passed).length}/${deepResult.checks.length} 条内部一致性检查`]);
  // Findings by group, with a row of links to each group; every card states the observation first, then its limit,
  // and keeps the exact fields, values and hashes it rests on one click away.
  const groups = [...new Set(deepResult.findings.map(f => f.group))];
  const toc = append(result, 'nav', 'ev-toc'); toc.setAttribute('aria-label', '证据分组');
  groups.forEach((group, i) => {
    const link = append(toc, 'a', 'ev-toc-link'); link.href = '#deep-group-' + i;
    append(link, 'b', null, group); append(link, 'span', 'visually-hidden', '：'); append(link, 'small', null, String(deepResult.findings.filter(f => f.group === group).length));
    // The link keeps #tool=deep in the address, so it scrolls itself and moves focus to the group for keyboard users.
    link.addEventListener('click', event => {
      event.preventDefault(); const target = $('#deep-group-' + i); if (!target) return;
      target.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start'});
      target.focus({preventScroll: true});
    });
  });
  const evidenceOf = (f, path) => (f.evidence.find(x => x.path === path) || {}).value;
  // With the hour unknown, the pillars the hour could change are the 12:00 placeholder's, so they are not shown as known.
  const open = current && current.bazi ? unsettledPillars(current.bazi) : new Set();
  const TIME_MODES = {clock: '钟表时间', mean_solar: '平太阳时', apparent_solar: '真太阳时'};
  const pillarsOf = value => {
    const row = elt('div', 'ev-pillars');
    PILLAR_KEYS.forEach(k => {
      const cell = append(row, 'span', 'ev-pillar' + (open.has(k) ? ' is-open' : '')); append(cell, 'small', null, nameMap[k]);
      if (open.has(k)) {append(cell, 'b', 'ev-gz', '?'); append(cell, 'small', 'muted', '随时辰而定'); return;}
      const gz = append(cell, 'b', 'ev-gz'); gz.dataset.noI18n = '';
      append(gz, 'span', stemClass(value[k][0]), value[k][0]); append(gz, 'span', branchClass(value[k][1]), value[k][1]);
    });
    return row;
  };
  // Structured views for the findings whose evidence is a table; the rest show the observation sentence.
  const views = {
    'bazi-pillars': f => {
      const value = evidenceOf(f, 'bazi.pillars'), mode = evidenceOf(f, 'bazi.time_basis');
      if (!value) return null;
      const box = elt('div', 'ev-hua'); box.append(pillarsOf(value));
      if (mode) texts(append(box, 'p', 'ev-basis'), '计算时制', ' ', TIME_MODES[mode] || mode);
      return box;
    },
    'bazi-hidden': f => {
      const hidden = evidenceOf(f, 'bazi.pillars'), base = deepResult.findings.find(x => x.id === 'bazi-pillars');
      const texts4 = base && evidenceOf(base, 'bazi.pillars');
      if (!hidden) return null;
      const table = elt('table', 'ev-hidden');
      PILLAR_KEYS.forEach(k => {
        const tr = append(table, 'tr', open.has(k) ? 'is-open' : null);
        const th = append(tr, 'th'); th.scope = 'row'; append(th, 'span', null, nameMap[k]);
        if (open.has(k)) {append(append(tr, 'td'), 'span', 'muted', '随时辰而定'); return;}
        if (texts4) {const branch = append(th, 'b', branchClass(texts4[k][1]), texts4[k][1]); branch.dataset.noI18n = '';}
        const stems = append(append(tr, 'td'), 'div', 'ev-chips');
        // Ten gods are counted from the day stem, so with the day pillar open they are left out.
        (hidden[k] || []).forEach(h => {const chip = append(stems, 'span', 'ev-chip'); append(chip, 'b', elementClass(h.element), h.stem); if (!open.has('day')) append(chip, 'span', null, h.ten_god);});
      });
      if (!open.has('day')) return table;
      const box = elt('div', 'ev-hua'); box.append(table); append(box, 'p', 'ev-basis', '日柱随时辰而定，日主未定，不标十神。');
      return box;
    },
    'bazi-relations': f => {
      const pairs = evidenceOf(f, 'bazi.branch_relations');
      if (!Array.isArray(pairs) || !pairs.length) return null;
      const box = elt('div', 'ev-hua');
      const settled = pairs.filter(r => !open.has(r.a) && !open.has(r.b));
      if (settled.length < pairs.length) append(box, 'p', 'ev-basis', '时辰不详：不列牵涉可能随时辰变化的柱的关系。');
      settled.forEach(r => {
        const row = append(box, 'p', 'ev-hua-row');
        texts(append(row, 'span', 'ev-hua-label'), nameMap[r.a] || r.a, ' · ', nameMap[r.b] || r.b);
        const branches = append(row, 'b', null, r.branches); branches.dataset.noI18n = '';
        r.labels.forEach(label => append(row, 'span', 'ev-chip', label));
      });
      return box;
    },
    'ziwei-four': f => {
      const natal = evidenceOf(f, 'ziwei.birth_year_transformations');
      if (!natal) return null;
      const box = elt('div', 'ev-hua');
      const line = (label, items) => {
        const row = append(box, 'p', 'ev-hua-row'); append(row, 'span', 'ev-hua-label', label);
        items.forEach(t => {
          const chip = append(row, 'span', 'reading-chip reading-hua-' + {化禄: 'lu', 化权: 'quan', 化科: 'ke', 化忌: 'ji'}[t.type]); append(chip, 'b', null, t.star); append(chip, 'span', null, t.type); append(chip, 'small', null, t.palace_name);
          if (t.self) append(chip, 'small', 'ev-self', '自化');
        });
      };
      if (currentHourUnknown) append(box, 'p', 'ev-basis', '时辰不详：宫位按 12:00 占位时辰排出，落宫会随时辰变化。');
      line('生年四化', natal);
      const flying = f.evidence.find(x => /palace_flying_transformations$/.test(x.path));
      if (flying && Array.isArray(flying.value)) line('焦点宫宫干飞化', flying.value.map(t => ({type: t.type, star: t.star, palace_name: t.target_palace, self: t.self_transform})));
      return box;
    },
  };
  groups.forEach((group, i) => {
    const section = append(result, 'section', 'ev-group'); section.id = 'deep-group-' + i; section.tabIndex = -1;
    append(section, 'h4', 'subheading', group);
    const grid = append(section, 'div', 'ev-grid');
    deepResult.findings.filter(f => f.group === group).forEach(f => {
      const card = append(grid, 'article', 'ev-card'); card.id = 'deep-' + f.id;
      append(card, 'h5', 'ev-title', f.title);
      const view = views[f.id] && views[f.id](f);
      if (view) card.append(view);
      if (!view) append(card, 'p', 'ev-observation', f.observation);
      append(card, 'p', 'ev-limit', '适用边界：' + f.limit);
      const more = append(card, 'details', 'ev-more');
      append(more, 'summary', null, '计算字段与规则');
      const fields = append(more, 'dl', 'ev-fields');
      f.evidence.forEach(x => {
        const term = append(fields, 'dt'); append(term, 'code', null, x.path);
        const value = append(fields, 'dd');
        const raw = typeof x.value === 'string' ? x.value : JSON.stringify(x.value);
        append(value, 'code', 'ev-value', raw);
        append(value, 'small', 'ev-hash', 'sha256 ' + x.sha256);
      });
      texts(append(more, 'p', 'ev-rules'), '规则 ID：', f.rule_ids.join('、'));
    });
  });
  append(result,'h4','subheading','内部一致性核查（不等于外部准确率认证）');
  const checks = append(result, 'ul', 'ev-checks'); checks.id = 'deep-checks';
  deepResult.checks.forEach(c => {const item = append(checks, 'li', c.passed ? 'is-pass' : 'is-fail'); append(item, 'b', null, c.passed ? '✓' : '⚠'); append(item, 'span', null, c.meaning);});
  append(result,'h4','subheading','参考来源与适用范围');
  const refs = append(append(result, 'div', 'table-wrap'), 'table', 'data-table ev-refs');
  const refHead = append(append(refs, 'thead'), 'tr'); ['规则', '来源', '适用范围'].forEach(x => append(refHead, 'th', null, x));
  const refBody = append(refs, 'tbody');
  deepResult.references.forEach(ref=>{
    const tr = append(refBody, 'tr');
    append(tr, 'td', null, ref.title);
    // On phones the rows stack, so each stacked cell carries its column name (hidden on wide screens).
    const source = append(tr, 'td'); append(source, 'small', 'ev-cell-label', '来源');
    if(ref.reference.startsWith('https://')){
      const a=append(source,'a',null,'查看公开方法文档 ↗');a.href=ref.reference;a.target='_blank';a.rel='noopener noreferrer';
    } else append(source,'code',null,ref.reference);
    const scope = append(tr, 'td'); append(scope, 'small', 'ev-cell-label', '适用范围'); append(scope, 'span', null, ref.scope);
  });
  const save=append(result,'button','tiny-button','导出带证据的 Markdown ↓');save.type='button';save.id='deep-download';
  save.addEventListener('click',()=>{
    const blob=new Blob([deepResult.markdown],{type:'text/markdown;charset=utf-8'});
    const url=URL.createObjectURL(blob);const a=elt('a');a.href=url;a.download='xuanshu-evidence.md';
    document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);
  });
  deepResult.limitations.forEach(text=>note(result,text));
}

// The report's parts: the four always computed, then the optional ones as cards, each saying what it needs.
const REPORT_BASE = ['时制与节令方法', '四柱与藏干统计', '紫微十二宫与四化', '出生数据与排盘边界审计'];
// One section of the Markdown, from its heading to the next.
function reportMarkdownSection(markdown, heading) {
  const lines = markdown.split('\n'), start = lines.indexOf('## ' + heading);
  if (start < 0) return '';
  const end = lines.findIndex((line, i) => i > start && line.startsWith('## '));
  return lines.slice(start, end < 0 ? undefined : end).join('\n').trim();
}
// A copy that the browser refuses (no clipboard on a plain-http address, say) selects the text instead.
async function reportCopy(button, label, text, region, done) {
  try {await navigator.clipboard.writeText(text); label.textContent = done; announce(calT(done));}
  catch (_) {
    const range = document.createRange(); range.selectNodeContents(region);
    const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range);
    label.textContent = '已选中文字，请按 Ctrl+C 复制'; announce(calT('已选中文字，请按 Ctrl+C 复制'));
  }
  clearTimeout(button.xsReset);
  button.xsReset = setTimeout(() => {if (label.isConnected) label.textContent = label.dataset.idle;}, 2500);
}
// With the hour unknown the report stands on the 12:00 placeholder, so the copies say so first.
const REPORT_HOUR_NOTE = '命盘时辰不详：本报告按 12:00 占位时辰计算，时柱、命宫、身宫与紫微十二宫都不可靠。';
const reportMarkdown = r => (r.xsHourUnknown ? '> ' + REPORT_HOUR_NOTE + '\n\n' : '') + r.markdown;
function renderReport() {
  title(result, '可追溯综合报告', '独立八字、紫微计算 → 可选年干四化和太阳时审计 → Markdown');
  if (!current) {append(result,'p','info-inline','请先生成出生盘，再生成综合报告。');return;}
  // The report is for the chart shown, like the other tools: its guards follow that chart, and a changed birth
  // form takes effect when the chart is cast again.
  const input = currentInput;
  // The settings are left out of print, which keeps only the report itself.
  const setup = append(result, 'div', 'rp-setup');
  append(setup, 'h4', 'subheading', '报告内容');
  const base = append(setup, 'div', 'rp-base');
  append(base, 'span', 'muted', '总是包含');
  REPORT_BASE.forEach(name => append(base, 'span', 'rp-chip', name));
  const modules = append(setup, 'div', 'rp-modules');
  // A card per optional part: a switch or field, what it adds, and why it cannot run when something is missing.
  const card = (id, what) => {
    const box = append(modules, 'div', 'rp-module'); box.id = id;
    const headLine = append(box, 'div', 'rp-module-head');
    append(box, 'p', 'rp-module-what', what).id = id + '-what';
    return {box, headLine, what: id + '-what'};
  };
  // Each switch or field is described by what its card adds and, when shown, what it still needs.
  const describe = (control, ...ids) => control.setAttribute('aria-describedby', ids.join(' '));
  const check = (headLine, id, name, on) => {
    const label = append(headLine, 'label', 'rp-switch');
    const box = append(label, 'input'); box.type = 'checkbox'; box.id = id; box.checked = on;
    append(label, 'b', null, name);
    return box;
  };
  const annual = card('report-module-annual', '把所选农历年的年干四化落到本命十二宫；留空不叠加。');
  append(annual.headLine, 'b', null, '农历年干四化叠加');
  const yearRow = append(annual.box, 'div', 'rp-module-fields inline-control');
  const year = createInput('农历年', 'number', reportDraft.lunar_year === null ? '' : String(reportDraft.lunar_year), yearRow);
  year.min = '1901'; year.max = '2099'; year.id = 'report-year'; year.placeholder = '留空不叠加'; describe(year, annual.what);
  const thisYear = append(yearRow, 'button', 'tiny-button', '今年'); thisYear.type = 'button'; thisYear.id = 'report-year-now';
  const timeCard = card('report-module-time', '同一出生资料按钟表时间、平太阳时、真太阳时各排一次，列出四柱和命宫的差别。');
  const audit = check(timeCard.headLine, 'report-audit', '三套时制审计', reportDraft.include_time_audit && input.longitude !== null);
  describe(audit, timeCard.what);
  // Without a longitude the box stays focusable, so the reason is read with it, but cannot be ticked.
  if (input.longitude === null) {
    audit.setAttribute('aria-disabled', 'true'); timeCard.box.classList.add('is-blocked');
    audit.addEventListener('click', e => e.preventDefault());
    append(timeCard.box, 'p', 'rp-module-need', '当前命盘没有经度，太阳时算不出来；在出生资料里选城市或填经度，重新生成命盘后再勾选。').id = 'report-module-time-need';
    describe(audit, timeCard.what, 'report-module-time-need');
  }
  const luckCard = card('report-module-dayun', '按年干阴阳与性别（或手动指定）定顺逆，报告列出起运年龄和前六步大运干支。');
  const dy = check(luckCard.headLine, 'report-dayun', '十年干支大运', reportDraft.include_dayun);
  const dyRow = append(luckCard.box, 'div', 'rp-module-fields inline-control');
  const dyLabel = append(dyRow, 'label', null, '大运方向');
  const dyselect = append(dyLabel, 'select'); dyselect.id = 'report-dayun-direction';
  [['', '自动'], ['forward', '顺排'], ['reverse', '逆排']].forEach(([v, t]) => {const op = append(dyselect, 'option', null, t); op.value = v;});
  dyselect.value = reportDraft.dayun_direction_override;
  const dyNeed = append(luckCard.box, 'p', 'rp-module-need', '当前命盘没有性别：自动方向排不出，请在这里选顺排、逆排，或填性别后重新生成命盘。'); dyNeed.id = 'report-module-dayun-need';
  describe(dy, luckCard.what, dyNeed.id); describe(dyselect, luckCard.what, dyNeed.id);
  const boundaryCard = card('report-module-boundary', '在出生时刻前后若干分钟内找出四柱、命宫等会变的切换点；留空不包含。');
  append(boundaryCard.headLine, 'b', null, '出生时刻临界地图');
  const bdRow = append(boundaryCard.box, 'div', 'rp-module-fields inline-control');
  const bd = createInput('前后分钟数（1–120）', 'number', String(reportDraft.birth_boundary_minutes), bdRow);
  bd.id = 'report-boundary-radius'; bd.min = '1'; bd.max = '120'; bd.placeholder = '留空不包含'; describe(bd, boundaryCard.what);
  const deepCard = card('report-module-deep', '加入八字与紫微的可追溯观察和交叉核查；每条观察依据的字段、规则编号和适用边界在 JSON 数据页里。');
  const evidenceBox = check(deepCard.headLine, 'report-deep', '证据溯源与跨体系复核', reportDraft.include_deep_evidence);
  describe(evidenceBox, deepCard.what);
  const actions = append(setup, 'div', 'rp-run inline-control');
  const go = append(actions, 'button', null, '生成综合报告'); go.type = 'button'; go.id = 'report-run';
  const plan = append(actions, 'span', 'rp-plan'); plan.id = 'report-plan';
  const error = append(setup, 'p', 'inline-msg'); error.setAttribute('role', 'alert');
  // The cards light up as they are switched on, and the step count follows: two charts and the quality audit,
  // then one step per optional part.
  const refresh = () => {
    const needsDirection = dy.checked && input.gender === 'unspecified' && !dyselect.value;
    dyNeed.hidden = !needsDirection;
    luckCard.box.classList.toggle('is-blocked', needsDirection);
    // A part that cannot run is not counted as a step.
    const on = {annual: year.value.trim() !== '', time: audit.checked, dayun: dy.checked && !needsDirection, boundary: bd.value.trim() !== '', deep: evidenceBox.checked};
    [[annual, on.annual], [timeCard, on.time], [luckCard, on.dayun], [boundaryCard, on.boundary], [deepCard, on.deep]].forEach(([c, v]) => c.box.classList.toggle('is-on', v));
    plan.replaceChildren(); texts(plan, '将运行', ' ', 3 + Object.values(on).filter(Boolean).length, ' ', '个计算步骤');
    // Choices are kept as they are made, so another redraw does not undo them.
    // A box that cannot be ticked for this chart keeps the earlier choice for the next chart.
    Object.assign(reportDraft, {lunar_year: year.value.trim() === '' ? null : Number(year.value),
      include_time_audit: input.longitude === null ? reportDraft.include_time_audit : audit.checked, include_dayun: dy.checked,
      include_deep_evidence: evidenceBox.checked, dayun_direction_override: dyselect.value, birth_boundary_minutes: bd.value.trim()});
  };
  [year, bd].forEach(x => x.addEventListener('input', refresh));
  [audit, dy, evidenceBox, dyselect].forEach(x => x.addEventListener('change', refresh));
  thisYear.addEventListener('click', () => {year.value = String(defaultLunarYear()); refresh();});
  refresh();
  go.addEventListener('click',async()=>{
    if (audit.checked && input.longitude===null){error.textContent='时制审计必须填写出生地经度。';return;}
    const value=year.value.trim();
    const lunar_year=value===''?null:Number(value);
    const boundary_minutes=bd.value.trim()===''?null:Number(bd.value);
    if(boundary_minutes!==null && (!Number.isInteger(boundary_minutes)||boundary_minutes<1||boundary_minutes>120)){
      error.textContent='临界地图分钟数必须为1–120整数';return;
    }
    if(dy.checked && input.gender==='unspecified' && !dyselect.value){error.textContent='大运方向需要指定性别或手动顺逆';return;}
    go.disabled=true;error.textContent='';
    const hourUnknown = currentHourUnknown;
    try {const data=await postForChart('/api/report',{birth:input,lunar_year,
      include_time_audit:audit.checked,include_dayun:dy.checked,include_deep_evidence:evidenceBox.checked,
      dayun_direction_override:dyselect.value||null,birth_boundary_minutes:boundary_minutes});
      // A report for a chart that has since been re-cast is dropped rather than shown under the new one.
      if (data === STALE) return;
      reportResult = data; reportResult.xsHourUnknown = hourUnknown; reportResult.xsBirth = input; render();
      const top = $('#report-doc'); if (top) top.focus();}
    catch(e){error.textContent='生成失败：'+e.message;}
    finally{go.disabled=false;}
  });
  append(setup, 'p', 'field-help', '该报告由确定性规则工具编排生成，展示各步骤来源，不调用外部大语言模型，也不保存到服务器。');
  if (!reportResult) return;
  const r = reportResult;
  const doc = append(result, 'article', 'rp-doc'); doc.id = 'report-doc'; doc.tabIndex = -1;
  doc.setAttribute('aria-labelledby', 'report-doc-title');
  const head = append(doc, 'header', 'rp-head');
  append(head, 'h3', null, '传统历法与命盘 · 可核验计算报告').id = 'report-doc-title';
  const pillars = append(head, 'div', 'rp-pillars');
  ['年柱', '月柱', '日柱', '时柱'].forEach((name, i) => {
    const cell = append(pillars, 'div', 'rp-pillar' + (i === 2 ? ' is-master' : ''));
    append(cell, 'small', null, name);
    const gz = append(cell, 'b'); gz.dataset.noI18n = '';
    if (i === 3 && r.xsHourUnknown) {append(gz, 'span', 'muted', '?'); append(gz, 'span', 'muted', '?'); tip(cell, calT('时辰不详')); return;}
    append(gz, 'span', stemClass(r.overview.pillars[i][0]), r.overview.pillars[i][0]); append(gz, 'span', branchClass(r.overview.pillars[i][1]), r.overview.pillars[i][1]);
  });
  const facts = append(head, 'div', 'rp-head-facts');
  const fact = (label, value, glyph) => {const p = append(facts, 'p'); append(p, 'span', 'muted', label); const b = append(p, 'b'); if (glyph) {b.dataset.noI18n = ''; append(b, 'span', glyph, value);} else b.textContent = value;};
  fact('日主', r.overview.day_master, stemClass(r.overview.day_master));
  fact('命宫', r.xsHourUnknown ? '?' : r.overview.ming_palace, r.xsHourUnknown ? 'muted' : branchClass(r.overview.ming_palace));
  fact('身宫', r.xsHourUnknown ? '?' : r.overview.shen_palace, r.xsHourUnknown ? 'muted' : branchClass(r.overview.shen_palace));
  const birth = r.xsBirth || {};
  meta(head, [(birth.birth_datetime || '').replace('T', ' ') + ' · ' + (birth.timezone || ''), r.system + ' ' + r.version, `${r.tool_trace.length} 次计算步骤`]);
  if (r.xsHourUnknown) append(head, 'p', 'rp-hour-note', REPORT_HOUR_NOTE).id = 'report-hour-note';
  // The steps the server ran, in order, each named by its tool.
  const trace = append(doc, 'ol', 'rp-trace'); trace.id = 'report-trace'; trace.setAttribute('aria-label', '计算步骤');
  r.tool_trace.forEach(step => {
    const li = append(trace, 'li', 'rp-step' + (step.status === 'computed' ? ' is-done' : ''));
    append(li, 'span', 'rp-step-n', String(step.step));
    const name = append(li, 'code', null, step.tool); tip(name, step.engine);
    if (step.status !== 'computed') append(li, 'small', null, step.status);
  });
  const layout = append(doc, 'div', 'rp-layout');
  const toc = append(layout, 'nav', 'rp-toc'); toc.id = 'report-toc'; toc.setAttribute('aria-label', '报告目录');
  append(toc, 'b', null, '目录');
  const tocList = append(toc, 'ol');
  const body = append(layout, 'div', 'rp-body');
  r.sections.forEach((section, i) => {
    const link = append(append(tocList, 'li'), 'a', null, section.title); link.href = '#report-sec-' + i;
    const panel = append(body, 'section', 'rp-section'); panel.id = 'report-sec-' + i; panel.tabIndex = -1;
    panel.setAttribute('aria-labelledby', 'report-sec-' + i + '-title');
    const headRow = append(panel, 'div', 'rp-section-head');
    const heading = append(headRow, 'h4', 'rp-section-title');
    append(heading, 'span', 'rp-section-n', String(i + 1)); append(heading, 'span', null, section.title).id = 'report-sec-' + i + '-title';
    const copy = append(headRow, 'button', 'tiny-button rp-copy'); copy.type = 'button'; copy.id = 'report-copy-' + i;
    const copyLabel = append(copy, 'span', null, '复制本节'); copyLabel.dataset.idle = '复制本节';
    copy.append(' '); append(copy, 'span', 'visually-hidden', section.title);
    copy.addEventListener('click', () => reportCopy(copy, copyLabel, reportMarkdownSection(r.markdown, section.title), panel, '已复制'));
    const ul = append(panel, 'ul', 'rp-facts');
    section.facts.forEach(f => append(ul, 'li', null, f));
    // Module names read as code; anything else in the sources (a published note, a document) as text.
    const source = append(panel, 'p', 'rp-source');
    append(source, 'span', 'muted', '来源');
    section.provenance.split(' / ').forEach(part => {const text = part.trim(); append(source, /^[\w]+(\.[\w]+)+$/.test(text) ? 'code' : 'span', 'rp-source-part', text);});
  });
  // The terms the report uses: what each is and how XuanShu computes it, after the numbered sections.
  if ((r.glossary || []).length) {
    const n = r.sections.length + 1;
    const link = append(append(tocList, 'li'), 'a', null, '术语解释'); link.href = '#report-glossary';
    const panel = append(body, 'section', 'rp-section rp-glossary'); panel.id = 'report-glossary'; panel.tabIndex = -1;
    panel.setAttribute('aria-labelledby', 'report-glossary-title');
    const headRow = append(panel, 'div', 'rp-section-head');
    const heading = append(headRow, 'h4', 'rp-section-title');
    append(heading, 'span', 'rp-section-n', String(n)); append(heading, 'span', null, '术语解释').id = 'report-glossary-title';
    const copy = append(headRow, 'button', 'tiny-button rp-copy'); copy.type = 'button'; copy.id = 'report-copy-glossary';
    const copyLabel = append(copy, 'span', null, '复制本节'); copyLabel.dataset.idle = '复制本节';
    copy.append(' '); append(copy, 'span', 'visually-hidden', '术语解释');
    copy.addEventListener('click', () => reportCopy(copy, copyLabel, reportMarkdownSection(r.markdown, '术语解释'), panel, '已复制'));
    append(panel, 'p', 'field-help', '只说明报告里出现的术语是什么、玄枢怎么算，不写断语；详细规则见各自的规则文档。');
    const terms = append(panel, 'dl', 'rp-terms'); terms.id = 'report-terms';
    // Headwords carry their own English and Japanese names: a bare term such as 流年 or 起运 is translated for
    // other places on the page. The Chinese term stays beside a translated headword.
    const lang = document.documentElement.lang;
    r.glossary.forEach(x => {
      const row = append(terms, 'div', 'rp-term');
      const dt = append(row, 'dt');
      const named = (lang === 'en' && x.term_en) || (lang === 'ja' && x.term_ja);
      append(dt, 'b', null, named || calT(x.term)).dataset.noI18n = '';
      if (named && named !== x.term) {const zh = append(dt, 'span', 'rp-term-zh', x.term); zh.dataset.noI18n = ''; zh.lang = 'zh-CN';}
      append(dt, 'span', 'rp-term-system', x.system);
      if (x.aliases.length) texts(append(dt, 'small', 'muted'), '又称', ' ', x.aliases.join('、'));
      const dd = append(row, 'dd');
      append(dd, 'p', null, x.definition);
      const how = append(dd, 'p', 'rp-term-how');
      append(how, 'span', 'rp-term-label', '玄枢怎么算'); how.append(' ');
      append(how, 'span', null, x.in_xuanshu); how.append(' ');
      const doc = append(how, 'code', 'rp-term-doc', x.rule_doc.replace('docs/rules/', '')); tip(doc, x.rule_doc);
    });
    const source = append(panel, 'p', 'rp-source');
    append(source, 'span', 'muted', '来源'); append(source, 'span', 'rp-source-part', 'docs/rules/glossary.md');
  }
  // Moving through the contents keeps the keyboard with the section it opens.
  toc.addEventListener('click', e => {
    const link = e.target.closest('a'); if (!link) return;
    e.preventDefault();
    const target = $(link.getAttribute('href'));
    target.scrollIntoView({block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
    target.focus({preventScroll: true});
  });
  const tools = append(result, 'div', 'rp-actions');
  const download=append(tools,'button','tiny-button','下载 Markdown 报告 ↓');download.type='button';download.id='report-download';
  download.addEventListener('click',()=>downloadBlob(new Blob([reportMarkdown(r)],{type:'text/markdown;charset=utf-8'}),'xuanshu-report.md'));
  const copyAll = append(tools, 'button', 'tiny-button'); copyAll.type = 'button'; copyAll.id = 'report-copy';
  const copyAllLabel = append(copyAll, 'span', null, '复制全文 Markdown'); copyAllLabel.dataset.idle = '复制全文 Markdown';
  copyAll.addEventListener('click', () => reportCopy(copyAll, copyAllLabel, reportMarkdown(r), doc, '已复制全文'));
  const printIt = append(tools, 'button', 'tiny-button', '打印 / 存为 PDF'); printIt.type = 'button'; printIt.id = 'report-print';
  printIt.addEventListener('click', () => window.print());
  r.limitations.forEach(x=>note(result,x));
}
// When their columns do not fit, the decade, year, month and hour tables stack each row (.dy-stack.is-stacked in the
// stylesheet): the relations and the stars take lines of their own under the pillar instead of columns a few characters
// wide that stretch a row to hundreds of pixels and scroll sideways. The 神煞 rules, today's pillars and the year's four
// transformations stack the same way. The roles keep the rows a table to screen readers
// once they no longer display as table rows; a label a stacked cell needs, its column head being out of sight, is hidden
// from them as the head says it already.
function stackTable(table) {
  table.classList.add('dy-stack'); table.setAttribute('role', 'table');
  table.querySelectorAll('thead,tbody').forEach(group => group.setAttribute('role', 'rowgroup'));
  table.querySelectorAll('tr').forEach(row => row.setAttribute('role', 'row'));
  table.querySelectorAll('th').forEach(cell => cell.setAttribute('role', cell.scope === 'col' ? 'columnheader' : 'rowheader'));
  table.querySelectorAll('td').forEach(cell => cell.setAttribute('role', 'cell'));
}
// Whether the columns fit is the table's own question, not the screen's: the side panel, the language and the content
// all change it (with the panel back on a small laptop the column is narrower than on a large phone, and English needs
// more room than Chinese). So each is laid out as a table and measured, and stacked when it overflows its wrapper, when
// its stars column (or the cell marked dy-fit-cell) is left under 7.5em (or its data-fit-em), where the text wraps a
// few characters to a line and stretches every row; within one task, so nothing is painted in between. A short label
// spelled out in letters (a dy-short cell: Direct Resource (Zheng Yin) for 正印) keeps a width of its own in the CSS,
// so the stars wrap instead of it, and a table that then overflows is stacked.
function fitStacks() {
  document.querySelectorAll('table.dy-stack').forEach(table => {
    table.classList.remove('is-stacked');
    const cell = table.querySelector('tbody td.dy-star-cell, tbody td.dy-fit-cell');
    const narrow = cell && cell.getBoundingClientRect().width < parseFloat(table.dataset.fitEm || '7.5') * parseFloat(getComputedStyle(cell).fontSize);
    table.classList.toggle('is-stacked', narrow || table.offsetWidth > table.parentElement.clientWidth + 1);
  });
}
function stackLabel(cell, text) {
  const label = append(cell, 'span', 'dy-stack-label', text + ' '); label.setAttribute('aria-hidden', 'true');
  return cell;
}
function stackStars(tr, text) {
  stackLabel(append(tr, 'td', 'dy-star-cell'), '神煞').append(text);
}
function renderDayun() {
  title(result, '八字大运十年干支', '年干阴阳 + 性别或手动顺逆 · 十二节令 · 三日折一岁');
  append(result, 'p', 'info-inline', '只计算传统干支和名义起运年龄，公历时间为均值年近似，绝非对人生事件的预测。');
  if (!current) {append(result, 'p', 'info-inline', '请先生成出生盘。'); return;}
  // With a gender (or a direction picked) the periods of the chart shown are worked out on opening, and again
  // whenever another chart is cast; the button applies a changed count or direction.
  const request = () => ({birth: currentInput, periods: dayunDraft.periods, direction_override: dayunDraft.direction_override || null, hour_unknown: currentHourUnknown, include_years: true});
  const ready = currentInput.gender !== 'unspecified' || !!dayunDraft.direction_override;
  if (ready && dayunKey !== JSON.stringify(request()) && !dayunPending) {
    const body = request(), key = JSON.stringify(body);
    dayunPending = true; dayunError = '';
    postJSON('/api/dayun', body).then(data => {dayunResult = data; dayunKey = key; dayunPick = null;})
      .catch(err => {dayunResult = null; dayunError = '计算失败：' + err.message; dayunKey = key;})
      .finally(() => {dayunPending = false; if (active === 'dayun') render();});
  }
  const row=append(result,'div','inline-control');
  const periods=createInput('显示运柱数量（1–12）','number',String(dayunDraft.periods),row);
  periods.id='dayun-periods';periods.min='1';periods.max='12';
  const label=append(row,'label',null,'顺逆方向（默认年干/性别）');
  const direction=append(label,'select');direction.id='dayun-direction';
  [['','按传统规则自动'],['forward','手动顺排'],['reverse','手动逆排']].forEach(([key,val])=>{const op=append(direction,'option',null,val);op.value=key;});
  direction.value=dayunDraft.direction_override;
  keepTyped(periods,direction);
  const run=append(row,'button',null,'计算大运');run.id='dayun-run';run.type='button';
  run.disabled = dayunPending;
  const error=append(result,'p','inline-msg', dayunError);
  run.addEventListener('click', ()=>{
    const count=Number(periods.value);if(!Number.isInteger(count)||count<1||count>12){error.textContent='显示数量必须是1–12的整数';return;}
    if(currentInput.gender==='unspecified' && !direction.value){error.textContent='性别未指定时需要手动选择顺逆。';return;}
    dayunDraft={periods:count,direction_override:direction.value};
    dayunKey=null; render();
  });
  if (!ready) {append(result, 'p', 'field-help', '命盘没有填性别：选好顺排或逆排后点「计算大运」。'); return;}
  if (dayunPending) append(result, 'p', 'field-help', '正在按当前命盘计算大运…');
  if(!dayunResult || dayunKey !== JSON.stringify(request())){if (dayunPending) loadingGhost(result, 'strip', 'table'); return;}
  const d=dayunResult, o=dayunOpenness(), parts=startAgeParts(d);
  meta(result,[`年柱 ${d.natal_year_pillar}`,`月柱 ${d.natal_month_pillar}`,`方向 ${d.direction==='forward'?'顺排':'逆排'}`,o.sequence?'起运随时辰而定':`起运约 ${parts.years}岁 ${parts.months}个月`]);
  // The decade this civil year belongs to, by the usual listing (the years under each decade, and the BaZi page's
  // luck strip, count it the same way): the year a decade begins in belongs to it whole.
  const now=localToday(), thisYear=Number(now.slice(0,4)), yearOf=s=>Number(s.slice(0,4));
  const live=d.periods.findIndex(x=>yearOf(x.approx_start_local)<=thisYear&&thisYear<yearOf(x.approx_end_local_exclusive));
  const pick = d.periods.find(x => x.sequence === dayunPick) || d.periods[Math.max(live, 0)];
  dayunStart(d, o, parts);
  // With the month pillar open the sequence itself is one of two, so only the table below is shown, said to be so.
  if (!o.sequence) {dayunAxis(d, live, pick, now); dayunDetail(d, pick, pick === d.periods[live], o, now);}
  append(result, 'h4', 'subheading', '全部大运');
  if (o.sequence) append(result, 'p', 'field-help', '这张表按 12:00 占位排出，只是其中一种可能。');
  if (o.day) append(result, 'p', 'field-help', '日柱随时辰而定，日主未定，十神和星运暂不标注。');
  const table=append(append(result,'div','table-wrap'),'table','data-table dayun-table'); table.id='dayun-table';
  append(table, 'caption', 'visually-hidden', '全部大运');
  const head=append(append(table,'thead'),'tr');['次序','十年干支',...(o.day?[]:['十神','星运']),'名义起始年龄','近似起始公历','与原局','神煞'].forEach(x=>{append(head,'th',null,x).scope='col';});
  const body=append(table,'tbody');
  d.periods.forEach((x,i)=>{
    const n=settledInteractions(x.natal_interactions, o);
    const tr=append(body,'tr',i===live?'is-current':null);append(tr,'td','dy-seq',String(x.sequence));
    if(i===live)tr.setAttribute('aria-current','date');
    const cell=append(tr,'td'),pillar=append(cell,'span','pillar-cell');append(pillar,'span',stemClass(x.pillar[0]),x.pillar[0]);append(pillar,'span',branchClass(x.pillar[1]),x.pillar[1]);
    if(i===live)append(cell,'span','dayun-now','约当前');
    if(!o.day){append(tr,'td','dy-short',n?n.ten_god_of_stem:'—');append(tr,'td','dy-short',n?n.growth_stage:'—');}
    stackLabel(append(tr,'td'),'起运').append(x.approx_start_age_years.toFixed(2));append(tr,'td','nowrap',x.approx_start_local.slice(0,10));
    const marks=append(tr,'td','dy-mark-cell');if(n){natalMarks(marks,n);tip(marks,natalText(n));}if(!marks.childNodes.length)marks.textContent='—';
    stackStars(tr,o.stars?'随时辰而定':(n&&n.shensha||[]).map(s=>s.name).join('、')||'—');});
  stackTable(table);
  d.limitations.forEach(x=>note(result,x));
}
// With the hour unknown, which pillars the noon placeholder leaves open (unsettledPillars) and what follows for the
// decades: a jie that day changes the month pillar (立春 the year pillar too) and with it the whole sequence; a day
// that can change takes the day master, and with it the ten gods, the growth stages and the day-based stars.
function dayunOpenness() {
  const open = currentHourUnknown ? unsettledPillars(current.bazi) : new Set();
  return {open, sequence: open.has('month') || open.has('year'), day: open.has('day'), stars: shenshaUnsettled(current.bazi)};
}
// A luck or year pillar's facts kept to what the hour does not change: relations with open pillars are left out.
function settledInteractions(n, o) {
  if (!n || !o.open.size) return n;
  return {...n, growth_stage: o.day ? null : n.growth_stage, void_of: n.void_of.filter(k => !o.open.has(k)),
    stem_relations: n.stem_relations.filter(r => !o.open.has(r.pillar)), branch_relations: n.branch_relations.filter(r => !o.open.has(r.pillar)),
    branch_groups: n.branch_groups.filter(g => !g.pillars.some(k => o.open.has(k))), shensha: o.stars ? [] : n.shensha};
}
// The starting age in years, months and whole days: 30 days carry into a month, as 12 months carry into a year.
function startAgeParts(d) {
  const raw = d.start_age_traditional_parts;
  let {years, months} = raw, days = Math.round(raw.days_nominal_30_day_month);
  if (days >= 30) {days = 0; months += 1;}
  if (months >= 12) {months = 0; years += 1;}
  return {years, months, days};
}
// How the starting age comes about: the birth and the month-boundary solar term it is counted to (back to the last
// one when the decades run in reverse, on to the next when forward), the days between, and three days to a year.
function dayunStart(d, o, parts) {
  const box = append(result, 'section', 'dy-start');
  append(box, 'h4', 'subheading', '起运怎么算');
  if (o.sequence) {
    const b = current.bazi, day = currentInput.birth_datetime.slice(0, 10);
    const jie = [b.jie_boundaries.previous, b.jie_boundaries.next].find(j => j.instant.slice(0, 10) === day);
    const warn = append(box, 'div', 'dy-warn'); warn.id = 'dayun-open'; warn.setAttribute('role', 'note');
    if (jie) {const line = append(warn, 'p'); texts(line, '出生当天交节', '：', jie.name, ' '); append(line, 'b', null, jie.instant.slice(11, 19));}
    append(warn, 'p', null, o.open.has('year')
      ? '时辰不详：生在交节之前或之后，年柱和月柱都不同，大运的顺逆、干支和起运岁数也都跟着变。下面的大运表按 12:00 占位排出，只是其中一种可能；补上出生时辰后才有起运推算和人生时间轴。'
      : '时辰不详：生在交节之前或之后，月柱不同，大运的干支和起运岁数也都跟着变。下面的大运表按 12:00 占位排出，只是其中一种可能；补上出生时辰后才有起运推算和人生时间轴。');
    return;
  }
  const reverse = d.direction !== 'forward';
  // To the second, with the zone offset each was given in (a daylight-saving year shows +09:00 in China).
  const node = (name, at) => {const n = elt('div', 'dy-node'); append(n, 'b', null, name); append(n, 'small', null, at.replace('T', ' ').replace(/\.\d+/, '')); return n;};
  const birth = node('出生', d.birth_datetime), jie = node(d.nearest_jie_used.name, d.nearest_jie_used.instant);
  if (currentHourUnknown) {const at = birth.querySelector('small'); at.textContent = ''; texts(at, d.birth_datetime.slice(0, 10), ' ', '时辰不详（按 12:00）');}
  const calc = append(box, 'div', 'dy-calc');
  const gap = elt('div', 'dy-gap');
  append(gap, 'span', null, reverse ? '逆排：往前数到上一个节' : '顺排：往后数到下一个节');
  countText(append(gap, 'b'), d.birth_to_jie_days.toFixed(2), ' 天');
  calc.append(...(reverse ? [jie, gap, birth] : [birth, gap, jie]));
  const f = append(box, 'p', 'dy-formula');
  countText(f, d.birth_to_jie_days.toFixed(2), ' 天'); f.append(' ÷ 3 = '); texts(f, d.start_age_years_nominal.toFixed(2), ' 年', ' ≈ ');
  const age = append(f, 'b');
  countText(age, parts.years, ' 岁'); age.append(' '); countText(age, parts.months, ' 个月'); age.append(' '); countText(age, parts.days, ' 天');
  f.append(' → '); texts(f, '起运约', ' '); append(f, 'span', 'nowrap', d.approx_first_start_local.slice(0, 16).replace('T', ' '));
  append(box, 'p', 'field-help', '三日折一岁：出生到节令每 3 天算 1 年，1 天算 4 个月，1 个时辰算 10 天；公历日期按每年 365.2425 天推算，是近似值。');
  if (currentHourUnknown) append(box, 'p', 'field-help', '时辰不详：按 12:00 占位计算；出生时间前后差 12 小时，起运最多差约 2 个月。');
}
// The life on one line: from birth to the end of the last decade shown, a band before the first decade begins and
// one per decade, with today marked. A decade opens its detail below.
function dayunAxis(d, live, pick, now) {
  const day = s => Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10));
  const t0 = day(d.birth_datetime), t1 = day(d.periods[d.periods.length - 1].approx_end_local_exclusive);
  const at = s => ((day(s) - t0) / (t1 - t0) * 100).toFixed(3) + '%';
  const wrap = append(result, 'div', 'dy-axis-wrap');
  const axis = append(wrap, 'div', 'dy-axis'); axis.id = 'dayun-axis';
  axis.setAttribute('role', 'group'); axis.setAttribute('aria-label', '大运时间轴');
  if (now >= d.birth_datetime.slice(0, 10) && now < d.periods[d.periods.length - 1].approx_end_local_exclusive.slice(0, 10)) {
    // Drawn above and below the bands only, so the labels of the decade it falls in stay readable.
    const mark = append(axis, 'div', 'dy-today'); mark.style.left = at(now);
    texts(append(mark, 'small'), '今天');
  }
  // One column per span of days, from birth to each decade's start and on to the last decade's end, so the bands
  // stay in proportion to the years while each grows as tall as its labels need.
  const edges = [t0, ...d.periods.map(x => day(x.approx_start_local)), t1];
  axis.style.gridTemplateColumns = edges.slice(1).map((t, i) => 'minmax(0,' + Math.max(0, (t - edges[i]) / 864e5) + 'fr)').join(' ');
  append(axis, 'div', 'dy-band dy-before');
  append(axis, 'small', 'dy-before-label', '起运前');
  d.periods.forEach((x, i) => {
    const band = append(axis, 'button', 'dy-band dy-decade' + (x === pick ? ' is-picked' : '') + (i === live ? ' is-now' : ''));
    band.type = 'button'; band.id = 'dayun-band-' + x.sequence; band.setAttribute('aria-pressed', String(x === pick));
    band.style.setProperty('--band', 'var(--' + stemClass(x.pillar[0]).slice(3) + ')');  // the decade stem's phase along the top
    if (i === live) band.setAttribute('aria-current', 'date');
    const gz = append(band, 'b', 'dy-band-gz'); gz.dataset.noI18n = '';
    append(gz, 'span', stemClass(x.pillar[0]), x.pillar[0]); append(gz, 'span', branchClass(x.pillar[1]), x.pillar[1]);
    append(band, 'small', null, x.approx_start_local.slice(0, 4));
    texts(append(band, 'small', 'dy-band-age'), x.approx_start_age_years.toFixed(1), ' 岁');
    band.addEventListener('click', () => {
      dayunPick = x.sequence; render();
      const back = $('#dayun-band-' + x.sequence); if (back) back.focus();
      announce(x.pillar + ' 大运 · ' + x.approx_start_local.slice(0, 4) + '–' + x.approx_end_local_exclusive.slice(0, 4));
    });
  });
  // On a narrow screen the axis scrolls sideways: a newly picked decade is brought into view, and a redraw with the
  // same one keeps where the reader scrolled to.
  const key = dayunKey + '#' + pick.sequence, shown = $('#dayun-band-' + pick.sequence);
  if (shown && wrap.scrollWidth > wrap.clientWidth) {
    wrap.scrollLeft = dayunAxisScroll && dayunAxisScroll.key === key ? dayunAxisScroll.left : shown.offsetLeft + shown.offsetWidth / 2 - wrap.clientWidth / 2;
  }
  wrap.addEventListener('scroll', () => {dayunAxisScroll = {key, left: wrap.scrollLeft};}, {passive: true});
}
// One decade in full: its stem and the stems hidden in its branch with their ten gods, the growth stages, the
// relations it forms with the natal pillars, its stars with the rule they come from, and its years one by one.
function dayunDetail(d, x, isNow, o, now) {
  const n = settledInteractions(x.natal_interactions, o), b = current.bazi;
  const box = append(result, 'section', 'dy-detail'); box.id = 'dayun-detail';
  box.setAttribute('aria-labelledby', 'dayun-detail-title');
  const heading = append(box, 'h4', 'visually-hidden'); heading.id = 'dayun-detail-title';
  texts(heading, '所选大运', ' ', x.pillar);
  const head = append(box, 'div', 'dy-detail-head');
  const gz = append(head, 'b', 'dy-detail-gz'); gz.dataset.noI18n = '';
  append(gz, 'span', stemClass(x.pillar[0]), x.pillar[0]); append(gz, 'span', branchClass(x.pillar[1]), x.pillar[1]);
  const facts = append(head, 'dl', 'dy-facts');
  const fact = (label, ...parts) => {const item = append(facts, 'div'); append(item, 'dt', null, label); return texts(append(item, 'dd'), ...parts);};
  const order = fact('次序', x.sequence);
  if (isNow) append(order, 'small', 'dayun-now', '约当前');
  fact('名义年龄', x.approx_start_age_years.toFixed(1), ' – ', x.approx_end_age_years.toFixed(1), ' 岁');
  fact('近似公历', x.approx_start_local.slice(0, 10), ' – ', x.approx_end_local_exclusive.slice(0, 10));
  // This civil year is listed under the decade it begins in; before the change date it is still the previous one.
  const change = x.approx_start_local.slice(0, 10);
  if (isNow && now < change) texts(append(box, 'p', 'field-help dy-change'), '交运约在', ' ', change, '：', '按常见排法，交运当年整年记在这步大运下；在这之前的几个月实际仍在上一步大运。');
  if (!n) return;
  if (!o.day) fact('十神', n.ten_god_of_stem);
  const hidden = fact('藏干');
  n.hidden_stems.forEach((h, i) => {
    if (i) hidden.append(' ');
    const item = append(hidden, 'span', 'dy-hidden');
    append(item, 'b', stemClass(h.stem), h.stem).dataset.noI18n = ''; if (!o.day) append(item, 'small', null, h.ten_god);
  });
  if (!o.day) fact('星运', n.growth_stage);
  fact('自坐', n.self_stage); fact('纳音', n.na_yin);
  const chips = append(box, 'div', 'dy-chips');
  const chip = (kind, ...parts) => texts(append(chips, 'span', 'dy-chip link-' + kind), ...parts);
  n.stem_relations.forEach(r => chip(r.labels.includes('相冲') ? 'clash' : 'combine', nameMap[r.pillar], ' ', r.stem, '：', r.labels.map(l => l === '相冲' ? x.pillar[0] + r.stem + l : l).join('·')));
  n.branch_relations.forEach(r => chip(LINK_CLASS[r.labels[0]] || 'same', nameMap[r.pillar], ' ', r.branch, '：', x.pillar[1] + r.branch, ' ', r.labels.join('·')));
  n.branch_groups.forEach(g => chip('combine', g.branches, ' ', g.kind === '三合' ? '三合局' : '三会方', '（', g.element, '）'));
  n.void_of.forEach(v => chip('void', v === 'day' ? '落日空' : '落年空'));
  if (!chips.childNodes.length) append(chips, 'span', 'muted', '与原局没有冲合刑害');
  if (o.stars) {const stars = append(box, 'p', 'dy-stars'); append(stars, 'span', 'muted', '神煞'); append(stars, 'span', null, '随时辰而定');}
  else if ((n.shensha || []).length) {
    const rules = new Map((d.shensha_rules || []).map(r => [r.name, r]));
    const stars = append(box, 'p', 'dy-stars');
    append(stars, 'span', 'muted', '神煞');
    n.shensha.forEach(sh => {
      const item = append(stars, 'span', 'dy-star', sh.name);
      const rule = rules.get(sh.name); if (rule) tip(item, rule.rule + ' · ' + rule.source);
      sh.by.forEach(by => {const why = append(item, 'small'); why.append(' '); texts(why, SHENSHA_BASIS[by.basis] || by.basis, ' ', by.value);});
    });
  }
  if (!(x.years || []).length) return;
  const birthYear = b.lunar_date ? b.lunar_date.year : Number(d.birth_datetime.slice(0, 4)), thisYear = Number(now.slice(0, 4));
  const inDecade = year => x.years.some(y => y.year === year);
  const shown = dayunMonths && dayunMonths.key === dayunKey && inDecade(dayunMonths.year) ? dayunMonths : null;
  const loading = dayunMonthsLoad && dayunMonthsLoad.key === dayunKey && inDecade(dayunMonthsLoad.year) ? dayunMonthsLoad : null;
  const hint = append(box, 'div', 'dy-years-hint dy-hint-row');
  append(hint, 'p', 'field-help', '点年份可展开这一年的十二个流月。');
  if (isNow && thisYear <= FLOW_MONTH_LAST_YEAR) {
    const jump = append(hint, 'button', 'tiny-button dy-today-jump', '展开今天'); jump.type = 'button'; jump.id = 'dayun-today';
    tip(jump, '一次展开今天所在的流月、流日和十二时辰');
    if (loading && loading.today) jump.setAttribute('aria-busy', 'true');
    jump.addEventListener('click', dayunToday);
  }
  const wrap = append(box, 'div', 'table-wrap');
  const table = append(wrap, 'table', 'data-table dy-years'); table.id = 'dayun-years';
  append(table, 'caption', 'visually-hidden', '这步大运里的流年');
  const th = append(append(table, 'thead'), 'tr');
  ['流年', '干支', ...(o.day ? [] : ['十神']), '虚龄', ...(o.day ? [] : ['星运']), '与原局', '神煞'].forEach(t => {append(th, 'th', null, t).scope = 'col';});
  const tbody = append(table, 'tbody');
  x.years.forEach(y => {
    const tr = append(tbody, 'tr', y.year === thisYear ? 'is-current' : null);
    if (y.year === thisYear) tr.setAttribute('aria-current', 'date');
    const first = append(tr, 'th'); first.scope = 'row';
    if (y.year > FLOW_MONTH_LAST_YEAR) first.textContent = String(y.year);
    else {
      const open = append(first, 'button', 'dy-year-toggle', String(y.year)); open.type = 'button'; open.id = 'dayun-year-' + y.year;
      // While another year loads its placeholder stands where the months were: nothing is expanded then.
      const expanded = !loading && !!shown && shown.year === y.year;
      open.setAttribute('aria-expanded', String(expanded));
      if (expanded) open.setAttribute('aria-controls', 'dayun-months');
      if (loading && loading.year === y.year) open.setAttribute('aria-busy', 'true');
      tip(open, '展开这一年的十二个流月');
      open.addEventListener('click', () => dayunMonthsToggle(y.year));
    }
    const cell = append(tr, 'td'), pair = append(cell, 'span', 'pillar-cell');
    append(pair, 'span', stemClass(y.pillar[0]), y.pillar[0]); append(pair, 'span', branchClass(y.pillar[1]), y.pillar[1]);
    const ys = settledInteractions(y, o);
    if (!o.day) append(tr, 'td', 'dy-short', ys.ten_god_of_stem);
    stackLabel(append(tr, 'td'), '虚龄').append(String(y.year - birthYear + 1));
    if (!o.day) append(tr, 'td', 'dy-short', ys.growth_stage);
    const marks = append(tr, 'td', 'dy-mark-cell'); natalMarks(marks, ys); tip(marks, natalText(ys)); if (!marks.childNodes.length) marks.textContent = '—';
    stackStars(tr, o.stars ? '随时辰而定' : (ys.shensha || []).map(s => s.name).join('、') || '—');
  });
  stackTable(table);
  append(box, 'p', 'field-help', '与原局一栏：冲月是与月柱六冲，合、刑、害同理，同是同支；日空、年空是落在日柱或年柱的旬空，悬停可看全部关系。流年以立春换年，虚龄从农历出生年起算。只列关系与标签，不判断吉凶。');
  const failed = dayunMonthsError && dayunMonthsError.key === dayunKey && inDecade(dayunMonthsError.year) ? dayunMonthsError : null;
  if (failed) append(box, 'p', 'inline-msg', failed.text);
  if (loading) loadingGhost(box, 'table');
  else if (shown) dayunMonthTable(box, shown, o);
}
// The twelve months of one year under the decade's years: each from the jie that opens it, read against the natal
// chart like the years. Fetched when a year is opened; opening it again closes it.
function dayunMonthsToggle(year) {
  const key = dayunKey;
  // A reply still out for a month's days or a day's hours is dropped with it.
  dayunMonthsError = dayunDaysError = dayunDaysLoad = dayunHoursError = dayunHoursLoad = null;
  if (dayunMonths && dayunMonths.key === key && dayunMonths.year === year) {dayunMonths = null; dayunRefocus('dayun-year-' + year); return;}
  if (dayunMonthsLoad && dayunMonthsLoad.key === key && dayunMonthsLoad.year === year) return;  // already on its way
  const load = dayunMonthsLoad = {key, year};
  dayunRefocus('dayun-year-' + year);
  postJSON('/api/dayun', {...JSON.parse(key), periods: 1, include_years: false, month_year: year})
    // Only the request made last counts: a reply to an earlier one (another year, or the chart before) is dropped.
    .then(data => {if (dayunMonthsLoad === load && dayunKey === key) dayunMonths = {key, year, pillar: data.flow_months.year_pillar, months: data.flow_months.months};})
    .catch(err => {if (dayunMonthsLoad === load) dayunMonthsError = {key, year, text: '流月计算失败：' + err.message};})
    .finally(() => {if (dayunMonthsLoad === load) dayunMonthsLoad = null; if (active === 'dayun') dayunRefocus('dayun-year-' + year);});
}
// The days of one of those months, opened from its row the same way.
function dayunDaysToggle(year, month) {
  const key = dayunKey, id = 'dayun-month-' + month;
  const same = x => x && x.key === key && x.year === year && x.month === month;
  dayunDaysError = dayunHoursError = dayunHoursLoad = null;  // and a reply still out for a day's hours
  if (same(dayunDays)) {dayunDays = null; dayunRefocus(id); return;}
  if (same(dayunDaysLoad)) return;  // already on its way
  const load = dayunDaysLoad = {key, year, month};
  dayunRefocus(id);
  postJSON('/api/dayun', {...JSON.parse(key), periods: 1, include_years: false, month_year: year, day_month: month})
    .then(data => {
      if (dayunDaysLoad !== load || dayunKey !== key) return;
      const m = data.flow_months.months[month - 1];
      dayunDays = {key, year, month, jie: m.jie, pillar: m.pillar, days: m.days};
    })
    .catch(err => {if (dayunDaysLoad === load) dayunDaysError = {key, year, month, message: err.message};})
    .finally(() => {if (dayunDaysLoad === load) dayunDaysLoad = null; if (active === 'dayun') dayunRefocus(id);});
}
// Today's date and the minute of the day by the clock of the birth zone, which the flow months, days and hours are
// worked in: a browser elsewhere may already be on another day. The browser's own clock if the zone is not known.
function flowNow() {
  const now = new Date();
  try {
    const zone = JSON.parse(dayunKey).birth.timezone;
    const parts = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {timeZone: zone, year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hourCycle: 'h23'}).formatToParts(now).map(part => [part.type, part.value]));
    return {date: parts.year + '-' + parts.month + '-' + parts.day, minute: Number(parts.hour) % 24 * 60 + Number(parts.minute)};
  } catch (e) {
    return {date: localToday(), minute: now.getHours() * 60 + now.getMinutes()};
  }
}
// The hours of one of those days, opened from its card the same way.
function dayunHoursToggle(date) {
  const key = dayunKey, id = 'dayun-day-' + date;
  const same = x => x && x.key === key && x.date === date;
  dayunHoursError = null; dayunDayCursor = date;
  if (same(dayunHours)) {dayunHours = null; dayunRefocus(id); return;}
  if (same(dayunHoursLoad)) return;  // already on its way
  const load = dayunHoursLoad = {key, date};
  dayunRefocus(id);
  postJSON('/api/dayun', {...JSON.parse(key), periods: 1, include_years: false, hour_date: date})
    .then(data => {if (dayunHoursLoad === load && dayunKey === key) dayunHours = {key, ...data.flow_hours};})
    .catch(err => {if (dayunHoursLoad === load) dayunHoursError = {key, date, message: err.message};})
    .finally(() => {if (dayunHoursLoad === load) dayunHoursLoad = null; if (active === 'dayun') dayunRefocus(id);});
}
// Open the chain down to today in one go: the year today falls in (before Lichun's day, the one before), the month of that
// year today falls in, its days and today's hours; then bring today's card into view. Opening another year meanwhile wins.
// The year and the month are picked by today's date in the birth zone, the rule the day cards are listed by: the day of a
// jie belongs to the new month whole. A flow year before the decade's first (January of its first year) shows that decade.
function dayunToday() {
  const key = dayunKey, today = flowNow().date;
  if (dayunMonthsLoad && dayunMonthsLoad.today && dayunMonthsLoad.key === key) return;  // already on its way
  const start = Number(today.slice(0, 4)), load = dayunMonthsLoad = {key, year: start, today: true};
  const live = () => dayunMonthsLoad === load && dayunKey === key;
  const ask = extra => postJSON('/api/dayun', {...JSON.parse(key), periods: 1, include_years: false, ...extra});
  dayunMonthsError = dayunDaysError = dayunDaysLoad = dayunHoursError = dayunHoursLoad = null;
  dayunRefocus('dayun-today');
  ask({month_year: load.year})
    .then(data => !live() || today >= data.flow_months.months[0].start_local.slice(0, 10) || load.year <= 1901 ? data
      : ask({month_year: --load.year}))
    .then(data => {
      if (!live()) return null;
      const months = data.flow_months.months;
      const month = [...months].reverse().find(m => m.start_local.slice(0, 10) <= today) || months[0];
      const decade = dayunResult.periods.find(p => (p.years || []).some(y => y.year === load.year));
      // Before Lichun in the year the first decade begins, today's flow year is listed under no decade.
      if (!decade) throw new Error('今天所在的流年早于第一步大运，大运页没有列出这一年');
      dayunPick = decade.sequence;
      return ask({month_year: load.year, day_month: month.month, hour_date: today});
    })
    .then(data => {
      if (!data || !live()) return;
      const flow = data.flow_months, month = flow.months.find(m => m.days);
      dayunMonths = {key, year: load.year, pillar: flow.year_pillar, months: flow.months};
      dayunDays = {key, year: load.year, month: month.month, jie: month.jie, pillar: month.pillar, days: month.days};
      dayunHours = {key, ...data.flow_hours}; dayunDayCursor = today;
    })
    // Said under this year's table, where the button was: the year it failed for may be listed under no decade.
    .catch(err => {if (dayunMonthsLoad === load) dayunMonthsError = {key, year: start, text: '展开今天失败：' + err.message};})
    .finally(() => {
      if (dayunMonthsLoad !== load) return;
      dayunMonthsLoad = null;
      if (active !== 'dayun') return;
      render();
      const card = document.getElementById('dayun-day-' + today) || document.getElementById('dayun-today');
      if (!card) return;
      card.focus({preventScroll: true});
      card.scrollIntoView({block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
    });
}
// Redraw, keeping the focus on a year's, month's or day's button when it was there.
function dayunRefocus(id) {
  const had = document.activeElement && document.activeElement.id === id;
  render();
  const back = document.getElementById(id); if (had && back) back.focus({preventScroll: true});
}
function dayunMonthTable(box, m, o) {
  const panel = append(box, 'section', 'dy-months'); panel.id = 'dayun-months';
  panel.setAttribute('aria-labelledby', 'dayun-months-title');
  const head = append(panel, 'div', 'dy-months-head');
  const heading = append(head, 'h5', 'dy-months-title'); heading.id = 'dayun-months-title';
  texts(heading, String(m.year), ' ', m.pillar, ' · ', '流月干支');
  append(head, 'span', 'muted', '立春起寅月，每月从节令交接时刻算起');
  const save = append(head, 'button', 'tiny-button dy-days-ics', '导出日历'); save.type = 'button'; save.id = 'dayun-months-ics';
  save.setAttribute('aria-label', '导出流月日历');
  tip(save, '把这一年的十二个流月存成日历文件（.ics），每月一条从交节日到下一个交节日前一天的全天事件；文件在本机生成，不经服务器。备注列出与原局四柱的关系和按出生地时区的交节时刻，可据此反推出生日期、时辰和出生地时区，分享前请留意');
  save.addEventListener('click', () => downloadBlob(new Blob([flowMonthsIcs(m, o)], {type: 'text/calendar;charset=utf-8'}),
    'xuanshu-flow-months-' + m.year + '.ics'));
  const wrap = append(panel, 'div', 'table-wrap');
  const table = append(wrap, 'table', 'data-table dy-years dy-month-table'); table.id = 'dayun-month-table';
  texts(append(table, 'caption', 'visually-hidden'), String(m.year), ' ', '流月干支');
  const th = append(append(table, 'thead'), 'tr');
  ['节令', '干支', ...(o.day ? [] : ['十神', '星运']), '与原局', '神煞'].forEach(t => {append(th, 'th', null, t).scope = 'col';});
  const tbody = append(table, 'tbody'), at = Date.now();
  const days = dayunDays && dayunDays.key === dayunKey && dayunDays.year === m.year ? dayunDays : null;
  const loading = dayunDaysLoad && dayunDaysLoad.key === dayunKey && dayunDaysLoad.year === m.year ? dayunDaysLoad : null;
  m.months.forEach(month => {
    const live = Date.parse(month.start_local) <= at && at < Date.parse(month.end_local_exclusive);
    const tr = append(tbody, 'tr', live ? 'is-current' : null);
    if (live) tr.setAttribute('aria-current', 'date');
    const first = append(tr, 'th'); first.scope = 'row';
    const open = append(first, 'button', 'dy-year-toggle dy-month-toggle'); open.type = 'button'; open.id = 'dayun-month-' + month.month;
    const label = append(open, 'span', 'dy-month-label');
    append(label, 'span', null, month.jie);
    append(label, 'small', 'dy-month-date', month.start_local.slice(5, 16).replace('T', ' '));
    const expanded = !loading && !!days && days.month === month.month;
    open.setAttribute('aria-expanded', String(expanded));
    if (expanded) open.setAttribute('aria-controls', 'dayun-days');
    if (loading && loading.month === month.month) open.setAttribute('aria-busy', 'true');
    tip(open, month.start_local.slice(0, 16).replace('T', ' ') + ' – ' + month.end_local_exclusive.slice(0, 16).replace('T', ' '));
    open.addEventListener('click', () => dayunDaysToggle(m.year, month.month));
    const cell = append(tr, 'td'), pair = append(cell, 'span', 'pillar-cell');
    append(pair, 'span', stemClass(month.pillar[0]), month.pillar[0]); append(pair, 'span', branchClass(month.pillar[1]), month.pillar[1]);
    const ms = settledInteractions(month, o);
    if (!o.day) {append(tr, 'td', 'dy-short', ms.ten_god_of_stem); append(tr, 'td', 'dy-short', ms.growth_stage);}
    const marks = append(tr, 'td', 'dy-mark-cell'); natalMarks(marks, ms); tip(marks, natalText(ms)); if (!marks.childNodes.length) marks.textContent = '—';
    stackStars(tr, o.stars ? '随时辰而定' : (ms.shensha || []).map(sh => sh.name).join('、') || '—');
  });
  stackTable(table);
  append(panel, 'p', 'field-help dy-years-hint', '点节令可展开这个月每天的日柱。');
  const failed = dayunDaysError && dayunDaysError.key === dayunKey && dayunDaysError.year === m.year ? dayunDaysError : null;
  // The failure names its month: the grid of another month may still be open above it.
  if (failed) texts(append(panel, 'p', 'inline-msg'), m.months[failed.month - 1].jie, ' ', '流日计算失败：', failed.message);
  if (loading) loadingGhost(panel, 'table');
  else if (days) dayunDayGrid(panel, days, o);
}
// A day's weekday, short; the interface language translates it like any other text.
const SHORT_WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
const shortWeekday = iso => SHORT_WEEKDAYS[(new Date(iso + 'T00:00:00Z').getUTCDay() + 6) % 7];
// The days of a month as cards: date and weekday, the day pillar, its ten god and short marks against the natal chart;
// the full relations and stars in the card's hint. Today and the day of the jie stand out.
function dayunDayGrid(panel, d, o) {
  const box = append(panel, 'section', 'dy-days'); box.id = 'dayun-days';
  box.setAttribute('aria-labelledby', 'dayun-days-title');
  const head = append(box, 'div', 'dy-months-head');
  const heading = append(head, 'h6', 'dy-months-title'); heading.id = 'dayun-days-title';
  texts(heading, String(d.year), ' ', d.jie, ' ', d.pillar, ' · ', '流日干支');
  // The twelfth month (and part of the eleventh) falls in the next calendar year: the range says which.
  const firstDate = d.days[0].date, lastDate = d.days[d.days.length - 1].date;
  const range = append(head, 'span', 'dy-days-range', firstDate + ' – ' + (lastDate.slice(0, 4) === firstDate.slice(0, 4) ? lastDate.slice(5) : lastDate));
  range.dataset.noI18n = '';
  append(head, 'span', 'muted', '日柱在午夜换日；交节当天列在本月');
  const save = append(head, 'button', 'tiny-button dy-days-ics', '导出日历'); save.type = 'button'; save.id = 'dayun-days-ics';
  save.setAttribute('aria-label', '导出流日日历');
  tip(save, '把这个月每天的日柱存成日历文件（.ics），可导入手机或电脑日历；文件在本机生成，不经服务器。备注列出与原局四柱的关系，可据此反推出生日期和时辰，分享前请留意');
  save.addEventListener('click', () => downloadBlob(new Blob([flowDaysIcs(d, o)], {type: 'text/calendar;charset=utf-8'}),
    'xuanshu-flow-days-' + d.days[0].date + '.ics'));
  const list = append(box, 'ol', 'dy-day-grid'); list.id = 'dayun-day-grid';
  const today = flowNow().date, inMonth = date => d.days.some(day => day.date === date);
  const hours = dayunHours && dayunHours.key === dayunKey && inMonth(dayunHours.date) ? dayunHours : null;
  const loading = dayunHoursLoad && dayunHoursLoad.key === dayunKey && inMonth(dayunHoursLoad.date) ? dayunHoursLoad : null;
  // One card takes the Tab stop: the one moved to last, else the open one, today, or the first.
  const stop = [dayunDayCursor, hours && hours.date, loading && loading.date, today].find(date => date && inMonth(date)) || d.days[0].date;
  d.days.forEach(day => {
    const ds = settledInteractions(day, o), item = append(list, 'li');
    // The twelfth month of 2099 runs into 2100, past the range hours are worked out for: those days are plain cards that
    // still take the arrow keys and show their hint on a tap, but open nothing.
    const closed = day.date > FLOW_HOUR_LAST_DATE;
    const open = append(item, closed ? 'div' : 'button', 'dy-day' + (day.date === today ? ' is-today' : '') + (day.jie_day ? ' is-jie' : '') + (closed ? ' is-closed' : ''));
    if (!closed) open.type = 'button';
    open.id = 'dayun-day-' + day.date; open.tabIndex = day.date === stop ? 0 : -1;
    if (day.date === today) open.setAttribute('aria-current', 'date');
    const expanded = !loading && !!hours && hours.date === day.date;
    if (!closed) open.setAttribute('aria-expanded', String(expanded));
    if (expanded) open.setAttribute('aria-controls', 'dayun-hours');
    if (loading && loading.date === day.date) open.setAttribute('aria-busy', 'true');
    const top = append(open, 'span', 'dy-day-top');
    append(top, 'b', 'dy-day-date', (day.date.slice(5) === '01-01' ? day.date.slice(0, 4) + '/' : '') + day.date.slice(5).replace('-', '/'));
    append(top, 'small', null, shortWeekday(day.date));
    const pair = append(open, 'span', 'pillar-cell dy-day-gz');
    append(pair, 'span', stemClass(day.pillar[0]), day.pillar[0]); append(pair, 'span', branchClass(day.pillar[1]), day.pillar[1]);
    const foot = append(open, 'span', 'dy-day-foot');
    if (day.jie_day) append(foot, 'small', 'dy-day-jie', d.jie);
    if (!o.day) append(foot, 'small', 'dy-day-god', ds.ten_god_of_stem);
    natalMarks(foot, ds);
    tip(open, natalText(ds));
    if (!closed) open.addEventListener('click', () => dayunHoursToggle(day.date));
  });
  // Arrow keys move along the cards, up and down by a row of the grid as it is laid out; Home and End to the ends.
  list.addEventListener('keydown', event => {
    const cards = [...list.querySelectorAll('.dy-day')], at = cards.indexOf(document.activeElement);
    if (at < 0 || event.altKey || event.ctrlKey || event.metaKey) return;
    const row = cards.filter(card => card.offsetTop === cards[0].offsetTop).length || 1;
    const to = {ArrowRight: at + 1, ArrowLeft: at - 1, ArrowDown: at + row, ArrowUp: at - row, Home: 0, End: cards.length - 1}[event.key];
    if (to === undefined || to < 0 || to >= cards.length) return;
    event.preventDefault();
    cards[at].tabIndex = -1; cards[to].tabIndex = 0; cards[to].focus();
    dayunDayCursor = d.days[to].date;
  });
  append(box, 'p', 'field-help dy-years-hint', '点日期可展开这一天的十二时辰；方向键可在日期间移动。');
  const failed = dayunHoursError && dayunHoursError.key === dayunKey && inMonth(dayunHoursError.date) ? dayunHoursError : null;
  // The failure names its day: the hours of another day may still be open above it.
  if (failed) texts(append(box, 'p', 'inline-msg'), failed.date.slice(5).replace('-', '/'), ' ', '流时计算失败：', failed.message);
  if (loading) loadingGhost(box, 'table');
  else if (hours) dayunHourTable(box, hours, o, d.days.find(day => day.date === hours.date));
}
// A month's flow days, or a year's months, as an iCalendar file made in the browser, nothing sent anywhere: all-day
// events titled with the pillar, ten god and the short marks against the natal chart, the full relations and stars in
// their notes, free time so they block nothing. The chart notation stays Chinese, as in the other chart exports (繁體 in
// that interface).
const icsEscape = text => String(text).replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n');
// Lines over 75 octets go on with a leading space, never splitting a character (RFC 5545, 3.1).
function icsFold(line) {
  const size = text => new TextEncoder().encode(text).length, parts = [];
  let part = '';
  for (const ch of line) {
    if (size(part + ch) > (parts.length ? 74 : 75)) {parts.push(part); part = '';}
    part += ch;
  }
  return [...parts, part].join('\r\n ');
}
// A short tag of the natal pillars the notes already show keeps two charts' events apart in one calendar; it is not
// made from the request, whose birth minute a search over every minute of 1901–2099 would find from the tag.
const chartTag = key => [...key].reduce((h, ch) => Math.imul(h ^ ch.codePointAt(0), 16777619) >>> 0, 2166136261).toString(16).padStart(8, '0');
// The calendar around flow events, all-day and free: the chart tag in each UID (after the event's key, its start date
// unless it names one), a sequence a later export raises.
function flowIcs(name, kind, events, o) {
  const traditional = typeof uiLang !== 'undefined' && uiLang === 'zh-TW' && typeof toTraditional === 'function';
  const local = text => traditional ? toTraditional(text) : text;
  const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+/, '');
  // Pillars the unknown hour leaves open are left out of the tag, as they are from the notes.
  const tag = chartTag(['year', 'month', 'day', 'hour'].map(k => o.open.has(k) ? '' : current.bazi.pillars[k].text).join(' '));
  // A later export of the same chart carries a higher sequence, so a calendar that updates events by UID takes it.
  const sequence = Math.max(0, Math.floor((Date.now() - Date.UTC(2026, 0, 1)) / 6e4));
  const compact = iso => iso.replace(/-/g, '');
  const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//XuanShu//Flow ' + kind + 's//ZH', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
    'X-WR-CALNAME:' + icsEscape(local(name))];
  events.forEach(e => lines.push('BEGIN:VEVENT', 'UID:flow-' + kind + '-' + (e.key || compact(e.start)) + '-' + tag + '@xuanshu.local', 'SEQUENCE:' + sequence,
    'DTSTAMP:' + stamp, 'DTSTART;VALUE=DATE:' + compact(e.start), 'DTEND;VALUE=DATE:' + compact(e.end),
    'SUMMARY:' + icsEscape(local(e.title.filter(Boolean).join(' · '))),
    'DESCRIPTION:' + icsEscape(local(e.notes.filter(Boolean).join('\n'))), 'TRANSP:TRANSPARENT', 'END:VEVENT'));
  lines.push('END:VCALENDAR');
  return lines.map(icsFold).join('\r\n') + '\r\n';
}
const flowStarsNote = o => o.stars ? calendarWords('神煞') + ' ' + calendarWords('随时辰而定') : '';
function flowDaysIcs(d, o) {
  return flowIcs(calendarWords('玄枢 · 流日') + ' ' + d.year + ' ' + calendarWords(d.jie) + ' ' + d.pillar, 'day', d.days.map(day => {
    const ds = settledInteractions(day, o);
    return {start: day.date, end: new Date(Date.parse(day.date + 'T00:00:00Z') + 864e5).toISOString().slice(0, 10),
      title: [day.pillar + '日', !o.day && calendarWords(ds.ten_god_of_stem), day.jie_day && calendarWords(d.jie), natalMarkList(ds).map(([text]) => calendarMark(text)).join(' ')],
      notes: [natalText(ds), flowStarsNote(o), calendarWords(TEXT_FOOTER[0])]};
  }), o);
}
// A year's twelve months, each from its jie day up to the day before the next (the jie day opens the month, as in the
// days), both jie named in its notes with their moments on the birth zone's clock and its UTC offset, so they are not
// read as the clock where the calendar is. Its UID is keyed on the flow year and month, not the jie date, which a
// corrected birth zone can move across midnight while the pillars stay the same.
function flowMonthsIcs(m, o) {
  const at = iso => iso.slice(0, 16).replace('T', ' '), offset = iso => 'UTC' + ((iso.match(/[+-]\d\d:\d\d$/) || ['+00:00'])[0]);
  return flowIcs(calendarWords('玄枢 · 流月') + ' ' + m.year + ' ' + m.pillar, 'month', m.months.map((month, i) => {
    const ms = settledInteractions(month, o), from = month.start_local, to = month.end_local_exclusive;
    const next = calendarWords(i < m.months.length - 1 ? m.months[i + 1].jie : '立春');
    const span = offset(from) === offset(to)
      ? calendarWords(month.jie) + ' ' + at(from) + ' – ' + next + ' ' + at(to) + ' (' + offset(from) + ')'
      : calendarWords(month.jie) + ' ' + at(from) + ' (' + offset(from) + ') – ' + next + ' ' + at(to) + ' (' + offset(to) + ')';
    return {key: m.year + String(month.month).padStart(2, '0'), start: from.slice(0, 10), end: to.slice(0, 10),
      title: [month.pillar + '月', calendarWords(month.jie), !o.day && calendarWords(ms.ten_god_of_stem), natalMarkList(ms).map(([text]) => calendarMark(text)).join(' ')],
      notes: [span, natalText(ms), flowStarsNote(o), calendarWords(TEXT_FOOTER[0])]};
  }), o);
}
// The thirteen double-hours of a day, Zi at both ends, read against the natal chart like the days. The hour now is marked
// when the day is today; with the 23:00 day change the last Zi shows the next day's pillar it belongs to.
function dayunHourTable(box, h, o, day) {
  const panel = append(box, 'section', 'dy-hours'); panel.id = 'dayun-hours';
  panel.setAttribute('aria-labelledby', 'dayun-hours-title');
  const head = append(panel, 'div', 'dy-months-head');
  const heading = append(head, 'h6', 'dy-months-title'); heading.id = 'dayun-hours-title';
  texts(heading, h.date.slice(5).replace('-', '/'), ' ', h.day_pillar, ' · ', '流时干支');
  append(head, 'span', 'muted', h.day_boundary === '23:00' ? '按出生时区的钟表时间分时辰；23:00 起的子时已换到次日' : '按出生时区的钟表时间分时辰');
  // The day's own relations in full, as its card's hint has them: a tap on the card opens its hours, not a hint.
  if (day) texts(append(panel, 'p', 'field-help dy-hour-day'), '当日', '：', natalText(settledInteractions(day, o)));
  const wrap = append(panel, 'div', 'table-wrap');
  const table = append(wrap, 'table', 'data-table dy-years dy-hour-table'); table.id = 'dayun-hour-table';
  texts(append(table, 'caption', 'visually-hidden'), h.date, ' ', '流时干支');
  const th = append(append(table, 'thead'), 'tr');
  ['时辰', '干支', ...(o.day ? [] : ['十神', '星运']), '与原局', '神煞'].forEach(t => {append(th, 'th', null, t).scope = 'col';});
  const tbody = append(table, 'tbody'), clock = flowNow();
  const minute = h.date === clock.date ? clock.minute : -1;
  const minutes = text => Number(text.slice(0, 2)) * 60 + Number(text.slice(3));
  h.hours.forEach(hour => {
    const live = minutes(hour.start) <= minute && minute < minutes(hour.end);
    const tr = append(tbody, 'tr', live ? 'is-current' : null);
    if (live) tr.setAttribute('aria-current', 'time');
    const first = append(tr, 'th', 'dy-hour-name'); first.scope = 'row';
    append(first, 'span', null, SHICHEN_NAMES['子丑寅卯辰巳午未申酉戌亥'.indexOf(hour.branch)]);
    const span = append(first, 'small', 'dy-month-date', hour.start + '–' + hour.end); span.dataset.noI18n = '';
    if (hour.day_pillar !== h.day_pillar) texts(append(first, 'small', 'dy-month-date'), '属次日', ' ', hour.day_pillar);
    const cell = append(tr, 'td'), pair = append(cell, 'span', 'pillar-cell');
    append(pair, 'span', stemClass(hour.pillar[0]), hour.pillar[0]); append(pair, 'span', branchClass(hour.pillar[1]), hour.pillar[1]);
    const hs = settledInteractions(hour, o);
    if (!o.day) {append(tr, 'td', 'dy-short', hs.ten_god_of_stem); append(tr, 'td', 'dy-short', hs.growth_stage);}
    const marks = append(tr, 'td', 'dy-mark-cell'); natalMarks(marks, hs); tip(marks, natalText(hs)); if (!marks.childNodes.length) marks.textContent = '—';
    stackStars(tr, o.stars ? '随时辰而定' : (hs.shensha || []).map(sh => sh.name).join('、') || '—');
  });
  stackTable(table);
}
function renderBirthBoundaries(){
  title(result,'出生时刻临界地图','模型边界自动分段 · 精度约1秒 · 与抽样不同');
  append(result,'p','info-inline','识别时辰、日界、节令和时区变更。仅保证当前已实现规则的数值分段，不保证所有流派的专业命盘。');
  if(!current){append(result,'p','info-inline','请先生成出生盘。');return;}
  const row=append(result,'div','inline-control');
  const radius=createInput('出生时间前后误差（分钟）','number',String(boundaryDraft.uncertainty_minutes),row);
  radius.id='boundary-radius';radius.min='1';radius.max='120';keepTyped(radius);
  const run=append(row,'button',null,'定位临界时刻');run.id='boundary-run';run.type='button';
  const error=append(result,'p','inline-msg');
  run.addEventListener('click', async()=>{
    const value=Number(radius.value);if(!Number.isInteger(value)||value<1||value>120){error.textContent='误差范围必须是1–120的整数';return;}
    boundaryDraft={uncertainty_minutes:value};run.disabled=true;error.textContent='';
    try{const data=await postForChart('/api/birth-boundaries',{birth:readInput(),uncertainty_minutes:value});if(data!==STALE){boundaryResult=data;render();}}
    catch(e){error.textContent='查询失败：'+e.message;}finally{run.disabled=false;}
  });
  if(!boundaryResult)return;
  const d=boundaryResult;
  meta(result,[`检测区间 ±${d.uncertainty_minutes}分钟`,`${d.boundaries.length}个边界`,`${d.segments.length}个区间`]);
  // Near the edge of the supported years the window stops there, and the page says which side was cut.
  const clipped = d.clipped_to_supported_range || [];
  if (clipped.includes('start')) append(result, 'p', 'info-inline', '误差区间早于支持范围（1901 年起）的部分没有检查，时间轴从支持范围的起点开始。');
  if (clipped.includes('end')) append(result, 'p', 'info-inline', '误差区间晚于支持范围（到 2099 年为止）的部分没有检查，时间轴到支持范围的终点为止。');
  // The interval as a line: a band per segment, a numbered tick per switch and a pin at the recorded birth time.
  // The window is symmetric around the birth instant unless it was cut at the supported years. (Old zone offsets such
  // as +01:19:32 do not parse in JS, so the local birth string is not read as a time; the UTC instant is.)
  const t0 = Date.parse(d.start_utc), span = Date.parse(d.end_utc) - t0, birthAt = d.birth_utc ? Date.parse(d.birth_utc) : t0 + span / 2;
  const at = iso => (typeof iso === 'number' ? iso - t0 : Date.parse(iso) - t0) / span * 100;
  const birthDay = d.original_birth_local.slice(0, 10);
  // When the zone's offset changes inside the window (daylight saving), local times carry their offset.
  const offsets = new Set(d.segments.flatMap(s => [s.start_local_inclusive.slice(19), s.end_local_exclusive.slice(19)]));
  const clock = iso => {
    const t = iso.slice(11, 19);
    return (iso.slice(0, 10) !== birthDay ? iso.slice(5, 10).replace('-', '/') + ' ' : '') + (t.endsWith(':00') ? t.slice(0, 5) : t) + (offsets.size > 1 ? ' (' + iso.slice(19) + ')' : '');
  };
  const offsetMinutes = o => {const m = /^([+-])(\d\d):(\d\d)(?::(\d\d))?$/.exec(o); return m ? (m[1] === '-' ? -1 : 1) * (+m[2] * 60 + +m[3] + +(m[4] || 0) / 60) : 0;};
  // The same instant on the clock before an offset change, e.g. 03:00 (+02:00) when the clock goes back to 02:00 (+01:00).
  const clockIn = (utc, offset) => clock(new Date(Date.parse(utc) + offsetMinutes(offset) * 60000).toISOString().slice(0, 19) + offset);
  const birthSegment = d.segments.find(s => Date.parse(s.start_utc_inclusive) <= birthAt && birthAt < Date.parse(s.end_utc_exclusive));
  const line = append(result, 'div', 'bt-line'); line.id = 'boundary-timeline';
  const track = append(line, 'div', 'bt-track'); track.setAttribute('aria-hidden', 'true');
  const bands = append(track, 'div', 'bt-bands');
  d.segments.forEach((s, i) => {
    const left = at(s.start_utc_inclusive), width = at(s.end_utc_exclusive) - left;
    const band = append(bands, 'span', 'bt-seg' + (i % 2 ? ' is-alt' : '') + (s === birthSegment ? ' is-birth' : '') + (width < 5 ? ' is-narrow' : ''));
    band.style.left = left + '%'; band.style.width = width + '%';
    append(band, 'span', 'bt-seg-num', String(s.index));
  });
  // A badge that would overlap the one before it (an 18px badge on the track's width) moves up a row.
  const badgeGap = 2000 / Math.max(track.getBoundingClientRect().width, 200), rows = [];
  d.boundaries.forEach((b, i) => {
    const left = at(b.utc), tick = append(track, 'span', 'bt-tick'); tick.style.left = left + '%';
    let row = rows.findIndex(last => left - last >= badgeGap); if (row < 0) row = rows.length; rows[row] = left;
    append(tick, 'span', 'bt-tick-num' + (row ? ' is-up' + Math.min(row, 2) : ''), String(i + 1));
    if (row) line.classList.add('has-up' + Math.min(row, 2));
  });
  // The pin stays on the track at either end, and the birth label slides so that it never leaves the line: centred in
  // the middle, flush with the start or end there. In a window cut at the supported years it takes its own row, clear
  // of the start and end times it would otherwise cover.
  const birthAtPct = at(birthAt);
  const pin = append(track, 'span', 'bt-pin'); pin.style.left = `clamp(6px, ${birthAtPct}%, calc(100% - 6px))`;
  const axis = append(line, 'div', 'bt-axis' + (clipped.length ? ' has-birth-row' : ''));
  append(axis, 'span', null, clock(d.segments[0].start_local_inclusive));
  const birthLabel = texts(append(axis, 'span', 'bt-axis-birth'), '出生时间', ' ' + d.original_birth_local.slice(11, 16));
  birthLabel.style.left = birthAtPct + '%'; birthLabel.style.transform = `translateX(-${birthAtPct}%)`;
  append(axis, 'span', null, clock(d.segments[d.segments.length - 1].end_local_exclusive));
  // What changes at each switch, read from the segments on either side of it.
  const changes = (a, b) => {
    const out = PILLAR_KEYS.filter(k => a.bazi_pillars[k] !== b.bazi_pillars[k]).map(k => [nameMap[k], a.bazi_pillars[k], b.bazi_pillars[k]]);
    [['命宫', 'ziwei_ming_palace'], ['身宫', 'ziwei_shen_palace'], ['五行局', 'ziwei_bureau']].forEach(([label, key]) => {if (a[key] !== b[key]) out.push([label, a[key], b[key]]);});
    const la = a.ziwei_lunar_date, lb = b.ziwei_lunar_date;
    if (la.year !== lb.year || la.month !== lb.month || la.day !== lb.day || la.is_leap_month !== lb.is_leap_month) out.push(['农历', lunarDateText(la), lunarDateText(lb), true]);
    return out;
  };
  append(result,'h4','subheading','检出的规则切换点');
  if(!d.boundaries.length)append(result,'p','info-inline','当前模型在此检查范围内未检出时辰、日界、节令或时区变更。');
  const switches = append(result, 'ol', 'bt-switches'); switches.id = 'boundary-switches';
  d.boundaries.forEach((b, i) => {
    const item = append(switches, 'li', 'bt-switch');
    append(item, 'span', 'bt-tick-num', String(i + 1));
    const body = append(item, 'div');
    const head = append(body, 'p', 'bt-switch-head');
    const after = d.segments.findIndex(s => s.start_utc_inclusive === b.utc);
    const before = after > 0 ? d.segments[after - 1].start_local_inclusive.slice(19) : '';
    append(head, 'b', null, (before && before !== b.local.slice(19) ? clockIn(b.utc, before) + ' → ' : '') + clock(b.local));
    b.types.forEach(type => {
      const chip = append(head, 'span', 'bt-type');
      if (type.startsWith('节令界:')) texts(chip, '节令界', ' · ', type.slice(4)); else chip.textContent = type;
    });
    const diff = after > 0 ? changes(d.segments[after - 1], d.segments[after]) : [];
    const list = append(body, 'p', 'bt-changes');
    if (!diff.length) append(list, 'span', 'muted', '四柱与紫微字段不变');
    diff.forEach(([label, from, to, own]) => {
      const chip = append(list, 'span', 'bt-change');
      texts(chip, label, ' ');
      const words = append(chip, 'span', null, from + ' → ' + to); if (own) words.dataset.noI18n = '';
    });
  });
  append(result,'h4','subheading','各区间代表命盘');
  const cards = append(result, 'div', 'bt-cards');
  d.segments.forEach(s => {
    const card = append(cards, 'section', 'bt-card' + (s === birthSegment ? ' is-birth' : '')); card.id = 'boundary-segment-' + s.index;
    const head = append(card, 'div', 'bt-card-head');
    append(head, 'b', 'bt-card-num', String(s.index));
    append(head, 'span', 'bt-card-range', clock(s.start_local_inclusive) + ' – ' + clock(s.end_local_exclusive));
    durationText(append(head, 'small', 'muted'), (Date.parse(s.end_utc_exclusive) - Date.parse(s.start_utc_inclusive)) / 60000);
    if (s === birthSegment) append(head, 'span', 'bt-badge', '出生所在');
    const changed = key => birthSegment && s !== birthSegment && s[key] !== birthSegment[key] ? ' is-changed' : '';
    const pillars = append(card, 'div', 'bt-pillars');
    PILLAR_KEYS.forEach(k => {
      const gz = s.bazi_pillars[k];
      const moved = birthSegment && s !== birthSegment && gz !== birthSegment.bazi_pillars[k];
      const cell = append(pillars, 'span', 'bt-pillar' + (moved ? ' is-changed' : ''));
      append(cell, 'small', null, nameMap[k]);
      const text = append(cell, 'b', 'bt-gz'); text.dataset.noI18n = '';
      append(text, 'span', stemClass(gz[0]), gz[0]); append(text, 'span', branchClass(gz[1]), gz[1]);
      if (moved) append(cell, 'span', 'visually-hidden', '与出生所在区间不同');
    });
    const ziwei = append(card, 'p', 'bt-ziwei');
    const field = (key, ...parts) => {const span = texts(append(ziwei, 'span', 'bt-field' + changed(key)), ...parts); if (changed(key)) append(span, 'span', 'visually-hidden', '与出生所在区间不同');};
    field('ziwei_ming_palace', '命宫', ' ', s.ziwei_ming_palace);
    field('ziwei_shen_palace', '身宫', ' ', s.ziwei_shen_palace);
    field('ziwei_bureau', s.ziwei_bureau);
    const lunar = append(card, 'p', 'bt-lunar');
    texts(lunar, '农历', ' '); append(lunar, 'span', null, lunarDateText(s.ziwei_lunar_date)).dataset.noI18n = '';
    texts(append(card, 'small', 'bt-utc'), 'UTC 区间起点', ' ' + s.start_utc_inclusive.slice(0, 19).replace('T', ' '));
  });
  d.limitations.forEach(x=>note(result,x));
}
// Printing opens the collapsed field sections (print CSS cannot open a closed <details>) and closes them afterwards.
addEventListener('beforeprint', () => document.querySelectorAll('details.ev-more:not([open])').forEach(d => {d.open = true; d.dataset.printOpened = '';}));
addEventListener('afterprint', () => document.querySelectorAll('details[data-print-opened]').forEach(d => {d.open = false; delete d.dataset.printOpened;}));
// The integration page asks the running server over MCP itself, so the connection check, the tool catalogue and every
// example are what an agent connecting now would get; nothing on it is written into the page by hand.
let capabilities = null, capabilitiesPending = false, capabilitiesError = '', capabilitiesToken = '';
let agentCatalog = null, agentPending = false, agentSeq = 0;
const agentRuns = {}, agentDocs = {};
const agentDraft = {client: 'claude-desktop', os: /Windows/i.test(navigator.userAgent) ? 'windows' : 'posix', path: '', query: '', group: 'all',
  expanded: new Set()};  // tools whose long description is shown in full
const MCP_MODERN = '2026-07-28', MCP_LEGACY = '2025-11-25';
// Tools by what they are for, and the workbench page that shows the same calculation.
const AG_GROUPS = [
  ['chart', '排盘', ['combined_chart', 'bazi_chart', 'ziwei_chart', 'ziwei_professional_chart', 'palace_detail', 'symbolic_reading']],
  ['cycles', '运限', ['bazi_dayun', 'ziwei_horoscope', 'annual_transformations', 'annual_timeline', 'life_path_review']],
  ['qimen', '奇门', ['qimen_hour_chart', 'qimen_reference_audit']],
  ['calendar', '历法择日', ['daily_almanac', 'calendar_days', 'solar_terms', 'lunar_to_gregorian', 'day_officers', 'date_candidate_scan', 'pillars_to_dates']],
  ['relations', '关系', ['pair_comparison', 'ziwei_pair_overlay', 'group_relations']],
  ['audit', '核验审计', ['chart_quality_audit', 'time_basis_audit', 'birth_time_window', 'birth_boundary_map', 'rule_comparison', 'rule_sensitivity_matrix', 'chart_import_check']],
  ['workflow', '工作流与报告', ['consultation_execute', 'deep_evidence_review', 'structured_report', 'decision_matrix']],
];
const AG_TABS = {combined_chart: 'bazi', bazi_chart: 'bazi', ziwei_chart: 'ziwei', ziwei_professional_chart: 'professional', symbolic_reading: 'reading',
  bazi_dayun: 'dayun', annual_transformations: 'annual', annual_timeline: 'timeline', life_path_review: 'chat', qimen_hour_chart: 'qimen',
  qimen_reference_audit: 'qimen-audit', daily_almanac: 'today', calendar_days: 'calendar', solar_terms: 'calendar', lunar_to_gregorian: 'calendar',
  day_officers: 'officers', date_candidate_scan: 'date-scan', pillars_to_dates: 'pillar-search', pair_comparison: 'pair', ziwei_pair_overlay: 'pair',
  group_relations: 'group', chart_quality_audit: 'quality', birth_time_window: 'quality', time_basis_audit: 'time', rule_comparison: 'time',
  birth_boundary_map: 'boundaries', rule_sensitivity_matrix: 'rule-matrix', ziwei_horoscope: 'ziwei',
  chart_import_check: 'import-check', consultation_execute: 'consult', deep_evidence_review: 'deep', structured_report: 'report', decision_matrix: 'decision'};
// Example calls use a fixed demonstration birth, never the birth in the form, so copying or trying one shares nothing personal.
const AG_BIRTH = {birth_datetime: '2000-08-16T04:00', timezone: 'Asia/Shanghai', gender: 'female'};
const AG_PARTNER = {birth_datetime: '1998-03-21T09:30', timezone: 'Asia/Shanghai', gender: 'male'};
const AG_MOMENT = {birth_datetime: '2024-06-15T14:30', timezone: 'Asia/Shanghai'};
const AG_EXAMPLES = {
  consultation_execute: {question: 'Which traditional structures relate to a 2027 career choice?', birth: AG_BIRTH},
  qimen_hour_chart: {moment: AG_MOMENT},
  qimen_reference_audit: {moment: AG_MOMENT, reference_source: 'Hand-copied reference chart (example)', reference_school: 'hour-qimen-chabu-rotating',
    root_fields: {bureau: 6, day_pillar: '庚戌', hour_pillar: '癸未'}},
  time_basis_audit: {birth: {...AG_BIRTH, longitude: 116.4}},
  rule_comparison: {original: AG_BIRTH, alternative: {...AG_BIRTH, late_zi_day_rollover: true}},
  decision_matrix: {question: 'Which offer to accept?', criteria: [{name: 'income', weight: 3}, {name: 'growth', weight: 2}],
    options: [{name: 'Offer A', ratings: {income: 4, growth: 3}}, {name: 'Offer B', ratings: {income: 3, growth: 5}}]},
  life_path_review: {birth: AG_BIRTH, events: [{date: '2018-09-01', title: 'Started university'}]},
  pillars_to_dates: {year: '庚辰', month: '甲申', day: '丙午', hour: '庚寅'},
  chart_import_check: {birth: AG_BIRTH, text: ['庚辰', '甲申', '丙午', '庚寅'].join(' ')},
  pair_comparison: {person_a: AG_BIRTH, person_b: AG_PARTNER},
  ziwei_pair_overlay: {person_a: AG_BIRTH, person_b: AG_PARTNER},
  group_relations: {members: [{label: 'A', birth: AG_BIRTH}, {label: 'B', birth: AG_PARTNER}]},
  daily_almanac: {moment: '2026-10-12T09:30', timezone: 'Asia/Shanghai'},
};
// Any other tool gets its required arguments from its input schema.
function agExample(tool) {
  if (AG_EXAMPLES[tool.name]) return AG_EXAMPLES[tool.name];
  const schema = tool.inputSchema || {}, defs = schema.$defs || {};
  const object = s => {
    if (!s) return {};
    if (s.title === 'BirthInput' || (s.properties && s.properties.birth_datetime)) return {...AG_BIRTH};
    const out = {};
    (s.required || []).forEach(key => {out[key] = value(key, (s.properties || {})[key] || {});});
    return out;
  };
  const value = (name, prop) => {
    if (prop.$ref) return object(defs[prop.$ref.split('/').pop()]);
    if (prop.enum) return prop.enum[0];
    if (prop.type === 'integer') return /year/.test(name) ? 2026 : prop.minimum ?? 1;
    if (prop.type === 'number') return prop.minimum ?? 0;
    if (prop.type === 'boolean') return false;
    if (prop.format === 'date' || /date$/.test(name)) return '2026-01-01';
    return prop.type === 'array' ? [] : prop.type === 'object' ? {} : 'example';
  };
  return object(schema);
}
// A tab's label as written in the page (the interface language may have replaced its text).
function tabSource(tab) {
  const node = [...tab.childNodes].find(n => n.nodeType === Node.TEXT_NODE && n.data.trim());
  return ((node && typeof uiOriginal !== 'undefined' && uiOriginal.get(node)) || tab.textContent).trim();
}
const agCall = tool => ({jsonrpc: '2.0', id: 1, method: 'tools/call', params: {name: tool.name, arguments: agExample(tool)}});
// One JSON-RPC request to POST /mcp, with the access token when one is entered. The 2026-07-28 form needs its version in
// the header and in the request metadata; the 2025 form needs neither a handshake nor a session.
async function mcpRequest(method, params, modern = false) {
  const headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream', 'MCP-Protocol-Version': modern ? MCP_MODERN : MCP_LEGACY};
  const token = $('#api_token').value;
  if (token) headers.Authorization = 'Bearer ' + token;
  const body = {jsonrpc: '2.0', id: ++agentSeq, method};
  if (modern) {
    headers['Mcp-Method'] = method;
    params = {...(params || {}), _meta: {'io.modelcontextprotocol/protocolVersion': MCP_MODERN,
      'io.modelcontextprotocol/clientInfo': {name: 'xuanshu-web', version: '0.1.0'}, 'io.modelcontextprotocol/clientCapabilities': {}}};
  }
  if (params) body.params = params;
  const started = performance.now();
  const reply = await fetch('/mcp', {method: 'POST', headers, body: JSON.stringify(body)});
  // The size shown is what the server sent, read before parsing.
  const raw = await reply.text();
  let data = null;
  try {data = JSON.parse(raw);} catch (e) {data = null;}
  const ms = Math.max(1, Math.round(performance.now() - started));
  if (data && data.error && typeof data.error === 'object') throw new Error(data.error.message + ' (' + data.error.code + ')');
  if (!reply.ok || !data) throw new Error('HTTP ' + reply.status);
  return {result: data.result, ms, bytes: new Blob([raw]).size};
}
async function loadAgentCatalog() {
  agentPending = true;
  const catalog = {token: $('#api_token').value, steps: [], failed: false};
  const step = async (method, modern, run, describe) => {
    const entry = {method, protocol: modern ? MCP_MODERN : MCP_LEGACY};
    catalog.steps.push(entry);
    try {
      const out = await run();
      Object.assign(entry, {ok: true, ms: out.ms, detail: describe(out.result)});
      return out.result;
    } catch (e) {
      Object.assign(entry, {ok: false, detail: [e.message]}); catalog.failed = true;
      return null;
    }
  };
  const plain = (method, params) => () => mcpRequest(method, params);
  const found = await step('server/discover', true, () => mcpRequest('server/discover', {}, true), r => {
    const info = (r._meta || {})['io.modelcontextprotocol/serverInfo'] || {};
    catalog.server = {name: info.name || 'MCP', version: info.version || '', versions: r.supportedVersions || []};
    return [catalog.server.name + ' ' + catalog.server.version];
  });
  await step('initialize', false, plain('initialize', {protocolVersion: MCP_LEGACY, capabilities: {}, clientInfo: {name: 'xuanshu-web', version: '0.1.0'}}),
    r => {if (!found) catalog.server = {name: r.serverInfo.name, version: r.serverInfo.version, versions: [r.protocolVersion]}; return ['协商版本', ' ' + r.protocolVersion];});
  catalog.tools = await step('tools/list', false, plain('tools/list'), r => [r.tools.length, ' ', '个工具']).then(r => r && r.tools);
  catalog.prompts = await step('prompts/list', false, plain('prompts/list'), r => [r.prompts.length, ' ', '个提示模板']).then(r => r && r.prompts);
  catalog.resources = await step('resources/list', false, plain('resources/list'), r => [r.resources.length, ' ', '个规则资源']).then(r => r && r.resources);
  catalog.templates = await step('resources/templates/list', false, plain('resources/templates/list'), r => [r.resourceTemplates.length, ' ', '个资源模板']).then(r => r && r.resourceTemplates);
  // The Skills extension pages its list; every page is read.
  catalog.skills = await step('skills/list', false, async () => {
    let skills = [], cursor = null, ms = 0;
    for (let page = 0; page < 20; page++) {
      const out = await mcpRequest('skills/list', cursor ? {cursor} : null);
      ms += out.ms; skills = skills.concat(out.result.skills); cursor = out.result.nextCursor;
      if (cursor == null) break;
    }
    return {result: {skills}, ms};
  }, r => [r.skills.length, ' Skills']).then(r => r && r.skills);
  agentCatalog = catalog; agentPending = false;
  if (active === 'integration') {
    render();
    announce(catalog.failed ? calT('MCP 连接自检有步骤没有通过') : calT('MCP 连接自检通过'));
  }
}
// Anything but plain path characters is quoted (globs and history marks included: zsh rejects an unquoted [v2]).
const agShellQuote = (text, windows) => /^[\w./:@%+=,-]+$/.test(text) ? text : (windows ? '"' + text.replace(/"/g, '""') + '"' : "'" + text.replace(/'/g, "'\\''") + "'");
// The configuration text for each client, built from the path typed on the page (kept in memory only).
function agentSetup(origin) {
  const windows = agentDraft.os === 'windows', sep = windows ? '\\' : '/';
  const projectPath = agentDraft.path.trim().replace(/[\\/]+$/, '') || (windows ? 'C:\\path\\to\\xuanshu' : '/path/to/xuanshu');
  const pythonPath = windows ? projectPath + '\\.venv\\Scripts\\python.exe' : projectPath + sep + '.venv/bin/python';
  const token = Boolean($('#api_token').value);
  const tokenVar = windows ? '%MCP_BEARER_TOKEN%' : '$MCP_BEARER_TOKEN';
  const url = origin + '/mcp';
  if (agentDraft.client === 'claude-desktop') {
    const snippet = JSON.stringify({mcpServers: {xuanshu: {command: pythonPath, args: ['-m', 'app.stdio'], env: {PYTHONPATH: projectPath}}}}, null, 2);
    return {where: windows ? '%APPDATA%\\Claude\\claude_desktop_config.json' : '~/Library/Application Support/Claude/claude_desktop_config.json',
      how: '写进 Claude Desktop 的配置文件（设置 → 开发者 → 编辑配置），保存后完全退出并重新打开 Claude Desktop。', blocks: [{caption: '配置文件', code: snippet}]};
  }
  if (agentDraft.client === 'claude-code') {
    const q = text => agShellQuote(text, windows);
    return {how: '在终端运行这条命令；加 --scope project 会写进项目的 .mcp.json，便于团队共享。', blocks: [
      {caption: '本机 stdio', code: `claude mcp add --transport stdio --env PYTHONPATH=${q(projectPath)} xuanshu -- ${q(pythonPath)} -m app.stdio`},
      {caption: '已运行的 HTTP 服务', code: `claude mcp add --transport http xuanshu ${url}` + (token ? ` --header "Authorization: Bearer ${tokenVar}"` : '')}]};
  }
  if (agentDraft.client === 'codex') {
    const toml = s => JSON.stringify(s);
    return {where: windows ? '%USERPROFILE%\\.codex\\config.toml' : '~/.codex/config.toml', how: '写进 Codex 的配置文件，然后重新启动 Codex。',
      blocks: [{caption: '配置文件', code: `[mcp_servers.xuanshu]\ncommand = ${toml(pythonPath)}\nargs = ["-m", "app.stdio"]\n\n[mcp_servers.xuanshu.env]\nPYTHONPATH = ${toml(projectPath)}`}]};
  }
  const auth = token ? ` -H "Authorization: Bearer ${tokenVar}"` : '';
  const body = JSON.stringify({jsonrpc: '2.0', id: 1, method: 'tools/list'});
  const curl = windows
    ? `curl.exe -s ${url} -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -H "MCP-Protocol-Version: ${MCP_LEGACY}"${auth} -d "${body.replace(/"/g, '\\"')}"`
    : `curl -s ${url} \\\n  -H 'Content-Type: application/json' \\\n  -H 'Accept: application/json, text/event-stream' \\\n  -H 'MCP-Protocol-Version: ${MCP_LEGACY}'${auth ? ' \\\n ' + auth : ''} \\\n  -d '${body}'`;
  return {how: '支持 Streamable HTTP 的客户端直接连这个地址；公网使用要另行部署 HTTPS 和鉴权。', blocks: [
    {caption: '端点', code: `POST ${url}`}, {caption: windows ? '终端验证：列出工具（命令提示符）' : '终端验证：列出工具', code: curl}]};
}
function agCopyButton(parent, label, text, id) {
  const button = append(parent, 'button', 'tiny-button', label); button.type = 'button'; if (id) button.id = id;
  button.addEventListener('click', async () => {
    try {await navigator.clipboard.writeText(text()); button.textContent = '已复制';}
    catch (e) {button.textContent = '无法自动复制，请手动选中';}
    setTimeout(() => {if (button.isConnected) button.textContent = label;}, 1800);
  });
  return button;
}
function agParams(parent, tool) {
  const schema = tool.inputSchema || {}, props = schema.properties || {}, required = new Set(schema.required || []);
  const names = Object.keys(props).sort((a, b) => required.has(b) - required.has(a));
  const list = append(parent, 'ul', 'ag-params'); list.dataset.noI18n = '';
  if (!names.length) append(list, 'li', 'ag-param is-none', '—');
  names.forEach(name => {
    const prop = props[name];
    const type = prop.$ref ? prop.$ref.split('/').pop() : prop.enum ? 'enum' : prop.anyOf ? prop.anyOf.map(x => x.$ref ? x.$ref.split('/').pop() : x.type).join(' | ') : prop.type || 'any';
    const item = append(list, 'li', 'ag-param' + (required.has(name) ? ' is-required' : ''));
    append(item, 'code', null, name + (required.has(name) ? '*' : ''));
    append(item, 'small', null, type);
    if (prop.description) tip(item, prop.description);
  });
}
function agRunView(box, tool) {
  box.replaceChildren();
  const run = agentRuns[tool.name];
  if (!run) return;
  if (run.pending) {append(box, 'p', 'ag-run-head', '正在调用…'); return;}
  const head = append(box, 'p', 'ag-run-head ' + (run.error ? 'is-fail' : run.isError ? 'is-warn' : 'is-ok'));
  append(head, 'span', 'ag-dot');
  texts(head, run.error ? '请求失败' : run.isError ? '工具返回错误' : '调用成功');
  if (!run.error) texts(append(head, 'small', 'muted'), run.ms + ' ms · ' + jvSize(run.bytes));
  if (run.links && run.links.length) {
    const line = append(box, 'p', 'ag-run-links');
    texts(line, '依据的规则文档', '：');
    run.links.forEach(uri => {
      const button = append(line, 'button', 'tiny-button', uri); button.type = 'button'; button.dataset.noI18n = '';
      button.addEventListener('click', () => {
        const doc = document.getElementById('integration-doc-' + uri.split('/').pop());
        if (!doc) return;
        doc.open = true;
        doc.scrollIntoView({block: 'nearest', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
        doc.querySelector('summary').focus({preventScroll: true});
      });
    });
  }
  const text = run.error || run.text;
  const pre = append(box, 'pre', 'json-code ag-output', text.length > 4000 ? text.slice(0, 4000) + '\n…' : text); pre.dataset.noI18n = '';
  if (text.length > 4000) append(box, 'small', 'muted', '只显示前 4000 个字符；完整结果请在工作台页面或你的客户端里查看。');
}
// The page may have been redrawn (another language) while the call ran, so its result goes to the elements now shown.
async function agTry(tool, box, button) {
  // The button stays focusable while the call runs (aria-disabled), so a keyboard user keeps their place.
  if (agentRuns[tool.name] && agentRuns[tool.name].pending) return;
  agentRuns[tool.name] = {pending: true}; button.setAttribute('aria-disabled', 'true'); agRunView(box, tool);
  try {
    const out = await mcpRequest('tools/call', agCall(tool).params);
    const result = out.result || {};
    const text = result.structuredContent ? JSON.stringify(result.structuredContent, null, 2) : (result.content || []).map(c => c.text || '').join('\n');
    // The rule documents the result links (resource_link, from 2025-06-18) open in the resource list below.
    const links = (result.content || []).filter(c => c && c.type === 'resource_link' && typeof c.uri === 'string').map(c => c.uri);
    agentRuns[tool.name] = {isError: Boolean(result.isError), ms: out.ms, bytes: out.bytes, text, links};
  } catch (e) {agentRuns[tool.name] = {error: e.message};}
  const shown = document.getElementById('integration-run-' + tool.name), again = document.getElementById('integration-try-' + tool.name);
  if (again) again.removeAttribute('aria-disabled');
  if (!shown) return;
  agRunView(shown, tool);
  const run = agentRuns[tool.name];
  announce(tool.name + ' ' + calT(run.error ? '请求失败' : run.isError ? '工具返回错误' : '调用成功'));
}
function agDocView(doc, uri) {
  const body = doc.querySelector('.ag-doc-body'), got = agentDocs[uri];
  body.replaceChildren();
  if (!got) return;
  if (got.pending) {append(body, 'p', 'muted', '正在读取…'); return;}
  if (got.error) {append(body, 'p', 'inline-msg', '读取失败：' + got.error); return;}
  texts(append(body, 'small', 'muted'), 'resources/read · ' + got.ms + ' ms · ' + jvSize(got.bytes));
  if (got.json) {
    // A computed fact comes back as JSON: shown indented, as data rather than as a document.
    let shown = got.text;
    try {shown = JSON.stringify(JSON.parse(got.text), null, 2);} catch (_) { /* shown as it came */ }
    const pre = append(body, 'pre', 'ag-doc-text ag-doc-json'); pre.dataset.noI18n = ''; pre.tabIndex = 0;
    pre.setAttribute('role', 'region'); pre.setAttribute('aria-label', uri); pre.textContent = shown;
    agCopyButton(body, '复制全文', () => got.text);
    return;
  }
  // The rule documents are Markdown; they are laid out with the same DOM-only renderer as chat answers.
  const doc2 = append(body, 'div', 'ag-doc-text chat-md'); doc2.dataset.noI18n = ''; doc2.tabIndex = 0;
  doc2.setAttribute('role', 'region'); doc2.setAttribute('aria-label', uri);
  if (window.XuanShuMarkdown) window.XuanShuMarkdown.render(got.text, doc2); else {doc2.textContent = got.text; doc2.style.whiteSpace = 'pre-wrap';}
  agCopyButton(body, '复制全文', () => got.text);
}
// The service's capabilities, read once for the Agent page and the professional page. A failed lookup is tried
// again once another access token is entered.
function ensureCapabilities() {
  const token = $('#api_token').value;
  if ((capabilities === null || (capabilitiesError && token !== capabilitiesToken)) && !capabilitiesPending) {
    capabilitiesPending = true; capabilitiesToken = token; capabilities = null;
    fetch('/api/capabilities', {headers: token ? {'Authorization': 'Bearer ' + token} : {}})
      .then(reply => reply.ok ? reply.json() : Promise.reject(new Error('HTTP ' + reply.status)))
      .then(data => {capabilities = data; capabilitiesError = '';}).catch(err => {capabilities = {}; capabilitiesError = err.message;})
      .finally(() => {capabilitiesPending = false; if (active === 'integration' || active === 'professional') render();});
  }
}
function renderIntegration() {
  title(result, 'Agent 接入中心', 'MCP 连接自检 · 工具目录 · 客户端配置');
  append(result, 'p', 'info-inline', '本项目兼容 MCP 2026-07-28 和旧版 2025 协议的 stdio / Streamable HTTP；本地 Web 运行不等于已上线公网或已登记到 ChatGPT/Claude。');
  const token = $('#api_token').value;
  ensureCapabilities();
  if ((agentCatalog === null || (agentCatalog.failed && token !== agentCatalog.token)) && !agentPending) loadAgentCatalog();
  const catalog = agentCatalog;
  const counts = (capabilities && capabilities.counts) || {};
  const count = (key, unit) => typeof counts[key] === 'number' ? counts[key] + ' ' + unit : capabilities === null ? '…' : '—';
  const box = rules(result, [
    {label: 'MCP 工具', value: count('mcp_tools', 'Tools'), detail: '八字 / 紫微 / 奇门 / 历法 / 关系 / 运限 / 审计'},
    {label: '规则资源', value: count('mcp_resources', 'Resources'), detail: '方法规则、隐私和限制说明'},
    {label: 'Agent Skills', value: count('agent_skills', 'Skills'), detail: '放在源码 skills/ 目录'},
    {label: '提示模板', value: count('mcp_prompts', 'Prompts'), detail: '可复用计算工作流'},
  ]);
  if (box) box.id = 'integration-counts';
  if (capabilitiesError) append(result, 'p', 'inline-msg', '读取服务能力失败：' + capabilitiesError + (capabilitiesError === 'HTTP 401' ? '，请检查 API 访问令牌。' : '。')).id = 'integration-error';
  // Contents: each part of the page, with its size once the server has answered.
  const sizes = {tools: catalog && catalog.tools, prompts: catalog && catalog.prompts, resources: catalog && catalog.resources, skills: catalog && catalog.skills};
  const nav = append(result, 'nav', 'ag-nav'); nav.setAttribute('aria-label', '本页内容');
  [['check', '连接自检'], ['setup', '接入配置'], ['tools', '工具目录'], ['prompts', '提示模板'], ['resources', '规则资源'], ['skills', 'Skills']].forEach(([key, label]) => {
    const link = append(nav, 'a', 'ag-nav-link'); link.href = '#integration-' + key;
    texts(link, label); if (sizes[key]) append(link, 'small', null, String(sizes[key].length));
  });
  nav.addEventListener('click', e => {
    const link = e.target.closest('a'); if (!link) return;
    e.preventDefault(); const target = $(link.getAttribute('href')); target.scrollIntoView({block: 'start'}); target.focus({preventScroll: true});
  });
  const section = (key, heading, detail) => {
    const part = append(result, 'section', 'ag-section'); part.id = 'integration-' + key; part.tabIndex = -1;
    const head = append(part, 'div', 'ag-section-head');
    append(head, 'h4', 'subheading', heading);
    if (detail) append(head, 'small', 'muted', detail);
    return part;
  };

  // 1. The connection check, step by step, in both protocol generations.
  const check = section('check', '连接自检', '本页刚刚用两代协议实际调用了这台服务');
  if (!catalog || agentPending) append(check, 'p', 'info-inline', catalog ? '正在重新检测，下面先保留上一次的结果…' : '正在通过 POST /mcp 检测…').setAttribute('role', 'status');
  else {
    const failures = catalog.steps.filter(s => !s.ok).length;
    const line = append(check, 'p', 'ag-summary ' + (failures ? 'is-fail' : 'is-ok')); line.id = 'integration-summary';
    append(line, 'span', 'ag-dot');
    const summary = append(line, 'span');
    if (!failures) {
      texts(summary, '已连上', ' ');
      append(summary, 'b', null, catalog.server.name + ' ' + catalog.server.version).dataset.noI18n = '';
      texts(summary, '：', '全部', ' ' + catalog.steps.length + ' ', '步通过');
    } else {
      texts(summary, failures + ' ', '步没有通过，原因写在对应一行');
      if (catalog.steps.some(s => !s.ok && /HTTP 401/.test(s.detail[0]))) texts(summary, '；', '请检查 API 访问令牌。');
      else if (catalog.steps.some(s => !s.ok && /HTTP 403/.test(s.detail[0]))) texts(summary, '；', '服务拒绝了本页的来源（Origin），请检查允许的来源设置。');
    }
    const steps = append(check, 'ol', 'ag-steps'); steps.id = 'integration-steps';
    catalog.steps.forEach(s => {
      const item = append(steps, 'li', 'ag-step ' + (s.ok ? 'is-ok' : 'is-fail'));
      append(item, 'span', 'ag-dot');
      append(item, 'code', 'ag-method', s.method);
      append(item, 'span', 'ag-proto', s.protocol);
      const detail = texts(append(item, 'span', 'ag-detail'), ...s.detail);
      if (!s.ok) detail.dataset.noI18n = '';
      if (s.ok) append(item, 'small', 'ag-ms', s.ms + ' ms');
      append(item, 'span', 'visually-hidden', s.ok ? '通过' : '未通过');
    });
    const facts = append(check, 'div', 'ag-facts');
    if (catalog.server && catalog.server.versions.length) {
      const line = append(facts, 'p'); append(line, 'span', 'muted', '服务支持的协议版本');
      catalog.server.versions.forEach(v => append(line, 'code', 'ag-chip', v));
    }
    if (catalog.tools && typeof counts.mcp_tools === 'number') {
      const same = counts.mcp_tools === catalog.tools.length;
      const line = append(facts, 'p', same ? 'ag-same' : 'ag-differ'); line.id = 'integration-consistency';
      texts(line, same ? '工具数与 /api/capabilities 的计数一致' : '工具数与 /api/capabilities 的计数不一致', '：', catalog.tools.length + ' / ' + counts.mcp_tools);
    }
  }
  const recheck = append(check, 'button', 'tiny-button', '重新检测'); recheck.type = 'button'; recheck.id = 'integration-recheck';
  // The last results stay on screen during a recheck, so the page does not jump and opened examples stay open.
  if (agentPending) recheck.setAttribute('aria-disabled', 'true');
  recheck.addEventListener('click', () => {if (agentPending) return; loadAgentCatalog(); render();});

  // 2. Configuration for each client, from the project path typed here.
  const setup = section('setup', '接入配置', '选择客户端和系统，填入项目所在的文件夹');
  const pick = (parent, label, options, key, idPrefix) => {
    const row = append(parent, 'div', 'ag-segment'); row.setAttribute('role', 'group'); row.setAttribute('aria-label', label);
    append(row, 'span', 'ag-segment-label', label).setAttribute('aria-hidden', 'true');
    options.forEach(([value, text]) => {
      const b = append(row, 'button', 'ag-seg', text); b.type = 'button'; b.id = idPrefix + value;
      b.setAttribute('aria-pressed', String(agentDraft[key] === value));
      b.addEventListener('click', () => {agentDraft[key] = value; drawSetup(); row.querySelectorAll('.ag-seg').forEach(x => x.setAttribute('aria-pressed', String(x === b)));});
    });
  };
  pick(setup, '客户端', [['claude-desktop', 'Claude Desktop'], ['claude-code', 'Claude Code'], ['codex', 'Codex'], ['http', 'HTTP 直连']], 'client', 'integration-client-');
  pick(setup, '系统', [['posix', 'macOS / Linux'], ['windows', 'Windows']], 'os', 'integration-os-');
  const pathRow = append(setup, 'div', 'inline-control ag-path');
  const pathInput = createInput('项目文件夹（只用于生成下面的文本，不保存、不上传）', 'text', agentDraft.path, pathRow);
  pathInput.id = 'integration-path'; pathInput.spellcheck = false; pathInput.autocomplete = 'off'; pathInput.maxLength = 400;
  pathInput.placeholder = agentDraft.os === 'windows' ? 'C:\\path\\to\\xuanshu' : '/path/to/xuanshu';
  const setupBody = append(setup, 'div', 'ag-setup'); setupBody.id = 'integration-setup-body';
  const origin = location.origin === 'null' ? 'http://127.0.0.1:8000' : location.origin;
  const drawSetup = () => {
    pathInput.placeholder = agentDraft.os === 'windows' ? 'C:\\path\\to\\xuanshu' : '/path/to/xuanshu';
    const plan = agentSetup(origin);
    setupBody.replaceChildren();
    const how = append(setupBody, 'p', 'ag-how', plan.how);
    if (plan.where) {const where = append(how, 'code', 'ag-where', plan.where); where.dataset.noI18n = ''; how.insertBefore(document.createTextNode(' '), where);}
    plan.blocks.forEach((block, i) => {
      const fig = append(setupBody, 'figure', 'ag-block');
      const cap = append(fig, 'figcaption', null, block.caption);
      const code = append(fig, 'pre', 'json-code', block.code); code.dataset.noI18n = ''; code.id = 'integration-snippet' + (i ? '-' + i : '');
      const copy = agCopyButton(cap, i ? '复制' : '复制配置', () => block.code, i ? null : 'integration-copy');
      copy.setAttribute('aria-label', calT('复制') + ' ' + calT(block.caption));
    });
    if (!agentDraft.path.trim() && agentDraft.client !== 'http') append(setupBody, 'p', 'small-text', '还没填项目文件夹，文本里是占位路径；运行 Python 的虚拟环境要先安装项目依赖。');
    if ($('#api_token').value && agentDraft.client !== 'claude-desktop' && agentDraft.client !== 'codex') append(setupBody, 'p', 'small-text', '令牌写成环境变量 MCP_BEARER_TOKEN 的占位（与服务端令牌同名），不会把你填写的令牌放进这段文本。');
  };
  pathInput.addEventListener('input', () => {agentDraft.path = pathInput.value; drawSetup();});
  drawSetup();

  // 3. The tool catalogue: grouped, searchable, each with its parameters, an example call and a trial run.
  const toolsPart = section('tools', '工具目录', 'Agent 通过 tools/list 看到的就是这些');
  if (!catalog) append(toolsPart, 'p', 'muted', '…');
  else if (!catalog.tools) append(toolsPart, 'p', 'inline-msg', '没有读到工具列表，见上方连接自检。');
  else {
    const tools = catalog.tools;
    // The server marks each tool read-only and repeatable (MCP annotations); say it once rather than on every card.
    if (tools.every(t => t.annotations && t.annotations.readOnlyHint && t.annotations.idempotentHint && t.annotations.openWorldHint === false))
      append(toolsPart, 'p', 'small-text ag-hints', '全部工具都标注为只读：不写入、不联网，重复调用不改变任何东西（不传时刻的工具按当前时间计算），支持这项标注的客户端可以不逐次确认就让 Agent 调用。').id = 'integration-hints';
    const groupOf = name => (AG_GROUPS.find(g => g[2].includes(name)) || ['other', '其他'])[0];
    const groups = AG_GROUPS.map(([key, label, names]) => [key, label, names.map(n => tools.find(t => t.name === n)).filter(Boolean)]);
    const others = tools.filter(t => groupOf(t.name) === 'other');
    if (others.length) groups.push(['other', '其他', others]);
    const bar = append(toolsPart, 'div', 'inline-control ag-toolbar');
    const search = createInput('按名称、用途或参数筛选', 'search', agentDraft.query, bar); search.id = 'integration-search'; search.maxLength = 80;
    search.setAttribute('aria-describedby', 'integration-tool-count');
    const status = append(bar, 'span', 'ag-count'); status.id = 'integration-tool-count'; status.setAttribute('role', 'status');
    const chips = append(toolsPart, 'div', 'ag-groups'); chips.setAttribute('role', 'group'); chips.setAttribute('aria-label', '按用途');
    [['all', '全部', tools], ...groups.filter(g => g[2].length)].forEach(([key, label, list]) => {
      const chip = append(chips, 'button', 'ag-group-chip'); chip.type = 'button'; chip.id = 'integration-group-' + key;
      texts(chip, label); append(chip, 'small', null, String(list.length));
      chip.setAttribute('aria-pressed', String(agentDraft.group === key));
      chip.addEventListener('click', () => {agentDraft.group = key; chips.querySelectorAll('.ag-group-chip').forEach(x => x.setAttribute('aria-pressed', String(x === chip))); filter();});
    });
    const listBox = append(toolsPart, 'div', 'ag-catalog'); listBox.id = 'integration-catalog';
    groups.filter(g => g[2].length).forEach(([key, label, list]) => {
      const group = append(listBox, 'section', 'ag-group'); group.id = 'integration-group-sec-' + key; group.dataset.group = key;
      const h = append(group, 'h5', 'ag-group-title'); texts(h, label); append(h, 'small', null, String(list.length));
      const grid = append(group, 'div', 'ag-tools');
      list.forEach(tool => {
        const card = append(grid, 'article', 'ag-tool'); card.id = 'integration-tool-' + tool.name; card.dataset.group = key;
        const tab = AG_TABS[tool.name] && tabs.find(t => t.dataset.tab === AG_TABS[tool.name]);
        const props = Object.keys((tool.inputSchema || {}).properties || {});
        card.dataset.search = [tool.name, tool.title, calT(tool.title || ''), tool.description, label, calT(label), tab ? tabSource(tab) : '', tab ? tab.textContent : '', ...props].join(' ').toLowerCase();
        const head = append(card, 'div', 'ag-tool-head');
        append(head, 'b', 'ag-tool-title', tool.title || tool.name);
        append(head, 'code', 'ag-name', tool.name).dataset.noI18n = '';
        const desc = append(card, 'p', 'ag-desc'); desc.id = 'integration-desc-' + tool.name;
        append(desc, 'span', 'muted', 'Agent 看到的说明');
        const words = append(desc, 'span', null, ' ' + (tool.description || '')); words.lang = 'en'; words.dataset.noI18n = '';
        // A long description is shown in three lines until opened.
        if ((tool.description || '').length > 180) {
          const full = agentDraft.expanded.has(tool.name);
          desc.classList.toggle('is-clamped', !full);
          const more = append(card, 'button', 'ag-more', full ? '收起' : '展开全文'); more.type = 'button'; more.id = 'integration-more-' + tool.name;
          more.setAttribute('aria-expanded', String(full)); more.setAttribute('aria-controls', desc.id);
          more.addEventListener('click', () => {
            const open = desc.classList.toggle('is-clamped') === false;
            if (open) agentDraft.expanded.add(tool.name); else agentDraft.expanded.delete(tool.name);
            more.setAttribute('aria-expanded', String(open)); more.textContent = open ? '收起' : '展开全文';
          });
        }
        agParams(card, tool);
        const actions = append(card, 'div', 'ag-actions');
        if (tab) {
          const open = append(actions, 'button', 'tiny-button', ''); open.type = 'button'; open.id = 'integration-open-' + tool.name;
          texts(open, '打开工作台页面', '：', tabSource(tab));
          open.addEventListener('click', () => {activateTab(tab); tab.focus();});
        }
        const example = append(card, 'details', 'ag-example'); example.id = 'integration-example-' + tool.name;
        append(example, 'summary', null, '调用示例与试运行').id = 'integration-example-summary-' + tool.name;
        append(example, 'p', 'small-text', '示例用固定的演示出生资料，不读取你填写的出生信息。');
        const request = JSON.stringify(agCall(tool), null, 2);
        const pre = append(example, 'pre', 'json-code ag-request', request); pre.dataset.noI18n = '';
        const row = append(example, 'div', 'ag-actions');
        agCopyButton(row, '复制请求', () => request).setAttribute('aria-label', '复制请求 ' + tool.name);
        const trial = append(row, 'button', 'tiny-button', '试运行'); trial.type = 'button'; trial.id = 'integration-try-' + tool.name;
        const output = append(example, 'div', 'ag-run'); output.id = 'integration-run-' + tool.name;
        agRunView(output, tool);
        trial.setAttribute('aria-label', '试运行 ' + tool.name);
        if (agentRuns[tool.name] && agentRuns[tool.name].pending) trial.setAttribute('aria-disabled', 'true');
        trial.addEventListener('click', () => agTry(tool, output, trial));
      });
    });
    const empty = append(toolsPart, 'p', 'info-inline', '没有符合条件的工具。'); empty.id = 'integration-empty';
    const filter = () => {
      const words = agentDraft.query.trim().toLowerCase().split(/\s+/).filter(Boolean);
      let shown = 0;
      listBox.querySelectorAll('.ag-group').forEach(group => {
        let visible = 0;
        group.querySelectorAll('.ag-tool').forEach(card => {
          const keep = (agentDraft.group === 'all' || card.dataset.group === agentDraft.group) && words.every(w => card.dataset.search.includes(w));
          card.hidden = !keep; if (keep) visible++;
        });
        group.hidden = !visible; shown += visible;
      });
      status.replaceChildren(); texts(status, '显示', ' ' + shown + ' / ' + tools.length + ' ', '个工具');
      empty.hidden = shown > 0;
    };
    let timer = null;
    search.addEventListener('input', () => {agentDraft.query = search.value; clearTimeout(timer); timer = setTimeout(filter, 150);});
    filter();
  }

  // 4. Prompt templates.
  const promptsPart = section('prompts', '提示模板', 'prompts/list：客户端可直接选用的工作流提示');
  if (catalog && catalog.prompts) {
    const list = append(promptsPart, 'ul', 'ag-list'); list.id = 'integration-prompt-list';
    catalog.prompts.forEach(p => {
      const item = append(list, 'li', 'ag-item');
      const head = append(item, 'div', 'ag-tool-head');
      append(head, 'b', 'ag-tool-title', p.title || p.name);
      append(head, 'code', 'ag-name', p.name).dataset.noI18n = '';
      const desc = append(item, 'p', 'ag-desc', p.description || ''); desc.lang = 'en'; desc.dataset.noI18n = '';
      const args = append(item, 'ul', 'ag-params'); args.dataset.noI18n = '';
      (p.arguments || []).forEach(a => {
        const li = append(args, 'li', 'ag-param' + (a.required ? ' is-required' : ''));
        append(li, 'code', null, a.name + (a.required ? '*' : ''));
        if (a.description) tip(li, a.description);
      });
    });
  } else if (catalog) append(promptsPart, 'p', 'inline-msg', '没有读到提示模板，见上方连接自检。');

  // 5. Rule resources, each readable here through resources/read.
  const resourcesPart = section('resources', '规则资源', 'resources/list：Agent 可读取的方法规则与限制');
  // One resource as a row that reads it through resources/read when opened.
  const docRow = (list, id, uri, label, note) => {
    const doc = append(list, 'details', 'ag-doc'); doc.id = id;
    const summary = append(doc, 'summary');
    append(summary, 'code', 'ag-name', label).dataset.noI18n = '';
    append(summary, 'small', 'muted', note);
    append(doc, 'div', 'ag-doc-body');
    doc.addEventListener('toggle', async () => {
      if (!doc.open) return;
      if (!agentDocs[uri] || agentDocs[uri].error) {
        agentDocs[uri] = {pending: true}; agDocView(doc, uri);
        try {
          const out = await mcpRequest('resources/read', {uri});
          const contents = out.result.contents || [];
          agentDocs[uri] = {text: contents.map(c => c.text || '').join('\n'), ms: out.ms, bytes: out.bytes,
            json: contents.length > 0 && contents.every(c => c.mimeType === 'application/json')};
        } catch (e) {agentDocs[uri] = {error: e.message};}
        // The page may have been redrawn while reading; the details shown now get the text.
        const shown = document.getElementById(doc.id);
        if (shown) agDocView(shown, uri);
      } else agDocView(doc, uri);
    });
    agDocView(doc, uri);
  };
  if (catalog && catalog.resources) {
    const list = append(resourcesPart, 'div', 'ag-docs'); list.id = 'integration-resource-list';
    catalog.resources.forEach(r => docRow(list, 'integration-doc-' + r.name, r.uri, r.uri, r.mimeType || ''));
  } else if (catalog) append(resourcesPart, 'p', 'inline-msg', '没有读到规则资源，见上方连接自检。');
  // Resource templates address computed facts (a year's solar terms, a day's lunar date); each row opens on an
  // example address filled with today.
  if (catalog && catalog.templates && catalog.templates.length) {
    texts(append(resourcesPart, 'p', 'field-help'), 'resources/templates/list', '：', '按地址读取的计算结果，打开时以今天为例读取。');
    const list = append(resourcesPart, 'div', 'ag-docs'); list.id = 'integration-template-list';
    const today = localToday();
    catalog.templates.forEach(t => {
      const example = t.uriTemplate.replace('{year}', today.slice(0, 4)).replace('{date}', today);
      docRow(list, 'integration-template-' + t.name, example, t.uriTemplate, t.title || t.name);
    });
  }

  // 6. Skills offered through the MCP Skills extension.
  const skillsPart = section('skills', 'Skills', 'skills/list：可导入客户端的工作流说明');
  if (catalog && catalog.skills) {
    append(skillsPart, 'p', 'small-text', '通过 MCP 导入的目录只放几个高优先级工作流；完整的 Skills 在源码 skills/ 目录，数量见上方计数。');
    const list = append(skillsPart, 'ul', 'ag-list'); list.id = 'integration-skill-list';
    catalog.skills.forEach(s => {
      const item = append(list, 'li', 'ag-item');
      const head = append(item, 'div', 'ag-tool-head');
      append(head, 'code', 'ag-name', (s.frontmatter || {}).name || s.uri).dataset.noI18n = '';
      const digest = ((s.resources || [])[0] || {}).digest || '';
      if (digest) {const d = append(head, 'small', 'ag-digest', digest.slice(0, 19) + '…'); tip(d, digest); d.dataset.noI18n = '';}
      const desc = append(item, 'p', 'ag-desc', (s.frontmatter || {}).description || ''); desc.lang = 'en'; desc.dataset.noI18n = '';
    });
  } else if (catalog) append(skillsPart, 'p', 'inline-msg', '没有读到 Skills，见上方连接自检。');
  append(result, 'div', 'feature-note', '公网接入必须单独部署 HTTPS、配置安全令牌/宿主支持的鉴权方式，并由用户在宿主平台进行连接授权。当前尚未自动注册插件。');
}
function jsonData() {
  // A longitude picked on the time audit page is for that page only, so its result stays out of the export.
  const timeAudit = timeRun && timeRun.ownLongitude ? null : timeResult;
  return {birth_hour_unknown:currentHourUnknown, pillar_search:pillarResult, chart_import_check:importResult, date_scan:dateScanResult, consultation:consultResult, qimen:qimenResult, qimen_reference_audit:referenceAuditResult,ziwei_professional:professionalResult, ziwei_horoscope:horoscopeResult, bazi_dayun:dayunResult, birth_boundaries:boundaryResult, day_officers:officerResult, annual_timeline:timelineResult, decision_matrix:decisionResult, chart: current, calendar: calendarResult, lunar_inverse: lunarInverseResult, pair: pairResult, ziwei_pair: pairZiweiResult, group_relations: groupResult, rule_matrix: ruleMatrixResult, annual: annualResult, time_audit: timeAudit, birth_window: windowResult, report: reportResult, quality_audit: qualityResult};
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
    // The form sends 12:00 when the hour is unknown; the result says so instead of reading as a known time.
    const hourUnknown=birthCheck.checked&&$('#hour_unknown').checked, ticket=++consultTicket;
    launch.disabled=true; feedback.className='inline-msg progress'; feedback.textContent='正在按问题调用计算工具…';
    try{
      const reply=await postJSON('/api/consultation',payload);
      if(ticket!==consultTicket)return;
      consultResult={...reply,xsHourUnknown:hourUnknown};consultCursor=reply.continuation;consultRunKey=payload.birth?JSON.stringify(payload.birth):null;
      render();
      const head=$('#consult-head');if(head)head.focus({preventScroll:true});
      announce('咨询工作流已执行：'+(CW_STATUS[reply.status]||[reply.status])[0]);
    }
    catch(e){if(ticket===consultTicket){const box=$('#consult-feedback');if(box){box.className='inline-msg';box.textContent='执行失败：'+e.message;}}}
    finally{const button=$('#consult-run');if(button&&ticket===consultTicket)button.disabled=false;}
  });
  if(!consultResult)return;
  renderConsultationResult(consultResult);
}
// The consultation as it ran: what it was taken to be about and why, each tool it called with what came out and the
// observations drawn from it, what is still missing with a way to supply it, and how a follow-up carries on.
const CW_INTENTS = {natal: '本命分析', career: '事业/年度', relationship: '双人关系', timing: '多时刻查询', decision: '方案比较', rules: '规则分歧'};
const CW_STATUS = {completed: ['已完成', 'is-done'], partial: ['部分完成，还缺输入', 'is-partial'], needs_input: ['需要补充输入', 'is-missing']};
// The workbench page of each tool; a page is offered only for tools whose page shows the chart the consultation used.
const CW_TOOLS = {chart_quality_audit: ['排盘质量审计', 'quality'], deep_evidence_review: ['深度证据', 'deep'],
  annual_transformations: ['年干四化', 'annual'], bazi_dayun: ['大运干支', 'dayun'], birth_boundary_map: ['生时边界地图', 'boundaries'],
  structured_report: ['综合报告', 'report'], rule_comparison: ['规则差异对照'], pair_comparison: ['双人对照'], decision_matrix: ['方案决策']};
const CW_ROUTES = {'intent selected explicitly': '手动选择了场景', 'matrix supplied': '提供了方案评分', 'candidate_times supplied': '填写了候选时刻',
  'no domain keywords; inherited client-provided topic cursor': '没有场景关键词，沿用上一问的场景',
  'no domain keywords; default to natal structural review': '没有场景关键词，默认看本命结构'};
const CW_TYPES = {'user-provided': '你提供的', calculated: '计算结果', 'traditional-rule': '传统规则', 'user-assumption': '你的评分'};
function cwToolName(tool) {
  const m = /^qimen_hour_chart_(\d+)$/.exec(tool);
  return m ? ['奇门遁甲', ' · ', '候选', ' ' + m[1]] : [(CW_TOOLS[tool] || [tool])[0]];
}
// A star and its transformation, each translated whole; English puts a space between them (太阴化禄 → Tai Yin Hua Lu).
function cwPair(star, type) {const pair = elt('span', 'cw-pair'); append(pair, 'span', null, star); append(pair, 'span', null, type); return pair;}
// One line of what each tool came back with, read from its own result.
// shown: how many of the tool's observations the consultation kept for this question; hourUnknown: the birth time was
// a 12:00 stand-in.
function cwToolFact(tool, r, shown, hourUnknown) {
  if (!r) return null;
  if (tool === 'chart_quality_audit') {
    const n = r.flags.filter(f => f.severity === 'review').length;
    if (hourUnknown) return ['时辰不详：只检查了 12:00 占位时间', ' · ', n, ' 项需核对'];
    return n ? [n, ' 项需核对'] : ['没有需要核对的边界', ' · ', r.flags.length, ' 项提示'];
  }
  if (tool === 'deep_evidence_review') {
    const passed = r.checks.filter(c => c.passed).length;
    const count = shown < r.findings.length ? [r.findings.length, ' 条观察', ' · ', '下面列出与问题相关的', ' ' + shown, ' 条'] : [r.findings.length, ' 条观察'];
    return [...count, ' · ', '内部检查', ' ' + passed + '/' + r.checks.length, ' ', '通过'];
  }
  if (tool === 'annual_transformations') return [r.lunar_year, ' 农历年', ' ' + r.year_pillar, ' · ', ...r.transformations.flatMap((t, i) => [i ? ' ' : '', cwPair(t.star, t.type)])];
  if (tool === 'bazi_dayun') {
    // The start age moves with the birth time; with the hour unknown it is not stated (the 大运 page shows which parts hold).
    if (hourUnknown) return ['时辰不详：起运岁数随时辰而定', ' · ', r.periods.length, ' 步大运'];
    const p = r.start_age_traditional_parts;
    return [r.direction === 'forward' ? '顺排' : '逆排', ' · ', '起运约', ' ', p.years, ' 岁', ' ', p.months, ' 个月', ' · ', r.periods.length, ' 步大运'];
  }
  if (tool === 'birth_boundary_map') return ['误差', ' ±' + r.uncertainty_minutes, ' 分钟', ...((r.clipped_to_supported_range || []).length ? [' · ', '已截到支持范围'] : []), ' · ', r.boundaries.length, ' 个规则切换点'];
  if (tool === 'structured_report') return [r.sections.length, ' 节'];
  if (tool === 'decision_matrix' && r.ranked_options.length) return ['排在第一', ' ', r.ranked_options[0].name];
  if (/^qimen_hour_chart_/.test(tool)) return [r.solar_term, ' · ', r.dun, ' ' + r.bureau, ' 局', ' · ', r.yuan, ' · ', '值符', ' ', r.zhi_fu_star, ' · ', '值使', ' ', r.zhi_shi_door];
  return null;
}
function cwObservation(list, o) {
  const item = append(list, 'li', 'cw-ob');
  append(item, 'span', 'cw-type cw-type-' + o.type, CW_TYPES[o.type] || o.type);
  append(item, 'p', 'cw-ob-text', o.text);
  if (o.limit) texts(append(item, 'p', 'cw-ob-limit'), '适用边界：', o.limit);
  const src = append(item, 'p', 'cw-ob-src');
  append(src, 'span', null, '来源字段');
  append(src, 'code', null, o.path);
  (o.rule_ids || []).forEach(id => append(src, 'code', 'cw-rule', id));
  if ((o.evidence_paths || []).length) {
    const ev = append(src, 'span', 'cw-ev');
    texts(ev, ' · ', '证据', ' ' + o.evidence_paths.length, ' 项');
    tip(ev, o.evidence_paths.map((path, i) => path + '  sha256 ' + ((o.evidence_hashes || [])[i] || '').slice(0, 16)).join('\n'));
  }
  (o.method_references || []).forEach(href => {
    const a = append(src, 'a', 'cw-ref', '方法出处 ↗'); a.href = href; a.target = '_blank'; a.rel = 'noopener noreferrer';
  });
}
function renderConsultationResult(c) {
  const v = c.verification || {}, [statusText, statusClass] = CW_STATUS[c.status] || [c.status, ''];
  const head = append(result, 'section', 'cw-head ' + statusClass); head.id = 'consult-head'; head.tabIndex = -1;
  const line = append(head, 'div', 'cw-status');
  append(line, 'b', 'cw-badge', statusText);
  append(line, 'span', 'cw-intent', CW_INTENTS[c.intent] || c.intent);
  if (c.continuation && c.continuation.turns > 1) texts(append(line, 'span', 'cw-turn'), '对话轮次', ' ' + c.continuation.turns);
  const summary = append(head, 'p', 'cw-summary');
  if (!c.tool_trace.length) summary.textContent = '需要先补齐下面的输入才能计算';
  else texts(summary, c.tool_trace.length, ' 步可复现计算已执行', ' · ', c.missing_inputs.length ? '还缺部分输入，见下方' : '没有缺少的必需输入');
  if (c.xsHourUnknown) append(head, 'p', 'cw-hour-note', '出生时辰不详：本次按 12:00 占位计算，时柱、起运岁数和与时辰有关的观察都可能不同。');
  const why = append(head, 'p', 'cw-route');
  append(why, 'span', 'muted', '场景依据');
  c.routing_evidence.forEach(text => {
    const m = /^question mentions: (.+)$/.exec(text), part = append(why, 'span', 'cw-route-item');
    if (m) {part.append('问题里提到'); const word = append(part, 'q', null, m[1]); word.dataset.noI18n = '';}
    else part.textContent = CW_ROUTES[text] || text;
  });
  const badges = append(head, 'div', 'cw-badges');
  const checks = v.internal_checks || [];
  if (checks.length) {
    const passed = checks.filter(x => x.passed).length;
    const b = texts(append(badges, 'span', 'cw-chip' + (passed < checks.length ? ' is-warn' : '')), '内部检查', ' ' + passed + '/' + checks.length, ' ', '通过');
    tip(b, checks.map(x => (x.passed ? '✓ ' : '✗ ') + x.meaning).join('\n'));
  }
  if (c.xsHourUnknown) append(badges, 'span', 'cw-chip is-warn', '时辰不详：按 12:00 占位');
  const review = v.needs_human_review || c.xsHourUnknown;
  if (c.status !== 'needs_input') append(badges, 'span', 'cw-chip' + (review ? ' is-warn' : ''), review ? '需要人工复核' : '没有标记需复核');
  append(badges, 'span', 'cw-chip', '未经独立认证');
  append(badges, 'span', 'cw-chip', '服务器不保存本次资料');
  const tools = append(head, 'div', 'cw-tools');
  const copyBtn = append(tools, 'button', 'tiny-button', '复制咨询报告 Markdown'); copyBtn.type = 'button'; copyBtn.id = 'consult-copy-markdown';
  copyBtn.addEventListener('click', async () => {
    try {await navigator.clipboard.writeText(c.markdown); copyBtn.textContent = '已复制报告';}
    catch (_) {copyBtn.textContent = '复制失败，请使用旁边的下载功能';}
  });
  const exportBtn = append(tools, 'button', 'tiny-button', '导出咨询报告 Markdown ↓'); exportBtn.type = 'button'; exportBtn.id = 'consult-export-markdown';
  exportBtn.addEventListener('click', () => {const blob = new Blob([c.markdown], {type: 'text/markdown;charset=utf-8'}); const url = URL.createObjectURL(blob); const a = elt('a'); a.href = url; a.download = 'xuanshu-consultation.md'; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 2000);});

  if (c.missing_inputs.length) {
    append(result, 'h4', 'subheading', '需要补充');
    const missing = append(result, 'div', 'cw-missing'); missing.id = 'consult-missing';
    const openAdvanced = () => {consultAdvancedOpen = true; const d = $('#consult-advanced'); if (d) d.open = true;};
    const page = (name, label) => () => cwOpenPage(name, label);
    const fixes = {
      birth: ['勾选使用出生资料', () => {const box = $('#consult-use-birth'); box.checked = true; consultDraft.useBirth = true; box.focus();}],
      lunar_year: ['填写农历年', () => $('#consult-year').focus()],
      candidate_times: ['填写候选时刻', () => {openAdvanced(); $('#consult-candidates').focus();}],
      partner: ['填写第二人出生时间', () => {openAdvanced(); const box = $('#consult-use-partner'); box.checked = true; consultDraft.usePartner = true; $('#consult-partner-date').focus();}],
      dayun_direction_override: ['在出生资料里选性别', () => focusBirthField('gender')],
      matrix: ['去方案决策页填写', page('decision', '方案决策')],
      alternative_birth: ['去规则差异对照页', page('rule-matrix', '规则差异对照')],
    };
    const FIELDS = {birth: '出生资料', partner: '第二人出生资料', lunar_year: '农历年', candidate_times: '候选时刻', matrix: '方案与评分', alternative_birth: '第二套出生时基', dayun_direction_override: '大运顺逆'};
    c.missing_inputs.forEach(x => {
      const card = append(missing, 'div', 'cw-need'); card.id = 'consult-need-' + x.field;
      const top = append(card, 'div', 'cw-need-head');
      append(top, 'b', null, FIELDS[x.field] || x.field);
      append(top, 'code', null, x.field);
      append(card, 'p', null, x.reason);
      const fix = fixes[x.field];
      if (fix) {const go = append(card, 'button', 'tiny-button', fix[0]); go.type = 'button'; go.addEventListener('click', fix[1]);}
    });
  }

  const given = c.observations.filter(o => o.tool === 'user_input');
  if (given.length) {
    append(result, 'h4', 'subheading', '你提供的现实条件');
    const box = append(result, 'section', 'cw-given'); box.id = 'consult-given';
    const list = append(box, 'ul', 'cw-given-list');
    given.forEach(o => append(list, 'li', null, o.text));
    append(box, 'p', 'field-help', given[0].limit);
  }

  if (c.tool_trace.length) {
    append(result, 'h4', 'subheading', '执行轨迹与可核验观察');
    const steps = append(result, 'ol', 'cw-steps'); steps.id = 'consult-steps';
    const samePage = consultRunKey !== null && current && consultRunKey === JSON.stringify(currentInput);
    c.tool_trace.forEach(step => {
      const li = append(steps, 'li', 'cw-step'); li.id = 'consult-step-' + step.step;
      append(li, 'span', 'cw-step-no', String(step.step));
      const body = append(li, 'div', 'cw-step-body');
      const top = append(body, 'div', 'cw-step-head');
      texts(append(top, 'b'), ...cwToolName(step.tool));
      append(top, 'code', null, step.tool);
      const tab = (CW_TOOLS[step.tool] || [])[1];
      if (tab && samePage) {
        const name = (CW_TOOLS[step.tool] || [])[0];
        const open = append(top, 'button', 'tiny-button', '打开这一页'); open.type = 'button';
        open.setAttribute('aria-label', '打开' + name);
        open.addEventListener('click', () => {
          const year = c.tool_results.annual_transformations && c.tool_results.annual_transformations.lunar_year;
          // The year page opens on the year the consultation read.
          if (tab === 'annual' && year && (!annualResult || annualResult.lunar_year !== year)) {annualDraft = year; annualResult = null; autoOpened.delete('annual');}
          cwOpenPage(tab, name);
        });
      }
      append(body, 'p', 'cw-step-purpose', step.purpose);
      const obs = c.observations.filter(o => o.tool === step.tool);
      const fact = cwToolFact(step.tool, c.tool_results[step.tool], obs.length, c.xsHourUnknown);
      if (fact) {const line = append(body, 'p', 'cw-step-fact'); fact.forEach(x => line.append(x instanceof Node ? x : String(x)));}
      if ((step.field_paths || []).length) {
        const fields = append(body, 'p', 'cw-fields');
        append(fields, 'span', null, '读取字段');
        step.field_paths.forEach(path => append(fields, 'code', null, path));
      }
      if (obs.length) {const list = append(body, 'ul', 'cw-obs'); obs.forEach(o => cwObservation(list, o));}
    });
    const traced = new Set(c.tool_trace.map(x => x.tool));
    const rest = c.observations.filter(o => o.tool !== 'user_input' && !traced.has(o.tool));
    if (rest.length) {const list = append(result, 'ul', 'cw-obs'); rest.forEach(o => cwObservation(list, o));}
  }

  // A question opening with 那, 然后, 再看 and the like carries on with this topic; the birth input is sent again each time.
  const cur = c.continuation;
  if (cur && c.status !== 'needs_input') {
    const next = append(result, 'section', 'cw-next'); next.id = 'consult-next';
    append(next, 'h4', 'subheading', '继续追问');
    const carrying = !!consultCursor, year = cur.intent === 'career' && cur.lunar_year;
    const p = append(next, 'p');
    if (carrying) {
      // The cue words stay as typed: the server recognises them in either script.
      p.append('以「那」「然后」「再看」等开头续问时，沿用本次的场景：');
      append(p, 'b', null, CW_INTENTS[cur.intent] || cur.intent);
      if (year) texts(p, '；农历年', ' ' + year);
    } else p.textContent = '下一问按新话题识别，不沿用本次场景。';
    append(next, 'p', 'field-help', '出生资料每次都要重新勾选，服务器不保存；关键词明确时按新问题重新识别场景。');
    const row = append(next, 'div', 'cw-next-row');
    if (carrying && year && year < 2099) {
      // The question itself stays in Chinese: the follow-up cue 那 is what carries the topic on. A filled 农历年 field
      // would override the year in the question, so it moves on with it.
      const text = `那${year + 1}年呢？`;
      const b = append(row, 'button', 'tiny-button'); b.type = 'button'; b.id = 'consult-next-year';
      const words = append(b, 'span', null, text); words.dataset.noI18n = '';
      tip(b, '用同一场景续问下一年');
      b.addEventListener('click', () => {
        const q = $('#consult-question'), y = $('#consult-year');
        q.value = text; consultDraft.question = text;
        if (y && y.value.trim()) {y.value = String(year + 1); consultDraft.lunarYear = y.value;}
        q.focus();
      });
    }
    const fresh = append(row, 'button', 'tiny-button', carrying ? '换个话题（不沿用本次场景）' : '下一问按新话题识别'); fresh.type = 'button'; fresh.id = 'consult-fresh';
    fresh.disabled = !carrying; fresh.dataset.focusFallback = 'consult-question';
    // A scenario picked by hand would still win over the question's words, so it goes back to automatic as well.
    fresh.addEventListener('click', () => {consultCursor = null; consultDraft.intent = 'auto'; render(); $('#consult-question').focus(); announce('下一问按新话题识别');});
  }
  c.limitations.forEach(x => note(result, x));
}
// A link from the consultation to another page: the page opens, says so, and takes the focus.
function cwOpenPage(tab, name) {
  activateTab(tabs.find(t => t.dataset.tab === tab));
  result.focus({preventScroll: true});
  announce('已打开' + name);
}

// The data behind every tool, as a browser: one card per tool that has a result, each a collapsible tree that fills
// in as it opens, with a filter over keys and values, the path of every field, and copy or download per card.
const JV_SECTIONS = {chart: '当前命盘（八字、紫微与解读）', consultation: 'AI 咨询工作流', qimen: '奇门遁甲', qimen_reference_audit: '奇门逐宫核验',
  ziwei_professional: '专业紫微', ziwei_horoscope: '紫微运限', annual: '年干四化', bazi_dayun: '大运干支', calendar: '历法日历',
  lunar_inverse: '农历反查', day_officers: '建除值日', date_scan: '择日择时', annual_timeline: '年度轨迹', pair: '双人对照',
  ziwei_pair: '紫微叠盘', group_relations: '多人关系', decision_matrix: '方案决策', time_audit: '太阳时审计', birth_window: '出生时间窗口',
  rule_matrix: '规则差异对照', birth_boundaries: '生时边界地图', quality_audit: '排盘质量审计', pillar_search: '四柱反查',
  chart_import_check: '命盘导入核对', report: '综合报告'};
const JV_LIMIT = 400;  // matches drawn at most while filtering, across all cards
let jsonFilter = '', jsonView = 'tree', jsonDrawnStale = false;
const jvBytes = value => new Blob([JSON.stringify(value, null, 2)]).size;
const jvSize = bytes => bytes < 1024 ? bytes + ' B' : (bytes / 1024).toFixed(bytes < 10240 ? 1 : 0) + ' KB';
const jvPath = (path, key, array) => array ? path + '[' + key + ']' : /^[A-Za-z_$][\w$]*$/.test(key) ? path + '.' + key : path + '[' + JSON.stringify(key) + ']';
// Copy with the clipboard, or select the text for Ctrl+C where there is none (a plain-http address); either way it is
// announced and the label returns after a moment.
async function jvCopy(button, text) {
  if (!button.dataset.idle) button.dataset.idle = button.textContent;
  try {await navigator.clipboard.writeText(text()); button.textContent = '已复制'; announce('已复制');}
  catch (_) {
    const pre = elt('pre', 'jv-copy-fallback', text()); button.after(pre);
    const range = document.createRange(); range.selectNodeContents(pre);
    const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range);
    button.textContent = '已选中文字，请按 Ctrl+C 复制'; announce('已选中文字，请按 Ctrl+C 复制');
    setTimeout(() => pre.remove(), 15000);
  }
  clearTimeout(button.xsReset);
  button.xsReset = setTimeout(() => {if (button.isConnected) button.textContent = button.dataset.idle;}, 2500);
}
function jvSave(name, value) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], {type: 'application/json;charset=utf-8'}));
  const a = elt('a'); a.href = url; a.download = name; document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
// Paths whose key or value contains the query. found.total counts every match; only as many as the shared budget
// allows (JV_LIMIT across all cards) are kept to draw, and found.cut says some were left out.
function jvMatches(value, path, query, found) {
  if (!(value && typeof value === 'object')) return;
  const array = Array.isArray(value);
  (array ? value.map((v, i) => [String(i), v]) : Object.entries(value)).forEach(([k, v]) => {
    const p = jvPath(path, k, array);
    const byKey = !array && k.toLowerCase().includes(query);
    const byValue = !byKey && !(v && typeof v === 'object') && String(v).toLowerCase().includes(query);
    if (byKey || byValue) {
      found.total++;
      if (found.budget.left > 0) {found.budget.left--; found.hits.push(p); if (byValue) found.leaves.push(p);}
      else found.cut = true;
    }
    jvMatches(v, p, query, found);
  });
}
// While filtering, `keep` holds every path to draw: the matches and the paths above them, the latter also entered
// with a trailing \u0000 to mark them open. Below a matched object that is not above another match, all is drawn;
// a path entered with a trailing \u0001 holds a matched value, and all its fields are drawn for context.
const jvKeep = (keep, hits, path) => keep && hits.has(path) && !keep.has(path + '\u0000') ? null : keep;
function jvNode(parent, key, value, path, depth, keep, hits) {
  const object = value !== null && typeof value === 'object';
  if (!object) {
    const row = append(parent, 'div', 'jv-leaf' + (hits && hits.has(path) ? ' is-match' : '')); tip(row, path);
    if (key !== null) {append(row, 'span', 'jv-key', key); row.append(': ');}
    const type = value === null ? 'null' : typeof value;
    append(row, 'span', 'jv-' + type, type === 'string' ? JSON.stringify(value) : String(value));
    return;
  }
  const array = Array.isArray(value), entries = array ? value.map((v, i) => [String(i), v]) : Object.entries(value);
  const node = append(parent, 'details', 'jv-node' + (hits && hits.has(path) ? ' is-match' : ''));
  node.id = 'jv-' + path.replace(/\s/g, '_');
  const summary = append(node, 'summary'); tip(summary, path);
  if (key !== null) append(summary, 'span', 'jv-key', key);
  append(summary, 'span', 'jv-count', array ? '[' + entries.length + ']' : '{' + entries.length + '}');
  // A short list of plain values is previewed on the closed line.
  if (array && entries.length && entries.length <= 12 && entries.every(([, v]) => v === null || typeof v !== 'object'))
    append(summary, 'span', 'jv-preview', entries.map(([, v]) => typeof v === 'string' ? v : String(v)).join(', '));
  const fill = () => {
    if (node.dataset.filled) return;
    node.dataset.filled = '1';
    const box = append(node, 'div', 'jv-children');
    const whole = keep && keep.has(path + '\u0001');
    entries.forEach(([k, v]) => {
      const p = jvPath(path, k, array);
      if (!keep || whole || keep.has(p)) jvNode(box, k, v, p, depth + 1, keep && keep.has(p) ? jvKeep(keep, hits, p) : null, hits);
    });
    if (!box.childNodes.length) append(box, 'div', 'jv-leaf muted', array ? '[]' : '{}');
  };
  if (keep ? keep.has(path) && keep.has(path + '\u0000') : depth < 1) {node.open = true; fill();}
  node.addEventListener('toggle', () => {if (node.open) fill();});
}
function renderJson() {
  title(result, '结构化 JSON 数据', '当前命盘与各工具最近一次结果 · 只在本机 · 复制或下载才离开页面');
  // Stale for any reason the export button knows (edited birth data, a scan or import check of an earlier chart).
  const data = jsonData(), birthStale = !!current && JSON.stringify(readInput()) !== JSON.stringify(currentInput);
  const stale = birthStale || $('#download-json').disabled;
  jsonDrawnStale = stale;
  const order = Object.keys(JV_SECTIONS), rank = k => order.includes(k) ? order.indexOf(k) : order.length;
  const sections = Object.entries(data).filter(([k, v]) => k !== 'birth_hour_unknown' && v !== null && v !== undefined)
    .sort(([a], [b]) => rank(a) - rank(b));
  const head = append(result, 'div', 'jv-head');
  const facts = append(head, 'p', 'jv-facts');
  texts(facts, sections.length === 1 ? '1 个工具有结果' : sections.length + ' 个工具有结果', ' · ', '共', ' ' + jvSize(jvBytes(data)));
  if (data.birth_hour_unknown) texts(facts, ' · ', '时辰不详');
  const tools = append(head, 'div', 'jv-tools');
  const copyAll = append(tools, 'button', 'tiny-button', '复制全部 JSON'); copyAll.type = 'button'; copyAll.id = 'json-copy';
  copyAll.addEventListener('click', () => jvCopy(copyAll, () => JSON.stringify(jsonData(), null, 2)));
  const saveAll = append(tools, 'button', 'tiny-button', '下载全部 JSON ↓'); saveAll.type = 'button'; saveAll.id = 'json-download';
  saveAll.disabled = !current || stale;
  saveAll.addEventListener('click', () => $('#download-json').click());
  const views = append(tools, 'div', 'jv-views'); views.setAttribute('role', 'group'); views.setAttribute('aria-label', '显示方式');
  [['tree', '树状'], ['raw', '原始文本']].forEach(([key, label]) => {
    const b = append(views, 'button', 'tiny-button' + (jsonView === key ? ' is-active' : ''), label); b.type = 'button'; b.id = 'json-view-' + key;
    b.setAttribute('aria-pressed', String(jsonView === key));
    b.addEventListener('click', () => {jsonView = key; render();});
  });
  append(result, 'p', 'field-help', 'JSON 含出生日期和时间，以及用过的工具里填写的内容：咨询问题与现实条件、其他人的称呼与出生资料等，复制或下载后由你保管；备注不在其中。下载与命盘工作台右上角的「导出 JSON」相同，资料过期时不能下载。');
  if (birthStale) append(result, 'p', 'inline-msg', '出生资料已修改：下面仍是上一张命盘的数据。');
  else if (stale) append(result, 'p', 'inline-msg', '有结果属于上一张命盘（见上方提示）：重新运行后才能下载。');
  if (jsonView === 'raw') {append(result, 'pre', 'json-code', JSON.stringify(data, null, 2)).id = 'json-raw'; return;}
  if (!sections.length) {append(result, 'p', 'info-inline', '还没有任何结果：生成命盘或使用任一工具后，数据会出现在这里。'); return;}
  const row = append(result, 'div', 'inline-control jv-filter-row');
  const filter = createInput('筛选字段名或数值', 'search', jsonFilter, row); filter.id = 'json-filter'; filter.maxLength = 80;
  filter.setAttribute('aria-describedby', 'json-filter-count');
  const count = append(row, 'span', 'jv-filter-count'); count.id = 'json-filter-count'; count.setAttribute('role', 'status');
  const expand = elt('button', 'tiny-button', '全部收起'); expand.type = 'button'; expand.id = 'json-collapse';
  views.before(expand);
  const list = append(result, 'div', 'jv-list'); list.id = 'json-sections';
  const draw = () => {
    list.replaceChildren(); count.replaceChildren();
    const query = jsonFilter.trim().toLowerCase(), budget = {left: JV_LIMIT};
    let total = 0, shown = 0, cut = false;
    sections.forEach(([key, value]) => {
      let keep = null, hits = null;
      if (query) {
        const found = {hits: [], leaves: [], total: 0, cut: false, budget};
        jvMatches(value, key, query, found);
        total += found.total; cut = cut || found.cut;
        // A card found only by its name is shown whole; one with matches inside shows just those.
        const named = !found.total && (key.toLowerCase().includes(query) || (JV_SECTIONS[key] || '').toLowerCase().includes(query));
        if (named) total += 1;
        else if (!found.hits.length) return;
        if (!named) {
          hits = new Set(found.hits); keep = new Set();
          found.hits.forEach(p => {
            const parts = p.match(/^[^.[]+|\.[^.[]+|\[[^\]]*\]/g) || [p];
            let acc = '';
            parts.forEach((part, i) => {acc += part; keep.add(acc); if (i < parts.length - 1) keep.add(acc + '\u0000');});
          });
          found.leaves.forEach(p => keep.add(p.slice(0, p.length - p.match(/(\.[^.[]+|\[[^\]]*\])$/)[0].length) + '\u0001'));
        }
      }
      shown++;
      const card = append(list, 'section', 'jv-card'); card.id = 'json-section-' + key;
      const top = append(card, 'div', 'jv-card-head');
      const name = append(top, 'div', 'jv-name');
      append(name, 'b', null, JV_SECTIONS[key] || key);
      append(name, 'code', null, key);
      const fields = value && typeof value === 'object' ? (Array.isArray(value) ? value.length : Object.keys(value).length) : 1;
      // The size is that of the file the card downloads ({key: value}).
      texts(append(name, 'small', 'jv-meta'), fields === 1 ? '1 个字段' : fields + ' 个字段', ' · ', jvSize(jvBytes({[key]: value})));
      const actions = append(top, 'div', 'jv-actions');
      const copy = append(actions, 'button', 'tiny-button', '复制本节'); copy.type = 'button';
      // Source text, so the label follows a later language switch.
      copy.setAttribute('aria-label', '复制本节 ' + (JV_SECTIONS[key] || key));
      copy.addEventListener('click', () => jvCopy(copy, () => JSON.stringify({[key]: value}, null, 2)));
      const save = append(actions, 'button', 'tiny-button', '下载本节 ↓'); save.type = 'button';
      save.setAttribute('aria-label', '下载本节 ' + (JV_SECTIONS[key] || key));
      save.disabled = stale;
      save.addEventListener('click', () => {
        if ($('#download-json').disabled) {render(); return;}
        jvSave('xuanshu-' + key.replace(/_/g, '-') + '.json', {[key]: value});
      });
      const tree = append(card, 'div', 'jv-tree'); tree.dataset.noI18n = '';  // keys and values are data, not interface text
      if (value === null || typeof value !== 'object') jvNode(tree, null, value, key, 0, null, hits);
      else {
        const array = Array.isArray(value), whole = keep && keep.has(key + '\u0001');
        (array ? value.map((v, i) => [String(i), v]) : Object.entries(value)).forEach(([k, v]) => {
          const p = jvPath(key, k, array);
          if (!keep || whole || keep.has(p)) jvNode(tree, k, v, p, 1, keep && keep.has(p) ? jvKeep(keep, hits, p) : null, hits);
        });
      }
    });
    if (query) {
      if (!shown) texts(count, '没有匹配的字段或数值');
      else if (cut) texts(count, '共', ' ' + total, ' 处匹配', ' · ', '只显示前', ' ' + JV_LIMIT, ' 处');
      else texts(count, total === 1 ? '1 处匹配' : total + ' 处匹配');
    }
  };
  let timer = null;
  // The text is kept at once (a redraw meanwhile must not drop it); the tree follows after a pause in typing.
  filter.addEventListener('input', () => {jsonFilter = filter.value; clearTimeout(timer); timer = setTimeout(draw, 200);});
  expand.addEventListener('click', () => list.querySelectorAll('details[open]').forEach(d => {d.open = false;}));
  draw();
}
// A long page lists its sections under its title; a click scrolls to the section and moves the focus to its heading.
// Pages with their own section navigation (the Agent page, the deep review's evidence groups) and short pages go without.
const PAGE_INDEX_MIN = 3;
function pageIndex() {
  const intro = result.querySelector(':scope > .result-intro');
  // A section's heading counts too, as one level down (a sub-part's heading inside a section does not).
  const heads = [...result.querySelectorAll(':scope > h4.subheading, :scope > section > h4.subheading')].filter(head => head.textContent.trim());
  if (!intro || heads.length < PAGE_INDEX_MIN || result.querySelector('.ag-nav, .ev-toc') || result.scrollHeight < innerHeight * 1.6) return;
  const nav = elt('nav', 'page-index'); nav.id = 'page-index'; nav.setAttribute('aria-label', '本页目录');
  heads.forEach((head, i) => {
    head.id ||= 'section-' + active + '-' + i;
    head.tabIndex = -1;
    // An id lets render() put the focus back on the button after a redraw.
    const jump = append(nav, 'button', 'page-index-link', head.textContent); jump.type = 'button'; jump.id = head.id + '-jump'; jump.setAttribute('aria-controls', head.id);
    jump.addEventListener('click', () => {
      head.scrollIntoView({block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
      head.focus({preventScroll: true});
    });
  });
  intro.after(nav);
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
  fitStacks();
  pageIndex();
  result.querySelectorAll('details').forEach(d => {const key = detailKey(d); if (openState.has(key)) d.open = openState.get(key);});
  if (focusId && !result.contains(document.activeElement)) {
    let again = document.getElementById(focusId);
    if (again && again.disabled && again.dataset.focusFallback) again = document.getElementById(again.dataset.focusFallback);
    if (again && !again.disabled) {
      again.focus({preventScroll: true});
      if (caret && again.setSelectionRange) try {again.setSelectionRange(caret[0], caret[1]);} catch (_) { /* not a text field */ }
    }
  }
  autoOpen();
  // Again once the translator has put the interface language in: translated text can change what fits.
  requestAnimationFrame(() => {fitStacks(); markScrollAreas();});
}
// Boxes that scroll inside the page (a luck strip, the palace board on a phone, a wide table, a code block) take the
// keyboard focus while they overflow, so arrow keys scroll them without a mouse; a sideways one fades at the edge
// that has more to show. Nothing changes for a box that fits.
const SCROLL_AREAS = '.luck-strip,.ziwei-wrap,.fh-wrap,.yt-wrap,.dy-axis-wrap,.dm-wrap,.table-wrap,.json-code,.luck-timeline-wrap,.pf-board-wrap,.share-text,.pf-command code';
function scrollEdges(el) {
  el.classList.toggle('at-start', el.scrollLeft <= 1);
  el.classList.toggle('at-end', el.scrollLeft + el.clientWidth >= el.scrollWidth - 1);
}
function markScrollAreas() {
  document.querySelectorAll(SCROLL_AREAS).forEach(el => {
    // A text box scrolls by itself and keeps its own role and name.
    if (el.matches('textarea,input,select')) return;
    const sideways = el.scrollWidth > el.clientWidth + 1, scrolls = sideways || el.scrollHeight > el.clientHeight + 1;
    // A strip of buttons scrolls as the focus moves along it, so it needs no tab stop of its own.
    const wanted = scrolls && !el.querySelector('a[href],button,input,select,textarea,summary,[tabindex]:not([tabindex="-1"])');
    if (wanted && !('xsScroll' in el.dataset) && !el.hasAttribute('tabindex')) {
      el.tabIndex = 0; el.dataset.xsScroll = '';
      if (!el.hasAttribute('role')) {el.setAttribute('role', 'region'); el.dataset.xsRole = '';}
      if (!el.hasAttribute('aria-label') && !el.hasAttribute('aria-labelledby')) el.dataset.xsLabel = '';
    } else if (!wanted && 'xsScroll' in el.dataset) {
      ['tabindex', 'data-xs-scroll'].forEach(a => el.removeAttribute(a));
      if ('xsRole' in el.dataset) ['role', 'data-xs-role'].forEach(a => el.removeAttribute(a));
      if ('xsLabel' in el.dataset) ['aria-label', 'data-xs-label', 'data-i18n-aria-label'].forEach(a => el.removeAttribute(a));
    }
    if ('xsLabel' in el.dataset) {
      // The translator leaves <pre> and code alone, so their name is translated here, and again after a language switch.
      const source = sideways ? '可左右滚动的内容' : '可滚动的内容';
      const name = el.closest('pre,code,[data-no-i18n]') ? calT(source) : source;
      if (el.getAttribute('aria-label') !== name && el.getAttribute('data-i18n-aria-label') !== name) el.setAttribute('aria-label', name);
    }
    el.classList.toggle('xs-hscroll', sideways);
    if (sideways) {
      if (!el.xsEdges) {el.xsEdges = true; el.addEventListener('scroll', () => scrollEdges(el), {passive: true});}
      scrollEdges(el);
    }
  });
}
// Where the browser draws a select in the page's own style (appearance: base-select, Chromium 135+), the select is
// as wide as the option chosen, so picking a longer one pushes the controls beside it along. A select sized by its
// text keeps the width of its widest option instead, as the classic select does; one sized by its row (a full-width
// form field) is left alone, and none grows wider than the row it sits in.
const BASE_SELECT = typeof CSS !== 'undefined' && CSS.supports('appearance', 'base-select');
// Measured only while it is drawn: a folded section's content keeps a box but is not laid out.
const drawn = el => el.isConnected && (el.checkVisibility ? el.checkVisibility() : el.offsetParent !== null);
const steadyQueue = new Set();
const steadyKnown = new Map();
let steadyFrame = 0, steadyRuler = null;
// Selects are measured together just before the next paint, once translation has replaced their text.
function steadySelect(sel) {
  if (!BASE_SELECT) return;
  steadyQueue.add(sel);
  if (!steadyFrame) steadyFrame = requestAnimationFrame(measureSelects);
}
function measureSelects() {
  steadyFrame = 0;
  const ruler = (steadyRuler ||= document.createElement('canvas').getContext('2d'));
  const jobs = [], known = [];
  // Reads first: the text of every option is measured in the select's font, without laying the page out.
  steadyQueue.forEach(sel => {
    if (sel.multiple || sel.size > 1 || sel.options.length < 2 || !drawn(sel)) return;
    const style = getComputedStyle(sel);
    const labels = [...sel.options].map(option => option.label);
    // The appearance is part of the key: a contrast theme brings back the browser's own drop-down, sized its own way.
    const key = [sel.id, sel.className, style.font, style.appearance, innerWidth, ...labels].join('\n');
    if (sel.xsSteadyKey === key) return;
    if (steadyKnown.has(key)) {known.push([sel, key]); return;}
    ruler.font = style.font || `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
    let wide = 0, narrow = 0, most = -1, least = Infinity;
    labels.forEach((label, i) => {
      const width = ruler.measureText(label).width;
      if (width > most) {most = width; wide = i;}
      if (width < least) {least = width; narrow = i;}
    });
    jobs.push({sel, key, wide, narrow, chosen: sel.selectedIndex, same: most - least < 1});
  });
  steadyQueue.clear();
  const settle = (sel, key, minWidth) => {
    sel.style.minWidth = minWidth;
    if (minWidth) sel.dataset.xsSteady = '1'; else delete sel.dataset.xsSteady;
    sel.xsSteadyKey = key;
    if (steadyKnown.size > 300) steadyKnown.clear();
    steadyKnown.set(key, minWidth);
  };
  known.forEach(([sel, key]) => settle(sel, key, steadyKnown.get(key)));
  jobs.filter(job => job.same).forEach(job => settle(job.sel, job.key, ''));
  const measured = jobs.filter(job => !job.same);
  if (!measured.length) return;
  // Then the browser's own box for the shortest and the longest option, two layouts for all of them together. A select
  // whose box does not change between the two is sized by its row, or by a minimum width that fits every option.
  measured.forEach(job => {job.sel.style.minWidth = ''; job.sel.selectedIndex = job.narrow;});
  measured.forEach(job => {job.short = job.sel.getBoundingClientRect().width;});
  measured.forEach(job => {job.sel.selectedIndex = job.wide;});
  measured.forEach(job => {
    job.long = job.sel.getBoundingClientRect().width;
    // A percentage cannot cap it, since the label around a select is as wide as the select: the row's width does.
    const row = job.sel.parentElement && job.sel.parentElement.closest('div,form,fieldset,details,section,li,td');
    job.room = row ? row.clientWidth : Infinity;
  });
  measured.forEach(job => {
    job.sel.selectedIndex = job.chosen;
    settle(job.sel, job.key, job.long - job.short < 1 ? '' : Math.ceil(Math.min(job.long, job.room)) + 'px');
  });
}
if (BASE_SELECT) {
  // New selects, new options and translated option text are measured before the next paint.
  new MutationObserver(records => {
    records.forEach(record => {
      // A section opening: its selects are measured before the paint that shows them, not after its toggle event.
      if (record.type === 'attributes') {if (record.target.open) record.target.querySelectorAll('select').forEach(steadySelect); return;}
      const node = record.target.nodeType === 1 ? record.target : record.target.parentElement;
      const sel = node && node.closest('select');
      if (sel) steadySelect(sel);
      record.addedNodes.forEach(added => {
        if (added.nodeType !== 1) return;
        if (added.matches('select')) steadySelect(added);
        added.querySelectorAll('select').forEach(steadySelect);
      });
    });
  }).observe(document.body, {childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['open']});
  // A contrast theme switched on or off changes how a select is drawn, so every select is measured again.
  if (window.matchMedia) matchMedia('(forced-colors: active)').addEventListener('change', () => document.querySelectorAll('select').forEach(steadySelect));
  // A select that was hidden (a folded section, another tab) is measured when it is shown or first used.
  document.addEventListener('toggle', e => {if (e.target instanceof Element) e.target.querySelectorAll('select').forEach(steadySelect);}, true);
  // Measured at once on first use, before its list opens, so the list never sees the option change under it.
  ['pointerdown', 'focusin'].forEach(type => document.addEventListener(type, e => {
    if (!(e.target instanceof HTMLSelectElement)) return;
    steadySelect(e.target);
    cancelAnimationFrame(steadyFrame);
    measureSelects();
  }, true));
  document.querySelectorAll('select').forEach(steadySelect);
  // Only a change of width can change which selects are sized by their row; a phone's keyboard changes the height.
  let steadyWidth = innerWidth;
  window.addEventListener('resize', () => {
    if (innerWidth === steadyWidth) return;
    steadyWidth = innerWidth;
    document.querySelectorAll('select').forEach(steadySelect);
  });
}
let scrollAreaFrame = 0;
const remarkScrollAreas = () => {cancelAnimationFrame(scrollAreaFrame); scrollAreaFrame = requestAnimationFrame(() => {fitStacks(); markScrollAreas();});};
window.addEventListener('resize', remarkScrollAreas);
// Translated text is longer or shorter, so what overflows changes with the language even without a redraw.
document.addEventListener('xuanshu-language', remarkScrollAreas);
// So does the browser's text size, which a reader can change while the page is open: a hidden 1rem-wide probe
// resizes with it.
if (typeof ResizeObserver === 'function') {
  const probe = append(document.body, 'span', 'rem-probe');
  probe.setAttribute('aria-hidden', 'true');
  new ResizeObserver(remarkScrollAreas).observe(probe);
}
// A reply that comes back after another chart was cast belongs to the old chart, so it is dropped (STALE). So is one
// overtaken by a newer request to the same tool: a redraw while an automatic run is on its way brings back an enabled
// button, and a run pressed then must not be overwritten when the older reply lands after it.
const STALE = Symbol('stale');
const latestPost = {};
async function postForChart(url, body) {
  const chart = currentInput, ticket = latestPost[url] = (latestPost[url] || 0) + 1, data = await postJSON(url, body);
  return currentInput === chart && latestPost[url] === ticket ? data : STALE;
}
// Tools that need nothing but the chart shown and their settings show their result as soon as they open, once per
// chart, by pressing their own button; a changed setting still waits for that button. A tool whose button reads the
// birth form rather than the chart shown does not run while the form holds edits not yet cast (READS_CHART lists the
// ones that read the chart and so may run).
// While a page computes its first result, soft blocks in the rough shape of that result hold the space below it, so
// the page neither sits as one bare line nor jumps when the result lands. Screen readers skip the blocks.
const GHOST_COUNT = {strip: 10, cards: 6, table: 8, month: 35, board: 9};
function loadingGhost(parent, ...shapes) {
  const box = append(parent, 'div', 'xs-ghosts'); box.setAttribute('aria-hidden', 'true');
  shapes.forEach(shape => {
    const ghost = append(box, 'div', 'xs-ghost xs-ghost-' + shape);
    for (let i = 0; i < GHOST_COUNT[shape]; i++) append(ghost, 'span');
  });
  return box;
}
// A placeholder while ``run``'s request is out. It goes when the page redraws with the result, or when the button is
// enabled again after a failure that only wrote a message.
function ghostWhileBusy(run, ...shapes) {
  const ghost = loadingGhost(result, ...shapes);
  const watch = new MutationObserver(() => {if (!run.isConnected || !run.disabled) {ghost.remove(); watch.disconnect();}});
  watch.observe(run, {attributes: true, attributeFilter: ['disabled']});
}
// Before a page's first result: what it will list, over a still outline of its shape. The outline shimmers while the
// page's button has a request out (``busy`` when the page is drawn mid-run), and stops again if the run fails.
function emptyPreview(parent, run, items, shapes, busy = false) {
  const box = append(parent, 'div', 'xs-empty' + (busy ? ' is-busy' : ''));
  append(box, 'p', 'xs-empty-head', '结果会列出');
  const list = append(box, 'ul', 'xs-empty-list');
  items.forEach(item => append(list, 'li', null, item));
  loadingGhost(box, ...shapes).classList.add('is-idle');
  // Listening after the page's own handler: a click that only wrote a message leaves the button enabled.
  run.addEventListener('click', () => {if (run.disabled) box.classList.add('is-busy');});
  new MutationObserver(() => {if (!run.disabled) box.classList.remove('is-busy');}).observe(run, {attributes: true, attributeFilter: ['disabled']});
  return box;
}
const AUTO_OPEN = {
  annual: ['annual-run', () => annualResult, () => annualDraft !== null || !todayLunarPending],
  timeline: ['timeline-run', () => timelineResult, () => timelineDraft.start_lunar_year !== null || !todayLunarPending],
  boundaries: ['boundary-run', () => boundaryResult],
  quality: ['quality-run', () => qualityResult],
  time: ['time-run', () => timeResult, () => readInput().longitude !== null],
  deep: ['deep-run', () => deepResult],
};
// The rough shape of each page's first result, drawn while the automatic run is out.
const AUTO_GHOST = {annual: ['cards', 'table'], timeline: ['table'], boundaries: ['table'], quality: ['cards', 'table'], time: ['table'], deep: ['cards']};
const READS_CHART = new Set(['annual', 'timeline']);
let autoOpened = new Set();
function autoOpen() {
  const [button, shown, possible = () => true] = AUTO_OPEN[active] || [];
  if (!button || !current) return;
  if (currentHourUnknown) {
    // A chart cast without the hour stands on a 12:00 placeholder, so nothing hour-bound runs on it by itself.
    const intro = result.querySelector('.result-intro');
    if (intro) intro.after(elt('p', 'field-help', '命盘时辰不详：本页按 12:00 占位时辰计算，时柱、宫位和时辰交界都不可靠，所以打开时不自动计算。'));
    return;
  }
  if (shown() || autoOpened.has(active) || !possible()) return;
  if (!READS_CHART.has(active) && JSON.stringify(readInput()) !== JSON.stringify(currentInput)) return;
  autoOpened.add(active);
  const tab = active;
  setTimeout(() => {
    const run = document.getElementById(button);
    if (!(active === tab && run && !run.disabled)) return;
    run.click();
    // A run that went out leaves its button disabled.
    if (run.disabled && !shown()) ghostWhileBusy(run, ...AUTO_GHOST[tab]);
  });
}
// What was typed into a tool's settings but not yet applied survives a redraw, such as the one an automatic
// result brings while the field is being edited.
const typedValues = {};
function keepTyped(...fields) {
  fields.forEach(field => {
    if (typedValues[field.id] !== undefined) field.value = typedValues[field.id];
    field.addEventListener(field.tagName === 'SELECT' ? 'change' : 'input', () => {typedValues[field.id] = field.value;});
  });
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
    taijiMark(empty, 'empty-orbit');
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
// The open tab's pill slides over from the tab that was open before, so the eye follows the switch. The first
// activation on load has nothing to slide from.
let tabsShown = false;
function slideTabPill(from, to) {
  const strip = $('#workspace-tabs');
  strip.querySelectorAll('.tab-pill').forEach(old => old.remove());
  tabs.forEach(other => other.classList.remove('pill-arriving'));
  if (!from || from === to || matchMedia('(prefers-reduced-motion: reduce)').matches || typeof to.animate !== 'function') return;
  const a = from.getBoundingClientRect(), b = to.getBoundingClientRect(), s = strip.getBoundingClientRect();
  if (!a.width || !b.width) return;
  const pill = append(strip, 'span', 'tab-pill'); pill.setAttribute('aria-hidden', 'true');
  pill.style.left = b.left - s.left - strip.clientLeft + strip.scrollLeft + 'px';
  pill.style.top = b.top - s.top - strip.clientTop + strip.scrollTop + 'px';
  pill.style.width = b.width + 'px'; pill.style.height = b.height + 'px';
  to.classList.add('pill-arriving');
  const slide = pill.animate([
    {transform: `translate(${a.left - b.left}px, ${a.top - b.top}px)`, width: a.width + 'px', height: a.height + 'px'},
    {transform: 'none', width: b.width + 'px', height: b.height + 'px'},
  ], {duration: 280, easing: 'cubic-bezier(.2, .7, .2, 1)'});
  const land = () => {pill.remove(); to.classList.remove('pill-arriving');};
  slide.onfinish = land; slide.oncancel = land;
}
function activateTab(tab, updateUrl = true) {
  if (!tab) return;
  const previous = tabsShown ? tabs.find(other => other.classList.contains('active')) : null;
  tabsShown = true;
  active = tab.dataset.tab;
  recentTools = [tab, ...recentTools.filter(other => other !== tab)].slice(0, RECENT_LIMIT + 1);
  result.setAttribute('aria-labelledby', tab.id);
  tabs.forEach(other => {
    const selected = other === tab;
    other.classList.toggle('active', selected);
    other.setAttribute('aria-selected', String(selected));
    other.tabIndex = selected ? 0 : -1;
  });
  slideTabPill(previous, tab);
  if (updateUrl && /^https?:$/.test(location.protocol)) {
    history.replaceState(null, '', '#tool=' + active);
  }
  updateToolNavigation();
  // On a phone the tabs are one sideways strip: bring the opened one into view, as a #tool= link or an in-page
  // "open …" button may pick a tab far outside it. Only the strip scrolls, never the page.
  const strip = $('#workspace-tabs');
  if (strip.scrollWidth > strip.clientWidth) {
    const left = tab.getBoundingClientRect().left - strip.getBoundingClientRect().left + strip.scrollLeft, right = left + tab.offsetWidth;
    if (left < strip.scrollLeft + 16 || right > strip.scrollLeft + strip.clientWidth - 24)
      strip.scrollTo({left: Math.max(0, left - (strip.clientWidth - tab.offsetWidth) / 2), behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
  }
  // Restart the fade-in for the newly opened tool (style.css: #result.is-entering).
  result.classList.remove('is-entering'); void result.offsetWidth; result.classList.add('is-entering');
  render();
  // The Qimen page opens on the chart of this moment, which its picker offers first; other moments wait for the button.
  if (active === 'qimen' && qimenMoment.mode === 'now' && !qimenResult) {
    const run = $('#qimen-run');
    if (run && !run.disabled) {run.click(); if (run.disabled) ghostWhileBusy(run, 'board');}
  }
}
tabs.forEach(tab => tab.addEventListener('click', () => activateTab(tab)));
// A screen past the tool tabs, a round button brings them back, and the opened tool's tab takes the focus.
const toTop = $('#to-top');
let toTopFrame = 0;
function placeToTop() {
  toTopFrame = 0;
  toTop.classList.toggle('is-shown', $('#workspace-tabs').getBoundingClientRect().bottom < -innerHeight);
}
['scroll', 'resize'].forEach(type => window.addEventListener(type, () => {toTopFrame ||= requestAnimationFrame(placeToTop);}, {passive: true}));
toTop.addEventListener('click', () => {
  $('#workspace').scrollIntoView({block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
  const tab = tabs.find(other => other.classList.contains('active'));
  if (tab) tab.focus({preventScroll: true});
});
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
    // Pressed again while the box has the focus, the list still opens.
    showPalette();
  }
  // ? lists every shortcut, except where it is typed (a text field) or another dialog is open.
  const typing = event.target instanceof Element && event.target.closest('input,textarea,select,[contenteditable]:not([contenteditable=false])');
  if (event.key === '?' && !event.ctrlKey && !event.metaKey && !event.altKey && !typing && !document.querySelector('dialog[open]')) {
    event.preventDefault();
    openShortcuts();
  }
});
// Every keyboard shortcut in one place, grouped by where it works. Keys are drawn as keycaps; on a Mac Ctrl is ⌘.
const ON_MAC = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent || '');
const SHORTCUTS = [
  ['任何地方', [[['Ctrl', 'K'], '查找功能或操作'], [['?'], '打开这份快捷键说明'], [['Esc'], '关闭对话框、日历或提示']]],
  ['功能查找', [[['Ctrl', 'K'], '框里不输入时列出本次打开过的功能'], [['↑', '↓'], '在匹配的功能和操作之间移动'], [['Enter'], '打开功能或执行操作'], [['Esc'], '清空查找']]],
  ['功能标签', [[['←', '→'], '上一个 / 下一个功能'], [['Home', 'End'], '第一个 / 最后一个功能']]],
  ['日期框和日历', [[['Alt', '↓'], '打开日历（也可以按 F4）'], [['←', '→', '↑', '↓'], '逐日、逐周移动'],
    [['Home', 'End'], '本周第一天 / 最后一天'], [['Page Up', 'Page Down'], '上个月 / 下个月，加 Shift 换年'], [['Enter'], '选定这一天']]],
  ['历法日历', [[['←', '→', '↑', '↓'], '逐日、逐周移动'], [['Home', 'End'], '本周第一天 / 最后一天'], [['Page Up', 'Page Down'], '上个月 / 下个月']]],
  ['命盘', [[['←', '→', '↑', '↓'], '在紫微宫位或五行之间移动'], [['Enter'], '选中当前宫位或五行']]],
  ['AI 对话', [[['Enter'], '发送'], [['Shift', 'Enter'], '换行'], [['Esc'], '停止生成']]],
];
function openShortcuts() {
  let dialog = $('#shortcuts-dialog');
  if (!dialog) {
    dialog = elt('dialog', 'share-dialog shortcuts-dialog'); dialog.id = 'shortcuts-dialog';
    dialog.setAttribute('aria-labelledby', 'shortcuts-title');
    document.body.append(dialog);
  }
  dialog.replaceChildren();
  const head = append(dialog, 'div', 'share-head');
  append(head, 'h3', null, '键盘快捷键').id = 'shortcuts-title';
  const close = append(head, 'button', 'tiny-button', '关闭'); close.type = 'button'; close.id = 'shortcuts-close';
  close.addEventListener('click', () => dialog.close());
  const groups = append(dialog, 'div', 'sc-groups');
  SHORTCUTS.forEach(([name, rows]) => {
    const group = append(groups, 'section', 'sc-group');
    const title = append(group, 'h4', null, name);
    title.id = 'sc-' + SHORTCUTS.findIndex(g => g[0] === name);
    const list = append(group, 'dl', 'sc-list'); list.setAttribute('aria-labelledby', title.id);
    rows.forEach(([keys, what]) => {
      const row = append(list, 'div', 'sc-row');
      const combo = append(row, 'dt', 'sc-keys'); combo.dataset.noI18n = '';
      // Keys pressed together are joined by +; a set of arrows is one choice among them.
      const together = keys.length === 2 && ['Ctrl', 'Alt', 'Shift'].includes(keys[0]);
      keys.forEach((key, i) => {
        if (i) append(combo, 'span', 'sc-join', together ? '+' : ' ');
        append(combo, 'kbd', null, key === 'Ctrl' && ON_MAC ? '⌘' : key);
      });
      append(row, 'dd', null, what);
    });
  });
  append(dialog, 'p', 'field-help', '在文本框里输入时，这些按键照常输入文字；? 只在焦点不在输入框时打开本说明。');
  if (!dialog.open) dialog.showModal();
  close.focus();
}
$('#shortcuts-open').addEventListener('click', openShortcuts);
window.addEventListener('hashchange', () => {
  const tab = tabFromHash();
  if (tab && tab.dataset.tab !== active) activateTab(tab, false);
});
// Keep old results visible for reference, but mark them as stale and
// disable export when the user edits any birth parameter.
function updateStaleBirthNotice() {
  recheckFieldProblems();
  hideStaleDstChoice();  // also for values set directly (时辰不详, a lunar date) rather than typed
  const fingerprint=JSON.stringify(readInput());
  const outdatedChart=!!currentInput && fingerprint !== JSON.stringify(currentInput);
  const outdatedQimen=!!qimenResult && !!qimenFingerprint && fingerprint !== qimenFingerprint;
  const outdated=outdatedChart || outdatedQimen || dateScanStale() || importStale();
  $('#stale-birth-warning').hidden = !outdated;
  // The collapsed summary's dot means the chart on screen was cast from exactly this data.
  $('#input-panel').classList.toggle('is-current', !!currentInput && !outdatedChart);
  const importNotice = document.getElementById('import-stale'); if (importNotice) importNotice.hidden = !importStale();
  if (outdated) {
    $('#result-subtitle').textContent = '出生资料已更改：旧命盘需要重新生成';
    $('#download-json').disabled = true;
  } else if (currentInput) {
    $('#result-subtitle').textContent = currentInput.birth_datetime.replace('T',' ') + ' · ' + currentInput.timezone;
    $('#download-json').disabled = false;
  }
  // The data page offers downloads only while the export does; it redraws when that changes.
  if (active === 'json' && current && jsonDrawnStale !== $('#download-json').disabled) render();
}
for (const type of ['input','change']) {
  form.addEventListener(type, event => {
    if (event.target.id !== 'api_token') updateStaleBirthNotice();
    else if (type === 'change' && active === 'integration' && (capabilitiesError || (agentCatalog && agentCatalog.failed))) render();
    else if (type === 'change' && active === 'professional' && capabilitiesError) render();
    // The professional page's guards and its stale-result note follow every birth field as it changes.
    if (type === 'change' && active === 'professional' && event.target.id !== 'api_token') render();
  });
}
// The browser's own validation bubble ignores the colour theme and speaks the browser's language rather than the
// interface's ("Please enter a valid value. The two nearest valid values are…"). The form checks itself instead:
// each problem is written under its field in the interface language, the field is marked for screen readers and
// focused, and the message clears as soon as the value is fixed. The lunar converter's fields have their own button
// and never hold back the birth form.
const FIELD_PROBLEMS = {
  birth_datetime: {valueMissing: '请填写出生日期与时间', badInput: '日期或时间没填完整：年、月、日、时、分都要填',
    rangeUnderflow: '出生时间需在 1901 年到 2099 年之间', rangeOverflow: '出生时间需在 1901 年到 2099 年之间'},
  longitude: {valueMissing: '按太阳时计算需要出生地经度：选择出生城市，或填写经度（东经为正、西经为负）',
    badInput: '经度只能填数字，例如 104.0667', rangeUnderflow: '经度需在 -180 到 180 之间（东经为正、西经为负）',
    rangeOverflow: '经度需在 -180 到 180 之间（东经为正、西经为负）', stepMismatch: '经度最多保留 4 位小数，例如 104.0667'},
};
// In this order: a half-typed date is both missing and bad input, and the half-typed part is what to fix.
const GENERIC_PROBLEMS = {badInput: '格式不正确', valueMissing: '这一项需要填写', typeMismatch: '格式不正确',
  rangeUnderflow: '超出可填写的范围', rangeOverflow: '超出可填写的范围', stepMismatch: '数值的精度超出范围', tooLong: '内容太长'};
const checkedFields = () => [...form.elements].filter(el => el.willValidate && !el.closest('#lunar-entry'));
function fieldProblem(el) {
  if (el.validity.valid) return '';
  const kind = Object.keys(GENERIC_PROBLEMS).find(key => el.validity[key]) || 'badInput';
  return (FIELD_PROBLEMS[el.id] || {})[kind] || GENERIC_PROBLEMS[kind];
}
function showFieldProblem(el, text) {
  const id = el.id + '-problem';
  let note = document.getElementById(id);
  const described = (el.getAttribute('aria-describedby') || '').split(' ').filter(x => x && x !== id);
  if (!text) {
    if (note) note.remove();
    el.removeAttribute('aria-invalid');
    if (described.length) el.setAttribute('aria-describedby', described.join(' ')); else el.removeAttribute('aria-describedby');
    return;
  }
  if (!note) {note = elt('p', 'field-problem'); note.id = id; el.after(note);}
  note.textContent = text;
  el.setAttribute('aria-invalid', 'true');
  el.setAttribute('aria-describedby', [...described, id].join(' '));
}
form.noValidate = true;
form.addEventListener('submit', event => {
  const bad = checkedFields().filter(el => !el.validity.valid);
  checkedFields().forEach(el => showFieldProblem(el, fieldProblem(el)));
  if (!bad.length) return;
  // Runs before the casting handler below (a capture listener on the form itself goes first) and stops it.
  event.preventDefault(); event.stopImmediatePropagation();
  // An error from an earlier cast no longer applies to what is on the form now.
  $('#error').hidden = true; $('#dst-choice').hidden = true;
  setBirthPanelCollapsed(false);
  const first = bad[0], section = first.closest('details');
  if (section) section.open = true;
  first.focus();
  // Emptied first, so the same words said again (Enter pressed twice in the same field) are read again.
  announce(''); requestAnimationFrame(() => announce(fieldProblem(first)));
}, true);
// Every field already marked is checked again whenever the birth data changes: typed, filled by a city choice (which
// also drops or brings back the need for a longitude), by the lunar converter or from a saved profile. Nothing is
// marked on leaving a field: the note it adds would push the 生成命盘 button down under a pointer on its way to it.
function recheckFieldProblems() {
  form.querySelectorAll('[aria-invalid=true]').forEach(el => showFieldProblem(el, fieldProblem(el)));
}
for (const type of ['input', 'change']) form.addEventListener(type, recheckFieldProblems);
// Enter in the lunar fields converts the lunar date (as the button beside them does) instead of casting a chart from
// the Gregorian date above, which those fields do not change.
$('#lunar-entry').addEventListener('keydown', event => {
  if (event.key !== 'Enter' || !(event.target instanceof HTMLInputElement) || event.isComposing) return;
  event.preventDefault();
  $('#lunar-fill').click();
});
form.addEventListener('submit', async event => {
  event.preventDefault();
  const run = $('#run-btn'); const error = $('#error');
  error.hidden = true;
  const local = $('#birth_datetime').value, zone = $('#timezone').value, guessed = !chosenOffset();
  $('#dst-choice').hidden = true;
  run.disabled = true; run.setAttribute('aria-busy', 'true'); run.querySelector('span').textContent = '正在计算…';
  const data = readInput();
  try {
    const [chart, reading] = await Promise.all([
      postJSON('/api/combined', data), postJSON('/api/analyze', data),
    ]);
    current = {...chart, reading}; currentInput = data; document.body.classList.add('has-chart');
    consultResult=null;consultCursor=null;consultRunKey=null;
    // A pasted-chart check belongs to the chart it ran on, unless this cast is the one its rule or hour asked for.
    if (!importRecheck) {importResult = null; importBirth = null; importHourPick = null; importFocusAfter = false;}
    pairResult = null; pairZiweiResult = null; annualResult = null; timelineResult=null; timeResult = null; timeRun = null; timeLongitude = ''; windowResult = null; reportResult = null; deepResult=null; qualityResult = null;
    dayunResult=null;dayunKey=null;dayunError='';autoOpened=new Set();boundaryResult=null;qimenResult=null;qimenFingerprint=null;qimenTicket++;professionalResult=null;professionalSent=null;professionalError=null;professionalTicket++;professionalPending=false;if (!referenceAuditResult || referenceAuditResult.xsMode !== 'custom') {referenceAuditResult=null;referenceAuditChart=null;referenceAuditSent=null;}
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
  } catch (err) {
    importRecheck = false; importFocusAfter = false;
    // The message or question sits in the form, so a folded form opens to show it.
    setBirthPanelCollapsed(false);
    // A repeated or skipped clock time: ask which offset the clock showed, then cast again with it.
    const asked = guessed && serverDstCase(err.detail, local, zone);
    if (asked && $('#birth_datetime').value === local && $('#timezone').value === zone) showDstChoice(asked);
    else {error.textContent = '计算失败：' + friendlyError(err.message); error.hidden = false; announce(error.textContent);}
  }
  finally {run.disabled = false; run.removeAttribute('aria-busy'); run.querySelector('span').textContent = '生成命盘';}
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
  $('#load-profile').disabled = $('#remove-profile').disabled = !list.length;
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
$('#remove-profile').addEventListener('click', async () => {
  const chosen = $('#profiles').value;
  if (!chosen) {setFeedback('请选择要删除的档案'); return;}
  if (!await xsConfirm('删除所选档案？它在本机保存的对话、记忆和人生事件也会一起删除。', {confirmLabel: '删除', danger: true})) return;
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
// The form folds into a one-line summary: on a small screen after each cast so the workspace is reachable, on a wide
// screen when the user folds it, and the workspace then takes the full width.
const genderLabels={male:'男',female:'女',unspecified:'不指定顺逆'};
function updateBirthSummary(){
  const input=readInput(), pieces=[];
  pieces.push($('#hour_unknown').checked?[input.birth_datetime.slice(0,10),'时辰不详']:[input.birth_datetime.replace('T',' ')]);
  // The city's own (Chinese) name, so the translator renders it in whatever language is chosen now.
  if($('#birth_city').value)pieces.push([$('#birth_city').value]);
  pieces.push([input.timezone],[genderLabels[input.gender]||input.gender]);
  // A rule that differs from the defaults (clock time, no 23:00 rollover, leap month follows on) changes the chart.
  const mode=$('#time_mode').value;
  if(mode!=='clock')pieces.push([{mean_solar:'平太阳时',apparent_solar:'真太阳时'}[mode]]);
  if($('#late_zi_day_rollover').checked)pieces.push(['23:00 换日']);
  if(!$('#leap_month_second_half_as_next').checked)pieces.push(['闰月不顺延']);
  const box=$('#birth-summary-text');box.replaceChildren();
  pieces.flat().forEach((text,i)=>{if(i)box.append(' · ');box.append(text);});
}
function setBirthPanelCollapsed(collapsed){
  $('#input-panel').classList.toggle('collapsed',collapsed);
  $('#input-panel').parentElement.classList.toggle('birth-collapsed',collapsed);
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
document.addEventListener('xuanshu-language',updateBirthSummary);
// A link to a birth field opens the folded form first, so the focus lands on something visible.
function focusBirthField(id){
  setBirthPanelCollapsed(false);
  const field=$('#'+id);field.scrollIntoView({block:'center'});field.focus();
}
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
    // English star and bureau names are set in the sans face; the Chinese serif's Latin letters are often Times.
    const rowFont = document.documentElement.lang.startsWith('en') ? sans : serif;
    rows.forEach(([label, value]) => {
      text(label, PAD, ry, 20, token('--muted'));
      // A list that would not fit on one line at a readable size continues on a second line.
      let lines = Array.isArray(value) ? [value.join('  ·  ')] : [value];
      g.font = `600 26px ${rowFont}`;
      if (Array.isArray(value) && g.measureText(lines[0]).width > W - PAD * 2) {
        const half = Math.ceil(value.length / 2);
        lines = [value.slice(0, half).join('  ·  '), value.slice(half).join('  ·  ')];
      }
      lines.forEach((line, n) => text(line, PAD, ry + 38 + n * 40, 32, token('--text'), rowFont, 'left', '600'));
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

// Relation card: the group or pair result as a PNG drawn on a local canvas. It shows the names as typed, the
// four pillars, the labels between each pair and, with a year, the luck timeline; never birth dates, times or
// notes. Nothing is uploaded.
function relationCardData(kind) {
  if (kind === 'pair') {
    const r = pairResult;
    return {kind, title: '双人对照卡片', file: 'xuanshu-pair.png', people: [{...r.person_a, label: 'A'}, {...r.person_b, label: 'B'}],
      pairs: [{a: 0, b: 1, day_stems: r.day_stems, label_counts: r.label_counts}], year_view: r.year_view, tags: ['A', 'B'], named: false};
  }
  const g = groupResult;
  // Only so many pairs fit: those the page is looking at (the member picked, the label filtered) come first.
  const filter = groupDraft.filter, focus = groupDraft.focus;
  const rank = p => (focus === null || p.a === focus || p.b === focus ? 0 : 2) + (filter === 'all' || pairHas(p, filter) ? 0 : 1);
  const pairs = g.pairs.map((p, i) => [rank(p), i, p]).sort((x, y) => x[0] - y[0] || x[1] - y[1]).map(x => x[2]);
  // Each member is numbered, so pairs and timeline rows stay apart even when long names are cut short.
  return {kind, title: '多人关系卡片', file: 'xuanshu-group.png', people: g.members, pairs, year_view: g.year_view,
    tags: g.members.map((_, i) => '①②③④⑤⑥⑦⑧'[i]), named: true};
}
const RELATION_CARD_PAIRS = 10;
const LINK_TOKEN = {'六合': '--green', '六冲': '--red', '六害': '--warn', '相刑': '--quan', '同支': '--muted'};
// Characters as the reader sees them, so a cut never splits an emoji or an accented letter.
const graphemes = value => typeof Intl === 'object' && Intl.Segmenter
  ? Array.from(new Intl.Segmenter().segment(value), s => s.segment) : Array.from(value);
function drawRelationCard(canvas, data, withLuck) {
  const T = text => typeof translateText === 'function' ? translateText(text) : text;
  const css = getComputedStyle(document.documentElement), token = name => css.getPropertyValue(name).trim();
  const sans = "'Noto Sans SC','PingFang SC','Microsoft YaHei',sans-serif", serif = "'Noto Serif SC','Songti SC','STSong',serif";
  const W = 1080, PAD = 64, inner = W - PAD * 2, CHIPS_X = PAD + 316;
  const people = data.people, v = data.year_view, tags = data.tags;
  const shownPairs = data.pairs.slice(0, RELATION_CARD_PAIRS);
  const rows = v && withLuck ? v.luck_timeline || [] : [];
  canvas.width = W; canvas.height = 1;
  const g = canvas.getContext('2d');
  // Cuts a value to max pixels in the current font, keeping its start and its end (a "(2)" suffix survives).
  const fitMiddle = (value, max) => {
    if (g.measureText(value).width <= max) return value;
    const chars = graphemes(value);
    let head = Math.ceil(chars.length / 2), tail = chars.length - head;
    const joined = () => chars.slice(0, head).join('') + '…' + chars.slice(chars.length - tail).join('');
    while (head + tail > 1 && g.measureText(joined()).width > max) {if (head >= tail) head--; else tail--;}
    return joined();
  };
  const named = i => data.named ? tags[i] + ' ' + people[i].label : people[i].label;
  // Each pair's labels as chips, laid out before the height is known: they wrap onto more lines in long languages.
  const chipsOf = pair => [...(pair.day_stems.combination ? [[T(pair.day_stems.combination), '--green']] : []),
    ...LINK_TYPES_ORDER.filter(type => pair.label_counts[type]).map(type => [T(type) + ' ' + pair.label_counts[type], LINK_TOKEN[type]])];
  const layoutChips = chips => {
    g.font = `400 18px ${sans}`;
    let x = CHIPS_X, line = 0;
    return chips.map(([label, color]) => {
      const width = Math.min(g.measureText(label).width + 20, W - PAD - CHIPS_X);
      if (x > CHIPS_X && x + width > W - PAD) {x = CHIPS_X; line += 1;}
      const placed = {label, color, x, line, width}; x += width + 8;
      return placed;
    });
  };
  // The day-stem ten god each way with its direction (① → ②, ② → ①); on two lines when both do not fit on one.
  const tenGodLines = pair => {
    const [a, b] = [tags[pair.a], tags[pair.b]];
    const one = `${a}→${b} ${pair.day_stems.a_sees_b ? T(pair.day_stems.a_sees_b) : '？'}`;
    const two = `${b}→${a} ${pair.day_stems.b_sees_a ? T(pair.day_stems.b_sees_a) : '？'}`;
    g.font = `400 17px ${sans}`;
    return g.measureText(one + ' · ' + two).width > CHIPS_X - PAD - 16 ? [one, two] : [one + ' · ' + two];
  };
  const pairLayouts = shownPairs.map(pair => {
    const chips = layoutChips(chipsOf(pair)), gods = tenGodLines(pair);
    const lines = chips.length ? chips[chips.length - 1].line + 1 : 1;
    return {pair, chips, gods, height: data.named ? Math.max(78 + gods.length * 22, 60 + lines * 42) : Math.max(74 + (gods.length - 1) * 22, 26 + lines * 42)};
  });
  // The closing note may need two lines.
  const footNote = T('传统文化符号，未经科学预测效力验证，不作医疗、投资、法律等决策依据。');
  g.font = `400 22px ${sans}`;
  const footLines = g.measureText(footNote).width > inner ? splitLine(footNote) : [footNote];
  const pillarsH = 104 + people.length * 72;
  const pairsH = 76 + pairLayouts.reduce((sum, x) => sum + x.height, 0) + (data.pairs.length > shownPairs.length ? 40 : 0);
  const luckH = rows.length ? 118 + rows.length * 56 : 0;
  const footH = 120 + footLines.length * 34;
  const H = 200 + pillarsH + pairsH + luckH + footH;
  canvas.height = H;
  g.fillStyle = token('--panel'); g.fillRect(0, 0, W, H);
  const glow = g.createRadialGradient(W * .85, 0, 0, W * .85, 0, W * .9);
  glow.addColorStop(0, token('--accent-soft')); glow.addColorStop(1, 'transparent');
  g.fillStyle = glow; g.fillRect(0, 0, W, H);
  g.strokeStyle = token('--accent-line'); g.lineWidth = 2; g.strokeRect(24, 24, W - 48, H - 48);
  // Shrinks a long value down to three quarters of its size, then cuts it with an ellipsis (names in the middle).
  const text = (value, x, y, size, color, {font = sans, align = 'left', weight = '400', max = W - PAD - x, middle = false} = {}) => {
    value = String(value);
    const floor = Math.max(12, Math.round(size * .75));
    g.font = `${weight} ${size}px ${font}`;
    while (size > floor && g.measureText(value).width > max) {size -= 1; g.font = `${weight} ${size}px ${font}`;}
    if (g.measureText(value).width > max) {
      if (middle) value = fitMiddle(value, max);
      else {
        const chars = graphemes(value);
        while (chars.length > 1 && g.measureText(chars.join('') + '…').width > max) chars.pop();
        value = chars.join('') + '…';
      }
    }
    g.fillStyle = color; g.textAlign = align; g.fillText(value, x, y);
    return g.measureText(value).width;
  };
  const stemColor = stem => token('--' + (ELEMENT_CLASS[STEM_ELEMENTS[STEM_ORDER.indexOf(stem)]] || 'faint'));
  const branchColor = branch => token('--' + (ELEMENT_CLASS[BRANCH_ELEMENTS[BRANCH_ORDER.indexOf(branch)]] || 'faint'));
  const rule = y => {g.strokeStyle = token('--border'); g.lineWidth = 1; g.beginPath(); g.moveTo(PAD, y); g.lineTo(W - PAD, y); g.stroke();};
  text('玄枢', PAD, 120, 52, token('--gold'), {font: serif, weight: '600'});
  text('XUANSHU', PAD + 120, 116, 22, token('--gold'), {weight: '600'});
  text(T(data.title) + ' · ' + T('本地确定性计算'), W - PAD, 116, 24, token('--muted'), {align: 'right', max: inner - 330});
  text(T('只标传统标签，不打分、不排名'), PAD, 168, 22, token('--text2'));
  let y = 200;
  // Four pillars: a row per person.
  text(T('四柱'), PAD, y + 34, 28, token('--gold2'), {weight: '600'});
  const nameW = 220, colW = 132, masterX = PAD + nameW + colW * 4, zodiacX = masterX + 118;
  ['年柱', '月柱', '日柱', '时柱'].forEach((label, i) => text(T(label), PAD + nameW + colW * i + colW / 2, y + 80, 18, token('--muted'), {align: 'center', max: colW - 8}));
  text(T('日主'), masterX + 50, y + 80, 18, token('--muted'), {align: 'center', max: 110});
  text(T('生肖'), zodiacX + 44, y + 80, 18, token('--muted'), {align: 'center', max: 92});
  y += 104;
  people.forEach((person, i) => {
    rule(y - 4);
    text(named(i), PAD, y + 44, 28, token('--text'), {weight: '600', max: nameW - 16, middle: true});
    PILLAR_KEYS.forEach((key, j) => {
      const pillar = person.pillars[key], cx = PAD + nameW + colW * j + colW / 2;
      if (!pillar) {text('？', cx, y + 48, 36, token('--faint'), {font: serif, align: 'center'}); return;}
      text(pillar[0], cx - 22, y + 48, 40, stemColor(pillar[0]), {font: serif, align: 'center', weight: '600', max: 48});
      text(pillar[1], cx + 22, y + 48, 40, branchColor(pillar[1]), {font: serif, align: 'center', weight: '600', max: 48});
    });
    if (person.day_master) {
      text(person.day_master, masterX + 34, y + 48, 36, stemColor(person.day_master), {font: serif, align: 'center', weight: '600', max: 44});
      text(T(person.day_master_element), masterX + 72, y + 46, 20, token('--muted'), {max: 44});
    } else text('？', masterX + 50, y + 48, 36, token('--faint'), {font: serif, align: 'center'});
    text(person.zodiac ? T(person.zodiac) : '？', zodiacX + 44, y + 46, 24, token('--text2'), {align: 'center', max: 92});
    y += 72;
  });
  y += 20;
  // Each pair: the day-stem ten god both ways and the labels between their pillars.
  text(T('两两关系'), PAD, y + 34, 28, token('--gold2'), {weight: '600'});
  y += 76;
  // On the group card the two names get a line of their own across the card, each cut in the middle when both do
  // not fit; the ten gods and the chips go beneath. The pair card names its two people A and B.
  pairLayouts.forEach(({pair, chips, gods, height}) => {
    rule(y - 30);
    let below = y + 2;
    if (data.named) {
      g.font = `600 22px ${sans}`;
      const arrow = '  ↔  ', arrowW = g.measureText(arrow).width, room = inner - arrowW;
      const [left, right] = [named(pair.a), named(pair.b)], [lw, rw] = [left, right].map(x => g.measureText(x).width);
      const leftMax = lw + rw <= room ? lw : rw < room / 2 ? room - rw : Math.max(room / 2, room - rw);
      const drawn = text(left, PAD, y + 2, 22, token('--text'), {weight: '600', max: leftMax, middle: true});
      const arrowEnd = PAD + drawn + text(arrow, PAD + drawn, y + 2, 22, token('--muted'), {weight: '600'});
      text(right, arrowEnd, y + 2, 22, token('--text'), {weight: '600', max: W - PAD - arrowEnd, middle: true});
      below = y + 36;
    } else text('A ↔ B', PAD, y + 2, 24, token('--text'), {weight: '600'});
    const godsTop = data.named ? below : y + 32;
    gods.forEach((line, n) => text(line, PAD, godsTop + n * 22, 17, token('--text2'), {max: CHIPS_X - PAD - 16}));
    const chipsTop = data.named ? below - 22 : y - 20;
    if (!chips.length) text(T('无标记'), CHIPS_X, chipsTop + 22, 20, token('--muted'));
    chips.forEach(({label, color, x, line, width}) => {
      const top = chipsTop + line * 42;
      g.strokeStyle = token(color); g.lineWidth = 1.5;
      g.beginPath(); (g.roundRect ? g.roundRect.bind(g) : g.rect.bind(g))(x, top, width, 32, 16); g.stroke();
      text(label, x + 10, top + 22, 18, token(color), {max: width - 16});
    });
    y += height;
  });
  if (data.pairs.length > shownPairs.length) {
    text(T('未画出的两两关系（见文字版）：') + (data.pairs.length - shownPairs.length), PAD, y - 10, 20, token('--muted'));
    y += 40;
  }
  // The luck timeline of the year shown: fifteen years, a colour per luck period.
  if (rows.length) {
    y += 10;
    text(T('大运时间轴') + ' · ' + v.year + ' ' + v.year_pillar, PAD, y + 34, 28, token('--gold2'), {weight: '600'});
    const start = luckWindowShown(data.kind, v.year), years = Array.from({length: LUCK_SPAN}, (_, k) => start + k);  // as on the page
    const left = PAD + 160, cell = (W - PAD - left) / LUCK_SPAN, k0 = years.indexOf(v.year);
    years.forEach((year, k) => text(String(year).slice(2), left + cell * k + cell / 2, y + 80, 16, year === v.year ? token('--text') : token('--muted'),
      {align: 'center', weight: year === v.year ? '700' : '400', max: cell}));
    y += 96;
    // Years with no luck period are named as on the page when the run is wide enough for the words.
    const EMPTY = {unborn: '尚未出生', not_started: '未起运', beyond: '已排完'};
    rows.forEach((row, r) => {
      text(named(r), PAD, y + 30, 22, token('--text'), {weight: '600', max: 150, middle: true});
      if (row.status !== 'ok') {
        text(T(row.status === 'needs_gender' ? '未填性别，不排大运' : '时辰不详且当天交节，大运无法确定'), left + 8, y + 30, 18, token('--muted'), {max: W - PAD - left - 16});
        y += 56; return;
      }
      // The year shown is outlined in each row that has periods (a note row is left uncrossed), beneath the
      // labels so that a long ten-god name running over it stays readable.
      if (k0 >= 0) {g.strokeStyle = token('--gold'); g.lineWidth = 2; g.strokeRect(left + cell * k0, y - 2, cell, 50);}
      years.forEach((year, k) => {
        const at = luckAt(row, year), x = left + cell * k + 1.5;
        if (EMPTY[at.kind]) {
          if (k > 0 && luckAt(row, year - 1).kind === at.kind) return;
          let run = 1;
          while (k + run < years.length && luckAt(row, years[k + run]).kind === at.kind) run++;
          if (run > 1) text(T(EMPTY[at.kind]), x + 6, y + 29, 15, token('--faint'), {max: run * cell - 15});
          return;
        }
        g.globalAlpha = at.kind === 'maybe' ? .12 : .28;
        g.fillStyle = at.kind === 'maybe' ? token('--gold') : stemColor(at.period.pillar[0]);
        g.fillRect(x, y, cell - 3, 46);
        g.globalAlpha = 1;
        if (at.kind === 'maybe') {text('?', x + (cell - 3) / 2, y + 30, 18, token('--muted'), {align: 'center'}); return;}
        if (at.first) {g.fillStyle = token('--gold'); g.fillRect(x, y, 3, 46);}
        if (at.first || k === 0 || luckAt(row, year - 1).kind !== 'period') {
          let run = 1;
          while (k + run < years.length && luckAt(row, years[k + run]).period === at.period) run++;
          g.save(); g.beginPath(); g.rect(x, y, run * cell - 3, 46); g.clip();
          // A period seen for a single year is written smaller so that both characters fit in the cell.
          const p = at.period, size = run > 1 ? 24 : 19, inset = run > 1 ? 8 : 4;
          const w = text(p.pillar[0], x + inset, y + 31, size, stemColor(p.pillar[0]), {font: serif, weight: '600', max: 30});
          text(p.pillar[1], x + inset + w, y + 31, size, branchColor(p.pillar[1]), {font: serif, weight: '600', max: 30});
          if (p.ten_god && run > 1) text(T(p.ten_god), x + inset + w * 2 + 8, y + 30, 16, token('--text2'), {max: run * cell - w * 2 - 24});
          g.restore();
        }
      });
      y += 56;
    });
  }
  rule(H - footH + 10);
  footLines.forEach((line, n) => text(line, PAD, H - footH + 56 + n * 34, 22, token('--muted'), {max: inner}));
  text('XuanShu · open source · deterministic, reproducible', PAD, H - 58, 22, token('--gold'));
}
// A long line split in two near its middle: after the punctuation mark closest to it, else at a space (English),
// else between characters.
function splitLine(line) {
  const middle = Math.floor(line.length / 2);
  let at = -1;
  for (let i = 0; i < line.length; i++) {
    if ('。；，、;,'.includes(line[i]) && Math.abs(i + 1 - middle) <= 14 && (at < 0 || Math.abs(i + 1 - middle) < Math.abs(at - middle))) at = i + 1;
  }
  if (at < 0) {const space = line.lastIndexOf(' ', middle + 12); at = space > middle - 20 ? space : middle;}
  return [line.slice(0, at).trim(), line.slice(at).trim()];
}
const LINK_TYPES_ORDER = ['同支', '六合', '六冲', '六害', '相刑'];
let relationCardRefresh = null;
document.addEventListener('xuanshu-language', () => {const dialog = $('#relation-card-dialog'); if (dialog && dialog.open && relationCardRefresh) relationCardRefresh();});
function openRelationCard(kind) {
  let dialog = $('#relation-card-dialog');
  if (!dialog) {
    dialog = elt('dialog', 'share-dialog'); dialog.id = 'relation-card-dialog';
    dialog.setAttribute('aria-labelledby', 'relation-card-title');
    document.body.append(dialog);
  }
  dialog.replaceChildren();
  const data = relationCardData(kind);
  // Focus goes back to the button that opened the card; if the page was redrawn meanwhile, to its new button.
  const opener = document.activeElement;
  dialog.onclose = () => {
    if (opener && opener !== document.body && opener.isConnected) return;
    const button = $('#' + kind + '-card'); if (button) button.focus();
  };
  const head = append(dialog, 'div', 'share-head');
  append(head, 'h3', null, data.title).id = 'relation-card-title';
  const close = append(head, 'button', 'tiny-button', '关闭'); close.type = 'button'; close.id = 'relation-card-close';
  close.addEventListener('click', () => dialog.close());
  const canvas = append(dialog, 'canvas', 'share-canvas'); canvas.id = 'relation-card-canvas';
  canvas.setAttribute('role', 'img'); canvas.setAttribute('aria-label', '关系卡片预览');
  // The luck timeline gives away each person's gender (the direction of the luck periods follows it), so like the
  // luck ages on the chart card it is drawn only when ticked.
  let withLuck = false;
  if (data.year_view && (data.year_view.luck_timeline || []).length) {
    const label = append(append(dialog, 'div', 'share-options'), 'label', 'check-line');
    const box = append(label, 'input'); box.type = 'checkbox'; box.id = 'relation-card-luck';
    label.append(' 加入大运时间轴');
    append(dialog, 'p', 'field-help', '大运顺排还是逆排由性别决定，所以时间轴会透露每个人的性别；不勾选就不画。');
    box.addEventListener('change', () => {withLuck = box.checked; refresh();});
  }
  append(dialog, 'p', 'field-help', '卡片只在这台设备上生成，不上传。画上的是称呼、四柱和传统标签，不画出生日期、时间和备注；但四柱本身大致能反推出生日期。');
  const actions = append(dialog, 'div', 'profile-actions share-actions');
  const save = append(actions, 'button', 'primary-btn', '下载 PNG'); save.type = 'button'; save.id = 'relation-card-download';
  save.addEventListener('click', () => canvas.toBlob(blob => {if (blob) downloadBlob(blob, data.file);}, 'image/png'));
  // As on the chart card, the PNG is prepared before the click so the share sheet still counts as a user gesture.
  let cardFile = null, version = 0;
  const share = typeof navigator.share === 'function' && typeof navigator.canShare === 'function' ? append(actions, 'button', 'tiny-button', '分享到…') : null;
  if (share) {
    share.type = 'button'; share.id = 'relation-card-share';
    share.addEventListener('click', async () => {
      const file = cardFile;
      if (!file || !navigator.canShare({files: [file]})) {share.textContent = '此浏览器不能分享图片，请下载 PNG'; return;}
      try {await navigator.share({files: [file], title: '玄枢'});}
      catch (e) {if (e.name !== 'AbortError') share.textContent = '分享失败，请下载 PNG';}
    });
  }
  const refresh = () => {
    drawRelationCard(canvas, data, withLuck);
    if (!share) return;
    const mine = ++version; cardFile = null; share.disabled = true; share.textContent = '分享到…';
    canvas.toBlob(blob => {
      if (!blob || mine !== version) return;
      cardFile = new File([blob], data.file, {type: 'image/png'}); share.disabled = false;
    }, 'image/png');
  };
  relationCardRefresh = refresh;
  refresh();
  if (dialog.showModal) dialog.showModal(); else dialog.setAttribute('open', '');
}

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
    texts(append(dialog, 'p', 'field-help'), '共', ' ' + d.shensha.charts.toLocaleString('en-US') + ' ', '张盘（每天一张）', ' · ', d.shensha.stars + ' ', '种神煞逐柱比较',
      ...(d.shensha.generated ? [' · ', '这一节单独重跑于', ' ' + d.shensha.generated] : []));
    countRows(dialog, ['natal', 'fortune'].map(field => ({field, reference: '@soul-atelier/bazi', ...d.shensha[field]})));
    append(dialog, 'p', 'field-help', '参考库给阴干也排羊刃、孤辰寡宿兼以日支查、大运流年也标魁罡、太极贵人戊己只取辰戌丑未、红艳按今通行表、学堂词馆按日干查，与玄枢所引规则不同，这几处不比较。');
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
    // The wide tables scroll sideways on a phone: they get the same edge fade and keyboard stop as the page's own.
    requestAnimationFrame(markScrollAreas);
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
