'use strict';
/* Entirely browser-side encrypted local archive. No password or archive is sent to API. */
(() => {
  const q = id => document.getElementById(id);
  const enc = new TextEncoder();
  const dec = new TextDecoder('utf-8', {fatal:true});
  const ITERATIONS = 250000;
  const rand = size => crypto.getRandomValues(new Uint8Array(size));
  const b64 = data => {
    // In slices: spreading a whole backup into one call overflows the argument limit above about 100 KB.
    let text = '';
    for (let i = 0; i < data.length; i += 0x8000) text += String.fromCharCode(...data.subarray(i, i + 0x8000));
    return btoa(text);
  };
  const unb64 = value => Uint8Array.from(atob(value), c => c.charCodeAt(0));
  // Pieces become separate text nodes, so each one translates whole and the counts stay as numbers.
  const inform = (...parts) => {q('profile-feedback').replaceChildren(...parts.map(String));};
  // Backups now carry each profile's memory, life events and saved conversations, so they can be larger.
  const MAX_FILE = 4 * 1024 * 1024, MAX_CIPHERTEXT = 3 * 1024 * 1024;
  const SCHEMA = 'xuanshu-backup-v2';
  const DAY = /^\d{4}-\d{2}-\d{2}$/;
  // Profile ids become object keys in the memory and conversation stores, where these names would reach the prototype.
  const RESERVED = new Set(['__proto__', 'constructor', 'prototype']);
  const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  const text = (value, max) => typeof value === 'string' && value.length <= max;
  const objects = list => Array.isArray(list) && list.every(isObject);
  function readStore(key) {
    try {const value = JSON.parse(localStorage.getItem(key) || '{}'); return isObject(value) ? value : {};}
    catch (_) {return {};}
  }
  // What this browser keeps beside each saved profile (written by chat.js), limited to the profiles being backed up.
  // It goes through the same checks a restore applies, so every backup this page writes can be restored.
  function companions(records) {
    const memory = {}, history = {}, kept = readStore(chatMemoryKey), talks = readStore(chatHistoryKey);
    records.forEach(({id}) => {
      if (isObject(kept[id])) memory[id] = cleanMemory(kept[id]);
      const turns = Array.isArray(talks[id]) ? talks[id].filter(validTurn).slice(-60).map(cleanTurn) : [];
      if (turns.length) history[id] = turns;
    });
    return {memory, history};
  }

  async function keyFromPassword(password, salt, iterations) {
    const material = await crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveKey']);
    return crypto.subtle.deriveKey({name:'PBKDF2', salt, iterations, hash:'SHA-256'}, material,
      {name:'AES-GCM', length:256}, false, ['encrypt','decrypt']);
  }
  async function encryptedArchive(records, password) {
    const salt=rand(16), iv=rand(12);
    const key=await keyFromPassword(password,salt,ITERATIONS);
    const data=enc.encode(JSON.stringify({schema:SCHEMA,created_at:new Date().toISOString(),records,...companions(records)}));
    const encrypted=await crypto.subtle.encrypt({name:'AES-GCM',iv},key,data);
    const archive=JSON.stringify({format:'xuanshu-aes256gcm-v1',kdf:'PBKDF2-SHA256',iterations:ITERATIONS,
      salt:b64(salt),iv:b64(iv),ciphertext:b64(new Uint8Array(encrypted))},null,2);
    // Refused here rather than written as a file the restore would then reject.
    if(encrypted.byteLength>MAX_CIPHERTEXT || archive.length>MAX_FILE) throw new Error('备份超过 4 MB 上限，多半是已保存的对话太长；请先清空部分对话再导出');
    return archive;
  }
  async function decryptedArchive(archive, password) {
    // Keep already exported pre-rename backups readable; always export XuanShu format.
    const legacy = archive?.format === 'oriental-astro-aes256gcm-v1';
    if (!archive || (!legacy && archive.format !== 'xuanshu-aes256gcm-v1') || archive.kdf !== 'PBKDF2-SHA256' ||
      !Number.isInteger(archive.iterations) || archive.iterations < 100000 || archive.iterations > 1000000) {
      throw new Error('备份格式或 PBKDF2 参数不受支持');
    }
    const salt=unb64(archive.salt),iv=unb64(archive.iv),ct=unb64(archive.ciphertext);
    if(salt.length!==16 || iv.length!==12 || ct.length>MAX_CIPHERTEXT) throw new Error('加密备份内容无效');
    const key=await keyFromPassword(password,salt,archive.iterations);
    const decrypted=await crypto.subtle.decrypt({name:'AES-GCM',iv},key,ct);
    const payload=JSON.parse(dec.decode(decrypted));
    const expectedSchema = legacy ? ['oriental-astro-profiles-v1'] : ['xuanshu-profiles-v1', SCHEMA];
    if(!expectedSchema.includes(payload.schema)||!Array.isArray(payload.records)||payload.records.length>20)
      throw new Error('档案格式不合法或超过数量限制');
    for(const item of payload.records){
      if(!item || typeof item.id!=='string' || item.id.length>80 || RESERVED.has(item.id) ||
        typeof item.label!=='string' || item.label.length>50 || !item.label.trim() ||
        !item.data || typeof item.data!=='object' ||
        typeof item.data.birth_datetime!=='string' || item.data.birth_datetime.length>50 ||
        typeof item.data.timezone!=='string' || item.data.timezone.length>100 ||
        (item.data.longitude!=null && (!Number.isFinite(item.data.longitude) || Math.abs(item.data.longitude)>180)) ||
        (item.note!=null && (typeof item.note!=='string' || item.note.length>120))) {
        throw new Error('备份中存在格式错误的档案');
      }
    }
    if (payload.schema !== SCHEMA) return {records: payload.records, memory: null, history: null};
    const ids = new Set(payload.records.map(item => item.id));
    const memory = payload.memory ?? {}, history = payload.history ?? {};
    if (!isObject(memory) || !isObject(history) || ![...Object.keys(memory), ...Object.keys(history)].every(id => ids.has(id)) ||
      !Object.values(memory).every(validMemory) || !Object.values(history).every(validHistory)) {
      throw new Error('备份中存在格式错误的记忆、人生事件或对话');
    }
    const turns = {};
    Object.entries(history).forEach(([id, list]) => {if (list.length) turns[id] = list.map(cleanTurn);});
    return {records: payload.records, memory, history: turns};
  }
  // The same limits the chat page applies when they are added: 30 notes of up to 300 characters, 30 events with a
  // date the date field accepts, a title and an optional note.
  const validNote = x => text(x, 300) && x.trim() !== '';
  function realDay(value) {
    if (!text(value, 10) || !DAY.test(value) || value < '1901-01-01' || value > '2099-12-31') return false;
    const day = new Date(value + 'T00:00:00Z');
    return !Number.isNaN(day.getTime()) && day.toISOString().slice(0, 10) === value;  // 2023-02-30 does not exist
  }
  const validEvent = e => isObject(e) && Object.keys(e).every(key => ['date', 'title', 'note'].includes(key)) &&
    realDay(e.date) && text(e.title, 80) && e.title.trim() !== '' && (e.note == null || text(e.note, 300));
  function validMemory(entry) {
    return isObject(entry) && Object.keys(entry).every(key => ['memory', 'life_events', 'keep_history'].includes(key)) &&
      (entry.memory === undefined || (Array.isArray(entry.memory) && entry.memory.length <= 30 && entry.memory.every(validNote))) &&
      (entry.life_events === undefined || (Array.isArray(entry.life_events) && entry.life_events.length <= 30 && entry.life_events.every(validEvent))) &&
      (entry.keep_history === undefined || typeof entry.keep_history === 'boolean');
  }
  // What a backup takes from this browser's copy: only the notes and events a restore would accept.
  function cleanMemory(entry) {
    const out = {};
    if (Array.isArray(entry.memory)) out.memory = entry.memory.filter(validNote).slice(0, 30);
    if (Array.isArray(entry.life_events)) {
      out.life_events = entry.life_events.filter(isObject)
        .map(({date, title, note}) => note == null ? {date, title} : {date, title, note}).filter(validEvent).slice(0, 30);
    }
    if (typeof entry.keep_history === 'boolean') out.keep_history = entry.keep_history;
    return out;
  }
  // Saved conversations: the last 60 turns, each a user or assistant message with its text.
  const validTurn = m => isObject(m) && (m.role === 'user' || m.role === 'assistant') && text(m.content, 40000);
  const validHistory = list => Array.isArray(list) && list.length <= 60 && list.every(validTurn);
  // A turn keeps its text and, when they have the shape the chat page draws, its tool steps, expert reports,
  // confidence labels, verification and memory suggestions; anything else in it is dropped.
  function cleanTurn(m) {
    const turn = {role: m.role, content: m.content};
    if (text(m.model, 200)) turn.model = m.model;
    if (Array.isArray(m.memory_suggestions)) turn.memory_suggestions = m.memory_suggestions.filter(validNote).slice(0, 10);
    if (objects(m.trace) && m.trace.length <= 60 &&
      m.trace.every(t => typeof t.tool === 'string' && (t.result_sha256 == null || typeof t.result_sha256 === 'string'))) turn.trace = m.trace;
    if (objects(m.panel) && m.panel.every(p => p.reply == null || typeof p.reply === 'string')) turn.panel = m.panel;
    if (isObject(m.chart_confidence) && objects(m.chart_confidence.facts)) turn.chart_confidence = m.chart_confidence;
    const check = m.verification;
    if (isObject(check) && (check.status !== 'ok' || (isObject(check.counts) && objects(check.claims)))) turn.verification = check;
    return turn;
  }
  // All of a restore lands, or none of it does (a full browser storage must not leave half a backup behind).
  function replaceStored(entries) {
    const before = entries.map(([key]) => [key, localStorage.getItem(key)]);
    const put = ([key, value]) => value === null ? localStorage.removeItem(key) : localStorage.setItem(key, value);
    try {entries.forEach(put);}
    catch (_) {
      before.forEach(entry => {try {put(entry);} catch (__) {}});
      throw new Error('浏览器存储空间不足，未作任何更改');
    }
  }
  const storeText = data => Object.keys(data).length ? JSON.stringify(data) : null;
  const count = (data, field) => Object.values(data).reduce((n, entry) => n + (Array.isArray(entry[field]) ? entry[field].length : 0), 0);
  // The list separator and the closing clause are pieces of their own, so each piece translates whole.
  const tally = (records, memory, history) => [records.length, ' 份档案', '、', count(memory, 'memory'), ' 条记忆', '、',
    count(memory, 'life_events'), ' 件人生事件', '、', Object.keys(history).length, ' 段已保存的对话', '；'];
  function downloadText(filename, contents){
    const blob=new Blob([contents],{type:'application/json;charset=utf-8'});
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');a.href=url;a.download=filename;
    document.body.append(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1500);
  }
  function password(){
    if(!window.isSecureContext || !crypto.subtle) throw new Error('加密功能仅支持 localhost 或 HTTPS 安全上下文');
    const value=q('vault-password').value;
    if(value.length<12) throw new Error('请填写至少 12 字符的备份口令');
    return value;
  }
  q('vault-export').addEventListener('click',async()=>{
    const button=q('vault-export');button.disabled=true;
    try {
      const records=loadProfiles();if(!records.length) throw new Error('尚无已保存的本地档案');
      const blob=await encryptedArchive(records,password());
      downloadText('xuanshu-encrypted-'+new Date().toISOString().slice(0,10)+'.astro',blob);
      const {memory, history} = companions(records);
      inform('已生成 AES-256-GCM 加密备份：', ...tally(records, memory, history), '口令不会保存，也不会上传服务器。');
    }catch(e){inform('加密导出失败：', e.message);}finally{button.disabled=false;q('vault-password').value='';}
  });
  q('vault-import').addEventListener('click',()=>q('vault-file').click());
  q('vault-file').addEventListener('change',async event=>{
    const file=event.target.files?.[0];if(!file)return;
    try {
      if(file.size>MAX_FILE) throw new Error('备份文件超过 4 MB');
      const value=password();
      const {records, memory, history}=await decryptedArchive(JSON.parse(await file.text()),value);
      // Replace rather than silently merge; user controls the complete backup state.
      if (memory === null) {
        // An older backup holds profiles only: memory and conversations of profiles it also contains stay.
        if(!await xsConfirm(['备份里有 ',records.length,' 份档案。','用它们替换当前浏览器里的全部档案吗？'],{confirmLabel:'替换'})) return;
        replaceStored([[profileKey, JSON.stringify(records)]]);
      } else {
        if(!await xsConfirm(['备份里有 ',records.length,' 份档案。','用这些档案及其记忆、人生事件和对话替换当前浏览器里的全部内容吗？'],{confirmLabel:'替换'})) return;
        replaceStored([[profileKey, JSON.stringify(records)], [chatMemoryKey, storeText(memory)], [chatHistoryKey, storeText(history)]]);
      }
      // The open conversation and memory panel were drawn from what was just replaced.
      showProfiles();purgeChatStores();restartChat();
      if (memory === null) inform('加密备份已恢复；原档案已被替换。');
      else inform('加密备份已恢复：', ...tally(records, memory, history), '原有内容已被替换。');
    }catch(e){
      // A wrong passphrase and a damaged file fail the same authenticated decryption, so they cannot be told apart.
      if (e && e.name === 'OperationError') inform('导入失败：口令错误或文件已损坏。');
      else if (e && (e.name === 'SyntaxError' || e.name === 'InvalidCharacterError')) inform('导入失败：这不是玄枢的加密备份文件。');
      else inform('导入失败：', e.message);
    }
    finally{event.target.value='';q('vault-password').value='';}
  });
  q('clear-profiles').addEventListener('click',async()=>{
    if(!await xsConfirm('确定清空当前浏览器保存的所有出生档案吗？此操作不可撤销。',{confirmLabel:'清空',danger:true}))return;
    try{localStorage.removeItem(profileKey);showProfiles();purgeChatStores();inform('已清空此浏览器的所有本地档案及其对话、记忆和人生事件。');}
    catch(e){inform('清空失败：', e.message);}
  });
})();
