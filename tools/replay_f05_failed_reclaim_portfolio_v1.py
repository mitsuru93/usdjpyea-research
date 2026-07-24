#!/usr/bin/env python3
"""Portfolio replay adapter for F05 failed reclaim.

This adapter is intentionally locked. It may consume a technical validation result only
when exact exploration reproduction, direct-spec changed-trade identity, and original
bundle identity all pass. A technical mismatch must never be converted into a portfolio
result by this file.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path

UNLOCK_STATUS = "PASS_REPRODUCTION_AND_DIRECT_IDENTITY"


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--technical-result',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    a=p.parse_args()
    result=json.loads(a.technical_result.read_text(encoding='utf-8'))
    a.output_dir.mkdir(parents=True,exist_ok=True)
    if result.get('status') != UNLOCK_STATUS:
        receipt={
            'schema_version':'f05_failed_reclaim_portfolio_replay_guard_receipt_v1',
            'status':'LOCKED_TECHNICAL_PREREQUISITE_NOT_MET',
            'required_status':UNLOCK_STATUS,
            'observed_status':result.get('status'),
            'portfolio_replay_computed':False,
            'historical_gates_evaluated':False,
            'mt4_accessed':False,
            '2025_accessed':False
        }
        (a.output_dir/'f05_failed_reclaim_portfolio_replay_guard_receipt_v1.json').write_text(
            json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        print(json.dumps(receipt,indent=2,sort_keys=True))
        return 3
    raise RuntimeError('Replay implementation remains locked until the exact prerequisite state exists on main.')


if __name__=='__main__':
    raise SystemExit(main())
