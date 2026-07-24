#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd
from run_usdjpy_r1_entry_registry_v2 import SIGNAL_FUNCTIONS, validate_registry, hard_exclusion_mask
from usdjpy_fixed5_portability_lib_v1 import load23, load24

HORIZONS=[1,2,3,4,6,8,12,16,24,32,48]
PERIODS={
 "2023H1":(pd.Timestamp("2023-01-01",tz="UTC"),pd.Timestamp("2023-07-01",tz="UTC")),
 "2023H2":(pd.Timestamp("2023-07-01",tz="UTC"),pd.Timestamp("2024-01-01",tz="UTC")),
 "2024H1":(pd.Timestamp("2024-01-01",tz="UTC"),pd.Timestamp("2024-07-01",tz="UTC")),
 "2024H2":(pd.Timestamp("2024-07-01",tz="UTC"),pd.Timestamp("2025-01-01",tz="UTC")),
}

def sha256_file(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
 return h.hexdigest()

def finalize(bars,candidate,side,session):
 work=pd.DataFrame({"signal_dt":bars.timestamp_utc,"entry_dt":bars.timestamp_utc.shift(-1),"side":side.fillna(0).astype("int8")})
 work=work[work.side.isin([-1,1])&work.entry_dt.notna()].copy()
 work=work[~hard_exclusion_mask(work.entry_dt,session)].copy()
 work["candidate_id"]=candidate["id"];work["family"]=candidate["family"];work["definition_sha256"]=candidate["definition_sha256"]
 work["signal_ts"]=work.signal_dt.dt.strftime("%Y-%m-%dT%H:%M:%SZ");work["entry_ts"]=work.entry_dt.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
 work["signal_month"]=work.signal_dt.dt.strftime("%Y-%m");work["signal_hour_utc"]=work.signal_dt.dt.hour.astype(int)
 work["entry_month"]=work.entry_dt.dt.strftime("%Y-%m");work["entry_hour_utc"]=work.entry_dt.dt.hour.astype(int)
 cols=["candidate_id","family","definition_sha256","signal_ts","entry_ts","side","signal_month","signal_hour_utc","entry_month","entry_hour_utc"]
 return work[cols].sort_values(["candidate_id","signal_ts","side"]).reset_index(drop=True)

def year_signals(bars,candidates,session):
 return pd.concat([finalize(bars,c,SIGNAL_FUNCTIONS[c["family"]](bars,c),session) for c in candidates],ignore_index=True).sort_values(["candidate_id","signal_ts","side"]).reset_index(drop=True)

def period_signals(signals,start,end):
 entry=pd.to_datetime(signals.entry_ts,utc=True)
 return signals[(entry>=start)&(entry<end)].copy().reset_index(drop=True)

def regress_h1(actual,path):
 accepted=pd.read_csv(path);cols=list(accepted.columns)
 left=accepted[cols].sort_values(["candidate_id","signal_ts","side"]).reset_index(drop=True)
 right=actual[cols].sort_values(["candidate_id","signal_ts","side"]).reset_index(drop=True)
 for frame in (left,right):
  for c in ["side","signal_hour_utc","entry_hour_utc"]:frame[c]=frame[c].astype("int64")
 return {"accepted_rows":len(left),"actual_rows":len(right),"exact":bool(left.equals(right)),"accepted_sha256":sha256_file(path)}

def build_trades(bars,signals,period,start,end):
 index_by_ts=pd.Series(bars.index.to_numpy(),index=bars.timestamp_utc).to_dict();w=signals.copy();w["entry_dt"]=pd.to_datetime(w.entry_ts,utc=True);w["entry_index"]=w.entry_dt.map(index_by_ts);assert w.entry_index.notna().all()
 opens=bars.mid_open.to_numpy(float);closes=bars.mid_close.to_numpy(float);spreads=bars.spread_mean_pips.to_numpy(float);timestamps=bars.timestamp_utc.tolist();months=bars.month_utc.to_numpy(str);dates=bars.date_utc.to_numpy(str)
 entry_index=w.entry_index.astype(int).to_numpy();side=w.side.astype(int).to_numpy();frames=[]
 for horizon in HORIZONS:
  exit_index=entry_index+horizon-1;valid=exit_index<len(bars);clip=np.minimum(exit_index,len(bars)-1)
  valid&=np.array([timestamps[i]>=start for i in entry_index]);valid&=np.array([timestamps[i]<end for i in clip]);valid&=months[entry_index]==months[clip]
  pos=np.where(valid)[0]
  if not len(pos):continue
  ei=entry_index[pos];xi=exit_index[pos];selected=w.iloc[pos].reset_index(drop=True);sides=side[pos];cost=np.maximum(.5,spreads[ei]);severe=3*cost+1;gross=sides*(closes[xi]-opens[ei])/.01
  frames.append(pd.DataFrame({"period":period,"candidate_id":selected.candidate_id.to_numpy(),"family":selected.family.to_numpy(),"definition_sha256":selected.definition_sha256.to_numpy(),"horizon_bars":horizon,"entry_ts":selected.entry_ts.to_numpy(),"entry_month":months[ei],"entry_date_utc":dates[ei],"side":sides,"gross_pips":gross,"default_net_pips":gross-cost,"severe_net_pips":gross-severe}))
 return pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()

def pf(values):
 gain=float(values[values>0].sum());loss=float(-values[values<0].sum())
 return math.inf if loss==0 and gain>0 else (0.0 if loss==0 else gain/loss)

def aggregate(trades,candidates):
 rows=[];direction=[]
 for (cid,family,horizon,period),group in trades.groupby(["candidate_id","family","horizon_bars","period"],sort=True):
  monthly=group.groupby("entry_month").default_net_pips.sum();daily=group.groupby("entry_date_utc").default_net_pips.sum()
  rows.append({"candidate_id":cid,"family":family,"horizon_bars":int(horizon),"period":period,"trades":len(group),"default_net_pips":float(group.default_net_pips.sum()),"default_pf":float(pf(group.default_net_pips)),"severe_net_pips":float(group.severe_net_pips.sum()),"severe_pf":float(pf(group.severe_net_pips)),"positive_months":int((monthly>0).sum()),"negative_months":int((monthly<0).sum()),"ex_best_two_dates":float(group.default_net_pips.sum()-daily.sort_values(ascending=False).head(2).sum())})
  for side,part in group.groupby("side",sort=True):direction.append({"candidate_id":cid,"family":family,"horizon_bars":int(horizon),"period":period,"side":int(side),"trades":len(part),"default_net_pips":float(part.default_net_pips.sum()),"severe_net_pips":float(part.severe_net_pips.sum())})
 metrics=pd.DataFrame(rows);gate_rows=[]
 for candidate in candidates:
  for horizon in HORIZONS:
   q=metrics[(metrics.candidate_id==candidate["id"])&(metrics.horizon_bars==horizon)].set_index("period").reindex(PERIODS)
   support=bool((q.trades.fillna(0)>=20).all());core=support and bool(((q.default_net_pips>0)&(q.default_pf>=1)&(q.severe_net_pips>0)&(q.severe_pf>=1)).all());full=core and bool(((q.positive_months>=4)&(q.negative_months<=2)&(q.ex_best_two_dates>0)).all())
   gate_rows.append({"candidate_id":candidate["id"],"family":candidate["family"],"definition_sha256":candidate["definition_sha256"],"horizon_bars":horizon,"support_pass":support,"core_pass":core,"full_pass":full,"minimum_fold_default_net":float(q.default_net_pips.min()),"minimum_fold_severe_net":float(q.severe_net_pips.min()),"minimum_fold_trades":int(q.trades.min()) if q.trades.notna().all() else 0,"fourfold_default_net":float(q.default_net_pips.sum()),"fourfold_severe_net":float(q.severe_net_pips.sum())})
 return metrics,pd.DataFrame(direction),pd.DataFrame(gate_rows)

def signal_hash(signals,cid):
 q=signals[signals.candidate_id==cid][["signal_ts","entry_ts","side"]].sort_values(["signal_ts","entry_ts","side"])
 return hashlib.sha256(q.to_csv(index=False,lineterminator="\n").encode()).hexdigest()

def neighbourhoods(gates,signals):
 rows=[]
 for cid,group in gates.groupby("candidate_id",sort=True):
  g=group.set_index("horizon_bars").reindex(HORIZONS);runs=[];current=[]
  for horizon in HORIZONS:
   if bool(g.loc[horizon,"core_pass"]):current.append(horizon)
   else:
    if current:runs.append(current);current=[]
  if current:runs.append(current)
  qualifying=[run for run in runs if len(run)>=3 and bool(g.loc[run,"full_pass"].any())]
  rows.append({"candidate_id":cid,"family":g.family.dropna().iloc[0],"definition_sha256":g.definition_sha256.dropna().iloc[0],"signal_ledger_sha256":signal_hash(signals,cid),"max_core_contiguous_horizons":max([len(run) for run in runs],default=0),"core_runs_json":json.dumps(runs),"qualifying_runs_json":json.dumps(qualifying),"neighbourhood_pass":bool(qualifying),"full_gate_horizons_json":json.dumps([int(h) for h in HORIZONS if bool(g.loc[h,"full_pass"])])})
 return pd.DataFrame(rows)

def family_regions(gates,entries):
 rows=[]
 for family,group in entries.groupby("family",sort=True):
  passed=group[group.neighbourhood_pass];core=gates[(gates.family==family)&gates.core_pass];median_min=float(core.minimum_fold_severe_net.median()) if len(core) else float("-inf")
  row={"family":family,"entry_definitions":len(group),"neighbourhood_entries":len(passed),"distinct_neighbourhood_signal_hashes":passed.signal_ledger_sha256.nunique(),"core_cells":len(core),"full_cells":int(gates[gates.family==family].full_pass.sum()),"median_core_minimum_fold_severe_net":median_min,"median_core_fourfold_severe_net":float(core.fourfold_severe_net.median()) if len(core) else float("-inf")}
  row["family_region_pass"]=bool(row["neighbourhood_entries"]>=2 and row["distinct_neighbourhood_signal_hashes"]>=2 and median_min>0);rows.append(row)
 return pd.DataFrame(rows).sort_values(["family_region_pass","neighbourhood_entries","full_cells","median_core_minimum_fold_severe_net","median_core_fourfold_severe_net"],ascending=[False,False,False,False,False]).reset_index(drop=True)

def main():
 parser=argparse.ArgumentParser();parser.add_argument("--m15-2023",type=Path,required=True);parser.add_argument("--m15-2024",type=Path,required=True);parser.add_argument("--registry",type=Path,required=True);parser.add_argument("--session-config",type=Path,required=True);parser.add_argument("--accepted-h1-signals",type=Path,required=True);parser.add_argument("--output-dir",type=Path,required=True);args=parser.parse_args()
 registry=json.load(open(args.registry));session=json.load(open(args.session_config));validated=validate_registry(registry);candidates=validated[0] if isinstance(validated,tuple) else validated;assert len(candidates)==60
 bars23=load23(args.m15_2023);bars24=load24(args.m15_2024)
 for bars in (bars23,bars24):
  bars["bar_range"]=bars.mid_high-bars.mid_low;bars["close_change"]=bars.mid_close.diff()
 signals23=year_signals(bars23,candidates,session);signals24=year_signals(bars24,candidates,session)
 regression=regress_h1(period_signals(signals24,*PERIODS["2024H1"]),args.accepted_h1_signals);assert regression["exact"],regression
 frames=[]
 for period,(start,end) in PERIODS.items():
  bars=bars23 if period.startswith("2023") else bars24;signals=signals23 if period.startswith("2023") else signals24;frames.append(build_trades(bars,period_signals(signals,start,end),period,start,end))
 trades=pd.concat(frames,ignore_index=True);metrics,direction,gates=aggregate(trades,candidates);all_signals=pd.concat([signals23,signals24],ignore_index=True);entries=neighbourhoods(gates,all_signals);families=family_regions(gates,entries);passing=families[families.family_region_pass];authorized=passing.head(1).family.tolist() if len(passing) else []
 output=args.output_dir;output.mkdir(parents=True,exist_ok=True)
 files={"usdjpy_full_architecture_fourfold_cell_metrics_v1.csv":metrics,"usdjpy_full_architecture_fourfold_direction_metrics_v1.csv":direction,"usdjpy_full_architecture_cell_gates_v1.csv":gates,"usdjpy_full_architecture_entry_neighbourhoods_v1.csv":entries,"usdjpy_full_architecture_family_regions_v1.csv":families}
 for name,frame in files.items():frame.to_csv(output/name,index=False)
 result={"schema_version":"usdjpy_full_frozen_architecture_census_result_v1","status":"FAMILY_REGION_FOUND" if authorized else "CLOSED_NO_ROBUST_FAMILY_REGION","decision":"AUTHORIZE_SEPARATE_FINITE_FAMILY_PREREGISTRATION" if authorized else "CLOSE_RQ_020E_REASSESS_M15_FIXED_TIME_ARCHITECTURE","h1_signal_regression":regression,"population":{"trade_rows":len(trades),"period_trade_rows":trades.groupby("period").size().astype(int).to_dict(),"cell_period_rows":len(metrics),"direction_rows":len(direction),"cells":len(gates),"entries":len(entries),"families":len(families)},"gate_counts":{"support_cells":int(gates.support_pass.sum()),"core_cells":int(gates.core_pass.sum()),"full_cells":int(gates.full_pass.sum()),"neighbourhood_entries":int(entries.neighbourhood_pass.sum()),"family_regions":int(families.family_region_pass.sum())},"authorized_successor_family_regions":authorized,"family_regions":families.to_dict("records"),"boundaries":{"single_combination_selected":False,"entry_or_horizon_changed":False,"weights_optimized":False,"2024_source_mutated":False,"2025_accessed":False,"MT4_accessed":False,"live_orders":False}}
 result["output_sha256"]={path.name:sha256_file(path) for path in output.iterdir() if path.is_file()};(output/"usdjpy_full_frozen_architecture_census_result_v1.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__":main()
