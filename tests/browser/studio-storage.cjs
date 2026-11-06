const {CATALOG,CONFIG,runtimePath}=require('../../server/workspace-paths.cjs');
const {waitState}=require('./studio-poll.cjs');
const {chromium}=require('playwright');const fs=require('node:fs');const assert=require('node:assert/strict');const {spawnSync}=require('node:child_process');
const configPath=CONFIG;const baseline=fs.readFileSync(configPath);
(async()=>{const b=await chromium.launch({channel:'chrome',headless:true});try{
 const p=await b.newPage({viewport:{width:390,height:844}});await p.goto('http://127.0.0.1:5174/studio');const node=p.locator('[data-storage-id="tigris"]');await node.getByRole('button',{name:'Pausar nuevas cargas'}).waitFor();
 const catalog=JSON.parse(fs.readFileSync(CATALOG));const audio=catalog.videos.find(v=>v.id==='native-audio');const mapPath=runtimePath('media',audio.source.media_map.split('/').slice(-3).join('/'));const mapBefore=fs.readFileSync(mapPath);
 await node.getByRole('button',{name:'Pausar nuevas cargas'}).click();await node.getByText('Nuevas cargas pausadas',{exact:true}).waitFor({timeout:15000});assert.equal(await p.getByLabel('Guardar en').locator('option[value="tigris"]').count(),0);assert.deepEqual(fs.readFileSync(mapPath),mapBefore);
 await node.getByRole('button',{name:'Habilitar nuevas cargas'}).click();await node.getByText('Recibe nuevas cargas',{exact:true}).waitFor({timeout:15000});assert.equal(await p.getByLabel('Guardar en').locator('option[value="tigris"]').count(),1);
 for(const id of ['tigris','hf']){const row=p.locator(`[data-storage-id="${id}"]`);await row.getByRole('button',{name:'Comprobar conexión'}).click();await waitState(p,state=>!state.busy&&state.jobs.at(-1)?.state==='succeeded'&&state.storage.find(n=>n.id===id)?.probe?.success,90000);}
 assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await p.screenshot({path:runtimePath('acceptance/studio-storage.png'),fullPage:true});console.log('PASS: provider pause/resume updates placement choices without changing existing maps; both real connection probes verified and test objects deleted');
}finally{await b.close();fs.writeFileSync(configPath+'.test-restore',baseline);fs.renameSync(configPath+'.test-restore',configPath)}})().catch(e=>{console.error(e);process.exit(1)});
