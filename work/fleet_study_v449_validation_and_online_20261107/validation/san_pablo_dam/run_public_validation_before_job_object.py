"""Bounded public-data tutorial validation. No traffic runs without --execute.
Adaptation: fixed tau grid, day holdout and ID-based instantaneous observations.
No optimizer, no SciPy, no delivery-solver imports, no original-data mutations.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,os,re,subprocess,sys,time,traceback
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def write_xml(p,r):ET.ElementTree(r).write(p,encoding='utf-8',xml_declaration=True)
def times(day,station):
    p=ROOT/'upstream/data'/f'obstimes_{day}_{station}.txt';rows=[]
    for raw in p.read_text().splitlines():
        a=raw.split(':')
        if len(a)!=3:raise ValueError(('timestamp',p,raw))
        h,m,s=map(int,a)
        if not(0<=h<24 and 0<=m<60 and 0<=s<60):raise ValueError(('clock',p,raw))
        rows.append(h*3600+m*60+s)
    if any(a>b for a,b in zip(rows,rows[1:])):raise ValueError(('nonmonotone',p))
    return rows

def verify_sources():
    manifest=json.loads((ROOT/'Upstream_Manifest.json').read_text())
    for r in manifest['sources']:
        if r['status']!='FETCHED' or sha(ROOT/'upstream'/r['file'])!=r['sha256']:raise ValueError(('upstream hash',r['file']))
    freeze=json.loads((ROOT/'Preparation_Manifest.json').read_text())
    for name,value in freeze['prepared_source_hashes'].items():
        if sha(ROOT/name)!=value:raise ValueError(('prepared hash',name))
    return manifest

def command(argv,folder,label,deadline,cap):
    remaining=min(cap,deadline-time.monotonic())
    if remaining<=0:raise TimeoutError('Global validation budget exhausted')
    dump(folder/(label+'_command.json'),{'argv':argv,'wall_cap_seconds':remaining})
    with (folder/(label+'_stdout.txt')).open('w',encoding='utf-8') as so,(folder/(label+'_stderr.txt')).open('w',encoding='utf-8') as se:
        proc=subprocess.run(argv,cwd=folder,stdout=so,stderr=se,timeout=remaining,check=False)
    if proc.returncode:raise RuntimeError((label,'exit',proc.returncode))
    return (folder/(label+'_stdout.txt')).read_text(),(folder/(label+'_stderr.txt')).read_text()

def prepare_run(folder,day,tau,p,net):
    folder.mkdir()
    obs={i:times(day,i) for i in (1,2,3,4,7,8)};n=len(obs[1])
    if n<100 or any(len(x)!=n for x in obs.values()):raise ValueError(('observation lengths',day))
    for a,b in p['segments']+[[7,8]]:
        if any(y<=x for x,y in zip(obs[a],obs[b])):raise ValueError(('nonpositive travel time',day,a,b))
    routes=ET.Element('routes');ET.SubElement(routes,'vType',id='pass',tau=str(tau),**{k:str(v) for k,v in p['parameters'].items()})
    ET.SubElement(routes,'route',id='route01',edges='1to7 7to8')
    for i,t in enumerate(obs[1]):ET.SubElement(routes,'vehicle',id=str(i),depart=str(t),arrivalPos='-1',route='route01',type='pass',departSpeed='max')
    write_xml(folder/'routes.rou.xml',routes)
    vss=ET.Element('vss')
    for i in range(n-1):
        if obs[7][i]!=obs[7][i+1]:ET.SubElement(vss,'step',time=str(obs[7][i]),speed=str(p['vss_distance_m']/(obs[8][i]-obs[7][i])))
    write_xml(folder/'boundary.vss.xml',vss)
    additional=ET.Element('additional');ET.SubElement(additional,'variableSpeedSign',id='vss',lanes='7to8_0',file='boundary.vss.xml')
    positions={x.attrib['id']:x.attrib for x in ET.parse(ROOT/'upstream/data/input_det.add.xml').getroot()}
    for i in (1,2,3,4):
        z=positions['obs'+str(i)];ET.SubElement(additional,'instantInductionLoop',id=z['id'],lane=z['lane'],pos=z['pos'],file='instant.xml')
    write_xml(folder/'detectors.add.xml',additional)
    cfg=ET.Element('configuration');inputs=ET.SubElement(cfg,'input')
    for key,val in [('net-file',str(net)),('route-files','routes.rou.xml'),('additional-files','detectors.add.xml')]:ET.SubElement(inputs,key,value=val)
    tt=ET.SubElement(cfg,'time')
    for key,val in [('begin',obs[1][0]//60*60),('end',obs[8][-1]+900),('step-length',p['step_length'])]:ET.SubElement(tt,key,value=str(val))
    pr=ET.SubElement(cfg,'processing')
    for key,val in [('time-to-teleport',p['time_to_teleport']),('collision.action',p['collision_action']),('collision.check-junctions','true')]:ET.SubElement(pr,key,value=str(val))
    output=ET.SubElement(cfg,'output')
    for key,val in [('tripinfo-output','tripinfo.xml'),('tripinfo-output.write-unfinished','true'),('summary-output','summary.xml')]:ET.SubElement(output,key,value=val)
    report=ET.SubElement(cfg,'report');ET.SubElement(report,'no-step-log',value='true')
    random=ET.SubElement(cfg,'random_number');ET.SubElement(random,'seed',value=str(p['seed']))
    write_xml(folder/'scenario.sumocfg',cfg)
    dump(folder/'Input_Manifest.json',{'day':day,'tau':tau,'n':n,'files':{x.name:sha(x) for x in folder.iterdir() if x.is_file()},'network_sha256':sha(net)})
    return obs

def measure(folder,obs,p,day,tau):
    n=len(obs[1]);seen={i:{} for i in (1,2,3,4)}
    for _,elem in ET.iterparse(folder/'instant.xml',events=('end',)):
        if elem.attrib.get('state')=='enter':
            detector=elem.attrib['id'];station=int(detector.removeprefix('obs'));vid=int(elem.attrib['vehID']);t=float(elem.attrib['time'])
            if station not in seen or not(0<=vid<n) or vid in seen[station]:raise ValueError(('duplicate/unknown crossing',station,vid))
            seen[station][vid]=t
        elem.clear()
    if any(set(z)!=set(range(n)) for z in seen.values()):raise ValueError(('missing detector crossings',day,tau,{i:len(z) for i,z in seen.items()}))
    trips=ET.parse(folder/'tripinfo.xml').getroot().findall('tripinfo');ids=[x.attrib['id'] for x in trips]
    if len(ids)!=n or set(ids)!=set(map(str,range(n))) or any(float(x.attrib['arrival'])<0 for x in trips):raise ValueError(('incomplete vehicle population',day,tau))
    text=(folder/'sumo_stdout.txt').read_text()+'\n'+(folder/'sumo_stderr.txt').read_text()
    bad=[line for line in text.splitlines() if re.search(r'(?i)(warning|error).*?(collision|teleport)',line)]
    if bad:raise ValueError(('invalid simulation warnings',bad))
    rows=[];segments=[]
    for a,b in p['segments']:
        errors=[]
        for i in range(n):
            observed=obs[b][i]-obs[a][i];simulated=seen[b][i]-seen[a][i]
            if simulated<=0:raise ValueError(('nonpositive simulated travel time',i,a,b))
            err=simulated-observed;errors.append(err)
            rows.append({'day':day,'tau':tau,'vehicle_row_index':i,'segment':f'{a}-{b}','observed_seconds':observed,'simulated_seconds':simulated,'error_seconds':err})
        segments.append({'segment':f'{a}-{b}','n':n,'rmse_seconds':math.sqrt(sum(e*e for e in errors)/n),'mae_seconds':sum(abs(e) for e in errors)/n,'bias_seconds':sum(errors)/n})
    with (folder/'Matched_Travel_Times.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    result={'day':day,'tau':tau,'vehicles':n,'segment_metrics':segments,'mean_segment_rmse_seconds':sum(x['rmse_seconds'] for x in segments)/len(segments),'all_requested_vehicles_arrived':True,'all_expected_crossings_present':True,'collision_or_teleport_warnings':bad,'max_depart_delay_seconds':max(float(x.attrib['departDelay']) for x in trips),'mean_depart_delay_seconds':sum(float(x.attrib['departDelay']) for x in trips)/n}
    dump(folder/'Metrics.json',result);return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    if not args.execute:ap.error('Use --execute only under the scheduled external thermal monitor; no simulation has run')
    os.environ.update(TEMP=r'E:\CodexResearch-xi\temp',TMP=r'E:\CodexResearch-xi\temp',PYTHONDONTWRITEBYTECODE='1')
    out=args.out.resolve();allowed=(ROOT/'runs').resolve()
    if allowed not in out.parents or out.exists() or out.drive.upper()!='E:':ap.error('Use fresh descendant of validation/san_pablo_dam/runs on E')
    manifest=verify_sources();p=json.loads((ROOT/'Frozen_Protocol.json').read_text());out.mkdir(parents=True)
    deadline=time.monotonic()+p['total_execution_seconds'];started=time.perf_counter();records=[]
    try:
        sumo=Path(p['sumo_binary']);netconvert=Path(p['netconvert_binary'])
        if not sumo.is_file() or not netconvert.is_file():raise FileNotFoundError('Existing SUMO binaries unavailable; no installation attempted')
        version,_=command([str(sumo),'--version'],out,'version',deadline,10)
        if not re.search(r'\bsumo '+re.escape(p['sumo_version_observed'])+r'\b',version):raise ValueError('SUMO version differs from freeze')
        net=out/'network.net.xml'
        command([str(netconvert),'-n',str(ROOT/'upstream/data/spd-road.nod.xml'),'-e',str(ROOT/'upstream/data/spd-road.edg.xml'),'-o',str(net)],out,'netconvert',deadline,p['max_per_process_seconds'])
        def run(day,tau):
            folder=out/f'day{day}_tau{tau:.1f}';obs=prepare_run(folder,day,tau,p,net)
            command([str(sumo),'-c',str(folder/'scenario.sumocfg')],folder,'sumo',deadline,p['max_per_process_seconds'])
            result=measure(folder,obs,p,day,tau);records.append(result);dump(out/'Progress.json',{'completed':len(records),'runs':records});return result
        train=[run(p['train_day'],tau) for tau in p['tau_candidates']]
        best=min(train,key=lambda r:(r['mean_segment_rmse_seconds'],r['tau']!=p['baseline_tau'],r['tau']))
        selection={'selected_tau':best['tau'],'selection_uses_day1_only':True,'train_results':train,'rule':p['selection']}
        dump(out/'Selection_Before_Heldout.json',selection)
        baseline=run(p['heldout_day'],p['baseline_tau']);winner=baseline if best['tau']==p['baseline_tau'] else run(p['heldout_day'],best['tau'])
        delta=winner['mean_segment_rmse_seconds']-baseline['mean_segment_rmse_seconds']
        summary={'workflow_status':'PASS','empirical_agreement_status':'MEASURED_NO_UNIVERSAL_ACCEPTANCE_THRESHOLD','source_commit':manifest['commit'],'sumo_version':version.splitlines()[0],'sumo_sha256':sha(sumo),'netconvert_sha256':sha(netconvert),'protocol_sha256':sha(ROOT/'Frozen_Protocol.json'),'script_sha256':sha(__file__),'sumo_runs':len(records),'selected_tau':best['tau'],'selection_before_heldout_sha256':sha(out/'Selection_Before_Heldout.json'),'baseline_heldout':baseline,'selected_heldout':winner,'heldout_mean_segment_rmse_delta_seconds':delta,'heldout_rmse_improved':delta<0,'no_day2_parameter_tuning':True,'conditional_on_observed_day_specific_inflow_and_outflow':True,'delivery_network_calibrated':False,'all_run_metrics':records,'elapsed_seconds':time.perf_counter()-started}
        dump(out/'Summary.json',summary)
        dump(out/'Output_Manifest.json',{'files':{str(f.relative_to(out)):sha(f) for f in sorted(out.rglob('*')) if f.is_file()}})
        dump(out/'PROCESS_COMPLETE.json',{'status':'PASS','sumo_runs':len(records),'interpretation':'Workflow completion only, not a physical-calibration acceptance threshold; inspect heldout error and failures.'})
        print(json.dumps({'status':'PASS','sumo_runs':len(records),'selected_tau':best['tau'],'heldout_rmse_delta_seconds':delta,'out':str(out)}));return 0
    except BaseException as exc:
        dump(out/'VALIDATION_FAILURE.json',{'error':repr(exc),'traceback':traceback.format_exc(),'completed_runs':records})
        dump(out/'PROCESS_COMPLETE.json',{'status':'FAIL','completed_runs':len(records)})
        raise
if __name__=='__main__':raise SystemExit(main())
