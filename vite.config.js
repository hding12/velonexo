import {studioMiddleware} from './server/studio.js';
import {defineConfig} from 'vite';
import fs from 'node:fs';
import path from 'node:path';
function localMedia(req,res,next){
 const pathname=new URL(req.url,'http://localhost').pathname;
 if(!pathname.startsWith('/local-media/'))return next();
 const match=pathname.match(/^\/local-media\/([A-Za-z0-9_-]+)\/([a-f0-9]{16})\/(map\.json|play\.m3u8|poster\.jpg|init\.mp4|seg_\d+\.m4s)$/);
 if(!match||!['GET','HEAD'].includes(req.method)){res.statusCode=404;return res.end()}
 const file=path.resolve('.local/media',...match.slice(1));
 try{
  const map=JSON.parse(fs.readFileSync(path.join(path.dirname(file),'map.json'),'utf8'));
  if(map.state==='purged'){res.statusCode=404;return res.end('Media removed')}
  const size=fs.statSync(file).size;let start=0,end=size-1;
  res.setHeader('Content-Type',({'.m3u8':'application/vnd.apple.mpegurl','.json':'application/json','.jpg':'image/jpeg','.mp4':'video/mp4','.m4s':'video/iso.segment'})[path.extname(file)]);
  res.setHeader('Cache-Control','no-store');res.setHeader('Accept-Ranges','bytes');
  if(req.headers.range){
   const r=/^bytes=(\d+)-(\d*)$/.exec(req.headers.range);
   if(!r||Number(r[1])>=size||(r[2]&&Number(r[2])<Number(r[1]))){res.statusCode=416;res.setHeader('Content-Range',`bytes */${size}`);return res.end()}
   start=Number(r[1]);end=r[2]?Math.min(Number(r[2]),size-1):size-1;res.statusCode=206;res.setHeader('Content-Range',`bytes ${start}-${end}/${size}`);
  }
  res.setHeader('Content-Length',end-start+1);
  if(req.method==='HEAD')return res.end();
  const stream=fs.createReadStream(file,{start,end});stream.on('error',()=>res.destroy());res.on('close',()=>stream.destroy());stream.pipe(res);
 }catch{res.statusCode=404;res.end('Media not available')}
}
export default defineConfig({server:{watch:{ignored:['**/.local/**','**/public/catalog/**']}},plugins:[{name:'local-demo-media',configureServer(server){
 server.middlewares.use(studioMiddleware(server));
 server.middlewares.use(localMedia);
 server.middlewares.use('/demo.m3u8',(req,res)=>{try{res.setHeader('Content-Type','application/vnd.apple.mpegurl');res.setHeader('Cache-Control','no-store');res.end(fs.readFileSync('.local/hls-smoke/remote.m3u8'))}catch{res.statusCode=404;res.end('Demo not generated')}})
}}]});
