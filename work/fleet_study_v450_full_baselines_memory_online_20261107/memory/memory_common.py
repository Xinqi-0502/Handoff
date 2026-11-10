"""Memory-only measurement plumbing. No solver work on import."""
from pathlib import Path
import hashlib,importlib.util,json,sys,os
P=Path(__file__).resolve().parent
WORK=P.parent.parent
V449=WORK/'fleet_study_v449_validation_and_online_20261107'
V448=WORK/'fleet_study_v448_radius_pair_prototype_20261107'
V447=WORK/'fleet_study_v447_random_high_load_20261107'
PRIMARY=('RADIUS','RADIUS_PAIR_EAGER','RADIUS_PAIR_LAZY','RADIUS_AWA','RADIUS_PAIR_AWA','RADIUS_PAIR_AWA_GATED','NO_BOUND','DP_ADAPTER','ROUTE')
EXTERNAL=('HZ_AWA_RADIUS','ANA_RADIUS','HZ_AWA_RADIUS_PAIR_GATED')
LOCAL=('native_memory.py','owned_process.py','memory_common.py','memory_worker.py','run_memory.py','run_memory_jobs.py','freeze_memory.py','check_memory_safety.py')

def require(ok,why):
    if not ok:raise AssertionError(why)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def append(p,x):
    with Path(p).open('a',encoding='utf-8') as f:f.write(json.dumps(x,allow_nan=False)+'\n');f.flush()
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def verify_manifest(path):
    m=load(path);require(m['status']=='FROZEN','Numerical memory manifest not frozen')
    require(m['primary_methods']==list(PRIMARY) and m['external_methods']==list(EXTERNAL),'Method registry')
    for name,h in m['sources'].items():require(sha(name)==h,('Frozen source drift',name))
    for name,h in m['inputs'].items():require(sha(name)==h,('Frozen input drift',name))
    require(m['common_external_import_ready'] is True,'Common full-baseline import set is pending')
    return m

def load_bundle(manifest):
    """All methods import the identical complete bundle, without oracle evaluation."""
    for d in (V449,V448,V447):
        if str(d) not in sys.path:sys.path.insert(0,str(d))
    sc=module('memory450_scale_sources',V449/'scale_sources_v449.py')
    # The controller validates gates once. Avoid loading gate result records into
    # every measured worker: they are validation data, not solver prerequisites.
    sp=sc.module('memory450_selective',V448/'selective_v448.py')
    dp=sc.module('memory450_reference_dp',V447/'independent_dp_v447.py')
    helper=sc.module('memory450_result_helper',V448/'run_v448.py')
    adapter=sc.module('memory450_dp_adapter',V449/'dp_adapter_v449.py')
    external=sc.module('memory450_published_full',Path(manifest['external_module']))
    require(set(external.METHODS)==set(EXTERNAL),'External registry mismatch')
    external.configure_domain(sp)
    origins=sorted({str(Path(m.__file__).resolve()) for m in tuple(sys.modules.values()) if getattr(m,'__file__',None)})
    return sc,sp,dp,helper,adapter,external,origins

def solve_selected(bundle,spec,method,wall_ms,hard_seconds=15):
    sc,sp,dp,helper,adapter,external,_=bundle
    if method=='DP_ADAPTER':return adapter.solve(spec,dp,wall_ms=wall_ms,hard_seconds=hard_seconds)
    if method in PRIMARY:return sc.run_search(sp,spec,method,sp.Watchdog(hard_seconds),wall_ms=wall_ms)
    require(method in EXTERNAL,'Unknown method')
    return external.solve(spec,method,watchdog=sp.Watchdog(hard_seconds),wall_ms=wall_ms,hard_seconds=hard_seconds,domain_module=sp,audit=False,node_limit=None)

def memory_semantics():
    return dict(native_API='psapi.GetProcessMemoryInfo / PROCESS_MEMORY_COUNTERS_EX',units='bytes',
        primary_endpoint='Lifetime PeakWorkingSetSize and PeakPagefileUsage sampled immediately after solve, before any oracle/replay or result serialization',
        baseline='Current and lifetime peak counters after common imports, input parsing and GC; before solver Context setup',
        algorithm_setup='Constructor/model setup and initial planning remain inside frozen solve and are included in the native peak; no separate resettable model-setup peak is claimed',
        lifetime_peak_cannot_be_reset=True,peak_growth_is_not_algorithm_private_RAM=True,
        process_working_set_includes_shared_pages=True,pagefile_fields_mean_commit_not_disk_io=True,
        post_solve_validation='Parent process only; never added to worker memory',
        post_exit_peak='Optional full-lifetime OS counters while owned process handle remains open; unavailable counters remain NA',
        timing_scope='Separate memory instrumentation run; do not combine with V449 timing observations',
        tracemalloc_used=False,proxy_counts_not_converted_to_bytes=True)


