#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
from usdjpy_hyp036_dukas_native_lib_v1 import HYP,FAM,CAND,clean,wj,sha,run

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw-2023",type=Path,required=True); ap.add_argument("--raw-2024",type=Path,required=True)
    ap.add_argument("--baseline-trades",type=Path,required=True); ap.add_argument("--baseline-states",type=Path,required=True)
    ap.add_argument("--prereg",type=Path,required=True); ap.add_argument("--source-manifest",type=Path,required=True)
    ap.add_argument("--out-dir",type=Path,required=True); ap.add_argument("--research-sha",required=True)
    ap.add_argument("--core-sha",required=True); ap.add_argument("--run-id",required=True); ap.add_argument("--preflight-only",action="store_true")
    a=ap.parse_args(); a.out_dir.mkdir(parents=True,exist_ok=True)
    pre=json.loads(a.prereg.read_text(encoding="utf-8")); man=json.loads(a.source_manifest.read_text(encoding="utf-8"))
    assert pre["status"]=="FROZEN_BEFORE_DEVELOPMENT_OUTCOMES" and pre["hypothesis_id"]==HYP and pre["candidate_id"]==CAND
    assert pre["fixed_source_native_contract"]["hold_bars"]==16 and pre["fixed_source_native_contract"]["atlas_identity_gate"] is False
    assert man["forbidden_assets"]==["2019","2020","2021","2022","2025"]
    if a.preflight_only:
        r={"schema_version":"usdjpy_hyp036_preflight_receipt_v1","status":"PASS_NO_SOURCE_NATIVE_OUTCOMES",
          "hypothesis_id":HYP,"family_id":FAM,"candidate_id":CAND,
          "raw_archive_count":len(list(a.raw_2023.glob("*.tar.gz")))+len(list(a.raw_2024.glob("*.tar.gz"))),
          "baseline_ledger_exists":a.baseline_trades.exists(),"baseline_state_ledger_exists":a.baseline_states.exists(),
          "candidate_outcome_computed":False,"historical_2020_2022_accessed":False,"protected_2025_accessed":False}
        r["pass"]=r["raw_archive_count"]==24 and r["baseline_ledger_exists"] and r["baseline_state_ledger_exists"]
        wj(a.out_dir/"preflight_receipt.json",r); print(json.dumps(r,indent=2)); return 0 if r["pass"] else 2
    x=run(a,pre,man); trades=x["trades"]; stand=x["standalone"]
    gf=pd.DataFrame(x["gates"]); gf.to_csv(a.out_dir/"candidate_gate_matrix.csv",index=False)
    for name in ["standalone","concentration","bootstrap","robustness","portfolio"]:
        out_name={"standalone":"standalone_metrics.json","robustness":"execution_robustness.json","portfolio":"portfolio_diagnostics.json"}.get(name,f"{name}.json")
        wj(a.out_dir/out_name,x[name])
    failed=gf[~gf["pass"]]
    result={"schema_version":"usdjpy_hyp036_development_result_v1","status":"COMPLETE_AT_FIRST_BINDING_STOP",
      "hypothesis_id":HYP,"family_id":FAM,"candidate_id":CAND,"decision":x["decision"],"failed_binding_stage":x["stage"],
      "failed_binding_gates":failed[["stage","gate"]].to_dict("records"),"research_start_sha":pre["starting_authority"]["research_main_sha"],
      "research_execution_sha":a.research_sha,"core_start_sha":pre["starting_authority"]["core_main_sha"],"core_end_sha":a.core_sha,
      "run_id":a.run_id,"source_authority":x["source"],"suppression":x["suppression"],
      "source_native_events":0 if trades is None else len(trades),"source_native_trades":0 if trades is None else len(trades),
      "standalone":stand,"concentration":x["concentration"],"bootstrap":x["bootstrap"],
      "execution_robustness":x["robustness"],"portfolio":x["portfolio"],"candidate_freeze_authorized":False,
      "historical_2020_2022_authorized":False,"historical_2020_2022_accessed":False,"core_mt4_authorized":False,
      "core_modified":False,"mt4_executed":False,"external_2025h1_authorized":False,"protected_2025_accessed":False,
      "production_authorized":False,"live_authorized":False,"hyp035_reopened":False,"atlas_event_population_reused":False,"no_retuning":True}
    wj(a.out_dir/"final_result.json",result)
    wj(a.out_dir/"candidate_registry.json",{"schema_version":"usdjpy_hyp036_candidate_registry_v1","hypothesis_id":HYP,
      "family_id":FAM,"candidate_ids":[CAND],"selected_candidate":None,"candidate_freeze_authorized":False,
      "decision":x["decision"],"failed_binding_stage":x["stage"],"historical_2020_2022_authorized":False,
      "core_mt4_authorized":False,"2025_authorized":False,"production_authorized":False,"live_authorized":False,"no_retuning":True})
    wj(a.out_dir/"period_access_receipt.json",{"development_2023_2024_accessed":True,"historical_2020_2022_accessed":False,
      "protected_2025h1_accessed":False,"protected_2025h2_accessed":False,"reason":f"Stopped at {x['stage']}"})
    wj(a.out_dir/"currency_audit.json",{"status":"PASS_DEVELOPMENT_JPY_CONTRACT",**pre["monetary_contract"],
      "currency_mismatch_count":0 if trades is not None else None})
    (a.out_dir/a.prereg.name).write_bytes(a.prereg.read_bytes()); (a.out_dir/a.source_manifest.name).write_bytes(a.source_manifest.read_bytes())
    (a.out_dir/"human_report.md").write_text(
      f"# USDJPY-HYP-036 Dukascopy-Native Pullback Continuation Development Result\n\nDecision: `{x['decision']}`\n\n"
      f"First binding stop: `{x['stage']}`\n\nSource-native trades: {result['source_native_trades']}. Net JPY: {stand.get('net_jpy')}. "
      f"PF: {stand.get('profit_factor')}. Positive folds: {stand.get('positive_folds')}. Positive months: {stand.get('positive_months')}. "
      f"MDD JPY: {stand.get('mdd_jpy')}.\n\nHYP-035 was not reopened. 2020-2022, Core/MT4 and 2025 were not accessed. "
      "No production/live authorization.\n",encoding="utf-8")
    files=[]
    for path in sorted(a.out_dir.iterdir()):
        if path.is_file() and path.name not in ["artifact_manifest.json","PACKAGE_SHA256SUMS"]:
            files.append({"path":path.name,"bytes":path.stat().st_size,"sha256":sha(path)})
    wj(a.out_dir/"artifact_manifest.json",{"schema_version":"usdjpy_hyp036_artifact_manifest_v1","hypothesis_id":HYP,
      "decision":x["decision"],"files":files,"historical_2020_2022_accessed":False,"protected_2025_accessed":False})
    files.append({"path":"artifact_manifest.json","sha256":sha(a.out_dir/"artifact_manifest.json")})
    (a.out_dir/"PACKAGE_SHA256SUMS").write_text("".join(f"{r['sha256']}  {r['path']}\n" for r in files),encoding="utf-8")
    print(json.dumps(clean({"decision":x["decision"],"failed_binding_stage":x["stage"],"source_native_trades":result["source_native_trades"],
      "net_jpy":stand.get("net_jpy"),"profit_factor":stand.get("profit_factor"),"positive_folds":stand.get("positive_folds"),
      "positive_months":stand.get("positive_months")}),indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
