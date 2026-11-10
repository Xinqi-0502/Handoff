"""Freeze unseen V450 static cases without running any search."""
from pathlib import Path
import importlib.util, hashlib, json, sys
P=Path(__file__).resolve().parent
W=P.parents[1]
G=W/'fleet_study_v447_random_high_load_20261107'/'instances_v447.py'
assert hashlib.sha256(G.read_bytes()).hexdigest()=='a2e8b402e0c913c371c4d37107b23ff934a91df98fecc58b8f3274cb791e2329'
x=importlib.util.spec_from_file_location('v450_generator',G);g=importlib.util.module_from_spec(x);sys.modules[x.name]=g;x.loader.exec_module(g)
oldfiles=[W/'fleet_study_v449_validation_and_online_20261107'/'instances'/f'scale_{s}_01'/'INPUTS.json' for s in ('cost','main')]
prior=set(s['seed'] for f in oldfiles for s in json.loads(f.read_text(encoding='utf-8-sig')))
seen=set(prior)
for split,base,count in [('cost',94510000,1),('main',94500000,16)]:
    p=P/'inputs'/split
    assert not p.exists(), 'Inputs cannot be overwritten'
    cases=[s for m in (6,8,10,12) for i in range(1,count+1) for s in g.variants(base+1000*m+i,m,'v450_fair_'+split)]
    seeds={s['seed'] for s in cases};assert not seeds&seen;seen|=seeds
    checks=g.verify_pairs(cases)
    p.mkdir(parents=True)
    def save(name,value):(p/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    save('INPUTS.json',cases);save('PAIR_CHECKS.json',checks)
    save('PROTOCOL.json',dict(status='STRUCTURAL_INPUT_FREEZE',split=split,mothers=len(seeds),cases=len(cases),seed_rule=f'{base}+1000*m+i; i=1..{count}',sizes=[6,8,10,12],outcome_selection=False,disjoint_from_cost_main_and_V449=True,generator=str(G),generator_sha256=hashlib.sha256(G.read_bytes()).hexdigest(),input_sha256=hashlib.sha256((p/'INPUTS.json').read_bytes()).hexdigest(),scope='Local two-atomic-handoff H2, deterministic FIFO; not native SUMO'))
    print(json.dumps(dict(split=split,mothers=len(seeds),cases=len(cases))),flush=True)