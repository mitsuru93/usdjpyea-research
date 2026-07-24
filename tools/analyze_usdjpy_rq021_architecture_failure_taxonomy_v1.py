#!/usr/bin/env python3
"""Taxonomize the already-opened RQ-020E four-fold architecture census."""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

PERIODS=["2023H1","2023H2","2024H1","2024H2"]

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""): h.update(chunk)
    return h.hexdigest()

def clean(x:Any)->Any:
    if isinstance(x,float) and (math.isnan(x) or math.isinf(x)): return None
    if isinstance(x,dict): return {k:clean(v) for k,v in x.items()}
    if isinstance(x,list): return [clean(v) for v in x]
    return x

def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--cell-fold-metrics",type=Path,required=True)
    ap.add_argument("--direction-metrics",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args(); a.output.mkdir(parents=True,exist_ok=True)
    m=pd.read_csv(a.cell_fold_metrics); d=pd.read_csv(a.direction_metrics)
    if len(m)!=2640 or len(d)!=5280: raise AssertionError((len(m),len(d)))

    rows=[]
    for (cid,fam,h),q in m.groupby(["candidate_id","family","horizon_bars"],sort=True):
        q=q.set_index("period").reindex(PERIODS)
        if q.isna().any().any(): raise AssertionError((cid,h,"fold grid"))
        default=((q.default_net_pips>0)&(q.default_pf>=1)); severe=((q.severe_net_pips>0)&(q.severe_pf>=1))
        breadth=((q.positive_months>=4)&(q.negative_months<=2)&(q.ex_best_two_dates>0))
        sv=q.severe_net_pips.to_numpy(float); dv=q.default_net_pips.to_numpy(float)
        rows.append({"candidate_id":cid,"family":fam,"horizon_bars":int(h),"default_pass_folds":int(default.sum()),"severe_pass_folds":int(severe.sum()),"breadth_pass_folds":int(breadth.sum()),"weakest_severe_fold":str(q.severe_net_pips.idxmin()),"minimum_fold_default_net":float(dv.min()),"minimum_fold_severe_net":float(sv.min()),"fourfold_default_net":float(dv.sum()),"fourfold_severe_net":float(sv.sum()),"severe_range":float(sv.max()-sv.min()),"default_sign_changes":int(np.sum(np.sign(dv[:-1])!=np.sign(dv[1:]))),"severe_sign_changes":int(np.sum(np.sign(sv[:-1])!=np.sign(sv[1:])))} )
    cell=pd.DataFrame(rows)
    if len(cell)!=660: raise AssertionError(len(cell))

    family_rows=[]
    for fam,q in cell.groupby("family",sort=True):
        weak=q.weakest_severe_fold.value_counts().reindex(PERIODS,fill_value=0); fm=m[m.family==fam]
        row={"family":fam,"entries":int(q.candidate_id.nunique()),"cells":len(q),"default_4fold_cells":int((q.default_pass_folds==4).sum()),"severe_4fold_cells":int((q.severe_pass_folds==4).sum()),"median_default_pass_folds":float(q.default_pass_folds.median()),"median_severe_pass_folds":float(q.severe_pass_folds.median()),"median_minimum_fold_default_net":float(q.minimum_fold_default_net.median()),"median_minimum_fold_severe_net":float(q.minimum_fold_severe_net.median()),"median_fourfold_default_net":float(q.fourfold_default_net.median()),"median_fourfold_severe_net":float(q.fourfold_severe_net.median()),"median_severe_range":float(q.severe_range.median())}
        for p in PERIODS:
            row[f"weakest_{p}"]=int(weak[p]); f=fm[fm.period==p]; row[f"median_default_net_{p}"]=float(f.default_net_pips.median()); row[f"median_severe_net_{p}"]=float(f.severe_net_pips.median())
        family_rows.append(row)
    family=pd.DataFrame(family_rows).sort_values(["severe_4fold_cells","default_4fold_cells","median_minimum_fold_severe_net"],ascending=[False,False,False])

    horizon_rows=[]
    for h,q in cell.groupby("horizon_bars",sort=True):
        weak=q.weakest_severe_fold.value_counts().reindex(PERIODS,fill_value=0); hm=m[m.horizon_bars==h]
        row={"horizon_bars":int(h),"cells":len(q),"default_4fold_cells":int((q.default_pass_folds==4).sum()),"severe_4fold_cells":int((q.severe_pass_folds==4).sum()),"median_default_pass_folds":float(q.default_pass_folds.median()),"median_severe_pass_folds":float(q.severe_pass_folds.median()),"median_minimum_fold_default_net":float(q.minimum_fold_default_net.median()),"median_minimum_fold_severe_net":float(q.minimum_fold_severe_net.median()),"median_fourfold_default_net":float(q.fourfold_default_net.median()),"median_fourfold_severe_net":float(q.fourfold_severe_net.median()),"median_severe_range":float(q.severe_range.median()),"median_trade_count":float(hm.trades.median())}
        for p in PERIODS: row[f"weakest_{p}"]=int(weak[p])
        horizon_rows.append(row)
    horizon=pd.DataFrame(horizon_rows).sort_values("horizon_bars")

    p=d.pivot_table(index=["candidate_id","family","horizon_bars","period"],columns="side",values=["default_net_pips","severe_net_pips","trades"],aggfunc="sum",fill_value=0).reset_index()
    p.columns=["candidate_id","family","horizon_bars","period"]+[f"{metric}_{'short' if side==-1 else 'long'}" for metric,side in p.columns[4:]]
    for c in ["severe_net_pips_short","severe_net_pips_long"]:
        if c not in p: p[c]=0.0
    p["dominant_severe_side"]=np.where(p.severe_net_pips_long>p.severe_net_pips_short,"long",np.where(p.severe_net_pips_short>p.severe_net_pips_long,"short","tie"))
    p["long_severe_positive"]=p.severe_net_pips_long>0; p["short_severe_positive"]=p.severe_net_pips_short>0; p["both_severe_positive"]=p.long_severe_positive&p.short_severe_positive
    direction_rows=[]
    for (cid,fam,h),q in p.groupby(["candidate_id","family","horizon_bars"],sort=True):
        q=q.set_index("period").reindex(PERIODS); dom=q.dominant_severe_side.tolist()
        direction_rows.append({"candidate_id":cid,"family":fam,"horizon_bars":int(h),"long_positive_folds":int(q.long_severe_positive.sum()),"short_positive_folds":int(q.short_severe_positive.sum()),"both_positive_folds":int(q.both_severe_positive.sum()),"same_dominant_side_all_folds":len(set(dom))==1,"dominant_side_sequence":"|".join(dom),"dominant_side_switches":int(sum(x!=y for x,y in zip(dom,dom[1:]))),"long_fourfold_severe_net":float(q.severe_net_pips_long.sum()),"short_fourfold_severe_net":float(q.severe_net_pips_short.sum())})
    direction_cell=pd.DataFrame(direction_rows)

    outputs={"cell":a.output/"usdjpy_rq021_cell_failure_taxonomy_v1.csv","family":a.output/"usdjpy_rq021_family_failure_taxonomy_v1.csv","horizon":a.output/"usdjpy_rq021_horizon_failure_taxonomy_v1.csv","direction_fold":a.output/"usdjpy_rq021_direction_fold_taxonomy_v1.csv","direction_stability":a.output/"usdjpy_rq021_direction_stability_v1.csv"}
    for frame,key in [(cell,"cell"),(family,"family"),(horizon,"horizon"),(p,"direction_fold"),(direction_cell,"direction_stability")]: frame.to_csv(outputs[key],index=False,lineterminator="\n")

    result={"schema_version":"usdjpy_rq021_architecture_failure_taxonomy_result_v1","status":"DESCRIPTIVE_TAXONOMY_COMPLETE_ONE_DISTINCT_QUESTION_IDENTIFIED","research_question":"USDJPY-RQ-021","source_scope":"already opened RQ-020E outputs only","source_sha256":{"cell_fold_metrics":sha(a.cell_fold_metrics),"direction_metrics":sha(a.direction_metrics)},"population":{"cells":len(cell),"families":cell.family.nunique(),"horizons":cell.horizon_bars.nunique(),"cell_fold_rows":len(m),"direction_rows":len(d)},"fold_pass_distribution":{"default":{str(k):int(v) for k,v in cell.default_pass_folds.value_counts().sort_index().items()},"severe":{str(k):int(v) for k,v in cell.severe_pass_folds.value_counts().sort_index().items()},"breadth":{str(k):int(v) for k,v in cell.breadth_pass_folds.value_counts().sort_index().items()}},"weakest_severe_fold_counts":{k:int(v) for k,v in cell.weakest_severe_fold.value_counts().items()},"direction_taxonomy":{"same_dominant_side_all_four_folds_cells":int(direction_cell.same_dominant_side_all_folds.sum()),"dominant_side_switch_at_least_once_cells":int((direction_cell.dominant_side_switches>=1).sum()),"dominant_side_switch_two_or_more_cells":int((direction_cell.dominant_side_switches>=2).sum()),"long_severe_positive_all_four_cells":int((direction_cell.long_positive_folds==4).sum()),"short_severe_positive_all_four_cells":int((direction_cell.short_positive_folds==4).sum()),"both_directions_severe_positive_all_four_cells":int((direction_cell.both_positive_folds==4).sum())},"retained_findings":["Cost fragility is architecture-wide: 14 cells pass all folds at default cost but only one at severe cost.","The weakest fold is distributed across all four periods; 2024H2 is most frequent but does not explain closure alone.","Dominant direction changes in 562 of 660 cells, so static M15 direction rules are strongly regime dependent.","No fixed horizon forms a robust family neighbourhood; longer holds improve isolated continuation cells but worsen median minimum-fold severe performance.","Session-handoff is the least-failed family but has only one isolated core cell and no full or neighbourhood pass."],"information_gap":{"identified_dimension":"native higher-timeframe state-transition architecture with state-conditional event termination","why_absent_from_R1_R2":"R1 entries are M15-local patterns or session references and R2 exits are unconditional fixed M15 horizons. A longer M15 lookback or 24/48-bar hold is not a completed H1/H4 state transition or event-defined termination.","duplicate_audit":{"Families_A_I":"shock/admission, overlap, event confirmation and checkpoint/state-adaptive repairs applied to existing B02/F05 or M15 signals","RQ_020B":"static 5-day/20-day state partitions and action routing, not native higher-timeframe signal construction","RQ_020E":"all frozen M15 Entry x fixed-time horizon cells","distinct_information":"primary signal and termination both use completed native higher-timeframe structure rather than an overlay on an M15 entry"},"successor_question_id":"USDJPY-RQ-022","successor_question":"Can a native H1/H4 state-transition architecture, with entry and termination events defined on completed higher-timeframe structure rather than an M15 pattern plus fixed horizon, produce a broad family region across all four development folds?","candidate_generated":False,"family_preregistered":False},"output_sha256":{k:sha(v) for k,v in outputs.items()},"boundaries":{"new_market_outcomes_accessed":False,"cell_retuned":False,"horizon_added":False,"candidate_generated":False,"family_preregistered":False,"MT4_accessed":False,"2025_accessed":False,"live_orders":False}}
    result=clean(result); (a.output/"usdjpy_rq021_architecture_failure_taxonomy_result_v1.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"); print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__": main()
