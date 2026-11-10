"""Independent small correctness gate and immutable input preparation; no SUMO run.
Run with -B. check is exhaustive on the 24 newly prepared V450 micro states.
The reference uses its own action/load recurrence and the frozen forecast leg,
not production children, bounds, search or its plan forecast.
"""
from pathlib import Path
import argparse,hashlib,json,sys,time,traceback
import online_model_v450 as model
import published_online_v450 as published
import native_online_v450  # same source closure in check and execution entry points
ROOT=Path(__file__).resolve().parent

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,indent=2,ensure_ascii=False,allow_nan=False)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sources():
    paths=set(ROOT.glob('*.py'))
    paths.add(ROOT.parent/'baseline_replication'/'published_search_v450.py')
    paths.add(model.WORK/'fleet_study_v449_validation_and_online_20261107'/'validation'/'san_pablo_dam'/'run_public_validation.py')
    for module in tuple(sys.modules.values()):
        raw=getattr(module,'__file__',None)
        if raw:
            p=Path(raw).resolve()
            if p.suffix=='.py' and p.is_relative_to(model.WORK):paths.add(p)
    paths.add(model.WORK/'fleet_study_v419_signal_pedestrian_traffic_20261104'/'turn2_legs.json')
    paths.update(model.old.NET/f'cycle_{o}.net.xml' for o in (0,24))
    return {str(p):sha(p) for p in sorted(paths)}

def reference(snapshot):
    """All legal complete routes, exact independent forecast prefix states and costs."""
    c=snapshot['c'];w=snapshot['wave2'];E=float(model.old.E);service=4.;transfer=2.
    sig=model.old.ShortForecast(snapshot['offset'],snapshot['obs'],'COARSE')
    def leg(t,p,q,speed=8):
        try:return sig.leg(t,p,q,speed,model.old.MATRIX,True,[])
        finally:sig.relevant.clear()
    jobs={v:tuple(model.old.items(c,v)) for v in c['actors']}
    fixed={}
    for v in c['actors']:
        first,*todo=jobs[v];seq=[first];at=c['old'][first]
        while todo:
            j=min(todo,key=lambda j:(model.old.MATRIX[at][c['old'][j]][0],j))
            seq.append(j);todo.remove(j);at=c['old'][j]
        fixed[v]=tuple(seq)
    others={}
    for v,seq in fixed.items():
        t=E;pos=c['old'][seq[0]];val=0.
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
                if phase==0 and len(remaining)<len(pending) and load+w['orders']['a']['weight']<=snapshot['capacity'][v]:options.append('Xa')
                if phase==1:
                    if not adone:options.append('a')
                    if load+w['orders']['b']['weight']<=snapshot['capacity'][v]:options.append('Xb')
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
            walk((initial,),E,c['old'][initial],pending,0,False,False,2*E,None)
    return prefixes,leaves,h2min,clocks

def check_case(s):
    prefixes,leaves,h2min,clocks=reference(s);ctx=model.Context(s);exact=model.Context(s,'exact');seen=set();terminal={};strong=cuts=0
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
            route=exact.bound(state,False)
            assert base<=route+1e-6 and route<=truth+1e-6
            for U in {base-.0001,base,base+.0001,joint-.0001,joint,joint+.0001,truth}:
                if 'Xa' not in state.tokens:
                    assert ctx.pair_cutoff(state,U,base)==(joint>U+model.EPS),(s['case'],state,U,base,joint)
                    cuts+=1
            if 'Xa' not in state.tokens:
                _,hbase,hpair=ctx.h2_bounds(state)
                assert hbase<=hpair+1e-7 and hpair<=h2min[key]+1e-6
            if ctx.terminal(state):
                p=ctx.plan(state);keyp=model.signature(p);pred=ctx.forecast(p)['J']
                assert abs(pred-truth)<1e-6 and abs(joint-truth)<1e-6
                terminal[keyp]=pred
            else:
                children=ctx.children(state)
                for child in children:
                    childtruth=prefixes[b,child.tokens]
                    assert max(base,ctx.bound(child,False))<=childtruth+1e-6
                stack.extend(children)
    assert seen==set(prefixes) and set(terminal)==set(leaves)
    opt=min(v[0] for v in leaves.values());solves={}
    for arm in model.ARMS:
        r=model.solve(s,arm,per_branch_cap=6,wall_seconds=None)
        counts=list(r['per_branch_forecasts'].values())
        assert len(counts)==4 and all(1<=n<=6 for n in counts)
        assert r['counts']['full_forecasts']==sum(counts)
        assert r['J']>=opt-1e-6 and sum(counts)<=24
        assert ctx.legal(r['plan']) and abs(ctx.forecast(r['plan'])['J']-r['J'])<1e-6
        solves[arm]=r
    for arm in model.ARMS:
        r=model.solve(s,arm,per_branch_cap=len(leaves)+1,wall_seconds=None)
        assert r['certified_forecast_optimal'] and abs(r['J']-opt)<1e-6
    for arm in published.METHODS:
        r=published.solve(s,arm,wall_seconds=None,audit=True)
        assert r['certified_forecast_optimal'] and abs(r['J']-opt)<1e-6
        assert ctx.legal(r['plan']) and abs(ctx.forecast(r['plan'])['J']-r['J'])<1e-6
        stop=published.solve(s,arm,wall_seconds=None,node_limit=0)
        assert stop['counts']['expanded']==0 and ctx.legal(stop['plan'])
        solves[arm]=r
    initial={model.signature(x['initial']['plan']) for x in solves.values()}
    assert len(initial)==1
    return {'case':s['case'],'status':'PASS','prefixes':len(seen),'plans':len(leaves),
            'strict_pair_prefixes':strong,'cutoff_equivalence_checks':cuts,'optimum_J':opt,
            'initial_is_optimal':abs(next(iter(solves.values()))['initial']['J']-opt)<1e-6,'fixed24':solves}

def validate_gate(path,inputs=None):
    path=Path(path)
    if (path/'FAILURE.json').exists():raise ValueError('Failed gate')
    complete=read(path/'PROCESS_COMPLETE.json');gate=read(path/'GATE.json')
    assert complete['status']=='PASS' and complete['gate_sha256']==sha(path/'GATE.json')
    assert gate['status']=='PASS' and gate['sources']==sources()
    if inputs is not None:assert gate['inputs_sha256']==sha(inputs)
    assert len(gate['cases'])==24 and len(set(gate['cases']))==24
    assert all(r['status']=='PASS' and r['prefixes'] and r['plans'] for r in gate['checks'])
    return gate

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='mode',required=True)
    p=sub.add_parser('check');p.add_argument('--inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.mkdir(exist_ok=False);frozen=sources();start=time.perf_counter()
    try:
        rows=read(a.inputs)['cases'];checks=[check_case(s) for s in rows]
        assert len({s['case'] for s in rows})==len(rows)==24 and sources()==frozen
        put(a.out/'GATE.json',{'status':'PASS','sources':frozen,'inputs_sha256':sha(a.inputs),
            'cases':[s['case'] for s in rows],'checks':checks,'micro_mothers':len({s['seed'] for s in rows}),'elapsed_seconds':time.perf_counter()-start})
        put(a.out/'PROCESS_COMPLETE.json',{'status':'PASS','gate_sha256':sha(a.out/'GATE.json')})
    except BaseException:
        put(a.out/'FAILURE.json',{'error':traceback.format_exc()});raise
if __name__=='__main__':main()



