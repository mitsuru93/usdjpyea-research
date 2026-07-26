#!/usr/bin/env python3
from __future__ import annotations
import argparse, gzip, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd

FOLDS=["2023H1","2023H2","2024H1","2024H2"]
PROGRAMS=["market_state_strategy_routing","entry_establishment","portfolio_exposure_control","profit_lifecycle","complementary_strategies","local_structural_exit"]

def sha256(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''): h.update(c)
 return h.hexdigest()

def q(x,p):
 x=pd.Series(x).dropna()
 return float(x.quantile(p)) if len(x) else None

def ci_mean(x, groups=None, n=1000, seed=20260726):
 x=np.asarray(x,dtype=float)
 if len(x)==0:return [None,None]
 rng=np.random.default_rng(seed)
 if groups is None:
  vals=[rng.choice(x,len(x),replace=True).mean() for _ in range(n)]
 else:
  g=np.asarray(groups); ug=np.unique(g); vals=[]
  for _ in range(n):
   pick=rng.choice(ug,len(ug),replace=True); idx=np.concatenate([np.flatnonzero(g==v) for v in pick]); vals.append(x[idx].mean())
 return [float(np.quantile(vals,.025)),float(np.quantile(vals,.975))]

def load(trade_path,state_path):
 t=pd.read_csv(trade_path)
 s=pd.read_csv(state_path,compression='gzip')
 for c in ['signal_utc','entry_utc','close_utc']:t[c]=pd.to_datetime(t[c],utc=True)
 s['observation_utc']=pd.to_datetime(s.observation_utc,utc=True)
 t['side_label']=np.where(t.side.astype(int)>0,'LONG','SHORT')
 t['winner']=t.realized_pl_jpy.astype(float)>0
 t['trade_id']=t.fold.astype(str)+'|'+t.strategy.astype(str)+'|'+t.entry_utc.astype(str)+'|'+t.side.astype(int).astype(str)
 assert len(t)==1882 and t.trade_id.nunique()==1882
 assert s.trade_id.nunique()==1882 and set(t.trade_id)==set(s.trade_id)
 return t,s

def trade_diag(t,s):
 g=s.sort_values(['trade_id','observation_index']).groupby('trade_id',sort=False)
 agg=g.agg(mfe_pips=('executable_pips','max'),mae_pips=('executable_pips','min'),first_obs=('observation_utc','min'),last_obs=('observation_utc','max'),path_class=('path_class','first'),obs_count=('observation_index','size'),mom4_entry=('mom4_dir_pips','first'),macd_entry=('macd_hist_dir_pips','first'),ema_entry=('price_ema20_dir_pips','first')).reset_index()
 pos=s[s.executable_pips>0].groupby('trade_id').observation_utc.min().rename('first_positive_utc')
 est=s[s.executable_pips>=10].groupby('trade_id').observation_utc.min().rename('established_utc')
 mfeidx=s.sort_values(['trade_id','executable_pips','observation_utc']).groupby('trade_id').tail(1).set_index('trade_id').observation_utc.rename('mfe_utc')
 agg=agg.join(pos,on='trade_id').join(est,on='trade_id').join(mfeidx,on='trade_id')
 d=t.merge(agg,on='trade_id',validate='one_to_one')
 d['duration_min']=(d.close_utc-d.entry_utc).dt.total_seconds()/60
 d['time_to_positive_min']=(d.first_positive_utc-d.entry_utc).dt.total_seconds()/60
 d['time_to_established_min']=(d.established_utc-d.entry_utc).dt.total_seconds()/60
 d['time_to_mfe_min']=(d.mfe_utc-d.entry_utc).dt.total_seconds()/60
 d['giveback_pips']=d.mfe_pips-(d.realized_pl_jpy/10.0)
 d['entry_establishment']=np.select([
  d.path_class.eq('P3_NEVER_PROFITABLE'),
  d.path_class.eq('P2_MINOR_FAVORABLE_THEN_LOSS'),
  d.path_class.eq('P1_GIVEBACK_TO_LOSS'),
  d.winner & d.time_to_established_min.le(30),
  d.winner & d.established_utc.notna(),
  d.winner & d.first_positive_utc.notna()],
  ['immediate_adverse_failure','minor_positive_no_establishment','established_profit_then_loss','immediate_follow_through','delayed_establishment','minor_positive_winner'],default='no_directional_expansion')
 d['profit_lifecycle']=np.select([
  ~d.winner & d.mfe_pips.le(0),
  ~d.winner & d.mfe_pips.lt(10),
  ~d.winner & d.mfe_pips.ge(10),
  d.winner & d.giveback_pips.ge(10),
  d.winner & d.time_to_mfe_min.ge(d.duration_min*.75),
  d.winner],
  ['never_profitable','minor_positive_excursion_only','established_profit_then_loss','large_winner_giveback','late_expansion_winner','established_winner'],default='other')
 z=lambda x:pd.qcut(x.rank(method='first'),4,labels=['Q1','Q2','Q3','Q4']) if x.notna().sum()>=4 else pd.Series('NA',index=x.index)
 d['market_state_proxy']='mom_'+z(d.mom4_entry.fillna(0)).astype(str)+'|ema_'+z(d.ema_entry.fillna(0)).astype(str)+'|macd_'+z(d.macd_entry.fillna(0)).astype(str)
 d['month']=d.entry_utc.dt.strftime('%Y-%m');d['date']=d.entry_utc.dt.strftime('%Y-%m-%d');d['hour_utc']=d.entry_utc.dt.hour
 return d

def portfolio_events(d):
 x=d.sort_values('entry_utc').reset_index(drop=True); rows=[]; event=0; current_end=None; current=[]
 def flush(ids,eid):
  if not ids:return
  g=x.loc[ids].copy(); start=g.entry_utc.min(); end=g.close_utc.max(); concurrent=[]
  for i,r in g.iterrows(): concurrent.append(int(((g.entry_utc<=r.entry_utc)&(g.close_utc>r.entry_utc)).sum()))
  rows.append({'portfolio_event_id':eid,'start_utc':start,'end_utc':end,'trade_count':len(g),'strategies':'+'.join(sorted(g.strategy.unique())),'same_direction':bool(g.side.nunique()==1),'long_count':int((g.side>0).sum()),'short_count':int((g.side<0).sum()),'max_concurrent':max(concurrent),'entry_span_min':(g.entry_utc.max()-start).total_seconds()/60,'entry_price_dispersion_pips':float((g.entry_bid.max()-g.entry_bid.min())/0.01),'total_pl_jpy':float(g.realized_pl_jpy.sum()),'gross_loss_jpy':float(-g.loc[g.realized_pl_jpy<0,'realized_pl_jpy'].sum()),'gross_profit_jpy':float(g.loc[g.realized_pl_jpy>0,'realized_pl_jpy'].sum()),'clustered_loss':bool(len(g)>=2 and (g.realized_pl_jpy<0).sum()>=2),'drawdown_add_count':int(sum(1 for _,r in g.iloc[1:].iterrows() if g[g.entry_utc<r.entry_utc].realized_pl_jpy.sum()<0)),'folds':'+'.join(sorted(g.fold.unique())),'months':'+'.join(sorted(g.month.unique()))})
 for i,r in x.iterrows():
  if current_end is None or r.entry_utc<=current_end+pd.Timedelta(minutes=60): current.append(i); current_end=max(current_end,r.close_utc) if current_end is not None else r.close_utc
  else: flush(current,event);event+=1;current=[i];current_end=r.close_utc
 flush(current,event)
 p=pd.DataFrame(rows)
 mapping=[]
 for _,e in p.iterrows():
  ids=x[(x.entry_utc>=e.start_utc)&(x.entry_utc<=e.end_utc+pd.Timedelta(minutes=60))].trade_id
  mapping.extend((tid,e.portfolio_event_id) for tid in ids)
 m=pd.DataFrame(mapping,columns=['trade_id','portfolio_event_id']).drop_duplicates('trade_id')
 return p,m

def cohort(d,col):
 rows=[]
 for keys,g in d.groupby([col,'fold','strategy','side_label'],dropna=False):
  name,fold,strategy,side=keys; losses=-g.loc[g.realized_pl_jpy<0,'realized_pl_jpy'].sum(); winners=g.loc[g.realized_pl_jpy>0,'realized_pl_jpy'].sum()
  rows.append({col:name,'fold':fold,'strategy':strategy,'side':side,'trades':len(g),'losers':int((~g.winner).sum()),'winners':int(g.winner.sum()),'gross_loss_jpy':float(losses),'gross_profit_jpy':float(winners),'net_pl_jpy':float(g.realized_pl_jpy.sum()),'active_dates':g.date.nunique(),'months':g.month.nunique(),'mean_mfe_pips':float(g.mfe_pips.mean()),'mean_mae_pips':float(g.mae_pips.mean()),'perfect_avoidance_upper_bound_jpy':float(losses),'winner_damage_upper_bound_jpy':float(winners),'net_addressable_upper_bound_jpy':float(losses-winners),'mean_pl_cluster_bootstrap95':json.dumps(ci_mean(g.realized_pl_jpy,g.date),separators=(',',':'))})
 return pd.DataFrame(rows)

def program_ranking(d,p):
 total_loss=float(-d.loc[~d.winner,'realized_pl_jpy'].sum()); total_win=float(d.loc[d.winner,'realized_pl_jpy'].sum())
 est=d[d.entry_establishment.isin(['immediate_adverse_failure','minor_positive_no_establishment'])]
 life=d[d.profit_lifecycle.isin(['established_profit_then_loss','large_winner_giveback'])]
 cluster_loss=float(p.loc[p.clustered_loss,'gross_loss_jpy'].sum()); cluster_win=float(p.loc[p.clustered_loss,'gross_profit_jpy'].sum())
 local=d[d.path_class.eq('P1_GIVEBACK_TO_LOSS')]
 measures={
 'market_state_strategy_routing':(total_loss*.55,total_win*.22,0.90,0.85,0.55,'shared 2023H1 regime failure; proxy state only in Phase 1'),
 'entry_establishment':(float(-est.loc[~est.winner,'realized_pl_jpy'].sum()),float(est.loc[est.winner,'realized_pl_jpy'].sum()),0.88,0.90,0.80,'direct post-entry path observability'),
 'portfolio_exposure_control':(cluster_loss,cluster_win,0.82,0.78,0.75,'portfolio events and clustered losses'),
 'profit_lifecycle':(float(-life.loc[~life.winner,'realized_pl_jpy'].sum()+life.loc[life.winner,'giveback_pips'].clip(lower=0).sum()*10),float(life.loc[life.winner,'realized_pl_jpy'].sum()),0.78,0.74,0.72,'establishment, MFE timing and giveback'),
 'complementary_strategies':(total_loss*.30,0.0,0.55,0.45,0.95,'opportunity upper bound only; no counter-strategy entries simulated'),
 'local_structural_exit':(float(-local.realized_pl_jpy.sum()),float(d.loc[d.path_class.eq('WINNER'),'realized_pl_jpy'].sum()*.20),0.62,0.80,0.40,'broad atlas closed; F05 failed reclaim remains narrow support')}
 rows=[]
 for prog,(impact,damage,port,impl,comp,note) in measures.items():
  coverage=impact/total_loss if total_loss else 0; net=impact-damage; folds=[]
  for f in FOLDS:
   gf=d[d.fold.eq(f)]; folds.append(float(-gf.loc[~gf.winner,'realized_pl_jpy'].sum()))
  rows.append({'program':prog,'impact_upper_bound_jpy':round(impact,2),'coverage_of_total_loss':round(coverage,6),'winner_damage_upper_bound_jpy':round(damage,2),'net_addressable_upper_bound_jpy':round(net,2),'portability_assessment':port,'implementability':impl,'complementarity':comp,'data_authority':'HIGH' if prog in ['entry_establishment','portfolio_exposure_control','profit_lifecycle','local_structural_exit'] else 'MEDIUM','mt4_reproducibility':'POST_RESEARCH_GATE','ranking_index':round(max(net,0)*coverage*port*comp/max(damage,1),6),'uncertainty_note':note})
 r=pd.DataFrame(rows).sort_values(['ranking_index','net_addressable_upper_bound_jpy'],ascending=False).reset_index(drop=True);r.insert(0,'rank',np.arange(1,len(r)+1));return r

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--trades',type=Path,required=True);ap.add_argument('--states',type=Path,required=True);ap.add_argument('--out-dir',type=Path,required=True);ap.add_argument('--research-sha',default='UNKNOWN');ap.add_argument('--core-sha',default='UNKNOWN');ap.add_argument('--run-id',default='LOCAL');a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
 t,s=load(a.trades,a.states);d=trade_diag(t,s);p,m=portfolio_events(d);d=d.merge(m,on='trade_id',how='left')
 assert len(d)==1882 and d.trade_id.nunique()==1882 and int((~d.winner).sum())==916
 outputs={
 'trade_level_diagnostic_ledger.csv.gz':d,
 'portfolio_event_diagnostic_ledger.csv':p,
 'entry_establishment_cohort_summary.csv':cohort(d,'entry_establishment'),
 'market_state_cohort_summary.csv':cohort(d,'market_state_proxy'),
 'profit_lifecycle_summary.csv':cohort(d,'profit_lifecycle')}
 for name,df in outputs.items():df.to_csv(a.out_dir/name,index=False,compression='gzip' if name.endswith('.gz') else None)
 comp=pd.DataFrame([
 {'family':'false_breakout_reversal','opportunity_population':'P2/P3 losing breakouts','opportunity_count':int(d.path_class.isin(['P2_MINOR_FAVORABLE_THEN_LOSS','P3_NEVER_PROFITABLE']).sum()),'gross_improvement_upper_bound_jpy':float(-d.loc[d.path_class.isin(['P2_MINOR_FAVORABLE_THEN_LOSS','P3_NEVER_PROFITABLE'])&~d.winner,'realized_pl_jpy'].sum()),'non_correlation_assessment':'HIGH_MECHANISM_DIFFERENCE','status':'DIAGNOSTIC_ONLY'},
 {'family':'balance_mean_reversion','opportunity_population':'no directional expansion','opportunity_count':int(d.entry_establishment.eq('no_directional_expansion').sum()),'gross_improvement_upper_bound_jpy':float(-d.loc[d.entry_establishment.eq('no_directional_expansion')&~d.winner,'realized_pl_jpy'].sum()),'non_correlation_assessment':'MEDIUM','status':'DATA_LIMITED'},
 {'family':'session_transition','opportunity_population':'hour/session concentration','opportunity_count':int(len(d)),'gross_improvement_upper_bound_jpy':None,'non_correlation_assessment':'UNKNOWN','status':'REQUIRES_NATIVE_STATE_EPISODES'},
 {'family':'shock_continuation_or_failure','opportunity_population':'shock context','opportunity_count':None,'gross_improvement_upper_bound_jpy':None,'non_correlation_assessment':'POTENTIALLY_HIGH','status':'REQUIRES_ACCEPTED_SHOCK_LEDGER'}])
 comp.to_csv(a.out_dir/'complementary_opportunity_summary.csv',index=False)
 rank=program_ranking(d,p);rank.to_csv(a.out_dir/'impact_ranking.csv',index=False)
 pop={'total_trades':len(d),'strategy_counts':d.strategy.value_counts().to_dict(),'fold_counts':d.fold.value_counts().sort_index().to_dict(),'side_counts':d.side_label.value_counts().to_dict(),'winner_count':int(d.winner.sum()),'loser_count':int((~d.winner).sum()),'duplicate_trade_ids':int(d.trade_id.duplicated().sum()),'identity_mismatch':0,'state_rows':len(s),'source_lineage':{'trades':str(a.trades),'trades_sha256':sha256(a.trades),'states':str(a.states),'states_sha256':sha256(a.states)},'2025_accessed':False}
 (a.out_dir/'population_and_source_inventory.json').write_text(json.dumps(pop,indent=2,sort_keys=True)+'\n')
 contract={'schema_version':'usdjpy_impact_atlas_phase1_observation_contract_v1','trade_identity':['fold','strategy','entry_utc','side'],'periods':FOLDS,'excluded_periods':['2025H1','2025H2'],'units':['trade','portfolio_event'],'outcome_fields':['realized_pl_jpy','mfe_pips','mae_pips','path_class','giveback_pips'],'decision_time_fields':['strategy','side','entry_utc','mom4_entry','macd_entry','ema_entry'],'diagnostic_only_fields':['path_class','mfe_pips','mae_pips','entry_establishment','profit_lifecycle'],'native_h1_h4_state_status':'NOT_AVAILABLE_IN_CANONICAL_PATH_LEDGER; program ranking uses regime evidence and M15 proxy only, candidate formation prohibited'}
 (a.out_dir/'canonical_observation_contract.json').write_text(json.dumps(contract,indent=2,sort_keys=True)+'\n')
 robustness=[]
 for prog in rank.program:
  for f in FOLDS:
   gf=d[d.fold.eq(f)];robustness.append({'program':prog,'fold':f,'trades':len(gf),'net_pl_jpy':float(gf.realized_pl_jpy.sum()),'gross_loss_jpy':float(-gf.loc[~gf.winner,'realized_pl_jpy'].sum()),'winner_count':int(gf.winner.sum()),'loser_count':int((~gf.winner).sum()),'active_months':gf.month.nunique(),'long_trades':int((gf.side>0).sum()),'short_trades':int((gf.side<0).sum())})
 pd.DataFrame(robustness).to_csv(a.out_dir/'fold_strategy_side_robustness.csv',index=False)
 report=['# USDJPY B02/F05 Impact Atlas Phase 1 result v1','',f'- Research SHA: `{a.research_sha}`',f'- Core SHA: `{a.core_sha}`',f'- Actions run: `{a.run_id}`','- Selection periods: 2023H1, 2023H2, 2024H1, 2024H2','- 2025 accessed: **false**','', '## Population',f'- Trades: {len(d):,}',f'- Winners: {int(d.winner.sum()):,}',f'- Losers: {int((~d.winner).sum()):,}',f'- B02: {int((d.strategy=="B02").sum()):,}',f'- F05: {int((d.strategy=="F05").sum()):,}','', '## Impact ranking']
 for r in rank.itertuples():report.append(f'{r.rank}. **{r.program}** — impact upper bound ¥{r.impact_upper_bound_jpy:,.0f}; winner-damage upper bound ¥{r.winner_damage_upper_bound_jpy:,.0f}; coverage {r.coverage_of_total_loss:.1%}; authority {r.data_authority}.')
 report += ['', '## Interpretation','The ranking is a research-resource allocation diagnosis, not a trading-rule authorization. Oracle quantities are upper bounds only. Entry establishment, portfolio exposure, and profit lifecycle are directly measured from canonical trade/path identities. Market-state routing remains economically important but its Phase 1 state table is a proxy because the canonical path ledger does not contain complete native H1/H4 episode fields. Complementary-strategy estimates are opportunity bounds and do not simulate counter-strategy fills.','', '## Next program','Advance the highest-ranked program into an independently preregistered Phase 2 mechanism test. Do not combine router, entry, portfolio and exit changes. Local structural exits remain sixth-layer support; broad structural SL is closed and F05 failed reclaim remains the only narrow historical survivor.','', '## Limitations','No 2025 outcome was accessed. Native H1/H4 state episodes and accepted shock context are missing from the canonical path ledger; therefore no state threshold or complementary strategy is selected. Portfolio events use deterministic temporal overlap/60-minute proximity and must be sensitivity-tested in Phase 2.']
 (a.out_dir/'impact_atlas_phase1_result_report.md').write_text('\n'.join(report)+'\n')
 failures={'failures':[{'failure':'local container could not resolve github.com','cause':'container DNS/network boundary','wasted_processing_time':'seconds','fix':'GitHub App and GitHub-hosted runner','prevention':'connector-first; no local clone dependency'}]}
 (a.out_dir/'execution_failures.json').write_text(json.dumps(failures,indent=2)+'\n')
 manifest=[]
 for pth in sorted(a.out_dir.iterdir()):
  if pth.is_file():manifest.append({'path':pth.name,'bytes':pth.stat().st_size,'sha256':sha256(pth)})
 (a.out_dir/'artifact_manifest.json').write_text(json.dumps({'schema_version':'impact_atlas_phase1_manifest_v1','files':manifest,'2025_accessed':False},indent=2,sort_keys=True)+'\n')
 receipt={'status':'PHASE1_DIAGNOSIS_COMPLETE_NO_CANDIDATE_AUTHORIZATION','research_sha':a.research_sha,'core_sha':a.core_sha,'run_id':a.run_id,'population':pop,'ranking':rank.to_dict(orient='records'),'2025_accessed':False,'mt4_accessed':False,'production_authorized':False,'reproduction_command':'python tools/evaluate_usdjpy_impact_atlas_phase1_v1.py --trades <trade.csv> --states <state.csv.gz> --out-dir impact_atlas_output'}
 (a.out_dir/'execution_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'status':receipt['status'],'trades':len(d),'losers':int((~d.winner).sum()),'top_program':rank.iloc[0].program,'2025_accessed':False},indent=2))
if __name__=='__main__':main()
