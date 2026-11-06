import './style.css';
import {lazy,Suspense} from 'react';
import {createRoot} from 'react-dom/client';
const Page=!import.meta.env.VITE_STATIC_EXPORT&&location.pathname==='/studio'?lazy(()=>import('./components/Studio').then(m=>({default:m.Studio}))):lazy(()=>import('./App'));
createRoot(document.getElementById('root')!).render(<Suspense fallback={<p role="status">Cargando…</p>}><Page/></Suspense>);
