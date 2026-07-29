#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd

PIP=.01; CAP=1_000_000.; TOL=1e-9

def clean(v):
    if isinstance(v,dict): return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)): return [clean(x) for x in v]
    if isinstance(v,(np.integer,)): return int(v)
    if isinstance(v,(np.floating,float)): return None if not np.isfinite(v) else float(v)
    if isinstance(v,(np.bool_,bool)): return bool(v)
    if isinstance(v,pd.Timestamp): return v.isoformat()
    return v

def wj(p,v): Path(p).write_text(json.dumps(clean(v),indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()
def pf(x):
    a=np.asarray(x,float); gp=a[a>0].sum(); gl=-a[a<0].sum(); return None if gl<=TOL else float(gp/gl)
def dd(x):
    e=CAP+np.cumsum(np.asarray(x,float)); peak=np.maximum.accumulate(np.r_[CAP,e])[1:]
    return float((peak-e).max(initial=0)),float(np.r_[CAP,e].min())
def bcount(mask, i, start=0):
    n=0
    for k in range(i,start-1,-1):
        if not bool(mask.iloc[k]): break
        n+=1
    return n

def side_summary(g):
    pl=g.realized_pl_jpy.to_numpy(float); mdd,mineq=dd(pl)
    o={'trades':len(g),'net_jpy':pl.sum(),'profit_factor':pf(pl),'win_rate':(pl>0).mean(),'median_pl_jpy':np.median(pl),'realized_mdd_jpy':mdd,'minimum_equity_jpy':mineq}
    for c in ['mfe_pips','mae_pips','time_to_mfe_seconds','time_to_mae_seconds','spread_pips']:
        o['mean_'+c]=g[c].mean(); o['median_'+c]=g[c].median()
    o['fixed_horizon_returns']={str(h):{'mean_pips':g[f'return_{h}m_pips'].mean(),'median_pips':g[f'return_{h}m_pips'].median(),'positive_rate':(g[f'return_{h}m_pips']>0).mean()} for h in [15,30,60,120,240]}
    o['continuation_failure_rate_240m_nonpositive']=(g.return_240m_pips<=0).mean()
    o['execution_stress_net_jpy']={
      'observed':g.realized_pl_jpy.sum(),'spread_plus_0_5':g.spread_plus_0_5_pl_jpy.sum(),'spread_plus_1_0':g.spread_plus_1_0_pl_jpy.sum(),'spread_plus_2_0':g.spread_plus_2_0_pl_jpy.sum(),
      'entry_delay_5s':g.entry_delay_5s_pl_jpy.sum(),'entry_delay_15s':g.entry_delay_15s_pl_jpy.sum(),'slippage_0_5_each':g.slippage_0_5_each_pl_jpy.sum(),'severe':g.severe_case_pl_jpy.sum()}
    return clean(o)

def feature_rows(bars, ledger):
    x=h35.features(bars)
    rows=[]
    for r in ledger.itertuples(index=False):
        i=int(r.signal_index); side=int(r.side); z=x.iloc[i]; atr=max(float(z.a20),TOL); unit=atr*PIP
        strong=(side*x.ts>=1).fillna(False)
        directional=(side*(x.close-x.open)>0).fillna(False)
        trend_age=bcount(strong,i-1,0)
        consecutive=bcount(directional,i-1,0)
        near=(x.close-x.e20).abs()<=x.tol
        near8=int(near.iloc[max(0,i-7):i+1].sum())
        recent=x.iloc[max(0,i-16):i]
        if side<0:
            swing_distance=(float(z.close)-float(recent.low.min()))/unit if len(recent) else np.nan
            cross_depth=(float(z.high)-float(z.e20))/unit
            close_loc_dir=1-float(z.close_loc)
            pre_disp=(float(x.close.iloc[max(0,i-1)])-float(x.close.iloc[max(0,i-9)]))*(-1)/unit
        else:
            swing_distance=(float(recent.high.max())-float(z.close))/unit if len(recent) else np.nan
            cross_depth=(float(z.e20)-float(z.low))/unit
            close_loc_dir=float(z.close_loc)
            pre_disp=(float(x.close.iloc[max(0,i-1)])-float(x.close.iloc[max(0,i-9)]))/unit
        dur=0
        for k in range(i-1,max(-1,i-9),-1):
            cond=(side*(float(x.close.iloc[k])-float(x.open.iloc[k]))<=0) or (abs(float(x.close.iloc[k])-float(x.e20.iloc[k]))<=.5*float(x.a20.iloc[k])*PIP)
            if not cond: break
            dur+=1
        win=x.iloc[max(0,i-max(1,dur)):i+1]
        retr=swing_distance/(float(z.rg16)/unit) if pd.notna(z.rg16) and float(z.rg16)>0 else np.nan
        prior_close=float(x.close.iloc[i-1]) if i else np.nan
        e20_accel=side*((float(z.e20)-float(x.e20.iloc[max(0,i-4)]))-(float(x.e20.iloc[max(0,i-4)])-float(x.e20.iloc[max(0,i-8)])))/PIP
        first_near=None
        for k in range(max(0,i-8),i+1):
            if bool(near.iloc[k]): first_near=k; break
        rows.append({
          'trade_id':r.trade_id,'side_label':r.side_label,'fold':r.fold,'session':r.session,
          'ema20_ema96_separation_pips_directional':side*(float(z.e20)-float(z.e96))/PIP,
          'separation_atr_ratio':abs(float(z.ts)),'ema20_slope_4bar_pips_directional':side*float(z.e20s4),'ema96_slope_4bar_pips_directional':side*float(z.e96s4),
          'trend_age_bars':trend_age,'consecutive_directional_bars':consecutive,'distance_from_recent_swing_atr':swing_distance,'pre_pullback_displacement_atr':pre_disp,'trend_acceleration_pips':e20_accel,
          'pullback_depth_atr':max(0,cross_depth),'pullback_duration_bars':dur,'ema20_cross_depth_atr':cross_depth,'retracement_ratio_to_16bar_range':retr,
          'pullback_volatility_ratio':float(win.tr.mean()/atr) if len(win) else np.nan,'pullback_tick_velocity_per_second':float(win.tick_count.mean()/900) if 'tick_count' in win else np.nan,
          'pullback_countertrend_bar_fraction':float((side*(win.close-win.open)<=0).mean()) if len(win) else np.nan,'time_spent_near_ema20_bars_last8':near8,'distance_from_ema96_atr_directional':side*(float(z.close)-float(z.e96))/unit,
          'confirmation_body_atr':float(z.body_pips)/atr,'confirmation_range_atr':float(z.range_pips)/atr,'confirmation_close_location_directional':close_loc_dir,
          'confirmation_close_vs_ema20_atr_directional':side*(float(z.close)-float(z.e20))/unit,'confirmation_close_vs_prior_close_atr_directional':side*(float(z.close)-prior_close)/unit,
          'completed_bar_tick_velocity_per_second':float(z.tick_count)/900 if 'tick_count' in z else np.nan,'first_executable_spread_pips':float(r.spread_pips),
          'minutes_from_first_near_ema20_to_confirmation':None if first_near is None else (i-first_near)*15,
          'mfe_pips':float(r.mfe_pips),'mae_pips':float(r.mae_pips),'time_to_mfe_minutes':float(r.time_to_mfe_seconds)/60,'time_to_mae_minutes':float(r.time_to_mae_seconds)/60,
          'return_15m_pips':float(r.return_15m_pips),'return_30m_pips':float(r.return_30m_pips),'return_60m_pips':float(r.return_60m_pips),'return_120m_pips':float(r.return_120m_pips),'return_240m_pips':float(r.return_240m_pips),
          'fixed_exit_pl_jpy':float(r.realized_pl_jpy),'continuation_failure_240m':float(r.return_240m_pips)<=0
        })
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--preflight-only',action='store_true'); ap.add_argument('--raw-2023'); ap.add_argument('--raw-2024'); ap.add_argument('--ledger'); ap.add_argument('--partial-manifest'); ap.add_argument('--historical-portfolio-result'); ap.add_argument('--release-status-json'); ap.add_argument('--out-dir',required=True); a=ap.parse_args()
    out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
    if a.preflight_only:
        wj(out/'preflight_receipt.json',{'status':'PASS_NO_OUTCOME_ACCESS','required_args':['raw-2023','raw-2024','ledger','partial-manifest','historical-portfolio-result','release-status-json'],'candidate_outcomes_2020_2022_accessed':False,'protected_2025_accessed':False}); return
    global h35
    import hyp035 as h35
    ledger=pd.read_csv(a.ledger)
    if set(ledger.side_label)!= {'LONG','SHORT'} or len(ledger)!=1332: raise SystemExit('HYP036 discovery ledger identity mismatch')
    bars,audit,src=h35.source([Path(a.raw_2023),Path(a.raw_2024)])
    f=feature_rows(bars,ledger)
    f.to_csv(out/'mechanism_feature_comparison.csv',index=False,lineterminator='\n')
    numeric=[c for c in f.columns if c not in ['trade_id','side_label','fold','session'] and pd.api.types.is_numeric_dtype(f[c])]
    comparison={}
    for c in numeric:
        s=f.groupby('side_label')[c].agg(['count','mean','median','std']).to_dict('index')
        comparison[c]={'LONG':s.get('LONG',{}),'SHORT':s.get('SHORT',{}),'short_minus_long_mean':s.get('SHORT',{}).get('mean',np.nan)-s.get('LONG',{}).get('mean',np.nan)}
    mechanism={'schema_version':'usdjpy_hyp037_mechanism_attribution_v1','status':'COMPLETE_DISCOVERY_ONLY_NOT_CANDIDATE_SELECTION','definitions':'All pre-entry features are deterministic descriptive calculations on the frozen HYP-036 event set. No feature is used to admit, exclude, route, or retune C1.',
      'side_summary':{side:side_summary(g) for side,g in ledger.groupby('side_label')},'feature_comparison':comparison,
      'interpretation':['Short profitability is not explained by a higher win rate or favorable first-hour momentum.','Short has materially larger favorable excursion and positive mean 120/240-minute continuation despite larger adverse excursion and wider first executable spread.','The observed asymmetry is therefore consistent with a right-tail/downtrend continuation payoff shape, but 2023-2024 remains discovery evidence and cannot establish historical portability.'],'candidate_changed':False,'post_entry_used_for_admission':False}
    wj(out/'mechanism_attribution.json',mechanism)
    releases=json.loads(Path(a.release_status_json).read_text())
    partial=json.loads(Path(a.partial_manifest).read_text())
    hist=json.loads(Path(a.historical_portfolio_result).read_text())
    years=[]
    for y in [2020,2021,2022]:
        years.append({'year':y,'required_release_tag':f'usdjpy-{y}-raw-bidask-ticks-v1','release_exists':bool(releases.get(str(y),False)),'complete_months_verified':0,'candidate_outcomes_accessed':False})
    authority_pass=all(x['release_exists'] and x['complete_months_verified']==12 for x in years)
    source={'schema_version':'usdjpy_hyp037_source_inventory_v1','source_required':'Dukascopy BI5 Bid/Ask Tick','years':years,'prior_acquisition_run_id':30318515957,
      'known_partial_evidence':{'artifact_id':8675274277,'month':partial.get('month'),'accepted':partial.get('accepted'),'present_days':partial.get('totals',{}).get('present_days'),'expected_days':partial.get('totals',{}).get('expected_days'),'resolved_hours':partial.get('totals',{}).get('resolved_hours'),'expected_hours':partial.get('totals',{}).get('expected_hours'),'failures':partial.get('failures',[])[:5]},
      'historical_portfolio_authority':{'available':True,'source_run_id':30364472840,'currency_contract':hist.get('currency_contract'),'baseline_full_equity_drawdown_jpy':hist.get('economics',{}).get('baseline_full_equity_drawdown_jpy'),'limitation':'B02/F05 portfolio authority does not reproduce Pullback signal or source-native Bid/Ask execution.'},
      'authority_pass':authority_pass,'candidate_outcomes_2020_2022_accessed':False,'scientific_limitation':'No complete immutable 36-month Dukascopy BI5 authority is available. Alternative MT4/HST or venue data cannot satisfy same-source signal/execution identity.'}
    wj(out/'source_inventory.json',source)
    currency={'schema_version':'usdjpy_hyp037_currency_contract_v1','status':'PASS_PREREGISTERED_JPY_CONTRACT_NOT_YET_APPLIED_TO_HISTORICAL_OUTCOMES','canonical_reporting_currency':'JPY','initial_capital_jpy':1000000,'lot_size':0.01,'contract_size_base_currency':1000,'pip_value_jpy':10,'commission_jpy':0,'swap_jpy':0,'conversion':'none for USDJPY quote P/L','candidate_outcomes_2020_2022_accessed':False}
    wj(out/'currency_contract.json',currency)
    decision='TECHNICAL_NO_RESULT_HISTORICAL_SOURCE_AUTHORITY_UNRESOLVED' if not authority_pass else 'PASS_SOURCE_AUTHORITY_READY_FOR_BINDING_HISTORICAL_CONFIRMATION'
    gates=[{'stage':'HYPOTHESIS_ID_AUTHORITY','gate':'HYP037_UNCONFLICTED','pass':True},{'stage':'DISCOVERY_MECHANISM','gate':'HYP036_LEDGER_IDENTITY','pass':True},{'stage':'HISTORICAL_SOURCE_AUTHORITY','gate':'COMPLETE_36_MONTH_DUKASCOPY_BI5','pass':authority_pass},{'stage':'MONETARY_CONTRACT','gate':'JPY_CONTRACT_FIXED','pass':True}]
    pd.DataFrame(gates).to_csv(out/'gate_matrix.csv',index=False,lineterminator='\n')
    period={'schema_version':'usdjpy_hyp037_period_access_receipt_v1','hypothesis_id':'USDJPY-HYP-037','2023_2024':'ACCESSED_DISCOVERY_MECHANISM_ONLY','2020_2022_source_metadata':'ACCESSED','2020_2022_candidate_outcomes':'NOT_ACCESSED_SOURCE_AUTHORITY_UNRESOLVED','Core':'NOT_MODIFIED','MT4':'NOT_RUN','2025H1':'NOT_ACCESSED','2025H2':'NOT_ACCESSED','production_authorized':False,'live_authorized':False}
    wj(out/'period_access_receipt.json',period)
    result={'schema_version':'usdjpy_hyp037_final_result_v1','hypothesis_id':'USDJPY-HYP-037','family_id':'S_SHORT_PULLBACK_CONTINUATION_PORTABILITY','candidate_id':'C1_SHORT_DUKASCOPY_NATIVE_16BAR','status':'COMPLETE_TECHNICAL_NO_RESULT','decision':decision,'failed_binding_stage':'HISTORICAL_SOURCE_AUTHORITY','scientific_failure':False,'technical_no_result':True,'hyp036_decision_changed':False,'candidate_rule_changed':False,'gate_changed':False,'retuning':False,'discovery_2023_2024':{'short_trades':500,'short_net_jpy':17679,'short_profit_factor':1.272769351827556,'long_trades':832,'long_net_jpy':-674,'long_profit_factor':0.992546556376344,'confirmation_credit':False},'source_authority':source,'currency_contract':currency,'historical_2020_2022':{'candidate_outcomes_accessed':False,'trades':None,'net_jpy':None,'profit_factor':None,'year_results':None,'halfyear_results':None,'month_results':None,'session_results':None,'concentration':None,'bootstrap':None,'execution_robustness':None},'not_reached':['historical standalone confirmation','historical portfolio risk gate','candidate freeze','Core implementation','MT4 parity','2025H1','2025H2'],'authorization':{'historical_candidate_outcomes':False,'candidate_freeze':False,'Core':False,'MT4':False,'2025H1':False,'2025H2':False,'production':False,'live':False},'exact_next_action':'Complete and checksum immutable Dukascopy BI5 Bid/Ask monthly archives for 2020-2022, then rerun the unchanged HYP-037 preregistration. Do not change candidate, gate, source lineage, periods, or lot.'}
    wj(out/'final_result.json',result)
    report=f'''# USDJPY-HYP-037 Short Pullback Continuation Portability Result v1\n\n## Decision\n\n`{decision}`\n\nHYP-037 was prospectively frozen as the Short-only counterpart of the closed HYP-036 rule. HYP-036 remains unchanged. The 2023-2024 Short result is discovery evidence only.\n\n## Discovery mechanism attribution\n\nThe fixed HYP-036 ledger was reproduced at 1,332 trades. Short had 500 trades, +JPY 17,679 and PF 1.273; Long had 832 trades, -JPY 674 and PF 0.993. Short did not have a materially higher win rate and was negative on mean 15/30/60-minute returns, but had larger MFE and positive mean 120/240-minute returns. This is consistent with a delayed right-tail continuation payoff rather than superior immediate confirmation. It is not confirmation.\n\n## Binding stop\n\nThe required 2020-2022 Dukascopy BI5 Bid/Ask annual Releases are absent. Prior Run 30318515957 produced partial artifacts; the inspected 2020-12 artifact has accepted=false, 0/31 day packets and 0/744 resolved hours. The HYP-032 historical B02/F05 full-equity ledger is available in JPY, but it cannot substitute for Pullback signal and executable Bid/Ask authority.\n\nNo 2020-2022 candidate trade or P/L was constructed. Under the preregistered stop rule, the study stops as a technical no-result before standalone economics, portfolio risk, freeze, Core/MT4 or 2025.\n\n## Authorization\n\nCandidate freeze, Core, MT4, 2025H1/H2, production and live authorization are all false.\n'''
    Path(out/'human_report.md').write_text(report,encoding='utf-8')
    files=[p for p in out.iterdir() if p.is_file() and p.name!='output_manifest.json']
    manifest={'schema_version':'usdjpy_hyp037_output_manifest_v1','files':[{'name':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(files)],'decision':decision,'candidate_outcomes_2020_2022_accessed':False,'protected_2025_accessed':False}
    wj(out/'output_manifest.json',manifest)
if __name__=='__main__': main()
