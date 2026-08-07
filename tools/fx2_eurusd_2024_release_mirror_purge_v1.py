#!/usr/bin/env python3
"""Delete EURUSD 2024 Actions copies after complete Release validation."""
from __future__ import annotations
import argparse,hashlib,json,os,re,sys
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools import fx2_release_backed_artifact_purge_v1 as base
from tools import fx2_release_backed_artifact_purge_v3 as semantic

IDS=(8477498593,8477440645,8477367327,8477474051,8477507450,8480213791,8478305114,8478602440,8478903697,8479255289,8479395926,8479506330,8480394478)
TAG='eurusd-2024-raw-bidask-ticks-v1'
class Error(RuntimeError):pass
def cj(v:Any)->str:return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sh(v:Any)->str:return hashlib.sha256(cj(v).encode()).hexdigest()
def fb(n:int)->str:
 x=float(n);u=['B','KiB','MiB','GiB'];i=0
 while x>=1024 and i<len(u)-1:x/=1024;i+=1
 return f'{x:.2f} {u[i]}' if i else f'{int(x)} B'
def release_identity(api:base.GitHubApi)->dict[str,Any]:
 r=api.json(f'/repos/{api.repository}/releases/tags/{TAG}')
 if r.get('draft') or r.get('prerelease') or r.get('tag_name')!=TAG:raise Error('unstable Release')
 expected={f'eurusd-2024-{m:02d}-raw-ticks-v1.{s}' for m in range(1,13) for s in ('tar.gz','manifest.json')}
 expected|={f'eurusd-2024-{m:02d}-source-artifacts.json' for m in range(1,13)}
 expected|={'eurusd-2024-raw-ticks-v1.annual-manifest.json','RELEASE_NOTES.md','SHA256SUMS'}
 assets=[a for a in r.get('assets',[]) if isinstance(a,dict)];names={a['name'] for a in assets}
 if names!=expected:raise Error(f'Release inventory mismatch missing={sorted(expected-names)} extra={sorted(names-expected)}')
 ident=[]
 for a in assets:
  d=str(a.get('digest') or '').lower()
  if a.get('state')!='uploaded' or int(a.get('size') or 0)<=0 or not re.fullmatch(r'sha256:[0-9a-f]{64}',d):raise Error(f'invalid Release asset {a.get("name")}')
  ident.append({'id':int(a['id']),'name':a['name'],'size':int(a['size']),'digest':d})
 ident.sort(key=lambda x:x['name'])
 return {'release_id':int(r['id']),'release_tag':TAG,'published_at':r.get('published_at'),'asset_count':len(ident),'asset_identity_sha256':sh(ident)}
def build(api:base.GitHubApi,root:Path):
 release=release_identity(api);classification=base.load_workflow_classification(root);files=list(base.iter_dependency_files(root,classification));rows=[];blocked=[];runs={}
 for aid in IDS:
  try:a=api.json(f'/repos/{api.repository}/actions/artifacts/{aid}')
  except base.PurgeError:continue
  d=str(a.get('digest') or '').lower();run_id=int((a.get('workflow_run') or {}).get('id') or 0)
  if a.get('expired') or int(a.get('size_in_bytes') or 0)<=0 or not re.fullmatch(r'sha256:[0-9a-f]{64}',d) or run_id<=0:raise Error(f'invalid Artifact {aid}')
  if run_id not in runs:runs[run_id]=api.json(f'/repos/{api.repository}/actions/runs/{run_id}')
  run=runs[run_id]
  if run.get('status')!='completed' or run.get('conclusion')!='success':raise Error(f'source run not successful {run_id}')
  row={'artifact_id':aid,'artifact_name':a['name'],'bytes':int(a['size_in_bytes']),'artifact_digest':d,'run_id':run_id,'head_sha':run.get('head_sha'),**release}
  refs=semantic.semantic_dependency_refs(a,files)
  if refs:row['blocking_reasons']=refs;blocked.append(row)
  else:rows.append(row)
 rows.sort(key=lambda x:x['artifact_id']);blocked.sort(key=lambda x:x['artifact_id'])
 return rows,blocked,release,{'dependency_file_count':len(files),'source_run_ids':sorted(runs)}
def ident(rows):
 keys=('artifact_id','artifact_name','bytes','artifact_digest','run_id','head_sha','release_id','release_tag','published_at','asset_count','asset_identity_sha256')
 return [{k:r[k] for k in keys} for r in rows]
def report(r):
 lines=['## FX2 EURUSD 2024 Release-mirror Artifact Purge','',f"- Mode: `{r['mode']}`",f"- Selected: `{r['candidate_count']}` ({fb(r['candidate_bytes'])})",f"- Blocked: `{r['blocked_count']}` ({fb(r['blocked_bytes'])})",f"- Deleted: `{r['deleted_count']}` ({fb(r['deleted_bytes'])})",f"- Remaining selected: `{r['remaining_candidate_count']}`",f"- Candidate digest: `{r['candidate_digest']}`",f"- Errors: `{r['error_count']}`",'', '| Artifact | Run | Size |','|---|---:|---:|']
 for x in r['candidates']:lines.append(f"| `{x['artifact_name']}` (`{x['artifact_id']}`) | {x['run_id']} | {fb(x['bytes'])} |")
 if r['blocked']:
  lines+=['','### Blocked','','| Artifact | Reason |','|---|---|']
  for x in r['blocked']:lines.append(f"| `{x['artifact_name']}` | {'<br>'.join('`'+z+'`' for z in x['blocking_reasons'][:8])} |")
 s={k:r[k] for k in ('schema_version','mode','repository','generated_at','candidate_count','candidate_bytes','candidate_digest','blocked_count','blocked_bytes','deleted_count','deleted_bytes','remaining_candidate_count','error_count','errors')}
 lines+=['','<details><summary>Machine-readable summary</summary>','','```json',cj(s),'```','</details>'];return '\n'.join(lines)+'\n'
def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=('dry-run','apply'),required=True);p.add_argument('--repository',required=True);p.add_argument('--root',default='.');p.add_argument('--expected-candidate-digest');p.add_argument('--max-deletions',type=int,default=20);p.add_argument('--max-bytes',type=int,default=2_000_000_000);p.add_argument('--receipt',required=True);p.add_argument('--report',required=True);a=p.parse_args()
 api=base.GitHubApi(os.environ.get('GITHUB_TOKEN',''),a.repository);root=Path(a.root).resolve();rows,blocked,release,meta=build(api,root);digest=sh(ident(rows));total=sum(x['bytes'] for x in rows)
 if len(rows)>a.max_deletions or total>a.max_bytes:raise Error('safety cap exceeded')
 if a.mode=='apply':
  if a.expected_candidate_digest!=digest:raise Error(f'candidate digest mismatch expected={a.expected_candidate_digest} observed={digest}')
  r2,b2,rel2,_=build(api,root)
  if sh(ident(r2))!=digest or cj(b2)!=cj(blocked) or cj(rel2)!=cj(release):raise Error('pre-delete evidence changed')
 deleted=[];errors=[]
 if a.mode=='apply':
  for x in rows:
   try:api.delete_artifact(x['artifact_id']);deleted.append(x['artifact_id'])
   except base.PurgeError as e:errors.append(f"{x['artifact_id']}: {e}")
 remain={int(x['id']) for x in api.paginate(f'/repos/{api.repository}/actions/artifacts?',cap=20_000)};remaining={x['artifact_id'] for x in rows if x['artifact_id'] in remain}
 for i in deleted:
  if i in remaining:errors.append(f'deleted Artifact still present {i}')
 if cj(release_identity(api))!=cj(release):errors.append('Release identity changed')
 ds=set(deleted);rec={'schema_version':'fx2_eurusd_2024_release_mirror_purge_receipt_v1','mode':a.mode,'repository':a.repository,'generated_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),**meta,'candidate_count':len(rows),'candidate_bytes':total,'candidate_digest':digest,'blocked_count':len(blocked),'blocked_bytes':sum(x['bytes'] for x in blocked),'deleted_count':len(deleted),'deleted_bytes':sum(x['bytes'] for x in rows if x['artifact_id'] in ds),'remaining_candidate_count':len(remaining),'error_count':len(errors),'errors':errors,'release':release,'candidates':rows,'blocked':blocked}
 Path(a.receipt).write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n');Path(a.report).write_text(report(rec));print(cj({k:rec[k] for k in ('candidate_count','candidate_bytes','candidate_digest','blocked_count','deleted_count','deleted_bytes','remaining_candidate_count','error_count')}))
 if errors:raise Error(f'{len(errors)} errors')
if __name__=='__main__':
 try:main()
 except (Error,base.PurgeError) as e:print(f'ERROR: {e}',file=sys.stderr);raise SystemExit(1)
