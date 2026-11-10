import csv, gzip, hashlib, itertools, json, math, sys, time, traceback, types
import xml.etree.ElementTree as ET
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'source'))
from models import SCALE, EPOCH, HZ, SERV, XFER, SITES, fh, digest, items, read, put
from dispatch import evaluate, dispatch
from audit import audit
FROZEN=ROOT/'runs/signal_freeze_01'
PEOPLE=True
ARMS=['PLAIN2','DIRECT2','SEP','COMMON']

def direct(s,mat,v,h):
    c,w,ctx=s['c'],s['wave2'],s['context']
    old_total=0
    for actor in c['actors']:
        first,*remain=items(c,actor)
        scores=[]
        for seq in itertools.permutations(remain):
            site=c['old'][first];clock=ctx[actor]['ready'];value=clock
            for j in seq:
                dest=c['old'][j];clock+=3*mat[site][dest][0]+SERV
                site=dest;value+=clock
            scores.append(value)
        old_total+=min(scores)
    depot=w['T'];truck_arr=EPOCH*SCALE//HZ+4*mat[depot]['T'+h[-1]][0]
    committed=items(c,v)[0];receiver_arr=ctx[v]['ready']+3*mat[c['old'][committed]][h][0]
    new=max(truck_arr,receiver_arr)+XFER+3*mat[h][w['i']][0]+SERV-EPOCH*SCALE//HZ
    return old_total+new

def select(s,mat,arm):
    c,w,ctx=s['c'],s['wave2'],s['context']
    start=time.perf_counter()
    if arm in ['SEP','COMMON']:
        out=dispatch(c,w,mat,ctx,arm,2)
        for k in ['choice','opened','plan','score','stop','rank']:
            assert json.loads(json.dumps(out[k]))==s['arms'][arm]['2'][k]
    else:
        options=list(itertools.product(sorted(c['actors']),('HE','HW')))
        ranks=[(None,v,h) for v,h in options] if arm=='PLAIN2' else sorted((direct(s,mat,v,h),v,h) for v,h in options)
        best=math.inf;choice='~';plan=None;opened=[];stop=None
        for lb,v,h in ranks:
            if len(opened)>=2:break
            if arm=='DIRECT2' and lb>best:
                stop=[v+h[-1],lb,best];break
            key=v+h[-1];score,paths=evaluate(c,w,mat,ctx,v,h);opened.append(key)
            if (score,key)<(best,choice):
                best,choice=score,key
                plan=dict(receiver=v,hub=h,route=paths)
        out=dict(choice=choice,plan=plan,score=best,opened=opened,rank=ranks,stop=stop)
    elapsed=time.perf_counter()-start
    assert elapsed<1 and 0<len(out['opened'])<=2
    opt=s['checks'][out['choice']]
    assert out['plan']=={k:opt[k] for k in ['receiver','hub','route']} and out['score']==opt['truth']
    return dict(choice=out['choice'],plan=out['plan'],plan_hash=digest(out['plan']),score=out['score'],opened=out['opened'],rank=out['rank'],stop=out['stop'],decision_s=elapsed)

def fingerprints():
    p=[FROZEN/'DECISIONS.json',FROZEN/'HASH.json',ROOT/'network/expanded_legs.json',HERE/'ops.py',HERE/'PROTOCOL.md']
    return {str(x.relative_to(ROOT)):fh(x) for x in p}
def freeze():
    ds=read(FROZEN/'DECISIONS.json');ref=read(FROZEN/'HASH.json')
    assert ref['decisions']==fh(FROZEN/'DECISIONS.json')
    assert all(fh(ROOT/'source'/k)==v for k,v in ref['sources'].items())
    m=read(ROOT/'network/expanded_legs.json');cases={};checks=[]
    assert len(ds)==8
    for key,s in sorted(ds.items()):
        for ident,r in s['checks'].items():
            proposed=direct(s,m,r['receiver'],r['hub'])
            assert proposed<=r['SEP']<=r['COMMON']<=r['truth']
            checks.append(dict(key=key,id=ident,DIRECT=proposed,SEP=r['SEP'],COMMON=r['COMMON'],truth=r['truth']))
        cases[key]={a:select(s,m,a) for a in ARMS}
    put(HERE/'FROZEN_CHOICES.json',cases)
    put(HERE/'GATE.json',dict(sources=fingerprints(),n_cases=len(ds),n_checks=len(checks),bounds=checks,choices=fh(HERE/'FROZEN_CHOICES.json')))
def verify_trace(folder,s,p):
    inp=read(folder/'INPUT.json');res=read(folder/'RESULT.json')
    source=ROOT/'runs/signal_prefix_01'/s['key']
    assert inp['plan']==p['plan'] and digest(inp['plan'])==p['plan_hash'] and inp['c']==s['c'] and inp['wave']==s['wave2']
    assert inp['people'] and inp['mode']=='replay'
    assert fh(folder/'old_batch.rou.xml')==inp['initial_xml_hash']==fh(source/'old_batch.rou.xml')
    assert inp['net']==fh(ROOT/'network'/f"cycle_{s['offset']}.net.xml")
    assert res['prefix']==s['prefix'] and res['epoch_context']==s['context']
    sha=hashlib.sha256();pref=hashlib.sha256();seen=set();n=0
    expected={x.get('state') for x in ET.parse(ROOT/'network'/f"cycle_{s['offset']}.net.xml").getroot().find("tlLogic[@id='C']").findall('phase')}
    with gzip.open(folder/'trace.jsonl.gz','rt',encoding='utf8') as f:
        for n,line in enumerate(f,1):
            d=json.loads(line); assert d['tick']==n
            sha.update(line.encode());seen.add(d['signal'])
            if n<=EPOCH:
                pref.update(line.encode());assert 'T' not in d['vehicles']
    assert pref.hexdigest()==s['prefix'] and sha.hexdigest()==res['trace_hash'] and seen==expected
    assert res['collision_ticks']==res['teleports']==0
    record=dict(trace_hash=res['trace_hash'],prefix=res['prefix'],ticks=n,signals=sorted(seen),route_file_sha=fh(folder/'old_batch.rou.xml'),input_net_sha=inp['net'])
    if res['error']:
        assert n==3000 and len(res['completed'])<len(s['c']['old'])+1
        return record|dict(status='horizon',error=res['error'],completion_ticks=res['completed'],missing=sorted((set(s['c']['old'])|{'i'})-set(res['completed'])))
    # Use original stop-episode auditor against read-only inputs, suppress its write into source folders.
    auditor=types.FunctionType(audit.__code__,audit.__globals__|{'put':lambda *args:None})
    a=auditor(folder)
    assert a['all_pass'] and a['trace_hash']==res['trace_hash'] and abs(a['old_s']+a['new_s']-a['J_s'])<1e-7
    if (folder/'AUDIT.json').exists(): assert a==read(folder/'AUDIT.json')
    return record|a|dict(status='complete')

def run():
    frozen=read(HERE/'FROZEN_CHOICES.json');gate=read(HERE/'GATE.json');ds=read(FROZEN/'DECISIONS.json')
    assert gate['choices']==fh(HERE/'FROZEN_CHOICES.json') and gate['sources']==fingerprints()
    from street_cycle import simulate
    raw=HERE/'new_replays';raw.mkdir();log=HERE/'verified';log.mkdir()
    state_rows=[];problems=[];count=0
    for key,s in sorted(ds.items()):
        options=frozen[key];prefix=ROOT/'runs/signal_prefix_01'/key
        s=dict(s,key=key)
        assert fh(prefix/'RESULT.json')==read(ROOT/'runs/signal_prefix_01/HISTORIES.json')[key]['sha']
        seed=s['c']['seed'];old_run=ROOT/'runs'/f'signal_actual_{seed}';lookups={}
        for folder in list(old_run.glob(key+'_*'))+list((ROOT/'ranking_check').glob(key+'_*')):
            candidate=read(folder/'INPUT.json')
            lookups.setdefault(digest(candidate['plan']),folder)
        cached={}
        for a in ['SEP','COMMON','PLAIN2','DIRECT2']:
            p=options[a];sig=p['plan_hash']
            if a in ['SEP','COMMON']:
                folder=old_run/(key+'_'+a)
            elif sig in cached:
                folder=cached[sig]
            elif sig in lookups:
                folder=lookups[sig]
            else:
                folder=raw/(key+'_'+p['choice']);count+=1
                assert count<=16
                try:simulate(s['c'],True,folder,s['wave2'],p['plan'],s['prefix'],s['offset'])
                except Exception as exc:problems.append(dict(key=key,arm=a,type='native_execution',path=str(folder.relative_to(ROOT)),error=traceback.format_exc()))
            cached[sig]=folder
            try:
                metrics=verify_trace(folder,s,p)
            except Exception as exc:
                metrics=dict(status='audit_failed',error=traceback.format_exc())
                problems.append(dict(key=key,arm=a,type='audit_failed',error=metrics['error'],path=str(folder.relative_to(ROOT))))
            if metrics['status']!='complete':
                problems.append(dict(key=key,arm=a,type=metrics['status'],path=str(folder.relative_to(ROOT))))
            put(log/(key+'_'+a+'.json'),metrics)
            state_rows.append(dict(key=key,arm=a,choice=p['choice'],plan_hash=sig,opened=p['opened'],static_s=p['score']/SCALE,source=str(folder.relative_to(ROOT)),**metrics))
            print(key,a,p['choice'],metrics['status'],flush=True)
    put(HERE/'ROWS.json',state_rows);put(HERE/'FAILURES.json',problems)
    put(HERE/'RUN.json',dict(new_cases=count,policy_rows=len(state_rows),unique_paths=len({r['source'] for r in state_rows})))
def paired():
    rows=read(HERE/'ROWS.json');pairs=[]
    for p in rows:
        if p['arm'] not in ['PLAIN2','DIRECT2']:continue
        for arm in ['SEP','COMMON']:
            q=next(r for r in rows if r['key']==p['key'] and r['arm']==arm)
            row={'key':p['key'],'baseline':p['arm'],'arm':arm,'base_choice':p['choice'],'arm_choice':q['choice'],'both_completed':p['status']==q['status']=='complete','base_status':p['status'],'arm_status':q['status'],'same_plan':p['plan_hash']==q['plan_hash'],'same_trace':p.get('trace_hash')==q.get('trace_hash')}
            for k in ['J_s','old_s','new_s','wait_s','handoff_s']:
                row[k+'_gain']=round(p[k]-q[k],6) if row['both_completed'] else ''
            pairs.append(row)
    with (HERE/'PAIRS.csv').open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(pairs[0]));w.writeheader();w.writerows(pairs)
    stats={}
    for base in ['PLAIN2','DIRECT2']:
        sub=[r for r in pairs if r['baseline']==base and r['arm']=='COMMON'];ok=[r for r in sub if r['both_completed']]
        stats[base]={'n':len(sub),'complete':len(ok),'same_plan':sum(r['same_plan'] for r in sub),'wins':sum(r['J_s_gain']>0 for r in ok),'ties':sum(r['J_s_gain']==0 for r in ok),'losses':sum(r['J_s_gain']<0 for r in ok),'delta_baseline_minus_COMMON':{f:round(sum(r[f+'_gain'] for r in ok),6) for f in ['J_s','old_s','new_s','wait_s','handoff_s']}}
    put(HERE/'SUMMARY.json',stats)
if __name__=='__main__':
    {'freeze':freeze,'run':run,'paired':paired}[sys.argv[1]]()
