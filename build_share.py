#!/usr/bin/env python3
"""Build the read-only league site (../bozo-parlay-club) from this app.
Strips every built-in seed (all leagues' history) out of the page, flips SHARE_MODE on,
and makes the page load its one league from data.json. data.json itself is managed
separately: the commissioner publishes it from the app (Crew → League site) or hands over a snapshot."""
import os,re,shutil,json,subprocess,sys
SRC=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(os.path.dirname(SRC),'bozo-parlay-club')
os.makedirs(OUT,exist_ok=True)
s=open(os.path.join(SRC,'index.html')).read()
a=s.index('/*@@SEEDS-START@@*/'); b=s.index('/*@@SEEDS-END@@*/')
STUB=r"""/* league site: no seeds, one league, loaded from data.json */
const SHARE_KEY='bozo-club-data-v1';
function migrateDB(d){return d}
function shareDB(j){const l={id:'share',name:j.name||'Bozo Parlay',seasons:(j.seasons||[]).map(x=>({...x,data:migrate(x.data||fresh())})),activeSeason:j.activeSeason,updatedAt:j.updatedAt||null};if(!l.seasons.length){const d=fresh();l.seasons=[{id:'s0',name:'',data:d}]}if(!l.seasons.find(x=>x.id===l.activeSeason))l.activeSeason=l.seasons[0].id;return{leagues:[l],active:'share',seedV:99,updatedAt:j.updatedAt||null}}
function loadDB(){try{const r=localStorage.getItem(SHARE_KEY);if(r)return shareDB(JSON.parse(r))}catch(e){}return shareDB({name:'Bozo Parlay',seasons:[]})}
let shareBusy=false;
async function refreshShare(loud){if(shareBusy)return;shareBusy=true;try{const r=await fetch('data.json?r='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);const j=await r.json();
    if(j.updatedAt!==DB.updatedAt){try{localStorage.setItem(SHARE_KEY,JSON.stringify(j))}catch(e){}const cur=season().id;DB=shareDB(j);const l=league();l.activeSeason=l.seasons.find(x=>x.id===cur)?cur:newestOf(l).id;S=season().data;ALLTIME=null;render();if(loud)toast('Updated with the latest results','good')}else if(loud)toast('Already up to date','good')}
  catch(e){if(!DB.updatedAt)document.getElementById('view').innerHTML=empty('Couldn\'t load the league','Check your connection and try again.');else if(loud)toast('Could not check for updates: '+e.message,'bad')}
  finally{shareBusy=false}}
"""
s=s[:a]+STUB+s[b:]
def sub(old,new):
    global s
    assert old in s, 'missing: '+old[:80]; s=s.replace(old,new,1)
sub("const SHARE_MODE=false;","const SHARE_MODE=true;")
sub("const KEY2='bozo-parlay-v2';","const KEY2='bozo-club-v1';")
sub("const KEY='bozo-parlay-v1';","const KEY='bozo-club-v0';")
s=re.sub(r"^const SEED_MARGINS=.*$","const SEED_MARGINS={};",s,flags=re.M)
sub("(async()=>{const joined=await joinFromUrl();if(!joined)pull();})();","refreshShare();document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshShare()});")
sub("<title>Bozo Parlay</title>","<title>Bozo Parlay Club</title>")
sub('<meta name="apple-mobile-web-app-title" content="Bozo Parlay">','<meta name="apple-mobile-web-app-title" content="Bozo Club">')
for bad in ['seedStags','OG25','STAGS24','MARGINS={"','seedOG','seedLeague2','SEED1=','Stags Bozo','Bozo University']:
    assert bad not in s, 'leaked: '+bad
open(os.path.join(OUT,'index.html'),'w').write(s)
js=re.search(r'<script>(.*)</script>',s,re.S).group(1);open('/tmp/club.js','w').write(js)
r=subprocess.run(['node','--check','/tmp/club.js'],capture_output=True,text=True)
if r.returncode:print(r.stderr[:600]);sys.exit(1)
sw=open(os.path.join(SRC,'sw.js')).read().replace("bozo-parlay-v4","bozo-club-v1").replace("k.startsWith('bozo-parlay-')","k.startsWith('bozo-club-')")
assert 'bozo-club-v1' in sw and "startsWith('bozo-club-')" in sw
open(os.path.join(OUT,'sw.js'),'w').write(sw)
m=json.load(open(os.path.join(SRC,'manifest.json')));m['name']='Bozo Parlay Club';m['short_name']='Bozo Club';m['description']='The Bozo Parlay league: every slip, every stat.'
json.dump(m,open(os.path.join(OUT,'manifest.json'),'w'),indent=2)
for f in ['icon.svg','icon-192.png','icon-512.png','apple-touch-icon.png']:shutil.copy(os.path.join(SRC,f),os.path.join(OUT,f))
print('built ->',OUT,len(s),'bytes')
