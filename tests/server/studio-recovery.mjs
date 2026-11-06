import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import {studioMiddleware} from '../../server/studio.js';
const root=fs.mkdtempSync(path.join(os.tmpdir(),'velonexo-recovery-'));
fs.mkdirSync(path.join(root,'public/catalog'),{recursive:true});fs.mkdirSync(path.join(root,'config'));
fs.writeFileSync(path.join(root,'public/catalog/videos.json'),JSON.stringify({schema_version:1,videos:[]}));fs.writeFileSync(path.join(root,'config/storage.json'),JSON.stringify({providers:[]}));
const stub=path.join(root,'worker.cjs');
fs.writeFileSync(stub,`const fs=require('fs');const a=process.argv.slice(2);const id=a[a.indexOf('--id')+1];
if(a[0]==='cleanup-unpublished')process.exit(0);
if(fs.existsSync('hang')){console.log('STAGE upload');setInterval(()=>{},1000)}else if(!fs.existsSync('fail-once')){fs.writeFileSync('fail-once','1');console.log('STAGE upload');console.error('ERROR_CODE storage-permission\\nsecret-url-that-must-not-leak');process.exitCode=1}else{const c=JSON.parse(fs.readFileSync('public/catalog/videos.json'));c.videos.push({id,source:{kind:'native'},visibility:'draft'});fs.writeFileSync('public/catalog/videos.json',JSON.stringify(c));console.log('STAGE catalog')}`);
let server,base,token;
async function start(timeoutMs=10000){server=http.createServer();const middleware=studioMiddleware({httpServer:server},{root,worker:[process.execPath,stub],timeoutMs});server.on('request',(req,res)=>middleware(req,res,()=>{res.statusCode=404;res.end()}));await new Promise(r=>server.listen(0,'127.0.0.1',r));base='http://127.0.0.1:'+server.address().port;token=(await(await fetch(base+'/api/studio/session')).json()).token;}
async function api(route,options={}){return fetch(base+'/api/studio/'+route,{...options,headers:{'X-Studio-Token':token,...options.headers}})}
async function state(){const r=await api('state');return r.json()}
async function wait(id,status){for(let i=0;i<150;i++){const s=await state();const j=s.jobs.find(j=>j.id===id);if(j?.state===status)return j;await new Promise(r=>setTimeout(r,50))}throw Error('job did not reach '+status)}
async function upload(){const r=await api('upload',{method:'POST',headers:{'X-Studio-Metadata':encodeURIComponent(JSON.stringify({title:'Test',creator:'@test',category:'prueba',tags:[]})),'X-Studio-Provider':'local'},body:Buffer.from('fixture')});assert.equal(r.status,202);return(await r.json()).job;}
async function close(){await new Promise(r=>server.close(r));await new Promise(r=>setTimeout(r,150));}
try{
 await start();const job=await upload();const failed=await wait(job.id,'failed');assert.equal(failed.error,'storage-permission');assert(failed.canRetry);assert(failed.canCleanup);const data=JSON.stringify(await state());assert(!data.includes('secret-url'));assert(!data.includes(root));assert(!data.includes('args'));
 assert.equal((await api('jobs/'+job.id+'/retry',{method:'POST'})).status,202);const done=await wait(job.id,'succeeded');assert.equal(done.attempts,2);assert.equal((await state()).entries.length,1);assert.equal((await api('jobs/'+job.id+'/cleanup',{method:'POST'})).status,409);
 // Interrupt a live worker, restart without automatically rerunning it, then retry.
 fs.writeFileSync(path.join(root,'hang'),'1');const interrupted=await upload();await wait(interrupted.id,'running');await close();await start();const recovered=await wait(interrupted.id,'failed');assert.equal(recovered.error,'interrupted');assert(recovered.canRetry);fs.unlinkSync(path.join(root,'hang'));await api('jobs/'+interrupted.id+'/retry',{method:'POST'});await wait(interrupted.id,'succeeded');assert.equal((await state()).entries.length,2);
 await close();await start(100);fs.writeFileSync(path.join(root,'hang'),'1');const timed=await upload();assert.equal((await wait(timed.id,'failed')).error,'timeout');assert.equal((await state()).busy,false);fs.unlinkSync(path.join(root,'hang'));
 const clean=await api('jobs/'+timed.id+'/cleanup',{method:'POST'});assert.equal(clean.status,202);await wait((await clean.json()).job.id,'succeeded');assert.equal((await state()).jobs.find(j=>j.id===timed.id).state,'cleaned');assert(!fs.existsSync(path.join(root,'.local/studio/uploads',timed.id+'.source')));
 console.log('PASS: retry preserves ID, no secret leakage, restart recovery, timeout termination, cleanup guard and source removal');
}finally{if(server?.listening)await close();fs.rmSync(root,{recursive:true,force:true})}
