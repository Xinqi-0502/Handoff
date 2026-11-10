"""V447 random high-load synthetic instances. Generation only; no solver import."""
from __future__ import annotations
import argparse,copy,hashlib,json,math,random,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
SIZES=(6,8,10,12)
PILOT_SEEDS={m:tuple(4470000+100*m+i for i in (1,2)) for m in SIZES}
MAIN_SEED_RESERVATION="8470000 + 1000*m + index (index 1..999); default formal count 25 per scale, frozen before outcomes"
MODEL_KEYS=("n_nodes","edges","hub","a_node","start_node","t0","A","Q","wa","wb",
            "a_service","tau_a","tau_b","old")

def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def positive_partition(total,count,rng):
    draws=[rng.randint(1,12) for _ in range(count)]
    budget=total-count;den=sum(draws)
    weights=[1+(budget*d)//den for d in draws]
    order=sorted(range(count),key=lambda i:((budget*draws[i])%den,-i),reverse=True)
    for i in order[:total-sum(weights)]:weights[i]+=1
    if len(set(weights))==1:
        # Declared non-equal cargo design, independent of any solver outcome.
        weights[0]+=1;weights[-1]-=1
    assert sum(weights)==total and min(weights)>0
    return weights

def mother(seed,m):
    if m not in SIZES and m not in (3,4,5):
        raise ValueError("This frozen generator supports validation m3/4/5 and pilot m6/8/10/12.")
    geo=random.Random(seed*1009+1)
    road=random.Random(seed*1009+2)
    calendar=random.Random(seed*1009+3)
    cargo=random.Random(seed*1009+4)
    service=random.Random(seed*1009+5)
    coords=[(0,0)]
    while len(coords)<m+2:
        point=(geo.randint(-50,50),geo.randint(-50,50))
        if point not in coords:coords.append(point)
    n=len(coords)
    # A bidirectional geometric ring guarantees strong connectivity. Nearest
    # neighbor arcs and prespecified random cross-links add directed alternatives.
    arcs=set()
    ring=sorted(range(n),key=lambda u:(math.atan2(coords[u][1],coords[u][0]),u))
    for i,u in enumerate(ring):
        v=ring[(i+1)%n];arcs.add((u,v));arcs.add((v,u))
    for u in range(n):
        nearest=sorted((v for v in range(n) if v!=u),
                       key=lambda v:((coords[u][0]-coords[v][0])**2+(coords[u][1]-coords[v][1])**2,v))
        for v in nearest[:3]:arcs.add((u,v))
        for v in range(n):
            if u!=v and road.random()<0.10:arcs.add((u,v))
    edges=[]
    for u,v in sorted(arcs):
        distance=math.hypot(coords[u][0]-coords[v][0],coords[u][1]-coords[v][1])
        travel=max(1,math.ceil(distance/3))+road.randint(0,5)
        if calendar.random()<0.55:
            period=calendar.choice((12,24,48))
            green=period*calendar.choice((1,2,3))//4
            offset=calendar.randrange(period)
        else:period=green=offset=0
        edges.append([u,v,travel,period,green,offset])
    load=cargo.choice((120,160,200))
    weights=positive_partition(load,m,cargo)
    old=[dict(node=i+2,weight=weights[i],service=service.randint(2,12)) for i in range(m)]
    t0=service.randrange(48)
    return dict(seed=seed,m=m,n_nodes=n,coordinates=[list(p) for p in coords],
                edges=edges,hub=0,a_node=1,start_node=0,t0=t0,A=t0+service.randint(0,12),
                wa=3*load//5,wb=4*load//5,a_service=service.randint(3,10),
                tau_a=service.randint(2,5),tau_b=service.randint(2,5),old=old,
                total_old_weight=load,total_old_service=sum(o["service"] for o in old))

def variants(seed,m,split="pilot"):
    base=mother(seed,m)
    result=[]
    for regime in ("tight","roomier"):
        Q=base["total_old_weight"] if regime=="tight" else (5*base["total_old_weight"]+3)//4
        for signals in (False,True):
            spec=copy.deepcopy(base)
            spec.update(case=f"{split}_s{seed}_m{m}_{regime}_{'signal' if signals else 'free'}",
                        split=split,Q=Q,capacity_regime=regime,signal=signals,
                        geometry="random_2d",control=False,
                        pair_id=f"{split}_s{seed}_m{m}_{regime}",
                        signal_pair_id=f"{split}_s{seed}_m{m}_{regime}",
                        capacity_pair_id=f"{split}_s{seed}_m{m}_{'signal' if signals else 'free'}",
                        generation="Prespecified random high-load FIFO synthetic transport",
                        atomic_incoming_order=["a","b"],units="Uncalibrated integer ticks and cargo units")
            if not signals:
                for e in spec["edges"]:e[3:]=[0,0,0]
            result.append(spec)
    return result

def pilot_suite():
    return [s for m in SIZES for seed in PILOT_SEEDS[m] for s in variants(seed,m)]

def small_validation_suite():
    # Independent from pilot and reserved main seeds; no output or solve on import.
    return [s for m in (3,4,5) for i in (1,2)
            for s in variants(3470000+100*m+i,m,"micro")]

def normalized(spec,axis):
    obj={k:copy.deepcopy(spec[k]) for k in MODEL_KEYS}
    if axis=="capacity":obj.pop("Q")
    elif axis=="signal":
        for e in obj["edges"]:e[3:]=[0,0,0]
    else:raise ValueError(axis)
    return obj

def verify_pairs(specs):
    checks=[]
    for s in specs:
        assert s["n_nodes"]==len(s["old"])+2
        assert sum(o["weight"] for o in s["old"])==s["total_old_weight"]<=s["Q"]
        assert 0<s["wa"]<s["wb"]<=s["Q"] and s["wa"]+s["wb"]>s["Q"]
        assert len({o["weight"] for o in s["old"]})>1
        assert all(o["weight"]>0 and o["service"]>0 for o in s["old"])
        assert s["t0"]<=s["A"] and min(s["tau_a"],s["tau_b"],s["a_service"])>0
        assert all(e[2]>0 and (e[3]==0 or 1<=e[4]<=e[3]) for e in s["edges"])
        # Directed structural connectivity only; not a shortest-path/oracle run.
        adj={u:[] for u in range(s["n_nodes"])}
        for u,v,*_ in s["edges"]:adj[u].append(v)
        for start in adj:
            reached={start};todo=[start]
            while todo:
                for v in adj[todo.pop()]:
                    if v not in reached:reached.add(v);todo.append(v)
            assert len(reached)==s["n_nodes"]
    for axis,key in (("signal","signal_pair_id"),("capacity","capacity_pair_id")):
        groups={}
        for s in specs:groups.setdefault(s[key],[]).append(s)
        for pid,pair in sorted(groups.items()):
            assert len(pair)==2 and normalized(pair[0],axis)==normalized(pair[1],axis)
            checks.append(dict(axis=axis,pair_id=pid,normalized_model_hash=digest(normalized(pair[0],axis)),
                               instance_hashes={s["case"]:digest(s) for s in pair}))
    return checks

def freeze_pilot():
    out=HERE/"instances"/"pilot_01"
    if out.exists():raise ValueError("Preserve existing generated inputs.")
    specs=pilot_suite();checks=verify_pairs(specs)
    out.mkdir(parents=True,exist_ok=False)
    for name,obj in (("INPUTS.json",specs),("PAIR_CHECKS.json",checks)):
        (out/name).write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
    protocol=dict(status="GENERATED_AND_STRUCTURALLY_VERIFIED_NOT_SOLVER_VALIDATED",
        sizes=SIZES,independent_mothers=8,independent_mothers_per_size=2,related_variants_per_mother=4,
        total_related_variants=len(specs),pilot_seeds=PILOT_SEEDS,
        formal_main_seed_reservation=MAIN_SEED_RESERVATION,formal_main_count_per_scale=25,
        occupancy="1.0 for tight Q=L; 0.8 for roomier Q=ceil(1.25L)",
        load_values=[120,160,200],incoming_weights="wa=0.6L, wb=0.8L; atomic named order a then b",
        coordinates="Unique integer 2D nodes in [-50,50]^2, hub at origin",
        graph="Bidirectional angle ring + three nearest outbound neighbors + Bernoulli(0.10) cross-links",
        signal="Each directed arc independently active with probability 0.55; period12/24/48 and green fractions1/4,1/2,3/4",
        calendar_lcm_ticks=48,positive_travel_and_service=True,strict_capacity_and_signal_pairing=True,
        no_outcome_based_filtering=True,no_solver_run=True,no_real_world_calibration=True,
        scope="One fixed receiver and hub, two atomic incoming batches, H2 only; generic synthetic transport, not indoor traffic lights or SUMO",
        risk="m10/12 can exceed time/memory; timed-prefix exhaustive oracle is unsuitable; pilot truncation/censoring must be retained",
        python=sys.version,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        inputs_sha256=hashlib.sha256((out/"INPUTS.json").read_bytes()).hexdigest())
    (out/"PROTOCOL.json").write_text(json.dumps(protocol,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(status=protocol["status"],path=str(out),instances=len(specs),independent_mothers=8)),flush=True)

def main_suite(count_per_scale=25):
    if not isinstance(count_per_scale,int) or not 1<=count_per_scale<=999:
        raise ValueError("Count per scale must be an integer in 1..999.")
    return [s for m in SIZES for i in range(1,count_per_scale+1)
            for s in variants(8470000+1000*m+i,m,"main")]

def _freeze_additional(label,specs,extra):
    out=HERE/"instances"/(label+"_01")
    if out.exists():raise ValueError("Preserve existing generated inputs.")
    checks=verify_pairs(specs)
    out.mkdir(parents=True,exist_ok=False)
    for name,obj in (("INPUTS.json",specs),("PAIR_CHECKS.json",checks)):
        (out/name).write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
    protocol=dict(status="GENERATED_AND_STRUCTURALLY_VERIFIED_NOT_SOLVER_VALIDATED",
        split=label,sizes=sorted({len(s["old"]) for s in specs}),
        independent_mothers=len({s["seed"] for s in specs}),related_variants=len(specs),
        related_variants_per_mother=4,seeds=sorted({s["seed"] for s in specs}),
        paired_axes=["capacity","signal"],input_count_not_independent_count=True,
        parameters="Same frozen mother()/variants() distributions as pilot; no outcome filtering",
        occupancy="1.0 or 0.8",calendar_lcm_ticks=48,no_solver_run=True,
        no_real_world_calibration=True,pilot_and_main_seeds_disjoint=True,
        preserve_timeouts_and_censoring=True,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        inputs_sha256=hashlib.sha256((out/"INPUTS.json").read_bytes()).hexdigest(),**extra)
    (out/"PROTOCOL.json").write_text(json.dumps(protocol,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(status=protocol["status"],path=str(out),instances=len(specs),
                         independent_mothers=protocol["independent_mothers"])),flush=True)
    return out

def freeze_main(count_per_scale=25):
    return _freeze_additional("main",main_suite(count_per_scale),
        dict(independent_mothers_per_scale=count_per_scale,
             primary_candidate="LAZY_ASTAR",primary_baselines=["ROUTE","AWA_ROUTE"],
             auxiliary_methods=["NO_BOUND","PAIR_EAGER"],
             formal_seed_rule="8470000 + 1000*m + index, index1..count_per_scale",
             scope="High-load synthetic two-handoff transport; H2 only",
             exclusion_rule="No outcome-based seed exclusions; infeasible resource size remains a censored/stress stratum"))

def freeze_micro():
    return _freeze_additional("micro",small_validation_suite(),
        dict(independent_mothers_per_scale=2,
             purpose="Independent DP versus old full timed-prefix enumeration; not performance data"))

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite",choices=("pilot","micro","main","all"),default="pilot")
    args=parser.parse_args()
    if args.suite in ("pilot","all"):freeze_pilot()
    if args.suite in ("micro","all"):freeze_micro()
    if args.suite in ("main","all"):freeze_main()


