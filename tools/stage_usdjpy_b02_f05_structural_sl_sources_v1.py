#!/usr/bin/env python3
"""Outcome-free source staging for B02/F05 all-loss structural-SL analysis.

This recovery stage intentionally does not consume the truncated Stage 1 archive.
It verifies and transfers the immutable 2024 M1 Release asset, while recording the
known Stage 1 archive defect for independent trade-ledger rematerialization.
"""
from __future__ import annotations
import argparse, hashlib, json, shutil
from pathlib import Path
import pandas as pd

EXPECTED_M1_2024_SHA = "f9f56be2daa39f07dc39cec197306fb87821ead01e4a640a73f17715bf27dde0"
CORRUPT_STAGE1_ARCHIVE_SHA = "ae450cd712c8e1533081b0bd609f736c2216e3e4a9cfaece8d19ac7ffd5addd8"
EXPECTED_STAGE1_LEDGER_SHA = "c4025d59eef9358fce9df70d50972159d52ff8aa02ebaa851e7fa0273082b82f"
EXPECTED_COLUMNS = [
    "time",
    "bid_open", "bid_high", "bid_low", "bid_close",
    "ask_open", "ask_high", "ask_low", "ask_close",
    "mid_open", "mid_high", "mid_low", "mid_close",
    "tick_count", "spread_open", "spread_mean", "spread_max",
]

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--m1-2024',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--research-commit',required=True)
    p.add_argument('--workflow-run-id',required=True)
    p.add_argument('--workflow-run-attempt',required=True)
    a=p.parse_args(); a.output_dir.mkdir(parents=True,exist_ok=True)
    actual=sha(a.m1_2024)
    if actual!=EXPECTED_M1_2024_SHA: raise SystemExit(f'2024 M1 SHA mismatch: {actual}')
    m1=pd.read_csv(a.m1_2024)
    if list(m1.columns)!=EXPECTED_COLUMNS: raise SystemExit(f'2024 M1 columns={list(m1.columns)}')
    if len(m1)!=373383: raise SystemExit(f'2024 M1 rows={len(m1)}')
    tcol='time'; mts=pd.to_datetime(m1[tcol],utc=True)
    if mts.duplicated().any() or not mts.is_monotonic_increasing: raise SystemExit('2024 M1 time integrity')
    target=a.output_dir/a.m1_2024.name; shutil.copy2(a.m1_2024,target)
    result={
      'schema_version':'usdjpy_b02_f05_structural_sl_source_recovery_v1',
      'status':'PASS_SOURCE_ONLY_NO_OUTCOMES',
      'outcomes_computed':False,
      'research_commit':a.research_commit,
      'workflow_run_id':int(a.workflow_run_id),
      'workflow_run_attempt':int(a.workflow_run_attempt),
      'm1_2024':{
        'release_tag':'usdjpy-2024-derived-bars-v1','sha256':actual,'rows':len(m1),
        'columns':m1.columns.tolist(),'timestamp_column':tcol,
        'first':mts.iloc[0].isoformat(),'last':mts.iloc[-1].isoformat(),
      },
      'stage1_archive_defect':{
        'archive_path':'.stage2_lifecycle_abc_package_v1.tar.gz',
        'runner_observed_sha256':CORRUPT_STAGE1_ARCHIVE_SHA,
        'expected_ledger_sha256':EXPECTED_STAGE1_LEDGER_SHA,
        'classification':'TECHNICAL_INCOMPLETE_NO_OUTCOMES',
        'used_for_this_stage':False,
        'recovery':'rematerialize all 1,882 trade identities independently from accepted 2023 Atlas/baseline and 2024 H1/H2 event-audit authorities',
      },
      'periods_accessed':['2024H1','2024H2'],
      'periods_not_accessed':['2025H1','2025H2'],
      'mt4_accessed':False,
    }
    (a.output_dir/'source_recovery_result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    files=[]
    for f in sorted(a.output_dir.iterdir()):
      if f.is_file() and f.name!='output_manifest.json': files.append({'name':f.name,'bytes':f.stat().st_size,'sha256':sha(f)})
    (a.output_dir/'output_manifest.json').write_text(json.dumps({'schema_version':'usdjpy_b02_f05_structural_sl_source_recovery_manifest_v1','files':files},indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'PASS_SOURCE_ONLY_NO_OUTCOMES','files':len(files),'m1_rows':len(m1)}))
    return 0
if __name__=='__main__': raise SystemExit(main())
