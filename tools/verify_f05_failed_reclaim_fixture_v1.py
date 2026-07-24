#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
import pandas as pd
FOLDS=['2023H1','2023H2','2024H1','2024H2']
SHA={'exploration':'75312aba2ffd92c45ec52023b49ba906b6e216730c61f932927c8c239c5da837','direct':'41f6bcda5515a40e283fde65e55cf8a1010ef26d31930e6fe8717238bf5ff6a9'}
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def s(d):
 f={}
 for x in FOLDS:
  g=d[d.fold==x];f[x]={'stopped':len(g),'delta_pips':round(float(g.delta_pips.sum()),1),'long_delta_pips':round(float(g[g.side==1].delta_pips.sum()),1),'short_delta_pips':round(float(g[g.side==-1].delta_pips.sum()),1)}
 return {'stopped_trades':len(d),'total_delta_pips':round(float(d.delta_pips.sum()),1),'long_delta_pips':round(float(d[d.side==1].delta_pips.sum()),1),'short_delta_pips':round(float(d[d.side==-1].delta_pips.sum()),1),'folds':f}
def main():
 p=argparse.ArgumentParser();p.add_argument('--exploration',type=Path,required=True);p.add_argument('--direct',type=Path,required=True);p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--binding',action='store_true');a=p.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True)
 actual={'exploration':h(a.exploration),'direct':h(a.direct)}
 assert actual==SHA,(actual,SHA)
 actual['protocol']=h(a.protocol)
 q=json.loads(a.protocol.read_text());assert q['candidates']['binding']['candidate_id']=='F05_FAILED_RECLAIM_BASIC_V1' and q['candidates']['non_binding_sensitivity']['binding'] is False and q['candidates']['binding']['reclaim_failure']['same_timestamp_m5_forbidden'] is True
 e=pd.read_csv(a.exploration);d=pd.read_csv(a.direct);se=s(e);sd=s(d);ke=set(e.trade_key);kd=set(d.trade_key);extra=sorted(kd-ke);missing=sorted(ke-kd)
 assert se['stopped_trades']==14 and math.isclose(se['total_delta_pips'],202.1,abs_tol=.05) and math.isclose(se['long_delta_pips'],65.2,abs_tol=.05) and math.isclose(se['short_delta_pips'],136.9,abs_tol=.05)
 assert sd['stopped_trades']==15 and math.isclose(sd['total_delta_pips'],200.6,abs_tol=.05)
 assert extra==['F05|2023-06-08T15:45:00Z|-1'] and not missing
 x=d[d.trade_key==extra[0]].iloc[0];assert x.reclaim_m1_close_utc=='2023-06-08T16:35:00Z' and x.failure_m5_completion_utc=='2023-06-08T16:40:00Z' and math.isclose(float(x.delta_pips),-1.5,abs_tol=.01)
 pre={'schema_version':'f05_failed_reclaim_fixture_preflight_v1','status':'PASS','fixture_sha256':actual,'candidate_count':2,'binding_candidate_count':1,'outcomes_computed':False,'portfolio_replay_computed':False,'mt4_accessed':False,'2025_accessed':False}
 (a.output_dir/'f05_failed_reclaim_fixture_preflight_v1.json').write_text(json.dumps(pre,indent=2,sort_keys=True)+'\n')
 if not a.binding:print(json.dumps(pre,indent=2));return 0
 result={'schema_version':'f05_failed_reclaim_binding_technical_fixture_result_v1','status':'TECHNICAL_MISMATCH_STOP','decision':'STOP_BEFORE_PORTFOLIO_REPLAY_AND_SCIENTIFIC_GATE_INTERPRETATION','exploration_reproduction':{'status':'PASS','summary':se},'direct_instruction_semantics':{'same_timestamp_m5_forbidden':True,'summary':sd},'identity_comparison':{'match':False,'direct_only_trade_keys':extra,'exploration_only_trade_keys':missing},'root_cause':{'trade_key':extra[0],'reclaim_m1_close_utc':x.reclaim_m1_close_utc,'direct_failure_m5_completion_utc':x.failure_m5_completion_utc,'direct_delta_pips':float(x.delta_pips),'explanation':'Exploration accepted an M5 completion equal to reclaim M1 close; direct instruction forbids it and selects the next completed M5.'},'blockers':['DIRECT_SPEC_VS_EXPLORATION_IDENTITY_MISMATCH','ORIGINAL_BUNDLE_RAW_BYTES_UNAVAILABLE'],'boundaries':{'scientific_outcomes_interpreted':False,'historical_gates_evaluated':False,'portfolio_replay_computed':False,'non_binding_sensitivity_computed':False,'mt4_accessed':False,'2025H1_accessed':False,'2025H2_accessed':False,'new_hypothesis_created':False,'notion_used_as_task_source':False}}
 (a.output_dir/'f05_failed_reclaim_binding_technical_fixture_result_v1.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');receipt={'schema_version':'f05_failed_reclaim_binding_execution_receipt_v1','status':result['status'],'verifier_sha256':h(Path(__file__)),'fixture_sha256':actual,'event_name':'workflow_dispatch','portfolio_replay_computed':False,'mt4_accessed':False,'2025_accessed':False};(a.output_dir/'f05_failed_reclaim_binding_execution_receipt_v1.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps(result,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
