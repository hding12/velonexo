// One next-video window, 512 KiB per attempt and 4 MiB per page lifetime.
const WINDOW=512*1024,SESSION=4*1024*1024;
let spent=0;
const cache=new Map<string,ArrayBuffer>();
export function takeWarm(url:string){const value=cache.get(url);cache.delete(url);return value}
export function canWarm(){const c=(navigator as Navigator&{connection?:{saveData?:boolean;effectiveType?:string;downlink?:number}}).connection;return !document.hidden&&navigator.onLine&&!c?.saveData&&(!c?.effectiveType||c.effectiveType==='4g')&&(c?.downlink===undefined||c.downlink>=2)&&!(/Safari/.test(navigator.userAgent)&&!/(Chrome|Chromium|Edg|OPR)/.test(navigator.userAgent))}
export function warmNext(playlist:string){
 const controller=new AbortController();let timer:ReturnType<typeof setTimeout>|undefined;let used=0;
 const stop=()=>controller.abort();
 const visibility=()=>{if(document.hidden)stop()};
 document.addEventListener('visibilitychange',visibility);
 async function get(url:string){
  const remaining=Math.min(WINDOW-used,SESSION-spent);if(remaining<=0)throw Error('budget');
  const r=await fetch(url,{signal:controller.signal,credentials:'omit'});if(!r.ok||!r.body)throw Error('unavailable');
  const length=Number(r.headers.get('Content-Length'));if(!length||length>remaining){if(length>SESSION-spent)spent=SESSION;await r.body.cancel();throw Error('size')}
  const reader=r.body.getReader();const chunks:Uint8Array[]=[];let size=0;
  while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;used+=value.byteLength;spent+=value.byteLength;if(size>length||used>WINDOW||spent>SESSION){await reader.cancel();throw Error('budget')}chunks.push(value)}
  if(size!==length)throw Error('incomplete');const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length}return bytes.buffer;
 }
 const done=(async()=>{if(!canWarm()||spent>=SESSION)return;cache.clear();timer=setTimeout(stop,5000);
  const url=new URL(playlist,location.origin).href;const bytes=await get(url);const text=new TextDecoder().decode(bytes);
  if(!text.startsWith('#EXTM3U')||text.includes('#EXT-X-STREAM-INF')||text.includes('#EXT-X-KEY')||text.includes('#EXT-X-BYTERANGE'))return;
  const init=text.match(/#EXT-X-MAP:URI="([^"]+)"/)?.[1];const first=text.split('\n').find(l=>l.trim()&&!l.startsWith('#'));
  cache.set(url,bytes);
  for(const item of [init,first])if(item){const resolved=new URL(item,url);if(!['http:','https:'].includes(resolved.protocol))return;const data=await get(resolved.href);if(controller.signal.aborted)return;cache.set(resolved.href,data)}
 })().catch(()=>{}).finally(()=>{if(timer)clearTimeout(timer);document.removeEventListener('visibilitychange',visibility)});
 return {cancel:stop,done};
}
