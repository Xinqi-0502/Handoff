from models import *
import gzip
import xml.etree.ElementTree as ET
def audit(folder):
 cfg=read(folder/'INPUT.json');r=read(folder/'RESULT.json');w=cfg['wave'];p=cfg['plan'];c=cfg['c'];v=p['receiver'];h=p['hub']
 with gzip.open(folder/'trace.jsonl.gz','rt') as f:frame=[json.loads(z) for z in f]
 def stopped(t,v,s):
  a=frame[t-1]['vehicles'].get(v);return bool(a and a[0]==SITES[s][0] and abs(a[1]-SITES[s][1])<1.6 and a[3]&1 and a[2]==0)
 assert all(r['tick']==j+1 for j,r in enumerate(frame));window={}
 for actor,seq in list(p['route'].items())+[('T',['X'])]:
  tick=1
  for a in seq:
   site=('T'+h[-1] if actor=='T' else h) if a=='X' else (w['i'] if a=='i' else c['old'][a])
   while tick<=len(frame) and not stopped(tick,actor,site):tick+=1
   assert tick<=len(frame),(actor,a,site)
   first=tick
   while tick<=len(frame) and stopped(tick,actor,site):tick+=1
   window[actor,a]=(first,tick-1)
 begin=max(window['T','X'][0],window[v,'X'][0]);end=begin+2*HZ
 assert window['T','X'][1]>=end and window[v,'X'][1]>=end
 for t in range(begin,end+1):
  m=frame[t-1]['vehicles'];assert math.dist(m['T'][4:],m[v][4:])<=12
 events=[];complete={};held={a:set(items(c,a)) for a in c['actors']};held['T']={'i'}
 for actor,seq in p['route'].items():
  assert seq[0]==items(c,actor)[0] and window[actor,seq[0]][0]>EPOCH
  for a in seq:
   b,z=window[actor,a];ti=end if a=='X' else b+SERV//(SCALE//HZ)
   assert b<=ti<=z;events.append((ti,actor,a))
 for t,actor,a in sorted(events):
  if a=='X':
   assert t>EPOCH and held['T']=={'i'} and sum(c['size'][x] for x in held[actor])+4<=CAP[actor]
   held['T'].clear();held[actor].add('i')
  else:
   assert a in held[actor] and a not in complete;held[actor].remove(a);complete[a]=t
 assert complete==r['completed'] and not any(held.values());assert all('T' not in rec['vehicles'] for rec in frame[:EPOCH])
 assert len(ET.parse(folder/'trips.xml').findall('tripinfo'))==len(c['actors'])+2 and not ET.parse(folder/'collisions.xml').findall('collision')
 total=sum(complete.values())-EPOCH
 metrics=dict(all_pass=True,J_s=total/HZ,old_s=(sum(complete.values())-complete['i'])/HZ,new_s=(complete['i']-EPOCH)/HZ,wait_s=(begin-window['T','X'][0])/HZ,truck_park_s=window['T','X'][0]/HZ,handoff_s=begin/HZ,customers={a:t/HZ for a,t in complete.items()},first_fixed={a:window[a,p['route'][a][0]][0]/HZ for a in p['route']},wave_old=0,wave_new=EPOCH/HZ,prefix=r['prefix'],trace_hash=r['trace_hash'])
 put(folder/'AUDIT.json',metrics);return metrics
