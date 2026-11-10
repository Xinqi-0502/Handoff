import gzip
import json
from pathlib import Path
from models import SITES

class StopController:
    def __init__(self,out,corrected):
        self.corrected=corrected
        self.log=gzip.open(out/'stop_queue.jsonl.gz','xt',encoding='utf8')
        self.paths={}
        self.registrations={}
        self.stops={}
        self.records={}
    def record(self,event,**data):
        self.log.write(json.dumps(dict(event=event,**data),separators=(',',':'))+'\n')
    def close(self):
        self.log.close()
    def install(self,conn,v,site,acts,c,w,o,mat,tick):
        at=site;path=[SITES[site][0]];targets=[]
        for action in acts:
            dest=o['hub'] if action=='X' else w['i'] if action=='i' else c['old'][action]
            edges=mat[at][dest][1]
            assert edges[0]==path[-1] and edges[-1]==SITES[dest][0]
            path+=edges[1:]
            targets.append((action,dest,len(path)-1))
            at=dest
        before_idx=conn.vehicle.getRouteIndex(v)
        before_route=list(conn.vehicle.getRoute(v))
        conn.vehicle.setRoute(v,path)
        after_idx=conn.vehicle.getRouteIndex(v)
        native=list(conn.vehicle.getRoute(v))
        assert native[after_idx:]==path, (native,after_idx,path)
        assert native[:after_idx]==before_route[:before_idx]
        self.paths[v]=native
        self.stops[v]=dict((i+1,(act,s,after_idx+idx)) for i,(act,s,idx) in enumerate(targets))
        self.record('install',tick=tick,v=v,route=native,route_idx=after_idx,targets=self.stops[v])
        if not self.corrected:
            for action,dest,idx in targets:
                edge,pos=SITES[dest]
                conn.vehicle.setStop(v,edge,pos=pos,laneIndex=0,duration=10000,flags=conn.vehicle.STOP_PARKING)
        self.record('initial_queue',tick=tick,v=v,queue=self.queue(conn,v))
    @staticmethod
    def queue(conn,v):
        return [(x.lane,x.endPos,x.stopFlags,x.arrival) for x in conn.vehicle.getStops(v)]
    def new_step(self,conn,vehicles,idx,acts,tick,site_func):
        for v in vehicles:
            if v=='T' or v not in self.paths:continue
            i=idx[v]
            if i>=len(acts[v]):continue
            road=conn.vehicle.getRoadID(v);rid=conn.vehicle.getRouteIndex(v)
            action,dest,target=self.stops[v][i]
            assert action==acts[v][i]
            edge,pos=SITES[dest]
            queue=self.queue(conn,v)
            stopstate=conn.vehicle.getStopState(v)
            self.record('snapshot',tick=tick,v=v,i=i,act=action,dest=dest,road=road,rid=rid,target=target,stop=stopstate,queue=queue)
            if self.corrected and stopstate&1:
                assert road==edge and rid==target and abs(conn.vehicle.getLanePosition(v)-pos)<1.6,(tick,v,road,rid,dest,target)
    def arm_next(self,conn,vehicles,idx,acts,tick):
        if not self.corrected:return
        for v in vehicles:
            if v=='T' or v not in self.paths:continue
            i=idx[v]
            if i>=len(acts[v]) or self.registrations.get(v)==i:continue
            action,dest,target=self.stops[v][i]
            edge,pos=SITES[dest]
            route=self.paths[v]
            assert route==list(conn.vehicle.getRoute(v)) and route[target]==edge
            rid=conn.vehicle.getRouteIndex(v)
            assert rid<=target,(tick,v,action,rid,target)
            # A setStop must bind to exactly this occurrence. On loops do not permit it to attach to a preceding visit.
            if edge in route[rid:target]:continue
            assert not self.queue(conn,v),(tick,v,'extra stops',self.queue(conn,v))
            conn.vehicle.setStop(v,edge,pos=pos,laneIndex=0,duration=10000,flags=conn.vehicle.STOP_PARKING)
            q=self.queue(conn,v)
            assert len(q)==1 and q[0][0]==edge+'_0' and abs(q[0][1]-pos)<1e-6,q
            self.registrations[v]=i
            self.record('arm',tick=tick,v=v,i=i,dest=dest,rid=rid,target=target,queue=q)
