// Shared by Vite, Studio and Node test runners; never imported by browser code.
const fs = require('node:fs');
const path = require('node:path');
const ROOT = path.resolve(__dirname, '..');
function workspacePaths(root = ROOT, override) {
 root = path.resolve(root);
 const marker = path.join(root, '.workspace.local.json');
 const value = override ?? (process.env.VELONEXO_LOCAL_ROOT || (fs.existsSync(marker) ? JSON.parse(fs.readFileSync(marker, 'utf8')).localRoot : '.local-work'));
 if (typeof value !== 'string' || !value.trim()) throw Error('Invalid local workspace path');
 const LOCAL_ROOT = path.resolve(root, value);
 const RUNTIME = path.join(LOCAL_ROOT, 'runtime');
 return {ROOT:root, LOCAL_ROOT, RUNTIME, CATALOG:path.join(LOCAL_ROOT,'catalog/videos.json'), CONFIG:path.join(LOCAL_ROOT,'config/storage.json'), ENV_FILE:path.join(LOCAL_ROOT,'secrets/.env.local')};
}
const paths = workspacePaths();
module.exports = {...paths, workspacePaths, runtimePath: (...parts) => path.join(paths.RUNTIME, ...parts)};
