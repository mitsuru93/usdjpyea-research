#!/usr/bin/env python3
"""Outcome-free source staging for B02/F05 all-loss structural-SL analysis."""
from __future__ import annotations
import argparse, hashlib, json, shutil
from pathlib import Path
import pandas as pd

EXPECTED_STAGE1_SHA = "c4025d59eef9358fce9df70d50972159d52ff8aa02ebaa851e7fa0273082b82f"
EXPECTED_M1_2024_SHA = "f9f56be2daa39f07dc39cec197306fb87821ead01e4a640a73f17715bf27dde0"
EXPECTED_COUNTS = {
    "2023H1|B02":121,"2023H1|F05":367,"2023H2|B02":109,"2023H2|F05":363,
    "2024H1|B02":97,"2024H1|F05":331,"2024H2|B02":102,"2024H2|F05":392,
}

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--stage1-ledger',type=Path,required=True)
    p.add_argument('--m1-2024',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--research-commit',required=True)
    a=p.parse_args(); a.output_dir.mkdir(parents=True,exist_ok=True)
    if sha(a.stage1_ledger)!=EXPECTED_STAGE1_SHA: raise SystemExit('stage1 SHA mismatch')
    if sha(a.m1_2024)!=EXPECTED_M1_2024_SHA: raise SystemExit('2024 M1 SHA mismatch')
    ledger=pd.read_csv(a.stage1_ledger)
    if len(ledger)!=1882: raise SystemExit(f'stage1 rows={len(ledger)}')
    required={'strategy','entry_utc','side','close_utc','gross_pips','breakout_level'}
    missing=sorted(required-set(ledger.columns))
    if missing: raise SystemExit(f'missing columns={missing}')
    ts=pd.to_datetime(ledger['entry_utc'],utc=True)
    fold=ts.dt.year.astype(str)+'H'+(ts.dt.month.gt(6).astype(int)+1).astype(str)
    counts={f'{x}|{y}':int(n) for (x,y),n in ledger.assign(fold=fold).groupby(['fold','strategy']).size().items()}
    if counts!=EXPECTED_COUNTS: raise SystemExit(f'population mismatch={counts}')
    m1=pd.read_csv(a.m1_2024)
    if len(m1)!=373383: raise SystemExit(f'2024 M1 rows={len(m1)}')
    tcol=next(c for c in ('timestamp_utc','timestamp','utc_time') if c in m1.columns)
    mts=pd.to_datetime(m1[tcol],utc=True)
    if mts.duplicated().any() or not mts.is_monotonic_increasing: raise SystemExit('2024 M1 time integrity')
    shutil.copy2(a.stage1_ledger,a.output_dir/a.stage1_ledger.name)
    shutil.copy2(a.m1_2024,a.output_dir/a.m1_2024.name)
    result={
      'schema_version':'usdjpy_b02_f05_structural_sl_source_stage_v1',
      'status':'PASS_SOURCE_ONLY_NO_OUTCOMES','outcomes_computed':False,
      'research_commit':a.research_commit,
      'stage1':{'sha256':EXPECTED_STAGE1_SHA,'rows':len(ledger),'columns':ledger.columns.tolist(),'fold_strategy_counts':counts},
      'm1_2024':{'sha256':EXPECTED_M1_2024_SHA,'rows':len(m1),'columns':m1.columns.tolist(),'timestamp_column':tcol,'first':mts.iloc[0].isoformat(),'last':mts.iloc[-1].isoformat()},
      'periods_accessed':['2023H1','2023H2','2024H1','2024H2'],
      'periods_not_accessed':['2025H1','2025H2'],'mt4_accessed':False,
    }
    (a.output_dir/'source_stage_result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    files=[]
    for f in sorted(a.output_dir.iterdir()):
      if f.is_file() and f.name!='output_manifest.json': files.append({'name':f.name,'bytes':f.stat().st_size,'sha256':sha(f)})
    (a.output_dir/'output_manifest.json').write_text(json.dumps({'schema_version':'usdjpy_b02_f05_structural_sl_source_stage_manifest_v1','files':files},indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'PASS_SOURCE_ONLY_NO_OUTCOMES','files':len(files),'stage1_rows':len(ledger)}))
    return 0
if __name__=='__main__': raise SystemExit(main())
