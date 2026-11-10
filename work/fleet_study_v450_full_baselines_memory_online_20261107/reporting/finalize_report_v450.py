from pathlib import Path
from html.parser import HTMLParser
import json, hashlib, datetime, math
ROOT=Path(__file__).resolve().parents[1]
def read(p): return json.loads((ROOT/p).read_text(encoding="utf-8-sig"))
def sha(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
class Links(HTMLParser):
    def __init__(self): super().__init__();self.links=[];self.images=[];self.text=[]
    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        if tag=="a": self.links.append(d["href"])
        if tag=="img": self.images.append(d["src"])
    def handle_data(self,data): self.text.append(data)
html_name="Research_Evidence_Report_01.html"
raw=(ROOT/html_name).read_text(encoding="utf-8")
parser=Links();parser.feed(raw)
for p in parser.links+parser.images:
    target=(ROOT/p).resolve()
    assert target.is_relative_to(ROOT) and target.exists(), p
assert len(parser.images)==3
assert "<html lang=\"en\">" in raw
static=read("static_comparison/analysis/main_01/Analysis.json")
online=read("online/analysis/interpretation_02/Summary.json")
audit_paths=[
"audit_code/results/main_01/Independent_Audit.json",
"audit_code/results/crosscheck_01/Crosscheck.json",
"audit_code/memory/results/main_01/Independent_Memory_Audit.json",
"online/analysis/full_02/SUMMARY.json"]
for p in audit_paths: assert read(p)["status"]=="PASS",p
assert static["status"]==online["status"]=="PASS"
reverse=next(x for x in static["pairs"] if x["lhs"]=="HZ_AWA_RADIUS" and x["rhs"]=="HZ_AWA_RADIUS_PAIR_GATED")
proof_delta=100*(reverse["rhs_seconds"]/reverse["lhs_seconds"]-1)
expansion_delta=100*(reverse["rhs_expansions"]/reverse["lhs_expansions"]-1)
assert reverse["common_proved_cases"]==255
assert round(proof_delta,2)==-27.17 and round(expansion_delta,2)==-54.74
for s in ("-27.17%","-54.74%","-23.42%","-51.64%","+2.82%","+4.07%","-7.96%"): assert s in raw,s
for row in online["main"]:
    assert row["actual_ties"]==64 and row["mean_actual_delta"]==0 and row["mean_handoff_wait_delta"]==0
    assert row["cross_arm_same_execution_rep_pairs"]==192
assert online["native"]["replays"]==128 and online["native"]["all_complete_18_customers"]
assert online["native"]["recorded_collision_elements"]==0
assert "do not establish memory savings" in raw
assert "late common initializer" in raw
assert "Complete freight ALNS systems have not been reproduced" in raw
assert "partial-primary-text comparison" in raw
report_manifest=read("Research_Evidence_Report_01.manifest.json")
assert report_manifest["report_sha256"]==sha(html_name)
for p,digest in report_manifest["evidence"].items(): assert sha(p)==digest,p
extra=[
"static_comparison/Frozen_Source_Manifest.json",
"online/Online_Source_Manifest_03.json",
"online/Online_Results_02.md",
"online/analysis/interpretation_02/Report_Manifest.json",
"online/analysis/full_02/Audit_Source_Hashes.json",
"figures/native_outcome/Native_Final_Delivery_Manifest_02.json",
"figures/native_outcome/render_native_02/VISUAL_QA_COMPLETE.json",
"figures/native_outcome/render_native_02/Caption.md",
"figures/native_outcome/conditions_main_01/All_Condition_Summary.csv",
"memory/Final_Delivery_Manifest_01.json",
"literature/Formula_Coverage_Matrix.md",
"records/Browser_Access_Retry_02.json",
"reporting/Report_Build_Failure_01.json",
"reporting/Report_Build_Failure_02.json",
"reporting/build_report_v450_v2.py"]
for p in extra: assert (ROOT/p).is_file(),p
receipt={
"status":"PASS","created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
"checks":{"local_links":len(parser.links),"figures":len(parser.images),"source_manifest_matches":len(report_manifest["evidence"]),"independent_audits":len(audit_paths),"local_proof_common_cases":255,"native_scenarios":64,"native_mothers":8,"native_policy_calls":1728,"native_distinct_replays":128},
"confirmed_claims":{"same_kernel_proof_change_percent":proof_delta,"same_kernel_expansion_change_percent":expansion_delta,"online_customer_and_truck_changes":"zero for all 64 cases at each budget","algorithm_specific_memory_savings":"not established"},
"visual_scope":"Root inspected all three final PNG figures. Separate agent receipts record PDF inspection and automatic figure QA. HTML structure, local assets, displayed numbers and evidence hashes were checked here.",
"experimental_data_modified":False}
out=ROOT/"reporting/Final_Verification_01.json"
assert not out.exists()
out.write_text(json.dumps(receipt,indent=2),encoding="utf-8")
index={
"status":"COMPLETED_V450_EVIDENCE_BATCH","report":html_name,
"main_version":"Frozen V449 RADIUS_PAIR_AWA_GATED",
"paired_causal_engine":"HZ_AWA_RADIUS_PAIR_GATED versus HZ_AWA_RADIUS",
"completed":["256 new local scenarios and 3072 formal solver calls","128 fresh-process memory observations","64 online scenarios, 1728 policy calls and 128 distinct SUMO replays","128 separate instrumented online calls","all-factorial reporting and three code-generated figures"],
"remaining_research_limits":["Full freight ALNS systems have not been reproduced","COR 10.1016/j.cor.2026.107577 full-text comparison remains incomplete","No city-traffic calibration or continuous rolling dispatch validation","No incremental online service gain or algorithm-specific memory saving established"],
"preservation":"All raw measurements, null effects, deadline misses, unsuccessful gates and report-building errors remain in this study directory or their linked frozen predecessor directories.",
"evidence":{p:sha(p) for p in [html_name,"Research_Evidence_Report_01.manifest.json","reporting/Final_Verification_01.json"]+audit_paths+extra}
}
out=ROOT/"FINAL_EVIDENCE_INDEX_01.json";assert not out.exists()
out.write_text(json.dumps(index,indent=2),encoding="utf-8")
print(json.dumps({"status":"PASS","report":str(ROOT/html_name),"index":str(out),"report_sha256":sha(html_name),"links":len(parser.links),"figures":len(parser.images)},indent=2))
