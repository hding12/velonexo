export type VideoEntry = {id:string;title:string;creator:string;visibility:'published'|'draft'|'removed';source:{kind:'native';format:'hls';playlist:string;media_map?:string}|{kind:'external';url:string};poster?:string;has_audio?:boolean;category?:string;published_at:string;tags:string[]};
function httpsUrl(value:unknown):boolean{
 if(typeof value!=='string')return false;
 try{const url=new URL(value);return url.protocol==='https:'&&!url.username&&!url.password}catch{return false}
}
function validSource(source:VideoEntry['source']):boolean{
 if(!source)return false;
 if(source.kind==='external')return httpsUrl(source.url);
 return source.kind==='native'&&source.format==='hls'&&typeof source.playlist==='string'&&(httpsUrl(source.playlist)||(/^\/[^/\\]/.test(source.playlist)&&!source.playlist.includes('\\')));
}
export function parseCatalog(value:unknown):VideoEntry[]{
 if(!value||typeof value!=='object'||!('schema_version' in value)||value.schema_version!==1||!('videos' in value)||!Array.isArray(value.videos))throw Error('Invalid catalog');
 const ids=new Set<string>();
 for(const item of value.videos){
  if(!item||typeof item.id!=='string'||!/^[a-zA-Z0-9_-]+$/.test(item.id)||ids.has(item.id)||typeof item.title!=='string'||typeof item.creator!=='string'||!['published','draft','removed'].includes(item.visibility)||!validSource(item.source)||(item.poster!==undefined&&!(typeof item.poster==='string'&&(httpsUrl(item.poster)||(/^\/[^/\\]/.test(item.poster)&&!item.poster.includes('\\')))))||(item.has_audio!==undefined&&typeof item.has_audio!=='boolean')||(item.category!==undefined&&typeof item.category!=='string')||typeof item.published_at!=='string'||!Number.isFinite(Date.parse(item.published_at))||!Array.isArray(item.tags)||!item.tags.every((t:unknown)=>typeof t==='string'))throw Error('Invalid video entry');
  ids.add(item.id);
 }
 return (value.videos as VideoEntry[]).filter(v=>v.visibility==='published').sort((a,b)=>b.published_at.localeCompare(a.published_at)||a.id.localeCompare(b.id));
}
export async function listVideos(signal?:AbortSignal){const r=await fetch('/catalog/videos.json',{signal,cache:'no-store'});if(!r.ok)throw Error('Catalog unavailable');return parseCatalog(await r.json())}

export type TaxonomyOrder={categories?:string[];tags?:string[]};
export async function loadCatalog(signal?:AbortSignal){const r=await fetch('/catalog/videos.json',{signal,cache:'no-store'});if(!r.ok)throw Error('Catalog unavailable');const value=await r.json();return {editorial:(value.editorial||{featured:[],topics:[]}) as Editorial,videos:parseCatalog(value),taxonomy:(value.taxonomy||{}) as TaxonomyOrder}}

export type Editorial={featured:string[];topics:{id:string;title:string;ids:string[]}[]};
