#!/usr/bin/env python3
"""Build the read-only league site (../bozo-parlay-club) from this app.
Strips every built-in seed (all leagues' history) out of the page, flips SHARE_MODE on,
and bakes in the one league it syncs live from the worker (--league <id> --key <memberKey> [--url]).
Rebuild and push the club repo whenever index.html changes."""
import os,re,shutil,json,subprocess,sys,argparse
ap=argparse.ArgumentParser();ap.add_argument('--league',required=True,help='sync league id');ap.add_argument('--key',required=True,help='member key');ap.add_argument('--url',default='https://bozo-sync.jsunaldo.workers.dev');ap.add_argument('--out');A=ap.parse_args()
SRC=os.path.dirname(os.path.abspath(__file__)); OUT=A.out or os.path.join(os.path.dirname(SRC),'bozo-parlay-club')
os.makedirs(OUT,exist_ok=True)
s=open(os.path.join(SRC,'index.html')).read()
a=s.index('/*@@SEEDS-START@@*/'); b=s.index('/*@@SEEDS-END@@*/')
STUB=r"""/* league site: no seeds; one league, live from the sync server, this phone claims one name */
const SHARE_LEAGUE={id:'__LEAGUE_ID__',key:'__MEMBER_KEY__',url:'__SYNC_URL__'};
function migrateDB(d){return d}
function loadDB(){let d=null;try{const r=localStorage.getItem(KEY2);if(r)d=JSON.parse(r)}catch(e){}
  if(!d||!Array.isArray(d.leagues))d={leagues:[],active:null,seedV:99};
  d.leagues.forEach(l=>{l.seasons=(l.seasons||[]).map(x=>({...x,data:migrate(x.data||fresh())}))});
  let l=d.leagues.find(x=>x.sync&&x.sync.id===SHARE_LEAGUE.id);
  if(!l){const dd=fresh();l={id:'cloud-'+SHARE_LEAGUE.id,name:'Bozo Parlay',seasons:[{id:'s0',name:'',data:dd}],activeSeason:'s0',sync:{url:SHARE_LEAGUE.url,id:SHARE_LEAGUE.id,key:SHARE_LEAGUE.key,role:'member',rev:0}}}
  l.sync.url=SHARE_LEAGUE.url;l.sync.key=SHARE_LEAGUE.key;d.leagues=[l];d.active=l.id;return d}
"""
s=s[:a]+STUB+s[b:]
def sub(old,new):
    global s
    assert old in s, 'missing: '+old[:80]; s=s.replace(old,new,1)
sub("const SHARE_MODE=false;","const SHARE_MODE=true;")
sub("const KEY2='bozo-parlay-v2';","const KEY2='bozo-club-v1';")
sub("const KEY='bozo-parlay-v1';","const KEY='bozo-club-v0';")
s=re.sub(r"^const SEED_MARGINS=.*$","const SEED_MARGINS={};",s,flags=re.M)
sub("(async()=>{const joined=(await adoptFromUrl())||(await joinFromUrl());if(!joined)pull();})();","pull(league(),false);")
s=s.replace("__LEAGUE_ID__",A.league).replace("__MEMBER_KEY__",A.key).replace("__SYNC_URL__",A.url)
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
