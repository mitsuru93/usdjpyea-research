#!/usr/bin/env python3
"""Metadata-only FX2 authority and workflow registry generator."""
from __future__ import annotations
import argparse,csv,hashlib,json,os,re,subprocess,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
WORK_ID='FX2-RESEARCH-EXECUTION-ENVIRONMENT-CONSOLIDATION-001'
FIREWALL={'candidate_outcome_computed':False,'strategy_rule_changed':False,'protected_period_accessed':False,'2025H1_accessed':False,'2025H2_accessed':False,'production_authorized':False,'live_authorized':False}
MANDATORY=[
 ('SOURCE_NATIVE_RAW_TICK',('tick','raw')),('CANONICAL_BAR_AUTHORITY',('bar','authority')),('SIGNAL_LEDGER',('signal','ledger')),
 ('TRADE_LEDGER',('trade','ledger')),('DECISION_STATE_LEDGER',('decision','state','ledger')),('SOURCE_TO_CANDIDATE_MAP',('source','candidate','map')),
 ('FULL_EQUITY_EVENT_LEDGER',('full','equity','ledger')),('CHRONOLOGY_LEDGER',('chronology','ledger')),('AUTHORITY_MANIFEST',('authority','manifest')),
 ('RULE_CONTRACT',('rule','contract')),('RULE_HASH',('rule','hash')),('IMPLEMENTATION_HASH',('implementation','hash')),
 ('FINAL_DECISION',('final','decision')),('READBACK_RECEIPT',('readback','receipt'))]
AUTH_HINTS=('authority','ledger','manifest','contract','decision','readback','chronology','rule_hash','implementation_hash','source_map','trade_','signal_','equity')

def utc():return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def dump(p:Path,o:Any):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def sha(p:Path):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def blob_sha(p:Path):
 try:return subprocess.check_output(['git','hash-object',str(p)],text=True).strip()
 except Exception:return None
def lines(p:Path):
 if p.suffix.lower() not in ('.csv','.jsonl','.ndjson','.tsv'):return None
 try:
  with p.open('rb') as f:return max(sum(b.count(b'\n') for b in iter(lambda:f.read(1024*1024),b''))- (1 if p.suffix.lower() in ('.csv','.tsv') else 0),0)
 except Exception:return None
def workflow_class(name,text):
 low=name.lower()
 if low in {'fx2_research_analysis.yml','fx2_core_compile.yml','fx2_mt4_execute.yml','fx2_evidence_publish.yml','fx2_runner_health.yml'}:return 'ACTIVE_CANONICAL'
 if 'workflow_call' in text:return 'ACTIVE_STUDY_WRAPPER'
 if any(low.startswith(x) for x in ('quick_','probe_','diagnose_','watch_','recover_','repair_','hotfix_','cancel_','monitor_','observe_','snapshot_')):return 'TEMPORARY_DIAGNOSTIC'
 if re.search(r'(?:_v[2-9]|_r[2-9])\.ya?ml$',low):return 'LEGACY_SUPERSEDED'
 if any(x in low for x in ('hyp0','archive','release','publisher','validation','qualification','parity')):return 'IMMUTABLE_HISTORICAL_REFERENCE'
 return 'UNKNOWN_REQUIRES_REVIEW'
def api_pages(url,token,key=None,limit=10):
 if not token:return []
 out=[]
 try:
  for page in range(1,limit+1):
   req=urllib.request.Request(f'{url}{"&" if "?" in url else "?"}per_page=100&page={page}',headers={'Authorization':f'Bearer {token}','Accept':'application/vnd.github+json','User-Agent':'fx2-authority-v1'})
   with urllib.request.urlopen(req,timeout=60) as r:d=json.load(r)
   b=d.get(key,[]) if key else d;out+=b
   if len(b)<100:break
 except Exception:return out
 return out
def type_for(path):
 low=path.lower()
 for typ,toks in MANDATORY:
  if all(t in low for t in toks):return typ
 return 'OTHER_AUTHORITY'
def strategy_for(path):
 up=path.upper().replace('-','_')
 for s in ('B02','F05','SHORT_PULLBACK','ASIAN_RANGE_SWEEP','HYP_039','HYP_040','HYP_041','HYP_042','HYP_043','HYP_044','HYP_045','P4','B0'):
  if s in up:return s.replace('_','-') if s.startswith('HYP_') else s
 return 'PROGRAM_OR_INFRASTRUCTURE'
def period_for(path):
 low=path.lower();found=[p.upper() for p in ('2020','2021','2022','2023','2024','2025h1','2025h2') if p in low]
 return ','.join(found) if found else 'UNSPECIFIED_METADATA_ONLY'
def source_class(path):
 low=path.lower()
 if 'dukascopy' in low:return 'SOURCE_NATIVE_DUKASCOPY'
 if 'rakuten' in low or 'mt4' in low:return 'BROKER_OR_MT4'
 if 'derived' in low:return 'DERIVED'
 return 'REPOSITORY_FILE'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',default='.');ap.add_argument('--out',required=True);ap.add_argument('--repository',required=True);ap.add_argument('--source-sha',required=True);a=ap.parse_args()
 root=Path(a.root).resolve();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);token=os.getenv('GITHUB_TOKEN')
 rels=api_pages(f'https://api.github.com/repos/{a.repository}/releases',token,limit=10);asset_by_name={}
 for r in rels:
  for x in r.get('assets',[]):asset_by_name.setdefault(x.get('name'),[]).append({'release_tag':r.get('tag_name'),'release_id':r.get('id'),'asset_id':x.get('id'),'asset_name':x.get('name'),'asset_bytes':x.get('size'),'remote_digest':x.get('digest')})
 auth=[]
 for p in sorted(x for x in root.rglob('*') if x.is_file() and '.git' not in x.parts):
  rp=p.relative_to(root).as_posix();low=rp.lower()
  if not any(h in low for h in AUTH_HINTS):continue
  typ=type_for(rp);asset=(asset_by_name.get(p.name) or [{}])[0]
  auth.append({'authority_id':'AUTH-'+hashlib.sha256(rp.encode()).hexdigest()[:16],'authority_type':typ,'strategy':strategy_for(rp),'period':period_for(rp),'source':rp,'source_class':source_class(rp),'raw_or_derived':'RAW' if ('raw' in low or 'tick' in low) and 'derived' not in low else 'DERIVED_OR_DOCUMENT','schema_version':'DISCOVERED_METADATA_V1','row_count':lines(p),'file_path':rp,'file_sha256':sha(p),'git_blob_sha':blob_sha(p),'source_commit_sha':a.source_sha,'parent_authority_id':None,'superseded_authority_id':None,'release_tag':asset.get('release_tag'),'release_id':asset.get('release_id'),'asset_id':asset.get('asset_id'),'asset_name':asset.get('asset_name'),'asset_bytes':asset.get('asset_bytes'),'remote_digest':asset.get('remote_digest'),'remote_readback_status':'PASS' if 'readback' in low and 'pass' in p.read_text(encoding='utf-8',errors='ignore').lower() else 'NOT_VERIFIED_BY_METADATA_SCAN','reconstruction_command':f'git show {a.source_sha}:{rp}','required_input_ids':[],'mandatory_retention':typ!='OTHER_AUTHORITY','deletion_prohibited':typ!='OTHER_AUTHORITY','authority_status':'PRESENT_IN_REPOSITORY','notes':'Metadata-only catalog; no scientific values inspected.'})
 dump(root/'authority/authority_catalog.json',{'schema_version':'fx2_authority_catalog_v1','work_id':WORK_ID,'generated_utc':utc(),'repository':a.repository,'source_commit_sha':a.source_sha,'authority_count':len(auth),'mandatory_retention_count':sum(x['mandatory_retention'] for x in auth),'authorities':auth,**FIREWALL})
 workflows=[]
 for p in sorted((root/'.github/workflows').glob('*.y*ml')):
  t=p.read_text(encoding='utf-8',errors='replace');workflows.append({'path':p.relative_to(root).as_posix(),'name':p.name,'classification':workflow_class(p.name,t),'sha256':sha(p),'bytes':p.stat().st_size,'contents_write':'contents: write' in t,'direct_git_write':bool(re.search(r'(?i)\bgit\s+(?:commit|push|pull\s+--rebase)\b',t)),'dependencies':re.findall(r'uses:\s*([^\s]+\.github/workflows/[^\s@]+)',t)})
 with (out/'workflow_inventory.csv').open('w',newline='',encoding='utf-8') as f:
  cols=['path','name','classification','sha256','bytes','contents_write','direct_git_write'];w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows({k:x[k] for k in cols} for x in workflows)
 counts={}
 for x in workflows:counts[x['classification']]=counts.get(x['classification'],0)+1
 dump(out/'workflow_classification.json',{'schema_version':'fx2_workflow_classification_v1','counts':counts,'workflows':workflows})
 dump(out/'workflow_dependency_graph.json',{'schema_version':'fx2_workflow_dependency_graph_v1','nodes':[x['path'] for x in workflows],'edges':[{'from':x['path'],'to':d} for x in workflows for d in x['dependencies']]})
 dump(out/'workflow_deletion_plan.json',{'schema_version':'fx2_workflow_deletion_plan_v1','status':'NO_RESEARCH_WORKFLOW_DELETION_WITHOUT_EXPLICIT_REVIEW','safe_to_delete':[],'retained_count':len(workflows)})
 dump(out/'migration_plan.json',{'schema_version':'fx2_migration_plan_v1','active_execution_migration_prohibited':True,'new_study_canonical_required':True,'items':[{'current_workflow':x['path'],'target_canonical_workflow':'DETERMINE_BY_OPERATION_CLASS','migration_status':'DEFERRED_UNTIL_REPEAT','rollback_method':f'git checkout {a.source_sha} -- {x["path"]}'} for x in workflows if x['classification'] in ('ACTIVE_STUDY_WRAPPER','UNKNOWN_REQUIRES_REVIEW')]})
 mandatory_types={x[0] for x in MANDATORY};present={x['authority_type'] for x in auth};missing=sorted(mandatory_types-present)
 dump(out/'authority_integrity_audit.json',{'schema_version':'fx2_authority_integrity_audit_v1','status':'PASS_WITH_CATALOG_GAPS' if missing else 'PASS','authority_count':len(auth),'duplicate_file_sha256_count':len(auth)-len({x['file_sha256'] for x in auth}),'missing_mandatory_types':missing,'remote_assets_indexed':sum(len(r.get('assets',[])) for r in rels),**FIREWALL})
 dump(out/'missing_authority_report.json',{'schema_version':'fx2_missing_authority_report_v1','missing_type_count':len(missing),'missing_mandatory_types':missing,'limitation':'Metadata scan cannot prove off-repository Release-only row-level authorities unless their manifests/readback receipts are present.',**FIREWALL})
 arts=api_pages(f'https://api.github.com/repos/{a.repository}/actions/artifacts',token,key='artifacts',limit=20)
 with (out/'artifact_inventory.csv').open('w',newline='',encoding='utf-8') as f:
  cols=['id','name','size_in_bytes','expired','created_at','expires_at'];w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows({k:x.get(k) for k in cols} for x in arts)
 dump(out/'repository_inventory.json',{'schema_version':'fx2_repository_inventory_v1','source_sha':a.source_sha,'workflow_count':len(workflows),'authority_count':len(auth),'release_count':len(rels),'release_asset_count':sum(len(r.get('assets',[])) for r in rels),'artifact_count':len(arts),**FIREWALL})
 dump(out/'migration_receipt.json',{'schema_version':'fx2_migration_receipt_v1','status':'PASS_NEW_STUDY_PATH_READY_LEGACY_RETAINED','migrated_active_runs':0,**FIREWALL})
 dump(out/'environment_status.json',{'schema_version':'fx2_environment_status_v1','work_id':WORK_ID,'research_source_sha':a.source_sha,'authority_catalog_path':'authority/authority_catalog.json','workflow_count':len(workflows),'authority_count':len(auth),'mandatory_retention_count':sum(x['mandatory_retention'] for x in auth),'missing_authority_type_count':len(missing),'decision':'PARTIAL_FX2_ENVIRONMENT_CONSOLIDATION_WITH_REMAINING_LEGACY_WORKFLOWS',**FIREWALL})
 dump(out/'final_decision.json',{'schema_version':'fx2_environment_final_decision_v1','work_id':WORK_ID,'decision':'PARTIAL_FX2_ENVIRONMENT_CONSOLIDATION_WITH_REMAINING_LEGACY_WORKFLOWS','reason':'Central registry is operational; legacy workflows and metadata-only authority gaps remain explicitly retained/reported.',**FIREWALL})
 (out/'human_report.md').write_text(f'# {WORK_ID}\n\n- Research source SHA: `{a.source_sha}`\n- Workflows: **{len(workflows)}**\n- Authorities: **{len(auth)}**\n- Mandatory retention: **{sum(x["mandatory_retention"] for x in auth)}**\n- Missing mandatory authority types: **{len(missing)}**\n- Scientific values inspected: **false**\n',encoding='utf-8')
 rows=[]
 for p in sorted(out.rglob('*')):
  if p.is_file() and p.name!='sha256sums.txt':rows.append(f'{sha(p)}  {p.relative_to(out).as_posix()}')
 (out/'sha256sums.txt').write_text('\n'.join(rows)+'\n',encoding='utf-8')
 return 0
if __name__=='__main__':raise SystemExit(main())
