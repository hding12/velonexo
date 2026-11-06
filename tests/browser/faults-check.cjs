const {chromium}=require('playwright');const assert=require('node:assert/strict');const fs=require('node:fs');
(async()=>{const b=await chromium.launch({channel:'chrome',headless:true});const results=[];try{
 const catalog=JSON.parse(fs.readFileSync('.local/acceptance/catalog.json'));catalog.videos=catalog.videos.slice(0,2);
 for(const scenario of ['manifest-404','segment-404','timeout','offline']){
  console.log('Testing',scenario);const context=await b.newContext();const p=await context.newPage();let requests=0;
  await p.route('**/catalog/videos.json',r=>r.fulfill({json:catalog}));
  const pattern=scenario==='segment-404'?'**/*.m4s':'**/play.m3u8';
  if(scenario!=='offline')await p.route(pattern,r=>{requests++;if(scenario!=='timeout')return r.fulfill({status:404,body:'missing'})});
  if(scenario==='offline')await context.setOffline(true);
  // Navigation itself must succeed before simulating offline.
  if(scenario==='offline'){await context.setOffline(false);await p.goto('http://127.0.0.1:5174');await p.waitForFunction(()=>document.querySelector('.zc-tiktok__fit video')?.currentTime>.1);await context.setOffline(true);await p.locator('article').nth(1).evaluate(el=>el.scrollIntoView({behavior:'instant'}));}
  else await p.goto('http://127.0.0.1:5174');
  await p.locator('.zc-tiktok__fit [role="alert"]').waitFor({timeout:22000});
  const before=requests;await p.waitForTimeout(1000);assert.equal(requests,before);assert(requests<=6);
  if(scenario==='manifest-404'){
   await p.unroute(pattern);await p.locator('.zc-tiktok__fit').getByRole('button',{name:'Saltar video'}).click();
   await p.waitForFunction(()=>document.querySelector('article[data-index="1"] .zc-tiktok__fit video')?.currentTime>.1);
  }
  results.push({scenario,requests,stoppedAfterError:true});await context.close();
 }
 console.log('PASS',JSON.stringify(results));fs.writeFileSync('.local/acceptance/fault-report.json',JSON.stringify(results,null,2));
}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
