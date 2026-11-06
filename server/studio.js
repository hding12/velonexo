// Development-only local Studio. Not a public administration service.
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import {randomUUID,randomBytes,timingSafeEqual} from 'node:crypto';
import {spawn} from 'node:child_process';

const MAX_UPLOAD=250*1024*1024;
const ID=/^[A-Za-z0-9_-]{1,100}$/;
function send(res,status,data){res.statusCode=status;res.setHeader('Content-Type','application/json');res.setHeader('Cache-Control','no-store');res.setHeader('Cross-Origin-Resource-Policy','same-origin');res.end(JSON.stringify(data))}
function metadata(value){
 if(!value||typeof value.title!=='string'||!value.title.trim()||value.title.length>300||typeof value.creator!=='string'||value.creator.length>80||typeof value.category!=='string'||value.category.length>80||!Array.isArray(value.tags)||value.tags.length>20||value.tags.some(t=>typeof t!=='string'||!t.trim()||t.length>50))throw Error('invalid-metadata');
 return {title:value.title.trim(),creator:value.creator.trim(),category:value.category.trim(),tags:value.tags};
}
async function body(req){let text='';for await(const chunk of req){text+=chunk.toString();if(Buffer.byteLength(text)>8192)throw Error('invalid-metadata')}return JSON.parse(text)}

export function studioMiddleware(server,options={}){
 const ROOT=options.root||process.cwd();
 const STATE=path.join(ROOT,'.local/studio');
 const worker=options.worker||[path.join(ROOT,'.venv/bin/python'),'-u',path.join(ROOT,'scripts/media_publish.py')];
 const readCatalog=()=>JSON.parse(fs.readFileSync(path.join(ROOT,'public/catalog/videos.json'),'utf8'));
 const sourceFile=job=>path.join(STATE,'uploads',job.id+'.source');
 const entryExists=job=>readCatalog().videos.some(v=>v.id===job.videoId);
 const publicJob=job=>({id:job.id,videoId:job.videoId,title:job.title,action:job.action,state:job.state,stage:job.stage,error:job.error,estimate:job.estimate,attempts:job.attempts||1,
  canRetry:job.state==='failed'&&!!job.args&&(job.action!=='upload'||(entryExists(job)||(job.sourceReady&&fs.existsSync(sourceFile(job))))),
  canCleanup:job.state==='failed'&&job.action==='upload'&&!entryExists(job)});
 fs.mkdirSync(path.join(STATE,'uploads'),{recursive:true});
 const token=randomBytes(32).toString('hex');
 const jobsFile=path.join(STATE,'jobs.json');
 let jobs=fs.existsSync(jobsFile)?JSON.parse(fs.readFileSync(jobsFile,'utf8')):[];
 for(const job of jobs)if(['running','uploading'].includes(job.state)){if(job.action==='upload'&&entryExists(job)){job.state='succeeded';job.stage='done';delete job.args;fs.rmSync(sourceFile(job),{force:true})}else{job.state='failed';job.error='interrupted';}}
 let active=null;let child=null;let shuttingDown=false;
 const persist=()=>{fs.writeFileSync(jobsFile+'.tmp',JSON.stringify(jobs,null,2));fs.renameSync(jobsFile+'.tmp',jobsFile)};
 persist();
 function run(job,args,reason){
  job.reason=job.reason||reason||'Operación local desde Studio';
  job.args=args;job.attempts=(job.attempts||0)+1;delete job.error;delete job.finishedAt;job.state='running';job.stage=job.action==='upload'?'prepare':job.action;persist();
  const processHandle=spawn(worker[0],[...worker.slice(1),...args],{cwd:ROOT,env:{...process.env,VELONEXO_AUDIT_REASON:job.reason},detached:true,stdio:['ignore','pipe','pipe']});
  child=processHandle;let finished=false;let stdout='';let stderr='';let stopReason;let forceKill;
  const stop=reason=>{stopReason=reason;try{process.kill(-processHandle.pid,'SIGTERM')}catch{}forceKill=setTimeout(()=>{if(!finished)try{process.kill(-processHandle.pid,'SIGKILL')}catch{}},3000)};
  const finish=(ok)=>{if(finished)return;finished=true;clearTimeout(timeout);clearTimeout(forceKill);
   const allowed=new Set(['busy','invalid-media','missing-file-or-tool','network-error','capacity-limit','provider-changed','integrity-error','validation-error','storage-permission','source-missing','storage-or-network-error']);
   const code=[...stderr.matchAll(/ERROR_CODE ([a-z-]+)/g)].at(-1)?.[1];
   job.state=ok?'succeeded':'failed';job.stage=ok?'done':job.stage;
   if(!ok)job.error=shuttingDown?'interrupted':stopReason||(allowed.has(code)?code:'operation-failed');
   if(ok&&job.action==='cleanup'){
    const original=jobs.find(j=>j.id===job.cleanupOf);if(original){original.state='cleaned';delete original.args;try{fs.rmSync(sourceFile(original),{force:true})}catch{original.state='failed';original.error='cleanup-local-failed'}}
   }
   if(ok&&job.action==='upload'){try{fs.rmSync(sourceFile(job),{force:true})}catch{}delete job.args;}
   job.finishedAt=new Date().toISOString();persist();if(active===job)active=null;if(child===processHandle)child=null;
  };
  const timeout=setTimeout(()=>stop('timeout'),options.timeoutMs||15*60*1000);
  processHandle.stdout.on('data',chunk=>{stdout=(stdout+chunk.toString()).slice(-8192);for(const line of stdout.split('\n')){try{const v=JSON.parse(line);if(Number.isFinite(v.new_bytes)&&v.new_bytes>=0&&v.project_bytes_after&&Object.values(v.project_bytes_after).every(n=>Number.isFinite(n)&&n>=0)){job.estimate={newBytes:v.new_bytes,projectBytesAfter:v.project_bytes_after};persist()}}catch{}}const matches=[...stdout.matchAll(/STAGE (prepare|upload|verify|catalog)/g)];if(matches.length){job.stage=matches.at(-1)[1];persist()}});
  // Drain stderr without exposing CLI errors, credentials or paths to the client.
  processHandle.stderr.on('data',chunk=>{stderr=(stderr+chunk.toString()).slice(-8192)});
  processHandle.on('error',()=>{stopReason='missing-file-or-tool';finish(false)});processHandle.on('close',code=>finish(code===0));
 }
 server.httpServer?.once('close',()=>{shuttingDown=true;if(child){try{process.kill(-child.pid,'SIGTERM')}catch{}}});
 return async(req,res,next)=>{
  const pathname=new URL(req.url,'http://localhost').pathname;if(!pathname.startsWith('/api/studio/'))return next();
  const host=req.headers.host;
  const expected=new Set([`127.0.0.1:${req.socket.localPort}`,`localhost:${req.socket.localPort}`,`[::1]:${req.socket.localPort}`]);
  if(!expected.has(host)||!['127.0.0.1','::1','::ffff:127.0.0.1'].includes(req.socket.remoteAddress)||
    (req.headers.origin&&req.headers.origin!==`http://${host}`)||['cross-site','same-site'].includes(req.headers['sec-fetch-site']))return send(res,403,{error:'local-only'});
  if(req.method==='GET'&&pathname==='/api/studio/session')return send(res,200,{token,maxUploadBytes:MAX_UPLOAD});
  const supplied=req.headers['x-studio-token'];
  if(typeof supplied!=='string'||!(/^[a-f0-9]{64}$/).test(supplied)||!timingSafeEqual(Buffer.from(supplied),Buffer.from(token)))return send(res,403,{error:'session-required'});
  try{
   if(req.method==='GET'&&pathname==='/api/studio/state'){
    const config=JSON.parse(fs.readFileSync(path.join(ROOT,'config/storage.json'),'utf8'));
    const ledgerFile=path.join(ROOT,'.local/publisher/objects.json');const ledger=fs.existsSync(ledgerFile)?JSON.parse(fs.readFileSync(ledgerFile,'utf8')):{};
    const probesFile=path.join(ROOT,'.local/publisher/probes.json');const probes=fs.existsSync(probesFile)?JSON.parse(fs.readFileSync(probesFile,'utf8')):{};
    const storage=config.providers.map(p=>({id:p.id,type:p.type,enabled:p.enabled!==false,limitBytes:p.project_limit_bytes,usedBytes:Object.values(ledger).filter(o=>o.provider_id===p.id&&!o.deleted).reduce((n,o)=>n+o.size_bytes,0),probe:probes[p.id]}));
    const catalog=readCatalog();const taxonomy={categories:[...new Set([...(catalog.taxonomy?.categories||[]),...catalog.videos.map(v=>v.category||'prueba').sort()])],tags:[...new Set([...(catalog.taxonomy?.tags||[]),...catalog.videos.flatMap(v=>v.tags).sort()])]};
    return send(res,200,{editorial:catalog.editorial||{featured:[],topics:[]},taxonomy,storage,entries:readCatalog().videos.filter(v=>v.source.kind==='native'),jobs:jobs.map(publicJob),busy:!!active,providers:config.providers.filter(p=>p.enabled!==false).map(p=>p.id)});
   }
   if(req.method==='GET'&&pathname==='/api/studio/backups'){
    const dir=path.join(ROOT,'.local/publisher/backups');
    const backups=(fs.existsSync(dir)?fs.readdirSync(dir):[]).filter(id=>/^\d{8}T\d{12}\.json$/.test(id)).sort().reverse().flatMap(id=>{
     try{const file=path.join(dir,id);if(!fs.lstatSync(file).isFile())return [];const data=JSON.parse(fs.readFileSync(file,'utf8'));if(!Array.isArray(data.videos))return [];return [{id,createdAt:fs.statSync(file).mtime.toISOString(),entries:data.videos.length,published:data.videos.filter(v=>v.visibility==='published').length}]}catch{return []}
    });return send(res,200,{backups});
   }
   if(req.method==='GET'&&pathname==='/api/studio/history'){
    const dir=path.join(ROOT,'.local/publisher/events');
    const events=(fs.existsSync(dir)?fs.readdirSync(dir):[]).filter(n=>/^\d{8}T\d{12}-[a-f0-9]{32}\.json$/.test(n)).sort().reverse().map(n=>{const file=path.join(dir,n);return fs.lstatSync(file).isFile()?JSON.parse(fs.readFileSync(file,'utf8')):null}).filter(Boolean);
    return send(res,200,{events});
   }
   if(req.method!=='POST')return send(res,405,{error:'method-not-allowed'});
   const requestReason=req.headers['x-studio-reason']?decodeURIComponent(req.headers['x-studio-reason']):'Operación local desde Studio';
   if(typeof requestReason!=='string'||!requestReason.trim()||requestReason.length>300)return send(res,400,{error:'invalid-reason'});
   if(active||shuttingDown)return send(res,409,{error:'busy'});
   if(pathname==='/api/studio/restore-backup'){
    const value=await body(req);
    if(typeof value.id!=='string'||!/^\d{8}T\d{12}\.json$/.test(value.id))return send(res,400,{error:'invalid-backup'});
    const file=path.join(ROOT,'.local/publisher/backups',value.id);
    if(!fs.existsSync(file)||!fs.lstatSync(file).isFile())return send(res,404,{error:'not-found'});
    if(active)return send(res,409,{error:'busy'});
    const job={id:randomUUID(),videoId:'',title:value.id,action:'restore-catalog',state:'running',stage:'restore-catalog',createdAt:new Date().toISOString()};jobs.push(job);active=job;run(job,['restore-catalog',file],requestReason);return send(res,202,{job:publicJob(job)});
   }
   const storageMatch=pathname.match(/^\/api\/studio\/storage\/([A-Za-z0-9_-]+)\/(probe|toggle)$/);
   if(storageMatch){
    const [,id,action]=storageMatch;const config=JSON.parse(fs.readFileSync(path.join(ROOT,'config/storage.json'),'utf8'));
    if(!config.providers.some(p=>p.id===id))return send(res,404,{error:'not-found'});
    const args=[action==='probe'?'probe-provider':'set-provider',id];
    if(action==='toggle'){const value=await body(req);if(typeof value.enabled!=='boolean')return send(res,400,{error:'invalid-request'});args.push('--enabled',String(value.enabled))}
    if(active)return send(res,409,{error:'busy'});
    const job={id:randomUUID(),videoId:'',title:id,action:'storage-'+action,state:'running',stage:'storage-'+action,createdAt:new Date().toISOString()};jobs.push(job);active=job;run(job,args,requestReason);return send(res,202,{job:publicJob(job)});
   }
   if(pathname==='/api/studio/editorial'){
    const value=await body(req);if(!value||typeof value!=='object')return send(res,400,{error:'invalid-request'});
    if(active)return send(res,409,{error:'busy'});
    const job={id:randomUUID(),videoId:'',title:'Selecciones',action:'editorial',state:'running',stage:'editorial',createdAt:new Date().toISOString()};jobs.push(job);active=job;run(job,['editorial','--value-json='+JSON.stringify(value)],requestReason);return send(res,202,{job:publicJob(job)});
   }
   if(pathname==='/api/studio/taxonomy'){
    const value=await body(req);
    if(!['category','tag'].includes(value.kind))return send(res,400,{error:'invalid-request'});
    const args=['taxonomy','--kind',value.kind];
    if(value.order!==undefined){if(!Array.isArray(value.order)||value.order.length>500||value.order.some(n=>typeof n!=='string'||!n.trim()||n.length>80))return send(res,400,{error:'invalid-request'});args.push('--order-json='+JSON.stringify(value.order))}
    else{if(typeof value.source!=='string'||typeof value.target!=='string'||!value.target.trim()||value.target.length>80)return send(res,400,{error:'invalid-request'});args.push('--source='+value.source,'--target='+value.target)}
    if(active)return send(res,409,{error:'busy'});
    const job={id:randomUUID(),videoId:'',title:value.kind,action:'taxonomy',state:'running',stage:'taxonomy',createdAt:new Date().toISOString()};jobs.push(job);active=job;run(job,args,requestReason);return send(res,202,{job:publicJob(job)});
   }
   if(pathname==='/api/studio/batch'){
    const value=await body(req);
    if(!['publish','withdraw'].includes(value.action)||!Array.isArray(value.ids)||!value.ids.length||value.ids.length>50||new Set(value.ids).size!==value.ids.length||value.ids.some(id=>typeof id!=='string'||!ID.test(id)))return send(res,400,{error:'invalid-batch'});
    const entries=readCatalog().videos;
    if(value.ids.some(id=>!entries.some(v=>v.id===id&&v.source.kind==='native')))return send(res,400,{error:'invalid-batch'});
    if(active)return send(res,409,{error:'busy'});
    const job={id:randomUUID(),videoId:value.ids[0],title:`${value.ids.length} videos`,action:'batch-'+value.action,state:'running',stage:'batch-'+value.action,createdAt:new Date().toISOString()};jobs.push(job);active=job;
    run(job,['bulk-state','--action',value.action,...value.ids],requestReason);return send(res,202,{job:publicJob(job)});
   }
   const jobMatch=pathname.match(/^\/api\/studio\/jobs\/([a-f0-9-]+)\/(retry|cleanup)$/);
   if(jobMatch){
    const job=jobs.find(j=>j.id===jobMatch[1]);if(!job||job.state!=='failed')return send(res,409,{error:'job-not-retryable'});
    if(jobMatch[2]==='retry'){
     // A crash after committing the catalog must not overwrite an existing entry.
     if(job.action==='upload'&&entryExists(job)){job.state='succeeded';job.stage='done';delete job.args;fs.rmSync(sourceFile(job),{force:true});persist();return send(res,200,{job:publicJob(job)})}
     if(!publicJob(job).canRetry)return send(res,409,{error:'source-unavailable'});
     active=job;run(job,job.args);return send(res,202,{job:publicJob(job)});
    }
    if(!publicJob(job).canCleanup)return send(res,409,{error:'cleanup-refused'});
    const cleanup={id:randomUUID(),videoId:job.videoId,title:job.title,action:'cleanup',cleanupOf:job.id,state:'running',stage:'cleanup',createdAt:new Date().toISOString()};
    jobs.push(cleanup);active=cleanup;run(cleanup,['cleanup-unpublished',job.videoId]);return send(res,202,{job:publicJob(cleanup)});
   }
   if(pathname==='/api/studio/upload'){
    const length=Number(req.headers['content-length']);if(!Number.isInteger(length)||length<=0||length>MAX_UPLOAD)return send(res,413,{error:'file-size'});
    const value=metadata(JSON.parse(decodeURIComponent(req.headers['x-studio-metadata']||'')));
    const provider=req.headers['x-studio-provider'];
    const allowed=['local','distributed',...JSON.parse(fs.readFileSync(path.join(ROOT,'config/storage.json'),'utf8')).providers.filter(p=>p.enabled!==false).map(p=>p.id)];
    if(!allowed.includes(provider))return send(res,400,{error:'invalid-provider'});
    const job={id:randomUUID(),videoId:'video-'+randomUUID(),action:'upload',title:value.title,state:'uploading',stage:'receiving',createdAt:new Date().toISOString()};jobs.push(job);active=job;persist();
    const file=path.join(STATE,'uploads',job.id+'.source');let received=0;let handle;
    try{handle=await fsp.open(file,'wx');for await(const chunk of req){received+=chunk.length;if(received>MAX_UPLOAD||received>length)throw Error('file-size');await handle.write(chunk)}await handle.close();handle=null;if(received!==length)throw Error('incomplete-upload');}
    catch{await handle?.close();await fsp.rm(file,{force:true});job.state='failed';job.error='upload-failed';persist();active=null;return send(res,400,{error:'upload-failed'})}
    const args=['publish','--draft','--input',file,'--id',job.videoId,`--title=${value.title}`,`--creator=${value.creator}`,`--category=${value.category}`];
    for(const tag of value.tags)args.push(`--tag=${tag}`);
    if(provider!=='distributed')args.push('--provider',provider);
    job.sourceReady=true;run(job,args,requestReason);return send(res,202,{job:publicJob(job)});
   }
   const match=pathname.match(/^\/api\/studio\/entries\/([A-Za-z0-9_-]+)\/(publish|withdraw|refresh|edit)$/);
   if(!match||!ID.test(match[1]))return send(res,404,{error:'not-found'});
   const [,id,action]=match;const entry=readCatalog().videos.find(v=>v.id===id&&v.source.kind==='native');if(!entry)return send(res,404,{error:'not-found'});
   const args=[{publish:'restore-entry',withdraw:'withdraw',refresh:'refresh',edit:'edit'}[action],id];
   if(action==='edit'){const v=metadata(await body(req));args.push(`--title=${v.title}`,`--creator=${v.creator}`,`--category=${v.category}`);for(const tag of v.tags)args.push(`--tag=${tag}`);}
   // Recheck after an asynchronous request body: there is only one worker at a time.
   if(active)return send(res,409,{error:'busy'});
   const job={id:randomUUID(),videoId:id,title:entry.title,action,state:'running',stage:action,createdAt:new Date().toISOString()};jobs.push(job);active=job;run(job,args,requestReason);return send(res,202,{job:publicJob(job)});
  }catch{return send(res,400,{error:'invalid-request'})}
 };
}
