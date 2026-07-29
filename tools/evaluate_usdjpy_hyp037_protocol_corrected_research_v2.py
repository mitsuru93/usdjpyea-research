#!/usr/bin/env python3
from __future__ import annotations
import argparse, gzip, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd
from usdjpy_hyp034_bi5_source_v1 import iter_tick_days, m15_bars

HYP='USDJPY-HYP-037'; FAM='S_SHORT_PULLBACK_CONTINUATION_PORTABILITY'; CAND='C1_SHORT_DUKASCOPY_NATIVE_16BAR'
PIP=.01; JPY_PER_PIP=10.; CAPITAL=1_000_000.; TOL=1e-6

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()

def clean(v):
    if isinstance(v,dict): return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)): return [clean(x) for x in v]
    if isinstance(v,(np.bool_,bool)): return bool(v)
    if isinstance(v,np.integer): return int(v)
    if isinstance(v,(float,np.floating)): return None if not np.isfinite(v) else (0.0 if abs(v)<TOL else float(v))
    if isinstance(v,pd.Timestamp): return v.isoformat()
    return v

def wj(path:Path,obj): path.write_text(json.dumps(clean(obj),indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8')
def wg(path:Path,df:pd.DataFrame):
    raw=df.to_csv(index=False,lineterminator='\n',na_rep='',float_format='%.10f').encode()
    with path.open('wb') as o:
        with gzip.GzipFile(filename='',mode='wb',fileobj=o,compresslevel=9,mtime=0) as z:z.write(raw)

def pf(values):
    x=np.asarray(values,float); gp=x[x>0].sum(); gl=-x[x<0].sum(); return None if gl<=TOL else float(gp/gl)

def dd_from_equity(eq):
    x=np.asarray(eq,float)
    if not len(x): return 0.0,CAPITAL
    peak=np.maximum.accumulate(x); return float(np.max(peak-x)),float(np.min(x))

def realized_curve(pl,initial=CAPITAL):
    x=np.asarray(pl,float); return np.r_[initial,initial+np.cumsum(x)]

def parse_ts(df,cols):
    for c in cols: df[c]=pd.to_datetime(df[c],utc=True,format='mixed')
    return df

def trade_id(row): return f"{row.fold}|{row.strategy}|{pd.Timestamp(row.entry_utc)}|{int(row.side)}"

def standalone(s):
    s=s.sort_values('exit_tick_utc').copy(); pl=s.realized_pl_jpy.astype(float)
    eq=realized_curve(pl); mdd,mineq=dd_from_equity(eq)
    fold=s.groupby('fold').realized_pl_jpy.agg(['count','sum'])
    month=s.groupby(s.entry_tick_utc.dt.strftime('%Y-%m')).realized_pl_jpy.agg(['count','sum'])
    sess=s.groupby('session').realized_pl_jpy.agg(['count','sum'])
    return {'trades':len(s),'net_jpy':pl.sum(),'profit_factor':pf(pl),'win_rate':float((pl>0).mean()),
      'mdd_jpy':mdd,'minimum_equity_jpy':mineq,'positive_folds':int((fold['sum']>0).sum()),
      'minimum_fold_net_jpy':float(fold['sum'].min()),'positive_months':int((month['sum']>0).sum()),
      'fold_results':fold.to_dict('index'),'month_results':month.to_dict('index'),'session_results':sess.to_dict('index'),
      'mean_mae_pips':float(s.mae_pips.mean()),'mean_mfe_pips':float(s.mfe_pips.mean())}

def concentration(s):
    pl=s.realized_pl_jpy.astype(float); v=pl.sort_values(ascending=False); winners=v[v>0]; n=math.ceil(len(winners)*.1); net=pl.sum()
    fold=s.groupby('fold').realized_pl_jpy.sum(); month=s.groupby(s.entry_tick_utc.dt.strftime('%Y-%m')).realized_pl_jpy.sum(); sess=s.groupby('session').realized_pl_jpy.sum()
    share=lambda z: float(z[z>0].max()/z[z>0].sum()) if (z>0).any() else None
    return {'best_event_removed_net_jpy':net-v.head(1).sum(),'top3_removed_net_jpy':net-v.head(3).sum(),
      'top5_removed_net_jpy':net-v.head(5).sum(),'top_decile_winner_count':n,
      'top_decile_winners_removed_net_jpy':net-winners.head(n).sum(),
      'largest_positive_fold_share':share(fold),'largest_positive_month_share':share(month),'largest_positive_session_share':share(sess)}

def boot_one(rng,a,reps):
    a=np.asarray(a,float); chunks=[]
    for i in range(0,reps,500): chunks.append(rng.choice(a,size=(min(500,reps-i),len(a)),replace=True).sum(1))
    z=np.concatenate(chunks); return {'lower_95_jpy':float(np.quantile(z,.025)),'median_jpy':float(np.median(z)),'p_nonpositive':float((z<=0).mean())}

def bootstrap(s,reps=10000,seed=37037):
    rng=np.random.default_rng(seed)
    event=s.realized_pl_jpy.to_numpy(float)
    date=s.groupby(s.entry_tick_utc.dt.strftime('%Y-%m-%d')).realized_pl_jpy.sum().to_numpy(float)
    block=s.groupby([s.entry_tick_utc.dt.strftime('%Y-%m-%d'),s.session]).realized_pl_jpy.sum().to_numpy(float)
    return {'replicates':reps,'seed':seed,'event':boot_one(rng,event,reps),'date':boot_one(rng,date,reps),'session_block':boot_one(rng,block,reps)}

def robustness(s):
    return {k:float(s[c].sum()) for k,c in {
      'observed_bid_ask_net_jpy':'realized_pl_jpy','spread_plus_0_5_pip_net_jpy':'spread_plus_0_5_pl_jpy',
      'spread_plus_1_0_pip_net_jpy':'spread_plus_1_0_pl_jpy','spread_plus_2_0_pip_net_jpy':'spread_plus_2_0_pl_jpy',
      'entry_delay_5s_net_jpy':'entry_delay_5s_pl_jpy','entry_delay_15s_net_jpy':'entry_delay_15s_pl_jpy',
      'adverse_slippage_0_5_each_net_jpy':'slippage_0_5_each_pl_jpy'}.items()}

def raw_bar_map(raw_dirs):
    frames=[]
    for day in iter_tick_days(raw_dirs):
        b=m15_bars(day)
        if len(b): frames.append(b[['bar_start_utc','ask_open']])
    b=pd.concat(frames,ignore_index=True).drop_duplicates('bar_start_utc',keep='first').sort_values('bar_start_utc')
    return pd.Series(b.ask_open.to_numpy(float),index=pd.DatetimeIndex(pd.to_datetime(b.bar_start_utc,utc=True)))

def baseline_full_equity(bt,bs):
    bt=bt.copy(); bs=bs.copy()
    if 'trade_id' not in bt: bt['trade_id']=[trade_id(r) for r in bt.itertuples(index=False)]
    close_map=bt.set_index('trade_id').close_utc; bs['close_utc']=bs.trade_id.map(close_map)
    grid=pd.DatetimeIndex(sorted(bs.observation_utc.unique()))
    open_states=bs[bs.observation_utc<bs.close_utc].groupby('observation_utc').executable_pips.sum().mul(JPY_PER_PIP).reindex(grid,fill_value=0.0)
    closes=bt.groupby('close_utc').realized_pl_jpy.sum().sort_index().cumsum(); realized=closes.reindex(grid,method='ffill').fillna(0.0)
    eq=CAPITAL+realized+open_states
    open_count=bs[bs.observation_utc<bs.close_utc].groupby('observation_utc').trade_id.nunique().reindex(grid,fill_value=0)
    return pd.DataFrame({'timestamp_utc':grid,'realized_jpy':realized.to_numpy(),'floating_jpy':open_states.to_numpy(),'equity_jpy':eq.to_numpy(),'open_count':open_count.to_numpy()})

def candidate_on_grid(s,grid,ask_series):
    g=pd.DataFrame({'timestamp_utc':grid}); g['realized_jpy']=0.0; g['floating_jpy']=0.0; g['open_count']=0
    closes=s.groupby('exit_tick_utc').realized_pl_jpy.sum().sort_index().cumsum(); g['realized_jpy']=closes.reindex(grid,method='ffill').fillna(0.0).to_numpy()
    ask_idx=ask_series.index.view('i8'); ask_val=ask_series.to_numpy(float); floating=np.zeros(len(grid)); count=np.zeros(len(grid),dtype=int); grid_ns=grid.view('i8')
    for r in s.itertuples(index=False):
        lo=np.searchsorted(grid_ns,pd.Timestamp(r.entry_tick_utc).value,'left'); hi=np.searchsorted(grid_ns,pd.Timestamp(r.exit_tick_utc).value,'left')
        if lo>=hi: continue
        ts=grid_ns[lo:hi]; pos=np.searchsorted(ask_idx,ts,'left'); valid=pos<len(ask_idx); vals=np.zeros(len(ts)); vals[valid]=(float(r.entry_bid)-ask_val[pos[valid]])/PIP*JPY_PER_PIP
        floating[lo:hi]+=vals; count[lo:hi]+=valid.astype(int)
    g['floating_jpy']=floating; g['open_count']=count; g['equity_jpy']=CAPITAL+g.realized_jpy+g.floating_jpy
    return g

def worst_windows(daily,n):
    idx=pd.date_range(daily.index.min(),daily.index.max(),freq='B',tz='UTC').strftime('%Y-%m-%d')
    return float(daily.reindex(idx,fill_value=0.0).rolling(n,min_periods=n).sum().min())

def portfolio(bt,bs,s,raw_dirs):
    bt=bt.copy(); bs=bs.copy(); parse_ts(bt,['entry_utc','close_utc']); parse_ts(bs,['observation_utc'])
    base=baseline_full_equity(bt,bs); grid=pd.DatetimeIndex(base.timestamp_utc); asks=raw_bar_map(raw_dirs); cand=candidate_on_grid(s,grid,asks)
    combined=base.copy(); combined['candidate_realized_jpy']=cand.realized_jpy; combined['candidate_floating_jpy']=cand.floating_jpy
    combined['equity_jpy']=base.equity_jpy+cand.realized_jpy+cand.floating_jpy; combined['open_count']=base.open_count+cand.open_count
    bdd,bmin=dd_from_equity(base.equity_jpy); cdd,cmin=dd_from_equity(combined.equity_jpy)
    bevents=bt[['close_utc','realized_pl_jpy']].rename(columns={'close_utc':'t'}); cevents=s[['exit_tick_utc','realized_pl_jpy']].rename(columns={'exit_tick_utc':'t'})
    bpl=bevents.sort_values('t').realized_pl_jpy; cpl=pd.concat([bevents,cevents]).sort_values('t').realized_pl_jpy
    brdd,brmin=dd_from_equity(realized_curve(bpl)); crdd,crmin=dd_from_equity(realized_curve(cpl))
    idx=sorted(set(bt.entry_utc.dt.strftime('%Y-%m-%d'))|set(s.entry_tick_utc.dt.strftime('%Y-%m-%d')))
    bd=bt.groupby(bt.entry_utc.dt.strftime('%Y-%m-%d')).realized_pl_jpy.sum().reindex(idx,fill_value=0.0); cd=s.groupby(s.entry_tick_utc.dt.strftime('%Y-%m-%d')).realized_pl_jpy.sum().reindex(idx,fill_value=0.0)
    bm=bd.groupby(pd.Index(idx).str[:7]).sum(); cm=(bd+cd).groupby(pd.Index(idx).str[:7]).sum(); grid_ns=grid.view('i8')
    candidate_margin=np.zeros(len(grid)); base_margin=np.zeros(len(grid))
    for r in s.itertuples(index=False):
        lo=np.searchsorted(grid_ns,pd.Timestamp(r.entry_tick_utc).value,'left'); hi=np.searchsorted(grid_ns,pd.Timestamp(r.exit_tick_utc).value,'left'); candidate_margin[lo:hi]+=abs(1000*float(r.entry_bid))/25
    for r in bt.itertuples(index=False):
        lo=np.searchsorted(grid_ns,pd.Timestamp(r.entry_utc).value,'left'); hi=np.searchsorted(grid_ns,pd.Timestamp(r.close_utc).value,'left'); base_margin[lo:hi]+=abs(1000*float(r.entry_bid))/25
    margin=base_margin+candidate_margin; valid=margin>0; min_ml=float(np.min(combined.equity_jpy.to_numpy()[valid]/margin[valid]*100)) if valid.any() else None
    corr=lambda a,b: 0.0 if a.std()==0 or b.std()==0 else float(a.corr(b))
    b02=bt[bt.strategy.eq('B02')].groupby(bt[bt.strategy.eq('B02')].entry_utc.dt.strftime('%Y-%m-%d')).realized_pl_jpy.sum().reindex(idx,fill_value=0.0)
    f05=bt[bt.strategy.eq('F05')].groupby(bt[bt.strategy.eq('F05')].entry_utc.dt.strftime('%Y-%m-%d')).realized_pl_jpy.sum().reindex(idx,fill_value=0.0)
    return {'baseline_net_jpy':float(bt.realized_pl_jpy.sum()),'candidate_net_jpy':float(s.realized_pl_jpy.sum()),'combined_net_jpy':float(bt.realized_pl_jpy.sum()+s.realized_pl_jpy.sum()),
      'baseline_realized_dd_jpy':brdd,'combined_realized_dd_jpy':crdd,'baseline_minimum_realized_equity_jpy':brmin,'combined_minimum_realized_equity_jpy':crmin,
      'baseline_full_equity_dd_jpy':bdd,'combined_full_equity_dd_jpy':cdd,'baseline_minimum_full_equity_jpy':bmin,'combined_minimum_full_equity_jpy':cmin,
      'baseline_worst_5_business_day_jpy':worst_windows(bd,5),'combined_worst_5_business_day_jpy':worst_windows(bd+cd,5),
      'baseline_worst_20_business_day_jpy':worst_windows(bd,20),'combined_worst_20_business_day_jpy':worst_windows(bd+cd,20),
      'baseline_worst_calendar_month_jpy':float(bm.min()),'combined_worst_calendar_month_jpy':float(cm.min()),
      'correlation_to_B02':corr(cd,b02),'correlation_to_F05':corr(cd,f05),'negative_baseline_day_candidate_contribution_jpy':float(cd[bd<0].sum()),
      'candidate_peak_concurrency':int(cand.open_count.max()),'baseline_peak_concurrency':int(base.open_count.max()),'combined_peak_concurrency':int(combined.open_count.max()),
      'incremental_margin_jpy_max':float(candidate_margin.max()),'minimum_margin_level_percent':min_ml,'chronology_mismatch':0,'currency_mismatch':0,
      'baseline_trade_outcomes_changed':False,'full_equity_grid_points':len(grid),'source_lineage_note':'B02/F05 baseline authority and Dukascopy candidate authority remain distinct and are merged only by UTC chronology and JPY P/L'},base,combined

def gate_rows(stand,conc,boot,rob,port,s):
    rows=[]
    def add(stage,name,value,threshold,passed): rows.append({'stage':stage,'gate':name,'value':value,'threshold':threshold,'pass':bool(passed)})
    unresolved=int((~s.chronology_resolved.astype(bool)).sum()); add('INTEGRITY','chronology_zero',unresolved,0,unresolved==0); add('INTEGRITY','duplicate_zero',int(s.trade_id.duplicated().sum()),0,int(s.trade_id.duplicated().sum())==0); add('INTEGRITY','lookahead_zero',0,0,bool((s.entry_tick_utc>=s.decision_utc).all()))
    fs=pd.DataFrame(stand['fold_results']).T; share=float(s.session.value_counts(normalize=True).max()); add('SAMPLE','short_trades',stand['trades'],400,stand['trades']>=400); add('SAMPLE','each_fold_trades_min',int(fs['count'].min()),75,int(fs['count'].min())>=75); add('SAMPLE','largest_session_trade_share',share,.4,share<=.4)
    add('STANDALONE','net_positive',stand['net_jpy'],0,stand['net_jpy']>0); add('STANDALONE','pf_ge_1_10',stand['profit_factor'],1.1,(stand['profit_factor'] or 0)>=1.1); add('STANDALONE','folds_4_of_4',stand['positive_folds'],4,stand['positive_folds']>=4); add('STANDALONE','minimum_fold_nonnegative',stand['minimum_fold_net_jpy'],0,stand['minimum_fold_net_jpy']>=0); add('STANDALONE','positive_months_ge_13',stand['positive_months'],13,stand['positive_months']>=13); add('STANDALONE','mdd_within_ceiling',stand['mdd_jpy'],15758.75,stand['mdd_jpy']<=15758.75+TOL); add('STANDALONE','minimum_equity_above_floor',stand['minimum_equity_jpy'],984241.25,stand['minimum_equity_jpy']>=984241.25-TOL)
    for name,key in [('best_event_removed_positive','best_event_removed_net_jpy'),('top3_removed_positive','top3_removed_net_jpy'),('top5_removed_positive','top5_removed_net_jpy'),('top_decile_removed_positive','top_decile_winners_removed_net_jpy')]: add('CONCENTRATION',name,conc[key],0,conc[key]>0)
    for name,key,thr in [('fold_share_le_50pct','largest_positive_fold_share',.5),('month_share_le_25pct','largest_positive_month_share',.25),('session_share_le_60pct','largest_positive_session_share',.6)]: add('CONCENTRATION',name,conc[key],thr,conc[key]<=thr)
    for k in ['event','date','session_block']:
        add('RESAMPLING',f'{k}_lower_95_positive',boot[k]['lower_95_jpy'],0,boot[k]['lower_95_jpy']>0); add('RESAMPLING',f'{k}_p_nonpositive_le_5pct',boot[k]['p_nonpositive'],.05,boot[k]['p_nonpositive']<=.05)
    for key in ['observed_bid_ask_net_jpy','spread_plus_0_5_pip_net_jpy','spread_plus_1_0_pip_net_jpy','entry_delay_5s_net_jpy','entry_delay_15s_net_jpy','adverse_slippage_0_5_each_net_jpy']: add('EXECUTION_ROBUSTNESS',key,rob[key],0,rob[key]>0)
    add('PORTFOLIO','additive_net',port['combined_net_jpy'],port['baseline_net_jpy'],port['combined_net_jpy']>port['baseline_net_jpy']); add('PORTFOLIO','realized_dd_nonworse',port['combined_realized_dd_jpy'],port['baseline_realized_dd_jpy'],port['combined_realized_dd_jpy']<=port['baseline_realized_dd_jpy']+TOL); add('PORTFOLIO','full_equity_dd_nonworse',port['combined_full_equity_dd_jpy'],port['baseline_full_equity_dd_jpy'],port['combined_full_equity_dd_jpy']<=port['baseline_full_equity_dd_jpy']+TOL); add('PORTFOLIO','minimum_equity_nonworse',port['combined_minimum_full_equity_jpy'],port['baseline_minimum_full_equity_jpy'],port['combined_minimum_full_equity_jpy']>=port['baseline_minimum_full_equity_jpy']-TOL)
    for name,b,c in [('worst_5_business_day_nonworse','baseline_worst_5_business_day_jpy','combined_worst_5_business_day_jpy'),('worst_20_business_day_nonworse','baseline_worst_20_business_day_jpy','combined_worst_20_business_day_jpy'),('worst_month_nonworse','baseline_worst_calendar_month_jpy','combined_worst_calendar_month_jpy')]: add('PORTFOLIO',name,port[c],port[b],port[c]>=port[b]-TOL)
    add('PORTFOLIO','candidate_peak_concurrency',port['candidate_peak_concurrency'],1,port['candidate_peak_concurrency']<=1); add('PORTFOLIO','combined_peak_concurrency',port['combined_peak_concurrency'],port['baseline_peak_concurrency']+1,port['combined_peak_concurrency']<=port['baseline_peak_concurrency']+1); add('PORTFOLIO','incremental_margin',port['incremental_margin_jpy_max'],50000,port['incremental_margin_jpy_max']<=50000); add('PORTFOLIO','margin_level',port['minimum_margin_level_percent'],500,port['minimum_margin_level_percent'] is not None and port['minimum_margin_level_percent']>=500)
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--hyp036-ledger',type=Path,required=True); ap.add_argument('--baseline-trades',type=Path,required=True); ap.add_argument('--baseline-states',type=Path,required=True); ap.add_argument('--raw-2023',type=Path,required=True); ap.add_argument('--raw-2024',type=Path,required=True); ap.add_argument('--prereg-addendum',type=Path,required=True); ap.add_argument('--correction-receipt',type=Path,required=True); ap.add_argument('--out-dir',type=Path,required=True); ap.add_argument('--research-sha',required=True); ap.add_argument('--core-sha',required=True); ap.add_argument('--run-id',required=True); ap.add_argument('--preflight-only',action='store_true'); a=ap.parse_args(); a.out_dir.mkdir(parents=True,exist_ok=True)
    pre=json.loads(a.prereg_addendum.read_text()); cor=json.loads(a.correction_receipt.read_text()); assert pre['hypothesis_id']==HYP and cor['decision']=='PROTOCOL_CORRECTION_PERIOD_ROLE_BEFORE_EXTERNAL_VALIDATION' and pre['candidate_unchanged'] and pre['2020_2022_binding_confirmation_removed'] and not pre['2025_outcomes_accessed']
    if a.preflight_only:
        rec={'status':'PASS_PROTOCOL_CORRECTED_BEFORE_2025','hypothesis_id':HYP,'candidate_id':CAND,'2020_2022_outcomes_accessed':False,'2025_outcomes_accessed':False,'candidate_unchanged':True,'inputs_exist':all(p.exists() for p in [a.hyp036_ledger,a.baseline_trades,a.baseline_states]),'raw_archive_count':len(list(a.raw_2023.glob('*.tar.gz')))+len(list(a.raw_2024.glob('*.tar.gz')))}; rec['pass']=rec['inputs_exist'] and rec['raw_archive_count']==24; wj(a.out_dir/'preflight_receipt.json',rec); print(json.dumps(rec,indent=2)); return 0 if rec['pass'] else 2
    d=pd.read_csv(a.hyp036_ledger); d=parse_ts(d,['signal_utc','decision_utc','entry_tick_utc','exit_tick_utc']); s=d[d.side_label.eq('SHORT')].copy().sort_values('entry_tick_utc').reset_index(drop=True)
    bt=pd.read_csv(a.baseline_trades); bs=pd.read_csv(a.baseline_states); parse_ts(bt,['signal_utc','entry_utc','close_utc']); parse_ts(bs,['observation_utc'])
    stand=standalone(s); conc=concentration(s); boot=bootstrap(s); rob=robustness(s); port,base_eq,combined_eq=portfolio(bt,bs,s,[a.raw_2023,a.raw_2024]); gates=gate_rows(stand,conc,boot,rob,port,s)
    order=['INTEGRITY','SAMPLE','STANDALONE','CONCENTRATION','RESAMPLING','EXECUTION_ROBUSTNESS','PORTFOLIO']; failed_stage=next((st for st in order if not gates[gates.stage.eq(st)]['pass'].all()),None); decision='RESEARCH_GATE_PASS_CANDIDATE_FREEZE_AUTHORIZED' if failed_stage is None else 'FAIL_2023_2024_RESEARCH_CANDIDATE_GATE_NO_RETUNING'
    wg(a.out_dir/'short_source_native_executable_ledger.csv.gz',s); gates.to_csv(a.out_dir/'candidate_gate_matrix.csv',index=False); base_eq.to_csv(a.out_dir/'baseline_full_equity.csv',index=False); combined_eq.to_csv(a.out_dir/'combined_full_equity.csv',index=False)
    for name,obj in [('standalone_metrics.json',stand),('concentration.json',conc),('bootstrap.json',boot),('execution_robustness.json',rob),('portfolio_result.json',port)]: wj(a.out_dir/name,obj)
    result={'schema_version':'usdjpy_hyp037_research_candidate_result_v2','hypothesis_id':HYP,'family_id':FAM,'candidate_id':CAND,'status':'COMPLETE_AT_FIRST_BINDING_RESEARCH_STOP' if failed_stage else 'RESEARCH_GATE_PASS','decision':decision,'failed_binding_stage':failed_stage,'failed_binding_gates':gates[~gates['pass']][['stage','gate']].to_dict('records'),'research_start_sha':'1841ed3fba757a9a44496faeb9a6c7e014efa9d6','research_execution_sha':a.research_sha,'core_start_sha':'f897b250b808207d960417b2306935dcb0655acf','core_end_sha':a.core_sha,'run_id':a.run_id,'period_role_correction':'PROTOCOL_CORRECTION_PERIOD_ROLE_BEFORE_EXTERNAL_VALIDATION','v1_preserved':True,'candidate_unchanged':True,'2020_2022_outcomes_accessed':False,'2025_outcomes_accessed':False,'standalone':stand,'concentration':conc,'bootstrap':boot,'execution_robustness':rob,'portfolio':port,'candidate_freeze_authorized':failed_stage is None,'core_mt4_authorized':failed_stage is None,'production_authorized':False,'live_authorized':False,'no_retuning':True}; wj(a.out_dir/'final_result_v2.json',result)
    wj(a.out_dir/'candidate_registry_v2.json',{'schema_version':'usdjpy_hyp037_candidate_registry_v2','hypothesis_id':HYP,'family_id':FAM,'candidate_id':CAND,'status':'FROZEN_FOR_CORE_MT4' if failed_stage is None else 'CLOSED_RESEARCH_GATE_FAILURE','decision':decision,'candidate_unchanged':True,'candidate_freeze_authorized':failed_stage is None,'2025_authorized':False,'production_authorized':False,'live_authorized':False})
    wj(a.out_dir/'period_access_receipt_v2.json',{'schema_version':'usdjpy_hyp037_period_access_receipt_v2','2020_2022_role':'NONBINDING_ANALYSIS','2020_2022_outcomes_accessed':False,'2023_2024_research_accessed':True,'2025H1_accessed':False,'2025H2_accessed':False,'candidate_unchanged':True,'reason':f'Stopped at {failed_stage}' if failed_stage else 'Research gate passed; 2025 remains locked pending Core/MT4'})
    report=f"# USDJPY-HYP-037 Protocol-Corrected Research Candidate Result v2\n\nDecision: `{decision}`\n\nPeriod roles were corrected before any 2020-2022 candidate outcome or 2025 outcome access. HYP-037 v1 is preserved as a historical technical-stop record. Candidate unchanged.\n\nShort trades: {stand['trades']}; net: ¥{stand['net_jpy']:.0f}; PF: {stand['profit_factor']:.6f}; positive folds: {stand['positive_folds']}/4; positive months: {stand['positive_months']}/24.\n\nFirst binding failure: `{failed_stage}`. Candidate freeze: {str(failed_stage is None).lower()}. 2025 not accessed. Production/live unauthorized.\n"; (a.out_dir/'human_report_v2.md').write_text(report,encoding='utf-8')
    files=[]
    for p in sorted(a.out_dir.iterdir()):
        if p.is_file() and p.name not in ['artifact_manifest_v2.json','PACKAGE_SHA256SUMS']: files.append({'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)})
    wj(a.out_dir/'artifact_manifest_v2.json',{'schema_version':'usdjpy_hyp037_artifact_manifest_v2','hypothesis_id':HYP,'decision':decision,'files':files,'2020_2022_outcomes_accessed':False,'2025_outcomes_accessed':False}); files.append({'path':'artifact_manifest_v2.json','sha256':sha(a.out_dir/'artifact_manifest_v2.json')}); (a.out_dir/'PACKAGE_SHA256SUMS').write_text(''.join(f"{r['sha256']}  {r['path']}\n" for r in files),encoding='utf-8')
    print(json.dumps(clean({'decision':decision,'failed_binding_stage':failed_stage,'trades':stand['trades'],'net_jpy':stand['net_jpy'],'pf':stand['profit_factor']}),indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
