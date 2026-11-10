"""Freeze memory-only inputs/configuration after static and upstream gates; no solving."""
from pathlib import Path
import argparse,json,sys
from memory_common import *
EXTERNAL_SHA='4d4286ad650f52264375bda90cf1a7c0c907eaa57df4396b58f959d7313b951c'

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--external-gate',type=Path,required=True);ap.add_argument('--safety-gate',type=Path,required=True);ap.add_argument('--out',type=Path,default=P/'freeze_01');a=ap.parse_args()
    out=a.out.resolve();require(out==P/'freeze_01','Version-one paths are fixed; preserve existing freeze');require(not out.exists(),'Fresh freeze required')
    external=P.parent/'baseline_replication'/'published_search_v450.py';require(sha(external)==EXTERNAL_SHA,'Reviewed external source changed')
    exgate=load(a.external_gate);require(exgate['status']=='PASS' and EXTERNAL_SHA in json.dumps(exgate).lower(),'Published runtime gate missing or source mismatch')
    safety=load(a.safety_gate);require(safety['status']=='PASS','Counter/lifecycle gate missing')
    for f,h in safety['sources'].items():require(sha(f)==h,'Counter/lifecycle source changed')
    upstream=load(V449/'Scale_Source_Manifest.json');sources=dict(upstream['sources'])
    for f,h in sources.items():require(sha(f)==h,'Frozen upstream source changed')
    sources.update({str(P/n):sha(P/n) for n in LOCAL});sources[str(external)]=EXTERNAL_SHA
    fullpath=V449/'instances/scale_main_01/INPUTS.json';micro_path=V447/'instances/micro_01/INPUTS.json'
    require(sha(fullpath)==upstream['inputs']['main'] and sha(micro_path)==upstream['inputs']['micro'],'Frozen parent input identity')
    full=load(fullpath);micro=load(micro_path);selected=[full[i] for base in (0,100,200,300) for i in range(base,base+8)]
    require(len(selected)==32 and len({s['seed'] for s in selected})==8,'32-scenario/8-mother selection')
    require([len(s['old']) for s in selected]==[m for m in (6,8,10,12) for _ in range(8)],'Scale selection')
    small=[micro[8]];require(len(small[0]['old'])==4,'Micro selection')
    out.mkdir(parents=True);dump(out/'INPUTS.json',selected);dump(out/'MICRO.json',small)
    manifest=dict(status='FROZEN',sources=sources,inputs={str(p):sha(p) for p in (fullpath,micro_path,out/'INPUTS.json',out/'MICRO.json')},
        primary_methods=list(PRIMARY),external_methods=list(EXTERNAL),external_module=str(external),common_external_import_ready=True,
        parent_main_sha256=sha(fullpath),parent_gate=str(V449/'gates/scale_micro_all_01/GATE.json'),external_gate=str(a.external_gate.resolve()),external_gate_sha256=sha(a.external_gate),
        safety_gate=str(a.safety_gate.resolve()),safety_gate_sha256=sha(a.safety_gate),selection='First two mothers per scale, all four capacity/signal conditions; original indexes 0:8,100:108,200:208,300:308; no outcome selection',
        micro_selection='Original micro index 8, m4; independent small exhaustive wrapper check',semantics=memory_semantics(),
        superseded_original_design=dict(primary_calls=576,external_calls=192,total_calls=768),main_design=dict(methods=['RADIUS_PAIR_AWA_GATED','HZ_AWA_RADIUS','HZ_AWA_RADIUS_PAIR_GATED','ANA_RADIUS'],repeats=1,calls=128),scope_amendment='Cost-driven, before any solver memory result; original design preserved in snapshots',main_requires_cost_approval=True)
    dump(out/'MANIFEST.json',manifest);jobsdir=out/'jobs';jobsdir.mkdir();configs={}
    for stage,indices,repeats,methods in (('correctness',[0],1,PRIMARY+EXTERNAL),('pilot',[0,8,16,24],1,PRIMARY),('main',list(range(32)),1,('RADIUS_PAIR_AWA_GATED','HZ_AWA_RADIUS','HZ_AWA_RADIUS_PAIR_GATED','ANA_RADIUS'))):
        paths=[];runs=[]
        for index in indices:
            run=P/'runs'/f'{stage}_{index:02d}_01';job=dict(stage=stage,run=str(run),manifest=str(out/'MANIFEST.json'),inputs=str(out/('MICRO.json' if stage=='correctness' else 'INPUTS.json')),offset=index,count=1,methods=list(methods),repeats=repeats,wall_ms=1000,hard_seconds=15,
                safety_gate=str(a.safety_gate.resolve()),correctness_gate=str(P/'gates/wrapper_all_01/GATE.json'),cost_approval=str(P/'Cost_Approval_01.json'))
            path=jobsdir/f'{stage}_{index:02d}.json';dump(path,job);paths.append(str(path));runs.append(str(run))
        config=out/f'{stage}_jobs.json';dump(config,dict(stage=stage,run=str(P/'runs'/f'{stage}_coordinator_01'),jobs=paths));dump(out/f'{stage}_selected.json',runs);configs[stage]=str(config)
    manifest['job_sha256']={str(f):sha(f) for f in jobsdir.glob('*.json')}
    manifest['config_sha256']={path:sha(path) for path in configs.values()}
    dump(out/'MANIFEST.json',manifest)
    dump(out/'FREEZE_COMPLETE.json',dict(status='PREPARED_NOT_EXECUTED',manifest_sha256=sha(out/'MANIFEST.json'),configs=configs,source_count=len(sources),cases=32,mothers=8))
    print(json.dumps(configs,indent=2))
if __name__=='__main__':main()

