#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

CANDIDATE='SESSION_LOSS_CAP_2'; SEED=20260728

def sha(p:Path)->str:
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def dump(p:Path,x:Any): p.write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def sl(t):
 h=t.hour
 return 'Tokyo' if h<7 else 'London' if h<13 else 'London_NY_overlap' if h<16 else 'New_York' if h<20 else 'session_transition'
def sk(t): return f"{t:%Y-%m-%d}|{sl(t)}"
def bounds(t):
 a={'Tokyo':(0,7),'London':(7,13),'London_NY_overlap':(13,16),'New_York':(16,20),'session_transition':(20,24)}[sl(t)]
 d=t.normalize(); return d+pd.Timedelta(hours=a[0]),d+pd.Timedelta(hours=a[1])
def pf(s):
 gp=float(s[s>0].sum()); gl=float(-s[s<0].sum()); return None if gl==0 and gp==0 else math.inf if gl==0 else gp/gl
def dd(x,col):
 z=x.sort_values(['close_utc','trade_id'],kind='mergesort')[col].cumsum(); return float((z.cummax().clip(lower=0)-z).max())

def replay(d,offset=0,close_first=True,shuffle=None):
 x=d.sample(frac=1,random_state=shuffle) if shuffle else d
 x=x.sort_values(['entry_utc','strategy','trade_id'],kind='mergesort')
 open_,losses,ids,states,closes={},{},{},[],[]
 for ts,g in x.groupby('entry_utc',sort=True):
  def close():
   q=[v for v in open_.values() if v['close_utc']+pd.Timedelta(seconds=offset)<=ts]
   for v in sorted(q,key=lambda z:(z['close_utc']+pd.Timedelta(seconds=offset),z['trade_id'])):
    k=v['exit_session_key']; before=losses.get(k,0); pnl=v['realized_pl_jpy']
    if pnl<0: losses[k]=before+1
    ids.setdefault(k,[]).append(v['trade_id'])
    closes.append({'trade_id':v['trade_id'],'close_utc':v['close_utc'].strftime('%Y-%m-%dT%H:%M:%SZ'),'exit_session_key':k,'realized_pl_jpy':pnl,'loss_count_before':before,'loss_count_after':losses.get(k,0),'state_updated':pnl<0})
    del open_[v['trade_id']]
  if close_first: close()
  for r in g.sort_values(['strategy','trade_id'],kind='mergesort').itertuples(index=False):
   n=losses.get(r.entry_session_key,0); allow=n<2; a,b=bounds(r.entry_utc)
   states.append({'candidate_id':CANDIDATE,'trade_id':r.trade_id,'entry_decision_utc':r.entry_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),'session_key':r.entry_session_key,'session_start_utc':a.strftime('%Y-%m-%dT%H:%M:%SZ'),'session_end_utc':b.strftime('%Y-%m-%dT%H:%M:%SZ'),'prior_accepted_close_count_in_session':len(ids.get(r.entry_session_key,[])),'prior_accepted_close_ids_in_session':';'.join(ids.get(r.entry_session_key,[])),'prior_realized_loss_count':n,'last_state_reset_utc':a.strftime('%Y-%m-%dT%H:%M:%SZ'),'allow':allow,'blocking_reason':'accepted' if allow else 'session_loss_cap','decision_information_cutoff_utc':r.entry_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),'future_information_violation':False})
   if allow: open_[r.trade_id]={'trade_id':r.trade_id,'close_utc':r.close_utc,'realized_pl_jpy':float(r.realized_pl_jpy),'exit_session_key':r.exit_session_key}
  if not close_first: close()
 return pd.DataFrame(states),pd.DataFrame(closes)

def slices(x,col,label):
 out=[]
 for k,g in x.groupby(col,sort=True,dropna=False):
  bgp=float(g.loc[g.realized_pl_jpy>0,'realized_pl_jpy'].sum()); bgl=float(-g.loc[g.realized_pl_jpy<0,'realized_pl_jpy'].sum()); cgp=float(g.loc[g.candidate_pl_jpy>0,'candidate_pl_jpy'].sum()); cgl=float(-g.loc[g.candidate_pl_jpy<0,'candidate_pl_jpy'].sum())
  out.append({'dimension':label,'value':str(k),'baseline_trades':len(g),'blocked_trades':int((~g.allow).sum()),'baseline_net_jpy':float(g.realized_pl_jpy.sum()),'candidate_net_jpy':float(g.candidate_pl_jpy.sum()),'net_improvement_jpy':float(g.delta_jpy.sum()),'avoided_gross_loss_jpy':bgl-cgl,'lost_gross_profit_jpy':bgp-cgp,'winner_retention':None if bgp==0 else cgp/bgp,'baseline_pf':None if bgl==0 else bgp/bgl,'candidate_pf':None if cgl==0 else cgp/cgl})
 return pd.DataFrame(out)
def gate(n,p,o,r): return {'gate':n,'pass':bool(p),'observed':o,'requirement':r}
def boot(x,n=10000):
 u=x.groupby(['fold','entry_session_key'],as_index=False).delta_jpy.sum(); u=u[u.delta_jpy!=0]; rng=np.random.default_rng(SEED); strata=[g.delta_jpy.to_numpy(float) for _,g in u.groupby('fold',sort=True)]; z=np.array([sum(float(rng.choice(a,len(a),replace=True).sum()) for a in strata) for _ in range(n)])
 return {'replicates':n,'seed':SEED,'resampling_unit':'entry_session_key_stratified_by_fold','affected_units':len(u),'observed_net_improvement_jpy':float(u.delta_jpy.sum()),'ci95_jpy':[float(v) for v in np.quantile(z,[.025,.975])],'median_jpy':float(np.median(z)),'probability_nonpositive':float((z<=0).mean())}
