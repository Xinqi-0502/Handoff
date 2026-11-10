"""Run all six small published-engine gate blocks serially under one monitor."""
from pathlib import Path
from types import SimpleNamespace
import hashlib,json,sys
ROOT=Path(__file__).resolve().parent.parent
B=ROOT/'baseline_replication';sys.path.insert(0,str(B))
assert hashlib.sha256((B/'published_search_v450.py').read_bytes()).hexdigest()=='4d4286ad650f52264375bda90cf1a7c0c907eaa57df4396b58f959d7313b951c'
assert hashlib.sha256((B/'check_published_search_v450.py').read_bytes()).hexdigest()=='05b5cc5481688639f1f59a24799cb4d39eec2fdea921d4008aadb685483df1b0'
import check_published_search_v450 as check
runs=[]
for start in range(0,24,4):
    run=B/'checks'/f'micro_b{start:02d}_01'
    check.batch(SimpleNamespace(start=start,stop=start+4,run=run))
    runs.append(str(run))
p=ROOT/'records'/'Selected_Published_Gate_Blocks_01.json'
with p.open('x',encoding='utf-8') as f:json.dump(runs,f,indent=2)
check.assemble(SimpleNamespace(runs_json=p,out=B/'gates'/'micro_all_01'))
print('FULL_PUBLISHED_GATE_PASS',flush=True)