"""Pinned V449 scale dependencies. Imports do not run solvers."""
from pathlib import Path
import hashlib,importlib.util,json,sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
V448=P.parent/'fleet_study_v448_radius_pair_prototype_20261107'
V447=P.parent/'fleet_study_v447_random_high_load_20261107'
PINS={
 'micro_gate_v448.py':(V448/'micro_gate_v448.py','2d8875a347f89fdca3f8eab6dc9052a2596bab86e00c4730c9d67f3e8d0dfe00'),
 'selective_v448.py':(V448/'selective_v448.py','f955dcb082a1e8fb4e683741a657c433209202f313571c07174d9ab15de42a6c'),
 'reference_v448.py':(V448/'reference_v448.py','9810d96023a7710329d34a42f5c831687ea73e09fbfb42968fe4c660366a7416'),
 'run_v448.py':(V448/'run_v448.py','4f310cb6213a9ca576d60dafa45c995068f88877a575c5ef844b5b5ba687896f'),
 'independent_dp_v447.py':(V447/'independent_dp_v447.py','8c59f8695dfa2347b0f8ac5c817aec93c0c41e07c0882d45f099abaf4d9c2431'),
 'instances_v447.py':(V447/'instances_v447.py','a2e8b402e0c913c371c4d37107b23ff934a91df98fecc58b8f3274cb791e2329')}
LOCAL=('scale_sources_v449.py','instances_scale_v449.py','dp_adapter_v449.py','check_scale_v449.py','run_scale_v449.py','run_scale_jobs_v449.py')
METHODS=('RADIUS','RADIUS_PAIR_EAGER','RADIUS_PAIR_LAZY','RADIUS_AWA','RADIUS_PAIR_AWA','RADIUS_PAIR_AWA_GATED','NO_BOUND','DP_ADAPTER','ROUTE')
MAP={'RADIUS':('ROUTE','radius'),'RADIUS_PAIR_EAGER':('PAIR_EAGER','radius'),
 'RADIUS_PAIR_LAZY':('LAZY_ASTAR','radius'),'RADIUS_AWA':('AWA_ROUTE','radius'),
 'RADIUS_PAIR_AWA':('AWA_PAIR','radius'),'RADIUS_PAIR_AWA_GATED':('AWA_GATED','radius'),
 'NO_BOUND':('NO_BOUND','exact'),'DP_ADAPTER':('TOPOLOGICAL_DP','none'),'ROUTE':('ROUTE','exact')}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def append(p,v):
 with Path(p).open('a',encoding='utf-8') as f:f.write(json.dumps(v,allow_nan=False)+'\n');f.flush()
def require(ok,detail):
 if not ok:raise AssertionError(detail)
def module(name,path,expected=None):
 if expected is not None:require(sha(path)==expected,('source hash',str(path)))
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
 sys.modules[name]=m;spec.loader.exec_module(m);return m
def current_sources():
 out={}
 for name,(path,expected) in PINS.items():
  actual=sha(path);require(actual==expected,('frozen parent source',name));out[str(path)]=actual
 out.update({str(P/name):sha(P/name) for name in LOCAL})
 return out
def validate_sources():
 current=current_sources();require(current==load(P/'Scale_Source_Manifest.json')['sources'],'V449 source freeze mismatch');return current
def load_modules():
 validate_sources()
 gate=module('v449_gate448',*PINS['micro_gate_v448.py'])
 require(sha(V448/'gates/micro_all_01/GATE.json')==load(P/'Scale_Source_Manifest.json')['parent_V448_gate_sha256'],'Parent gate identity')
 gate.validate_gate(V448/'gates/micro_all_01/GATE.json')
 sp=module('v449_selective448',PINS['selective_v448.py'][0])
 dp=module('v449_reference_dp',PINS['independent_dp_v447.py'][0])
 helper=module('v449_result_helpers',PINS['run_v448.py'][0])
 return sp,dp,helper

def run_search(sp,spec,method,watchdog,wall_ms=None):
    if method in ('RADIUS_PAIR_AWA','RADIUS_PAIR_AWA_GATED'):
        policy,basis=MAP[method]
        row=sp.solve(spec,policy,watchdog,wall_ms=wall_ms,profile=False,audit=False,checkpoints=(),basis=basis)
        require(row['arm']==policy and row['bound_basis']==basis,'Existing internal policy mapping')
        row['method']=method
        return row
    return sp.solve_method(spec,method,watchdog,wall_ms=wall_ms,profile=False,audit=False,checkpoints=())
