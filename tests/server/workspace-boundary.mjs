import assert from 'node:assert/strict';
import paths from '../../server/workspace-paths.cjs';
const base=process.env.TEST_BASE_URL||'http://127.0.0.1:5174';
for(const file of [paths.ENV_FILE,paths.CONFIG,paths.CATALOG,paths.ROOT+'/.workspace.local.json']) {
 const response=await fetch(base+'/@fs/'+file);
 assert([403,404].includes(response.status),'Private filesystem path was not denied');
}
const response=await fetch(base+'/catalog/videos.json');
assert.equal(response.status,200);
assert(Array.isArray((await response.json()).videos));
console.log('PASS: catalog route works; private local files and workspace marker are not served');
