#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
from usdjpy_fixed5_portability_lib_v1 import *
EXPECTED={'m15':'4c10ab3244996d73d0955850675231a533f918da09a41ac642c9a3e287b7ac78','canonical_ledger':'33d08d580d584f533bc5f9dda510184fb86c668608f76f8e9b7c014924c5f1b8'}
def file_sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
def parse(root):
 reg=json.load(open(root/'workr1/r1_registry_snapshot.json')); cs={}
 for fam in reg['families']:
  for c in fam['candidates']:
   if c['id'] in IDS: cs[c['id']]=c
 sp=pd.read_csv(root/'workr6/frozen_complete_strategies.csv'); specs=[]
 for _,r in sp.iterrows():
  if r.candidate_id in IDS: specs.append({'freeze_rank':int(r.freeze_rank),'strategy_id':r.strategy_id,'candidate_id':r.candidate_id,'family':r.family,'entry_definition_sha256':r.definition_sha256,'time_cap_bars':int(r.time_cap_bars)})
 return cs,specs
def canonical_bars(p):
 d=pd.read_csv(p); return enrich(pd.DataFrame({'timestamp_utc':pd.to_datetime(d.timestamp_utc,utc=True),'symbol':'USDJPY','mid_open':d.open,'mid_high':d.high,'mid_low':d.low,'mid_close':d.close,'spread_open_pips':.5,'spread_mean_pips':.5}))
def compare_ledger(actual,accepted):
 keys=['trade_key','strategy','signal_utc','entry_utc','side','entry_index','cap_bars','closed','close_index','close_utc']; nums=['entry_bid','entry_price','close_bid','close_price','gross_pips','realized_pl_jpy']; a=accepted.copy(); b=actual.copy()
 for x in (a,b):
  x['close_utc']=x.close_utc.fillna(''); x['closed']=x.closed.astype(bool)
 exact=len(a)==len(b) and a[keys].equals(b[keys]); numeric=len(a)==len(b) and all(np.allclose(pd.to_numeric(a[c],errors='coerce'),pd.to_numeric(b[c],errors='coerce'),rtol=0,atol=1e-9,equal_nan=True) for c in nums)
 return {'rows':len(a),'exact_keys':bool(exact),'numeric':bool(numeric),'passed':bool(exact and numeric)}
def regress_signals(actual,accepted,period):
 cols=['candidate_id','family','definition_sha256','signal_ts','entry_ts','side','signal_month','signal_hour_utc','entry_month','entry_hour_utc']; rows=[]
 for cid in IDS:
  a=accepted[accepted.candidate_id==cid][cols].sort_values(['signal_ts','side']).reset_index(drop=True); b=actual[actual.candidate_id==cid][cols].sort_values(['signal_ts','side']).reset_index(drop=True)
  for x in (a,b): x[['side','signal_hour_utc','entry_hour_utc']]=x[['side','signal_hour_utc','entry_hour_utc']].astype('int64')
  rows.append({'period':period,'candidate_id':cid,'accepted':len(a),'actual':len(b),'passed':a.equals(b)})
 return pd.DataFrame(rows)
def regress_trades(actual,accepted,period):
 accepted=accepted[(accepted.candidate_id.isin(IDS))&(accepted.policy_id=='T0_fixed_time_cap')].copy(); keys=['candidate_id','family','definition_sha256','time_cap_bars','policy_id','signal_ts','entry_ts','exit_ts','side','bars_held']; nums=['entry_mid','exit_mid','default_cost_pips','severe_cost_pips','gross_pips','default_net_pips','severe_net_pips']; rows=[]
 for x in (actual,accepted):
  for c in ['signal_ts','entry_ts','exit_ts']: x[c]=pd.to_datetime(x[c],utc=True).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
 for cid in IDS:
  a=accepted[accepted.candidate_id==cid].sort_values(['entry_ts','side']).reset_index(drop=True); b=actual[actual.candidate_id==cid].sort_values(['entry_ts','side']).reset_index(drop=True); ke=len(a)==len(b) and a[keys].equals(b[keys]); ne=len(a)==len(b) and all(np.allclose(a[c].to_numpy(float),b[c].to_numpy(float),rtol=0,atol=1e-9,equal_nan=True) for c in nums); rows.append({'period':period,'candidate_id':cid,'accepted':len(a),'actual':len(b),'exact_keys':ke,'numeric':ne,'passed':ke and ne})
 return pd.DataFrame(rows)
def aggregate(alltr):
 periods={'2023H1':('2023-01-01','2023-07-01'),'2023H2':('2023-07-01','2024-01-01'),'2024H1':('2024-01-01','2024-07-01'),'2024H2':('2024-07-01','2025-01-01')}; ports={'PORT_EQ5':IDS}|{f'PORT_LOO_EXCL_{x}':[i for i in IDS if i!=x] for x in IDS}; sr=[];pr=[]; t=pd.to_datetime(alltr.entry_ts,utc=True)
 for p,(a,z) in periods.items():
  q=alltr[(t>=pd.Timestamp(a,tz='UTC'))&(t<pd.Timestamp(z,tz='UTC'))]
  for cid in IDS:
   g=q[q.candidate_id==cid]; r={'period':p,'entity_id':cid,'entity_type':'strategy'}
   for lab,col in [('default','default_net_pips'),('severe','severe_net_pips')]: r.update({f'{lab}_{k}':v for k,v in metrics(g,col).items()})
   sr.append(r)
  for pid,members in ports.items():
   g=q[q.candidate_id.isin(members)]; r={'period':p,'entity_id':pid,'entity_type':'portfolio','members':'|'.join(members)}
   for lab,col in [('default','default_net_pips'),('severe','severe_net_pips')]: r.update({f'{lab}_{k}':v for k,v in metrics(g,col).items()})
   pr.append(r)
 return pd.DataFrame(sr),pd.DataFrame(pr),ports
def gate(sr,pr):
 x=pd.concat([sr,pr],ignore_index=True,sort=False); x=x[x.period.isin(['2023H1','2023H2'])]; g=x.groupby(['entity_id','entity_type'],as_index=False).agg(default_net_pips=('default_net_pips','sum'),severe_net_pips=('severe_net_pips','sum'),default_min_half=('default_net_pips','min'),severe_min_half=('severe_net_pips','min'),trades=('default_trades','sum')); g['eligible']=(g.default_net_pips>0)&(g.severe_net_pips>0)&(g.default_min_half>=0)&(g.severe_min_half>=0); return g.sort_values(['eligible','severe_net_pips','default_net_pips'],ascending=[False,False,False]).reset_index(drop=True)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input-root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args(); root=a.input_root; out=a.output;out.mkdir(parents=True,exist_ok=True); cs,specs=parse(root); m15=root/'work23/normalized/usdjpy_2023_m15_bid_utc_rakuten_mt4_v1.csv.gz'; assert file_sha(m15)==EXPECTED['m15']; can=canonical_bars(m15); hist=load23(m15); raw=pd.read_csv(m15); true=pd.to_datetime(raw.timestamp_utc,utc=True); server=pd.to_datetime(raw.first_timestamp_mt4_server,utc=True); hts=pd.DatetimeIndex([server_to_hist_utc(x) for x in server]); transform={'rows':len(raw),'shifted_rows':int((hts!=true).sum()),'duplicates':int(hts.duplicated().sum()),'monotonic':bool(hts.is_monotonic_increasing)}; assert transform=={'rows':24825,'shifted_rows':1543,'duplicates':0,'monotonic':True}
 st=pd.Timestamp('2023-01-01',tz='UTC');en=pd.Timestamp('2024-01-01',tz='UTC'); cled=historical_ledger(can,cs,st,en); accepted=pd.read_csv(root/'work23/baseline/usdjpy_2023_canonical_baseline_expected_trade_ledger_v1.csv'); assert file_sha(root/'work23/baseline/usdjpy_2023_canonical_baseline_expected_trade_ledger_v1.csv')==EXPECTED['canonical_ledger']; cr=compare_ledger(cled,accepted); assert cr['passed']; hled=historical_ledger(hist,cs,st,en); hc=hled[hled.closed]; hs={'opened':len(hled),'closed':len(hc),'B02':int((hled.strategy=='B02').sum()),'F05':int((hled.strategy=='F05').sum()),'net_jpy':float(hc.realized_pl_jpy.sum()),'B02_net_jpy':float(hc.loc[hc.strategy=='B02','realized_pl_jpy'].sum()),'F05_net_jpy':float(hc.loc[hc.strategy=='F05','realized_pl_jpy'].sum())}; assert hs=={'opened':961,'closed':960,'B02':230,'F05':731,'net_jpy':-9279.0,'B02_net_jpy':-12459.0,'F05_net_jpy':3180.0}
 b24=load24(root/'workr0/canonical/bars/M15/USDJPY_M15.csv.gz'); sigs={};trs={}; sreg=[];treg=[]
 for p,aa,zz,sf,tf in [('2024H1','2024-01-01','2024-07-01','workr1/candidate_signals.csv.gz','workr5/exit_trades.csv.gz'),('2024H2','2024-07-01','2025-01-01','workh2/h2_candidate_signals.csv.gz','workh2/h2_candidate_trades.csv.gz')]:
  ps=pd.Timestamp(aa,tz='UTC');pe=pd.Timestamp(zz,tz='UTC'); sigs[p]=pd.concat([build_signals(b24,cs[i],ps,pe) for i in IDS],ignore_index=True); trs[p]=build_trades(b24,sigs[p],specs,ps,pe); sreg.append(regress_signals(sigs[p],pd.read_csv(root/sf),p)); treg.append(regress_trades(trs[p],pd.read_csv(root/tf),p))
 sreg=pd.concat(sreg,ignore_index=True);treg=pd.concat(treg,ignore_index=True);assert sreg.passed.all() and treg.passed.all(); sig23=pd.concat([build_signals(hist,cs[i],st,en) for i in IDS],ignore_index=True);tr23=build_trades(hist,sig23,specs,st,en);alltr=pd.concat([tr23,trs['2024H1'],trs['2024H2']],ignore_index=True);sr,pr,ports=aggregate(alltr);g=gate(sr,pr);eligible=g[g.eligible]
 for df,name in [(sreg,'usdjpy_fixed5_2024_signal_regression_v1.csv'),(treg,'usdjpy_fixed5_2024_trade_regression_v1.csv'),(sr,'usdjpy_fixed5_fourfold_strategy_metrics_v1.csv'),(pr,'usdjpy_fixed5_fourfold_portfolio_metrics_v1.csv'),(g,'usdjpy_fixed5_2023_portability_gate_v1.csv')]: df.to_csv(out/name,index=False)
 tr23.to_csv(out/'usdjpy_fixed5_2023_trades_v1.csv',index=False); hled.to_csv(out/'usdjpy_2023_legacy2024_historical_baseline_ledger_v1.csv',index=False)
 res={'schema_version':'usdjpy_fixed5_exact_portability_result_v1','status':'CLOSED_NO_PORTABLE_STRATEGY_OR_PREDECLARED_PORTFOLIO' if eligible.empty else 'PORTABLE_ENTITY_FOUND','decision':'CLOSE_RQ_020A_AND_RQ_020D; AUTHORIZE_RQ_020B_LONG_HORIZON_REGIME_DIAGNOSIS' if eligible.empty else 'FREEZE_AT_MOST_ONE_PORTABLE_ENTITY','transform':transform,'canonical_baseline_reconciliation':cr,'legacy2024_2023_baseline':hs,'fixed_cohort':IDS,'portfolios':ports,'2024_regression_all_pass':bool(sreg.passed.all() and treg.passed.all()),'eligible_count':len(eligible),'gate_rows':g.to_dict('records'),'boundaries':{'2024_source_mutated':False,'parameters_changed':False,'weights_optimized':False,'2025_accessed':False,'MT4_accessed':False,'live_orders':False}}
 res['output_sha256']={p.name:file_sha(p) for p in out.iterdir() if p.is_file()}; (out/'usdjpy_fixed5_exact_portability_result_v1.json').write_text(json.dumps(res,indent=2,sort_keys=True)+'\n'); print(json.dumps(res,indent=2,sort_keys=True))
if __name__=='__main__':main()
