"""Independent small correctness gate and immutable input preparation; no SUMO run.
Run with -B. check is exhaustive on the explicitly prepared old V420 snapshots.
The reference uses its own action/load recurrence and the frozen forecast leg,
not production children, bounds, search or its plan forecast.
"""
from pathlib import Path
import argparse,hashlib,json,sys,time,traceback
import online_model as model
import native_two_batch  # same source closure in check and execution entry points
ROOT=Path(__file__).resolve().parent

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,indent=2,ensure_ascii=False,allow_nan=False)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sources():
    paths=set(ROOT.glob('*.py'))
    paths.add(ROOT.parent/'validation'/'san_pablo_dam'/'run_public_validation.py')
    for module in tuple(sys.modules.values()):
        raw=getattr(module,'__file__',None)
        if raw:
            p=Path(raw).resolve()
            if p.suffix=='.py' and p.is_relative_to(model.WORK):paths.add(p)
    paths.add(model.WORK/'fleet_study_v419_signal_pedestrian_traffic_20261104'/'turn2_legs.json')
    paths.update(model.old.NET/f'cycle_{o}.net.xml' for o in (0,24))
    return {str(p):sha(p) for p in sorted(paths)}

def prepare(out):
    src=model.LEGACY/'runs/decisions_01/DECISIONS.json';archive=read(src)
    # Fixed lexical first four archived snapshots, independent of any new outcome.
    rows=[]
    for name in sorted(archive)[:4]:
        s=archive[name];w=s['wave'];a=w['i'];b='ME' if a=='MW' else 'MW'
        row={k:s[k] for k in ('seed','offset','people','slow','c','ctx','obs','prefix','xml')}
        row.update(case=name,wave2={'T':w['T'],'release':6.,'orders':{
            'a':{'dest':a,'weight':3},'b':{'dest':b,'weight':4}}})
        rows.append(row)
    put(out,{'schema':'V449-two-batch-original-J-v1','source_archive':str(src),
             'source_sha256':sha(src),'selection':'sorted archive keys first 4; not selected by outcome',
             'cases':rows})

def reference(snapshot):
    """All legal complete routes, exact independent forecast prefix states and costs."""
    c=snapshot['c'];w=snapshot['wave2'];E=float(model.old.E);service=4.;transfer=2.
    sig=model.old.ShortForecast(snapshot['offset'],snapshot['obs'],'COARSE')
    def leg(t,p,q,speed=8):
        try:return sig.leg(t,p,q,speed,model.old.MATRIX,True,[])
        finally:sig.relevant.clear()
    jobs={v:tuple(model.old.items(c,v)) for v in c['actors']}
    fixed={v:tuple(model.old.lengths(c,v)) for v in c['actors']}
    others={}
    for v,seq in fixed.items():
        t=E;pos=c['old'][seq[0]];val=E
        for j in seq[1:]:t=leg(t,pos,c['old'][j])+service;val+=t;pos=c['old'][j]
        others[v]=val
    prefixes={};leaves={};h2min={};clocks={}
    for v in c['actors']:
        for h in model.old.POINTS:
            b=model.Branch(v,h);u=next(x for x in c['actors'] if x!=v)
            truck=leg(E,w['T'],'T'+h[-1],6);initial=jobs[v][0];pending=jobs[v][1:]
            def walk(tokens,t,pos,remaining,phase,adone,bdone,cost,h2):
                key=(b,tokens);clocks[key]=(t,pos,cost)
                if not remaining and phase==2 and adone and bdone:
                    val=cost+others[u];plan={'receiver':v,'hub':h,'route':{v:list(tokens),u:list(fixed[u])}}
                    leaves[model.signature(plan)]=(val,plan)
                    for k in range(1,len(tokens)+1):
                        pk=(b,tokens[:k]);prefixes[pk]=min(prefixes.get(pk,float('inf')),val)
                        if 'Xa' not in tokens[:k]:h2min[pk]=min(h2min.get(pk,float('inf')),h2)
                    return
                options=list(remaining);load=sum(c['size'][j] for j in remaining)
                if phase>=1 and not adone:load+=w['orders']['a']['weight']
                if phase>=2 and not bdone:load+=w['orders']['b']['weight']
                if phase==0 and len(remaining)<len(pending) and load+w['orders']['a']['weight']<=model.old.CAP[v]:options.append('Xa')
                if phase==1:
                    if not adone:options.append('a')
                    if load+w['orders']['b']['weight']<=model.old.CAP[v]:options.append('Xb')
                if phase==2 and not bdone:options.append('b')
                for j in sorted(options):
                    dest=h if j.startswith('X') else w['orders'][j]['dest'] if j in ('a','b') else c['old'][j]
                    nt=leg(t,pos,dest);nc=cost;np=phase;na=adone;nb=bdone;nr=remaining;nh=h2
                    if j=='Xa':nt=max(nt,truck)+transfer;np=1
                    elif j=='Xb':nt+=transfer;np=2;nh=nt
                    else:
                        nt+=service;nc+=nt-(E if j in ('a','b') else 0.)
                        if j=='a':na=True
                        elif j=='b':nb=True
                        else:nr=tuple(x for x in remaining if x!=j)
                    walk(tokens+(j,),nt,dest,nr,np,na,nb,nc,nh)
            walk((initial,),E,c['old'][initial],pending,0,False,False,E,None)
    return prefixes,leaves,h2min,clocks

def check_case(s):
    prefixes,leaves,h2min,clocks=reference(s);ctx=model.Context(s);seen=set();terminal={};strong=cuts=0
    for b in ctx.branches():
        stack=[ctx.initial(b)]
        while stack:
            state=stack.pop();key=(b,state.tokens)
            if key in seen:raise AssertionError('Duplicate prefix')
            seen.add(key);rt,rp,rc=clocks[key]
            assert abs(rt-state.t)<1e-7 and rp==state.pos and abs(rc-state.cost)<1e-7
            base=ctx.bound(state,False);joint=ctx.bound(state,True);truth=prefixes[key]
            assert base<=joint+1e-7 and joint<=truth+1e-6,(s['case'],state,base,joint,truth)
            strong+=joint>base+1e-7
            if 'Xa' not in state.tokens:
                _,hbase,hpair=ctx.h2_bounds(state)
                assert hbase<=hpair+1e-7 and hpair<=h2min[key]+1e-6
            if ctx.terminal(state):
                p=ctx.plan(state);keyp=model.signature(p);pred=ctx.forecast(p)['J']
                assert abs(pred-truth)<1e-6 and abs(joint-truth)<1e-6
                terminal[keyp]=pred
            else:stack.extend(ctx.children(state))
    assert seen==set(prefixes) and set(terminal)==set(leaves)
    opt=min(v[0] for v in leaves.values());solves={}
    for arm in model.ARMS:
        r=model.solve(s,arm,per_branch_cap=6)
        counts=list(r['per_branch_forecasts'].values())
        assert len(counts)==4 and all(1<=n<=6 for n in counts)
        assert r['counts']['full_forecasts']==sum(counts)
        assert r['J']>=opt-1e-6 and sum(counts)<=24
        assert ctx.legal(r['plan']) and abs(ctx.forecast(r['plan'])['J']-r['J'])<1e-6
        solves[arm]=r
    for arm in ('RADIUS','PAIR'):
        r=model.solve(s,arm,per_branch_cap=len(leaves)+1)
        assert r['certified_forecast_optimal'] and abs(r['J']-opt)<1e-6
    initial={model.signature(x['initial']['plan']) for x in solves.values()}
    assert len(initial)==1
    return {'case':s['case'],'status':'PASS','prefixes':len(seen),'plans':len(leaves),
            'strict_pair_prefixes':strong,'optimum_J':opt,'fixed24':solves}

def validate_gate(path,inputs):
    path=Path(path)
    if (path/'FAILURE.json').exists():raise ValueError('Failed gate')
    complete=read(path/'PROCESS_COMPLETE.json');gate=read(path/'GATE.json')
    assert complete['status']=='PASS' and complete['gate_sha256']==sha(path/'GATE.json')
    assert gate['status']=='PASS' and gate['sources']==sources() and gate['inputs_sha256']==sha(inputs)
    rows=read(inputs)['cases'];assert gate['cases']==[s['case'] for s in rows]
    assert all(r['status']=='PASS' and r['prefixes'] and r['plans'] for r in gate['checks'])
    return gate

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='mode',required=True)
    p=sub.add_parser('prepare');p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('check');p.add_argument('--inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if a.mode=='prepare':prepare(a.out);return
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.mkdir(exist_ok=False);frozen=sources();start=time.perf_counter()
    try:
        rows=read(a.inputs)['cases'];checks=[check_case(s) for s in rows]
        assert len({s['case'] for s in rows})==len(rows)==4 and sources()==frozen
        put(a.out/'GATE.json',{'status':'PASS','sources':frozen,'inputs_sha256':sha(a.inputs),
            'cases':[s['case'] for s in rows],'checks':checks,'elapsed_seconds':time.perf_counter()-start})
        put(a.out/'PROCESS_COMPLETE.json',{'status':'PASS','gate_sha256':sha(a.out/'GATE.json')})
    except BaseException:
        put(a.out/'FAILURE.json',{'error':traceback.format_exc()});raise
if __name__=='__main__':main()



