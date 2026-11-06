import {useEffect,useRef,useState} from 'react';
export function externalEmbed(raw:string):{kind:'youtube'|'x';id:string}|null{
 const u=new URL(raw);const host=u.hostname.toLowerCase();
 if(['youtube.com','www.youtube.com','m.youtube.com','youtu.be'].includes(host)){
  const id=host==='youtu.be'?u.pathname.slice(1):u.pathname==='/watch'?u.searchParams.get('v'):u.pathname.match(/^\/(?:shorts|embed)\/([^/]+)\/?$/)?.[1];
  if(id&&/^[\w-]{11}$/.test(id))return {kind:'youtube',id};
 }
 if(['twitter.com','www.twitter.com','x.com','www.x.com'].includes(host)){
  const id=u.pathname.match(/^\/\w+\/status\/(\d+)(?:\/video\/\d+)?\/?$/)?.[1];
  if(id)return {kind:'x',id};
 }
 return null;
}
export function ExternalPlayer({url,active}:{url:string;active:boolean}){
 const root=useRef<HTMLDivElement>(null);const [visible,setVisible]=useState(false);const embed=externalEmbed(url);
 useEffect(()=>{const sync=()=>setVisible(active&&!document.hidden&&!root.current?.closest('.zc-tiktok__fill'));sync();document.addEventListener('visibilitychange',sync);return()=>document.removeEventListener('visibilitychange',sync)},[active,url]);
 const src=embed?.kind==='youtube'?`https://www.youtube.com/embed/${embed.id}?playsinline=1&rel=0&hl=es&origin=${encodeURIComponent(location.origin)}`:embed?`/embeds/x.html?id=${embed.id}`:null;
 return <div ref={root} className={embed?'external-player':'external-source'}>{src&&visible?<iframe key={src} src={src} title={embed?.kind==='youtube'?'Reproductor de YouTube':'Publicación de X'} allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowFullScreen referrerPolicy="strict-origin-when-cross-origin"/>:!embed?<><h2>Enlace externo</h2><p>{new URL(url).hostname}</p></>:null}<a href={url} target="_blank" rel="noopener noreferrer">Ver en el sitio original</a></div>
}
