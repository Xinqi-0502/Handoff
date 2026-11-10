"""Explicit correctness CLI only. Imports do not execute any search.
Root runs 6 batches of 4 micro cases, then assembles a full 24-case gate.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,math,sys,time,traceback
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
WORK=ROOT.parent
V448=WORK/'fleet_study_v448_radius_pair_prototype_20261107'
V447=WORK/'fleet_study_v447_random_high_load_20261107'
V449=WORK/'fleet_study_v449_validation_and_online_20261107'
MICRO=V447/'instances/micro_01/INPUTS.json'
METHODS=('HZ_AWA_RADIUS','HZ_AWA_RADIUS_PAIR_GATED','ANA_RADIUS','RADIUS_PAIR_AWA_GATED')
CAPS=(0.001,1,1000)
PINS={
 'domain':(V448/'selective_v448.py','f955dcb082a1e8fb4e683741a657c433209202f313571c07174d9ab15de42a6c'),
 'reference':(V448/'reference_v448.py','9810d96023a7710329d34a42f5c831687ea73e09fbfb42968fe4c660366a7416'),
 'dp':(V447/'independent_dp_v447.py','8c59f8695dfa2347b0f8ac5c817aec93c0c41e07c0882d45f099abaf4d9c2431')}

def require(ok,detail):
    if not ok:raise AssertionError(detail)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,data):Path(p).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def append(p,data):
    with Path(p).open('a',encoding='utf-8') as f:f.write(json.dumps(data,allow_nan=False)+'\n');f.flush()
def lines(p):return [json.loads(x) for x in Path(p).read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def fresh(p):
    p=(p if p.is_absolute() else ROOT/p).resolve()
    require(ROOT in p.parents and not p.exists(),'Fresh output under V450 required')
    p.mkdir(parents=True);return p

def sources():
    result={}
    for name,(p,expected) in PINS.items():
        actual=digest(p);require(actual==expected,('Frozen dependency changed',name));result[str(p)]=actual
    for p in (HERE/'published_search_v450.py',Path(__file__),MICRO):result[str(p)]=digest(p)
    require(result[str(MICRO)]==read(V449/'Scale_Source_Manifest.json')['inputs']['micro'],'Micro input pin changed')
    return result

def load_module(name,p):
    spec=importlib.util.spec_from_file_location(name,p);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module

def modules():
    sp=load_module('v450_check_domain',PINS['domain'][0])
    dp=load_module('v450_check_dp',PINS['dp'][0])
    pub=load_module('v450_published',HERE/'published_search_v450.py')
    pub.configure_domain(sp);return sp,dp,pub

class Toy:
    def __init__(self,which):
        self.which=which
        if which=='REOPEN':
            self.edges={'S':(('A',1),('B',2),('G',100)),'A':(('R',4),),'B':(('C',0),),'C':(('R',1),),'R':(('G',10),)}
            self.h={'S':0,'A':1,'B':5,'C':0,'R':0,'G':0}
        elif which=='REKEY':
            self.edges={'S':(('A',1),('B',2),('C',14),('G',100)),'A':(('G',19),),'B':(('G',10),),'C':(('G',4),)}
            self.h={'S':0,'A':0,'B':5,'C':2,'G':0}
        elif which=='PATHMAX_KEY':
            self.edges={'S':(('A',1),('G',100)),'A':(('C',1),('D',4)),'C':(('G',10),),'D':(('G',6),)}
            self.h={'S':0,'A':9,'C':0,'D':0,'G':0}
        else:raise ValueError(which)
    def initial(self):return ('S',0)
    def greedy(self):return 100,('G',)
    def successors(self,s):
        for node,edge in self.edges.get(s[0],()):yield (node,s[1]+edge),node
    def is_goal(self,s):return s[0]=='G'
    def g(self,s):return s[1]
    def lower_cost(self,s):return s[1]+self.h[s[0]]
    def dominance_key(self,s):return s[0]
    def dominance_vector(self,s):return (s[1],)
    def audit_state(self,s):return list(s)
    def exhaustive(self,node='S',cost=0):
        if node=='G':return cost
        return min(self.exhaustive(n,cost+w) for n,w in self.edges[node])
    def replay(self,plan):
        node='S';cost=0
        for target in plan:
            edges=[w for n,w in self.edges[node] if n==target]
            require(len(edges)==1,('Invalid toy action',node,target));cost+=edges[0];node=target
        require(node=='G','Incomplete toy plan');return cost

def toy_checks(pub):
    checks=[]
    expected={
      ('REOPEN','AWA'):(['S','A','R','B','C','R'],[100,15,13]),
      ('REOPEN','ANA'):(['S','A','R','B','C','R'],[100,15,13]),
      ('REKEY','AWA'):(['S','A','B'],[100,20,12]),
      ('REKEY','ANA'):(['S','A','B'],[100,20,12]),
      ('PATHMAX_KEY','AWA'):(['S','A','D','C'],[100,11])}
    for (name,algorithm),(order,values) in expected.items():
        domain=Toy(name);row=pub.search_domain(lambda:domain,algorithm,wall_ms=None,audit=True)
        require(row['objective_value']==domain.exhaustive() and row['certified_optimal'],'Toy oracle/certificate')
        require([x['state'][0] for x in row['audit_trace']]==order,('Handwritten expansion order',name,algorithm))
        require([x['cost'] for x in row['trace']]==values,('Handwritten improvements',name,algorithm))
        for x in row['trace']:require(domain.replay(x['plan'])==x['cost'],'Toy action replay')
        if name=='REOPEN':require(row['reopened']>=1,'Reopening fixture failed to reopen')
        if algorithm=='ANA':
            require(row['goal_pops']==2 and row['frontier_rekeys']==2 and row['rekey_labels']>=1,'ANA goal pop/rekey not exercised')
            require(all(x['event_kind']=='goal_pop' for x in row['trace'][1:]),'ANA wrong goal semantics')
        if name=='PATHMAX_KEY':
            require([x['lower'] for x in row['audit_trace']][1:]==[10,10,10],'Pathmax floor lost')
        row.pop('_started_clock',None);checks.append(dict(name=name,algorithm=algorithm,result=row))
    # At 3 complete expansions, ANA has generated but has not popped goal15.
    for algorithm,value in (('AWA',15),('ANA',100)):
        domain=Toy('REOPEN');row=pub.search_domain(lambda:domain,algorithm,wall_ms=None,node_limit=3,audit=True)
        require(row['objective_value']==value and row['lower_bound']==7 and not row['certified_optimal'],'Unweighted frontier/goal-pop budget fixture')
        row.pop('_started_clock',None);checks.append(dict(name='NODE3_UNWEIGHTED',algorithm=algorithm,result=row))
    return checks

def run_method(pub,sp,spec,method,cap):
    if method=='RADIUS_PAIR_AWA_GATED':
        row=sp.solve(spec,'AWA_GATED',sp.Watchdog(30),wall_ms=cap,profile=False,audit=False,checkpoints=(),basis='radius')
        row['method']=method;return row
    return pub.solve(spec,method,sp.Watchdog(30),wall_ms=cap,audit=False)

def check_result(sp,dp,spec,row,opt,cap,initial):
    lower=row['remaining_bound']
    require(row['H2']>=opt and (lower is None or lower<=opt),'Invalid feasible/certificate bound')
    require(row['certified_gap']==(None if lower is None else row['H2']-lower),'Certificate gap identity')
    require(row['certified_optimal']==(row['certified_gap']==0),'Certificate Boolean identity')
    require(not row['certified_optimal'] or row['H2']==opt,'False optimality certificate')
    require(row['expanded']==row['expanded_phase0']+row['expanded_phase1'],'Phase expansion accounting')
    require(abs(row['setup_seconds']+row['initial_seconds']+row['search_seconds']-row['elapsed_seconds'])<1e-6,'Timer partition')
    require(0<=row['root_bound_seconds']<=row['search_seconds']+1e-6,'Root timer scope')
    if cap is not None:require(abs(row['overrun_seconds']-max(0,row['elapsed_seconds']-cap/1000))<1e-6,'Soft-overrun accounting')
    require(row['trace'],'Missing feasible initialization')
    require((row['trace'][0]['H2'],tuple(row['trace'][0]['plan']))==initial,'Different initial plan/value')
    last_time=-1;last_value=math.inf
    for j,x in enumerate(row['trace']):
        require(last_time<=x['seconds']<=row['elapsed_seconds']+1e-6,'Trace time order')
        require(x['H2']<last_value and x['H2']>=opt,'Strict feasible improvement')
        require(sp.ref.replay_plan(spec,x['plan'],sp.Watchdog(30))==x['H2'],'Timed-network reference replay')
        require(dp.replay_plan(spec,x['plan'],max_seconds=30)==x['H2'],'Independent DP network/action replay')
        k=x['expansion_index'];completed=x['expansions_completed']
        require(0<=completed<=k<=row['expanded'],'Trace expansion range')
        if j==0:require(k==completed==0,'Initial trace indices')
        elif row['method']=='ANA_RADIUS':require(x['event_kind']=='goal_pop' and completed==k,'ANA goal-pop trace')
        else:require(completed==k-1,'AWA generated-goal trace')
        last_time=x['seconds'];last_value=x['H2']
    require(row['trace'][-1]['H2']==row['H2'] and row['trace'][-1]['plan']==row['plan'],'Final trace value/plan')
    return len(row['trace'])

def batch(args):
    require(0<=args.start<args.stop<=24 and args.stop-args.start<=4,'Run batches of 1..4 micro cases')
    run=fresh(args.run);active=None;started=time.perf_counter()
    try:
        frozen=sources();sp,dp,pub=modules();specs=read(MICRO)[args.start:args.stop]
        write(run/'PROTOCOL.json',dict(sources=frozen,methods=METHODS,start=args.start,stop=args.stop,timecaps_ms=CAPS,
            expected_solution_checks_per_case=16,scope='Correctness only; no timing inference'))
        write(run/'INPUTS.json',specs);toys=toy_checks(pub);write(run/'TOYS.json',toys)
        for spec in specs:
            active=spec['case'];clock=time.perf_counter()
            oracle=sp.ref.ReferenceOracle(spec,sp.Watchdog(30));opt=oracle.suffix(oracle.initial())
            independent=dp.solve(spec,max_seconds=30)
            require(independent['status']=='PASS' and independent['optimum_H2']==opt,'Separate exhaustive oracle vs independent topological DP')
            write(run/('ORACLE_'+str(active)+'.json'),dict(case=active,optimum_H2=opt,exhaustive_states=len(oracle.memo),dp=independent))
            initctx=sp.Context(spec,sp.Watchdog(30),False,basis='radius');iv,ip=initctx.greedy();initial=(iv,tuple(ip))
            total=0;replays=0
            for method in METHODS:
                for cap in (None,)+CAPS:
                    require(time.perf_counter()-clock<180,'Micro case total watchdog')
                    row=run_method(pub,sp,spec,method,cap)
                    n=check_result(sp,dp,spec,row,opt,cap,initial);total+=1;replays+=2*n
                    if cap is None:require(row['H2']==opt and row['certified_optimal'],'Unlimited search failed optimum')
                    append(run/'CHECKS.jsonl',dict(case=active,method=method,wall_ms=cap,trace_count=n,double_replays=2*n,result=row))
            append(run/'CASE_COMPLETE.jsonl',dict(case=active,status='PASS',solution_checks=total,double_replays=replays,exact_optimum=opt,initial_H2=iv))
            print(json.dumps(dict(case=active,status='PASS',solution_checks=total)),flush=True)
        require(sources()==frozen,'Sources changed during gate')
        result=dict(status='PASS',sources=frozen,start=args.start,stop=args.stop,cases=len(specs),toy_checks=len(toys),seconds=time.perf_counter()-started)
        write(run/'SUMMARY.json',result);write(run/'PROCESS_COMPLETE.json',result)
    except BaseException as exc:
        failure=dict(status='FAIL',case=active,error=repr(exc),traceback=traceback.format_exc())
        write(run/'FAILURE.json',failure);write(run/'PROCESS_COMPLETE.json',failure);raise

def validate_gate(path):
    path=Path(path);gate=read(path);require(gate['status']=='PASS','Gate failed')
    require(gate['sources']==sources(),'Gate source mismatch')
    require(gate['methods']==list(METHODS) and gate['timecaps_ms']==list(CAPS),'Gate methods/caps')
    expected=[s['case'] for s in read(MICRO)]
    require(len(gate['case_ids'])==24 and len(set(gate['case_ids']))==24 and set(gate['case_ids'])==set(expected),'Full unique micro coverage')
    for p,h in gate['evidence_sha256'].items():require(digest(p)==h,('Gate evidence changed',p))
    return gate

def assemble(args):
    out=fresh(args.out)
    try:
        frozen=sources();runs=read(args.runs_json);require(isinstance(runs,list) and runs,'Run list required')
        ids=[];evidence={};specs=read(MICRO)
        for item in runs:
            run=Path(item);run=(run if run.is_absolute() else ROOT/run).resolve()
            require(ROOT in run.parents,'Gate source folder must be V450')
            protocol=read(run/'PROTOCOL.json');done=read(run/'PROCESS_COMPLETE.json');summary=read(run/'SUMMARY.json')
            require(done==summary and done['status']=='PASS' and done['sources']==frozen,'Complete successful batch required')
            require(protocol['sources']==frozen and protocol['methods']==list(METHODS) and protocol['timecaps_ms']==list(CAPS),'Batch protocol differs')
            expected=[s['case'] for s in specs[protocol['start']:protocol['stop']]]
            completed=lines(run/'CASE_COMPLETE.jsonl');checks=lines(run/'CHECKS.jsonl')
            require([c['case'] for c in completed]==expected,'Batch case coverage')
            require(len(checks)==16*len(expected),'Batch check coverage')
            want={(case,method,cap) for case in expected for method in METHODS for cap in (None,)+CAPS}
            require({(c['case'],c['method'],c['wall_ms']) for c in checks}==want,'Exact method/cap matrix')
            require(all(c['status']=='PASS' and c['solution_checks']==16 and c['double_replays']>=32 for c in completed),'Incomplete per-case evidence')
            require(done['toy_checks']==7 and len(read(run/'TOYS.json'))==7,'Toy evidence missing')
            ids.extend(expected)
            for p in run.iterdir():
                if p.is_file():evidence[str(p)]=digest(p)
        require(len(ids)==24 and len(set(ids))==24 and set(ids)=={s['case'] for s in specs},'Exactly all 24 micro cases required')
        gate=dict(status='PASS',sources=frozen,methods=METHODS,timecaps_ms=CAPS,case_ids=ids,evidence_sha256=evidence,
            scope='24 micro optima, dual action/network replay, common greedy, 3 soft cutoffs, handwritten reopen/ANA-rekey/weighted-key fixtures',
            algorithm_runtime_correctness=True,performance_validated=False,freight_algorithm_reproduction=False)
        write(out/'GATE.json',gate);validate_gate(out/'GATE.json');write(out/'PROCESS_COMPLETE.json',dict(status='PASS',cases=24))
    except BaseException as exc:
        write(out/'FAILURE.json',dict(status='FAIL',error=repr(exc),traceback=traceback.format_exc()));raise

def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    b=sub.add_parser('batch');b.add_argument('--start',type=int,required=True);b.add_argument('--stop',type=int,required=True);b.add_argument('--run',type=Path,required=True)
    a=sub.add_parser('assemble');a.add_argument('--runs-json',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();batch(args) if args.command=='batch' else assemble(args)
if __name__=='__main__':main()
