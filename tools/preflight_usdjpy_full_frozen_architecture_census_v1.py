from __future__ import annotations
import json, hashlib, math, io, gzip
from pathlib import Path
import numpy as np, pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
PIP=0.01
H1_END=pd.Timestamp("2024-07-01T00:00:00Z")
H1_MONTHS=[f"2024-{m:02d}" for m in range(1,7)]
DIRECTIONS=[-1,1]
HORIZONS=[1,2,3,4,6,8,12,16,24,32,48]
def sha256_file(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for c in iter(lambda:f.read(1<<20),b''): h.update(c)
 return h.hexdigest()
def canonical_candidate_definition(family,candidate):
 metadata={"id","origin","legacy_ids","h2_information_status","literature_refs","family"}
 payload={"family":family,"parameters":{k:v for k,v in candidate.items() if k not in metadata}}
 text=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":"))
 return text, hashlib.sha256((text+"\n").encode()).hexdigest()
def csv_bytes(frame,float_format="%.12f"):
 return frame.to_csv(index=False,float_format=float_format,lineterminator="\n",na_rep="").encode()
def deterministic_gzip(payload):
 t=io.BytesIO()
 with gzip.GzipFile(filename="",mode="wb",fileobj=t,mtime=0,compresslevel=6) as h:h.write(payload)
 return t.getvalue()
def load_inputs(canonical_path,signal_path,registry_path):
 bars=pd.read_csv(canonical_path)
 required=["timestamp_utc","symbol","mid_open","mid_high","mid_low","mid_close","spread_mean_pips"]
 bars=bars[required].copy();bars.timestamp_utc=pd.to_datetime(bars.timestamp_utc,utc=True)
 for c in required[2:]:bars[c]=pd.to_numeric(bars[c])
 assert (bars.symbol=="USDJPY").all() and not bars.timestamp_utc.duplicated().any() and bars.timestamp_utc.is_monotonic_increasing
 bars=bars.reset_index(drop=True);bars["month_utc"]=bars.timestamp_utc.dt.strftime("%Y-%m");bars["date_utc"]=bars.timestamp_utc.dt.strftime("%Y-%m-%d")
 sig=pd.read_csv(signal_path);cols=["candidate_id","family","definition_sha256","signal_ts","entry_ts","side"];sig=sig[cols].copy();sig.signal_ts=pd.to_datetime(sig.signal_ts,utc=True);sig.entry_ts=pd.to_datetime(sig.entry_ts,utc=True);sig.side=sig.side.astype(int)
 assert sig.side.isin([-1,1]).all() and (sig.entry_ts>sig.signal_ts).all() and (sig.entry_ts<H1_END).all() and not sig.duplicated(["candidate_id","signal_ts","side"]).any()
 return bars,sig,json.load(open(registry_path,encoding="utf-8"))
def build_trades(bars,signals,candidates,horizons):
 mp=pd.Series(bars.index.to_numpy(),index=bars.timestamp_utc).to_dict();opens=bars.mid_open.to_numpy(float);highs=bars.mid_high.to_numpy(float);lows=bars.mid_low.to_numpy(float);closes=bars.mid_close.to_numpy(float);spreads=bars.spread_mean_pips.to_numpy(float);timestamps=bars.timestamp_utc.tolist();months=bars.month_utc.to_numpy(str);dates=bars.date_utc.to_numpy(str)
 work=signals.copy();work["entry_index"]=work.entry_ts.map(mp);assert work.entry_index.notna().all();ei_all=work.entry_index.astype(int).to_numpy();side_all=work.side.to_numpy(int);cid_all=work.candidate_id.to_numpy(str);fam_all=work.family.to_numpy(str);def_all=work.definition_sha256.to_numpy(str);sig_all=work.signal_ts.tolist();entry_all=work.entry_ts.tolist();frames=[]
 for h in horizons:
  xi_all=ei_all+h-1;pos=np.where(xi_all<len(bars))[0];same=months[ei_all[pos]]==months[xi_all[pos]];before=np.array([timestamps[i]<H1_END for i in xi_all[pos]]);pos=pos[same&before]
  if not len(pos):continue
  ei=ei_all[pos];xi=xi_all[pos];side=side_all[pos];entry_mid=opens[ei];exit_mid=closes[xi];entry_spread=spreads[ei];default_cost=np.maximum(.5,entry_spread);severe_cost=default_cost*3+1;gross=side*(exit_mid-entry_mid)/PIP
  high_windows=sliding_window_view(highs,h);low_windows=sliding_window_view(lows,h);selected_high=high_windows[ei];selected_low=low_windows[ei];high_max=selected_high.max(1);low_min=selected_low.min(1);high_argmax=selected_high.argmax(1)+1;low_argmin=selected_low.argmin(1)+1;long_mask=side==1
  raw_mfe=np.where(long_mask,(high_max-entry_mid)/PIP,(entry_mid-low_min)/PIP);raw_mae=np.where(long_mask,(low_min-entry_mid)/PIP,(entry_mid-high_max)/PIP);mfe=np.maximum(0,raw_mfe);mae=np.minimum(0,raw_mae);bars_to_mfe=np.where(raw_mfe>0,np.where(long_mask,high_argmax,low_argmin),0);bars_to_mae=np.where(raw_mae<0,np.where(long_mask,low_argmin,high_argmax),0)
  frames.append(pd.DataFrame({"candidate_id":cid_all[pos],"family":fam_all[pos],"definition_sha256":def_all[pos],"horizon_bars":h,"signal_ts":[sig_all[i] for i in pos],"entry_ts":[entry_all[i] for i in pos],"exit_ts":[timestamps[i] for i in xi],"entry_month":months[ei],"entry_date_utc":dates[ei],"side":side,"entry_mid":entry_mid,"exit_mid":exit_mid,"entry_spread_pips":entry_spread,"gross_pips":gross,"default_cost_pips":default_cost,"severe_cost_pips":severe_cost,"default_net_pips":gross-default_cost,"severe_net_pips":gross-severe_cost,"mfe_pips":mfe,"mae_pips":mae,"bars_to_mfe":bars_to_mfe.astype(int),"bars_to_mae":bars_to_mae.astype(int)}))
 return pd.concat(frames,ignore_index=True).sort_values(["candidate_id","horizon_bars","entry_ts","side"]).reset_index(drop=True)
def _aggregate(frame,keys,daily):
 w=frame.copy();w["win_default"]=(w.default_net_pips>0).astype(float);w["default_gain"]=w.default_net_pips.clip(lower=0);w["default_loss"]=-w.default_net_pips.clip(upper=0);w["severe_gain"]=w.severe_net_pips.clip(lower=0);w["severe_loss"]=-w.severe_net_pips.clip(upper=0);grouped=w.groupby(keys,sort=True,observed=True)
 out=grouped.agg(trades=("default_net_pips","size"),win_rate=("win_default","mean"),avg_gross_pips=("gross_pips","mean"),avg_default_net_pips=("default_net_pips","mean"),total_default_net_pips=("default_net_pips","sum"),default_gains=("default_gain","sum"),default_losses=("default_loss","sum"),avg_severe_net_pips=("severe_net_pips","mean"),total_severe_net_pips=("severe_net_pips","sum"),severe_gains=("severe_gain","sum"),severe_losses=("severe_loss","sum"),median_default_net_pips=("default_net_pips","median"),avg_mfe_pips=("mfe_pips","mean"),avg_mae_pips=("mae_pips","mean"),median_mfe_pips=("mfe_pips","median"),median_mae_pips=("mae_pips","median"),avg_bars_to_mfe=("bars_to_mfe","mean"),avg_bars_to_mae=("bars_to_mae","mean")).reset_index();q05=grouped.default_net_pips.quantile(.05).rename("q05_default_net_pips").reset_index();q95=grouped.default_net_pips.quantile(.95).rename("q95_default_net_pips").reset_index();out=out.merge(q05,on=keys).merge(q95,on=keys)
 out["default_profit_factor"]=np.where(out.default_losses>0,out.default_gains/out.default_losses,np.where(out.default_gains>0,np.inf,0));out["severe_profit_factor"]=np.where(out.severe_losses>0,out.severe_gains/out.severe_losses,np.where(out.severe_gains>0,np.inf,0));out=out.drop(columns=["default_gains","default_losses","severe_gains","severe_losses"])
 if daily:
  d=w.groupby(keys+["entry_date_utc"],sort=True,observed=True).default_net_pips.sum().rename("daily_net").reset_index();d=d.sort_values(keys+["daily_net"],ascending=[True]*len(keys)+[False]);d["daily_rank"]=d.groupby(keys,sort=False).cumcount()+1;b1=d[d.daily_rank==1].set_index(keys).daily_net;b2=d[d.daily_rank<=2].groupby(keys).daily_net.sum();idx=pd.MultiIndex.from_frame(out[keys]) if len(keys)>1 else pd.Index(out[keys[0]]);out["total_excluding_best_utc_day"]=out.total_default_net_pips.to_numpy()-b1.reindex(idx,fill_value=0).to_numpy();out["total_excluding_best_two_utc_days"]=out.total_default_net_pips.to_numpy()-b2.reindex(idx,fill_value=0).to_numpy()
 else:out["total_excluding_best_utc_day"]=0.;out["total_excluding_best_two_utc_days"]=0.
 return out
def _complete(base,aggregate,keys):
 r=base.merge(aggregate,on=keys,how="left");non=[c for c in r.columns if c not in keys+["family","definition_sha256"]];r[non]=r[non].fillna(0.);r["trades"]=r.trades.astype(int);return r
def build_reports(trades,candidates,horizons):
 candidate_frame=pd.DataFrame(candidates)[["candidate_id","family","definition_sha256"]];horizon_frame=pd.DataFrame({"horizon_bars":horizons});candidate_frame["_join"]=1;horizon_frame["_join"]=1;grid=candidate_frame.merge(horizon_frame,on="_join").drop(columns="_join")
 summary=_complete(grid,_aggregate(trades,["candidate_id","horizon_bars"],True),["candidate_id","horizon_bars"]);month_frame=pd.DataFrame({"month":H1_MONTHS});grid["_join"]=1;month_frame["_join"]=1;monthly_grid=grid.merge(month_frame,on="_join").drop(columns="_join");monthly_source=trades.rename(columns={"entry_month":"month"});monthly=_complete(monthly_grid,_aggregate(monthly_source,["candidate_id","horizon_bars","month"],False),["candidate_id","horizon_bars","month"]);flags=monthly.assign(positive=(monthly.trades>0)&(monthly.avg_default_net_pips>0));stats=flags.groupby(["candidate_id","horizon_bars"],sort=True).agg(positive_months=("positive","sum"),minimum_monthly_trades=("trades","min")).reset_index();summary=summary.merge(stats,on=["candidate_id","horizon_bars"]);summary[["positive_months","minimum_monthly_trades"]]=summary[["positive_months","minimum_monthly_trades"]].astype(int)
 direction_frame=pd.DataFrame({"side":DIRECTIONS});grid["_join"]=1;direction_frame["_join"]=1;direction_grid=grid.merge(direction_frame,on="_join").drop(columns="_join");direction=_complete(direction_grid,_aggregate(trades,["candidate_id","horizon_bars","side"],False),["candidate_id","horizon_bars","side"]);direction.side=direction.side.astype(int)
 ledger_columns=["signal_ts","entry_ts","exit_ts","side","entry_mid","exit_mid","entry_spread_pips","gross_pips","default_cost_pips","severe_cost_pips","default_net_pips","severe_net_pips","mfe_pips","mae_pips","bars_to_mfe","bars_to_mae"];groups={(str(c),int(h)):g for (c,h),g in trades.groupby(["candidate_id","horizon_bars"],sort=False)};empty=trades.iloc[:0];hash_rows=[]
 for row in grid.itertuples(index=False):
  g=groups.get((row.candidate_id,int(row.horizon_bars)),empty);normalized=g[ledger_columns].copy()
  for column in ["signal_ts","entry_ts","exit_ts"]:normalized[column]=pd.to_datetime(normalized[column],utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
  payload=csv_bytes(normalized.sort_values(["entry_ts","side"]).reset_index(drop=True),"%.10f");hash_rows.append({"candidate_id":row.candidate_id,"family":row.family,"definition_sha256":row.definition_sha256,"horizon_bars":int(row.horizon_bars),"trade_rows":int(len(g)),"trade_ledger_sha256":hashlib.sha256(payload).hexdigest()})
 hashes=pd.DataFrame(hash_rows);surface_rows=[]
 for candidate_id,current in summary.groupby("candidate_id",sort=True):
  current=current.set_index("horizon_bars").reindex(horizons);positive=((current.trades>0)&(current.avg_default_net_pips>0)).tolist();longest=running=0
  for flag in positive:running=running+1 if flag else 0;longest=max(longest,running)
  with_trades=current[current.trades>0];best_horizon=int(with_trades.avg_default_net_pips.idxmax()) if len(with_trades) else 0;best_average=float(with_trades.avg_default_net_pips.max()) if len(with_trades) else 0.;first=current.iloc[0];surface_rows.append({"candidate_id":candidate_id,"family":first.family,"definition_sha256":first.definition_sha256,"reported_horizons":len(horizons),"horizons_with_trades":int((current.trades>0).sum()),"positive_default_horizons":int((current.avg_default_net_pips>0).sum()),"positive_severe_horizons":int((current.avg_severe_net_pips>0).sum()),"longest_positive_default_run":int(longest),"diagnostic_best_horizon_bars":best_horizon,"best_avg_default_net_pips":best_average,"hold6_avg_default_net_pips":float(current.loc[6,"avg_default_net_pips"]),"total_trade_rows_across_horizons":int(current.trades.sum())})
 return summary.sort_values(["candidate_id","horizon_bars"]).reset_index(drop=True),monthly.sort_values(["candidate_id","horizon_bars","month"]).reset_index(drop=True),direction.sort_values(["candidate_id","horizon_bars","side"]).reset_index(drop=True),pd.DataFrame(surface_rows).sort_values("candidate_id").reset_index(drop=True),hashes.sort_values(["candidate_id","horizon_bars"]).reset_index(drop=True)
def main():
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument("--canonical-m15",type=Path,required=True);ap.add_argument("--signals",type=Path,required=True);ap.add_argument("--registry-snapshot",type=Path,required=True);ap.add_argument("--accepted-dir",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);args=ap.parse_args()
 expected_inputs={"canonical":"1566b9d0497f3a2aa156868144d31b89721fca48329feaf82035826ada7ee25c","signals":"99c2e2d19bd76b2438c1cec6c777228f82cdca16eeb1b471257bd389d6b7dc9e","registry":"3bb43eeb1234ec6d175e37df3b1bbdb385364857351938bd088247ab14567549"};actual_inputs={"canonical":sha256_file(args.canonical_m15),"signals":sha256_file(args.signals),"registry":sha256_file(args.registry_snapshot)};assert actual_inputs==expected_inputs,(actual_inputs,expected_inputs)
 bars,signals,registry=load_inputs(args.canonical_m15,args.signals,args.registry_snapshot);candidates=[]
 for family_block in registry["families"]:
  family=str(family_block["family"])
  for candidate in family_block["candidates"]:
   _,definition_sha256=canonical_candidate_definition(family,candidate);candidates.append({"candidate_id":str(candidate["id"]),"family":family,"definition_sha256":definition_sha256})
 candidates.sort(key=lambda row:row["candidate_id"]);assert len(candidates)==60 and len({row["candidate_id"] for row in candidates})==60;observed=signals.groupby("candidate_id")["definition_sha256"].first().to_dict()
 for row in candidates:
  if row["candidate_id"] in observed:assert observed[row["candidate_id"]]==row["definition_sha256"]
 trades=build_trades(bars,signals,candidates,HORIZONS);summary,monthly,direction,surface,hashes=build_reports(trades,candidates,HORIZONS);generated={"candidate_horizon_summary.csv":summary,"candidate_horizon_monthly.csv":monthly,"candidate_horizon_direction.csv":direction,"candidate_horizon_surface.csv":surface,"candidate_horizon_hashes.csv":hashes};expected_sha={"candidate_horizon_trades.csv.gz":"70c2313147607096976a76328b72a628e42fa0001816f14824bcd9e9a3ead6c6","candidate_horizon_summary.csv":"fa46a5db3e73c4d25b8e8c97ef4727c39d737cc8823080b23d21b0419d9e44f6","candidate_horizon_monthly.csv":"43dcb463a1a6f7a668f56ab5339eddbec8c0a04cd506f3161204a7f2edf3ec3c","candidate_horizon_direction.csv":"ca7bf7f0b59b8e915fe2e9e36d90d8779f2ccd29133b374620b2c607a34c06af","candidate_horizon_surface.csv":"a47b68bd8417f94e66712e7324a7077e96e169350b6a779e7db8d3ac873890d0","candidate_horizon_hashes.csv":"04130a947b297c7dad7e2016db6dcce10369eb374fe57cd862e1c34287f66a0f"};comparisons=[]
 for name,frame in generated.items():
  digest=hashlib.sha256(csv_bytes(frame)).hexdigest();accepted=pd.read_csv(args.accepted_dir/name);equal=list(frame.columns)==list(accepted.columns) and len(frame)==len(accepted)
  if equal:
   for column in frame.columns:
    if pd.api.types.is_numeric_dtype(frame[column]) or pd.api.types.is_numeric_dtype(accepted[column]):
     if not np.allclose(pd.to_numeric(frame[column],errors="coerce").to_numpy(float),pd.to_numeric(accepted[column],errors="coerce").to_numpy(float),rtol=0,atol=1e-9,equal_nan=True):equal=False;break
    elif not frame[column].fillna("").astype(str).equals(accepted[column].fillna("").astype(str)):equal=False;break
  comparisons.append({"file":name,"rows":len(frame),"sha256":digest,"expected_sha256":expected_sha[name],"row_numeric_exact":bool(equal),"sha_exact":digest==expected_sha[name],"passed":bool(equal and digest==expected_sha[name])})
 trade_columns=["candidate_id","horizon_bars","signal_ts","entry_ts","exit_ts","entry_month","entry_date_utc","side","entry_mid","exit_mid","entry_spread_pips","gross_pips","default_cost_pips","severe_cost_pips","default_net_pips","severe_net_pips","mfe_pips","mae_pips","bars_to_mfe","bars_to_mae"];trade_output=trades[trade_columns].copy()
 for column in ["signal_ts","entry_ts","exit_ts"]:trade_output[column]=pd.to_datetime(trade_output[column],utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
 trade_digest=hashlib.sha256(deterministic_gzip(csv_bytes(trade_output))).hexdigest();accepted_trades=pd.read_csv(args.accepted_dir/"candidate_horizon_trades.csv.gz");trade_equal=list(trade_output.columns)==list(accepted_trades.columns) and len(trade_output)==len(accepted_trades)
 if trade_equal:
  for column in trade_output.columns:
   if pd.api.types.is_numeric_dtype(trade_output[column]) or pd.api.types.is_numeric_dtype(accepted_trades[column]):
    if not np.allclose(pd.to_numeric(trade_output[column],errors="coerce").to_numpy(float),pd.to_numeric(accepted_trades[column],errors="coerce").to_numpy(float),rtol=0,atol=1e-9,equal_nan=True):trade_equal=False;break
   elif not trade_output[column].fillna("").astype(str).equals(accepted_trades[column].fillna("").astype(str)):trade_equal=False;break
 comparisons.append({"file":"candidate_horizon_trades.csv.gz","rows":len(trade_output),"sha256":trade_digest,"expected_sha256":expected_sha["candidate_horizon_trades.csv.gz"],"row_numeric_exact":bool(trade_equal),"sha_exact":trade_digest==expected_sha["candidate_horizon_trades.csv.gz"],"passed":bool(trade_equal and trade_digest==expected_sha["candidate_horizon_trades.csv.gz"])})
 shapes={"trade_rows":len(trade_output),"summary_rows":len(summary),"monthly_rows":len(monthly),"direction_rows":len(direction),"surface_rows":len(surface),"hash_rows":len(hashes)};expected_shapes={"trade_rows":383078,"summary_rows":660,"monthly_rows":3960,"direction_rows":1320,"surface_rows":60,"hash_rows":660};passed=all(row["passed"] for row in comparisons) and shapes==expected_shapes;result={"schema_version":"usdjpy_full_frozen_architecture_census_preflight_result_v1","status":"PASS" if passed else "FAIL","decision":"UNLOCK_STAGE2_FOURFOLD_CENSUS_AFTER_ATOMIC_MERGE" if passed else "STOP_DO_NOT_ACCESS_CENSUS_OUTCOMES","authority":{"release":"usdjpy-r2-horizon-surface-v1","run_id":29646040010,"artifact_id":8430064217,"artifact_sha256":"84a495b7c7cddf1c719bb4c8ce78bfef2c990b355649d362c18481836d953426"},"input_sha256":actual_inputs,"horizons":HORIZONS,"candidates":len(candidates),"shapes":shapes,"expected_shapes":expected_shapes,"file_comparisons":sorted(comparisons,key=lambda x:x["file"]),"boundaries":{"2023_outcomes_accessed":False,"2024H2_census_outcomes_accessed":False,"single_combination_selected":False,"2025_accessed":False,"MT4_accessed":False,"live_orders":False}};args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");print(json.dumps(result,indent=2,sort_keys=True))
 if not passed:raise SystemExit(1)
if __name__=="__main__":main()
