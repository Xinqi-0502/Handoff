from pathlib import Path
import hashlib,json,random,itertools,math,time
ROOT=Path(__file__).resolve().parents[1];NET=ROOT/'network';HZ=5;EPOCH=30;SCALE=2400;SERV=4*SCALE;XFER=2*SCALE
SEEDS=[408411,408412,408413,408414];SITES={'HW':('WC',22),'HE':('EC',22),'TW':('WC',30),'TE':('EC',30),'tW':('WC',7),'tE':('EC',7),'ME':('CE',59),'MW':('CW',59)}
for side,br,tag,edge,pos in itertools.product('WE','UD',[],[],[]):pass
for side in 'WE':
 for br in 'UD':
  for tag,edge,pos in [('u','0',28),('v','0',73),('x','1',27)]:SITES[side+br+tag]=(side+br+edge,pos)
for j,v in enumerate('ABC'):
 for side in 'WE':
  SITES[v+'in'+side]=(('WC' if side=='W' else 'EC'),34+12*j)
  SITES[v+'out'+side]=(('CW' if side=='W' else 'CE'),83-12*j)
CARGO={'A':(1,2,2),'B':(1,2,1),'C':(1,2,1)};CAP={'A':5,'B':5,'C':4}
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(p,data):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
def fh(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def parent(seed,n):
 rng=random.Random(seed);pool=[s+b+t for s in 'WE' for b in 'UD' for t in 'uvx'];dest=rng.sample(pool,9);old={};size={};start={}
 for j,v in enumerate('ABC'):
  start[v]=v+'in'+rng.choice(['W','E'])
  for k,w in enumerate(CARGO[v]):o=v.lower()+str(k);old[o]=dest[3*j+k];size[o]=w
 actors=list('ABC')[:n];return {'seed':seed,'actors':actors,'start':{v:start[v] for v in actors},'old':{o:x for o,x in old.items() if o[0].upper() in actors},'size':{o:x for o,x in size.items() if o[0].upper() in actors}}
def reveal(seed):
 rng=random.Random(810000+seed);return {'i':rng.choice(['MW','ME']),'T':rng.choice(['tW','tE']),'weight':4,'release_tick':EPOCH}
def items(c,v):return tuple(o for o in c['old'] if o[0].upper()==v)
def costs(c,mat,ctx,wave,x,h):
 # All clocks are absolute; SUM latency counts every old job and new flow time relative to the actual release.
 base={};rows={};exact={};bestseq={}
 truck=EPOCH*SCALE//HZ+mat[wave['T']]['T'+h[-1]][0]*4
 for v in c['actors']:
  orders=items(c,v);start=c['old'][orders[0]];t0=ctx[v]['ready'];routes=[];full=[]
  target=wave['weight'];remain=orders[1:];d=max(0,sum(c['size'][j] for j in remain)+target-CAP[v])
  for seq in itertools.permutations(remain):
   a=start;tt=t0;old=t0;prefix=t0;prefix_site=start;released=0
   for j in seq:
    b=c['old'][j];tt+=3*mat[a][b][0]+SERV;old+=tt;a=b
    if released<d:released+=c['size'][j];prefix=tt;prefix_site=b
   new=max(truck,prefix+3*mat[prefix_site][h][0])+XFER+3*mat[h][wave['i']][0]+SERV-EPOCH*SCALE//HZ
   routes.append((old,new,seq))
  base[v]=min(r[0] for r in routes);rows[v]=routes
  events=remain+(('X','i') if x==v else ())
  for seq in itertools.permutations(events):
   owned=set(remain);a=start;tt=t0;val=t0;ok=True
   for j in seq:
    if j=='X':
     if sum(c['size'][o] for o in owned)+target>CAP[v]:ok=False;break
     tt=max(tt+3*mat[a][h][0],truck)+XFER;owned.add('i');a=h
    else:
     if j not in owned:ok=False;break
     b=wave['i'] if j=='i' else c['old'][j];tt+=3*mat[a][b][0]+SERV;val+=tt-(EPOCH*SCALE//HZ if j=='i' else 0);owned.remove(j);a=b
   if ok:full.append((val,seq))
  exact[v],bestseq[v]=min(full)
 sep=sum(base.values())+min(r[1] for r in rows[x])
 common=sum(base[v] for v in base if v!=x)+min(row[0]+row[1] for row in rows[x])
 truth=sum(exact.values());assert sep<=common<=truth
 return {'receiver':x,'hub':h,'SEP':sep,'COMMON':common,'truth':truth,'route':{v:list((items(c,v)[0],)+bestseq[v]) for v in c['actors']},'old_min':base,'order_profiles':rows[x]}
def pick(vals,arm,k):
 inc=math.inf;chosen=None;opened=[];counter=0;stops=[]
 for key,o in sorted(vals.items(),key=lambda z:(z[1][arm],z[0])):
  if len(opened)==k:break
  if o[arm]>inc:
   stops.append((key,inc,o[arm]))
   if arm=='COMMON' and o['SEP']<=inc<o['COMMON']:counter+=1
   break
  opened.append(key)
  if (o['truth'],key)<(inc,chosen or '~'):inc=o['truth'];chosen=key
 return {'choice':chosen,'opened':opened,'incumbent':inc,'frontier_cutoff':stops,'common_only_first_cutoff':counter}
