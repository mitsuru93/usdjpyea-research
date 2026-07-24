#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import evaluate_usdjpy_b02_f05_structural_sl_atlas_v2 as atlas
from usdjpy_policy_v3.common import *

MONTH_WINDOWS=['EXPANDING','ROLLING_6M','ROLLING_12M'];ROUTERS=['SESSION_X_VOL','SIDE_X_VOL','SESSION_X_SIDE_X_VOL'];QUORUM=[2,3];VOTE_WINDOWS=[5,15,30];MODELS=['RIDGE_ALPHA10','HIST_GB_REGULARIZED'];MARGINS=[0.,1.,2.];PERSIST=[1,2];HMM_K=[2,3,4]
FEATURES=['current_norm','mfe_norm','mae_norm','giveback_norm','level_distance_norm','underwater_fraction','crossings','slope_tstat','delta_norm','time_fraction','pre_range_pips'];HMM_FEATURES=['current_norm','delta_norm','giveback_norm','level_distance_norm','underwater_fraction']

def monthly(events,master):
    detail=[];summ=[];months=sorted(master.month.unique())
    for sc in SCOPES:
        ms=scope(master,sc);es=scope(events,sc)
        for w in MONTH_WINDOWS:
            parts=[]
            for i in range(6,len(months)):
                test=months[i];train=months[:i] if w=='EXPANDING' else months[max(0,i-(6 if w=='ROLLING_6M' else 12)):i]
                cid,_=select_candidate(es[es.entry_utc.dt.strftime('%Y-%m').isin(train)])
                h=es[(es.entry_utc.dt.strftime('%Y-%m')==test)&(es.candidate_id==cid)] if cid else es.iloc[:0]
                if len(h):parts.append(h)
                detail.append({'scope':sc,'window':w,'test_month':test,'training_months':len(train),'selected_candidate':cid,'holdout_triggers':len(h),'holdout_delta_pips':round(float(h.delta_pips.sum()),1),'holdout_severe1_pips':round(float(h.severe1_delta_pips.sum()),1)})
            z=pd.concat(parts,ignore_index=True) if parts else es.iloc[:0];summ.append(policy_summary(z,ms,'MONTHLY_WALK_FORWARD',f'{sc}|{w}'))
    return pd.DataFrame(detail),summ

def volbin(df,cuts):return pd.cut(df.pre_range_pips,[-np.inf,cuts[0],cuts[1],np.inf],labels=['LOW','MID','HIGH'],include_lowest=True).astype(str)
def regkey(df,r):
    if r=='SESSION_X_VOL':return df.session.astype(str)+'|'+df.vol.astype(str)
    if r=='SIDE_X_VOL':return df.side.astype(str)+'|'+df.vol.astype(str)
    return df.session.astype(str)+'|'+df.side.astype(str)+'|'+df.vol.astype(str)

def router(events,master):
    detail=[];summ=[]
    for sc in SCOPES:
        ms=scope(master,sc);es=scope(events,sc)
        for r in ROUTERS:
            parts=[]
            for hold in FOLDS:
                tr=ms[ms.fold!=hold].copy();te=ms[ms.fold==hold].copy();cuts=tuple(tr.pre_range_pips.quantile([1/3,2/3]).to_numpy(float));tr['vol']=volbin(tr,cuts);te['vol']=volbin(te,cuts);tr['reg']=regkey(tr,r);te['reg']=regkey(te,r);selected={}
                for reg,g in tr.groupby('reg'):
                    if len(g)<30:continue
                    cid,_=select_candidate(es[(es.fold!=hold)&es.trade_id.isin(g.trade_id)])
                    if cid:selected[str(reg)]=cid
                out=[]
                for reg,cid in selected.items():
                    ids=set(te.loc[te.reg==reg,'trade_id']);out.append(es[(es.fold==hold)&(es.candidate_id==cid)&es.trade_id.isin(ids)])
                h=pd.concat(out,ignore_index=True) if out else es.iloc[:0]
                if len(h):parts.append(h)
                detail.append({'scope':sc,'router':r,'holdout':hold,'regimes_selected':len(selected),'holdout_triggers':len(h),'holdout_delta_pips':round(float(h.delta_pips.sum()),1),'holdout_severe1_pips':round(float(h.severe1_delta_pips.sum()),1)})
            z=pd.concat(parts,ignore_index=True) if parts else es.iloc[:0];summ.append(policy_summary(z,ms,'EX_ANTE_REGIME_ROUTER',f'{sc}|{r}'))
    return pd.DataFrame(detail),summ

def first_vote(g,q,w):
    a=list(g.sort_values('trigger_utc').itertuples(index=False));cnt=defaultdict(int);left=0
    for right,row in enumerate(a):
        cnt[row.family]+=1;cut=pd.Timestamp(row.trigger_utc)-pd.Timedelta(minutes=w)
        while left<=right and pd.Timestamp(a[left].trigger_utc)<cut:
            cnt[a[left].family]-=1
            if cnt[a[left].family]<=0:del cnt[a[left].family]
            left+=1
        if len(cnt)>=q:return row._asdict()
    return None

def votes(events,master):
    detail=[];summ=[];families=sorted(events.family.unique())
    for sc in SCOPES:
        ms=scope(master,sc);es=scope(events,sc)
        for q in QUORUM:
            for w in VOTE_WINDOWS:
                allrows=[]
                for hold in FOLDS:
                    train=es[es.fold!=hold];selected=[]
                    for fam in families:
                        cid,_=select_candidate(train,fam)
                        if cid:selected.append(cid)
                    he=es[(es.fold==hold)&es.candidate_id.isin(selected)];rows=[]
                    for _,g in he.groupby('trade_id'):
                        x=first_vote(g,q,w)
                        if x:rows.append(x)
                    h=pd.DataFrame(rows)
                    if len(h):
                        for c in ['entry_utc','trigger_utc','exit_utc']:h[c]=pd.to_datetime(h[c],utc=True)
                        allrows.append(h)
                    detail.append({'scope':sc,'quorum':q,'window_minutes':w,'holdout':hold,'families_selected':len(selected),'holdout_triggers':len(h),'holdout_delta_pips':round(float(h.delta_pips.sum()),1) if len(h) else 0.,'holdout_severe1_pips':round(float(h.severe1_delta_pips.sum()),1) if len(h) else 0.})
                z=pd.concat(allrows,ignore_index=True) if allrows else es.iloc[:0];summ.append(policy_summary(z,ms,'FAMILY_VOTE',f'{sc}|Q{q}|W{w}'))
    return pd.DataFrame(detail),summ

def matrix(df,cols=None):
    x=pd.get_dummies(df[FEATURES+['side','session']].copy(),columns=['side','session'],dtype=float).replace([np.inf,-np.inf],np.nan).fillna(0.)
    if cols is not None:x=x.reindex(columns=cols,fill_value=0.)
    return x.to_numpy(float),list(x.columns)
@dataclass
class Bundle:pred:Any

def fitreg(name,df,y):
    X,c=matrix(df)
    if name=='RIDGE_ALPHA10':
        s=StandardScaler();m=Ridge(alpha=10.).fit(s.fit_transform(X),y);return Bundle(lambda z:m.predict(s.transform(z))),c
    m=HistGradientBoostingRegressor(max_leaf_nodes=7,max_iter=80,learning_rate=.05,l2_regularization=2.,min_samples_leaf=20,random_state=RNG_SEED).fit(X,y);return Bundle(m.predict),c

def train_dynamic(df,name):
    bt={tid:g.sort_values('time_idx') for tid,g in df.groupby('trade_id')};nxt={tid:float(g.baseline_pips.iloc[0]) for tid,g in bt.items()};models={}
    for t in range(48,0,-1):
        rows=[];y=[]
        for tid,g in bt.items():
            q=g[g.time_idx==t]
            if len(q):rows.append(q.iloc[0]);y.append(nxt[tid])
        if len(rows)<40:continue
        fr=pd.DataFrame(rows);b,c=fitreg(name,fr,np.array(y));models[t]=(b,c);X,_=matrix(fr,c);v=np.maximum(fr.exit_pips.to_numpy(float)-1.,b.pred(X))
        for tid,z in zip(fr.trade_id,v):nxt[tid]=float(z)
    return models

def run_dynamic(df,models,margin,pers):
    out=[]
    for tid,g in df.groupby('trade_id'):
        g=g.sort_values('time_idx');run=0;chosen=None
        for _,r in g.iterrows():
            if int(r.time_idx) not in models:continue
            b,c=models[int(r.time_idx)];X,_=matrix(pd.DataFrame([r]),c);run=run+1 if float(r.exit_pips)-1.>=float(b.pred(X)[0])+margin else 0
            if run>=pers:chosen=r;break
        if chosen is not None:
            pos=g.index.get_loc(chosen.name);delay=float(g.iloc[min(pos+1,len(g)-1)].exit_pips);out.append({'trade_id':tid,'fold':chosen.fold,'strategy':chosen.strategy,'side':int(chosen.side),'entry_utc':chosen.entry_utc,'trigger_utc':chosen.trigger_utc,'baseline_pips':float(chosen.baseline_pips),'baseline_loser':bool(chosen.baseline_loser),'candidate_pips':float(chosen.exit_pips),'delta_pips':float(chosen.exit_pips-chosen.baseline_pips),'severe1_delta_pips':float(chosen.exit_pips-1-chosen.baseline_pips),'severe2_delta_pips':float(chosen.exit_pips-2-chosen.baseline_pips),'delay5_delta_pips':float(delay-chosen.baseline_pips)})
    return pd.DataFrame(out)

def dynamic(states,master):
    detail=[];summ=[]
    for st in STRATEGIES:
        ms=master[master.strategy==st];ss=states[states.strategy==st]
        for name in MODELS:
            store={(m,p):[] for m in MARGINS for p in PERSIST}
            for hold in FOLDS:
                models=train_dynamic(ss[ss.fold!=hold],name)
                for m in MARGINS:
                    for p in PERSIST:
                        h=run_dynamic(ss[ss.fold==hold],models,m,p)
                        if len(h):store[(m,p)].append(h)
                        detail.append({'strategy':st,'model':name,'margin':m,'persistence':p,'holdout':hold,'trained_time_models':len(models),'holdout_triggers':len(h),'holdout_delta_pips':round(float(h.delta_pips.sum()),1) if len(h) else 0.,'holdout_severe1_pips':round(float(h.severe1_delta_pips.sum()),1) if len(h) else 0.})
            for (m,p),z in store.items():summ.append(policy_summary(pd.concat(z,ignore_index=True) if z else pd.DataFrame(),ms,'APPROX_OPTIMAL_STOPPING',f'{st}|{name}|M{m}|P{p}'))
    return pd.DataFrame(detail),summ

def hmm(states,master):
    detail=[];summ=[]
    for st in STRATEGIES:
        ms=master[master.strategy==st];ss=states[states.strategy==st];store={(k,p):[] for k in HMM_K for p in PERSIST}
        for hold in FOLDS:
            tr=ss[ss.fold!=hold].copy();te=ss[ss.fold==hold].copy();sc=StandardScaler().fit(tr[HMM_FEATURES].fillna(0));X=sc.transform(tr[HMM_FEATURES].fillna(0));Z=sc.transform(te[HMM_FEATURES].fillna(0));L=tr.groupby('trade_id',sort=False).size().tolist();LT=te.groupby('trade_id',sort=False).size().tolist()
            for k in HMM_K:
                mod=GaussianMarkov(k).fit(X,L);tr['state']=mod.predict(X,L);te['state']=mod.predict(Z,LT);selected=[]
                for state,g in tr.groupby('state'):
                    lo=g[g.baseline_loser==1];wi=g[g.baseline_loser==0];ben=float((lo.exit_pips-lo.baseline_pips-1).sum());dam=float((wi.exit_pips-wi.baseline_pips-1).sum())
                    if len(g)>=40 and len(lo)>=10 and ben+dam>0 and ben>0 and dam>=-.7*ben:selected.append(int(state))
                for p in PERSIST:
                    rows=[]
                    for tid,g in te.groupby('trade_id'):
                        g=g.sort_values('time_idx');run=0;ch=None
                        for _,r in g.iterrows():
                            run=run+1 if int(r.state) in selected else 0
                            if run>=p:ch=r;break
                        if ch is not None:
                            pos=g.index.get_loc(ch.name);delay=float(g.iloc[min(pos+1,len(g)-1)].exit_pips);rows.append({'trade_id':tid,'fold':ch.fold,'strategy':ch.strategy,'side':int(ch.side),'entry_utc':ch.entry_utc,'trigger_utc':ch.trigger_utc,'baseline_pips':float(ch.baseline_pips),'baseline_loser':bool(ch.baseline_loser),'candidate_pips':float(ch.exit_pips),'delta_pips':float(ch.exit_pips-ch.baseline_pips),'severe1_delta_pips':float(ch.exit_pips-1-ch.baseline_pips),'severe2_delta_pips':float(ch.exit_pips-2-ch.baseline_pips),'delay5_delta_pips':float(delay-ch.baseline_pips)})
                    h=pd.DataFrame(rows)
                    if len(h):store[(k,p)].append(h)
                    detail.append({'strategy':st,'components':k,'persistence':p,'holdout':hold,'selected_states':json.dumps(selected),'holdout_triggers':len(h),'holdout_delta_pips':round(float(h.delta_pips.sum()),1) if len(h) else 0.,'holdout_severe1_pips':round(float(h.severe1_delta_pips.sum()),1) if len(h) else 0.})
        for (k,p),z in store.items():summ.append(policy_summary(pd.concat(z,ignore_index=True) if z else pd.DataFrame(),ms,'GAUSSIAN_MARKOV_STATE',f'{st}|K{k}|P{p}'))
    return pd.DataFrame(detail),summ

def oracle(states,events,master):
    bs=states.groupby('trade_id').exit_pips.max();be=events.groupby('trade_id').delta_pips.max();rows=[]
    for r in master.itertuples(index=False):rows.append({'trade_id':r.trade_id,'strategy':r.strategy,'loser':bool(r.baseline_loser),'state':float(bs.get(r.trade_id,r.baseline_pips))-r.baseline_pips,'event':float(be.get(r.trade_id,0.))})
    x=pd.DataFrame(rows);lo=x[x.loser];fixed=[]
    for cp in [5,15,30,60,120,180,240]:
        for st in STRATEGIES:
            g=states[(states.minutes==cp)&(states.strategy==st)];fixed.append({'strategy':st,'checkpoint_minutes':cp,'trades_available':len(g),'all_trade_delta_pips':round(float(g.delta_pips.sum()),1),'loser_only_delta_pips':round(float(g[g.baseline_loser==1].delta_pips.sum()),1),'winner_delta_pips':round(float(g[g.baseline_loser==0].delta_pips.sum()),1)})
    a=float(lo.state.clip(lower=0).sum());b=float(lo.event.clip(lower=0).sum());return {'loss_only_5m_oracle_salvage_pips':round(a,1),'loss_only_atlas_candidate_oracle_salvage_pips':round(b,1),'atlas_candidate_capture_ratio':round(b/max(a,1e-9),6),'universal_5m_oracle_improvement_pips':round(float(x.state.clip(lower=0).sum()),1),'loser_count':len(lo),'fixed_checkpoint_benchmarks':fixed,'lookahead_diagnostic_only':True}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--protocol',type=Path,required=True);ap.add_argument('--preflight-only',action='store_true');ap.add_argument('--atlas-dir',type=Path);ap.add_argument('--m15-2023',type=Path);ap.add_argument('--m1-2023',type=Path);ap.add_argument('--events-2024h1',type=Path);ap.add_argument('--events-2024h2',type=Path);ap.add_argument('--m1-2024',type=Path);ap.add_argument('--out-dir',type=Path);ap.add_argument('--research-commit',default='');ap.add_argument('--workflow-run-id',default='');ap.add_argument('--workflow-run-attempt',default='');a=ap.parse_args();p=verify_protocol(a.protocol)
    pre={'schema_version':'usdjpy_b02_f05_structural_sl_policy_regime_preflight_v3','status':'PASS_NO_OUTCOMES','protocol_sha256':sha256_file(a.protocol),'evaluator_sha256':sha256_file(Path(__file__)),'methods':6,'policy_cells':69,'outcomes_computed':False,'mt4_accessed':False,'2025_accessed':False,'candidate_frozen':False,'notion_task_dependency':False}
    if a.preflight_only:print(json.dumps(pre,indent=2,sort_keys=True));return 0
    a.out_dir.mkdir(parents=True,exist_ok=True);write_json(a.out_dir/'preflight_result_v3.json',pre);events,_,diag=load_atlas(a.atlas_dir,p);trades,m23,m24,src=atlas.load_authorities(a);master=make_master(trades,diag)
    print('monthly',file=sys.stderr);mwd,mws=monthly(events,master);print('router',file=sys.stderr);rrd,rrs=router(events,master);print('votes',file=sys.stderr);fvd,fvs=votes(events,master);print('state ledger',file=sys.stderr);states=state_ledger(trades,m23,m24,atlas);print('dynamic',file=sys.stderr);dpd,dps=dynamic(states,master);print('markov',file=sys.stderr);hmd,hms=hmm(states,master)
    summaries=mws+rrs+fvs+dps+hms;surv=[x for x in summaries if x['binding_gate_pass']];status='POLICY_REGIME_AUDIT_COMPLETE_SURVIVOR_REQUIRES_FULL_REPLAY' if surv else 'POLICY_REGIME_AUDIT_COMPLETE_NO_SURVIVOR'
    pd.DataFrame(summaries).to_csv(a.out_dir/'policy_summary_v3.csv',index=False);mwd.to_csv(a.out_dir/'monthly_walk_forward_v3.csv',index=False);rrd.to_csv(a.out_dir/'regime_router_v3.csv',index=False);fvd.to_csv(a.out_dir/'family_vote_v3.csv',index=False);dpd.to_csv(a.out_dir/'dynamic_policy_v3.csv',index=False);hmd.to_csv(a.out_dir/'gaussian_markov_v3.csv',index=False);states.to_csv(a.out_dir/'state_ledger_5m_v3.csv.gz',index=False,compression='gzip',float_format='%.6f')
    result={'schema_version':'usdjpy_b02_f05_structural_sl_policy_regime_result_v3','status':status,'research_commit':a.research_commit,'workflow_run_id':int(a.workflow_run_id) if a.workflow_run_id else None,'workflow_run_attempt':int(a.workflow_run_attempt) if a.workflow_run_attempt else None,'population':{'trade_count':len(master),'baseline_loser_count':int(master.baseline_loser.sum()),'state_rows':len(states)},'methods':{'monthly_walk_forward_cells':len(mws),'regime_router_cells':len(rrs),'family_vote_cells':len(fvs),'dynamic_policy_cells':len(dps),'gaussian_markov_cells':len(hms)},'survivor_count':len(surv),'survivors':surv,'top_pooled_policies':sorted(summaries,key=lambda x:x['total_delta_pips'],reverse=True)[:20],'oracle_bounds':oracle(states,events,master),'decision':{'candidate_frozen':False,'implementation_authorized':False,'survivor_requires_full_admission_portfolio_replay':True,'survivor_requires_raw_tick_event_order':True,'survivor_requires_mt4_parity':True,'existing_F05_failed_reclaim_unchanged':True},'boundaries':{'fixed_pip_stop_evaluated':False,'full_admission_portfolio_replay_computed':False,'mt4_accessed':False,'2025H1_accessed':False,'2025H2_accessed':False,'notion_used_as_task_source':False,'closed_hypotheses_reopened':False}}
    write_json(a.out_dir/'result_v3.json',result);write_json(a.out_dir/'output_manifest_v3.json',{'schema_version':'usdjpy_b02_f05_structural_sl_policy_regime_output_manifest_v3','files':{q.name:{'bytes':q.stat().st_size,'sha256':sha256_file(q)} for q in sorted(a.out_dir.iterdir()) if q.is_file()}});print(json.dumps({'status':status,'trades':len(master),'state_rows':len(states),'policy_cells':len(summaries),'survivors':len(surv)},sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
