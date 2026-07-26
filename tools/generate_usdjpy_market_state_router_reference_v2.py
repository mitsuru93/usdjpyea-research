#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
from usdjpy_native_htf_state_data_v1 import load_m15_2023, load_m15_2024, aggregate_exact, add_state

EXPECTED_TRADE_SHA='98c9c8cf57c62c23a94aa38efa6ee257e823dd0b68c413615197a48be00b08ca'
ALLOW='MSR_S3_H4_ALIGNED_ALLOW'
OPPOSED='MSR_S3_H4_STATE_OPPOSED'
NEUTRAL='MSR_S3_H4_STATE_NEUTRAL'
MISSING='MSR_S3_H4_STATE_MISSING'

def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''): h.update(c)
 return h.hexdigest()

def iso(s:pd.Series)->pd.Series:
 return pd.to_datetime(s,utc=True).dt.strftime('%Y-%m-%dT%H:%M:%SZ')

def main()->None:
 ap=argparse.ArgumentParser();ap.add_argument('--trades',type=Path,required=True);ap.add_argument('--m15-2023',type=Path,required=True);ap.add_argument('--m15-2024',type=Path,required=True);ap.add_argument('--contract',type=Path,required=True);ap.add_argument('--out-dir',type=Path,required=True);ap.add_argument('--research-sha',default='');ap.add_argument('--run-id',default='');a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
 assert sha256(a.trades)==EXPECTED_TRADE_SHA
 contract=json.loads(a.contract.read_text())
 assert contract['candidate_id']=='S3_H4_ALIGNED' and contract['indicator_contract']['fast_span']==6 and contract['indicator_contract']['slow_span']==24
 t=pd.read_csv(a.trades);required={'fold','strategy','signal_utc','entry_utc','side','realized_pl_jpy'};assert required.issubset(t.columns),sorted(set(required)-set(t.columns))
 t['signal_utc']=pd.to_datetime(t.signal_utc,utc=True);t['entry_utc']=pd.to_datetime(t.entry_utc,utc=True);t['_row']=np.arange(len(t));assert len(t)==1882
 t['trade_id']=t.fold.astype(str)+'|'+t.strategy.astype(str)+'|'+iso(t.entry_utc)+'|'+t.side.astype(int).astype(str)
 assert t.trade_id.nunique()==1882 and int(t.trade_id.duplicated().sum())==0
 m=pd.concat([load_m15_2023(a.m15_2023),load_m15_2024(a.m15_2024)],ignore_index=True).sort_values('logical_utc').reset_index(drop=True)
 assert not m.logical_utc.duplicated().any()
 h4=add_state(aggregate_exact(m,'4h',16),6,24,'h4').sort_values('information_utc').reset_index(drop=True)
 left=t[['_row','entry_utc']].sort_values('entry_utc');right=h4[['information_utc','bucket_server','close','h4_fast','h4_slow','h4_state']]
 joined=pd.merge_asof(left,right,left_on='entry_utc',right_on='information_utc',direction='backward',allow_exact_matches=True).set_index('_row').reindex(t._row).reset_index(drop=True)
 out=t[['trade_id','fold','strategy','side','signal_utc','entry_utc','realized_pl_jpy']].copy()
 out['referenced_h4_slot']=joined.bucket_server
 out['h4_information_utc']=joined.information_utc
 out['h4_close']=joined.close
 out['h4_fast_ema']=joined.h4_fast
 out['h4_slow_ema']=joined.h4_slow
 out['h4_state']=joined.h4_state.fillna(0).astype(int)
 out['permission_result']=out.h4_state.eq(out.side.astype(int))
 out['blocked']=~out.permission_result
 out['expected_reason_code']=np.where(out.permission_result,ALLOW,np.where(joined.information_utc.isna(),MISSING,np.where(out.h4_state.eq(0),NEUTRAL,OPPOSED)))
 out['blocked_delta_jpy']=np.where(out.blocked,-out.realized_pl_jpy,0)
 out['future_information_use']=joined.information_utc.gt(out.entry_utc).fillna(False)
 assert int(out.blocked.sum())==671
 assert int((~out.blocked).sum())==1211
 assert int(out.trade_id.duplicated().sum())==0
 assert int(joined.information_utc.isna().sum())==0
 assert int(out.future_information_use.sum())==0
 trade_path=a.out_dir/'usdjpy_market_state_router_reference_trade_ledger_v2.csv.gz'
 h4_path=a.out_dir/'usdjpy_market_state_router_reference_h4_state_v2.csv.gz'
 cols=['trade_id','fold','strategy','side','signal_utc','entry_utc','referenced_h4_slot','h4_information_utc','h4_close','h4_fast_ema','h4_slow_ema','h4_state','permission_result','blocked','expected_reason_code','realized_pl_jpy','blocked_delta_jpy','future_information_use']
 out[cols].to_csv(trade_path,index=False,compression='gzip',float_format='%.12f',date_format='%Y-%m-%dT%H:%M:%SZ')
 h4out=h4[['bucket_server','information_utc','close','h4_fast','h4_slow','h4_state']].copy();h4out.columns=['referenced_h4_slot','h4_information_utc','h4_close','h4_fast_ema','h4_slow_ema','h4_state'];h4out.to_csv(h4_path,index=False,compression='gzip',float_format='%.12f',date_format='%Y-%m-%dT%H:%M:%SZ')
 reason_counts={str(k):int(v) for k,v in out.expected_reason_code.value_counts().sort_index().items()}
 result={'schema_version':'usdjpy_market_state_router_reference_receipt_v2','status':'PASS_COMPLETE_REFERENCE_FREEZE','candidate_id':'S3_H4_ALIGNED','population_trades':len(out),'blocked_trades':int(out.blocked.sum()),'allowed_trades':int((~out.blocked).sum()),'duplicate_trade_id':int(out.trade_id.duplicated().sum()),'missing_state':int(joined.information_utc.isna().sum()),'future_information_use':int(out.future_information_use.sum()),'net_delta_jpy':float(out.blocked_delta_jpy.sum()),'reason_counts':reason_counts,'reference_trade_sha256':sha256(trade_path),'reference_h4_sha256':sha256(h4_path),'contract_sha256':sha256(a.contract),'2025_accessed':False,'mt4_accessed':False,'research_sha':a.research_sha,'run_id':a.run_id}
 (a.out_dir/'reference_receipt_v2.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n');print(json.dumps(result,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
