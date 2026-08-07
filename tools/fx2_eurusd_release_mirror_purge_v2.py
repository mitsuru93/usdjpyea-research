#!/usr/bin/env python3
"""Require the aggregate SHA256SUMS asset in each EURUSD yearly Release."""
from __future__ import annotations
import re, sys
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from tools import fx2_eurusd_release_mirror_purge_v1 as v1

def release_identity(api:v1.base.GitHubApi,year:int)->dict[str,Any]:
    tag=f'eurusd-{year}-raw-bidask-ticks-v1'
    r=api.json(f'/repos/{api.repository}/releases/tags/{tag}')
    if r.get('draft') or r.get('prerelease') or r.get('tag_name')!=tag:
        raise v1.Error(f'unstable Release {tag}')
    assets=[a for a in r.get('assets',[]) if isinstance(a,dict)]
    expected={f'eurusd-{year}-{m:02d}-raw-ticks-v1.{s}' for m in range(1,13) for s in ('tar.gz','manifest.json','SHA256SUMS')}
    expected|={f'eurusd-{year}-raw-ticks-v1.annual-manifest.json','RELEASE_NOTES.md','SHA256SUMS'}
    names={str(a.get('name')) for a in assets}
    if names!=expected:
        raise v1.Error(f'Release inventory mismatch {tag}: missing={sorted(expected-names)} extra={sorted(names-expected)}')
    ident=[]
    for a in assets:
        d=str(a.get('digest') or '').lower()
        if a.get('state')!='uploaded' or int(a.get('size') or 0)<=0 or not re.fullmatch(r'sha256:[0-9a-f]{64}',d):
            raise v1.Error(f'invalid Release asset {tag}/{a.get("name")}')
        ident.append({'id':int(a['id']),'name':a['name'],'size':int(a['size']),'digest':d})
    ident.sort(key=lambda x:x['name'])
    return {'release_id':int(r['id']),'tag':tag,'published_at':r.get('published_at'),'asset_count':len(ident),'asset_identity_sha256':v1.sh(ident)}

def main()->None:
    v1.release_identity=release_identity
    v1.main()
if __name__=='__main__':main()
