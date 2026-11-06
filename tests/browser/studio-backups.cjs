const {chromium}=require('playwright');const fs=require('node:fs');const assert=require('node:assert/strict');
const file='public/catalog/videos.json',baseline=fs.readFileSync(file),dir='.local/publisher/backups';
const good='20990101T000000000001.json',bad='20990101T000000000002.json';
(async()=>{const b=await chromium.launch({channel:'chrome',headless:true});try{
 const candidate=JSON.parse(baseline);candidate.videos.find(v=>v.id==='native-audio').visibility='draft';candidate.videos.find(v=>v.id==='demo-1').title='Prueba de restauración';
 fs.writeFileSync(dir+'/'+good,JSON.stringify(candidate));const invalid=structuredClone(candidate);invalid.videos.find(v=>v.id==='demo-1').source.media_map='/local-media/demo-1/0000000000000000/map.json';fs.writeFileSync(dir+'/'+bad,JSON.stringify(invalid));
 const p=await b.newPage();await p.goto('http://127.0.0.1:5174/studio');await p.waitForFunction(()=>document.querySelector('fieldset')?.disabled===false);
 const session=await(await p.request.get('http://127.0.0.1:5174/api/studio/session')).json();const headers={'X-Studio-Token':session.token};
 assert.equal((await p.request.post('http://127.0.0.1:5174/api/studio/restore-backup',{headers,data:{id:'../../config/storage.json'}})).status(),400);
 await p.getByRole('button',{name:'Ver respaldos',exact:true}).click();await p.getByRole('button',{name:'Restaurar '+good,exact:true}).click();await p.getByRole('dialog').getByRole('button',{name:'Cancelar',exact:true}).click();assert.deepEqual(fs.readFileSync(file),baseline);
 async function restore(id){await p.getByRole('button',{name:'Restaurar '+id,exact:true}).click();const response=p.waitForResponse(r=>r.url().endsWith('/api/studio/restore-backup')&&r.request().method()==='POST');await p.getByRole('dialog').getByRole('button',{name:'Confirmar restauración'}).click();const job=(await(await response).json()).job;assert(job);for(let attempt=0;attempt<600;attempt++){const session=await(await p.request.get('http://127.0.0.1:5174/api/studio/session')).json();const state=await(await p.request.get('http://127.0.0.1:5174/api/studio/state',{headers:{'X-Studio-Token':session.token}})).json();const current=state.jobs.find(j=>j.id===job.id);if(['failed','succeeded'].includes(current?.state)){assert.equal(current.state,id===good?'succeeded':'failed');return}await new Promise(r=>setTimeout(r,100))}throw Error('restore did not finish')}

 await restore(bad);assert.deepEqual(fs.readFileSync(file),baseline);
 await restore(good);assert.equal(JSON.parse(fs.readFileSync(file)).videos.find(v=>v.id==='demo-1').title,'Prueba de restauración');
 assert(fs.readdirSync(dir).some(n=>n!==good&&n!==bad&&fs.readFileSync(dir+'/'+n,'utf8')===baseline.toString()));
 console.log('PASS: backup list, cancel, traversal rejection, failed verification preserves catalog, valid restore and automatic backup');
 }finally{await b.close();fs.writeFileSync(file,baseline);for(const id of [good,bad])fs.rmSync(dir+'/'+id,{force:true})}
})().catch(e=>{console.error(e);process.exit(1)});
