"""Freeze new V449 inputs only. No numerical solver is imported."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys
P=Path(__file__).resolve().parent
V447=P.parent/'fleet_study_v447_random_high_load_20261107'
V448=P.parent/'fleet_study_v448_radius_pair_prototype_20261107'
SOURCE=V447/'instances_v447.py'
SOURCE_SHA='a2e8b402e0c913c371c4d37107b23ff934a91df98fecc58b8f3274cb791e2329'
SIZES=(6,8,10,12)
CONFIG={'main':(94490000,25),'cost':(94480000,2)}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def generate(split):
 assert sha(SOURCE)==SOURCE_SHA
 spec=importlib.util.spec_from_file_location('v449_frozen_generator',SOURCE)
 g=importlib.util.module_from_spec(spec);sys.modules[spec.name]=g;spec.loader.exec_module(g)
 namespace,count=CONFIG[split]
 cases=[s for m in SIZES for i in range(1,count+1) for s in g.variants(namespace+1000*m+i,m,'v449_scale_'+split)]
 checks=g.verify_pairs(cases)
 prior=[V447/'instances'/x/'INPUTS.json' for x in ('micro_01','pilot_01','main_01')]+[V448/'instances/pilot_01/INPUTS.json']
 oldseeds=set();oldhashes={}
 for f in prior:
  data=json.loads(f.read_text(encoding='utf-8-sig'));oldseeds.update(s['seed'] for s in data);oldhashes[str(f)]=sha(f)
 seeds={s['seed'] for s in cases}
 assert not seeds&oldseeds and len(seeds)==4*count and len(cases)==16*count
 other_namespace,other_count=CONFIG['cost' if split=='main' else 'main']
 assert not seeds&{other_namespace+1000*m+i for m in SIZES for i in range(1,other_count+1)}
 return cases,checks,oldhashes
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('split',choices=CONFIG)
 args=ap.parse_args();out=P/'instances'/('scale_'+args.split+'_01')
 assert not out.exists(),'Preserve previous inputs'
 cases,checks,oldhashes=generate(args.split);out.mkdir(parents=True)
 for name,obj in (('INPUTS.json',cases),('PAIR_CHECKS.json',checks)):
  (out/name).write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
 namespace,count=CONFIG[args.split]
 protocol=dict(status='GENERATED_STRUCTURAL_ONLY_NO_SOLVER',split=args.split,sizes=SIZES,
  seed_rule=f'{namespace}+1000*m+i, i=1..{count}',independent_mothers=len(cases)//4,
  related_scenarios=len(cases),related_variants_per_mother=4,source_sha256=SOURCE_SHA,
  generator_sha256=sha(Path(__file__)),input_sha256=sha(out/'INPUTS.json'),prior_input_sha256=oldhashes,
  disjoint_from_all_read_prior_seeds=True,cost_main_seed_disjoint=True,no_outcome_filtering=True,
  distributions='Frozen V447 generator; Q=L or ceil1.25L, wa=.6L, wb=.8L; capacity/signal paired',
  scope='Fixed receiver/hub, two atomic incoming batches, H2, uncalibrated synthetic FIFO network; no SUMO')
 (out/'PROTOCOL.json').write_text(json.dumps(protocol,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(protocol))
if __name__=='__main__':main()
