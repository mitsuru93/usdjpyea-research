#!/usr/bin/env python3
"""Pre-outcome native H1/H4 construction audit; no signals or P/L."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import pandas as pd

def file_sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(1<<20),b''):h.update(x)
 return h.hexdigest()
def nth(y,m,n,h):
 d=datetime(y,m,1,h,tzinfo=timezone.utc);return pd.Timestamp(d+timedelta(days=(6-d.weekday())%7+7*(n-1)))
def dst(t):return nth(t.year,3,2,7)<=t<nth(t.year,11,1,6)
def s2u(s):
 w=s-pd.Timedelta(hours=2);return s-pd.Timedelta(hours=3) if dst(w) else w
def u2s(u):return u+pd.Timedelta(hours=3 if dst(u) else 2)
def load23(p):
 d=pd.read_csv(p);true=pd.to_datetime(d.timestamp_utc,utc=True);first=pd.to_datetime(d.first_timestamp_mt4_server,utc=True);accepted=pd.DatetimeIndex([s2u(x) for x in first]);server=first.dt.floor('15min');logical=pd.DatetimeIndex([s2u(x) for x in server])
 f=pd.DataFrame({'utc':logical,'server':server,'o':d.open,'h':d.high,'l':d.low,'c':d.close,'inc':d.incomplete_source_count.astype(bool)}).sort_values('server').reset_index(drop=True)
 ident={'rows':len(f),'accepted_first_tick_shifted_rows':int((accepted!=pd.DatetimeIndex(true)).sum()),'logical_bucket_shifted_rows':int((logical!=pd.DatetimeIndex(true)).sum()),'logical_vs_accepted_first_tick_different_rows':int((logical!=accepted).sum()),'maximum_first_tick_offset_minutes':float(np.max(np.abs((accepted-logical).total_seconds()/60))),'logical_utc_duplicates':int(f.utc.duplicated().sum()),'logical_server_duplicates':int(f.server.duplicated().sum()),'logical_server_monotonic':bool(f.server.is_monotonic_increasing),'incomplete_m15_rows':int(f.inc.sum())}
 return f,ident
def load24(p):
 d=pd.read_csv(p,compression='gzip');utc=pd.to_datetime(d.timestamp_utc,utc=True);server=pd.DatetimeIndex([u2s(x) for x in utc]);rt=pd.DatetimeIndex([s2u(x) for x in server]);f=pd.DataFrame({'utc':utc,'server':server,'o':d.mid_open,'h':d.mid_high,'l':d.mid_low,'c':d.mid_close,'inc':False}).sort_values('server').reset_index(drop=True)
 return f,{'rows':len(f),'utc_to_server_to_utc_mismatches':int((rt!=pd.DatetimeIndex(utc)).sum()),'logical_utc_duplicates':int(f.utc.duplicated().sum()),'logical_server_duplicates':int(f.server.duplicated().sum()),'logical_server_monotonic':bool(f.server.is_monotonic_increasing),'server_offset_hours':sorted({int((s-u).total_seconds()/3600) for s,u in zip(server,utc)})}
def aggregate(f,label,n,freq):
 b=f.server.dt.floor(freq);w=f.assign(bucket=b);q=w.groupby('bucket',sort=True).agg(constituent_m15=('server','size'),first=('server','min'),last=('server','max'),open=('o','first'),high=('h','max'),low=('l','min'),close=('c','last'),incomplete_constituent_m15=('inc','sum'))
 q['exact']=[set(w.loc[b==k,'server'])==set(pd.date_range(k,periods=n,freq='15min')) for k in q.index];q['timeframe']=label;q['bucket_close_server']=q.index+pd.tseries.frequencies.to_offset(freq);q['information_utc']=[s2u(x) for x in q.bucket_close_server]
 p=q[~q.exact];summary={'timeframe':label,'expected_m15_slots':n,'nonempty_buckets':len(q),'exact_slot_buckets':int(q.exact.sum()),'partial_buckets':int((~q.exact).sum()),'exact_buckets_with_incomplete_source_m15':int((q.exact&(q.incomplete_constituent_m15>0)).sum()),'partial_constituent_count_distribution':json.dumps({str(k):int(v) for k,v in p.constituent_m15.value_counts().sort_index().items()},sort_keys=True),'information_time_monotonic':bool(q.information_utc.is_monotonic_increasing),'information_time_duplicates':int(q.information_utc.duplicated().sum())}
 return q.reset_index(),summary
def main():
 a=argparse.ArgumentParser();a.add_argument('--m15-2023',type=Path,required=True);a.add_argument('--m15-2024',type=Path,required=True);a.add_argument('--output-dir',type=Path,required=True);x=a.parse_args();x.output_dir.mkdir(parents=True,exist_ok=True)
 f23,i23=load23(x.m15_2023);f24,i24=load24(x.m15_2024);assert i23['accepted_first_tick_shifted_rows']==1543 and not i23['logical_server_duplicates'];assert not i24['utc_to_server_to_utc_mismatches']
 rows=[];partials=[];agg={}
 for year,f in [(2023,f23),(2024,f24)]:
  for tf,n,freq in [('H1',4,'1h'),('H4',16,'4h')]:
   q,s=aggregate(f,tf,n,freq);s['year']=year;rows.append(s);agg[f'{year}_{tf}']=s;p=q[~q.exact].copy();p.insert(0,'year',year);partials.append(p)
 sp=x.output_dir/'usdjpy_native_htf_construction_summary_v1.csv';pp=x.output_dir/'usdjpy_native_htf_partial_bucket_inventory_v1.csv';pd.DataFrame(rows).to_csv(sp,index=False,lineterminator='\n');pd.concat(partials,ignore_index=True).to_csv(pp,index=False,lineterminator='\n')
 result={'schema_version':'usdjpy_native_htf_construction_feasibility_result_v1','status':'PASS_DETERMINISTIC_NATIVE_H1_H4_CONSTRUCTION','decision':'USE_LOGICAL_MT4_SERVER_M15_BUCKETS_NOT_ACCEPTED_FIRST_TICK_DISPLAY_TIMESTAMPS','source_identity':{'2023_m15_sha256':file_sha(x.m15_2023),'2024_m15_sha256':file_sha(x.m15_2024)},'2023_identity':i23,'2024_identity':i24,'aggregation':agg,'contract':{'2023_membership_key':'floor(first_timestamp_mt4_server, 15 minutes)','2024_membership_key':'historical UTC converted to MT4 server UTC+2 winter / UTC+3 US-DST','H1_bucket':'floor logical MT4 server timestamp to one hour','H4_bucket':'floor logical MT4 server timestamp to four hours','OHLC':'first open, maximum high, minimum low, last close','complete_bar_information_time':'server bucket close converted by historical ServerToUtc','state_update_eligibility':'only exact constituent-slot buckets; partial buckets are inventoried and do not update state','execution_time':'first accepted M15 open at or after completed higher-timeframe information time','lookahead':False,'historical_2024_mutated':False},'interpretation':['Accepted 2023 first-tick timestamps preserve the binding 1,543-shift identity but 123 bars are not logical 15-minute boundaries.','Higher-timeframe membership therefore uses source server bucket boundaries while accepted first-tick timestamps remain unchanged for historical M15 identity.','Partial market-open, market-close and holiday buckets are excluded rather than imputed.'],'boundaries':{'strategy_signal_generated':False,'strategy_PL_calculated':False,'parameter_selected_from_outcomes':False,'MT4_accessed':False,'2025_accessed':False,'live_orders':False},'output_sha256':{sp.name:file_sha(sp),pp.name:file_sha(pp)}}
 rp=x.output_dir/'usdjpy_native_htf_construction_feasibility_result_v1.json';rp.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
