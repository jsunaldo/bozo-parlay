const CACHE='bozo-parlay-v5';
const ASSETS=['./','./index.html','./manifest.json','./icon.svg'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS.map(a=>new Request(a,{cache:'reload'})))).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith('bozo-parlay-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  const url=new URL(e.request.url);
  if(url.origin!==location.origin)return;
  // network first, always revalidated against the server, cache only as the offline fallback
  const net=fetch(new Request(e.request,{cache:'no-cache'})).then(r=>{if(r.ok&&(!url.search||e.request.mode==='navigate')){const cp=r.clone();caches.open(CACHE).then(c=>c.put(url.search?url.origin+url.pathname:e.request,cp))}return r});   // opening from a notification link keeps the offline copy up to date, one entry per address: one-off links (?t=) used to pile up forever
  if(e.request.mode!=='navigate'){e.respondWith(url.search?net:net.catch(()=>caches.match(e.request,{ignoreSearch:true})));return}
  // weak signal: after 3 s open the copy already on the phone instead of sitting on a blank screen (the app still checks for a newer build once it is up)
  e.respondWith(caches.match(e.request,{ignoreSearch:true}).then(hit=>hit?Promise.race([net.catch(()=>null),new Promise(r=>setTimeout(()=>r(null),3000))]).then(r=>r||hit):net));
});
// phone notifications: always show one (iPhones drop subscriptions that stay silent); a tap opens the app
self.addEventListener('push',e=>{let d={};try{d=e.data?e.data.json():{}}catch(x){d={body:e.data?e.data.text():''}}
  e.waitUntil(self.registration.showNotification(d.title||'Bozo Parlay',{body:d.body||'',tag:d.tag||undefined,renotify:!!d.tag,icon:new URL('icon-192.png',self.registration.scope).href,data:{url:d.url||self.registration.scope}}))});
self.addEventListener('notificationclick',e=>{e.notification.close();const url=(e.notification.data&&e.notification.data.url)||self.registration.scope;
  e.waitUntil(self.clients.matchAll({type:'window',includeUncontrolled:true}).then(cs=>{for(const c of cs){if(c.url.startsWith(self.registration.scope)&&'focus'in c){c.postMessage({type:'bp-open',url});return c.focus()}}return self.clients.openWindow(url)}))});
