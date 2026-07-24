#!/usr/bin/env python3
"""Frozen six-cell native H4/H1 evaluator; supports outcome-free preflight."""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import pandas as pd
from usdjpy_native_htf_state_data_v1 import FOLDS,EXPECTED_CELLS,add_state,aggregate_exact,file_sha,load_m15_2023,load_m15_2024,profit_factor
from usdjpy_native_htf_state_sim_v1 import simulate_fold

def fold_metrics(trades:pd.DataFrame,fold:str)->dict:
 if trades.empty:return {"fold":fold,"trades":0,"core_pass":False,"full_pass":False}
 event=trades[~trades.boundary_liquidation];months=trades.groupby("entry_month").severe_net_pips.sum();quarters=trades.groupby("entry_quarter").severe_net_pips.sum();daily_d=trades.groupby("entry_date").default_net_pips.sum();daily_s=trades.groupby("entry_date").severe_net_pips.sum();start=FOLDS[fold][0];expected=[f"{start.year}-Q{(start.month-1)//3+1}",f"{start.year}-Q{(start.month-1)//3+2}"];q=quarters.reindex(expected,fill_value=0.0)
 dn=float(trades.default_net_pips.sum());sn=float(trades.severe_net_pips.sum());ed=float(event.default_net_pips.sum());es=float(event.severe_net_pips.sum());core=len(trades)>=10 and dn>0 and profit_factor(trades.default_net_pips)>=1 and sn>0 and profit_factor(trades.severe_net_pips)>=1 and len(event)>0 and ed>0 and profit_factor(event.default_net_pips)>=1 and es>0 and profit_factor(event.severe_net_pips)>=1 and bool((q>=0).all());exd=float(dn-daily_d.sort_values(ascending=False).head(2).sum());exs=float(sn-daily_s.sort_values(ascending=False).head(2).sum());full=core and int((months>0).sum())>=4 and int((months<0).sum())<=2 and exd>0 and exs>0
 return {"fold":fold,"trades":int(len(trades)),"event_exited_trades":int(len(event)),"boundary_liquidations":int(trades.boundary_liquidation.sum()),"default_net_pips":dn,"default_pf":profit_factor(trades.default_net_pips),"severe_net_pips":sn,"severe_pf":profit_factor(trades.severe_net_pips),"event_default_net_pips":ed,"event_default_pf":profit_factor(event.default_net_pips) if len(event) else 0.0,"event_severe_net_pips":es,"event_severe_pf":profit_factor(event.severe_net_pips) if len(event) else 0.0,"minimum_quarter_severe_net_pips":float(q.min()),"positive_months":int((months>0).sum()),"negative_months":int((months<0).sum()),"default_ex_best_two_dates_pips":exd,"severe_ex_best_two_dates_pips":exs,"core_pass":bool(core),"full_pass":bool(full)}
def pooled(trades:pd.DataFrame)->dict:
 daily=trades.groupby("entry_date").severe_net_pips.sum();pos=daily[daily>0].sort_values(ascending=False);den=float(pos.sum());largest=0 if den==0 else float(pos.head(1).sum()/den);top2=0 if den==0 else float(pos.head(2).sum()/den);counts=trades.side.value_counts().reindex([-1,1],fill_value=0);total=int(counts.sum());ss=0 if total==0 else float(counts[-1]/total);ls=0 if total==0 else float(counts[1]/total);event=trades[~trades.boundary_liquidation];ed=float(event.default_net_pips.sum());es=float(event.severe_net_pips.sum());passed=largest<=.35 and top2<=.55 and ss>=.2 and ls>=.2 and ed>0 and es>0
 return {"largest_positive_date_share":largest,"top_two_positive_date_share":top2,"short_position_share":ss,"long_position_share":ls,"event_only_default_net_pips":ed,"event_only_severe_net_pips":es,"pooled_pass":bool(passed)}
def components(cells:pd.DataFrame)->tuple[list[list[str]],list[str]]:
 core={(int(r.h4_index),int(r.h1_index)):r.candidate_id for r in cells.itertuples() if r.core_all_folds};visited=set();out=[]
 for node in core:
  if node in visited:continue
  stack=[node];visited.add(node);comp=[]
  while stack:
   cur=stack.pop();comp.append(core[cur])
   for nb in [(cur[0]-1,cur[1]),(cur[0]+1,cur[1]),(cur[0],cur[1]-1),(cur[0],cur[1]+1)]:
    if nb in core and nb not in visited:visited.add(nb);stack.append(nb)
  out.append(sorted(comp))
 full=set(cells.loc[cells.full_all_gates,"candidate_id"]);eligible=sorted({x for comp in out if len(comp)>=2 and full.intersection(comp) for x in comp});return out,eligible
def main()->None:
 ap=argparse.ArgumentParser();ap.add_argument("--m15-2023",type=Path,required=True);ap.add_argument("--m15-2024",type=Path,required=True);ap.add_argument("--protocol",type=Path,required=True);ap.add_argument("--output-dir",type=Path,required=True);ap.add_argument("--preflight-only",action="store_true");a=ap.parse_args();protocol=json.loads(a.protocol.read_text());assert protocol["finite_grid"]["candidate_ids"]==[x[0] for x in EXPECTED_CELLS] and protocol["status"]=="FROZEN_BEFORE_CANDIDATE_SIGNAL_OR_OUTCOME_EVALUATION"
 m15=pd.concat([load_m15_2023(a.m15_2023),load_m15_2024(a.m15_2024)],ignore_index=True).sort_values("logical_utc").reset_index(drop=True);h1b=aggregate_exact(m15,"1h",4);h4b=aggregate_exact(m15,"4h",16);pre={"schema_version":"usdjpy_native_h4_h1_ema_state_transition_preflight_v1","status":"PASS","protocol_sha256":file_sha(a.protocol),"evaluator_sha256":file_sha(Path(__file__)),"data_module_sha256":file_sha(Path(__file__).with_name("usdjpy_native_htf_state_data_v1.py")),"simulation_module_sha256":file_sha(Path(__file__).with_name("usdjpy_native_htf_state_sim_v1.py")),"m15_rows":len(m15),"h1_exact_rows":len(h1b),"h4_exact_rows":len(h4b),"candidate_count":len(EXPECTED_CELLS),"execution_time_duplicates":int(m15.logical_utc.duplicated().sum()),"fold_m15_rows":{f:int(((m15.logical_utc>=s)&(m15.logical_utc<e)).sum()) for f,(s,e) in FOLDS.items()},"outcomes_computed":not a.preflight_only};a.output_dir.mkdir(parents=True,exist_ok=True);(a.output_dir/"usdjpy_native_h4_h1_ema_state_transition_preflight_v1.json").write_text(json.dumps(pre,indent=2,sort_keys=True)+"\n")
 if a.preflight_only:print(json.dumps(pre,indent=2,sort_keys=True));return
 signals_all=[];trades_all=[];metrics_rows=[];cell_rows=[]
 for cid,h4f,h4s,h1f,h1s,i4,i1 in EXPECTED_CELLS:
  h4=add_state(h4b,h4f,h4s,"h4");h1=add_state(h1b,h1f,h1s,"h1");candidate_trades=[];candidate_metrics=[]
  for fold,(start,end) in FOLDS.items():
   signals,trades=simulate_fold(cid,h4,h1,m15,start,end);signals.insert(1,"fold",fold);trades.insert(1,"fold",fold);signals_all.append(signals);trades_all.append(trades);candidate_trades.append(trades);row=fold_metrics(trades,fold);row.update({"candidate_id":cid,"h4_fast":h4f,"h4_slow":h4s,"h1_fast":h1f,"h1_slow":h1s});metrics_rows.append(row);candidate_metrics.append(row)
  alltr=pd.concat(candidate_trades,ignore_index=True);pg=pooled(alltr);core=all(r["core_pass"] for r in candidate_metrics);full=all(r["full_pass"] for r in candidate_metrics);cell_rows.append({"candidate_id":cid,"h4_fast":h4f,"h4_slow":h4s,"h1_fast":h1f,"h1_slow":h1s,"h4_index":i4,"h1_index":i1,"core_all_folds":core,"full_each_fold":full,**pg,"full_all_gates":bool(core and full and pg["pooled_pass"]),"minimum_fold_severe_net":min(r.get("severe_net_pips",-math.inf) for r in candidate_metrics),"minimum_quarter_severe_net":min(r.get("minimum_quarter_severe_net_pips",-math.inf) for r in candidate_metrics),"pooled_severe_net":float(alltr.severe_net_pips.sum())})
 signals=pd.concat(signals_all,ignore_index=True);trades=pd.concat(trades_all,ignore_index=True);fm=pd.DataFrame(metrics_rows);cells=pd.DataFrame(cell_rows);comps,eligible=components(cells);finalist=None
 if eligible:finalist=str(cells[cells.candidate_id.isin(eligible)].sort_values(["minimum_fold_severe_net","minimum_quarter_severe_net","pooled_severe_net"],ascending=False).iloc[0].candidate_id)
 outputs={"usdjpy_native_h4_h1_signals_v1.csv":signals,"usdjpy_native_h4_h1_trades_v1.csv":trades,"usdjpy_native_h4_h1_fold_metrics_v1.csv":fm,"usdjpy_native_h4_h1_cell_summary_v1.csv":cells}
 for name,frame in outputs.items():frame.to_csv(a.output_dir/name,index=False,lineterminator="\n")
 result={"schema_version":"usdjpy_native_h4_h1_ema_state_transition_result_v1","status":"ELIGIBLE_FAMILY_REGION" if finalist else "CLOSED_NO_ELIGIBLE_FAMILY_REGION","candidate_count":6,"core_cells":int(cells.core_all_folds.sum()),"full_cells":int(cells.full_all_gates.sum()),"core_components":comps,"eligible_component_candidates":eligible,"finalist":finalist,"cells":cells.to_dict("records"),"boundaries":{"2025_accessed":False,"MT4_accessed":False,"grid_expanded":False,"gate_changed":False},"output_sha256":{n:file_sha(a.output_dir/n) for n in outputs}};(a.output_dir/"usdjpy_native_h4_h1_ema_state_transition_result_v1.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__":main()
