const {CATALOG,CONFIG,runtimePath}=require('../server/workspace-paths.cjs');
const {spawnSync}=require('node:child_process');const fs=require('node:fs');
const python=process.env.VELONEXO_PYTHON||'.venv/bin/python';
const commands=[
 [python,['-m','unittest','discover','-s','tests/python','-v']],
 ['npm',['run','build']],
 [python,['scripts/media_publish.py','validate']],
 [python,['scripts/check_artifacts.py']],
 ...['catalog-check','routes-check','filters-check','feed-check','keyboard-check','external-check','acceptance','faults-check'].map(n=>['node',[`tests/browser/${n}.cjs`]])
];
if(process.argv.includes('--remote'))commands.push(['node',['tests/browser/native-check.cjs']]);
const results=[];
for(const [command,args] of commands){console.log(`\nChecking ${command} ${args.join(' ')}`);const r=spawnSync(command,args,{stdio:'inherit'});results.push({command:[command,...args].join(' '),exitCode:r.status});if(r.status!==0){process.exitCode=1;break}}
fs.mkdirSync(runtimePath('acceptance'),{recursive:true});fs.writeFileSync(runtimePath('acceptance/checks-report.json'),JSON.stringify({checkedAt:new Date().toISOString(),results},null,2));
