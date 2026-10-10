'use strict';
/* Entirely browser-side encrypted local archive. No password or archive is sent to API. */
(() => {
  const q = id => document.getElementById(id);
  const enc = new TextEncoder();
  const dec = new TextDecoder('utf-8', {fatal:true});
  const ITERATIONS = 250000;
  const rand = size => crypto.getRandomValues(new Uint8Array(size));
  const b64 = data => btoa(String.fromCharCode(...data));
  const unb64 = value => Uint8Array.from(atob(value), c => c.charCodeAt(0));
  const inform = message => {q('profile-feedback').textContent = message;};

  async function keyFromPassword(password, salt, iterations) {
    const material = await crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveKey']);
    return crypto.subtle.deriveKey({name:'PBKDF2', salt, iterations, hash:'SHA-256'}, material,
      {name:'AES-GCM', length:256}, false, ['encrypt','decrypt']);
  }
  async function encryptedArchive(records, password) {
    const salt=rand(16), iv=rand(12);
    const key=await keyFromPassword(password,salt,ITERATIONS);
    const data=enc.encode(JSON.stringify({schema:'xuanshu-profiles-v1',created_at:new Date().toISOString(),records}));
    const encrypted=await crypto.subtle.encrypt({name:'AES-GCM',iv},key,data);
    return JSON.stringify({format:'xuanshu-aes256gcm-v1',kdf:'PBKDF2-SHA256',iterations:ITERATIONS,
      salt:b64(salt),iv:b64(iv),ciphertext:b64(new Uint8Array(encrypted))},null,2);
  }
  async function decryptedArchive(archive, password) {
    // Keep already exported pre-rename backups readable; always export XuanShu format.
    const legacy = archive?.format === 'oriental-astro-aes256gcm-v1';
    if (!archive || (!legacy && archive.format !== 'xuanshu-aes256gcm-v1') || archive.kdf !== 'PBKDF2-SHA256' ||
      !Number.isInteger(archive.iterations) || archive.iterations < 100000 || archive.iterations > 1000000) {
      throw new Error('备份格式或 PBKDF2 参数不受支持');
    }
    const salt=unb64(archive.salt),iv=unb64(archive.iv),ct=unb64(archive.ciphertext);
    if(salt.length!==16 || iv.length!==12 || ct.length>128*1024) throw new Error('加密备份内容无效');
    const key=await keyFromPassword(password,salt,archive.iterations);
    const decrypted=await crypto.subtle.decrypt({name:'AES-GCM',iv},key,ct);
    const payload=JSON.parse(dec.decode(decrypted));
    const expectedSchema = legacy ? 'oriental-astro-profiles-v1' : 'xuanshu-profiles-v1';
    if(payload.schema!==expectedSchema||!Array.isArray(payload.records)||payload.records.length>20)
      throw new Error('档案格式不合法或超过数量限制');
    for(const item of payload.records){
      if(!item || typeof item.id!=='string' || item.id.length>80 ||
        typeof item.label!=='string' || item.label.length>50 || !item.label.trim() ||
        !item.data || typeof item.data!=='object' ||
        typeof item.data.birth_datetime!=='string' || item.data.birth_datetime.length>50 ||
        typeof item.data.timezone!=='string' || item.data.timezone.length>100 ||
        (item.data.longitude!=null && (!Number.isFinite(item.data.longitude) || Math.abs(item.data.longitude)>180))) {
        throw new Error('备份中存在格式错误的档案');
      }
    }
    return payload.records;
  }
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
      inform('已生成 AES-256-GCM 加密备份；口令不会保存，也不会上传服务器。');
    }catch(e){inform('加密导出失败：'+e.message);}finally{button.disabled=false;q('vault-password').value='';}
  });
  q('vault-import').addEventListener('click',()=>q('vault-file').click());
  q('vault-file').addEventListener('change',async event=>{
    const file=event.target.files?.[0];if(!file)return;
    try {
      if(file.size>256*1024) throw new Error('备份文件超过 256 KB');
      const value=password();
      const records=await decryptedArchive(JSON.parse(await file.text()),value);
      // Replace rather than silently merge; user controls the complete backup state.
      if(!window.confirm(`即将使用备份中的 ${records.length} 条档案替换当前浏览器档案，确定吗？`)) return;
      localStorage.setItem(profileKey,JSON.stringify(records));showProfiles();
      inform('加密备份已恢复；原档案已被替换。');
    }catch(e){inform('导入失败：口令错误、文件损坏或 '+e.message);}
    finally{event.target.value='';q('vault-password').value='';}
  });
  q('clear-profiles').addEventListener('click',()=>{
    if(!window.confirm('确定清空当前浏览器保存的所有出生档案吗？此操作不可撤销。'))return;
    try{localStorage.removeItem(profileKey);showProfiles();inform('已清空此浏览器的所有本地档案。');}
    catch(e){inform('清空失败：'+e.message);}
  });
})();
