#!/usr/bin/env python3
"""Materialize preregistered post-result summaries for USDJPY HYP-023.

This script does not generate signals or trades and cannot change the frozen
protocol. It consumes the exact evaluator ledgers and emits missing descriptive
outputs required by the preregistration: month/quarter/direction, exit and
duration, realized balance drawdown, boundary sensitivity, parameter
equivalence, and explicit gate failures.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd

def pf(s: pd.Series) -> float:
    gain=float(s[s>0].sum()); loss=float(-s[s<0].sum())
    if loss==0: return float("inf") if gain>0 else 0.0
    return gain/loss

def grouped_metrics(trades: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows=[]
    for key,group in trades.groupby(keys,dropna=False,sort=True):
        if not isinstance(key,tuple): key=(key,)
        row=dict(zip(keys,key))
        row.update({
            "trades":int(len(group)),
            "default_net_pips":float(group.default_net_pips.sum()),
            "default_pf":pf(group.default_net_pips),
            "severe_net_pips":float(group.severe_net_pips.sum()),
            "severe_pf":pf(group.severe_net_pips),
            "gross_pips":float(group.gross_pips.sum()),
            "mean_duration_hours":float(group.duration_hours.mean()),
            "median_duration_hours":float(group.duration_hours.median()),
            "boundary_liquidations":int(group.boundary_liquidation.astype(bool).sum()),
        })
        rows.append(row)
    return pd.DataFrame(rows)

def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path,index=False,lineterminator="\n")

def realized_drawdown(group: pd.DataFrame) -> dict:
    group=group.sort_values(["exit_logical_utc","entry_logical_utc"]).copy()
    result={}
    for column,prefix in [("default_net_pips","default"),("severe_net_pips","severe")]:
        equity=group[column].cumsum()
        peak=pd.concat([pd.Series([0.0]),equity.reset_index(drop=True)]).cummax().iloc[1:].to_numpy()
        draw=equity.to_numpy()-peak
        idx=int(np.argmin(draw)) if len(draw) else -1
        result[f"{prefix}_net_pips"]=float(equity.iloc[-1]) if len(equity) else 0.0
        result[f"{prefix}_max_realized_drawdown_pips"]=float(-draw[idx]) if idx>=0 else 0.0
        result[f"{prefix}_minimum_realized_equity_pips"]=float(min(0.0,equity.min())) if len(equity) else 0.0
        result[f"{prefix}_drawdown_trough_exit_utc"]=group.iloc[idx].exit_logical_utc.strftime("%Y-%m-%dT%H:%M:%SZ") if idx>=0 else None
    return result

def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--trades",type=Path,required=True)
    parser.add_argument("--signals",type=Path,required=True)
    parser.add_argument("--fold-metrics",type=Path,required=True)
    parser.add_argument("--cell-summary",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args(); args.output_dir.mkdir(parents=True,exist_ok=True)
    trades=pd.read_csv(args.trades); signals=pd.read_csv(args.signals); folds=pd.read_csv(args.fold_metrics); cells=pd.read_csv(args.cell_summary)
    for column in ["entry_logical_utc","exit_logical_utc","entry_information_utc","exit_information_utc"]:
        trades[column]=pd.to_datetime(trades[column],utc=True)
    signals["information_utc"]=pd.to_datetime(signals["information_utc"],utc=True)
    outputs={
        "usdjpy_native_h4_h1_month_metrics_v1.csv":grouped_metrics(trades,["candidate_id","fold","entry_month"]),
        "usdjpy_native_h4_h1_quarter_metrics_v1.csv":grouped_metrics(trades,["candidate_id","fold","entry_quarter"]),
        "usdjpy_native_h4_h1_direction_metrics_v1.csv":grouped_metrics(trades,["candidate_id","fold","side"]),
        "usdjpy_native_h4_h1_exit_reason_metrics_v1.csv":grouped_metrics(trades,["candidate_id","fold","exit_reason"]),
        "usdjpy_native_h4_h1_exit_reason_pooled_v1.csv":grouped_metrics(trades,["exit_reason"]),
        "usdjpy_native_h4_h1_signal_counts_v1.csv":signals.groupby(["candidate_id","fold","event"],sort=True).size().reset_index(name="events"),
    }
    duration=[]
    for key,group in trades.groupby(["candidate_id","fold","exit_reason"],sort=True):
        duration.append({"candidate_id":key[0],"fold":key[1],"exit_reason":key[2],"trades":len(group),"duration_q25_hours":float(group.duration_hours.quantile(.25)),"duration_median_hours":float(group.duration_hours.median()),"duration_q75_hours":float(group.duration_hours.quantile(.75)),"duration_mean_hours":float(group.duration_hours.mean()),"duration_max_hours":float(group.duration_hours.max())})
    outputs["usdjpy_native_h4_h1_duration_metrics_v1.csv"]=pd.DataFrame(duration)
    drawdown=[]
    for candidate_id,candidate in trades.groupby("candidate_id",sort=True):
        for fold,group in candidate.groupby("fold",sort=True): drawdown.append({"candidate_id":candidate_id,"scope":fold,"trades":len(group),**realized_drawdown(group)})
        drawdown.append({"candidate_id":candidate_id,"scope":"POOLED","trades":len(candidate),**realized_drawdown(candidate)})
    outputs["usdjpy_native_h4_h1_realized_drawdown_v1.csv"]=pd.DataFrame(drawdown)
    boundary=[]
    for candidate_id,group in trades.groupby("candidate_id",sort=True):
        event=group[~group.boundary_liquidation.astype(bool)]; end=group[group.boundary_liquidation.astype(bool)]
        boundary.append({"candidate_id":candidate_id,"all_trades":len(group),"event_exited_trades":len(event),"boundary_liquidations":len(end),"all_default_net_pips":float(group.default_net_pips.sum()),"event_only_default_net_pips":float(event.default_net_pips.sum()),"boundary_default_net_pips":float(end.default_net_pips.sum()),"all_severe_net_pips":float(group.severe_net_pips.sum()),"event_only_severe_net_pips":float(event.severe_net_pips.sum()),"boundary_severe_net_pips":float(end.severe_net_pips.sum()),"event_only_default_positive":bool(event.default_net_pips.sum()>0),"event_only_severe_positive":bool(event.severe_net_pips.sum()>0)})
    outputs["usdjpy_native_h4_h1_boundary_sensitivity_v1.csv"]=pd.DataFrame(boundary)
    identities=[]
    for candidate_id in sorted(cells.candidate_id):
        s=signals[signals.candidate_id==candidate_id].sort_values(["fold","information_utc","event","side","detail"])
        t=trades[trades.candidate_id==candidate_id].sort_values(["fold","entry_logical_utc","exit_logical_utc","side"])
        sb=s[["fold","event","information_utc","side","detail"]].to_csv(index=False,lineterminator="\n").encode()
        tb=t[["fold","entry_logical_utc","exit_logical_utc","side","entry_price","exit_price","gross_pips","default_net_pips","severe_net_pips","exit_reason","boundary_liquidation"]].to_csv(index=False,lineterminator="\n").encode()
        identities.append({"candidate_id":candidate_id,"signal_identity_sha256":hashlib.sha256(sb).hexdigest(),"trade_outcome_identity_sha256":hashlib.sha256(tb).hexdigest(),"signals":len(s),"trades":len(t)})
    equivalence=pd.DataFrame(identities); equivalence["equivalence_key"]=equivalence.signal_identity_sha256+"|"+equivalence.trade_outcome_identity_sha256
    classes=[]
    for index,(_,group) in enumerate(equivalence.groupby("equivalence_key",sort=True),1):
        class_id=f"EQ{index:02d}"; candidates=sorted(group.candidate_id.tolist())
        classes.append({"equivalence_class_id":class_id,"candidate_count":len(group),"candidate_ids":candidates,"signal_identity_sha256":group.iloc[0].signal_identity_sha256,"trade_outcome_identity_sha256":group.iloc[0].trade_outcome_identity_sha256})
        equivalence.loc[equivalence.candidate_id.isin(candidates),"equivalence_class_id"]=class_id
    outputs["usdjpy_native_h4_h1_parameter_equivalence_v1.csv"]=equivalence.drop(columns=["equivalence_key"])
    gate_rows=[]
    for row in folds.itertuples():
        failed=[]
        if row.trades<10: failed.append("support_trades_at_least_10")
        if not (row.default_net_pips>0 and row.default_pf>=1): failed.append("default_net_pf")
        if not (row.severe_net_pips>0 and row.severe_pf>=1): failed.append("severe_net_pf")
        if not (row.event_default_net_pips>0 and row.event_default_pf>=1): failed.append("event_only_default_net_pf")
        if not (row.event_severe_net_pips>0 and row.event_severe_pf>=1): failed.append("event_only_severe_net_pf")
        if row.minimum_quarter_severe_net_pips<0: failed.append("three_month_subblock_severe_nonnegative")
        if row.positive_months<4: failed.append("positive_months_at_least_4")
        if row.negative_months>2: failed.append("negative_months_at_most_2")
        if row.default_ex_best_two_dates_pips<=0: failed.append("default_ex_best_two_positive")
        if row.severe_ex_best_two_dates_pips<=0: failed.append("severe_ex_best_two_positive")
        gate_rows.append({"candidate_id":row.candidate_id,"fold":row.fold,"core_pass":bool(row.core_pass),"full_pass":bool(row.full_pass),"failed_gate_count":len(failed),"failed_gates":"|".join(failed)})
    outputs["usdjpy_native_h4_h1_gate_failures_v1.csv"]=pd.DataFrame(gate_rows)
    for name,frame in outputs.items(): write_csv(frame,args.output_dir/name)
    (args.output_dir/"usdjpy_native_h4_h1_parameter_equivalence_classes_v1.json").write_text(json.dumps({"schema_version":"usdjpy_native_h4_h1_parameter_equivalence_classes_v1","definition":"exact equality of ordered signal identity and ordered trade/outcome identity across all four folds","classes":classes,"equivalent_multi_candidate_classes":sum(row["candidate_count"]>1 for row in classes)},indent=2,sort_keys=True)+"\n")

if __name__=="__main__": main()
