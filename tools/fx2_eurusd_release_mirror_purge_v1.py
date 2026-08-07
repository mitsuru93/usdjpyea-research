#!/usr/bin/env python3
"""Delete EURUSD Tick Actions copies after complete yearly Release validation."""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from tools import fx2_release_backed_artifact_purge_v1 as base
from tools import fx2_release_backed_artifact_purge_v3 as semantic

class Error(RuntimeError): pass

def cj(v:Any)->str: return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def sh(v:Any)->str: return hashlib.sha256(cj(v).encode()).hexdigest()
def fb(n:int)->str:
    x=float(n);u=['B','KiB','MiB','GiB'];i=0
    while x>=1024 and i<len(u)-1:x/=1024;i+=1
    return f'{x:.2f} {u[i]}' if i else f'{int(x)} B'

def release_identity(api:base.GitHubApi,year:int)->dict[str,Any]:
    tag=f'eurusd-{year}-raw-bidask-ticks-v1'
    r=api.json(f'/repos/{api.repository}/releases/tags/{tag}')
    if r.get('draft') or r.get('prerelease') or r.get('tag_name')!=tag: raise Error(f'unstable Release {tag}')
    assets=[a for a in r.get('assets',[]) if isinstance(a,dict)]
    expected={f'eurusd-{year}-{m:02d}-raw-ticks-v1.{s}' for m in range(1,13) for s in ('tar.gz','manifest.json','SHA256SUMS')}
    expected|={f'eurusd-{year}-raw-ticks-v1.annual-manifest.json','RELEASE_NOTES.md'}
    names={str(a.get('name')) for a in assets}
    if names!=expected: raise Error(f'Release inventory mismatch {tag}: missing={sorted(expected-names)} extra={sorted(names-expected)}')
    ident=[]
    for a in assets:
        d=str(a.get('digest') or '').lower()
        if a.get('state')!='uploaded' or int(a.get('size') or 0)<=0 or not re.fullmatch(r'sha256:[0-9a-f]{64}',d):
            raise Error(f'invalid Release asset {tag}/{a.get("name")}')
        ident.append({'id':int(a['id']),'name':a['name'],'size':int(a['size']),'digest':d})
    ident.sort(key=lambda x:x['name'])
    return {'release_id':int(r['id']),'tag':tag,'published_at':r.get('published_at'),'asset_count':len(ident),'asset_identity_sha256':sh(ident)}

def candidates(api:base.GitHubApi,root:Path,run_id:int,years:list[int]):
    run=api.json(f'/repos/{api.repository}/actions/runs/{run_id}')
    if run.get('status')!='completed' or run.get('conclusion')!='success' or run.get('name')!='Collect EURUSD 2020-2023 Raw Bid Ask Ticks v1':
        raise Error(f'wrong source run: {run.get("name")} {run.get("status")}/{run.get("conclusion")}')
    arts=api.paginate(f'/repos/{api.repository}/actions/runs/{run_id}/artifacts?',cap=100)
    expected_names={f'eurusd-{y}-raw-ticks-month-{m:02d}-{run_id}' for y in years for m in range(1,13)}
    expected_names|={f'eurusd-{y}-raw-ticks-annual-{run_id}-1' for y in years}
    by_name={a['name']:a for a in arts}
    if set(by_name)!=expected_names: raise Error(f'run Artifact inventory mismatch missing={sorted(expected_names-set(by_name))} extra={sorted(set(by_name)-expected_names)}')
    releases=[release_identity(api,y) for y in years]
    relmap={int(r['tag'].split('-')[1]):r for r in releases}
    classification=base.load_workflow_classification(root); files=list(base.iter_dependency_files(root,classification))
    selected=[];blocked=[]
    for name in sorted(expected_names):
        a=by_name[name];y=int(name.split('-')[1]);d=str(a.get('digest') or '').lower()
        if a.get('expired') or int(a.get('size_in_bytes') or 0)<=0 or not re.fullmatch(r'sha256:[0-9a-f]{64}',d): raise Error(f'invalid Artifact {a.get("id")}')
        row={'artifact_id':int(a['id']),'artifact_name':name,'bytes':int(a['size_in_bytes']),'artifact_digest':d,'run_id':run_id,'head_sha':run.get('head_sha'),'year':y,**relmap[y]}
        refs=semantic.semantic_dependency_refs(a,files)
        if refs: row['blocking_reasons']=refs;blocked.append(row)
        else:selected.append(row)
    return selected,blocked,releases,{'source_run_id':run_id,'source_run_sha':run.get('head_sha'),'source_run_updated_at':run.get('updated_at'),'dependency_file_count':len(files)}

def identity(rows):
    keys=('artifact_id','artifact_name','bytes','artifact_digest','run_id','head_sha','year','release_id','tag','published_at','asset_count','asset_identity_sha256')
    return [{k:r[k] for k in keys} for r in rows]

def report(r):
    lines=['## FX2 EURUSD Release-mirror Artifact Purge','',f"- Mode: `{r['mode']}`",f"- Selected: `{r['candidate_count']}` ({fb(r['candidate_bytes'])})",f"- Blocked: `{r['blocked_count']}` ({fb(r['blocked_bytes'])})",f"- Deleted: `{r['deleted_count']}` ({fb(r['deleted_bytes'])})",f"- Remaining selected: `{r['remaining_candidate_count']}`",f"- Candidate digest: `{r['candidate_digest']}`",f"- Errors: `{r['error_count']}`",'', '| Artifact | Release | Size |','|---|---|---:|']
    for x in r['candidates']: lines.append(f"| `{x['artifact_name']}` (`{x['artifact_id']}`) | `{x['tag']}` | {fb(x['bytes'])} |")
    if r['blocked']:
        lines+=['','### Blocked','','| Artifact | Reason |','|---|---|']
        for x in r['blocked']:lines.append(f"| `{x['artifact_name']}` | {'<br>'.join('`'+z+'`' for z in x['blocking_reasons'][:8])} |")
    summary={k:r[k] for k in ('schema_version','mode','repository','generated_at','source_run_id','candidate_count','candidate_bytes','candidate_digest','blocked_count','blocked_bytes','deleted_count','deleted_bytes','remaining_candidate_count','error_count','errors')}
    lines+=['','<details><summary>Machine-readable summary</summary>','','```json',cj(summary),'```','</details>']
    return '\n'.join(lines)+'\n'

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=('dry-run','apply'),required=True);p.add_argument('--repository',required=True);p.add_argument('--root',default='.');p.add_argument('--run-id',type=int,required=True);p.add_argument('--years',required=True);p.add_argument('--expected-candidate-digest');p.add_argument('--max-deletions',type=int,default=100);p.add_argument('--max-bytes',type=int,default=10_000_000_000);p.add_argument('--receipt',required=True);p.add_argument('--report',required=True);a=p.parse_args()
    years=[int(x) for x in a.years.split(',') if x];
    if years!=[2020,2021,2022,2023]: raise Error('years must be exactly 2020,2021,2022,2023')
    api=base.GitHubApi(os.environ.get('GITHUB_TOKEN',''),a.repository);root=Path(a.root).resolve()
    rows,blocked,releases,meta=candidates(api,root,a.run_id,years);digest=sh(identity(rows));total=sum(x['bytes'] for x in rows)
    if len(rows)>a.max_deletions or total>a.max_bytes:raise Error('safety cap exceeded')
    if a.mode=='apply':
        if a.expected_candidate_digest!=digest:raise Error(f'candidate digest mismatch expected={a.expected_candidate_digest} observed={digest}')
        rows2,blocked2,releases2,_=candidates(api,root,a.run_id,years)
        if sh(identity(rows2))!=digest or cj(blocked2)!=cj(blocked) or cj(releases2)!=cj(releases):raise Error('pre-delete evidence changed')
    deleted=[];errors=[]
    if a.mode=='apply':
        for x in rows:
            try:api.delete_artifact(x['artifact_id']);deleted.append(x['artifact_id'])
            except base.PurgeError as e:errors.append(f"{x['artifact_id']}: {e}")
    remain={int(x['id']) for x in api.paginate(f'/repos/{api.repository}/actions/artifacts?',cap=20_000)}
    remaining={x['artifact_id'] for x in rows if x['artifact_id'] in remain}
    for i in deleted:
        if i in remaining:errors.append(f'deleted Artifact still present {i}')
    post=[release_identity(api,y) for y in years]
    if cj(post)!=cj(releases):errors.append('Release identity changed')
    ds=set(deleted);rec={'schema_version':'fx2_eurusd_release_mirror_purge_receipt_v1','mode':a.mode,'repository':a.repository,'generated_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),**meta,'candidate_count':len(rows),'candidate_bytes':total,'candidate_digest':digest,'blocked_count':len(blocked),'blocked_bytes':sum(x['bytes'] for x in blocked),'deleted_count':len(deleted),'deleted_bytes':sum(x['bytes'] for x in rows if x['artifact_id'] in ds),'remaining_candidate_count':len(remaining),'error_count':len(errors),'errors':errors,'releases':releases,'candidates':rows,'blocked':blocked}
    Path(a.receipt).write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n');Path(a.report).write_text(report(rec));print(cj({k:rec[k] for k in ('candidate_count','candidate_bytes','candidate_digest','blocked_count','deleted_count','deleted_bytes','remaining_candidate_count','error_count')}))
    if errors:raise Error(f'{len(errors)} errors')
if __name__=='__main__':
    try:main()
    except (Error,base.PurgeError) as e:print(f'ERROR: {e}',file=sys.stderr);raise SystemExit(1)
