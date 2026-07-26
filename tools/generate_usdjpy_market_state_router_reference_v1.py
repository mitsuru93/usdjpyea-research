#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
from usdjpy_native_htf_state_data_v1 import load_m15_2023, load_m15_2024, aggregate_exact, add_state

EXPECTED_TRADE_SHA='98c9c8cf57c62c23a94aa38efa6ee257e823dd0b68c413615197a48be00b08ca'

def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''): h.update(c)
 return h.hexdigest()

def main()->None:
 ap=argparse.ArgumentParser();ap.add_argument('--trades',type=Path,required=True);ap.add_argument('--m15-2023',type=Path,required=True);ap.add_argument('--m15-2024',type=Path,required=True);ap.add_argument('--out-dir',type=Path,required=True);ap.add_argument('--research-sha',default='');ap.add_argument('--run-id',default='');a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
 assert sha256(a.trades)==EXPECTED_TRADE_SHA
 t=pd.read_csv(a.trades);t['entry_utc']=pd.to_datetime(t.entry_utc,utc=True);t['_row']=np.arange(len(t));assert len(t)==1882
 m=pd.concat([load_m15_2023(a.m15_2023),load_m15_2024(a.m15_2024)],ignore_index=True).sort_values('logical_utc').reset_index(drop=True)
 h4=add_state(aggregate_exact(m,'4h',16),6,24,'h4')
 left=t[['_row','entry_utc']].sort_values('entry_utc');right=h4[['information_utc','bucket_server','close','h4_fast','h4_slow','h4_state']].sort_values('information_utc')
 joined=pd.merge_asof(left,right,left_on='entry_utc',right_on='information_utc',direction='backward',allow_exact_matches=True).set_index('_row').reindex(t._row).reset_index(drop=True)
 out=t[['fold','strategy','side','entry_utc','realized_pl_jpy']].copy()
 out['h4_information_utc']=joined.information_utc.astype('string');out['h4_bucket_server']=joined.bucket_server.astype('string');out['h4_close']=joined.close;out['h4_fast_ema']=joined.h4_fast;out['h4_slow_ema']=joined.h4_slow;out['h4_state']=joined.h4_state.fillna(0).astype(int);out['entry_allowed']=out.h4_state.eq(out.side.astype(int));out['blocked_delta_jpy']=np.where(out.entry_allowed,0,-out.realized_pl_jpy)
 assert int((~out.entry_allowed).sum())==671
 out.to_csv(a.out_dir/'usdjpy_market_state_router_reference_trade_ledger_v1.csv.gz',index=False,compression='gzip',float_format='%.12f')
 h4[['bucket_server','information_utc','close','h4_fast','h4_slow','h4_state']].to_csv(a.out_dir/'usdjpy_market_state_router_reference_h4_state_v1.csv.gz',index=False,compression='gzip',float_format='%.12f')
 result={'status':'PASS_REFERENCE_FREEZE','candidate_id':'S3_H4_ALIGNED','population_trades':len(out),'blocked_trades':int((~out.entry_allowed).sum()),'net_delta_jpy':float(out.blocked_delta_jpy.sum()),'reference_trade_sha256':sha256(a.out_dir/'usdjpy_market_state_router_reference_trade_ledger_v1.csv.gz'),'reference_h4_sha256':sha256(a.out_dir/'usdjpy_market_state_router_reference_h4_state_v1.csv.gz'),'2025_accessed':False,'mt4_accessed':False,'research_sha':a.research_sha,'run_id':a.run_id}
 (a.out_dir/'reference_receipt.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n');print(json.dumps(result,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
