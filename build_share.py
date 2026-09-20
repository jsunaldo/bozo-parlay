#!/usr/bin/env python3
"""Build a league's own app (a "club" site) from this app.

Strips every built-in seed (all leagues' history) out of the page, flips SHARE_MODE on, and bakes in the one
league it syncs live from the worker. Every club app lives on the same origin (jsunaldo.github.io), so each one
gets its own storage and cache prefix — two clubs must never share one.

  Bozo Parlay club (defaults):
    python3 build_share.py --league o77nefhml4 --key <memberKey>
  Bozo University:
    python3 build_share.py --league <id> --key <memberKey> --out ../bozo-university --prefix bozo-uni \\
      --title "Bozo University" --short "Bozo U" --name "Bozo University" \\
      --site https://jsunaldo.github.io/bozo-university/ --icons icons/university

Rebuild and push the club repo whenever index.html changes.
"""
import os, re, shutil, json, subprocess, sys, argparse

ap = argparse.ArgumentParser()
ap.add_argument('--league', required=True, help='sync league id')
ap.add_argument('--key', required=True, help='member key')
ap.add_argument('--url', default='https://bozo-sync.jsunaldo.workers.dev')
ap.add_argument('--out')
ap.add_argument('--prefix', default='bozo-club', help='storage + cache prefix, unique per club app')
ap.add_argument('--title', default='Bozo Parlay Club')
ap.add_argument('--short', default='Bozo Club', help='home-screen name')
ap.add_argument('--name', default='Bozo Parlay', help='league name shown before the first sync')
ap.add_argument('--desc', default='The Bozo Parlay league: every slip, every stat.')
ap.add_argument('--site', default='https://jsunaldo.github.io/bozo-parlay-club/', help="this app's own URL")
ap.add_argument('--icons', default='icons/parlay', help='folder with icon.svg, icon-192.png, icon-512.png, apple-touch-icon.png')
A = ap.parse_args()

SRC = os.path.dirname(os.path.abspath(__file__))
OUT = A.out or os.path.join(os.path.dirname(SRC), 'bozo-parlay-club')
if not os.path.isabs(OUT): OUT = os.path.normpath(os.path.join(SRC, OUT))
ICONS = os.path.join(SRC, A.icons) if A.icons else SRC
P = A.prefix
assert re.fullmatch(r'[a-z][a-z0-9-]*', P) and not P.startswith('bozo-parlay'), 'prefix must be unique and not start with bozo-parlay (the main app)'
os.makedirs(OUT, exist_ok=True)
# Never build one league into another league's app: members' phones would load the wrong league and lose their saved name.
_old = os.path.join(OUT, 'index.html')
if os.path.exists(_old):
    _m = re.search(r"SHARE_LEAGUE=\{id:'([A-Za-z0-9]+)'", open(_old, encoding='utf-8').read())
    _pm = re.search(r"const KEY2='([a-z0-9-]+)-v1'", open(_old, encoding='utf-8').read())
    if _m and _m.group(1) != A.league: sys.exit(f"STOPPED, nothing was written: {OUT} is the app for league {_m.group(1)}, but you asked for league {A.league}. Check --league and --out (the Bozo University build needs its full flag list).")
    if _pm and _pm.group(1) != P: sys.exit(f"STOPPED, nothing was written: {OUT} was built with --prefix {_pm.group(1)}, not {P}. A different prefix would sign every member out. Check the flags.")

s = open(os.path.join(SRC, 'index.html')).read()
a = s.index('/*@@SEEDS-START@@*/'); b = s.index('/*@@SEEDS-END@@*/')
STUB = r"""/* league app: no seeds; one league, live from the sync server, this phone claims one name */
const SHARE_LEAGUE={id:'__LEAGUE_ID__',key:'__MEMBER_KEY__',url:'__SYNC_URL__'};
function migrateDB(d){return d}
function isOwner(){return false}function setOwner(){}   // a club device is never the commissioner's
function loadDB(){let d=null;try{const r=localStorage.getItem(KEY2);if(r)d=JSON.parse(r)}catch(e){}
  if(!d||!Array.isArray(d.leagues))d={leagues:[],active:null,seedV:99};
  d.leagues.forEach(l=>{l.seasons=(l.seasons||[]).map(x=>({...x,data:migrate(x.data||fresh())}));if(!l.seasons.length)l.seasons=[{id:'s0',name:'',data:fresh()}];if(!l.seasons.find(x=>x.id===l.activeSeason))l.activeSeason=l.seasons[0].id});
  let l=d.leagues.find(x=>x.sync&&x.sync.id===SHARE_LEAGUE.id);
  if(!l){const dd=fresh();l={id:'cloud-'+SHARE_LEAGUE.id,name:'__LEAGUE_NAME__',seasons:[{id:'s0',name:'',data:dd}],activeSeason:'s0',sync:{url:SHARE_LEAGUE.url,id:SHARE_LEAGUE.id,key:SHARE_LEAGUE.key,role:'member',rev:0}}}
  l.sync.url=SHARE_LEAGUE.url;l.sync.key=SHARE_LEAGUE.key;d.leagues=[l];d.active=l.id;return d}
"""
s = s[:a] + STUB + s[b:]

def sub(old, new):
    global s
    assert old in s, 'missing: ' + old[:80]; s = s.replace(old, new, 1)

sub("const SHARE_MODE=false;", "const SHARE_MODE=true;")
sub("const KEY2='bozo-parlay-v2';", f"const KEY2='{P}-v1';")
sub("const KEY='bozo-parlay-v1';", f"const KEY='{P}-v0';")
sub("const CACHE_PREFIX='bozo-parlay-';", f"const CACHE_PREFIX='{P}-';")
# only this league's own app link ships in this build — never the other leagues'
s, n = re.subn(r"^const SHARE_SITES=\{.*\};$", lambda m: "const SHARE_SITES={self:" + json.dumps({'url': A.site, 'sync': A.league, 'app': A.title, 'home': A.short}) + "};", s, flags=re.M)
assert n == 1, 'SHARE_SITES line not found'
s = re.sub(r"^const SEED_MARGINS=.*$", "const SEED_MARGINS={};", s, flags=re.M)
s, n = re.subn(r"^const LEAGUE_LOGOS=\{.*\};$", "const LEAGUE_LOGOS={};", s, flags=re.M); assert n == 1, 'LEAGUE_LOGOS line not found'   # a club app only ever shows its own icon
sub("(async()=>{const joined=(await adoptFromUrl())||(await joinFromUrl());if(!joined)pull();})();", "pull(league(),false);")
s = s.replace("__LEAGUE_ID__", A.league).replace("__MEMBER_KEY__", A.key).replace("__SYNC_URL__", A.url).replace("__LEAGUE_NAME__", A.name.replace("'", "\\'"))
sub("<title>Bozo Commish</title>", f"<title>{A.title}</title>")
sub('<meta name="apple-mobile-web-app-title" content="Bozo Commish">', f'<meta name="apple-mobile-web-app-title" content="{A.short}">')

# nothing from the other leagues may ship: no seeds, no other league's app link
for bad in ['seedStags', 'OG25', 'STAGS24', 'MARGINS={"', 'seedOG', 'seedLeague2', 'SEED1=', 'Stags Bozo', '__BU_SYNC_ID__']:
    assert bad not in s, 'leaked: ' + bad
for site in ['https://jsunaldo.github.io/bozo-parlay-club/', 'https://jsunaldo.github.io/bozo-university/']:
    if site != A.site: assert site not in s, 'leaked another app link: ' + site
other_names = {'Bozo University', 'Bozo Parlay Club'} - {A.title, A.name}
for nm in other_names | {'Stags Bozo Parlay'}:
    assert nm.lower() not in s.lower(), 'leaked another league name: ' + nm

open(os.path.join(OUT, 'index.html'), 'w').write(s)
js = re.search(r'<script>(.*)</script>', s, re.S).group(1); open('/tmp/club.js', 'w').write(js)
r = subprocess.run(['node', '--check', '/tmp/club.js'], capture_output=True, text=True)
if r.returncode: print(r.stderr[:600]); sys.exit(1)

_sw = open(os.path.join(SRC, 'sw.js')).read()
_cv = re.search(r"CACHE='bozo-parlay-(v\d+)'", _sw).group(1)   # a club's offline copy rotates whenever the main app's does
sw = _sw.replace('bozo-parlay-' + _cv, f'{P}-{_cv}').replace("k.startsWith('bozo-parlay-')", f"k.startsWith('{P}-')")
assert f'{P}-{_cv}' in sw and f"startsWith('{P}-')" in sw
open(os.path.join(OUT, 'sw.js'), 'w').write(sw)

m = json.load(open(os.path.join(SRC, 'manifest.json')))
m['name'] = A.title; m['short_name'] = A.short; m['description'] = A.desc
json.dump(m, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=2)
for f in ['icon.svg', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png']:
    shutil.copy(os.path.join(ICONS, f), os.path.join(OUT, f))
print('built ->', OUT, len(s), 'bytes')

# every device checks this to know a newer build is out (the Commish reads the copy next to its own index.html)
ver = re.search(r"APP_VERSION='([^']+)'", s).group(1)
for d in (OUT, SRC): json.dump({'v': ver}, open(os.path.join(d, 'version.json'), 'w'))
