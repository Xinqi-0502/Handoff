from pathlib import Path
import ast,hashlib,json,difflib
parent=Path(r"E:\CodexResearch-xi\workspace\work\fleet_study_v447_random_high_load_20261107")
out=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
raw=(parent/"selective_v447.py").read_bytes()
ref_bytes=(parent/"reference_v447.py").read_bytes()
src=raw.decode("utf-8-sig");text=src
assert sha(raw)=="1bbdf82f14286102e31ec35a9fec7b8f8588c5d5cbe63935787aef59fad3e4f4",sha(raw)
assert sha(ref_bytes)=="9810d96023a7710329d34a42f5c831687ea73e09fbfb42968fe4c660366a7416"
def replace(a,b,n=1):
    global text
    assert text.count(a)==n,(text.count(a),n,a[:90])
    text=text.replace(a,b)
start=text.index('"""');end=text.index('"""',start+3)+3
text=text[:start]+'''"""V448 unmeasured RADIUS-plus-PAIR prototype copied from frozen V447.
Exact basis is the default. Only phase-0 quota-return values can switch to
weighted individual-via thresholds; the union formula and search policies stay.
No common quota cutoff, new global cache, network change or domain change is added.
The local reference is byte-identical to V447. This source is prepared only:
AST/static checks are not numerical correctness or performance evidence.
"""'''+text[end:]
replace("reference_v447.py","reference_v448.py")
replace("Frozen local V447 reference source hash changed.","Frozen local V448 reference source hash changed.")
replace('"v447_frozen_reference"','"v448_frozen_reference"')
replace('SOURCE_VERSION = "v447-random-high-load-validation12-1"','SOURCE_VERSION = "v448-radius-pair-prototype-unmeasured-1"')
replace('LAZY_ASTAR_SOURCE = "https://tzin.bgu.ac.il/~felner/2013/lazya.pdf"', '''LAZY_ASTAR_SOURCE = "https://tzin.bgu.ac.il/~felner/2013/lazya.pdf"
BOUND_BASES = ("exact", "radius")
# Public method names separate mathematical basis from unchanged queue policy.
METHOD_MAP = {arm: (arm, "exact") for arm in ARMS}
METHOD_MAP.update({
    "RADIUS": ("ROUTE", "radius"),
    "RADIUS_PAIR_LAZY": ("LAZY_ASTAR", "radius"),
    "RADIUS_PAIR_EAGER": ("PAIR_EAGER", "radius"),
    "RADIUS_AWA": ("AWA_ROUTE", "radius"),
})


def method_name(arm, basis):
    for name, pair in METHOD_MAP.items():
        if pair == (arm, basis):
            return name
    return basis.upper()+"_"+arm
''')
replace('    gb: int\n','    gb: int  # Exact G_qb or radius R_qb according to Context.basis.\n')
replace('''class Context:
    """No global bound/detail/via/quota-table caches; scalar shared caches retained."""
    def __init__(self, spec, watchdog, profile=False):
        ref.validate_instance(spec)''','''class Context:
    """Fixed quota basis; original scalar caches and all feasible actions retained."""
    def __init__(self, spec, watchdog, profile=False, *, basis="exact"):
        if basis not in BOUND_BASES:
            raise ValueError("basis must be exact or radius")
        self.basis = basis
        ref.validate_instance(spec)''')
replace('        self.phase1_calls = self.phase1_via_items = self.phase1_ns = 0','''        self.phase1_calls = self.phase1_via_items = self.phase1_ns = 0
        self.radius_calls = self.radius_via_items = self.radius_ns = 0
        self.radius_union_saturation_skips = 0''')
replace('    def fa(self, x):','''    def radius_pair(self, s, qa, qb):
        """Two indivisible weighted thresholds from one sorted individual-via list.

        This is not a feasible common quota route. No new global/local-state cache
        is retained. Later alphas use the original Network scalar cache as before.
        """
        self.radius_calls += 1
        started = time.perf_counter_ns() if self.profile else 0
        try:
            direct = self.net.arrive(s.pos, self.h, s.t)
            if qb == 0:
                return direct, direct
            values = []
            for i in ref.bit_ids(s.oldmask):
                if self.profile:
                    self.radius_via_items += 1
                item = self.old[i]
                at = self.net.arrive(s.pos, item["node"], s.t) + item["service"]
                returned = self.net.arrive(item["node"], self.h, at)
                values.append((returned, item["weight"]))
            ga = direct if qa == 0 else INF
            gb = INF
            released = 0
            for returned, weight in sorted(values):
                released += weight
                if ga == INF and released >= qa:
                    ga = returned
                if released >= qb:
                    gb = returned
                    break
            if ga == INF or gb == INF:
                raise AssertionError("Capacity quotas must be covered by remaining old weight.")
            return ga, gb
        finally:
            if self.profile:
                self.radius_ns += time.perf_counter_ns()-started

    def fa(self, x):''')
replace('        ga, gb = self.quota_pair(s, qa, qb)','''        if self.basis == "exact":
            ga, gb = self.quota_pair(s, qa, qb)
        else:
            ga, gb = self.radius_pair(s, qa, qb)''')
replace('''            if base.gb + self.spec["tau_a"] <= base.B:
                self.exact_quota_skips += 1''','''            if base.gb + self.spec["tau_a"] <= base.B:
                if self.basis == "exact":
                    self.exact_quota_skips += 1
                else:
                    # R_qb threshold means E1(B) covers qb, not a feasible path.
                    self.radius_union_saturation_skips += 1''',2)
replace('                     detailed_profile_enabled=self.profile)','''                     detailed_profile_enabled=self.profile,
                     radius_calls=self.radius_calls,
                     skip_radius_union_saturation=self.radius_union_saturation_skips)''')
replace('                         pair_ns=self.pair_ns, quota_ns=self.quota_ns,','''                         pair_ns=self.pair_ns, quota_ns=self.quota_ns,
                         radius_ns=self.radius_ns,
                         radius_individual_via_items=self.radius_via_items,''')
replace('''          _context_factory=None, node_limit=None, checkpoints=NODE_CHECKPOINTS):
    if arm not in ARMS:''','''          _context_factory=None, node_limit=None, checkpoints=NODE_CHECKPOINTS,
          *, basis="exact"):
    if basis not in BOUND_BASES:
        raise ValueError("basis must be exact or radius")
    if _context_factory is not None and basis != "exact":
        raise ValueError("Custom policy fixtures support the legacy exact default only.")
    if arm not in ARMS:''')
replace('''    factory = Context if _context_factory is None else _context_factory
    ctx = factory(spec, watchdog, profile)''','''    if _context_factory is None:
        ctx = Context(spec, watchdog, profile, basis=basis)
    else:
        ctx = _context_factory(spec, watchdog, profile)''')
replace('''    return dict(case=spec["case"],seed=spec["seed"],split=spec["split"],arm=arm,
                H2=best,''','''    return dict(case=spec["case"],seed=spec["seed"],split=spec["split"],arm=arm,
                bound_basis=basis,method=method_name(arm,basis),
                H2=best,''')
replace('def get_cases(split):','''def solve_method(spec, method, watchdog, **kwargs):
    """Explicit public name -> (unchanged search policy, phase-0 quota basis)."""
    if method not in METHOD_MAP:
        raise ValueError(method)
    if "basis" in kwargs:
        raise ValueError("solve_method fixes basis through METHOD_MAP.")
    arm, basis = METHOD_MAP[method]
    return solve(spec, arm, watchdog, basis=basis, **kwargs)


def get_cases(split):''')
replace("Fresh descendant of the V444 directory.","Fresh descendant of the V448 directory (legacy exact-only CLI).")
old_ast=ast.parse(src);new_ast=ast.parse(text);ast.parse(ref_bytes.decode("utf-8-sig"))
def cls(tree,name):return next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==name)
def dump(n):return ast.dump(n,include_attributes=False)
def methods(tree,name):return {n.name:dump(n) for n in cls(tree,name).body if isinstance(n,ast.FunctionDef)}
a,b=methods(old_ast,"Context"),methods(new_ast,"Context")
unchanged=("quota_pair","fa","gamma_order","gamma","gamma_at_most","continuation","alphas")
assert all(a[n]==b[n] for n in unchanged)
assert dump(cls(old_ast,"Network"))==dump(cls(new_ast,"Network"))
assert dump(cls(old_ast,"Base"))==dump(cls(new_ast,"Base"))
funcs=("queue_priority","reference_phase1_bound","verify_pathmax_edges","reference_lazy_policy","verify_lazy_toy")
for name in funcs:
    oa=next(n for n in old_ast.body if isinstance(n,ast.FunctionDef) and n.name==name)
    nb=next(n for n in new_ast.body if isinstance(n,ast.FunctionDef) and n.name==name)
    assert dump(oa)==dump(nb),name
targets=("selective_v448.py","reference_v448.py","Source_Changes.diff","Static_Preparation.json")
assert not any((out/n).exists() for n in targets),"Preserve existing V448 outputs"
(out/"reference_v448.py").write_bytes(ref_bytes)
(out/"selective_v448.py").write_text(text,encoding="utf-8",newline="\n")
(out/"Source_Changes.diff").write_text("".join(difflib.unified_diff(src.splitlines(True),text.splitlines(True),fromfile="V447/selective_v447.py",tofile="V448/selective_v448.py")),encoding="utf-8",newline="\n")
record=dict(status="AST_STATIC_ONLY_NOT_RUN",parent_solver_sha256=sha(raw),
    parent_reference_sha256=sha(ref_bytes),solver_sha256=sha((out/"selective_v448.py").read_bytes()),
    reference_sha256=sha((out/"reference_v448.py").read_bytes()),reference_byte_identical=True,
    unchanged_context_methods=list(unchanged),unchanged_network_ast=True,unchanged_base_ast=True,
    unchanged_top_level_functions=list(funcs),no_solver_or_oracle_executed=True,
    source_version="v448-radius-pair-prototype-unmeasured-1",exact_default=True,max_old_items=12,
    new_global_caches=False,new_quota_cutoffs=False)
(out/"Static_Preparation.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
print(json.dumps(record))

