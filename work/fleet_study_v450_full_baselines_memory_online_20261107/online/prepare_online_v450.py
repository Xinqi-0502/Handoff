"""Predeclared V450 inputs and native-prefix preparation; never run at import.
Definitions is deterministic data generation only. Prefix mode runs SUMO and
must be scheduled by root under the reviewed thermal/owned-process host.
"""
from pathlib import Path
import argparse,hashlib,json,itertools,random,traceback
import online_model_v450 as model
ROOT=Path(__file__).resolve().parent
MOTHERS=tuple(range(4509001,4509009));BUDGETS=(.01,.05,.2)

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,indent=2,ensure_ascii=False,allow_nan=False)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def case(seed,offset,people,slow,n=8,Q=12):
    rng=random.Random(seed);pool=[s+b+t for s in 'WE' for b in 'UD' for t in 'uvx'];old={};sizes={};starts={}
    for v in ('A','B'):
        first=rng.choice([site for site in pool if site!=old.get('a0')])
        destinations=[first]+rng.sample([site for site in pool if site!=first],n-1)
        weights=[1]*(n-1)
        for i in range(12-n):weights[i%len(weights)]+=1
        rng.shuffle(weights)
        for i,(dest,w) in enumerate(zip(destinations,[1]+weights)):
            old[v.lower()+str(i)]=dest;sizes[v.lower()+str(i)]=w
        starts[v]=v+'in'+rng.choice('WE')
    wave=model.old.reveal(seed);a=wave['i'];b='ME' if a=='MW' else 'MW'
    return dict(case=f's{seed}_n{n}_q{Q}_o{offset}_p{people}_f{slow}',seed=seed,offset=offset,people=people,slow=slow,
        epoch=6.,capacity={'A':Q,'B':Q},c=dict(seed=seed,actors=['A','B'],old=old,size=sizes,start=starts,slow=slow),
        wave2={'T':wave['T'],'release':6.,'orders':{'a':{'dest':a,'weight':8},'b':{'dest':b,'weight':10}}})
def definitions(out):
    rows=[case(seed,o,p,q) for seed in MOTHERS for o,p,q in itertools.product((0,24),(0,10),(0,2))]
    put(out,dict(schema='V450-fixed64-native-single-epoch-v1',mothers=list(MOTHERS),budgets=list(BUDGETS),
        cases=rows,pilot_cases=[x['case'] for x in rows if x['seed']==MOTHERS[0] and x['people']==10 and x['slow']==2],
        primary_arms=['HZ_AWA_RADIUS','HZ_AWA_PAIR_GATED'],auxiliary_arms_50ms=['RADIUS','ROUTE','ANA_RADIUS'],
        external_baselines='Complete Hansen-Zhou AWA and complete ANA search engines adapted to this J domain; not a freight-paper replication',
        technical_repeats=3,physical_selection='For each distinct selected plan among three repetitions, choose its median-latency repetition (lower middle for two, then repetition ID); replay once. Preserve all plans.',
        scope='One frozen decision epoch. Full continuous two-epoch rolling execution is not implemented in this stage.'))
def micro(out):
    rows=[]
    for seed,n,Q,o in itertools.product((4509901,4509902,4509903),(3,4),(12,16),(0,24)):
        s=case(seed,o,0,0,n,Q)
        s['ctx']={v:dict(remaining_cm=0,ready=6*model.old.SCALE) for v in ('A','B')}
        s['obs']={e:dict(category=('slow' if seed%2 else 'moving')) for e in ('WC','EC')}
        rows.append(s)
    put(out,dict(schema='V450-unselected-small-exhaustive-gate-v1',cases=rows,
        purpose='24 fixed micro states, 3 mother seeds; synthetic public observations, not native traffic validation'))
def prefixes(inputs,out,pilot=False):
    import native420 as native
    import gzip
    frozen=sha(inputs);data=read(inputs);rows=data['cases']
    if pilot:rows=[s for s in rows if s['case'] in data['pilot_cases']]
    out.mkdir(parents=True,exist_ok=False);records=[]
    try:
        from check_online_v450 import sources
        source=sources();put(out/'PROTOCOL.json',dict(sources=source,input_sha256=frozen,pilot=pilot,cases=[s['case'] for s in rows]))
        for row in rows:
            s=dict(row);dest=out/s['case'];h=native.simulate(s['c'],bool(s['people']),dest,offset=s['offset'])
            with gzip.open(dest/'trace.jsonl.gz','rt',encoding='utf8') as stream:fs=[json.loads(line) for line in stream]
            assert len(fs)==30 and fs[-1]['tick']==30 and len(fs[-1]['people'])==s['people']
            s.update(ctx=h['epoch_context'],prefix=h['prefix'],xml=sha(dest/'old_batch.rou.xml'),obs=model.old.summary(fs,s['offset']))
            records.append(s)
        assert sha(inputs)==frozen and sources()==source
        put(out/'INPUTS.json',dict(schema='V450-native-prefix-snapshots-v1',cases=records,source_inputs_sha256=frozen))
        put(out/'PROCESS_COMPLETE.json',dict(status='PASS',input_sha256=sha(out/'INPUTS.json'),cases=len(records),sources=source))
    except BaseException:put(out/'FAILURE.json',dict(error=traceback.format_exc()));raise

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
    for mode in ('definitions','micro'):
        q=sub.add_parser(mode);q.add_argument('--out',type=Path,required=True)
    q=sub.add_parser('prefix');q.add_argument('--inputs',type=Path,required=True);q.add_argument('--out',type=Path,required=True);q.add_argument('--pilot',action='store_true')
    a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True)
    if a.mode=='definitions':definitions(a.out)
    elif a.mode=='micro':micro(a.out)
    else:prefixes(a.inputs,a.out,a.pilot)
if __name__=='__main__':main()
