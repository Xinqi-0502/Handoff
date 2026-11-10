import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
HERE=Path(__file__).resolve().parent
V415=HERE.parent/'fleet_study_v415_common_prefix_witness_20261104'
FIX=HERE.parent/'fleet_study_v415b_executor_audit_20261104'
sys.path.insert(0,str(V415))
import witness
from witness import CAP,SCALE,MATRIX,fh,digest,put,read,items,parent,reveal
sys.path.insert(0,str(FIX))
from models import HZ,EPOCH,SERV,SITES,XFER
from reused_road_sumo import discover_runtime
from schedule import StopController

NET=HERE.parent/'fleet_study_v419_crosswalk_audit_20261104'/'turn_network_v2'
TURN_DATA=read(HERE/'turn2_legs.json')
MATRIX=TURN_DATA['matrix']
witness.MATRIX=MATRIX
witness.prev.MATRIX=MATRIX
E=EPOCH/HZ
SEEDS=tuple(range(419411,419415))
ARMS=('SEP_SIGNAL','COMMON_SIGNAL','SEP_VISIBLE','COMMON_VISIBLE')
POSITIONS=(36,34,30,27,23,19,15,11,7,3)
class Crossing(witness.v410.PublicSignal):
    def __init__(self,offset,ped,visible):
        tree=ET.parse(NET/f'cycle_{offset}.net.xml').getroot()
        self.length={e.get('id'):round(float(e.find('lane').get('length'))*100) for e in tree.findall('edge')}
        prog=tree.find("tlLogic[@id='C']")
        self.offset=float(prog.get('offset'))
        self.phases=[(float(p.get('duration')),p.get('state')) for p in prog.findall('phase')]
        self.turns={(c.get('from'),c.get('to')):int(c.get('linkIndex')) for c in tree.findall('connection') if c.get('tl')=='C'}
        self.right_links={int(c.get('linkIndex')) for c in tree.findall('connection') if c.get('tl')=='C' and c.get('from')=='WC' and c.get('to')=='CE' and c.get('dir')=='r'}
        self.pedestrian_link=next(i for (a,b),i in self.turns.items() if b==':C_c0')
        assert self.right_links and self.turns.get(('WC','CE')) in self.right_links
        self.windows=[]
        self.visible=[]
        self.applied=[]
        from math import hypot
        def geom(edge):
            node=tree.find(f"edge[@id='{edge}']/lane")
            return [tuple(map(float,pt.split(','))) for pt in node.get('shape').split()]
        def along(x,y,points):
            best=(float('inf'),0.);acc=0.
            for a,b in zip(points,points[1:]):
                dx=b[0]-a[0];dy=b[1]-a[1];l=hypot(dx,dy)
                f=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/max(l*l,1.e-12)))
                pair=(hypot(x-a[0]-f*dx,y-a[1]-f*dy),acc+f*l)
                best=min(best,pair);acc+=l
            return best[1],acc
        north_path=geom('NC'); crossing=geom(':C_c0')
        near=north_path[-1]
        if hypot(near[0]-crossing[-1][0],near[1]-crossing[-1][1])<hypot(near[0]-crossing[0][0],near[1]-crossing[0][1]):crossing.reverse()
        lane_table={lane.get('id'):lane for e in tree.findall('edge') for lane in e.findall('lane')}
        def path_for(link):
            conn=next(c for c in tree.findall('connection') if c.get('tl')=='C' and int(c.get('linkIndex'))==link)
            via=conn.get('via'); path=[]
            while via:
                sh=[tuple(map(float,p.split(','))) for p in lane_table[via].get('shape').split()]
                path+=sh[1:] if path and path[-1]==sh[0] else sh
                edge,idx=via.rsplit('_',1)
                nexts=[c for c in tree.findall('connection') if c.get('from')==edge and c.get('fromLane')==idx and c.get('to')==conn.get('to')]
                assert len(nexts)==1
                via=nexts[0].get('via')
            return path
        def conflict_dist(a,b,curve,step):
            def cross(p,q):return p[0]*q[1]-p[1]*q[0]
            u=(b[0]-a[0],b[1]-a[1]);travel=0
            for c,d in zip(curve,curve[1:]):
                v=(d[0]-c[0],d[1]-c[1]);den=cross(u,v)
                if abs(den)>1e-12:
                    delta=(c[0]-a[0],c[1]-a[1]); pu=cross(delta,v)/den;pv=cross(delta,u)/den
                    if 0<=pu<=1 and 0<=pv<=1:return step+pu*hypot(*u),travel+pv*hypot(*v)
                travel+=hypot(*v)
            return None
        self.geometry={}
        for link in self.right_links:
            curve=path_for(link);step=0;found=None
            for a,b in zip(crossing,crossing[1:]):
                found=conflict_dist(a,b,curve,step)
                if found:break
                step+=hypot(b[0]-a[0],b[1]-a[1])
            assert found is not None,(link,crossing,curve)
            self.geometry[link]=found
        for identifier,(edge,x,y) in ped.items():
            if edge not in ('NC',':C_w0',':C_w1',':C_c0'):continue
            if edge==':C_c0':
                where,total=along(x,y,crossing); enter=E-where/1.2
            else:
                if edge=='NC':
                    where,total=along(x,y,north_path);distance=total-where+hypot(near[0]-crossing[0][0],near[1]-crossing[0][1])
                else:
                    distance=hypot(x-crossing[0][0],y-crossing[0][1])
                    if hypot(x-crossing[-1][0],y-crossing[-1][1])<distance:continue
                if distance>46:continue
                arrival=E+distance/1.2;enter=arrival+super().waiting(arrival,self.pedestrian_link)
            self.visible.append(identifier)
            for link,(ped_run,veh_run) in self.geometry.items():
                # Crossing and turn centerlines intersect; 1.6m is half a local lane width and a finite prediction band.
                low=max(E,enter+max(0,ped_run-1.6)/1.2);high=enter+(ped_run+1.6)/1.2
                if high>low:self.windows.append((round(low,8),round(high,8),identifier,link))
        self.visible.sort();self.windows.sort();self.use=bool(visible)
    def turn_wait(self,t,link,speed):
        gate=super().waiting(t,link); entry=t+gate
        if not self.use or link not in self.right_links or self.signal(entry+1e-7)[link]!='g':return gate
        # Before knowing lane choice, use the same advertised costs for both lane options, conservative max across possible lanes.
        extra=0.
        for li,(ped_run,car_run) in self.geometry.items():
            at=entry+car_run/speed; initial=at
            for _ in range(len(self.windows)+1):
                ends=[end for start,end,p,j in self.windows if j==li and start-1.e-7<=at<end-1.e-7]
                if not ends:break
                at=max(ends)
            extra=max(extra,at-initial)
        if extra>1e-7:self.applied.append((round(t,6),round(entry,6),round(extra,6),link))
        # Once the stopline has been crossed, do not reacquire a green to leave the interior.
        return gate+extra
    def traverse(self,start,route,start_cm,total_cm,speed,on,passages):
        position=0; clock=start;advanced=0
        for idx,(a,b) in enumerate(zip(route,route[1:])):
            position+=self.length[a]-(start_cm if idx==0 else 0)
            if (link:=self.turns.get((a,b))) is not None:
                assert 0<=position<=total_cm+1
                clock+=(position-advanced)/100/speed
                delay=self.turn_wait(clock,link,speed) if on else 0
                passages.append([a,b,clock,delay]);clock+=delay;advanced=position
            position+=TURN_DATA['connectors'][a+'>'+b]
        return clock+(total_cm-advanced)/100/speed
    def forecast(self,case,ctx,wave,mat,plan,on=True):
        visits=[];h=plan['hub'];truck=self.leg(E,wave['T'],'T'+h[-1],6,mat,on,visits)
        done={};wait=None
        for v,seq in plan['route'].items():
            first=seq[0];done[first]=E; t=E; at=case['old'][first]
            for j in seq[1:]:
                site=h if j=='X' else wave['i'] if j=='i' else case['old'][j]
                t=self.leg(t,at,site,8,mat,on,visits)
                if j=='X':
                    wait=max(0,t-truck);t=max(t,truck)+XFER/SCALE
                else:
                    t+=SERV/SCALE;done[j]=t
                at=site
        return dict(J=sum(done.values())-E,old=sum(t for j,t in done.items() if j!='i'),new=done['i']-E,
            truck_wait=wait,crossings=visits)
def first_completion(sig,state,phase):
    assert state['ready']==round(E*SCALE)
    return E
witness.prev.first_completion=first_completion
def select(c,w,ctx,ped,offset,arm):
    sig=Crossing(offset,ped,arm.endswith('VISIBLE'))
    result=witness.decide(c,w,ctx,sig,'COMMON_WIT' if arm.startswith('COMMON') else 'EXTREME_SEP')
    # After choice, expose which post-first-stop crossings had an actual forecast interference opportunity.
    sig.applied.clear()
    evidence=sig.forecast(c,ctx,w,MATRIX,result['plan'])
    assert abs(evidence['J']-next(a['pred']['J'] for a in result['alternatives'] if a['key']==result['choice']))<1e-6
    result.update(arm=arm,visible=sig.visible,predicted_windows=sig.windows,selected_crossings=evidence['crossings'],active_ped=sorted(set(sig.applied)))
    return result
