from model_turn2 import *
from models import *
from model_turn2 import NET, POSITIONS, MATRIX
from reused_road_sumo import discover_runtime
from dispatch import dispatch
import xml.etree.ElementTree as ET
import gzip,traceback
from schedule import StopController
def scene(c,path,people,mat):
 xml=ET.Element('routes')
 for name,kind,l,speed,ac,de in [('small','delivery',2,8,2,4.5),('truck','delivery',8,6,1.5,3),('traffic','passenger',4,10,2,4.5)]:
  ET.SubElement(xml,'vType',id=name,vClass=kind,length=str(l),maxSpeed=str(speed),accel=str(ac),decel=str(de),sigma='0',speedFactor='1',speedDev='0',tau='1',emergencyDecel='9')
 ET.SubElement(xml,'vType',id='walker',vClass='pedestrian',maxSpeed='1.2',speedFactor='1',speedDev='0')
 if c['slow']:
  ET.SubElement(xml,'vType',id='slow',vClass='passenger',length='4',maxSpeed='1.2',accel='2.6',decel='4.5',sigma='0',speedFactor='1',speedDev='0',tau='1',lcStrategic='0',lcCooperative='0',lcSpeedGain='0',lcKeepRight='0')
  for n,pos in enumerate((55,67)):
   a=ET.SubElement(xml,'vehicle',id='slow'+str(n),type='slow',depart='0',departPos=str(pos),departLane='0',departSpeed='1.2')
   ET.SubElement(a,'route',edges='WC CE')
 for v in c['actors']:
  dest=c['old'][items(c,v)[0]];at=dest
  a=ET.SubElement(xml,'vehicle',id=v,type='small',depart='0',departPos=str(SITES[at][1]),departLane='0',departSpeed='0')
  ET.SubElement(a,'route',edges=SITES[dest][0])
  ET.SubElement(a,'stop',lane=SITES[dest][0]+'_0',endPos=str(SITES[dest][1]),duration='10000',parking='true')
 a=ET.SubElement(xml,'vehicle',id='bg',type='traffic',depart='0',departPos='40',departLane='0',departSpeed='8');ET.SubElement(a,'route',edges='WC CE')
 if people:
  for i in range(10):
   p=ET.SubElement(xml,'person',id='ped'+str(i),type='walker',depart=str(i*.4),departPos=str(POSITIONS[i]))
   ET.SubElement(p,'walk',edges='NC CS',arrivalPos='2')
 ET.indent(xml);ET.ElementTree(xml).write(path,encoding='utf-8',xml_declaration=True)
def hit(row,site):
 e,p=SITES[site];return row is not None and row[0]==e and abs(row[1]-p)<1.6 and bool(row[3]&1) and row[2]==0
def start_context(c,conn,frame,lengths):
 ctx={}
 for v in c['actors']:
  work=c['old'][items(c,v)[0]];target,ep=SITES[work];route=list(conn.vehicle.getRoute(v));idx=conn.vehicle.getRouteIndex(v);at=conn.vehicle.getRoadID(v);pos=conn.vehicle.getLanePosition(v);assert route[-1]==target and idx>=0
  if at in lengths:
   remaining=(100*ep-round(pos*100)) if idx==len(route)-1 else lengths[at]-round(pos*100)+sum(lengths[e] for e in route[idx+1:-1])+100*ep
  else:
   remaining=sum(lengths[e] for e in route[idx+1:-1])+100*ep
  assert remaining>=0 and not hit(frame['vehicles'][v],work),(v,remaining,at,work)
  ctx[v]={'ready':EPOCH*SCALE//HZ+remaining*3+SERV,'remaining_cm':remaining,'edge':at,'pos_m':pos,'speed':conn.vehicle.getSpeed(v),'native_route':route,'route_index':idx,'committed':work}
 assert any(v['speed']>0 for v in ctx.values())
 return ctx
def install_suffix(conn,v,site,acts,c,w,o,mat):
 at=site;path=[SITES[site][0]];stoplist=[]
 for a in acts:
  dest=o['hub'] if a=='X' else (w['i'] if a=='i' else c['old'][a])
  path+=mat[at][dest][1][1:];at=dest;stoplist.append(dest)
 conn.vehicle.setRoute(v,path)
 for s in stoplist:
  e,p=SITES[s];conn.vehicle.setStop(v,e,pos=p,laneIndex=0,duration=10000,flags=conn.vehicle.STOP_PARKING)
def add_truck(conn,w,o,mat):
 dest='T'+o['hub'][-1];src=w['T'];conn.route.add('new_truck',mat[src][dest][1]);conn.vehicle.add('T','new_truck',typeID='truck',depart='now',departLane='0',departPos=str(SITES[src][1]),departSpeed='0')
 e,p=SITES[dest];conn.vehicle.setStop('T',e,pos=p,laneIndex=0,duration=10000,flags=conn.vehicle.STOP_PARKING)
def simulate(c,people,out,w=None,o=None,expected=None,offset=0,corrected=True):
 out.mkdir();mat=MATRIX;tc,_,env=discover_runtime();C=tc.constants
 lengths={e.get('id'):round(float(e.find('lane').get('length'))*100) for e in ET.parse(NET/f'cycle_{offset}.net.xml').getroot().findall('edge')}
 scene(c,out/'old_batch.rou.xml',people,mat)
 put(out/'INPUT.json',dict(c=c,people=people,offset=offset,mode='prefix' if o is None else 'replay',wave=w,plan=o,initial_xml_hash=fh(out/'old_batch.rou.xml'),runtime=env,net=fh(NET/f'cycle_{offset}.net.xml')))
 args=[env['sumo_binary'],'-n',str(NET/f'cycle_{offset}.net.xml'),'-r',str(out/'old_batch.rou.xml'),'--step-length','0.2','--seed','40801','--collision.check-junctions','true','--collision.action','warn','--time-to-teleport','-1','--no-step-log','true','--duration-log.disable','true','--xml-validation','never','--pedestrian.striping.dawdling','0','--pedestrian.striping.jamtime','1000','--pedestrian.striping.jamtime.crossing','1000','--tripinfo-output',str(out/'trips.xml'),'--tripinfo-output.write-unfinished','true','--collision-output',str(out/'collisions.xml'),'--error-log',str(out/'sumo.log')]
 conn=None;prefix=hashlib.sha256();total=hashlib.sha256();events=[];arr={};done={};ctx=None;dx=0;tel=0;error=None;clock=time.perf_counter()
 controller=StopController(out,corrected)
 try:
  with (out/'stdout.log').open('x') as stdout,gzip.open(out/'trace.jsonl.gz','xt',encoding='utf-8') as stream:
   tc.start(args,label=out.name,stdout=stdout,numRetries=2);conn=tc.getConnection(out.name)
   assert conn.trafficlight.getProgram('C')=='custom'
   seen=set();exitset=set();pseen=set();pexit=set();co={v:set(items(c,v)) for v in c['actors']};co['T']=set()
   idx={v:0 for v in c['actors']};idx['T']=0
   acts={v:[items(c,v)[0]] for v in c['actors']};acts['T']=[]
   parked={};trans=None
   for tick in range(1,3001):
    conn.simulationStep();assert round(conn.simulation.getTime()*HZ)==tick
    for v in conn.simulation.getDepartedIDList():
     seen.add(v);conn.vehicle.subscribe(v,[C.VAR_ROAD_ID,C.VAR_LANEPOSITION,C.VAR_SPEED,C.VAR_STOPSTATE,C.VAR_POSITION])
    for p in conn.simulation.getDepartedPersonIDList():
     pseen.add(p);conn.person.subscribe(p,[C.VAR_ROAD_ID,C.VAR_POSITION])
    exitset.update(conn.simulation.getArrivedIDList());pexit.update(conn.simulation.getArrivedPersonIDList())
    dx+=conn.simulation.getCollidingVehiclesNumber();tel+=conn.simulation.getStartingTeleportNumber()
    veh={v:[r[C.VAR_ROAD_ID],round(r[C.VAR_LANEPOSITION],6),round(r[C.VAR_SPEED],6),r[C.VAR_STOPSTATE],*[round(z,6) for z in r[C.VAR_POSITION]]] for v,r in conn.vehicle.getAllSubscriptionResults().items() if r and v not in exitset}
    ped={p:[r[C.VAR_ROAD_ID],*[round(z,6) for z in r[C.VAR_POSITION]]] for p,r in conn.person.getAllSubscriptionResults().items() if r and p not in pexit}
    frame={'tick':tick,'vehicles':veh,'people':ped,'signal':conn.trafficlight.getRedYellowGreenState('C')};line=json.dumps(frame,sort_keys=True,separators=(',',':'))+'\n';stream.write(line);total.update(line.encode())
    if tick<=EPOCH:
     prefix.update(line.encode());assert 'T' not in veh
    if tick==EPOCH:
     ctx={}
     for vv in c['actors']:
      first=items(c,vv)[0];dest=c['old'][first];assert hit(veh[vv],dest) and parked[vv]==10
      ctx[vv]=dict(ready=EPOCH*SCALE//HZ,edge=veh[vv][0],pos_m=veh[vv][1],speed=veh[vv][2],remaining_cm=0,
          native_route=list(conn.vehicle.getRoute(vv)),route_index=conn.vehicle.getRouteIndex(vv),committed=dest)
     if o is None:break
     assert expected==prefix.hexdigest()
     acts={v:o['route'][v] for v in c['actors']}|{'T':['X']};co['T'].add('i');events.append([tick,'release','T','i','DEPOT']);add_truck(conn,w,o,mat)
    controller.new_step(conn,veh,idx,acts,tick,hit)
    for v in c['actors']+['T']:
     if idx[v]>=len(acts[v]):continue
     act=acts[v][idx[v]]
     dest=('T'+o['hub'][-1] if v=='T' else o['hub']) if act=='X' else (w['i'] if act=='i' else c['old'][act])
     if v in c['actors'] and idx[v]==0 and tick<10:continue
     if not hit(veh.get(v),dest):continue
     if v not in parked:
      parked[v]=tick;events.append([tick,'arrive',v,act,dest])
      if act=='X':arr[v]=tick
     if act!='X' and tick==parked[v]+4*HZ:
      assert o is not None and act in co[v] and act not in done
      if idx[v]==0:assert tick==EPOCH
      co[v].remove(act);done[act]=tick;events.append([tick,'delivery',v,act,dest])
      conn.vehicle.resume(v)
      if idx[v]==0:controller.install(conn,v,dest,acts[v][1:],c,w,o,mat,tick)
      idx[v]+=1;del parked[v]
    if o:
     v=o['receiver'];h=o['hub']
     if v in parked and 'T' in parked and acts[v][idx[v]]=='X':
      assert hit(veh[v],h) and hit(veh['T'],'T'+h[-1]) and math.dist(veh[v][4:],veh['T'][4:])<=12
      assert sum(c['size'][a] for a in co[v])+4<=CAP[v]
      if trans is None:trans=tick;events.append([tick,'beginX',v,'i',h])
      if tick==trans+2*HZ:
       assert co['T']=={'i'};co['T'].clear();co[v].add('i');events.append([tick,'transfer',v,'i',h])
       for who in ['T',v]:conn.vehicle.resume(who);del parked[who];idx[who]+=1
     controller.arm_next(conn,veh,idx,acts,tick)
     if len(done)==len(c['old'])+1 and conn.simulation.getMinExpectedNumber()==0:break
   if o:
    assert len(done)==len(c['old'])+1 and not any(co.values()) and exitset==seen==(set(c['actors'])|{'bg','T'}|({'slow0','slow1'} if c['slow'] else set())) and len(pexit)==len(pseen)==(10 if people else 0)
   assert dx==tel==0
 except BaseException:error=traceback.format_exc()
 finally:
  controller.close()
  if conn:
   try:conn.close()
   except Exception:pass
 res={'error':error,'prefix':prefix.hexdigest(),'trace_hash':total.hexdigest(),'epoch_context':ctx,'events':events,'completed':done,'collision_ticks':dx,'teleports':tel,'elapsed_s':time.perf_counter()-clock}
 put(out/'RESULT.json',res)
 if error:raise ValueError(error)
 return res
