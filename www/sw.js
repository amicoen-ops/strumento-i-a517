// Service worker: l'app funziona anche senza internet.
// Pagine: dalla cache e aggiornate in sottofondo. Terreno e mappa: dalla cache appena scaricati.
const V='ia517-app-1.0.0';
const CORE=['./','index.html','app.html','version.js','manifest.webmanifest','icon-192.png','icon-512.png'];
// nell'app installata (APK) le pagine sono già sul telefono: si mettono in cache solo terreno, mappe e meteo
const NATIVE=self.location.hostname==='localhost' && self.location.port==='';
self.addEventListener('install',e=>{ e.waitUntil((NATIVE?Promise.resolve():caches.open(V).then(c=>c.addAll(CORE))).then(()=>self.skipWaiting())); });
self.addEventListener('activate',e=>{ e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith('ia517-app-')&&k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim())); });
async function trim(name,max){ const c=await caches.open(name), ks=await c.keys(); for(let i=0;i<ks.length-max;i++) await c.delete(ks[i]); }
async function cacheFirst(req,name,max){
  const c=await caches.open(name), hit=await c.match(req); if(hit) return hit;
  const r=await fetch(req); if(r.ok||r.type==='opaque'){ c.put(req,r.clone()); if(max) trim(name,max); } return r;
}
async function networkFirst(req,name){
  const c=await caches.open(name);
  try{ const r=await fetch(req); if(r.ok) c.put(req,r.clone()); return r; }
  catch(e){ const hit=await c.match(req); if(hit) return hit; throw e; }
}
async function staleWhileRevalidate(req){
  const c=await caches.open(V), hit=await c.match(req,{ignoreSearch:true});
  const net=fetch(req).then(r=>{ if(r.ok) c.put(req,r.clone()); return r; }).catch(()=>null);
  return hit||(await net)||new Response('offline',{status:503});
}
self.addEventListener('fetch',e=>{
  const req=e.request; if(req.method!=='GET') return;
  const u=new URL(req.url);
  if(u.hostname==='s3.amazonaws.com' && u.pathname.includes('/elevation-tiles-prod/')) e.respondWith(cacheFirst(req,'ia517-dem',4000));
  else if(/tile\.opentopomap\.org$|tile\.openstreetmap\.org$/.test(u.hostname)) e.respondWith(cacheFirst(req,'ia517-map',3000));
  else if(u.hostname==='api.open-meteo.com') e.respondWith(networkFirst(req,'ia517-wx'));
  else if(/fonts\.(googleapis|gstatic)\.com$/.test(u.hostname)) e.respondWith(cacheFirst(req,'ia517-fonts',40));
  else if(u.origin===location.origin && !NATIVE) e.respondWith(staleWhileRevalidate(req));
});
