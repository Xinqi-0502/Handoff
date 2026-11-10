"""Operational scoring: SEP and COMMON use the same order choices and tie rule; compute exact schedules only for opened branches."""
from models import *
def reference(meta,c,w,mat,ctx,v,h,sep=True):
 starts={i:c['old'][items(c,i)[0]] for i in c['actors']};target=4;truck=EPOCH*SCALE//HZ+4*mat[w['T']]['T'+h[-1]][0];oldtotal=0
 for actor in c['actors']:
  rr=[];first=items(c,actor)[0];remaining=items(c,actor)[1:];deficit=max(0,sum(c['size'][j] for j in remaining)+target-CAP[actor])
  for seq in itertools.permutations(remaining):
   at=starts[actor];t=ctx[actor]['ready'];old=t;freed=0;last_site=at;last=t
   for j in seq:
    dest=c['old'][j];t+=3*mat[at][dest][0]+SERV;old+=t;at=dest
    if freed<deficit:freed+=c['size'][j];last=t;last_site=at
   if actor==v:
    new=max(last+3*mat[last_site][h][0],truck)+XFER+3*mat[h][w['i']][0]+SERV-EPOCH*SCALE//HZ
    rr.append((old,new))
   else:rr.append((old,0))
  if actor==v and not sep:oldtotal+=min(a+b for a,b in rr)
  else:oldtotal+=min(a for a,b in rr)+min(b for a,b in rr)
 return oldtotal
def evaluate(c,w,mat,ctx,v,h):
 # Enumerate feasible old orders and new pickup/delivery insertions; first old customer already committed.
 tt_truck=EPOCH*SCALE//HZ+4*mat[w['T']]['T'+h[-1]][0];full=0;paths={}
 for actor in c['actors']:
  previous=items(c,actor);old=previous[1:];choices=[]
  for seq in itertools.permutations(old+(('X','i') if v==actor else ())):
   at=c['old'][previous[0]];t=ctx[actor]['ready'];val=t;held=set(old)
   for j in seq:
    dest=h if j=='X' else (w['i'] if j=='i' else c['old'][j])
    t+=3*mat[at][dest][0];at=dest
    if j=='X':
     if sum(c['size'].get(a,4) for a in held)+4>CAP[actor]:break
     t=max(t,tt_truck)+XFER;held.add('i')
    else:
     if j not in held:break
     held.remove(j);t+=SERV;val+=t-(EPOCH*SCALE//HZ if j=='i' else 0)
   else:
    if not held:choices.append((val,seq))
  best=min(choices);full+=best[0];paths[actor]=list((previous[0],)+best[1])
 return full,paths
def dispatch(c,w,mat,ctx,arm,K):
 tick=time.perf_counter();bounds=sorted((reference(None,c,w,mat,ctx,v,h,arm=='SEP'),v,h) for v,h in itertools.product(c['actors'],('HW','HE')))
 best=math.inf;choice='~';opened=[];selected=None;stop=None
 for lb,v,h in bounds:
  if len(opened)>=K:break
  if lb>best:stop=[v+h[-1],lb,best];break
  score,paths=evaluate(c,w,mat,ctx,v,h);key=v+h[-1];opened.append(key)
  if (score,key)<(best,choice):
   best,choice=score,key;selected={'receiver':v,'hub':h,'route':paths}
 elapsed=time.perf_counter()-tick
 if elapsed>1:raise TimeoutError('1s dispatch budget exceeded')
 return {'choice':choice,'score':best,'plan':selected,'opened':opened,'stop':stop,'rank':bounds,'seconds':elapsed}
