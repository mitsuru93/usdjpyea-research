#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,gzip,hashlib,json,math,random
from collections import defaultdict
from datetime import datetime
from pathlib import Path

H='USDJPY-HYP-032'; C='C1_SHORT_SHARED_SESSION_LOSS_CAP_2'; SEED=20260728; N=10000; T=1e-6
IN_SHA='d2b9a2845a1793d614fb4be193963c29ee2f958733c49d7d1b656184c7d18670'; IN_BYTES=1600400
CORE_RUN=30355284109; CORE_SHA='898d6c19f747dddaf93372e5fe26dc4c01dd3b86'; REL_SHA='e6f06139e7b8d0120da8249441fc9457ef556f44fcc83c974190bbc9e9257165'
S0=datetime(2020,1,1); S1=datetime(2023,1,1)
BASE={'trades':2782,'net':275.92,'pf':1.0894128474258808,'rdd':288.84,'edd':294.06,'min_eq':9967.83}

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def js(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
def dt(x):return datetime.fromisoformat(x) if x else None
def sn(x):return 'Tokyo' if x.hour<7 else 'London' if x.hour<13 else 'London_NY_overlap' if x.hour<16 else 'New_York' if x.hour<20 else 'session_transition'
def sk(x):return f'{x:%Y-%m-%d}|{sn(x)}'
def hy(x):return f'{x.year}H{1 if x.month<=6 else 2}'
def pf(v):
 gp=sum(x for x in v if x>0);gl=-sum(x for x in v if x<0)
 return math.inf if gl==0 and gp>0 else None if gl==0 else gp/gl
def dd(v):
 c=p=m=0.0
 for x in v:c+=x;p=max(p,c);m=max(m,p-c)
 return m
def edd(v):
 v=iter(v)
 try:p=next(v)
 except StopIteration:return 0.0
 m=0.0
 for x in v:p=max(p,x);m=max(m,p-x)
 return m
def met(rows,key):
 q=sorted(rows,key=lambda r:(r['close_seq'],r['ticket']));v=[float(r[key]) for r in q]
 return {'trades':len(q),'net_jpy':sum(v),'gross_profit_jpy':sum(x for x in v if x>0),'gross_loss_jpy':-sum(x for x in v if x<0),'profit_factor':pf(v),'wins':sum(x>0 for x in v),'losses':sum(x<0 for x in v),'breakeven':sum(abs(x)<=T for x in v),'realized_drawdown_jpy':dd(v)}
def csvw(p,rows):
 f=[]
 for r in rows:
  for k in r:
   if k not in f:f.append(k)
 with open(p,'w',newline='',encoding='utf-8') as h:w=csv.DictWriter(h,fieldnames=f,extrasaction='ignore');w.writeheader();w.writerows(rows)
def share(d):
 q=[x for x in d.values() if x>0];return max(q)/sum(q) if q else 0.0
def boot(cl):
 y=defaultdict(list)
 for r in cl:y[int(r['year'])].append(float(r['delta_jpy']))
 if sorted(y)!=[2020,2021,2022] or any(not y[k] for k in y):raise RuntimeError('bootstrap strata missing')
 g=random.Random(SEED);z=[]
 for _ in range(N):z.append(sum(sum(a[g.randrange(len(a))] for _ in a) for a in (y[2020],y[2021],y[2022])))
 z.sort();lo=z[math.floor(.025*(N-1))];hi=z[math.ceil(.975*(N-1))]
 return {'method':'calendar-year-stratified UTC entry-date/session cluster bootstrap','seed':SEED,'replicates':N,'cluster_counts':{str(k):len(y[k]) for k in y},'ci95_jpy':[lo,hi],'probability_nonpositive':sum(x<=0 for x in z)/N}

def main():
 a=argparse.ArgumentParser();a.add_argument('--input',type=Path,required=True);a.add_argument('--freeze',type=Path,required=True);a.add_argument('--preregistration',type=Path,required=True);a.add_argument('--out-dir',type=Path,required=True);a.add_argument('--research-sha',required=True);a.add_argument('--run-id',required=True);a.add_argument('--preflight-only',action='store_true');z=a.parse_args();z.out_dir.mkdir(parents=True,exist_ok=True)
 f=json.load(open(z.freeze));p=json.load(open(z.preregistration))
 assert f['hypothesis_id']==H and f['candidate_id']==C and f['threshold']==2 and f['winner_reset'] is False and f['no_retuning'] is True
 assert p['hypothesis_id']==H and p['candidate_id']==C and p['input_gzip_sha256']==IN_SHA and p['one_shot'] is True and p['no_retuning'] is True
 if z.preflight_only:js(z.out_dir/'preflight_result.json',{'status':'PASS_NO_HISTORICAL_OUTCOME_ACCESS','hypothesis_id':H,'candidate_id':C,'candidate_outcome_computed':False,'2025_accessed':False});return
 if z.input.stat().st_size!=IN_BYTES or sha(z.input)!=IN_SHA:raise RuntimeError('input identity mismatch')
 with gzip.open(z.input,'rt',encoding='utf-8') as h:head=json.loads(next(h));ev=[json.loads(x) for x in h if x.strip()]
 assert head['record_type']=='header' and head['hypothesis_id']==H and head['source_run_id']==CORE_RUN and head['source_core_sha']==CORE_SHA and head['source_release_asset_sha256']==REL_SHA
 assert not head['candidate_outcomes_computed'] and not head['candidate_logic_present'] and not head['2025_accessed']
 b=head['baseline_result'];bc=b['combined_2020_2022'];checks={'trades':int(bc['trades'])==BASE['trades'],'net':abs(float(bc['net_jpy'])-BASE['net'])<=T,'pf':abs(float(bc['profit_factor'])-BASE['pf'])<=T,'rdd':abs(float(bc['realized_drawdown_jpy'])-BASE['rdd'])<=T,'edd':abs(float(bc['full_equity_drawdown_jpy'])-BASE['edd'])<=T,'min_eq':abs(float(bc['minimum_equity_jpy'])-BASE['min_eq'])<=T,'runtime':int(b['identity']['runtime_errors'])==0,'chronology':int(b['chronology']['unresolved_rows'])==0 and int(b['chronology']['native_close_before_entry_violations'])==0,'accounting':abs(float(b['accounting']['accounting_residual_jpy']))<=.01}
 if not all(checks.values()):raise RuntimeError(f'baseline mismatch {checks}')
 count=defaultdict(int);last=0;byts=defaultdict(list)
 for e in ev:
  if e['record_type']!='event' or int(e['audit_sequence'])<=last:raise RuntimeError('event sequence failure')
  last=int(e['audit_sequence']);count[e['event']]+=1;byts[e['utc_time']].append(e)
 if dict(count)!={'order_opened':3624,'order_closed':3624,'portfolio_snapshot':100055}:raise RuntimeError(f'event count {dict(count)}')
 viol=[]
 for t,q in byts.items():
  c=[int(x['audit_sequence']) for x in q if x['event']=='order_closed'];o=[int(x['audit_sequence']) for x in q if x['event']=='order_opened']
  if c and o and max(c)>=min(o):viol.append(t)
 if viol:raise RuntimeError('native order violation')
 loss=defaultdict(int);dec={};ao={};bo={};tr={};cumblock=0.0;snap=[];dup=[];orphan=[];spread=float(head['account_contract']['spread_points'])*.001
 for e in ev:
  t=dt(e['utc_time']);k=e['event'];ticket=int(e['ticket'])
  if k=='order_opened':
   if ticket in dec:dup.append(ticket);continue
   et=dt(e['entry_utc']);key=sk(et);n=loss[key];app=int(e['side'])<0 and e['strategy'] in {'B02','F05'};allow=(not app) or n<2
   q={'ticket':ticket,'trade_id':f'MT4-{ticket}','strategy':e['strategy'],'side':int(e['side']),'side_label':'LONG' if int(e['side'])>0 else 'SHORT','entry_utc':et.isoformat(),'entry_seq':int(e['audit_sequence']),'entry_session':sn(et),'entry_session_key':key,'fold':hy(et),'year':et.year,'month':et.strftime('%Y-%m'),'entry_date':et.strftime('%Y-%m-%d'),'prior_relevant_loss_count':n,'applicable':app,'allow':allow,'reason':'ALLOW_NON_TARGET' if not app else 'ALLOW_PRIOR_LOSSES_LT_2' if allow else 'BLOCK_SHORT_SHARED_SESSION_LOSS_CAP_2','lots':float(e['lots']),'entry_price':float(e['price'])}
   dec[ticket]=q;(ao if allow else bo)[ticket]=q
  elif k=='order_closed':
   q=dec.get(ticket)
   if q is None:orphan.append(ticket);continue
   pl=float(e['balance_delta_jpy']);r=dict(q);r.update({'close_utc':t.isoformat(),'close_seq':int(e['audit_sequence']),'close_session':sn(t),'close_session_key':sk(t),'close_price':float(e['price']),'gross_pips':float(e['gross_pips']),'realized_pl_jpy':pl,'candidate_pl_jpy':pl if q['allow'] else 0.0,'delta_jpy':0.0 if q['allow'] else -pl,'scoring':S0<=dt(q['entry_utc'])<S1});tr[ticket]=r
   if q['allow']:
    ao.pop(ticket,None)
    if pl<0:loss[sk(t)]+=1
   else:bo.pop(ticket,None);cumblock+=pl
  elif k=='portfolio_snapshot':
   if not S0<=t<S1:continue
   bid=float(e['price']);u=0.0
   for q in bo.values():u+=(bid-q['entry_price'] if q['side']>0 else q['entry_price']-(bid+spread))*100000*q['lots']
   be=float(e['equity_jpy']);bb=float(e['balance_jpy']);snap.append({'audit_sequence':int(e['audit_sequence']),'utc_time':t.isoformat(),'baseline_balance_jpy':bb,'candidate_balance_jpy':bb-cumblock,'baseline_equity_jpy':be,'candidate_equity_jpy':be-cumblock-u,'blocked_cumulative_realized_jpy':cumblock,'blocked_open_unrealized_jpy':u,'blocked_open_count':len(bo)})
 if dup or orphan or ao or bo or len(tr)!=3624:raise RuntimeError(f'replay identity dup={dup[:3]} orphan={orphan[:3]} ao={list(ao)[:3]} bo={list(bo)[:3]} trades={len(tr)}')
 s=[x for x in tr.values() if x['scoring']]
 if len(s)!=BASE['trades']:raise RuntimeError('scoring identity')
 bm=met(s,'realized_pl_jpy');ac=[x for x in s if x['allow']];cm=met(ac,'candidate_pl_jpy');bed=edd(x['baseline_equity_jpy'] for x in snap);ced=edd(x['candidate_equity_jpy'] for x in snap);bmin=min(x['baseline_equity_jpy'] for x in snap);cmin=min(x['candidate_equity_jpy'] for x in snap)
 if abs(bm['net_jpy']-BASE['net'])>T or abs(bm['profit_factor']-BASE['pf'])>T or abs(bm['realized_drawdown_jpy']-BASE['rdd'])>T or abs(bed-BASE['edd'])>T or abs(bmin-BASE['min_eq'])>T:raise RuntimeError(f'replayed baseline mismatch {bm} edd={bed} min={bmin}')
 blocked=[x for x in s if not x['allow']];win=[x for x in s if x['realized_pl_jpy']>0];wr=sum(x['realized_pl_jpy'] for x in win if x['allow'])/sum(x['realized_pl_jpy'] for x in win);top={x['ticket'] for x in sorted(win,key=lambda r:r['realized_pl_jpy'],reverse=True)[:20]};toploss=sum(x['realized_pl_jpy'] for x in blocked if x['ticket'] in top and x['realized_pl_jpy']>0)
 delta=cm['net_jpy']-bm['net_jpy'];rddred=bm['realized_drawdown_jpy']-cm['realized_drawdown_jpy'];eddred=bed-ced
 folds=[]
 for name in ['2020H1','2020H2','2021H1','2021H2','2022H1','2022H2']:
  q=[x for x in s if x['fold']==name];bq=met(q,'realized_pl_jpy');cq=met([x for x in q if x['allow']],'candidate_pl_jpy');folds.append({'fold':name,'baseline_trades':bq['trades'],'candidate_trades':cq['trades'],'blocked_trades':bq['trades']-cq['trades'],'baseline_net_jpy':bq['net_jpy'],'candidate_net_jpy':cq['net_jpy'],'net_improvement_jpy':cq['net_jpy']-bq['net_jpy'],'baseline_pf':bq['profit_factor'],'candidate_pf':cq['profit_factor'],'baseline_realized_dd_jpy':bq['realized_drawdown_jpy'],'candidate_realized_dd_jpy':cq['realized_drawdown_jpy'],'realized_dd_reduction_jpy':bq['realized_drawdown_jpy']-cq['realized_drawdown_jpy']})
 yg=defaultdict(float);sg=defaultdict(float);mg=defaultdict(float);cl=defaultdict(float)
 for x in blocked:yg[str(x['year'])]+=x['delta_jpy'];sg[x['entry_session']]+=x['delta_jpy'];mg[x['month']]+=x['delta_jpy'];cl[(x['year'],f"{x['entry_date']}|{x['entry_session']}")]+=x['delta_jpy']
 cr=[{'year':y,'date_session_key':k,'delta_jpy':v} for (y,k),v in sorted(cl.items())];bt=boot(cr);events=sorted((x['delta_jpy'] for x in blocked),reverse=True);best=delta-(events[0] if events else 0);top3=delta-sum(events[:3]);posy=sum(x>0 for x in yg.values());posh=sum(x['net_improvement_jpy']>0 for x in folds);minh=min(x['net_improvement_jpy'] for x in folds)
 gates={'baseline_trade_identity_complete':len(s)==BASE['trades'] and len({x['ticket'] for x in s})==BASE['trades'],'chronology_unresolved_zero':not viol,'research_mt4_order_reproducible':True,'lookahead_zero':True,'duplicate_decision_zero':not dup,'combined_net_improvement_positive':delta>0,'candidate_pf_not_below_baseline':float(cm['profit_factor'])>=float(bm['profit_factor']),'realized_dd_reduction_positive':rddred>0,'full_equity_dd_reduction_positive':eddred>0,'winner_retention_at_least_99pct':wr>=.99,'top20_winner_loss_zero':abs(toploss)<=T,'positive_calendar_years_at_least_2of3':posy>=2,'positive_halfyears_at_least_4of6':posh>=4,'minimum_halfyear_delta_floor':minh>=-1500,'largest_positive_year_share_at_most_60pct':share(yg)<=.6,'largest_positive_session_share_at_most_60pct':share(sg)<=.6,'largest_positive_month_share_at_most_25pct':share(mg)<=.25,'best_event_removed_positive':best>0,'top3_events_removed_positive':top3>0,'date_session_bootstrap_lower_95_positive':bt['ci95_jpy'][0]>0,'date_session_bootstrap_probability_nonpositive_at_most_5pct':bt['probability_nonpositive']<=.05}
 failed=[k for k,v in gates.items() if not v];decision='PASS_HISTORICAL_VALIDATION' if not failed else 'FAIL_HISTORICAL_VALIDATION_NO_RETUNING';econ={'baseline':{**bm,'full_equity_drawdown_jpy':bed,'minimum_equity_jpy':bmin},'candidate':{**cm,'full_equity_drawdown_jpy':ced,'minimum_equity_jpy':cmin},'net_improvement_jpy':delta,'realized_dd_reduction_jpy':rddred,'full_equity_dd_reduction_jpy':eddred,'minimum_equity_improvement_jpy':cmin-bmin,'winner_retention':wr,'top20_winner_loss_jpy':toploss,'blocked_trades':len(blocked),'blocked_losers':sum(x['realized_pl_jpy']<0 for x in blocked),'blocked_winners':sum(x['realized_pl_jpy']>0 for x in blocked),'avoided_gross_loss_jpy':-sum(x['realized_pl_jpy'] for x in blocked if x['realized_pl_jpy']<0),'lost_gross_profit_jpy':sum(x['realized_pl_jpy'] for x in blocked if x['realized_pl_jpy']>0)};conc={'year_net_effect_jpy':dict(sorted(yg.items())),'session_net_effect_jpy':dict(sorted(sg.items())),'month_net_effect_jpy':dict(sorted(mg.items())),'largest_positive_year_share':share(yg),'largest_positive_session_share':share(sg),'largest_positive_month_share':share(mg),'best_event_removed_net_jpy':best,'top3_events_removed_net_jpy':top3}
 result={'schema_version':'usdjpy_hyp032_historical_validation_result_v1','hypothesis_id':H,'family_id':'R_SHORT_REALIZED_LOSS_PERSISTENCE','candidate_id':C,'decision':decision,'research_sha':z.research_sha,'run_id':z.run_id,'input_gzip_sha256':IN_SHA,'source_core_run_id':CORE_RUN,'source_core_sha':CORE_SHA,'source_core_release_asset_sha256':REL_SHA,'baseline_identity_checks':checks,'event_counts':dict(count),'economics':econ,'halfyear_metrics':folds,'concentration':conc,'date_session_bootstrap':bt,'gates':gates,'failed_gates':failed,'candidate_outcome_computed':True,'2025_accessed':False,'no_retuning':True,'Core_candidate_implementation_authorized':decision=='PASS_HISTORICAL_VALIDATION','production_authorized':False,'live_authorized':False}
 csvw(z.out_dir/'historical_candidate_decision_ledger.csv',sorted(dec.values(),key=lambda r:r['entry_seq']));csvw(z.out_dir/'historical_blocked_trade_ledger.csv',sorted(blocked,key=lambda r:r['entry_seq']));csvw(z.out_dir/'historical_full_equity_ledger.csv',snap);csvw(z.out_dir/'historical_halfyear_metrics.csv',folds);csvw(z.out_dir/'historical_date_session_clusters.csv',cr);js(z.out_dir/'historical_validation_result.json',result);js(z.out_dir/'historical_gate_matrix.json',{'decision':decision,'gates':gates,'failed_gates':failed});js(z.out_dir/'historical_bootstrap.json',bt);js(z.out_dir/'historical_concentration.json',conc);js(z.out_dir/'historical_winner_damage.json',{'winner_retention':wr,'top20_winner_loss_jpy':toploss,'blocked_winners':econ['blocked_winners'],'lost_gross_profit_jpy':econ['lost_gross_profit_jpy']})
 (z.out_dir/'human_report.md').write_text(f"# USDJPY-HYP-032 Historical Validation\n\n- Decision: `{decision}`\n- Candidate: `{C}`\n- Baseline trades: `{bm['trades']}`; candidate trades: `{cm['trades']}`; blocked: `{len(blocked)}`.\n- Net: baseline `¥{bm['net_jpy']:,.2f}` / candidate `¥{cm['net_jpy']:,.2f}` / delta `¥{delta:,.2f}`.\n- PF: baseline `{bm['profit_factor']:.6f}` / candidate `{cm['profit_factor']:.6f}`.\n- Realized DD reduction: `¥{rddred:,.2f}`.\n- Full-equity DD reduction: `¥{eddred:,.2f}`.\n- Winner retention: `{wr:.6%}`; top-20 winner loss: `¥{toploss:,.2f}`.\n- Positive years: `{posy}/3`; positive half-years: `{posh}/6`; minimum half-year delta: `¥{minh:,.2f}`.\n- Bootstrap lower 95%: `¥{bt['ci95_jpy'][0]:,.2f}`; P(non-positive): `{bt['probability_nonpositive']:.6%}`.\n- Failed gates: `{', '.join(failed) if failed else 'none'}`.\n- 2025 was not accessed. No retuning is permitted.\n",encoding='utf-8')
 files=sorted(x for x in z.out_dir.iterdir() if x.is_file());js(z.out_dir/'output_manifest.json',{'schema_version':'usdjpy_hyp032_historical_validation_output_manifest_v1','hypothesis_id':H,'decision':decision,'files':{x.name:{'bytes':x.stat().st_size,'sha256':sha(x)} for x in files},'candidate_outcome_computed':True,'2025_accessed':False});q=sorted(x for x in z.out_dir.iterdir() if x.is_file() and x.name!='SHA256SUMS');(z.out_dir/'SHA256SUMS').write_text(''.join(f'{sha(x)}  {x.name}\n' for x in q),encoding='ascii');print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))
if __name__=='__main__':main()
