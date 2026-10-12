/* Node-only integration check of the shipped browser vault.js, no mock encryption. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const {webcrypto} = require('node:crypto');

const initial = [{id:'test-01',label:'本地测试',data:{birth_datetime:'2000-08-16T04:00',timezone:'Asia/Shanghai'},note:'母亲，在外地工作'}];
const profileKey = 'xuanshu-test-profiles';
const store = new Map([[profileKey,JSON.stringify(initial)]]);
let downloaded = null;
let displayCalls = 0;
const elements = new Map();
const get = id => {
  if(!elements.has(id)) {
    elements.set(id,{value:'',files:[],textContent:'',disabled:false,_events:{},click(){this.clicked=true;},addEventListener(name,callback){this._events[name]=callback;}});
  }
  return elements.get(id);
};
const sandbox = {
  TextEncoder,TextDecoder,crypto:webcrypto,Uint8Array,Uint32Array,
  btoa,atob,Blob,Date,JSON,Number,Error,
  document:{getElementById:get,body:{append(){}},createElement(){return {click(){},remove(){}};}},
  window:{isSecureContext:true,confirm:()=>true},
  localStorage:{getItem:key=>store.get(key)||null,setItem:(key,value)=>store.set(key,value),removeItem:key=>store.delete(key)},
  URL:{createObjectURL(blob){downloaded=blob;return 'blob:temporary';},revokeObjectURL(){}},
  setTimeout(){},
  profileKey,
  loadProfiles:()=>JSON.parse(store.get(profileKey)||'[]'),
  showProfiles:()=>{displayCalls++;},
};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/vault.js'),'utf8'),sandbox,{filename:'vault.js'});
const fire = (id,name,event={}) => get(id)._events[name](event);
async function main(){
  get('vault-password').value='test-vault-password-with-24-chars';
  await fire('vault-export','click');
  assert.ok(downloaded, 'A Blob containing the AES-GCM encrypted backup must be downloaded');
  const contents=await downloaded.text();
  const envelope=JSON.parse(contents);
  assert.equal(envelope.format,'xuanshu-aes256gcm-v1');
  assert.equal(envelope.kdf,'PBKDF2-SHA256');
  assert.equal(envelope.iterations,250000);
  assert.equal(typeof envelope.ciphertext,'string');
  assert.ok(!contents.includes('2000-08-16T04:00'),'Birth data cannot be exposed as plaintext');
  assert.ok(!contents.includes('test-vault-password'),'Password cannot be serialized');
  assert.ok(!contents.includes('外地'),'A member note cannot be exposed as plaintext');

  store.set(profileKey,'[]');
  get('vault-password').value='test-vault-password-with-24-chars';
  const file={size:contents.length,text:async()=>contents};
  await fire('vault-file','change',{target:{files:[file],value:'backup.astro'}});
  assert.deepEqual(JSON.parse(store.get(profileKey)),initial,'Decryption must exactly recover the profile');
  assert.ok(displayCalls>0);

  // A user may import a pre-rename archive without losing encrypted data.
  const oldSalt=Uint8Array.from(Buffer.from(envelope.salt,'base64'));
  const oldIV=Uint8Array.from(Buffer.from(envelope.iv,'base64'));
  const oldPassword='test-vault-password-with-24-chars';
  const oldMaterial=await webcrypto.subtle.importKey('raw',new TextEncoder().encode(oldPassword),
    'PBKDF2',false,['deriveKey']);
  const oldKey=await webcrypto.subtle.deriveKey({name:'PBKDF2',salt:oldSalt,iterations:250000,hash:'SHA-256'},
    oldMaterial,{name:'AES-GCM',length:256},false,['encrypt','decrypt']);
  const oldPayload={schema:'oriental-astro-profiles-v1',created_at:'2026-10-09T00:00:00Z',records:initial};
  const oldCipher=await webcrypto.subtle.encrypt({name:'AES-GCM',iv:oldIV},oldKey,
    new TextEncoder().encode(JSON.stringify(oldPayload)));
  const oldBackup=JSON.stringify({...envelope,format:'oriental-astro-aes256gcm-v1',
    ciphertext:Buffer.from(oldCipher).toString('base64')});
  store.set(profileKey,'[]');
  get('vault-password').value=oldPassword;
  await fire('vault-file','change',{target:{files:[{size:oldBackup.length,text:async()=>oldBackup}],value:'old-backup.astro'}});
  assert.deepEqual(JSON.parse(store.get(profileKey)),initial,'Pre-rename AES-GCM archive must remain importable');

  // A note is optional text of at most 120 characters; anything else is refused.
  for (const note of ['x'.repeat(121), 42]) {
    const payload={schema:'xuanshu-profiles-v1',created_at:'2026-10-12T00:00:00Z',records:[{...initial[0],note}]};
    const cipher=await webcrypto.subtle.encrypt({name:'AES-GCM',iv:oldIV},oldKey,new TextEncoder().encode(JSON.stringify(payload)));
    const bad=JSON.stringify({...envelope,ciphertext:Buffer.from(cipher).toString('base64')});
    store.set(profileKey,'[]');
    get('vault-password').value=oldPassword;
    await fire('vault-file','change',{target:{files:[{size:bad.length,text:async()=>bad}],value:'bad-note.astro'}});
    assert.deepEqual(JSON.parse(store.get(profileKey)),[],'An invalid note must not be restored');
    assert.match(get('profile-feedback').textContent,/格式错误/);
  }

  store.set(profileKey,'[]');
  get('vault-password').value='invalid-test-password';
  await fire('vault-file','change',{target:{files:[file],value:'backup.astro'}});
  assert.deepEqual(JSON.parse(store.get(profileKey)),[],'Incorrect password must not restore data');
  assert.match(get('profile-feedback').textContent,/导入失败/);

  get('vault-password').value='test-vault-password-with-24-chars';
  const corrupted={...envelope,ciphertext:envelope.ciphertext.slice(0,-4)+'AAAA'};
  const broken=JSON.stringify(corrupted);
  await fire('vault-file','change',{target:{files:[{size:broken.length,text:async()=>broken}],value:'broken.astro'}});
  assert.deepEqual(JSON.parse(store.get(profileKey)),[],'Tampering must fail authenticated decryption');

  store.set(profileKey,JSON.stringify(initial));
  fire('clear-profiles','click');
  assert.equal(store.has(profileKey),false,'Clearing should remove the local profile');
  console.log('vault_smoke: PASS — AES-256-GCM roundtrip with member note, legacy archive import, invalid note, wrong password, tampering, clearing');
}
main().catch(err=>{console.error(err);process.exitCode=1;});
