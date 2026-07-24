#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,math,re
from datetime import datetime,timezone,timedelta,time
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np,pandas as pd
PIP=.01;SP=.005
FOLDS=['2023H1','2023H2','2024H1','2024H2']
SHA={'m1_2023':'167509bde6553a468ffe48b082ed79de183cc57991f668cf4b3e7341350d307e','m15_2023':'4c10ab3244996d73d0955850675231a533f918da09a41ac642c9a3e287b7ac78','events_2024h1':'9560d6382e2457eaec83415316fb59d4989244d49c9977ce76cbdd717f32f09a','events_2024h2':'a5a871d7105c6e68548e804c9ab517ee6bc0b08553474b158799f47ebd32edcd','m1_2024':'f9f56be2daa39f07dc39cec197306fb87821ead01e4a640a73f17715bf27dde0','m5_2024':'af04cf642171a1916abc11a77d0120e88a1f61382385e54c9a49d9107d5d7f36','report':'489a2484be135209fd731951990e508b67d6ff11cd2aeff3a4fbac23dffdfad5'}
EXP={'n':14,'total':202.1,'long':65.2,'short':136.9,'folds':{'2023H1':(4,70.8),'2023H2':(4,14.1),'2024H1':(5,110.7),'2024H2':(1,6.5)}}
def h(p):
 x=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):x.update(b)
 return x.hexdigest()
def r1(x):return float(round(float(x)+0.,1))
def z(t):return pd.Timestamp(t).tz_convert('UTC').strftime('%Y-%m-%dT%H:%M:%SZ')
def nth(y,m,n,h):
 d=datetime(y,m,1,h,tzinfo=timezone.utc);return pd.Timestamp(d+timedelta(days=(6-d.weekday())%7+7*(n-1)))
def hist(s):
 w=s-pd.Timedelta(hours=2);return s-pd.Timedelta(hours=3) if nth(s.year,3,2,7)<=w<nth(s.year,11,1,6) else w
def excl(s):
 t=s.dt.tz_convert(ZoneInfo('America/New_York')).dt.time;return (t>=time(16))&(t<time(19))
def protocol(p):
 q=json.loads(Path(p).read_text());assert q['schema_version']=='f05_failed_reclaim_validation_protocol_v1' and q['status']=='FROZEN_BEFORE_OUTCOME_EXECUTION';c=q['candidates'];assert c['count']==2 and c['binding_count']==1 and c['binding']['candidate_id']=='F05_FAILED_RECLAIM_BASIC_V1' and c['non_binding_sensitivity']['candidate_id']=='F05_FAILED_RECLAIM_WEAK_QUICK_V1' and c['non_binding_sensitivity']['binding'] is False and c['binding']['reclaim_failure']['same_timestamp_m5_forbidden'] is True and q['authorizing_instruction']['notion_task_dependency'] is False;return q
def source(a):
 act={'m1_2023':h(a.m1_2023),'m15_2023':h(a.m15_2023),'events_2024h1':h(a.events_2024h1),'events_2024h2':h(a.events_2024h2),'m1_2024':h(a.m1_2024),'m5_2024':h(a.m5_2024),'report':h(a.report)}
 assert act==SHA,(act,SHA);return act
def trades23(p):
 d=pd.read_csv(p);s=pd.to_datetime(d.first_timestamp_mt4_server,utc=True);d['t']=pd.DatetimeIndex([hist(x) for x in s]);d=d.sort_values('t').reset_index(drop=True);d['et']=d.t.shift(-1);hi=d.high.shift(1).rolling(96,min_periods=96).max();lo=d.low.shift(1).rolling(96,min_periods=96).min();ok=d.et.dt.hour.isin(range(20));side=pd.Series(0,index=d.index);side[ok&(d.close>hi)&(d.close.shift(1)<=hi.shift(1))]=1;side[ok&(d.close<lo)&(d.close.shift(1)>=lo.shift(1))]=-1
 s=pd.DataFrame({'signal':d.t,'entry':d.et,'side':side,'level':np.where(side.eq(1),hi,lo)});s=s[s.side.isin([1,-1])&s.entry.notna()];s=s[~excl(s.entry)];mp=pd.Series(d.index,index=d.t).to_dict();rows=[]
 for x in s.itertuples(index=False):
  ei=int(mp[x.entry]);xi=ei+32
  if xi>=len(d) or d.t.iloc[xi]>=pd.Timestamp('2024-01-01T00:00:00Z'):continue
  eb=float(d.open.iloc[ei]);ep=eb+SP if x.side==1 else eb;cb=float(d.open.iloc[xi]);xp=cb if x.side==1 else cb+SP;bp=x.side*(xp-ep)/PIP;fold='2023H1' if x.entry<pd.Timestamp('2023-07-01T00:00:00Z') else '2023H2';rows.append(dict(fold=fold,signal=x.signal,entry=x.entry,close=d.t.iloc[xi],side=int(x.side),level=float(x.level),ep=ep,bp=r1(bp),key=f'F05|{z(x.signal)}|{int(x.side)}'))
 o=pd.DataFrame(rows);assert len(o)==730 and o.groupby('fold').size().to_dict()=={'2023H1':367,'2023H2':363};return o
def bars23(p):
 d=pd.read_csv(p);s=pd.to_datetime(d.timestamp_mt4_server,utc=True);d['t']=pd.DatetimeIndex([hist(x) for x in s]);d=d.set_index('t').sort_index();m=d[['open','high','low','close']].resample('5min',closed='left',label='left').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna();m['completion']=m.index+pd.Timedelta(minutes=5);return d,m
def level(x):
 q=dict(re.findall(r'(\w+)=([^;]+)',str(x.detail)));return float(q['current_high'] if int(x.side)==1 else q['current_low'])
def trades24(p,fold):
 e=pd.read_csv(p,encoding='utf-8-sig');o=e[(e.event=='order_opened')&(e.strategy=='F05')].copy();c=e[(e.event=='order_closed')&(e.strategy=='F05')].copy();o['signal']=pd.to_datetime(o.signal_utc,format='%Y.%m.%d %H:%M:%S',utc=True);o['entry']=pd.to_datetime(o.entry_utc,format='%Y.%m.%d %H:%M:%S',utc=True);c['close']=pd.to_datetime(c.utc_time,format='%Y.%m.%d %H:%M:%S',utc=True);x=o.merge(c[['ticket','close','price','gross_pips']],on='ticket',suffixes=('_open','_close'),validate='one_to_one');x['level']=x.apply(level,axis=1);x['fold']=fold;x['key']='F05|'+x.signal.dt.strftime('%Y-%m-%dT%H:%M:%SZ')+'|'+x.side.astype(int).astype(str);x=x.rename(columns={'price_open':'ep','gross_pips_close':'bp'});return x[['fold','signal','entry','close','side','level','ep','bp','key']]
def bars24(p1,p5):
 a=pd.read_csv(p1);b=pd.read_csv(p5)
 for d in (a,b):d['t']=pd.to_datetime(d.time,utc=True);d.set_index('t',inplace=True)
 b['completion']=b.index+pd.Timedelta(minutes=5);return a,b
def row(x,fc,rc,fail,ex,mx,cp):return {'trade_key':x.key,'fold':x.fold,'side':int(x.side),'signal_utc':z(x.signal),'entry_utc':z(x.entry),'baseline_exit_utc':z(x.close),'breakout_level':round(float(x.level),6),'first_m5_completion_utc':z(fc),'reclaim_m1_close_utc':z(rc),'failure_m5_completion_utc':z(fail),'candidate_exit_utc':z(ex),'max_executable_profit_through_trigger_pips':r1(mx),'baseline_pips':r1(x.bp),'candidate_pips':r1(cp),'delta_pips':r1(cp-float(x.bp))}
def ev23(x,m1,m5,same):
 side=int(x.side);ent=x.entry;close=x.close;lev=float(x.level);ep=float(x.ep);st=ent.floor('5min')
 if st not in m5.index:return
 fm=m5.loc[st];fc=st+pd.Timedelta(minutes=5);w=m1[(m1.index>=ent)&((m1.index+pd.Timedelta(minutes=1))<=fc)]
 if w.empty:return
 mx=(w.high.max()-ep)/PIP if side==1 else (ep-(w.low.min()+SP))/PIP;inside=(fm.close<=lev-.02+1e-12) if side==1 else (fm.close+SP>=lev+.02-1e-12)
 if mx>1e-9 or not inside:return
 rc=None
 for t,b in m1[((m1.index+pd.Timedelta(minutes=1))>fc)&((m1.index+pd.Timedelta(minutes=1))<close)].iterrows():
  ct=t+pd.Timedelta(minutes=1);xc=b.close if side==1 else b.close+SP
  if (side==1 and xc>lev+1e-12) or (side==-1 and xc<lev-1e-12):rc=ct;break
 if rc is None:return
 q=m5[m5.completion>=rc] if same else m5[m5.completion>rc];q=q[q.completion<close]
 if q.empty:return
 f=q.iloc[0];fail=f.completion;xc=f.close if side==1 else f.close+SP
 if not ((side==1 and xc<=lev+1e-12) or (side==-1 and xc>=lev-1e-12)):return
 w=m1[(m1.index>=ent)&((m1.index+pd.Timedelta(minutes=1))<=fail)];mx=(w.high.max()-ep)/PIP if side==1 else (ep-(w.low.min()+SP))/PIP
 if mx>1e-9:return
 q=m1[m1.index>=fail]
 if q.empty or q.index[0]>=close:return
 ex=q.index[0];b=q.iloc[0];xp=b.open if side==1 else b.open+SP;return row(x,fc,rc,fail,ex,mx,side*(xp-ep)/PIP)
def ev24(x,m1,m5,same):
 side=int(x.side);ent=x.entry;close=x.close;lev=float(x.level);ep=float(x.ep);st=ent.floor('5min')
 if st not in m5.index:return
 fm=m5.loc[st];fc=st+pd.Timedelta(minutes=5);w=m1[(m1.index>=ent)&((m1.index+pd.Timedelta(minutes=1))<=fc)]
 if w.empty:return
 mx=(w.bid_high.max()-ep)/PIP if side==1 else (ep-w.ask_low.min())/PIP;inside=(fm.bid_close<=lev-.02+1e-12) if side==1 else (fm.ask_close>=lev+.02-1e-12)
 if mx>1e-9 or not inside:return
 rc=None
 for t,b in m1[((m1.index+pd.Timedelta(minutes=1))>fc)&((m1.index+pd.Timedelta(minutes=1))<close)].iterrows():
  ct=t+pd.Timedelta(minutes=1);xc=b.bid_close if side==1 else b.ask_close
  if (side==1 and xc>lev+1e-12) or (side==-1 and xc<lev-1e-12):rc=ct;break
 if rc is None:return
 q=m5[m5.completion>=rc] if same else m5[m5.completion>rc];q=q[q.completion<close]
 if q.empty:return
 f=q.iloc[0];fail=f.completion;xc=f.bid_close if side==1 else f.ask_close
 if not ((side==1 and xc<=lev+1e-12) or (side==-1 and xc>=lev-1e-12)):return
 w=m1[(m1.index>=ent)&((m1.index+pd.Timedelta(minutes=1))<=fail)];mx=(w.bid_high.max()-ep)/PIP if side==1 else (ep-w.ask_low.min())/PIP
 if mx>1e-9:return
 q=m1[m1.index>=fail]
 if q.empty or q.index[0]>=close:return
 ex=q.index[0];b=q.iloc[0];xp=b.bid_open if side==1 else b.ask_open;return row(x,fc,rc,fail,ex,mx,side*(xp-ep)/PIP)
def evaluate(t23,b23,t24,b24,same):
 rows=[]
 for _,x in t23.iterrows():
  y=ev23(x,*b23,same)
  if y:rows.append(y)
 for _,x in t24.iterrows():
  y=ev24(x,*b24,same)
  if y:rows.append(y)
 return pd.DataFrame(rows).sort_values(['fold','entry_utc']).reset_index(drop=True)
def summary(d):
 f={}
 for x in FOLDS:
  g=d[d.fold==x];f[x]={'stopped':len(g),'delta_pips':r1(g.delta_pips.sum()),'long_delta_pips':r1(g[g.side==1].delta_pips.sum()),'short_delta_pips':r1(g[g.side==-1].delta_pips.sum())}
 return {'stopped_trades':len(d),'total_delta_pips':r1(d.delta_pips.sum()),'long_delta_pips':r1(d[d.side==1].delta_pips.sum()),'short_delta_pips':r1(d[d.side==-1].delta_pips.sum()),'folds':f}
def save(d,p):d.to_csv(p,index=False,lineterminator='\n',float_format='%.6f')
def main():
 p=argparse.ArgumentParser();
 for n in ['m1_2023','m15_2023','events_2024h1','events_2024h2','m1_2024','m5_2024','report','protocol']:p.add_argument('--'+n.replace('_','-'),dest=n,type=Path,required=True)
 p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--preflight-only',action='store_true');a=p.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True);protocol(a.protocol);src=source(a);test={'status':'PASS','reclaim':'2023-06-08T16:35:00Z','legacy_m5':'2023-06-08T16:35:00Z','direct_m5':'2023-06-08T16:40:00Z','same_timestamp_forbidden':True};pre={'schema_version':'f05_failed_reclaim_preflight_v1','status':'PASS','candidate_count':2,'binding_candidate_count':1,'source_sha256':src,'protocol_sha256':h(a.protocol),'evaluator_sha256':h(Path(__file__)),'timing_unit_test':test,'outcomes_computed':False,'portfolio_replay_computed':False,'2025_accessed':False,'mt4_accessed':False,'notion_task_dependency':False};(a.output_dir/'f05_failed_reclaim_preflight_v1.json').write_text(json.dumps(pre,indent=2,sort_keys=True)+'\n')
 if a.preflight_only:print(json.dumps(pre,indent=2));return 0
 t23=trades23(a.m15_2023);b23=bars23(a.m1_2023);t24=pd.concat([trades24(a.events_2024h1,'2024H1'),trades24(a.events_2024h2,'2024H2')],ignore_index=True);assert t24.groupby('fold').size().to_dict()=={'2024H1':331,'2024H2':391};b24=bars24(a.m1_2024,a.m5_2024);old=evaluate(t23,b23,t24,b24,True);new=evaluate(t23,b23,t24,b24,False);so=summary(old);sn=summary(new);errs=[]
 for k,v in [('stopped_trades',EXP['n']),('total_delta_pips',EXP['total']),('long_delta_pips',EXP['long']),('short_delta_pips',EXP['short'])]:
  if not math.isclose(float(so[k]),float(v),abs_tol=.05):errs.append(f'{k}:{so[k]}!={v}')
 for f,(n,v) in EXP['folds'].items():
  if so['folds'][f]['stopped']!=n or not math.isclose(so['folds'][f]['delta_pips'],v,abs_tol=.05):errs.append(f'{f}:{so["folds"][f]}!=({n},{v})')
 ko=set(old.trade_key);kn=set(new.trade_key);diff=new[new.trade_key.isin(kn-ko)].copy();save(old,a.output_dir/'f05_failed_reclaim_exploration_reproduction_ledger_v1.csv');save(new,a.output_dir/'f05_failed_reclaim_direct_spec_ledger_v1.csv');save(diff,a.output_dir/'f05_failed_reclaim_identity_diff_v1.csv');res={'schema_version':'f05_failed_reclaim_technical_validation_result_v1','status':'TECHNICAL_MISMATCH_STOP','decision':'STOP_BEFORE_PORTFOLIO_REPLAY_AND_SCIENTIFIC_GATE_INTERPRETATION','exploration_reproduction':{'status':'PASS' if not errs else 'FAIL','summary':so,'errors':errs},'direct_instruction_semantics':{'same_timestamp_m5_forbidden':True,'summary':sn},'identity_comparison':{'match':ko==kn,'exploration_trade_count':len(ko),'direct_trade_count':len(kn),'direct_only_trade_keys':sorted(kn-ko),'exploration_only_trade_keys':sorted(ko-kn)},'blockers':[{'code':'DIRECT_SPEC_VS_EXPLORATION_IDENTITY_MISMATCH','cause':'Exploration accepted an M5 completion equal to reclaim M1 close; direct instruction forbids it.','direct_only_trade_keys':sorted(kn-ko)},{'code':'ORIGINAL_BUNDLE_RAW_BYTES_UNAVAILABLE','filename':'F05_structural_SL_event_sequence_bundle_v1.zip','expected_sha256':'463850652d08f7c3d6b170a345ba92a1f7228c9efb24eb0f89f90b13a59b686d','substitute_claimed':False}],'boundaries':{'scientific_outcomes_interpreted':False,'historical_gates_evaluated':False,'portfolio_replay_computed':False,'non_binding_sensitivity_computed':False,'2024_tick_exact_candidate_ordering_completed':False,'mt4_accessed':False,'2025H1_accessed':False,'2025H2_accessed':False,'candidate_definition_changed':False,'new_hypothesis_created':False,'notion_used_as_task_source':False}};(a.output_dir/'f05_failed_reclaim_technical_validation_result_v1.json').write_text(json.dumps(res,indent=2,sort_keys=True)+'\n');receipt={'schema_version':'f05_failed_reclaim_execution_identity_receipt_v1','status':res['status'],'protocol_sha256':h(a.protocol),'evaluator_sha256':h(Path(__file__)),'source_sha256':src,'portfolio_replay_computed':False,'mt4_accessed':False,'2025_accessed':False};(a.output_dir/'f05_failed_reclaim_execution_identity_receipt_v1.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');files={x.name:h(x) for x in a.output_dir.iterdir() if x.is_file()};(a.output_dir/'f05_failed_reclaim_output_manifest_v1.json').write_text(json.dumps({'schema_version':'f05_failed_reclaim_output_manifest_v1','status':res['status'],'output_sha256':files},indent=2,sort_keys=True)+'\n');print(json.dumps(res,indent=2));return 2
if __name__=='__main__':raise SystemExit(main())
