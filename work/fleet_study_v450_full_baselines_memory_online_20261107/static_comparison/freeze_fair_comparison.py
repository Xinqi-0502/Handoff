"""Seal source/inputs only after the complete published-engine correctness gate."""
from pathlib import Path
import hashlib,json,sys
P=Path(__file__).resolve().parent;R=P.parent;W=R.parent
sys.path.insert(0,str(R/'baseline_replication'));sys.path.insert(0,str(W/'fleet_study_v449_validation_and_online_20261107'))
import check_published_search_v450 as check
import scale_sources_v449 as old
G=R/'baseline_replication'/'gates'/'micro_all_02'/'GATE.json'
gate=check.validate_gate(G)
files=dict(gate['sources']);files.update(old.validate_sources())
for p in (G,Path(__file__),P/'run_fair_comparison.py',P/'generate_fair_inputs.py',P/'Prospective_Protocol.md'):
    files[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
inputs={s:hashlib.sha256((P/'inputs'/s/'INPUTS.json').read_bytes()).hexdigest() for s in ('cost','main')}
for s,count in (('cost',16),('main',256)):
    assert len(json.loads((P/'inputs'/s/'INPUTS.json').read_text()))==count
out=P/'Frozen_Source_Manifest.json'
with out.open('x',encoding='utf-8') as f:json.dump(dict(status='FROZEN',gate=str(G),files=files,inputs=inputs,methods=['RADIUS_PAIR_AWA_GATED','HZ_AWA_RADIUS','HZ_AWA_RADIUS_PAIR_GATED','ANA_RADIUS'],wall_ms=1000,main_repeats=3,main_cases=256,main_mothers=64,cost_cases=16,cost_repeats=1),f,indent=2)
print(json.dumps(dict(status='FROZEN',file=str(out),sha256=hashlib.sha256(out.read_bytes()).hexdigest())),flush=True)