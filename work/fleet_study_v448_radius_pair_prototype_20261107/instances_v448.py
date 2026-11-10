"""V448 fixed fresh exploratory inputs. Generation only; no solver import."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/"fleet_study_v447_random_high_load_20261107"
SOURCE=PARENT/"instances_v447.py"
SOURCE_SHA256="a2e8b402e0c913c371c4d37107b23ff934a91df98fecc58b8f3274cb791e2329"
SIZES=(6,8,10,12)
SEEDS={m:tuple(9480000+1000*m+i for i in (1,2)) for m in SIZES}
SPLIT="v448_radius_pilot"

def frozen_generator():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA256:
        raise ValueError("Frozen generator source hash changed.")
    spec=importlib.util.spec_from_file_location("v448_frozen_input_generator",SOURCE)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

def generate():
    source=frozen_generator()
    cases=[s for m in SIZES for seed in SEEDS[m]
           for s in source.variants(seed,m,SPLIT)]
    pairs=source.verify_pairs(cases)
    assert len(cases)==32 and len({s["seed"] for s in cases})==8
    assert len({s["case"] for s in cases})==32
    assert all(s["split"]==SPLIT for s in cases)
    return cases,pairs

def freeze(out):
    out=Path(out).resolve()
    if HERE not in out.parents or out.exists():
        raise ValueError("Use a fresh V448 descendant; preserve frozen inputs.")
    cases,pairs=generate()
    out.mkdir(parents=True,exist_ok=False)
    for name,value in (("INPUTS.json",cases),("PAIR_CHECKS.json",pairs)):
        (out/name).write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")
    protocol=dict(status="GENERATED_STRUCTURAL_ONLY_NOT_SOLVER_VALIDATED",
        sizes=list(SIZES),seed_rule="9480000 + 1000*m + i; i in {1,2}",
        seeds=SEEDS,independent_mothers=8,independent_mothers_per_scale=2,
        related_variants_per_mother=4,related_scenarios=32,
        split=SPLIT,source_formula="Frozen V447 mother/variants/verify_pairs",
        inherited_generator_sha256=SOURCE_SHA256,
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        inputs_sha256=hashlib.sha256((out/"INPUTS.json").read_bytes()).hexdigest(),
        no_solver_executed=True,no_outcome_filtering=True,
        formal_results_read=False,
        scope="Exploratory cost/mechanism pilot; fixed receiver/hub, atomic a before b, H2 only",
        paired_axes=["capacity","signal"],units="Uncalibrated integer ticks/cargo")
    (out/"PROTOCOL.json").write_text(json.dumps(protocol,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(status=protocol["status"],inputs_sha256=protocol["inputs_sha256"],
                         scenarios=32,independent_mothers=8)),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,default=HERE/"instances"/"pilot_01")
    freeze(p.parse_args().out)

