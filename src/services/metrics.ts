export type PlaybackSample={at:string;mediaId:string;firstFrameMs:number|null;switchMs?:number|null;watchMs:number;stallMs:number;stalls:number;segmentErrors:number;retries:number;failed:boolean};
const KEY='velonexo:playback:v1';
export function readMetrics():PlaybackSample[]{try{const rows=JSON.parse(localStorage.getItem(KEY)||'[]');return Array.isArray(rows)?rows.slice(-200):[]}catch{return []}}
export function saveMetric(sample:PlaybackSample){try{localStorage.setItem(KEY,JSON.stringify([...readMetrics(),sample].slice(-200)))}catch{/* Playback must survive storage denial or quota exhaustion. */}}
export function clearMetrics(){try{localStorage.removeItem(KEY)}catch{}}
export function mediaId(src:string){try{const p=new URL(src,location.origin).pathname;return p.startsWith('/local-media/')?p.split('/')[2]:'native'}catch{return 'native'}}

const activations=new Map<string,number>();
export function markActivation(src:string){activations.set(src,performance.now())}
export function activationTime(src:string){const t=activations.get(src);activations.delete(src);return t}
