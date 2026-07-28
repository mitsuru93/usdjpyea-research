#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,heapq,json,math
from pathlib import Path
import numpy as np
import pandas as pd
SEED=20260728
CANDIDATES={"C1_SHORT_SHARED_SESSION_LOSS_CAP_2":{"target":"ANY_SHORT","counter":"SHARED"},"C2_F05_SHORT_SHARED_SESSION_LOSS_CAP_2":{"target":"F05_SHORT","counter":"SHARED"},"C3_F05_SHORT_OWN_LOSS_CAP_2":{"target":"F05_SHORT","counter":"F05_SHORT"}}
TIE_ORDER={"C3_F05_SHORT_OWN_LOSS_CAP_2":0,"C2_F05_SHORT_SHARED_SESSION_LOSS_CAP_2":1,"C1_SHORT_SHARED_SESSION_LOSS_CAP_2":2}
def sha256(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def session_label(t):
 h=t.hour
 return 'Tokyo' if h<7 else 'London' if h<13 else 'London_NY_overlap' if h<16 else 'New_York' if h<20 else 'session_transition'
def session_key(t):return f"{t:%Y-%m-%d}|{session_label(t)}"
def pf(s):
 s=pd.Series(s,dtype=float);gp=float(s[s>0].sum());gl=float(-s[s<0].sum())
 return None if gp==0 and gl==0 else math.inf if gl==0 else gp/gl
def drawdown(rows):
 if len(rows)==0:return 0.0
 z=rows.sort_values(['close_utc','trade_id'],kind='mergesort').candidate_pl_jpy.cumsum()
 return float((z.cummax().clip(lower=0)-z).max())
def target_entry(r,target):
 return int(r.side)<0 if target=='ANY_SHORT' else r.strategy=='F05' and int(r.side)<0
def relevant_loss(v,counter):
 return float(v['realized_pl_jpy'])<0 and (counter=='SHARED' or v['strategy']=='F05' and int(v['side'])<0)
def replay(d,candidate_id,same_timestamp_close_first=True):
 cfg=CANDIDATES[candidate_id];entries=d.sort_values(['entry_utc','strategy','trade_id'],kind='mergesort');heap=[];seq=0;counts={};decisions=[];closes=[]
 def apply(limit,exact):
  while heap and (heap[0][0]<limit or exact and heap[0][0]==limit):
   _,_,v=heapq.heappop(heap);k=v['exit_session_key'];before=counts.get(k,0);hit=relevant_loss(v,cfg['counter'])
   if hit:counts[k]=before+1
   closes.append({'trade_id':v['trade_id'],'close_utc':v['close_utc'],'exit_session_key':k,'strategy':v['strategy'],'side':int(v['side']),'realized_pl_jpy':float(v['realized_pl_jpy']),'loss_count_before':before,'loss_count_after':counts.get(k,0),'counter_incremented':hit})
 for ts,g in entries.groupby('entry_utc',sort=True):
  apply(ts,False)
  if same_timestamp_close_first:apply(ts,True)
  for r in g.sort_values(['strategy','trade_id'],kind='mergesort').itertuples(index=False):
   k=r.entry_session_key;n=counts.get(k,0);targeted=target_entry(r,cfg['target']);allow=not targeted or n<2
   decisions.append({'candidate_id':candidate_id,'trade_id':r.trade_id,'entry_utc':ts,'strategy':r.strategy,'side':int(r.side),'session_key':k,'prior_loss_count':n,'targeted':targeted,'allow':allow,'blocking_reason':'session_loss_cap' if not allow else 'accepted'})
   if allow:
    seq+=1;v={'trade_id':r.trade_id,'close_utc':r.close_utc,'exit_session_key':r.exit_session_key,'strategy':r.strategy,'side':int(r.side),'realized_pl_jpy':float(r.realized_pl_jpy)};heapq.heappush(heap,(r.close_utc,seq,v))
  if not same_timestamp_close_first:apply(ts,True)
 while heap:apply(heap[0][0],True)
 return pd.DataFrame(decisions),pd.DataFrame(closes)
def baseline_features(d):
 entries=d.sort_values(['entry_utc','strategy','trade_id'],kind='mergesort');heap=[];seq=0;shared={};own={};rows=[]
 def apply(ts):
  while heap and heap[0][0]<=ts:
   _,_,v=heapq.heappop(heap);k=v['exit_session_key']
   if v['realized_pl_jpy']<0:
    shared[k]=shared.get(k,0)+1
    if v['strategy']=='F05' and v['side']<0:own[k]=own.get(k,0)+1
 for ts,g in entries.groupby('entry_utc',sort=True):
  apply(ts)
  for r in g.sort_values(['strategy','trade_id'],kind='mergesort').itertuples(index=False):
   rows.append({'trade_id':r.trade_id,'prior_shared_loss_count':shared.get(r.entry_session_key,0),'prior_F05_short_loss_count':own.get(r.entry_session_key,0)})
   seq+=1;heapq.heappush(heap,(r.close_utc,seq,{'exit_session_key':r.exit_session_key,'strategy':r.strategy,'side':int(r.side),'realized_pl_jpy':float(r.realized_pl_jpy)}))
 return pd.DataFrame(rows)
def legacy_replay(d,close_first):
 x=d.sort_values(['entry_utc','strategy','trade_id'],kind='mergesort');open_,losses={},{};rows=[]
 for ts,g in x.groupby('entry_utc',sort=True):
  processed=[]
  def close():
   q=[v for v in open_.values() if v['close_utc']<=ts]
   for v in sorted(q,key=lambda z:(z['close_utc'],z['trade_id'])):
    k=v['exit_session_key']
    if v['realized_pl_jpy']<0:losses[k]=losses.get(k,0)+1
    processed.append(v);del open_[v['trade_id']]
  if close_first:close()
  for r in g.sort_values(['strategy','trade_id'],kind='mergesort').itertuples(index=False):
   n=losses.get(r.entry_session_key,0);allow=n<2
   rows.append({'trade_id':r.trade_id,'entry_utc':ts,'allow':allow,'prior_loss_count':n,'exact_timestamp_close_count':sum(v['close_utc']==ts for v in processed)})
   if allow:open_[r.trade_id]={'trade_id':r.trade_id,'close_utc':r.close_utc,'exit_session_key':r.exit_session_key,'realized_pl_jpy':float(r.realized_pl_jpy)}
  if not close_first:close()
 return pd.DataFrame(rows)
def mechanism_table(d,feat,col):
 x=d.merge(feat,on='trade_id',validate='one_to_one');x=x[(x.strategy=='F05')&(x.side.astype(int)<0)].copy();x['bucket']=np.where(x[col]>=2,'2plus',x[col].astype(int).astype(str));out=[]
 for b in ['0','1','2plus']:
  g=x[x.bucket==b];pnl=g.realized_pl_jpy.astype(float);out.append({'counter':col,'bucket':b,'trades':len(g),'net_jpy':float(pnl.sum()),'mean_jpy':None if len(g)==0 else float(pnl.mean()),'profit_factor':pf(pnl),'positive_rate':None if len(g)==0 else float((pnl>0).mean())})
 return out
def bootstrap(x,n=10000):
 u=x.groupby(['fold','entry_session_key'],as_index=False).delta_jpy.sum();u=u[u.delta_jpy!=0];rng=np.random.default_rng(SEED)
 if len(u)==0:return {'replicates':n,'probability_nonpositive':1.0,'ci95_jpy':[0.0,0.0],'affected_units':0}
 strata=[g.delta_jpy.to_numpy(float) for _,g in u.groupby('fold',sort=True)];z=np.array([sum(float(rng.choice(a,len(a),replace=True).sum()) for a in strata) for _ in range(n)])
 return {'replicates':n,'seed':SEED,'affected_units':len(u),'probability_nonpositive':float((z<=0).mean()),'ci95_jpy':[float(v) for v in np.quantile(z,[.025,.975])],'median_jpy':float(np.median(z))}
def gate(name,passed,observed,requirement):return {'gate':name,'pass':bool(passed),'observed':observed,'requirement':requirement}
def candidate_metrics(d,decisions,mechanism_rows,candidate_id):
 x=d.merge(decisions[['trade_id','allow','prior_loss_count','targeted']],on='trade_id',validate='one_to_one');x['candidate_pl_jpy']=x.realized_pl_jpy.astype(float)*x.allow.astype(float);x['delta_jpy']=x.candidate_pl_jpy-x.realized_pl_jpy
 base_pf=pf(x.realized_pl_jpy);cand_pf=pf(x.candidate_pl_jpy);base_dd=drawdown(x.assign(candidate_pl_jpy=x.realized_pl_jpy.astype(float)));cand_dd=drawdown(x[x.allow]);folds=x.groupby('fold',as_index=False).delta_jpy.sum();months=x.assign(entry_month=x.entry_utc.dt.strftime('%Y-%m')).groupby('entry_month',as_index=False).delta_jpy.sum();posm=months[months.delta_jpy>0];negm=months[months.delta_jpy<0];largest=0.0 if posm.empty else float(posm.delta_jpy.max()/posm.delta_jpy.sum());bgp=float(x.loc[x.realized_pl_jpy>0,'realized_pl_jpy'].sum());cgp=float(x.loc[x.candidate_pl_jpy>0,'candidate_pl_jpy'].sum());top20=x[x.realized_pl_jpy>0].nlargest(20,'realized_pl_jpy');top20loss=float(top20.loc[~top20.allow,'realized_pl_jpy'].sum());fshort=float(x.loc[(x.strategy=='F05')&(x.side.astype(int)<0),'delta_jpy'].sum());bshort=float(x.loc[(x.strategy=='B02')&(x.side.astype(int)<0),'delta_jpy'].sum());counter='prior_shared_loss_count' if CANDIDATES[candidate_id]['counter']=='SHARED' else 'prior_F05_short_loss_count';mm={r['bucket']:r for r in mechanism_rows if r['counter']==counter};mechanism_pass=all(mm.get(k,{}).get('mean_jpy') is not None for k in ['0','1','2plus']) and mm['2plus']['mean_jpy']<0 and mm['2plus']['mean_jpy']<mm['0']['mean_jpy'] and mm['2plus']['mean_jpy']<mm['1']['mean_jpy'];boot=bootstrap(x)
 metrics={'candidate_id':candidate_id,'baseline':{'trades':len(x),'net_jpy':float(x.realized_pl_jpy.sum()),'profit_factor':base_pf,'realized_dd_jpy':base_dd},'candidate':{'accepted_trades':int(x.allow.sum()),'blocked_trades':int((~x.allow).sum()),'net_jpy':float(x.candidate_pl_jpy.sum()),'profit_factor':cand_pf,'realized_dd_jpy':cand_dd},'delta':{'net_improvement_jpy':float(x.delta_jpy.sum()),'realized_dd_reduction_jpy':base_dd-cand_dd,'F05_SHORT_delta_jpy':fshort,'B02_SHORT_delta_jpy':bshort},'fold_deltas':{str(r.fold):float(r.delta_jpy) for r in folds.itertuples(index=False)},'positive_delta_folds':int((folds.delta_jpy>0).sum()),'month_deltas':{str(r.entry_month):float(r.delta_jpy) for r in months.itertuples(index=False)},'positive_effect_months':len(posm),'negative_effect_months':len(negm),'largest_positive_month_share':largest,'winner_retention':None if bgp==0 else cgp/bgp,'top20_winner_loss_jpy':top20loss,'mechanism_counter':counter,'mechanism_pass':mechanism_pass,'bootstrap':boot}
 g=[gate('candidate_net_improvement_positive',metrics['delta']['net_improvement_jpy']>0,metrics['delta']['net_improvement_jpy'],'>0'),gate('candidate_pf_not_below_baseline',cand_pf is not None and base_pf is not None and cand_pf>=base_pf,{'baseline':base_pf,'candidate':cand_pf},'>=baseline'),gate('realized_drawdown_nonworse',cand_dd<=base_dd,{'baseline':base_dd,'candidate':cand_dd},'<=baseline'),gate('positive_delta_folds',metrics['positive_delta_folds']>=3,metrics['positive_delta_folds'],'>=3/4'),gate('winner_retention',metrics['winner_retention'] is not None and metrics['winner_retention']>=.99,metrics['winner_retention'],'>=0.99'),gate('top20_winner_loss_zero',top20loss==0,top20loss,'0'),gate('F05_SHORT_delta_positive',fshort>0,fshort,'>0'),gate('positive_months_gt_negative',len(posm)>len(negm),{'positive':len(posm),'negative':len(negm)},'positive>negative'),gate('largest_positive_month_share',largest<=.35,largest,'<=0.35'),gate('session_bootstrap_probability_nonpositive',boot['probability_nonpositive']<=.10,boot,'<=0.10'),gate('C1_B02_SHORT_nonnegative',candidate_id!='C1_SHORT_SHARED_SESSION_LOSS_CAP_2' or bshort>=0,bshort,'>=0 for C1'),gate('mechanism_requirement',mechanism_pass,{'counter':counter,'buckets':mm},'2plus mean<0 and below 0/1')]
 metrics['gate_matrix']=g;metrics['eligible']=all(v['pass'] for v in g);return metrics,x
def main():
 a=argparse.ArgumentParser();a.add_argument('--protocol',required=True);a.add_argument('--source-audit',required=True);a.add_argument('--ledger');a.add_argument('--out-dir',required=True);a.add_argument('--preflight-only',action='store_true');a.add_argument('--workflow-run-id',default='LOCAL');a.add_argument('--research-sha',default='UNKNOWN');z=a.parse_args();p=json.loads(Path(z.protocol).read_text());s=json.loads(Path(z.source_audit).read_text());out=Path(z.out_dir);out.mkdir(parents=True,exist_ok=True)
 assert p['hypothesis_id']=='USDJPY-HYP-032' and p['family_id']=='R_SHORT_REALIZED_LOSS_PERSISTENCE' and p['status']=='FROZEN_BEFORE_FIRST_HYP032_OUTCOME';assert [v['candidate_id'] for v in p['fixed_candidate_catalog']]==list(CANDIDATES) and all(v['threshold']==2 for v in p['fixed_candidate_catalog']);assert s['core_main_sha']==p['source_identity']['core_main_at_start']
 if z.preflight_only:
  dump(out/'preflight_result.json',{'status':'PASS_NO_OUTCOMES','hypothesis_id':p['hypothesis_id'],'candidate_count':3,'outcomes_computed':False,'2020_2022_accessed':False,'MT4_accessed':False,'2025H1_accessed':False,'2025H2_accessed':False});return
 lp=Path(z.ledger);assert sha256(lp)==p['source_identity']['canonical_trade_ledger_sha256'];d=pd.read_csv(lp);d['entry_utc']=pd.to_datetime(d.entry_utc,utc=True);d['close_utc']=pd.to_datetime(d.close_utc,utc=True);d['entry_session_key']=d.entry_utc.map(session_key);d['exit_session_key']=d.close_utc.map(session_key);assert len(d)==1882 and d.trade_id.nunique()==1882 and set(d.fold)=={'2023H1','2023H2','2024H1','2024H2'}
 lc=legacy_replay(d,True);le=legacy_replay(d,False);q=lc.merge(le[['trade_id','allow']],on='trade_id',suffixes=('_close_first','_entry_first'));changed=q[q.allow_close_first!=q.allow_entry_first].copy();exact=int((changed.exact_timestamp_close_count>0).sum());prior=int((changed.exact_timestamp_close_count==0).sum());attribution={'legacy_decision_mismatches':len(changed),'strictly_prior_close_recoverable':prior,'exact_same_timestamp':exact,'interpretation':'The legacy entry-before diagnostic delayed every matured close since the previous entry, not only exact-timestamp closes. HYP-027 final decision remains unchanged.'};pd.DataFrame([{'trade_id':r.trade_id,'entry_utc':r.entry_utc,'classification':'SAME_TICK_DETERMINISTIC_EA_ORDER' if r.exact_timestamp_close_count>0 else 'SEPARATE_TICK_ORDER_RECOVERABLE'} for r in changed.itertuples(index=False)]).to_csv(out/'hyp027_interaction_reattribution.csv',index=False)
 tie_rows=[];decision_mismatch_total=0
 for cid in CANDIDATES:
  cf,_=replay(d,cid,True);ef,_=replay(d,cid,False);c=cf.merge(ef[['trade_id','allow','prior_loss_count']],on='trade_id',suffixes=('_close_first','_entry_first'));m=c[c.allow_close_first!=c.allow_entry_first];decision_mismatch_total+=len(m)
  for r in m.itertuples(index=False):
   er=d[d.trade_id==r.trade_id].iloc[0];losses=d[(d.close_utc==r.entry_utc)&(d.realized_pl_jpy<0)]
   for v in losses.itertuples(index=False):
    cls='SAME_TICK_DETERMINISTIC_EA_ORDER' if v.strategy==er.strategy else 'MULTI_EA_ORDER_UNRESOLVED';tie_rows.append({'candidate_id':cid,'entry_trade_id':r.trade_id,'entry_utc':r.entry_utc,'entry_strategy':er.strategy,'close_trade_id':v.trade_id,'close_strategy':v.strategy,'close_pl_jpy':float(v.realized_pl_jpy),'classification':cls})
 ties=pd.DataFrame(tie_rows,columns=['candidate_id','entry_trade_id','entry_utc','entry_strategy','close_trade_id','close_strategy','close_pl_jpy','classification']);ties.to_csv(out/'native_chronology_interaction_audit.csv',index=False);unresolved=0 if ties.empty else int(ties.classification.isin(p['native_chronology_gate']['unresolved_classes']).sum());chronology={'decision_mismatch_count':decision_mismatch_total,'interaction_rows':len(ties),'unresolved_interaction_rows':unresolved,'classification_counts':{} if ties.empty else {str(k):int(v) for k,v in ties.classification.value_counts().items()},'source_audit_status':s['status'],'portable':unresolved==0}
 result={'schema_version':'usdjpy_short_realized_loss_persistence_development_result_v1','hypothesis_id':p['hypothesis_id'],'family_id':p['family_id'],'workflow_run_id':z.workflow_run_id,'execution_research_sha':z.research_sha,'research_start_sha':p['source_identity']['research_main_at_start'],'core_start_sha':p['source_identity']['core_main_at_start'],'HYP027_boundary_maintained':True,'HYP027_interaction_reattribution':attribution,'native_chronology':chronology,'candidate_results':[],'selected_candidate_id':None,'period_firewall':{'2020_2022_outcomes_accessed':False,'Core_candidate_accessed':False,'MT4_accessed':False,'2025H1_accessed':False,'2025H2_accessed':False},'production_authorized':False,'live_authorized':False}
 if unresolved:
  result.update(decision='FAIL_NATIVE_CHRONOLOGY_NOT_PORTABLE',stop_rule_applied=True,next_action='CLOSE_HYP032_NO_CANDIDATE_ECONOMICS_OR_DOWNSTREAM_ACCESS')
 else:
  feat=baseline_features(d);mech=mechanism_table(d,feat,'prior_shared_loss_count')+mechanism_table(d,feat,'prior_F05_short_loss_count');pd.DataFrame(mech).to_csv(out/'mechanism_attribution.csv',index=False);allx=[]
  for cid in CANDIDATES:
   dec,_=replay(d,cid,True);met,x=candidate_metrics(d,dec,mech,cid);result['candidate_results'].append(met);dec.to_csv(out/f'{cid}_decision_ledger.csv.gz',index=False,compression='gzip');allx.append(x.assign(candidate_id=cid))
  eligible=[v for v in result['candidate_results'] if v['eligible']];eligible.sort(key=lambda v:(-v['delta']['net_improvement_jpy'],v['candidate']['blocked_trades'],TIE_ORDER[v['candidate_id']]))
  if eligible:result.update(selected_candidate_id=eligible[0]['candidate_id'],decision='PASS_DEVELOPMENT_ELIGIBLE_FOR_CANDIDATE_FREEZE',stop_rule_applied=False,next_action='FREEZE_SELECTED_CANDIDATE_BEFORE_2019_2022_AUTHORITY')
  else:result.update(decision='NO_PORTABLE_DEVELOPMENT_CANDIDATE',stop_rule_applied=True,next_action='CLOSE_HYP032_NO_HISTORICAL_CORE_MT4_OR_2025')
  pd.concat(allx,ignore_index=True).to_csv(out/'candidate_trade_economics.csv.gz',index=False,compression='gzip')
 dump(out/'result.json',result);(out/'human_report.md').write_text(f"# USDJPY-HYP-032 Development Result\n\n- Decision: `{result['decision']}`\n- HYP-027 legacy 21 reattribution: strictly-prior {prior}; exact timestamp {exact}.\n- Native chronology unresolved interactions: {unresolved}.\n- Selected candidate: `{result['selected_candidate_id']}`.\n- 2020-2022, MT4 and 2025 remain unaccessed.\n",encoding='utf-8');manifest={'schema_version':'usdjpy_short_realized_loss_persistence_output_manifest_v1','files':{}}
 for f in sorted(out.iterdir()):
  if f.is_file() and f.name!='output_manifest.json':manifest['files'][f.name]={'bytes':f.stat().st_size,'sha256':sha256(f)}
 dump(out/'output_manifest.json',manifest)
if __name__=='__main__':main()
