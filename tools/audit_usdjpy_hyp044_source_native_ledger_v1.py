#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any

def f(v:Any)->float:
    try:return float(v)
    except:return 0.0

def main()->None:
    ap=argparse.ArgumentParser();ap.add_argument('--ledger',type=Path,required=True);ap.add_argument('--result',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    with args.ledger.open(encoding='utf-8-sig',newline='') as h:rows=list(csv.DictReader(h))
    result=json.loads(args.result.read_text())
    variants=defaultdict(list)
    for r in rows:variants[r['variant_id']].append(r)
    vm={}
    for vid,group in variants.items():
        ids=[r['trade_id'] for r in group]
        vm[vid]={'rows':len(group),'net_pnl_jpy':sum(f(r['pnl_jpy']) for r in group),'net_baseline_pnl_jpy':sum(f(r['baseline_pnl_jpy']) for r in group),'duplicate_trade_ids':sum(c-1 for c in Counter(ids).values() if c>1),'blank_pnl':sum(not str(r['pnl_jpy']).strip() for r in group),'modified':sum(str(r['modified']).lower() in {'1','true'} for r in group),'strategies':dict(Counter(r['strategy'] for r in group))}
    combos={
      'P0_B02_BASELINE_F05_BASELINE':['B02_BASELINE','F05_BASELINE'],
      'P1_B02_BASELINE_F05_C2':['B02_BASELINE','F05_C2'],
      'P2_B02_C3_F05_BASELINE':['B02_C3','F05_BASELINE'],
      'P3_B02_C3_F05_C2':['B02_C3','F05_C2'],
      'P4_B02_C3_F05_C2_SP39':['B02_C3','F05_C2','SP39_UNCHANGED']}
    cm={}
    for pid,vids in combos.items():
        ledger_net=sum(vm[v]['net_pnl_jpy'] for v in vids);reported=result['portfolio_metrics'][pid]['net_jpy'];cm[pid]={'variant_ids':vids,'ledger_net_jpy':ledger_net,'source_result_net_jpy':reported,'difference_jpy':ledger_net-reported,'pass':abs(ledger_net-reported)<0.01}
    payload={'schema_version':'usdjpy_hyp044_source_native_ledger_tieout_v1','status':'PASS' if all(x['pass'] for x in cm.values()) else 'FAIL_LEDGER_RESULT_DIVERGENCE','variants':vm,'combinations':cm,'row_count':len(rows),'2025H2_accessed':False}
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
    print(json.dumps(payload,indent=2))
if __name__=='__main__':main()
