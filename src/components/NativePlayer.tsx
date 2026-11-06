import {useEffect,useRef,useState} from 'react';
import Hls,{type LoaderContext,type LoaderConfiguration,type LoaderCallbacks} from 'hls.js';
import {takeWarm} from '../services/preload';
class WarmLoader extends Hls.DefaultConfig.loader {
 load(context:LoaderContext,config:LoaderConfiguration,callbacks:LoaderCallbacks<LoaderContext>){
  const data=!context.rangeEnd?takeWarm(context.url):undefined;
  if(!data){super.load(context,config,callbacks);return}
  this.context=context;const now=performance.now();this.stats.loaded=this.stats.total=data.byteLength;this.stats.loading={start:now,first:now,end:now};
  queueMicrotask(()=>{if(!this.stats.aborted)callbacks.onSuccess({url:context.url,data:context.responseType==='arraybuffer'?data:new TextDecoder().decode(data),code:200},this.stats,context,null)});
 }
}
import {saveMetric,mediaId,activationTime,type PlaybackSample} from '../services/metrics';

type Props={active:boolean;src:string;poster?:string;hasAudio?:boolean;onSkip:()=>void};
export function NativePlayer({active,src,poster,hasAudio,onSkip}:Props){
 const ref=useRef<HTMLVideoElement>(null);
 const [status,setStatus]=useState<'idle'|'loading'|'playing'|'paused'|'error'>('idle');
 const [muted,setMuted]=useState(true);
 const [attempt,setAttempt]=useState(0);
 const [progress,setProgress]=useState({time:0,duration:0});
 useEffect(()=>{
  const v=ref.current;
  if(!v||!active||v.closest('.zc-tiktok__fill'))return;
  let h:Hls|undefined;let disposed=false;let failed=false;let timeout:ReturnType<typeof setTimeout>|undefined;
  const started=performance.now();const activated=activationTime(src);let frameHandle:number|undefined;let playingAt:number|null=null;let stalledAt:number|null=null;let saved=false;
  const sample:PlaybackSample={at:new Date().toISOString(),mediaId:mediaId(src),firstFrameMs:null,switchMs:null,watchMs:0,stallMs:0,stalls:0,segmentErrors:0,retries:attempt>0?1:0,failed:false};
  const retryPending=new Set<string>();
  class TrackedLoader extends WarmLoader {
   load(context:LoaderContext,config:LoaderConfiguration,callbacks:LoaderCallbacks<LoaderContext>){
    const segment=/\.(m4s|mp4)(?:[?#]|$)/.test(context.url);
    if(retryPending.delete(context.url))sample.retries++;
    const record=()=>{if(segment)sample.segmentErrors++;retryPending.add(context.url)};
    super.load(context,config,{...callbacks,onError:(...args)=>{record();callbacks.onError(...args)},onTimeout:(...args)=>{record();callbacks.onTimeout(...args)}});
   }
  }
  const closeIntervals=()=>{const now=performance.now();if(playingAt!==null){sample.watchMs+=now-playingAt;playingAt=null}if(stalledAt!==null){sample.stallMs+=now-stalledAt;stalledAt=null}};
  const save=()=>{if(saved)return;closeIntervals();saved=true;saveMetric(sample)};
  const pagehide=()=>save();window.addEventListener('pagehide',pagehide);
  const clear=()=>{if(timeout)clearTimeout(timeout)};
  const fail=()=>{if(disposed||failed)return;failed=true;sample.failed=true;closeIntervals();clear();setStatus('error');v.pause();h?.destroy();h=undefined;v.removeAttribute('src');v.load()};
  const loading=()=>{if(failed||disposed)return;if(sample.firstFrameMs!==null&&stalledAt===null&&!v.paused&&!document.hidden){closeIntervals();stalledAt=performance.now();sample.stalls++}setStatus('loading');clear();timeout=setTimeout(fail,15000)};
  const play=()=>{if(!document.hidden)void v.play().catch(()=>{if(!disposed&&!failed){clear();setStatus('paused')}})};
  const firstFrame=()=>{if(sample.firstFrameMs!==null||disposed)return;const now=performance.now();sample.firstFrameMs=now-started;sample.switchMs=activated===undefined?null:now-activated};
  if(v.requestVideoFrameCallback)frameHandle=v.requestVideoFrameCallback(firstFrame);
  const playing=()=>{if(disposed||failed)return;closeIntervals();if(!v.requestVideoFrameCallback)firstFrame();playingAt=performance.now();clear();setStatus('playing')};
  const paused=()=>{closeIntervals();setStatus(s=>s==='error'?s:'paused')};
  const time=()=>setProgress({time:v.currentTime,duration:Number.isFinite(v.duration)?v.duration:0});
  const visibility=()=>{if(document.hidden){v.pause();clear();h?.stopLoad()}else{h?.startLoad();setStatus(s=>s==='error'?s:'paused')}};
  v.addEventListener('playing',playing);v.addEventListener('pause',paused);v.addEventListener('waiting',loading);v.addEventListener('error',fail);v.addEventListener('timeupdate',time);v.addEventListener('loadedmetadata',time);
  document.addEventListener('visibilitychange',visibility);
  loading();
  // Chromium advertises native HLS but failed remote fMP4 decoding in acceptance.
  const safari=/Safari/.test(navigator.userAgent)&&!/(Chrome|Chromium|Edg|OPR)/.test(navigator.userAgent);
  if(v.canPlayType('application/vnd.apple.mpegurl')&&(safari||!Hls.isSupported())){v.src=src;v.addEventListener('loadedmetadata',play)}else if(Hls.isSupported()){
   h=new Hls({loader:TrackedLoader,maxBufferLength:6,maxMaxBufferLength:10,backBufferLength:2,
    manifestLoadingTimeOut:8000,manifestLoadingMaxRetry:1,levelLoadingTimeOut:8000,levelLoadingMaxRetry:1,
    fragLoadingTimeOut:8000,fragLoadingMaxRetry:2});
   h.on(Hls.Events.MANIFEST_PARSED,play);
   h.on(Hls.Events.ERROR,(_,data)=>{if(data.fatal)fail()});
   h.loadSource(src);h.attachMedia(v);
  }else fail();
  return()=>{disposed=true;if(frameHandle!==undefined)v.cancelVideoFrameCallback(frameHandle);save();window.removeEventListener('pagehide',pagehide);clear();document.removeEventListener('visibilitychange',visibility);
   v.removeEventListener('playing',playing);v.removeEventListener('pause',paused);v.removeEventListener('waiting',loading);v.removeEventListener('error',fail);v.removeEventListener('timeupdate',time);v.removeEventListener('loadedmetadata',time);v.removeEventListener('loadedmetadata',play);
   v.pause();h?.destroy();v.removeAttribute('src');v.load();
  };
 },[active,src,attempt]);
 function toggle(){const v=ref.current;if(!v||!active||status==='error')return;if(v.paused)void v.play().catch(()=>setStatus('paused'));else v.pause()}
 return <div className="player" data-player-status={active?status:'idle'}>
  <video ref={ref} muted={muted} playsInline loop poster={poster} onClick={toggle} aria-label="Video"/>
  {active&&<div className="player-controls"><button onClick={toggle} disabled={status==='error'} aria-label={status==='playing'?'Pausar':'Reproducir'}>{status==='playing'?'Pausar':'Reproducir'}</button>{hasAudio!==false&&<button onClick={()=>setMuted(m=>!m)} aria-label={muted?'Activar sonido':'Silenciar'}>{muted?'Activar sonido':'Silenciar'}</button>}</div>}
  {active&&status==='loading'&&<p className="player-loading" role="status">Cargando video…</p>}
  {active&&status==='error'&&<div className="error" role="alert"><p>No pudimos reproducir este video.</p><button onClick={()=>setAttempt(a=>a+1)}>Intentar de nuevo</button><button onClick={onSkip}>Saltar video</button></div>}
  {active&&progress.duration>0&&status!=='error'&&<input className="player-progress" type="range" min={0} max={progress.duration} step={0.1} value={Math.min(progress.time,progress.duration)} aria-label="Posición del video" onChange={e=>{if(ref.current)ref.current.currentTime=Number(e.target.value)}}/>}
 </div>
}
