const {CATALOG,CONFIG,runtimePath}=require('../../server/workspace-paths.cjs');
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const config=JSON.parse(fs.readFileSync(CONFIG));
 assert.deepEqual(config.providers.filter(p=>p.enabled!==false).map(p=>p.id),['hf']);
 const entry=JSON.parse(fs.readFileSync(CATALOG)).videos.find(v=>v.id==='native-audio');
 const map=JSON.parse(fs.readFileSync(runtimePath('media',entry.source.media_map.split('/local-media/')[1])));
 assert(map.objects.every(o=>o.provider_id==='hf'));
 assert.equal(map.expires_in_seconds,null);
 const manifest=fs.readFileSync(runtimePath('media',entry.source.playlist.split('/local-media/')[1]),'utf8');
 assert(!manifest.includes('X-Amz-'));
 const b=await chromium.launch({channel:'chrome',headless:true});
 try {
  const p=await b.newPage();
  await p.goto('http://127.0.0.1:5174/studio');
  await p.waitForFunction(()=>document.querySelector('select[name="provider"] option[value="hf"]'));
  assert.equal(await p.locator('select[name="provider"]').inputValue(),'distributed');
  assert.equal(await p.locator('select[name="provider"] option[value="tigris"]').count(),0);
  await p.goto('http://127.0.0.1:5174/video/native-audio');
  await p.waitForFunction(()=>document.querySelector('.zc-tiktok__fit video')?.currentTime>3,null,{timeout:60000});
  console.log('PASS: HF-only allocation, unsigned manifest, no expiry, Studio default, real browser playback');
 } finally {await b.close()}
})().catch(e=>{console.error(e);process.exit(1)});
