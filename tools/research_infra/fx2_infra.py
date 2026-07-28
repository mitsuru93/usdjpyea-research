#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, platform, shutil, stat, subprocess, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
FIXED_ZIP_TIME=(1980,1,1,0,0,0)
ARCHIVE_SCHEMA='fx2_deterministic_evidence_zip_v1'

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def norm(raw):
    p=PurePosixPath(str(raw).replace('\\','/'))
    if not raw or p.is_absolute() or any(x in ('','.','..') for x in p.parts) or (p.parts and p.parts[0].endswith(':')): raise ValueError('invalid archive path')
    return p.as_posix()
def runner_probe(j,m):
    cwd=Path.cwd(); disk=shutil.disk_usage(cwd)
    active=[]
    try:
        cmd=['tasklist','/FO','CSV','/NH'] if os.name=='nt' else ['ps','-eo','comm=']
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=10)
        active=[x.strip() for x in p.stdout.splitlines() if any(y in x.lower() for y in ('terminal.exe','metatester','metaeditor'))]
    except Exception: pass
    r={'schema_version':'fx2_research_infra_v1','generated_utc':now(),'os':{'name':os.name,'platform':platform.platform()},'runner':{'name':os.getenv('RUNNER_NAME'),'environment':os.getenv('RUNNER_ENVIRONMENT')},'python_version':platform.python_version(),'git_path':shutil.which('git'),'temp':tempfile.gettempdir(),'disk_free_bytes':disk.free,'tool_paths':{'terminal':os.getenv('MT4_TERMINAL_PATH'),'metaeditor':os.getenv('METAEDITOR_PATH')},'active_mt4_processes':active,'active_tester_lock':{'path':os.getenv('FX2_TESTER_LOCK_PATH'),'exists':bool(os.getenv('FX2_TESTER_LOCK_PATH') and Path(os.getenv('FX2_TESTER_LOCK_PATH')).exists())},'zip':True,'sha256':True,'github_api_auth':bool(os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')),'scientific_result_generated':False,'protected_period_accessed':False,'mt4_executed':False}
    Path(j).write_text(json.dumps(r,indent=2,sort_keys=True),encoding='utf-8'); Path(m).write_text('# Runner Capability Report\n\n```json\n'+json.dumps(r,indent=2,sort_keys=True)+'\n```\n',encoding='utf-8'); return r
def collect(root):
    rows=[]; seen=set()
    for p in sorted(x for x in Path(root).rglob('*') if x.is_file()):
        n=norm(p.relative_to(root).as_posix())
        if n in seen: raise ValueError('duplicate archive member')
        seen.add(n); rows.append((n,p.read_bytes()))
    return rows
def archive(inp,out,source_sha,run_id,classification):
    if classification not in ('scientific','non-scientific'): raise ValueError('classification')
    rows=collect(inp); manifest={'schema_version':ARCHIVE_SCHEMA,'source_commit_sha':source_sha,'workflow_run_id':str(run_id),'generated_utc':'1980-01-01T00:00:00Z','classification':classification,'members':[{'path':n,'sha256':hashlib.sha256(b).hexdigest(),'byte_size':len(b)} for n,b in rows]}
    payload=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n,b in sorted(rows+[('evidence_manifest.json',payload)]):
            i=zipfile.ZipInfo(n,FIXED_ZIP_TIME); i.create_system=3; i.external_attr=(stat.S_IFREG|0o644)<<16; i.compress_type=zipfile.ZIP_DEFLATED; i.flag_bits|=0x800; z.writestr(i,b)
    return {'archive_path':str(out),'archive_sha256':sha(out),**manifest}
def readback(path):
    with zipfile.ZipFile(path) as z:
        names={norm(i.filename):i for i in z.infolist()}
        if 'evidence_manifest.json' not in names: raise ValueError('manifest missing')
        m=json.loads(z.read(names['evidence_manifest.json']))
        exp={x['path']:x for x in m['members']}; act=set(names)-{'evidence_manifest.json'}
        if act!=set(exp): raise ValueError('member set mismatch')
        for n,s in exp.items():
            b=z.read(names[n])
            if len(b)!=s['byte_size'] or hashlib.sha256(b).hexdigest()!=s['sha256']: raise ValueError('member integrity')
    return {'status':'PASS','archive_sha256':sha(path),'manifest':m}
def storage_route(actions_available,release_allowed,release_available,local_retained):
    if actions_available:return {'mode':'ACTIONS_ARTIFACT','status':'READY','artifact_id':'PENDING_UPLOAD'}
    if release_allowed and release_available:return {'mode':'GITHUB_RELEASE_ASSET','status':'READY','artifact_id':None}
    if local_retained:return {'mode':'LOCAL_RETAINED_PENDING_PUBLICATION','status':'PENDING_PUBLICATION','artifact_id':None}
    return {'mode':'NO_EVIDENCE_NO_RESULT','status':'TECHNICAL_NO_RESULT','artifact_id':None}
def concurrency_key(repository,runner_id,terminal_id):
    clean=lambda x:''.join(c.lower() if c.isalnum() or c in '-_' else '-' for c in x).strip('-')
    return f'fx2-mt4-{clean(repository)}-runner-{clean(runner_id)}-terminal-{clean(terminal_id)}'
def tnr(stage,code,reason,repository,source_sha,run_id,runner,storage,repair):
    return {'schema_version':'fx2_technical_no_result_receipt_v1','status':'TECHNICAL_NO_RESULT','stage':stage,'reason_code':code,'human_readable_reason':reason,'repository':repository,'source_sha':source_sha,'workflow_run_id':str(run_id),'runner':runner,'evidence_storage_mode':storage,'candidate_outcome_computed':False,'protected_period_accessed':False,'mt4_executed':False,'retry_eligibility':True,'repair_boundary':repair}
def cli():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    x=sub.add_parser('probe');x.add_argument('--json',required=True);x.add_argument('--markdown',required=True)
    x=sub.add_parser('archive');x.add_argument('--input',required=True);x.add_argument('--output',required=True);x.add_argument('--source-sha',required=True);x.add_argument('--run-id',required=True);x.add_argument('--classification',default='non-scientific')
    x=sub.add_parser('readback');x.add_argument('--archive',required=True)
    x=sub.add_parser('concurrency-key');x.add_argument('--repository',required=True);x.add_argument('--runner',required=True);x.add_argument('--terminal',required=True)
    x=sub.add_parser('technical-no-result')
    for n in ('stage','reason-code','reason','repository','source-sha','run-id','runner','storage-mode','repair-boundary','output'): x.add_argument('--'+n,required=True)
    a=p.parse_args()
    if a.cmd=='probe': print(json.dumps(runner_probe(a.json,a.markdown),indent=2))
    elif a.cmd=='archive': print(json.dumps(archive(a.input,a.output,a.source_sha,a.run_id,a.classification),indent=2))
    elif a.cmd=='readback': print(json.dumps(readback(a.archive),indent=2))
    elif a.cmd=='concurrency-key': print(concurrency_key(a.repository,a.runner,a.terminal))
    else: Path(a.output).write_text(json.dumps(tnr(a.stage,a.reason_code,a.reason,a.repository,a.source_sha,a.run_id,a.runner,a.storage_mode,a.repair_boundary),indent=2,sort_keys=True),encoding='utf-8')
if __name__=='__main__': cli()
