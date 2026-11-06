import {lazy,Suspense,useEffect,useRef,useState} from 'react';
import {TikTok} from '@zyncat/ui/tiktok';
const NativePlayer=lazy(()=>import('./components/NativePlayer').then(m=>({default:m.NativePlayer})));
import {ExternalPlayer} from './components/ExternalPlayer';
import {loadCatalog,type VideoEntry,type TaxonomyOrder,type Editorial} from './services/catalog';
import {readMetrics,markActivation} from './services/metrics';
import {warmNext} from './services/preload';
import {copy} from './content/es-CL';

export default function App(){
 const [editorial,setEditorial]=useState<Editorial>({featured:[],topics:[]});const [topic,setTopic]=useState('');
 const [taxonomy,setTaxonomy]=useState<TaxonomyOrder>({});
 const [active,setActive]=useState(0);
 const [notice,setNotice]=useState('');
 const feed=useRef<HTMLDivElement>(null);
 const [videos,setVideos]=useState<VideoEntry[]>([]);
 const [status,setStatus]=useState<'loading'|'ready'|'error'>('loading');
 const [attempt,setAttempt]=useState(0);
 const [query,setQuery]=useState('');
 const [path,setPath]=useState(location.pathname.replace(/\/$/,'')||'/');
 const [tag,setTag]=useState('');
 const [category,setCategory]=useState('');
 const [order,setOrder]=useState('newest');
 const selectedId=path.startsWith('/video/')?path.slice(7):null;
 const explore=path==='/explore';
 const unknown=path!=='/'&&!explore&&!selectedId;
 const compare=(order:string[]|undefined)=>(a:string,b:string)=>{const ai=order?.indexOf(a)??-1,bi=order?.indexOf(b)??-1;return (ai<0?1e9:ai)-(bi<0?1e9:bi)||a.localeCompare(b,'es-CL')};
 const tags=Array.from(new Set(videos.flatMap(v=>v.tags))).sort(compare(taxonomy.tags));
 const categories=Array.from(new Set(videos.map(v=>v.category||'prueba'))).sort(compare(taxonomy.categories));
 const popularity=readMetrics().filter(m=>!m.failed&&m.watchMs>=3000&&Date.now()-Date.parse(m.at)<7*86400000).reduce<Record<string,number>>((a,m)=>{a[m.mediaId]=(a[m.mediaId]||0)+1;return a},{});
 const selectedTopic=editorial.topics.find(t=>t.id===topic);
 const rankIds=selectedTopic?.ids||(order==='featured'?editorial.featured:[]);
 const shown=videos.filter(v=>selectedId?v.id===selectedId:
  (!topic||!!selectedTopic?.ids.includes(v.id))&&(order!=='featured'||editorial.featured.includes(v.id))&&(!tag||v.tags.includes(tag))&&(!category||(v.category||'prueba')===category)&&
  (v.title+' '+v.tags.join(' ')).toLocaleLowerCase('es-CL').includes(query.toLocaleLowerCase('es-CL')))
  .sort((a,b)=>selectedTopic||order==='featured'?rankIds.indexOf(a.id)-rankIds.indexOf(b.id):order==='popular'?(popularity[b.id]||0)-(popularity[a.id]||0)||b.published_at.localeCompare(a.published_at):order==='oldest'?a.published_at.localeCompare(b.published_at)||a.id.localeCompare(b.id):b.published_at.localeCompare(a.published_at)||a.id.localeCompare(b.id));
 const filtered=!!(tag||query||category||topic||order==='featured');
 function navigate(url:string){history.pushState({},'',url);setPath(url)}
 function clearFilters(){setQuery('');setTag('');setCategory('');setTopic('');setOrder('newest')}
 function home(){clearFilters();navigate('/')}
 function next(delta:number){feed.current?.querySelectorAll('article')[Math.max(0,Math.min(shown.length-1,active+delta))]?.scrollIntoView({behavior:'smooth'})}
 async function share(id:string){const url=new URL('/video/'+id,location.origin).href;try{await navigator.clipboard.writeText(url);setNotice('Enlace copiado.')}catch{setNotice(url)}}
 useEffect(()=>{const sync=()=>setPath(location.pathname.replace(/\/$/,'')||'/');window.addEventListener('popstate',sync);return()=>window.removeEventListener('popstate',sync)},[]);
 useEffect(()=>{
  const controller=new AbortController();setStatus('loading');
  loadCatalog(controller.signal).then(v=>{setVideos(v.videos);setTaxonomy(v.taxonomy);setEditorial(v.editorial);setStatus('ready')}).catch(()=>{if(!controller.signal.aborted)setStatus('error')});
  return()=>controller.abort();
 },[attempt]);
 useEffect(()=>{setActive(0);feed.current?.scrollTo(0,0)},[query,videos,path,tag,category,order,topic]);
 useEffect(()=>{
  const observer=new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting){const index=Number((e.target as HTMLElement).dataset.index);const entry=shown[index];if(entry?.source.kind==='native')markActivation(entry.source.playlist);setActive(index)}},{root:feed.current,threshold:.65});
  feed.current?.querySelectorAll('article').forEach(e=>observer.observe(e));return()=>observer.disconnect();
 },[videos,query,path,tag,category,order,topic]);
 useEffect(()=>{if(explore||unknown)return;const next=shown[active+1];if(next?.source.kind!=='native')return;const playlist=next.source.playlist;let task:ReturnType<typeof warmNext>|undefined;const timer=setTimeout(()=>{task=warmNext(playlist)},1200);return()=>{clearTimeout(timer);task?.cancel()}},[active,videos,query,path,tag,category,order,topic]);
 useEffect(()=>{if(!notice)return;const id=setTimeout(()=>setNotice(''),3500);return()=>clearTimeout(id)},[notice]);
 useEffect(()=>{
  const labels:Record<string,string>={Like:'Me gusta',Comment:'Comentar',Share:'Compartir',Follow:'Seguir','Open menu':'Abrir menú',Search:'Buscar'};
  document.querySelectorAll('[aria-label]').forEach(e=>{const old=e.getAttribute('aria-label')!;if(labels[old])e.setAttribute('aria-label',labels[old])});
  document.querySelectorAll('.zc-tiktok__more').forEach(e=>e.textContent='más');
 },[videos,query,path,tag,category,order,topic,active]);
 return <>
  <aside><h1>VeloNexo<span>•</span></h1><button className={path==='/'?'selected':''} onClick={home}>⌂ <b>Para ti</b></button><button className={explore?'selected':''} onClick={()=>navigate('/explore')}>⌕ <b>Explorar</b></button>{!import.meta.env.VITE_STATIC_EXPORT&&<a href="/studio">Gestionar videos</a>}<p>Mira. Explora.</p><small>Vista previa · Videos de prueba</small></aside>
  <main>
   <header><strong>{selectedId?'Video':explore?'Explorar':'Para ti'}</strong>{selectedId&&<button onClick={home}>Volver al inicio</button>}{!selectedId&&<input aria-label={copy.search} placeholder={copy.search} value={query} onChange={e=>setQuery(e.target.value)}/>}</header>
   {!selectedId&&!unknown&&<section className="catalog-filters" aria-label="Filtrar videos">
    {explore&&<label>Categoría<select aria-label="Categoría" value={category} onChange={e=>setCategory(e.target.value)}><option value="">Todas</option>{categories.map(c=><option key={c} value={c}>{c}</option>)}</select></label>}
    <label>Etiqueta<select aria-label="Etiqueta" value={tag} onChange={e=>setTag(e.target.value)}><option value="">Todas</option>{tags.map(t=><option key={t} value={t}>{t}</option>)}</select></label>
    <label>Ordenar<select aria-label="Ordenar" value={order} onChange={e=>setOrder(e.target.value)}><option value="newest">Más recientes</option><option value="oldest">Más antiguos</option><option value="featured">Destacados</option><option value="popular">Más vistos aquí</option></select></label>
    <label>Colección<select aria-label="Colección" value={topic} onChange={e=>setTopic(e.target.value)}><option value="">Todas</option>{editorial.topics.map(t=><option key={t.id} value={t.id}>{t.title}</option>)}</select></label>
    {order==='popular'&&<small>Según las reproducciones de al menos 3 segundos guardadas en este navegador durante los últimos 7 días.</small>}
    {filtered&&<button onClick={clearFilters}>Limpiar filtros</button>}
   </section>}
   <div className={explore?'explore':selectedId?'feed':'feed with-filters'} ref={feed} tabIndex={0} aria-label={explore?'Resultados':'Videos'} onKeyDown={e=>{
    if(e.target!==e.currentTarget&&/INPUT|SELECT|BUTTON|A/.test((e.target as HTMLElement).tagName))return;
    if(!explore&&['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();next(e.key==='ArrowDown'?1:-1)}
   }}>
    {unknown?<div className="feed-status"><p>Esta página no está disponible.</p><button onClick={home}>Volver al inicio</button></div>:
    status==='loading'?<p className="feed-status">{copy.loading}</p>:
    status==='error'?<div className="feed-status" role="alert"><p>{copy.failed}</p><button onClick={()=>setAttempt(a=>a+1)}>{copy.retry}</button></div>:
    shown.length===0?<p className="feed-status">{selectedId?'Este video no está disponible.':filtered?copy.noResults:copy.empty}</p>:
    explore?<div className="explore-grid">{shown.map(entry=><a className="explore-card" key={entry.id} href={'/video/'+entry.id} onClick={e=>{if(!e.metaKey&&!e.ctrlKey&&!e.shiftKey&&!e.altKey){e.preventDefault();navigate('/video/'+entry.id)}}}>
     {entry.poster?<img src={entry.poster} alt="" loading="lazy"/>:<div className="poster-placeholder" aria-hidden="true">▶</div>}<strong>{entry.title}</strong><span>{entry.creator}</span><small>{entry.tags.join(' · ')}</small>
    </a>)}</div>:
    shown.map((entry,i)=><article key={entry.id} data-index={i} data-video-id={entry.id}>
     {Math.abs(active-i)<=1?<TikTok className={entry.source.kind==='external'?'video-card has-external':'video-card'} surface="mobile" ratio="9:16"
      name={entry.creator} caption={entry.title} music={entry.source.kind==='external'?new URL(entry.source.url).hostname:'Video de prueba'} sound={entry.source.kind==='external'?'Enlace externo':entry.has_audio?'Audio original':'Sin audio'} avatar={<span className="avatar">V</span>}
      media={entry.source.kind==='native'?(active===i?<Suspense fallback={<p role="status">Cargando video…</p>}><NativePlayer active={active===i} src={entry.source.playlist} poster={entry.poster} hasAudio={entry.has_audio} onSkip={()=>shown.length>1?next(i===shown.length-1?-i:1):home()}/></Suspense>:<div className="inactive-media">{entry.poster&&<img src={entry.poster} alt=""/>}</div>):<ExternalPlayer active={active===i} url={entry.source.url}/>}
      onAction={a=>{if(a==='share')void share(entry.id)}} followed={false}/>:<div className="dormant-card" aria-label={entry.title}/>}
    </article>)}
   </div>
   {!explore&&<nav className="arrows" hidden={shown.length<2||unknown}><button aria-label="Video anterior" onClick={()=>next(-1)}>↑</button><button aria-label="Video siguiente" onClick={()=>next(1)}>↓</button></nav>}
   <footer><button onClick={home} aria-current={path==='/'?'page':undefined}>⌂ <strong>Inicio</strong></button><button onClick={()=>navigate('/explore')} aria-current={explore?'page':undefined}>⌕ <strong>Explorar</strong></button>{!import.meta.env.VITE_STATIC_EXPORT&&<a href="/studio">Gestionar</a>}</footer>
  </main>{notice&&<div className="notice" role="status">{notice}</div>}
 </>;
}
