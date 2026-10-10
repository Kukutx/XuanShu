'use strict';
// AI conversation view. Uses helpers from app.js (append, elt, result, postJSON,
// readInput, loadProfiles, $). Nothing here is uploaded except the request
// itself; memory, life events and history stay in this browser and are saved
// only after a deliberate click.
const chatMemoryKey = 'xuanshu-chat-memory-v1';
const chatHistoryKey = 'xuanshu-chat-history-v1';
const CHAT_BODY_LIMIT = 56 * 1024;  // server rejects bodies over 64 KiB
const chatLanguages = {'zh-CN':'简体中文','zh-TW':'繁體中文','en':'English','ja':'日本語'};
let chatMessages = [];   // [{role, content, trace?, memory_suggestions?}]
let chatStatus = null;
let chatBusy = false;
let chatDraft = '';
let chatLanguage = 'zh-CN';
let chatUseBirth = true;
let chatTokenWatch = false;

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
function persistChatHistory() {
  const profile = chatProfile();
  if (!profile || !profileMemory(profile.id).keep_history) return;
  const all = chatStore(chatHistoryKey); all[profile.id] = chatMessages.slice(-60); chatSave(chatHistoryKey, all);
}
async function fetchChatStatus() {
  const token = $('#api_token').value;
  try {
    const response = await fetch('/api/chat/status', {headers: token ? {'Authorization': 'Bearer ' + token} : {}});
    chatStatus = response.ok ? await response.json() : {enabled:false, reason:'无法读取对话服务状态（HTTP ' + response.status + '）'};
  } catch (_) {chatStatus = {enabled:false, reason:'无法连接对话服务'};}
  if (active === 'chat') render();
}
// Send the most recent turns that fit under the server body limit.
function chatPayload() {
  const profile = chatProfile();
  const payload = {language: chatLanguage, messages: []};
  if (profile || chatUseBirth) {
    const stored = profile ? profileMemory(profile.id) : {memory:[], life_events:[]};
    payload.profile = {label: profile ? profile.label.slice(0, 50) : '当前参数', memory: stored.memory,
      life_events: stored.life_events.map(e => ({date:e.date, title:e.title, note:e.note || ''}))};
    if (chatUseBirth) {
      const birth = readInput();
      Object.keys(birth).forEach(k => {if (birth[k] === null) delete birth[k];});
      payload.profile.birth = birth;
    }
  }
  let turns = chatMessages.map(m => ({role: m.role, content: m.content.slice(0, 4000)})).slice(-24);
  while (turns.length && turns[0].role !== 'user') turns.shift();
  payload.messages = turns;
  while (turns.length > 1 && new Blob([JSON.stringify(payload)]).size > CHAT_BODY_LIMIT) {
    turns.splice(0, 2);
    while (turns.length && turns[0].role !== 'user') turns.shift();
  }
  return payload;
}
async function sendChat(text) {
  const content = text.trim();
  if (!content || chatBusy) return;
  chatMessages.push({role:'user', content: content.slice(0, 4000)});
  chatDraft = ''; chatBusy = true; render();
  try {
    const data = await postJSON('/api/chat', chatPayload());
    chatMessages.push({role:'assistant', content: data.reply || '（模型没有返回文字）', trace: data.trace || [],
      memory_suggestions: data.memory_suggestions || [], model: data.model});
  } catch (err) {
    chatMessages.push({role:'assistant', content: '请求失败：' + err.message, error: true});
  } finally {
    chatBusy = false; persistChatHistory(); render();
    const box = $('#chat-input'); if (box) box.focus();
  }
}
function exportChatMarkdown() {
  const profile = chatProfile();
  const lines = ['# 玄枢 AI 对话', '', '档案：' + (profile ? profile.label : '未选择'), ''];
  chatMessages.forEach(m => {
    lines.push(m.role === 'user' ? '## 我' : '## 玄枢', '', m.content, '');
    (m.trace || []).forEach(t => lines.push('- 工具 ' + t.step + '：' + t.tool + (t.ok ? '' : '（失败：' + (t.error || '') + '）')));
    if ((m.trace || []).length) lines.push('');
  });
  lines.push('> 传统术数未经科学预测效力验证，不作医疗、投资、法律等决策依据。');
  const blob = new Blob([lines.join('\n')], {type:'text/markdown;charset=utf-8'});
  const url = URL.createObjectURL(blob); const a = elt('a'); a.href = url; a.download = 'xuanshu-chat.md';
  document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 2000);
}
function renderTrace(parent, trace) {
  if (!trace || !trace.length) return;
  const box = append(parent, 'details', 'chat-trace');
  append(box, 'summary', null, '推理过程 · ' + trace.length + ' 次工具调用');
  trace.forEach(t => {
    const row = append(box, 'div', 'chat-trace-step' + (t.ok ? '' : ' failed'));
    append(row, 'strong', null, t.step + '. ' + t.tool);
    append(row, 'span', null, t.ok ? (t.summary || '') : ('失败：' + (t.error || '')));
    const args = append(row, 'code', null, JSON.stringify(t.arguments));
    args.title = '调用参数';
    if (t.result_sha256) append(row, 'small', null, '结果 SHA-256 ' + t.result_sha256.slice(0, 16) + '…');
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
    append(row, 'span', null, item);
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
  append(panel, 'summary', null, '档案记忆与人生事件' + (profile ? ' · ' + profile.label : ''));
  if (!profile) {
    append(panel, 'p', 'field-help', '先在左侧「本机档案」保存并选择一个档案。每个档案的记忆、人生事件和对话彼此独立，只保存在这个浏览器。');
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
    append(row, 'span', null, item);
    const del = append(row, 'button', 'tiny-button danger-btn', '删除'); del.type = 'button';
    del.addEventListener('click', () => {stored.memory.splice(index, 1); saveProfileMemory(profile.id, stored); render();});
  });
  const addRow = append(panel, 'div', 'inline-control');
  const memInput = append(addRow, 'input'); memInput.id = 'chat-memory-input'; memInput.maxLength = 300; memInput.placeholder = '例如：正在考虑转行做设计';
  const addBtn = append(addRow, 'button', 'tiny-button', '添加记忆'); addBtn.type = 'button';
  addBtn.addEventListener('click', () => {
    const value = memInput.value.trim().replace(/\s+/g, ' ');
    if (!value || stored.memory.length >= 30) return;
    stored.memory.push(value); saveProfileMemory(profile.id, stored); render();
  });
  append(panel, 'h4', 'subheading', '人生事件（命途回溯锚点）');
  append(panel, 'p', 'field-help', '记录已经发生的重要事件，AI 会把事件日期和大运、流年干支、年度四化并列对照。只陈述结构对应，不声称因果。');
  stored.life_events.slice().sort((a, b) => a.date.localeCompare(b.date)).forEach(event => {
    const row = append(panel, 'div', 'chat-memory-row');
    append(row, 'span', null, event.date + ' · ' + event.title + (event.note ? '：' + event.note : ''));
    const del = append(row, 'button', 'tiny-button danger-btn', '删除'); del.type = 'button';
    del.addEventListener('click', () => {
      stored.life_events = stored.life_events.filter(x => x !== event); saveProfileMemory(profile.id, stored); render();
    });
  });
  const eventRow = append(panel, 'div', 'inline-control');
  const evDate = append(eventRow, 'input'); evDate.type = 'date'; evDate.id = 'chat-event-date'; evDate.min = '1901-01-01'; evDate.max = '2099-12-31';
  const evTitle = append(eventRow, 'input'); evTitle.id = 'chat-event-title'; evTitle.maxLength = 80; evTitle.placeholder = '事件，如：换工作';
  const evNote = append(eventRow, 'input'); evNote.id = 'chat-event-note'; evNote.maxLength = 300; evNote.placeholder = '备注（选填）';
  const evBtn = append(eventRow, 'button', 'tiny-button', '添加事件'); evBtn.type = 'button';
  evBtn.addEventListener('click', () => {
    const title = evTitle.value.trim();
    if (!evDate.value || !title || stored.life_events.length >= 30) return;
    stored.life_events.push({date: evDate.value, title, note: evNote.value.trim()});
    saveProfileMemory(profile.id, stored); render();
  });
}
function renderChat() {
  if (!chatTokenWatch) {
    chatTokenWatch = true;
    $('#api_token').addEventListener('change', () => {chatStatus = null; if (active === 'chat') render();});
  }
  if (chatStatus === null) {chatStatus = {pending:true}; fetchChatStatus();}
  const area = append(result, 'section', 'consult-panel chat-panel');
  append(area, 'h3', null, 'AI 对话');
  const statusLine = append(area, 'p', 'field-help', chatStatus.pending ? '正在检查对话服务…'
    : chatStatus.enabled ? ('模型：' + chatStatus.model + '（' + chatStatus.provider + '）· 命盘事实只来自确定性工具，每次调用都可展开查看')
    : ('对话服务未启用：' + chatStatus.reason));
  statusLine.id = 'chat-status';
  const controls = append(area, 'div', 'inline-control');
  const langLabel = append(controls, 'label', null, '回答语言 ');
  const lang = append(langLabel, 'select'); lang.id = 'chat-language';
  Object.entries(chatLanguages).forEach(([value, label]) => {const op = append(lang, 'option', null, label); op.value = value;});
  lang.value = chatLanguage; lang.addEventListener('change', () => {chatLanguage = lang.value;});
  const birthLabel = append(controls, 'label', 'check-line');
  const birth = append(birthLabel, 'input'); birth.type = 'checkbox'; birth.id = 'chat-use-birth'; birth.checked = chatUseBirth;
  birthLabel.append(' 附带左侧出生参数');
  birth.addEventListener('change', () => {chatUseBirth = birth.checked;});
  const profile = chatProfile();
  const loadBtn = append(controls, 'button', 'tiny-button', '载入本档案对话'); loadBtn.type = 'button'; loadBtn.id = 'chat-load-history';
  loadBtn.disabled = !profile || !profileMemory(profile.id).keep_history;
  loadBtn.addEventListener('click', () => {chatMessages = loadChatHistory(profile.id); render();});
  renderMemoryPanel(area);

  const log = append(area, 'div', 'chat-log'); log.id = 'chat-log'; log.setAttribute('aria-live', 'polite');
  if (!chatMessages.length) {
    append(log, 'p', 'field-help', '直接提问即可，例如「我今年适合换工作吗？」。缺少出生时间或问题范围时，AI 会先追问。');
    const shortcuts = append(log, 'div', 'consult-shortcuts');
    ['看看我的本命盘有什么特点', '对照我的人生事件回溯一下大运', '下个月哪几天适合搬家？请先问我候选日期', '比较一下我和伴侣的命盘（对方已同意）'].forEach(example => {
      const btn = append(shortcuts, 'button', 'tiny-button', example); btn.type = 'button';
      btn.addEventListener('click', () => sendChat(example));
    });
  }
  chatMessages.forEach(message => {
    const bubble = append(log, 'div', 'chat-msg ' + message.role + (message.error ? ' error' : ''));
    append(bubble, 'small', null, message.role === 'user' ? '我' : '玄枢');
    append(bubble, 'div', 'chat-text', message.content);
    if (message.role === 'assistant') {renderTrace(bubble, message.trace); renderMemorySuggestions(bubble, message);}
  });
  if (chatBusy) append(log, 'p', 'inline-msg', '正在调用工具和模型…');

  const input = append(area, 'textarea'); input.id = 'chat-input'; input.rows = 3; input.maxLength = 4000;
  input.placeholder = '输入问题，Ctrl+Enter 发送'; input.value = chatDraft; input.disabled = chatBusy;
  input.setAttribute('aria-label', '对话输入');
  input.addEventListener('input', () => {chatDraft = input.value;});
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {event.preventDefault(); sendChat(input.value);}
  });
  const actions = append(area, 'div', 'profile-actions');
  const send = append(actions, 'button', 'primary-btn', chatBusy ? '思考中…' : '发送'); send.type = 'button'; send.id = 'chat-send';
  send.disabled = chatBusy || (chatStatus.enabled === false);
  send.addEventListener('click', () => sendChat(input.value));
  const exportBtn = append(actions, 'button', 'tiny-button', '导出对话 Markdown'); exportBtn.type = 'button'; exportBtn.id = 'chat-export';
  exportBtn.disabled = !chatMessages.length; exportBtn.addEventListener('click', exportChatMarkdown);
  const reset = append(actions, 'button', 'tiny-button danger-btn', '清空对话'); reset.type = 'button'; reset.id = 'chat-clear';
  reset.disabled = !chatMessages.length || chatBusy;
  reset.addEventListener('click', () => {chatMessages = []; persistChatHistory(); render();});
  note(area, '对话由你配置的语言模型生成；命盘计算只来自本地确定性工具。服务器不保存对话、记忆或出生资料。传统术数未经科学预测效力验证。');
  log.scrollTop = log.scrollHeight;
}
