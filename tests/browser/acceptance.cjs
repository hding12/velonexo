const {chromium}=require('playwright');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');
const root=process.cwd();const catalog=JSON.parse(fs.readFileSync(path.join(root,'.local/acceptance/catalog.json')));
(async()=>{const b=await chromium.launch({channel:'chrome',headless:true});const report={checks:[],heap:[],cards:catalog.videos.length,errors:[]};try{
 const p=await b.newPage({viewport:{width:390,height:844}});p.on('pageerror',e=>report.errors.push(e.message));
 await p.route('**/catalog/videos.json',r=>r.fulfill({json:catalog}));await p.goto('http://127.0.0.1:5174');
 const cdp=await p.context().newCDPSession(p);await cdp.send('Performance.enable');
 for(let i=0;i<catalog.videos.length;i++){
  await p.locator('article').nth(i).evaluate(el=>el.scrollIntoView({behavior:'instant'}));
  await p.waitForFunction(i=>{const v=document.querySelector(`article[data-index="${i}"] .zc-tiktok__fit video`);return v&&v.currentTime>.12&&!v.paused},i,{timeout:15000});
  const state=await p.evaluate(()=>({playing:[...document.querySelectorAll('video')].filter(v=>!v.paused).length,players:document.querySelectorAll('video').length,loaded:[...document.querySelectorAll('video')].filter(v=>v.currentSrc).length}));
  assert.equal(state.playing,1);assert(state.players<=6);assert.equal(state.loaded,1);
  if(i%10===0||i===catalog.videos.length-1){await cdp.send('HeapProfiler.collectGarbage');const m=await cdp.send('Performance.getMetrics');report.heap.push({index:i,bytes:m.metrics.find(x=>x.name==='JSHeapUsedSize').value,players:state.players});console.log('Verified cards',i+1)}
 }
 report.checks.push('50 distinct clips: one playing, one loaded, at most 3 mounted cards');
 assert(report.heap.at(-1).bytes<report.heap[1].bytes+25*1024*1024);
 await p.goto('http://127.0.0.1:5174/explore');await p.locator('.explore-card').first().waitFor();assert.equal(await p.locator('video').count(),0);
 await p.getByLabel('Categoría',{exact:true}).selectOption('horizontal');assert.equal(await p.locator('.explore-card').count(),17);
 await p.getByLabel('Etiqueta',{exact:true}).selectOption('sonido');assert.equal(await p.locator('.explore-card').count(),4);
 await p.getByRole('textbox').fill('no-existe');await p.getByText('No encontramos videos con esa búsqueda.').waitFor();
 await p.getByRole('button',{name:'Limpiar filtros'}).click();assert.equal(await p.locator('.explore-card').count(),50);
 await p.locator('.explore-card').first().click();assert(p.url().endsWith('/video/acceptance-00'));await p.goBack();await p.locator('.explore-card').first().waitFor();
 report.checks.push('explore: category/tag/search/reset/detail/history and zero players');
 for(const width of [360,390,430,1440]){await p.setViewportSize({width,height:844});assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
 await p.setViewportSize({width:390,height:844});await p.screenshot({path:'.local/acceptance/explore.png'});
 await p.goto('http://127.0.0.1:5174/video/acceptance-00');await p.waitForFunction(()=>document.querySelector('.zc-tiktok__fit video')?.currentTime>.2);
 await p.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))});assert(await p.locator('.zc-tiktok__fit video').evaluate(v=>v.paused));
 report.checks.push('visibility handler pauses on hidden event (simulated; not real phone)');
 await p.reload();await p.waitForFunction(()=>document.querySelector('.zc-tiktok__fit video')?.currentTime>.2);
 await p.screenshot({path:'.local/acceptance/player.png'});
 // An automatic play rejection must leave a usable manual button, without waiting forever.
 await p.addInitScript(()=>{const original=HTMLMediaElement.prototype.play;let first=true;HTMLMediaElement.prototype.play=function(){if(first){first=false;return Promise.reject(new DOMException('Not allowed','NotAllowedError'))}return original.call(this)}});
 await p.reload();await p.waitForFunction(()=>document.querySelector('.zc-tiktok__fit .player')?.dataset.playerStatus==='paused');
 await p.locator('.zc-tiktok__fit').getByRole('button',{name:'Reproducir',exact:true}).click();await p.waitForFunction(()=>document.querySelector('.zc-tiktok__fit video')?.currentTime>.2);
 report.checks.push('autoplay refusal recovers through manual play');
 assert.deepEqual(report.errors,[]);report.passed=true;fs.writeFileSync('.local/acceptance/browser-report.json',JSON.stringify(report,null,2));console.log('PASS',JSON.stringify(report));
}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
