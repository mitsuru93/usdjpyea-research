#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, json, os, urllib.error, urllib.parse, urllib.request
from pathlib import Path, PurePosixPath

def normalize(raw: str) -> str:
    if not raw or '\x00' in raw:
        raise ValueError('unexpected path')
    p=PurePosixPath(raw.replace('\\','/'))
    if p.is_absolute() or any(x in ('','.','..') for x in p.parts) or (p.parts and p.parts[0].endswith(':')):
        raise ValueError(f'path traversal or invalid path: {raw}')
    return p.as_posix()

def request(url: str, token: str|None, accept='application/vnd.github+json') -> bytes:
    h={'Accept':accept,'User-Agent':'fx2-exact-sha-fetch-v1','X-GitHub-Api-Version':'2022-11-28'}
    if token: h['Authorization']=f'Bearer {token}'
    with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=60) as r:
        return r.read()

def fetch(repository: str, sha: str, manifest_path: Path, root: Path, token: str|None):
    if len(sha)!=40 or any(c not in '0123456789abcdefABCDEF' for c in sha):
        raise ValueError('exact 40-character commit SHA required; branch names are forbidden')
    m=json.loads(manifest_path.read_text(encoding='utf-8'))
    if m.get('schema_version')!='fx2_source_manifest_v1': raise ValueError('schema mismatch')
    items=m.get('required_files')
    if not isinstance(items,list) or not items: raise ValueError('required_files missing')
    root.mkdir(parents=True,exist_ok=True)
    seen=set(); records=[]
    for item in items:
        rp=normalize(item['repository_path']); lp=normalize(item.get('local_path',rp))
        if lp in seen: raise ValueError('duplicate destination')
        seen.add(lp)
        url=f"https://api.github.com/repos/{repository}/contents/{urllib.parse.quote(rp,safe='/')}?ref={sha}"
        try: meta=json.loads(request(url,token).decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code==404: raise FileNotFoundError(rp) from e
            raise
        if meta.get('type')!='file' or not meta.get('sha'): raise ValueError(f'unexpected file response: {rp}')
        content=meta.get('content')
        payload=base64.b64decode(''.join(content.split()),validate=True) if content else request(url,token,'application/vnd.github.raw')
        digest=hashlib.sha256(payload).hexdigest()
        if item.get('sha256') and digest.lower()!=item['sha256'].lower(): raise ValueError(f'SHA-256 mismatch: {rp}')
        if item.get('blob_sha') and meta['sha'].lower()!=item['blob_sha'].lower(): raise ValueError(f'blob SHA mismatch: {rp}')
        dest=(root/Path(*PurePosixPath(lp).parts)).resolve(); rr=root.resolve()
        if rr!=dest and rr not in dest.parents: raise ValueError('path traversal')
        dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(payload)
        records.append({'repository_path':rp,'local_path':lp,'blob_sha':meta['sha'],'sha256':digest,'byte_size':len(payload)})
    out={'schema_version':'fx2_fetched_source_manifest_v1','repository':repository,'source_commit_sha':sha.lower(),'files':records}
    (root/'source_fetch_manifest.json').write_text(json.dumps(out,indent=2,sort_keys=True),encoding='utf-8')
    return out

def main():
    p=argparse.ArgumentParser(); p.add_argument('--repository',required=True); p.add_argument('--sha',required=True); p.add_argument('--manifest',required=True); p.add_argument('--work-root',required=True); p.add_argument('--token-env',default='GITHUB_TOKEN'); a=p.parse_args()
    print(json.dumps(fetch(a.repository,a.sha,Path(a.manifest),Path(a.work_root),os.getenv(a.token_env)),indent=2))
if __name__=='__main__': main()
