const {chromium}=require('playwright');const assert=require('node:assert/strict');
(async()=>{const b=await chromium.launch({channel:'chrome',headless:true});try{
 const p=await b.newPage({viewport:{width:390,height:844}});const errors=[];const mediaHosts=new Set();p.on('response',r=>{const u=new URL(r.url());if(r.status()<400&&(u.hostname.endsWith('storage.dev')||u.hostname==='huggingface.co'))mediaHosts.add(u.hostname)});p.on('pageerror',e=>errors.push(e.message));
 await p.goto('http://127.0.0.1:5174/video/native-audio');
 const v=p.locator('.zc-tiktok__fit video');
 await p.waitForFunction(()=>[...document.querySelectorAll('.zc-tiktok__fit video')].some(v=>v.currentTime>7&&!v.paused),{},{timeout:30000});
 assert(mediaHosts.has('t3.storage.dev'));assert(mediaHosts.has('huggingface.co'));assert.equal(await v.evaluate(v=>v.muted),true);
 await p.locator('.zc-tiktok__fit').getByRole('button',{name:'Activar sonido',exact:true}).click();assert.equal(await v.evaluate(v=>v.muted),false);
 await p.locator('.zc-tiktok__fit').getByRole('button',{name:'Pausar',exact:true}).click();assert.equal(await v.evaluate(v=>v.paused),true);
 await p.locator('.zc-tiktok__fit').getByRole('button',{name:'Reproducir',exact:true}).click();await p.waitForTimeout(300);assert.equal(await v.evaluate(v=>v.paused),false);
 await p.getByRole('button',{name:'Explorar',exact:false}).last().click();await p.locator('.explore-grid').waitFor();assert.equal(await p.locator('video').count(),0);
 await p.locator('.explore-card').filter({hasText:'Video de prueba con sonido'}).click();await v.waitFor();
 await p.route('**/play.m3u8',r=>r.fulfill({status:404,body:'missing'}));await p.reload();await p.locator('.zc-tiktok__fit [role="alert"]').waitFor({timeout:25000});
 await p.unroute('**/play.m3u8');await p.locator('.zc-tiktok__fit').getByRole('button',{name:'Intentar de nuevo'}).click();
 await p.waitForFunction(()=>[...document.querySelectorAll('.zc-tiktok__fit video')].some(v=>v.currentTime>1&&!v.paused),{},{timeout:30000});
 assert.deepEqual(errors,[]);console.log('PASS: played beyond 7s across both storage hosts; real two-store HLS, audio toggle, pause/resume, route cleanup, 404/retry');
}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
