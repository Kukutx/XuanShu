'use strict';
// AI conversation view. Uses helpers from app.js (append, elt, result, postJSON,
// readInput, loadProfiles, $). Nothing here is uploaded except the request
// itself; memory, life events and history stay in this browser and are saved
// only after a deliberate click.
const chatMemoryKey = 'xuanshu-chat-memory-v1';
const chatHistoryKey = 'xuanshu-chat-history-v1';
const CHAT_BODY_LIMIT = 56 * 1024;  // server rejects bodies over 64 KiB
const CHAT_TIMEOUT_MS = 6 * 60 * 1000;  // panel mode with verification can take several minutes
const chatLanguages = {'zh-CN':'简体中文','zh-TW':'繁體中文','en':'English','ja':'日本語'};
let chatMessages = [];   // [{role, content, trace?, charts?, memory_suggestions?, error?}]
let chatStatus = null;
let chatBusy = false;
let chatDraft = '';
let chatLanguage = 'zh-CN';
let chatUseBirth = true;
let chatMode = 'single';   // 'panel': one specialist per school, then a synthesizer
let chatVerify = true;     // second, independent model call that checks claims against tool results
let chatUncertainty = 15;  // minutes the recorded birth time may be off
let chatPartnerOK = false;  // the user's own consent tick; never set by the model
let chatOwner = null;      // profile id the current conversation belongs to
let chatTokenWatch = false;
let chatController = null;  // aborts the request in flight
let chatLive = null;        // progress of the answer being written: {text, steps, stage, charts}
let chatLiveFrame = 0;
let lifePathResult = null;

// Plain-language names for tool calls shown while an answer is being prepared.
const TOOL_LABELS = {
  bazi_chart:'八字排盘', ziwei_chart:'紫微排盘', combined_chart:'八字紫微联合排盘', qimen_hour_chart:'时家奇门排盘',
  bazi_dayun:'八字大运', annual_transformations:'流年四化', annual_timeline:'年度四化轨迹', palace_detail:'宫位详情',
  ziwei_professional_chart:'专业紫微', ziwei_pair_overlay:'双人紫微叠盘', pair_comparison:'双人四柱对照',
  life_path_review:'人生事件回溯', date_candidate_scan:'择日扫描', day_officers:'建除值日', calendar_days:'农历日历',
  solar_terms:'节气查询', lunar_to_gregorian:'农历换算', time_basis_audit:'时制审计', chart_quality_audit:'排盘质量审计',
  birth_time_window:'出生时间误差', birth_boundary_map:'生时边界', rule_comparison:'规则对照', symbolic_reading:'文化规则说明',
  structured_report:'综合报告', deep_evidence_review:'深度证据', consultation_execute:'咨询工作流',
  qimen_reference_audit:'奇门参考盘核对', decision_matrix:'决策矩阵', propose_memory:'提议保存记忆',
};
const toolLabel = name => TOOL_LABELS[name] || name;
// Follow-up questions offered after an answer, keyed by the tools that answer used.
const FOLLOW_UPS = [
  ['bazi_chart', ['我的大运走势是怎样的？', '今年流年和我的八字有什么关系？']],
  ['combined_chart', ['八字和紫微的结论有哪些一致、哪些不同？']],
  ['ziwei_chart', ['详细讲讲我的命宫和官禄宫', '今年的流年四化落在哪些宫？']],
  ['bazi_dayun', ['现在这步大运和上一步有什么不同？']],
  ['annual_transformations', ['明年的四化和今年比有什么变化？']],
  ['qimen_hour_chart', ['换一个时间再排一盘对比一下']],
  ['date_candidate_scan', ['这些日子里哪几个时辰更合适？']],
  ['life_path_review', ['还可以补充哪些人生事件来对照？']],
  ['pair_comparison', ['我们两人的命盘在哪些方面互补？']],
];
function followUps(message) {
  const used = new Set((message.trace || []).filter(t => t.ok).map(t => t.tool));
  const items = [];
  FOLLOW_UPS.forEach(([tool, list]) => {if (used.has(tool)) items.push(...list);});
  if (used.size && !message.panel) items.push('请用多流派会诊再看一次');
  items.push('这个结论的依据是什么？');
  return [...new Set(items)].slice(0, 4);
}

function chatStore(key) {
  try {const data = JSON.parse(localStorage.getItem(key) || '{}'); return data && typeof data === 'object' && !Array.isArray(data) ? data : {};}
  catch (_) {return {};}
}
function chatSave(key, data) {
  try {localStorage.setItem(key, JSON.stringify(data)); return true;} catch (_) {return false;}
}
function chatProfile() {
  const id = $('#profiles').value;
  return loadProfiles().find(x => x.id === id) || null;
}
function profileMemory(id) {
  const entry = chatStore(chatMemoryKey)[id] || {};
  return {
    memory: Array.isArray(entry.memory) ? entry.memory.filter(x => typeof x === 'string').slice(0, 30) : [],
    life_events: Array.isArray(entry.life_events) ? entry.life_events.filter(x => x && typeof x.date === 'string' && typeof x.title === 'string').slice(0, 30) : [],
    keep_history: entry.keep_history === true,
  };
}
function saveProfileMemory(id, value) {
  const all = chatStore(chatMemoryKey); all[id] = value; return chatSave(chatMemoryKey, all);
}
function loadChatHistory(id) {
  const list = chatStore(chatHistoryKey)[id];
  return Array.isArray(list) ? list.filter(m => m && (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string').slice(-60) : [];
}
// A failed or stopped answer and the question that led to it are left out together.
function completeExchanges(messages) {
  const kept = [];
  messages.forEach(m => {
    if (m.error) {if (kept.length && kept[kept.length - 1].role === 'user') kept.pop(); return;}
    kept.push(m);
  });
  return kept;
}
// Saved conversations keep the text, trace and labels but not the chart data, which can be recomputed.
function persistChatHistory() {
  if (!chatOwner || chatOwner !== $('#profiles').value || !profileMemory(chatOwner).keep_history) return;
  const all = chatStore(chatHistoryKey);
  all[chatOwner] = completeExchanges(chatMessages).slice(-60).map(m => {const copy = {...m}; delete copy.charts; return copy;});
  chatSave(chatHistoryKey, all);
}
// A conversation belongs to one profile: switching profiles starts a fresh one
// so one profile's history is never sent or saved under another.
function syncChatOwner() {
  const id = $('#profiles').value || null;
  if (id === chatOwner) return;
  // An answer still being written belongs to the previous profile: stop it.
  if (chatController) chatController.abort();
  // A conversation started before any profile existed is adopted by the first one.
  if (chatOwner !== null) {chatMessages = []; lifePathResult = null;}
  chatOwner = id;
}
// Remove memory, life events and saved conversations of deleted profiles.
function purgeChatStores() {
  const alive = new Set(loadProfiles().map(x => x.id));
  for (const key of [chatMemoryKey, chatHistoryKey]) {
    const all = chatStore(key); let changed = false;
    Object.keys(all).forEach(id => {if (!alive.has(id)) {delete all[id]; changed = true;}});
    if (changed) {
      if (Object.keys(all).length) chatSave(key, all);
      else try {localStorage.removeItem(key);} catch (_) {}
    }
  }
  syncChatOwner();
}
async function fetchChatStatus() {
  const token = $('#api_token').value;
  try {
    const response = await fetch('/api/chat/status', {headers: token ? {'Authorization': 'Bearer ' + token} : {}});
    chatStatus = response.ok ? await response.json() : {enabled:false, reason:'无法读取对话服务状态（HTTP ' + response.status + '）'};
  } catch (_) {chatStatus = {enabled:false, reason:'无法连接对话服务'};}
  if (active === 'chat') render();
}
// The turns sent to the model: failed exchanges are left out, so the model never
// reads the interface's own error text as if it had written it.
function chatTurns(messages) {
  return completeExchanges(messages).map(m => ({role: m.role, content: m.content.slice(0, 4000)}));
}
// Send the most recent turns that fit under the server body limit.
function chatPayload(messages = chatMessages) {
  const profile = chatProfile();
  const now = new Date();
  const today = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');
  const payload = {language: chatLanguage, messages: [], partner_authorized: chatPartnerOK, today, verify: chatVerify, mode: chatMode};
  if (profile || chatUseBirth) {
    const stored = profile ? profileMemory(profile.id) : {memory:[], life_events:[]};
    payload.profile = {label: profile ? profile.label.slice(0, 50) : '当前参数', memory: stored.memory,
      life_events: stored.life_events.map(e => ({date:e.date, title:e.title, note:e.note || ''})),
      birth_time_uncertainty_minutes: chatUncertainty};
    if (chatUseBirth) {
      const birth = readInput();
      Object.keys(birth).forEach(k => {if (birth[k] === null) delete birth[k];});
      payload.profile.birth = birth;
      // Unknown hour: the noon placeholder is flagged, and the confidence labels cover the whole day.
      if ($('#hour_unknown').checked) {payload.profile.birth_hour_unknown = true; payload.profile.birth_time_uncertainty_minutes = 690;}
    }
  }
  let turns = chatTurns(messages).slice(-24);
  while (turns.length && turns[0].role !== 'user') turns.shift();
  payload.messages = turns;
  while (turns.length > 1 && new Blob([JSON.stringify(payload)]).size > CHAT_BODY_LIMIT) {
    turns.splice(0, 2);
    while (turns.length && turns[0].role !== 'user') turns.shift();
  }
  return payload;
}
// Stream the answer as newline-delimited JSON events. Servers or test doubles
// without a readable body fall back to the single-response endpoint.
async function streamChat(payload, signal, onEvent) {
  const token = $('#api_token').value;
  const response = await fetch('/api/chat/stream', {
    method: 'POST', signal, body: JSON.stringify(payload),
    headers: {'Content-Type': 'application/json', ...(token ? {'Authorization': 'Bearer ' + token} : {})},
  });
  if (!response.body || typeof response.body.getReader !== 'function' || response.status === 404) {
    return postJSON('/api/chat', payload, signal);
  }
  if (!response.ok) {
    let detail = '';
    try {const data = await response.json(); detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail || data);} catch (_) {}
    if (response.status === 401) throw new Error('请检查 API 访问令牌（401）：' + detail);
    throw new Error('HTTP ' + response.status + '：' + detail);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '', final = null;
  for (;;) {
    const {value, done} = await reader.read();
    if (value) buffer += decoder.decode(value, {stream: !done});
    let cut;
    while ((cut = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, cut).trim(); buffer = buffer.slice(cut + 1);
      if (!line) continue;
      const event = JSON.parse(line);
      if (event.type === 'done') final = event.result;
      else if (event.type === 'error') throw new Error((event.status ? 'HTTP ' + event.status + '：' : '') + event.detail);
      else onEvent(event);
    }
    if (done) break;
  }
  if (!final) throw new Error('连接中断，没有收到完整回答');
  return final;
}
function onChatEvent(event) {
  const live = chatLive;
  if (!live) return;
  if (event.type === 'text') live.text += event.text;
  else if (event.type === 'reset') live.text = '';
  else if (event.type === 'status') live.stage = event.stage;
  else if (event.type === 'tool_start') live.steps.push({key: (event.agent || '') + event.step, tool: event.tool, agent: event.agent, running: true});
  else if (event.type === 'tool') {
    const step = live.steps.find(s => s.key === (event.agent || '') + event.step && s.running);
    if (step) {step.running = false; step.ok = event.ok; step.summary = event.ok ? '' : event.error;}
    if (event.chart) live.charts.push({tool: event.tool, result: event.chart, agent: event.agent});
  } else if (event.type === 'specialist') live.steps.push({key: 'done-' + event.agent, label: agentLabel(event.agent) + '完成 · ' + event.tool_calls + ' 次工具调用', ok: true});
  if (!chatLiveFrame) chatLiveFrame = requestAnimationFrame(() => {chatLiveFrame = 0; updateLiveBubble();});
}
const STAGE_LABELS = {specialists: '各流派专家正在分别排盘…', synthesis: '综合者正在汇总各流派意见…', verifying: '正在独立核验回答…'};
function fillLiveBubble(bubble) {
  bubble.replaceChildren();
  append(bubble, 'small', null, '玄枢 · 正在回答');
  const live = chatLive;
  const steps = append(bubble, 'div', 'chat-live');
  const seconds = Math.round((Date.now() - live.started) / 1000);
  append(steps, 'div', 'chat-live-step running', (STAGE_LABELS[live.stage] || (live.text ? '正在写回答…' : '正在调用工具和模型…')) + ' · ' + seconds + ' 秒');
  live.steps.forEach(s => {
    append(steps, 'div', 'chat-live-step' + (s.running ? ' running' : s.ok === false ? ' failed' : ''),
      s.label || ((s.agent ? agentLabel(s.agent) + ' · ' : '') + toolLabel(s.tool) + (s.running ? '…' : s.ok === false ? '：失败 ' + (s.summary || '') : ' ✓')));
  });
  live.charts.forEach(c => renderChartCard(bubble, c));
  if (live.text) {
    const text = append(bubble, 'div', 'chat-text chat-md chat-cursor');
    window.XuanShuMarkdown ? window.XuanShuMarkdown.render(live.text, text) : (text.textContent = live.text);
  }
}
function updateLiveBubble() {
  const bubble = $('#chat-live-bubble');
  const log = $('#chat-log');
  if (!bubble || !chatLive || !log) return;
  const pinned = log.scrollHeight - log.scrollTop - log.clientHeight < 80;
  fillLiveBubble(bubble);
  if (pinned) log.scrollTop = log.scrollHeight;
}
function announce(text) {const box = $('#live-status'); if (box) box.textContent = text;}
async function sendChat(text) {
  const content = text.trim();
  if (!content || chatBusy || !chatStatus || chatStatus.enabled !== true) return;
  syncChatOwner();
  const owner = chatOwner, convo = chatMessages;
  convo.push({role:'user', content: content.slice(0, 4000)});
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {timedOut = true; controller.abort();}, CHAT_TIMEOUT_MS);
  chatDraft = ''; chatBusy = true; chatController = controller;
  chatLive = {text: '', steps: [], stage: '', charts: [], started: Date.now()};
  const ticker = setInterval(updateLiveBubble, 1000);
  render();
  let reply;
  try {
    const data = await streamChat(chatPayload(convo), controller.signal, onChatEvent);
    reply = {role:'assistant', content: data.reply || '（模型没有返回文字）', trace: data.trace || [],
      charts: Array.isArray(data.charts) ? data.charts : [],
      memory_suggestions: data.memory_suggestions || [], model: data.model,
      verification: data.verification || null, chart_confidence: data.chart_confidence || null,
      panel: Array.isArray(data.panel) ? data.panel : null};
  } catch (err) {
    const stopped = controller.signal.aborted;
    const partial = chatLive && chatLive.text ? chatLive.text : '';
    reply = {role:'assistant', error: true, retry: content,
      content: stopped ? (timedOut ? '等待超时，已停止。' : '已停止生成。') + (partial ? '\n\n' + partial : '') : '请求失败：' + err.message};
  } finally {
    clearTimeout(timer); clearInterval(ticker);
    chatBusy = false; chatController = null; chatLive = null;
  }
  // The profile may have changed while waiting; the answer then never joins the other profile's conversation.
  if (owner === chatOwner && convo === chatMessages) {convo.push(reply); persistChatHistory();}
  render();
  // A long answer is read from its beginning, so bring its first line into view.
  const log = $('#chat-log'), answer = log && log.querySelector('.chat-msg:last-of-type');
  if (answer && answer.offsetHeight > log.clientHeight) log.scrollTop += answer.getBoundingClientRect().top - log.getBoundingClientRect().top - 8;
  announce(reply.error ? reply.content.split('\n')[0] : '回答完成');
  const box = $('#chat-input'); if (box) box.focus({preventScroll: true});
}
function stopChat() {if (chatController) chatController.abort();}
// Take back the last question: drop it (and its answer) and resend or edit it.
function lastExchange() {
  for (let i = chatMessages.length - 1; i >= 0; i--) if (chatMessages[i].role === 'user') return i;
  return -1;
}
function resendLast() {
  const index = lastExchange();
  if (index < 0 || chatBusy) return;
  const question = chatMessages[index].content;
  chatMessages.splice(index);
  persistChatHistory();
  sendChat(question);
}
function editLast() {
  const index = lastExchange();
  if (index < 0 || chatBusy) return;
  chatDraft = chatMessages[index].content;
  chatMessages.splice(index);
  persistChatHistory(); render();
  const box = $('#chat-input'); if (box) {box.focus(); box.setSelectionRange(box.value.length, box.value.length);}
}
function copyText(button, text) {
  const original = button.textContent;
  navigator.clipboard.writeText(text)
    .then(() => {button.textContent = '已复制';}).catch(() => {button.textContent = '复制失败';})
    .finally(() => setTimeout(() => {button.textContent = original;}, 1800));
}
function exportChatMarkdown() {
  const profile = chatProfile();
  const lines = ['# 玄枢 AI 对话', '', '档案：' + (profile ? profile.label : '未选择'), ''];
  chatMessages.forEach(m => {
    lines.push(m.role === 'user' ? '## 我' : '## 玄枢', '', m.content, '');
    (m.panel || []).forEach(p => lines.push('### ' + p.label, '', p.reply, ''));
    (m.trace || []).forEach(t => lines.push('- 工具 ' + t.step + '：' + (t.agent ? agentLabel(t.agent) + ' · ' : '') + t.tool + (t.ok ? '' : '（失败：' + (t.error || '') + '）')));
    if ((m.trace || []).length) lines.push('');
    if (m.verification && m.verification.status === 'ok') {
      lines.push('核验：' + m.verification.overall, '');
      m.verification.claims.forEach(c => lines.push('- [' + SUPPORT_LABELS[c.support] + ' · ' + TIER_LABELS[c.confidence] + '] ' + c.claim + '：' + c.reason));
      lines.push('');
    }
  });
  lines.push('> 传统术数未经科学预测效力验证，不作医疗、投资、法律等决策依据。');
  const blob = new Blob([lines.join('\n')], {type:'text/markdown;charset=utf-8'});
  const url = URL.createObjectURL(blob); const a = elt('a'); a.href = url; a.download = 'xuanshu-chat.md';
  document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 2000);
}
function markdownInto(parent, text) {
  const node = append(parent, 'div', 'chat-text chat-md');
  if (window.XuanShuMarkdown) window.XuanShuMarkdown.render(text, node); else node.textContent = text;
  return node;
}
// Compact chart cards drawn from tool results inside the conversation.
function miniBazi(card, b) {
  const grid = append(card, 'div', 'mini-pillars');
  for (const [key, p] of Object.entries(b.pillars || {})) {
    const box = append(grid, 'div', 'mini-pillar' + (key === 'day' ? ' day-master' : ''));
    append(box, 'small', null, nameMap[key] || key);
    append(box, 'span', 'mini-god', p.ten_god_of_stem);
    append(box, 'b', elementClass(p.stem_element), p.stem);
    append(box, 'b', elementClass(p.branch_element), p.branch);
  }
  if (b.surface_five_elements) elementBars(card, b.surface_five_elements);
}
function miniZiwei(card, z) {
  const board = append(card, 'div', 'mini-ziwei');
  (z.palaces || []).forEach((p, index) => {
    const cell = ZIWEI_CELLS[index];
    if (!cell) return;
    const node = append(board, 'div', 'mini-palace' + (p.is_ming ? ' ming' : ''));
    node.style.gridRow = String(cell[0]); node.style.gridColumn = String(cell[1]);
    append(node, 'small', null, p.name.replace('宫', '') + ' ' + p.stem + p.branch);
    const stars = append(node, 'div', 'mini-stars');
    if (!p.main_stars.length) stars.append('—');
    p.main_stars.forEach(star => {
      const item = append(stars, 'span', null, star);
      p.birth_year_transformations.filter(t => t.star === star).forEach(t => huaBadge(item, t.type));
    });
  });
  const center = append(board, 'div', 'mini-center');
  append(center, 'span', null, z.five_elements_bureau || '');
  append(center, 'span', null, '命 ' + (z.ming_palace || '') + ' · 身 ' + (z.shen_palace || ''));
}
function miniQimen(card, q) {
  append(card, 'small', 'mini-caption', [q.solar_term, (q.dun || '') + (q.bureau || '') + '局', q.yuan, '值符 ' + q.zhi_fu_star, '值使 ' + q.zhi_shi_door].filter(Boolean).join(' · '));
  const board = append(card, 'div', 'mini-qimen');
  [4, 9, 2, 3, 5, 7, 8, 1, 6].forEach(n => {
    const p = (q.palaces || []).find(x => x.number === n);
    if (!p) return;
    const cell = append(board, 'div', 'mini-qimen-cell' + (p.void ? ' empty' : ''));
    append(cell, 'small', null, n + ' ' + p.trigram);
    append(cell, 'span', null, [p.deity, p.star, p.door].filter(Boolean).join(' '));
    append(cell, 'b', null, p.heaven_stem + '/' + p.earth_stem);
  });
}
const CHART_TITLES = {bazi_chart:'四柱八字', ziwei_chart:'紫微命盘', qimen_hour_chart:'时家奇门', combined_chart:'八字 · 紫微'};
function renderChartCard(parent, chart) {
  const r = chart.result || {};
  const card = append(parent, 'figure', 'chat-chart');
  const caption = append(card, 'figcaption', null, CHART_TITLES[chart.tool] || chart.tool);
  if (chart.agent) caption.append(' · ' + agentLabel(chart.agent));
  if (chart.tool === 'bazi_chart') miniBazi(card, r);
  else if (chart.tool === 'ziwei_chart') miniZiwei(card, r);
  else if (chart.tool === 'qimen_hour_chart') miniQimen(card, r);
  else if (chart.tool === 'combined_chart') {if (r.bazi) miniBazi(card, r.bazi); if (r.ziwei) miniZiwei(card, r.ziwei);}
}
function renderTrace(parent, trace) {
  if (!trace || !trace.length) return;
  const box = append(parent, 'details', 'chat-trace');
  append(box, 'summary', null, '推理过程 · ' + trace.length + ' 次工具调用');
  trace.forEach(t => {
    const row = append(box, 'div', 'chat-trace-step' + (t.ok ? '' : ' failed'));
    append(row, 'strong', null, t.step + '. ' + (t.agent ? agentLabel(t.agent) + ' · ' : '') + toolLabel(t.tool) + ' (' + t.tool + ')');
    append(row, 'span', null, t.ok ? (t.summary || '') : ('失败：' + (t.error || '')));
    const args = append(row, 'code', null, JSON.stringify(t.arguments));
    args.title = '调用参数';
    if (t.result_sha256) append(row, 'small', null, '结果 SHA-256 ' + t.result_sha256.slice(0, 16) + '…');
  });
}
const AGENT_LABELS = {bazi: '八字专家', ziwei: '紫微斗数专家', qimen: '奇门与择时专家'};
function agentLabel(key) {return AGENT_LABELS[key] || key;}
function renderPanel(parent, panel) {
  if (!Array.isArray(panel) || !panel.length) return;
  const box = append(parent, 'details', 'chat-trace chat-panel-reports');
  append(box, 'summary', null, '各流派专家意见 · ' + panel.length + ' 位');
  panel.forEach(p => {
    const row = append(box, 'div', 'chat-trace-step');
    append(row, 'strong', null, agentLabel(p.agent) + ' · ' + p.tool_calls + ' 次工具调用');
    markdownInto(row, p.reply || '（没有返回文字）');
  });
}
const TIER_LABELS = {high: '高', medium: '中', low: '低'};
const SUPPORT_LABELS = {tool_backed: '有工具依据', partially_backed: '部分依据', unsupported: '无依据'};
function renderConfidence(parent, message) {
  const conf = message.chart_confidence;
  if (conf && Array.isArray(conf.facts)) {
    const row = append(parent, 'div', 'chat-confidence');
    append(row, 'small', null, '排盘置信度（出生时间误差 ±' + conf.birth_time_uncertainty_minutes + ' 分钟）：');
    conf.facts.forEach(f => {
      const tag = append(row, 'span', 'conf-tag conf-' + f.confidence, f.fact + ' ' + f.value + ' · ' + TIER_LABELS[f.confidence]);
      tag.title = '距' + f.nearest_boundary + '约 ' + f.margin_minutes + ' 分钟';
    });
  }
  const ver = message.verification;
  if (!ver) return;
  if (ver.status !== 'ok') {append(parent, 'small', 'chat-verify-failed', '核验未完成：' + (ver.error || '')); return;}
  const box = append(parent, 'details', 'chat-trace chat-verify');
  append(box, 'summary', null, '独立核验 · 有工具依据 ' + ver.counts.tool_backed + ' · 部分依据 ' + ver.counts.partially_backed + ' · 无依据 ' + ver.counts.unsupported);
  append(box, 'p', 'field-help', ver.overall);
  ver.claims.forEach(c => {
    const row = append(box, 'div', 'chat-trace-step' + (c.support === 'unsupported' ? ' failed' : ''));
    append(row, 'strong', null, SUPPORT_LABELS[c.support] + ' · 把握' + TIER_LABELS[c.confidence]);
    append(row, 'span', null, c.claim);
    append(row, 'small', null, c.reason);
  });
}
function renderMemorySuggestions(parent, message) {
  const items = (message.memory_suggestions || []).filter(x => typeof x === 'string');
  if (!items.length) return;
  const box = append(parent, 'div', 'chat-memory-suggest');
  append(box, 'small', null, '建议保存到档案记忆（点击才会保存，只存在本机）：');
  const profile = chatProfile();
  items.forEach(item => {
    const row = append(box, 'div', 'chat-memory-row');
    append(row, 'span', 'user-text', item);
    const btn = append(row, 'button', 'tiny-button', profile ? '保存' : '先选择档案'); btn.type = 'button';
    btn.disabled = !profile;
    btn.addEventListener('click', () => {
      const stored = profileMemory(profile.id);
      if (!stored.memory.includes(item) && stored.memory.length < 30) stored.memory.push(item);
      message.memory_suggestions = message.memory_suggestions.filter(x => x !== item);
      saveProfileMemory(profile.id, stored); persistChatHistory(); render();
    });
  });
}
function renderMemoryPanel(parent) {
  const profile = chatProfile();
  const panel = append(parent, 'details', 'consult-advanced chat-memory-panel'); panel.id = 'chat-memory-panel';
  const summary = append(panel, 'summary', null, '档案记忆与人生事件');
  if (profile) {summary.append(' · '); append(summary, 'span', 'user-text', profile.label);}
  if (!profile) {
    append(panel, 'p', 'field-help', '先在「本机档案」保存并选择一个档案。每个档案的记忆、人生事件和对话彼此独立，只保存在这个浏览器。');
    return;
  }
  const stored = profileMemory(profile.id);
  const keepLabel = append(panel, 'label', 'check-line');
  const keep = append(keepLabel, 'input'); keep.type = 'checkbox'; keep.id = 'chat-keep-history'; keep.checked = stored.keep_history;
  keepLabel.append(' 在本机保存这个档案的对话（明文）');
  keep.addEventListener('change', () => {
    stored.keep_history = keep.checked; saveProfileMemory(profile.id, stored);
    if (keep.checked) persistChatHistory();
    else {const all = chatStore(chatHistoryKey); delete all[profile.id]; chatSave(chatHistoryKey, all);}
  });
  append(panel, 'h4', 'subheading', '档案记忆');
  if (!stored.memory.length) append(panel, 'p', 'field-help', '还没有记忆。AI 提议的内容或你手动添加的背景会显示在这里，并随每次提问发送给模型。');
  stored.memory.forEach((item, index) => {
    const row = append(panel, 'div', 'chat-memory-row');
    append(row, 'span', 'user-text', item);
    const del = append(row, 'button', 'tiny-button danger-btn', '删除'); del.type = 'button';
    del.addEventListener('click', () => {stored.memory.splice(index, 1); saveProfileMemory(profile.id, stored); render();});
  });
  const addRow = append(panel, 'div', 'inline-control');
  const memInput = append(addRow, 'input'); memInput.id = 'chat-memory-input'; memInput.maxLength = 300; memInput.placeholder = '例如：正在考虑转行做设计';
  memInput.setAttribute('aria-label', '新的档案记忆');
  const addBtn = append(addRow, 'button', 'tiny-button', '添加记忆'); addBtn.type = 'button'; addBtn.id = 'chat-memory-add';
  addBtn.addEventListener('click', () => {
    const value = memInput.value.trim().replace(/\s+/g, ' ');
    if (!value || stored.memory.length >= 30) return;
    stored.memory.push(value); saveProfileMemory(profile.id, stored); render();
  });
  append(panel, 'h4', 'subheading', '人生事件（命途回溯锚点）');
  append(panel, 'p', 'field-help', '记录已经发生的重要事件，AI 会把事件日期和大运、流年干支、年度四化并列对照。只陈述结构对应，不声称因果。');
  stored.life_events.slice().sort((a, b) => a.date.localeCompare(b.date)).forEach(event => {
    const row = append(panel, 'div', 'chat-memory-row');
    append(row, 'span', 'user-text', event.date + ' · ' + event.title + (event.note ? '：' + event.note : ''));
    const del = append(row, 'button', 'tiny-button danger-btn', '删除'); del.type = 'button';
    del.addEventListener('click', () => {
      stored.life_events = stored.life_events.filter(x => x !== event); saveProfileMemory(profile.id, stored); render();
    });
  });
  const eventRow = append(panel, 'div', 'inline-control');
  const evDate = append(eventRow, 'input'); evDate.type = 'date'; evDate.id = 'chat-event-date'; evDate.min = '1901-01-01'; evDate.max = '2099-12-31';
  evDate.setAttribute('aria-label', '事件日期');
  const evTitle = append(eventRow, 'input'); evTitle.id = 'chat-event-title'; evTitle.maxLength = 80; evTitle.placeholder = '事件，如：换工作';
  const evNote = append(eventRow, 'input'); evNote.id = 'chat-event-note'; evNote.maxLength = 300; evNote.placeholder = '备注（选填）';
  const evBtn = append(eventRow, 'button', 'tiny-button', '添加事件'); evBtn.type = 'button'; evBtn.id = 'chat-event-add';
  evBtn.addEventListener('click', () => {
    const title = evTitle.value.trim();
    if (!evDate.value || !title || stored.life_events.length >= 30) return;
    stored.life_events.push({date: evDate.value, title, note: evNote.value.trim()});
    lifePathResult = null; saveProfileMemory(profile.id, stored); render();
  });
  const reviewRow = append(panel, 'div', 'profile-actions');
  const review = append(reviewRow, 'button', 'tiny-button', '对照人生事件（不需要模型）'); review.type = 'button'; review.id = 'life-path-run';
  review.disabled = !stored.life_events.length;
  const reviewMsg = append(panel, 'p', 'inline-msg');
  review.addEventListener('click', async () => {
    const birth = readInput(); if (birth.longitude === null) delete birth.longitude;
    review.disabled = true; reviewMsg.textContent = '';
    try {
      lifePathResult = await postJSON('/api/life-path', {birth, events: stored.life_events.map(e => ({date: e.date, title: e.title, note: e.note || ''}))});
      render();
    } catch (err) {reviewMsg.textContent = '对照失败：' + err.message; review.disabled = false;}
  });
  if (lifePathResult) {
    const table = append(append(panel, 'div', 'table-wrap'), 'table', 'data-table'); table.id = 'life-path-table';
    const hr = append(append(table, 'thead'), 'tr');
    ['日期', '事件', '虚岁', '大运', '流年', '流年与本命', '年度四化（化忌）'].forEach(x => append(hr, 'th', null, x));
    const body = append(table, 'tbody');
    lifePathResult.events.forEach(e => {
      const tr = append(body, 'tr');
      const rel = e.solar_year_branch_relations.map(r => r.with + r.type).join('、') || '—';
      const ji = e.annual_transformations.find(t => t.type === '化忌');
      [e.date, e.title, e.nominal_age_xusui, e.dayun ? e.dayun.pillar : '未指定方向', e.solar_year_pillar, rel,
        ji ? ji.star + '→' + ji.natal_palace : '—'].forEach((x, i) => append(tr, 'td', i === 1 ? 'user-text' : null, x));
    });
    lifePathResult.notes.concat(lifePathResult.limitations).forEach(x => note(panel, x));
  }
}
function chatSettingsSummary() {
  return [chatLanguages[chatLanguage], chatMode === 'panel' ? '多流派会诊' : '单一助手', chatVerify ? '核验开' : '核验关',
    '±' + chatUncertainty + ' 分钟', chatUseBirth ? '附带出生信息' : '不附带出生信息'].join(' · ');
}
function renderChatSettings(area) {
  const box = append(area, 'details', 'chat-settings'); box.id = 'chat-settings';
  const summary = append(box, 'summary', null, '对话设置');
  append(summary, 'small', 'chat-settings-summary', ' · ' + chatSettingsSummary());
  const controls = append(box, 'div', 'inline-control');
  const langLabel = append(controls, 'label', null, '回答语言 ');
  const lang = append(langLabel, 'select'); lang.id = 'chat-language';
  Object.entries(chatLanguages).forEach(([value, label]) => {const op = append(lang, 'option', null, label); op.value = value;});
  lang.value = chatLanguage; lang.addEventListener('change', () => {chatLanguage = lang.value; render();});
  const modeLabel = append(controls, 'label', null, '回答方式 ');
  const mode = append(modeLabel, 'select'); mode.id = 'chat-mode';
  [['single', '单一助手'], ['panel', '多流派会诊（多次模型调用）']].forEach(([value, label]) => {
    const op = append(mode, 'option', null, label); op.value = value;
  });
  mode.value = chatMode; mode.addEventListener('change', () => {chatMode = mode.value; render();});
  const errLabel = append(controls, 'label', null, '出生时间误差 ');
  const err = append(errLabel, 'select'); err.id = 'chat-uncertainty';
  [[2, '±2 分钟'], [15, '±15 分钟'], [30, '±30 分钟'], [60, '±1 小时'], [120, '±2 小时']].forEach(([value, label]) => {
    const op = append(err, 'option', null, label); op.value = String(value);
  });
  err.value = String(chatUncertainty); err.addEventListener('change', () => {chatUncertainty = Number(err.value); render();});
  const checks = append(box, 'div', 'chat-checks');
  const check = (id, text, value, onChange) => {
    const label = append(checks, 'label', 'check-line');
    const input = append(label, 'input'); input.type = 'checkbox'; input.id = id; input.checked = value;
    label.append(' ' + text);
    input.addEventListener('change', () => {onChange(input.checked); render();});
  };
  check('chat-use-birth', '附带出生信息', chatUseBirth, v => {chatUseBirth = v;});
  check('chat-verify', '独立核验回答（多一次模型调用）', chatVerify, v => {chatVerify = v;});
  check('chat-partner-ok', '已获第二人同意使用其出生资料', chatPartnerOK, v => {chatPartnerOK = v;});
  const profile = chatProfile();
  const loadBtn = append(checks, 'button', 'tiny-button', '载入本档案对话'); loadBtn.type = 'button'; loadBtn.id = 'chat-load-history';
  loadBtn.disabled = !profile || !profileMemory(profile.id).keep_history || chatBusy;
  loadBtn.addEventListener('click', () => {chatOwner = profile.id; chatMessages = loadChatHistory(profile.id); render();});
}
function renderChatDisabled(area) {
  const card = append(area, 'div', 'chat-disabled');
  append(card, 'h4', null, 'AI 对话尚未启用');
  append(card, 'p', null, '排盘、择日、报告等全部工具都能直接使用，不需要语言模型。AI 对话需要运行这个服务的人配置一个语言模型。');
  const go = append(card, 'button', 'tiny-button', '先看我的四柱八字 →'); go.type = 'button'; go.id = 'chat-go-chart';
  go.addEventListener('click', () => {
    const tab = tabs.find(t => t.dataset.tab === 'bazi');
    if (!current) form.requestSubmit();
    activateTab(tab);
  });
  const how = append(card, 'details', 'chat-trace');
  append(how, 'summary', null, '如何启用（给服务器管理员）');
  append(how, 'p', 'field-help', chatStatus.reason || '');
}
function renderComposer(area, enabled) {
  const composer = append(area, 'div', 'chat-composer');
  const input = append(composer, 'textarea'); input.id = 'chat-input'; input.rows = 2; input.maxLength = 4000;
  input.placeholder = enabled ? '输入问题，Enter 发送，Shift+Enter 换行' : 'AI 对话尚未启用';
  input.value = chatDraft; input.disabled = !enabled;
  input.setAttribute('aria-label', '对话输入');
  const grow = () => {input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 240) + 'px';};
  input.addEventListener('input', () => {chatDraft = input.value; grow();});
  input.addEventListener('keydown', event => {
    // Never send while an input method is still composing (Chinese, Japanese).
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && event.keyCode !== 229) {
      event.preventDefault();
      if (!chatBusy) sendChat(input.value);
    }
    if (event.key === 'Escape' && chatBusy) {event.preventDefault(); stopChat();}
  });
  requestAnimationFrame(grow);
  const bar = append(composer, 'div', 'chat-composer-bar');
  append(bar, 'small', null, chatSettingsSummary());
  const actions = append(bar, 'div', 'profile-actions');
  if (chatBusy) {
    const stop = append(actions, 'button', 'tiny-button danger-btn', '停止生成'); stop.type = 'button'; stop.id = 'chat-stop';
    stop.addEventListener('click', stopChat);
  }
  const send = append(actions, 'button', 'primary-btn', '发送'); send.type = 'button'; send.id = 'chat-send';
  send.disabled = chatBusy || !enabled;
  send.addEventListener('click', () => sendChat(input.value));
}
function renderMessage(log, message, index) {
  const bubble = append(log, 'div', 'chat-msg ' + message.role + (message.error ? ' error' : ''));
  append(bubble, 'small', null, message.role === 'user' ? '我' : '玄枢' + (message.model ? ' · ' + message.model : ''));
  if (message.role === 'user') append(bubble, 'div', 'chat-text user-text', message.content);
  else {
    (message.charts || []).forEach(c => renderChartCard(bubble, c));
    markdownInto(bubble, message.content);
    renderPanel(bubble, message.panel); renderTrace(bubble, message.trace); renderConfidence(bubble, message); renderMemorySuggestions(bubble, message);
  }
  const last = index === chatMessages.length - 1;
  const actions = append(bubble, 'div', 'chat-msg-actions');
  const copy = append(actions, 'button', 'tiny-button', '复制'); copy.type = 'button';
  copy.addEventListener('click', () => copyText(copy, message.content));
  if (last && !chatBusy && chatStatus && chatStatus.enabled) {
    if (message.role === 'assistant') {
      const again = append(actions, 'button', 'tiny-button', message.error ? '重试' : '重新回答'); again.type = 'button'; again.id = 'chat-regenerate';
      again.addEventListener('click', resendLast);
    }
    const edit = append(actions, 'button', 'tiny-button', '编辑问题'); edit.type = 'button'; edit.id = 'chat-edit';
    edit.addEventListener('click', editLast);
  }
  if (last && !chatBusy && message.role === 'assistant' && !message.error && chatStatus && chatStatus.enabled) {
    const chips = append(bubble, 'div', 'chat-followups');
    followUps(message).forEach(question => {
      const chip = append(chips, 'button', 'tiny-button', question); chip.type = 'button';
      // Send the text as shown, so a translated interface asks in its own language.
      chip.addEventListener('click', () => {
        if (question === '请用多流派会诊再看一次') chatMode = 'panel';
        sendChat(chip.textContent);
      });
    });
  }
}
function renderChat() {
  if (!chatTokenWatch) {
    chatTokenWatch = true;
    $('#api_token').addEventListener('change', () => {chatStatus = null; if (active === 'chat') render();});
    $('#profiles').addEventListener('change', () => {syncChatOwner(); if (active === 'chat') render();});
  }
  syncChatOwner();
  if (chatStatus === null) {chatStatus = {pending:true}; fetchChatStatus();}
  const enabled = chatStatus.enabled === true;
  const area = append(result, 'section', 'consult-panel chat-panel');
  const head = append(area, 'div', 'chat-intro');
  append(head, 'h3', null, 'AI 对话');
  const birth = readInput();
  if (chatUseBirth) {
    const chip = append(head, 'span', 'chat-birth-chip');
    chip.append('出生信息 ');
    append(chip, 'b', null, birth.birth_datetime.replace('T', ' ') + ' · ' + birth.timezone);
  }
  const statusLine = append(area, 'p', 'field-help', chatStatus.pending ? '正在检查对话服务…'
    : enabled ? ('模型：' + chatStatus.model + '（' + chatStatus.provider + '）· 命盘事实只来自确定性工具，每次调用都可展开查看')
    : ('对话服务未启用：' + chatStatus.reason));
  statusLine.id = 'chat-status';
  if (chatStatus.enabled === false) renderChatDisabled(area);
  renderChatSettings(area);
  renderMemoryPanel(area);

  const log = append(area, 'div', 'chat-log'); log.id = 'chat-log';
  if (!chatMessages.length && !chatBusy) {
    append(log, 'p', 'field-help', '直接提问即可，例如「我今年适合换工作吗？」。缺少出生时间或问题范围时，AI 会先追问。');
    const shortcuts = append(log, 'div', 'consult-shortcuts');
    ['看看我的本命盘有什么特点', '对照我的人生事件回溯一下大运', '下个月哪几天适合搬家？请先问我候选日期', '比较一下我和伴侣的命盘（对方已同意）'].forEach(example => {
      const btn = append(shortcuts, 'button', 'tiny-button', example); btn.type = 'button';
      btn.disabled = !enabled;
      btn.addEventListener('click', () => sendChat(btn.textContent));
    });
  }
  chatMessages.forEach((message, index) => renderMessage(log, message, index));
  if (chatBusy && chatLive) {
    const bubble = append(log, 'div', 'chat-msg assistant chat-live-bubble'); bubble.id = 'chat-live-bubble';
    fillLiveBubble(bubble);
  }
  renderComposer(area, enabled);
  const actions = append(area, 'div', 'profile-actions chat-footer-actions');
  const exportBtn = append(actions, 'button', 'tiny-button', '导出对话 Markdown'); exportBtn.type = 'button'; exportBtn.id = 'chat-export';
  exportBtn.disabled = !chatMessages.length; exportBtn.addEventListener('click', exportChatMarkdown);
  const reset = append(actions, 'button', 'tiny-button danger-btn', '清空对话'); reset.type = 'button'; reset.id = 'chat-clear';
  reset.disabled = !chatMessages.length || chatBusy;
  reset.addEventListener('click', () => {
    if (!confirm('清空当前对话？如果这个档案开启了本机保存，已保存的对话也会一起删除。')) return;
    chatMessages = []; persistChatHistory(); render();
  });
  note(area, '对话由你配置的语言模型生成；命盘计算只来自本地确定性工具。服务器不保存对话、记忆或出生资料。传统术数未经科学预测效力验证。');
  log.scrollTop = log.scrollHeight;
}
