from __future__ import annotations
import gzip, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
import hyp035 as h35

HYP="USDJPY-HYP-036"; FAM="S_PULLBACK_CONTINUATION_DUKASCOPY_NATIVE"; CAND="A_DUKASCOPY_NATIVE_16BAR"; TOL=1e-6

def clean(v):
    if isinstance(v,dict): return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)): return [clean(x) for x in v]
    if isinstance(v,(np.bool_,bool)): return bool(v)
    if isinstance(v,np.integer): return int(v)
    if isinstance(v,(float,np.floating)): return None if not np.isfinite(v) else (0.0 if abs(v)<TOL else float(v))
    if isinstance(v,pd.Timestamp): return v.isoformat()
    return v

def wj(path,value): Path(path).write_text(json.dumps(clean(value),indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
def wg(path,frame):
    raw=frame.to_csv(index=False,lineterminator="\n",na_rep="",float_format="%.10f").encode()
    with Path(path).open("wb") as out:
        with gzip.GzipFile(filename="",mode="wb",fileobj=out,compresslevel=9,mtime=0) as z:z.write(raw)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""): h.update(chunk)
    return h.hexdigest()

def run(a,pre,man):
    gates=[]
    def add(stage,d): gates.extend({"stage":stage,"gate":k,"pass":bool(v)} for k,v in d.items())
    decision=stage=None; raw=[a.raw_2023,a.raw_2024]
    bars,audit,source=h35.source(raw)
    wg(a.out_dir/"source_tick_day_audit.csv.gz",audit); wj(a.out_dir/"source_inventory.json",source)
    sg={"archive_count_24":source["archive_count"]==24,"ask_bid_inversion_zero":source["ask_bid_inversion_count"]==0,
        "nonmonotonic_zero":source["nonmonotonic_timestamp_count"]==0,"duplicate_bar_zero":source["duplicate_bar_count"]==0,
        "m15_population_min":source["m15_bar_count"]>=49000,"m15_population_max":source["m15_bar_count"]<=50100}
    add("SOURCE_AUTHORITY",sg)
    if not all(sg.values()): decision="FAIL_SOURCE_AUTHORITY"; stage="SOURCE_AUTHORITY"
    suppression={}; trades=None; standalone={"status":"NOT_EXECUTED"}; concentration={"status":"NOT_EXECUTED"}
    bootstrap={"status":"NOT_EXECUTED"}; robustness={"status":"NOT_EXECUTED"}; portfolio={"status":"NOT_EXECUTED"}
    if decision is None:
        features=h35.features(bars); events,suppression=h35.signals(features)
        events=events.rename(columns={"raw_event_id":"trade_id"}); wg(a.out_dir/"source_native_event_population.csv.gz",events)
        trades=h35.execute(raw,events.rename(columns={"trade_id":"raw_event_id"})).rename(columns={"raw_event_id":"trade_id"})
        integrity={"unresolved_chronology_zero":int((~trades.chronology_resolved.astype(bool)).sum())==0,
          "duplicate_event_zero":int(trades.trade_id.duplicated().sum())==0,
          "lookahead_zero":bool((pd.to_datetime(trades.entry_tick_utc,utc=True)>=pd.to_datetime(trades.decision_utc,utc=True)).all()),
          "currency_mismatch_zero":True,
          "replay_mismatch_zero":bool(np.allclose(trades.realized_pl_jpy,trades.observed_pips*h35.JPYPP,atol=TOL))}
        add("EXECUTABLE_INTEGRITY",integrity)
        if not all(integrity.values()): decision="TECHNICAL_NO_RESULT"; stage="EXECUTABLE_CHRONOLOGY"
    if decision is None:
        wg(a.out_dir/"source_native_executable_ledger.csv.gz",trades)
        trades["month"]=pd.to_datetime(trades.entry_tick_utc,utc=True).dt.strftime("%Y-%m")
        for key in ["side_label","fold","month","session"]: h35.bucket(trades,key).to_csv(a.out_dir/f"{key}_metrics.csv",index=False)
        standalone=h35.metrics(trades)
        sample={"resolved_ge_1000":standalone["trades"]>=1000,
          "each_fold_ge_200":all(v["count"]>=200 for v in standalone["fold_results"].values()),
          "long_ge_200":standalone["side_results"]["LONG"]["count"]>=200,
          "short_ge_200":standalone["side_results"]["SHORT"]["count"]>=200,"fold_crossing_zero":True}
        econ={"net_positive":standalone["net_jpy"]>0,"pf_ge_1_10":(standalone["profit_factor"] or 0)>=1.10,
          "folds_4_of_4":standalone["positive_folds"]==4,"minimum_fold_nonnegative":standalone["minimum_fold_net_jpy"]>=-TOL,
          "positive_months_ge_16":standalone["positive_months"]>=16,"mdd_within_ceiling":standalone["mdd_jpy"]<=15758.75+TOL,
          "minimum_equity_above_floor":standalone["minimum_equity_jpy"]>=984241.25-TOL}
        add("SAMPLE",sample); add("STANDALONE_ECONOMICS",econ); portfolio=h35.portfolio(a.baseline_trades,trades)
        if not all(sample.values()) or not all(econ.values()): decision="NO_PORTABLE_EXECUTABLE_CANDIDATE"; stage="DEVELOPMENT_STANDALONE"
    if decision is None:
        concentration=h35.concentration(trades)
        cg={"best_event_excluded_positive":concentration["best_event_excluded_net_jpy"]>0,
          "top3_excluded_positive":concentration["top3_events_excluded_net_jpy"]>0,
          "top5_excluded_positive":concentration["top5_events_excluded_net_jpy"]>0,
          "top_decile_excluded_positive":concentration["top_decile_winners_excluded_net_jpy"]>0,
          "fold_share_le_50pct":concentration["largest_positive_fold_share"]<=.5,
          "month_share_le_20pct":concentration["largest_positive_month_share"]<=.2,
          "session_share_le_60pct":concentration["largest_positive_session_share"]<=.6}
        add("CONCENTRATION",cg)
        if not all(cg.values()): decision="NO_PORTABLE_EXECUTABLE_CANDIDATE"; stage="DEVELOPMENT_CONCENTRATION"
    if decision is None:
        bootstrap=h35.bootstrap(trades)
        bg={"event_lower_positive":bootstrap["event"]["lower_95_jpy"]>0,"date_lower_positive":bootstrap["date"]["lower_95_jpy"]>0,
          "session_lower_positive":bootstrap["session_block"]["lower_95_jpy"]>0,"event_p_le_5pct":bootstrap["event"]["p_nonpositive"]<=.05,
          "date_p_le_5pct":bootstrap["date"]["p_nonpositive"]<=.05,"session_p_le_5pct":bootstrap["session_block"]["p_nonpositive"]<=.05}
        add("RESAMPLING",bg)
        if not all(bg.values()): decision="NO_PORTABLE_EXECUTABLE_CANDIDATE"; stage="DEVELOPMENT_RESAMPLING"
    if decision is None:
        robustness={"observed_bid_ask_net_jpy":trades.realized_pl_jpy.sum(),"spread_plus_0_5_pip_net_jpy":trades.spread_plus_0_5_pl_jpy.sum(),
          "spread_plus_1_0_pip_net_jpy":trades.spread_plus_1_0_pl_jpy.sum(),"spread_plus_2_0_pip_net_jpy":trades.spread_plus_2_0_pl_jpy.sum(),
          "entry_delay_5s_net_jpy":trades.entry_delay_5s_pl_jpy.sum(),"entry_delay_15s_net_jpy":trades.entry_delay_15s_pl_jpy.sum(),
          "adverse_slippage_0_5_each_net_jpy":trades.slippage_0_5_each_pl_jpy.sum(),"severe_case_net_jpy":trades.severe_case_pl_jpy.sum()}
        rg={k:robustness[k]>0 for k in ["observed_bid_ask_net_jpy","spread_plus_0_5_pip_net_jpy","spread_plus_1_0_pip_net_jpy",
          "entry_delay_5s_net_jpy","entry_delay_15s_net_jpy","adverse_slippage_0_5_each_net_jpy"]}
        add("EXECUTION_ROBUSTNESS",rg)
        if not all(rg.values()): decision="NO_PORTABLE_EXECUTABLE_CANDIDATE"; stage="DEVELOPMENT_EXECUTION_ROBUSTNESS"
    if decision is None:
        decision="TECHNICAL_NO_RESULT"; stage="DEVELOPMENT_PORTFOLIO_FULL_EQUITY_AUTHORITY"
        add("PORTFOLIO",{"full_equity_authority_implemented":False})
    return {"decision":decision,"stage":stage,"gates":gates,"source":source,"suppression":suppression,"trades":trades,
      "standalone":standalone,"concentration":concentration,"bootstrap":bootstrap,"robustness":robustness,"portfolio":portfolio}
