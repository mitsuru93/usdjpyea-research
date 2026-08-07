#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPO = "mitsuru93/usdjpyea-research"
RECEIPT = ROOT / "configs/research/usdjpy_hyp034_release_receipt_v1.json"
PREFIXES = ("usdjpy-hyp034-development-v1-r1-", "usdjpy-hyp034-development-v1-")
CONSUMER_TOKENS = (
    "actions/download-artifact", "download-artifact", "gh run download",
    "/actions/artifacts/", "artifact_id", "artifact-id", "archive_download_url",
)

class Failure(RuntimeError): pass


def api(path: str, method: str = "GET") -> Any:
    import urllib.request, urllib.error
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        method=method,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raise Failure(f"GitHub API {method} {path}: {exc.code} {exc.read().decode(errors='replace')[:500]}") from exc


def canonical(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(v: Any) -> str:
    return hashlib.sha256(canonical(v).encode()).hexdigest()


def human(n: int) -> str:
    x=float(n)
    for unit in ("B","KiB","MiB","GiB"):
        if x < 1024 or unit == "GiB": return f"{int(x)} {unit}" if unit == "B" else f"{x:.2f} {unit}"
        x/=1024
    return f"{x:.2f} GiB"


def artifacts() -> list[dict[str, Any]]:
    out=[]; page=1
    while True:
        payload=api(f"/repos/{REPO}/actions/artifacts?per_page=100&page={page}")
        rows=payload.get("artifacts") or []
        out.extend(rows)
        if len(rows)<100: return out
        page+=1
        if page>100: raise Failure("pagination safety limit")


def validate_release() -> dict[str, Any]:
    receipt=json.loads(RECEIPT.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS_BYTE_IDENTICAL_RELEASE_READBACK" or receipt.get("byte_identical_readback") is not True:
        raise Failure("HYP034 durable Release receipt is not PASS byte-identical")
    tag=str(receipt["release_tag"]); asset_name=str(receipt["release_asset"])
    release=api(f"/repos/{REPO}/releases/tags/{tag}")
    if release.get("draft") or release.get("prerelease") or release.get("tag_name") != tag:
        raise Failure("HYP034 Release is not stable")
    assets={str(a.get("name")):a for a in release.get("assets") or []}
    asset=assets.get(asset_name)
    expected="sha256:"+str(receipt["release_asset_sha256"]).lower()
    if not asset or asset.get("state") != "uploaded" or int(asset.get("size") or 0)<=0 or str(asset.get("digest") or "").lower()!=expected:
        raise Failure("HYP034 Release asset digest/readback mismatch")
    return {
        "release_id": int(release["id"]), "release_tag": tag,
        "release_asset_id": int(asset["id"]), "release_asset": asset_name,
        "release_asset_size": int(asset["size"]), "release_asset_digest": expected,
        "receipt_sha256": hashlib.sha256(RECEIPT.read_bytes()).hexdigest(),
    }


def workflow_texts() -> dict[str,str]:
    result={}
    for path in sorted((ROOT/".github/workflows").glob("*.y*ml")):
        result[str(path.relative_to(ROOT))]=path.read_text(encoding="utf-8", errors="replace")
    return result


def blockers(name: str, aid: int, texts: dict[str,str]) -> list[str]:
    found=[]
    for path,text in texts.items():
        lines=text.splitlines()
        for i,line in enumerate(lines):
            if name not in line and str(aid) not in line: continue
            context="\n".join(lines[max(0,i-8):min(len(lines),i+9)]).lower()
            if any(tok in context for tok in CONSUMER_TOKENS):
                found.append(f"{path}:{i+1}"); break
    return sorted(set(found))


def build() -> tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    texts=workflow_texts(); selected=[]; blocked=[]; run_cache={}
    for a in artifacts():
        if a.get("expired") is True: continue
        name=str(a.get("name") or "")
        if not name.startswith(PREFIXES): continue
        aid=int(a["id"]); run_id=int((a.get("workflow_run") or {}).get("id") or 0)
        if run_id not in run_cache: run_cache[run_id]=api(f"/repos/{REPO}/actions/runs/{run_id}")
        run=run_cache[run_id]
        row={
            "artifact_id":aid,"artifact_name":name,"bytes":int(a.get("size_in_bytes") or 0),
            "artifact_digest":str(a.get("digest") or ""),"run_id":run_id,
            "run_status":str(run.get("status") or ""),"run_conclusion":str(run.get("conclusion") or ""),
            "head_sha":str(run.get("head_sha") or ""),"created_at":a.get("created_at"),"expires_at":a.get("expires_at"),
        }
        reasons=blockers(name,aid,texts)
        if run.get("status") != "completed": reasons.append(f"run_not_completed:{run.get('status')}")
        if reasons:
            row["blocking_reasons"]=sorted(set(reasons)); blocked.append(row)
        else: selected.append(row)
    selected.sort(key=lambda r:r["artifact_id"]); blocked.sort(key=lambda r:(-r["bytes"],r["artifact_id"]))
    return selected,blocked


def ident(rows:list[dict[str,Any]])->list[dict[str,Any]]:
    keys=("artifact_id","artifact_name","bytes","artifact_digest","run_id","run_conclusion","head_sha","created_at","expires_at")
    return [{k:r[k] for k in keys} for r in rows]


def report(rec:dict[str,Any])->str:
    lines=["## HYP-034 Release-backed Actions Artifact purge","",
        f"- Mode: `{rec['mode']}`",f"- Selected: **{rec['candidate_count']}** ({human(rec['candidate_bytes'])})",
        f"- Blocked: `{rec['blocked_count']}` ({human(rec['blocked_bytes'])})",f"- Deleted: **{rec['deleted_count']}** ({human(rec['deleted_bytes'])})",
        f"- Remaining selected: `{rec['remaining_candidate_count']}`",f"- Candidate digest: `{rec['candidate_digest']}`",
        f"- Release: `{rec['release']['release_tag']}`",f"- Errors: **{rec['error_count']}**","", "```json",
        canonical({k:rec[k] for k in ("mode","candidate_count","candidate_bytes","blocked_count","blocked_bytes","deleted_count","deleted_bytes","remaining_candidate_count","candidate_digest","error_count","errors")}),"```",""]
    return "\n".join(lines)


def main()->None:
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=("dry-run","apply"),required=True); ap.add_argument("--expected-candidate-digest"); ap.add_argument("--receipt",required=True); ap.add_argument("--report",required=True); args=ap.parse_args()
    release=validate_release(); rows,blocked=build(); cd=digest(ident(rows))
    if args.mode=="apply" and args.expected_candidate_digest!=cd: raise Failure(f"candidate digest mismatch expected={args.expected_candidate_digest} observed={cd}")
    if args.mode=="apply":
        release2=validate_release(); rows2,blocked2=build()
        if canonical(release2)!=canonical(release) or digest(ident(rows2))!=cd or canonical(blocked2)!=canonical(blocked): raise Failure("pre-delete evidence changed")
    deleted=[]; errors=[]
    if args.mode=="apply":
        for r in rows:
            try: api(f"/repos/{REPO}/actions/artifacts/{r['artifact_id']}",method="DELETE"); deleted.append(r["artifact_id"])
            except Failure as exc: errors.append(f"{r['artifact_id']}: {exc}")
    remaining_ids={int(a["id"]) for a in artifacts()}; remaining=[r for r in rows if r["artifact_id"] in remaining_ids]
    if args.mode=="apply" and canonical(validate_release())!=canonical(release): errors.append("HYP034 Release identity changed")
    deleted_set=set(deleted)
    rec={"schema_version":"fx2_hyp034_release_backed_artifact_purge_receipt_v1","mode":args.mode,"repository":REPO,"release":release,
        "candidate_count":len(rows),"candidate_bytes":sum(r["bytes"] for r in rows),"candidate_digest":cd,"blocked_count":len(blocked),"blocked_bytes":sum(r["bytes"] for r in blocked),
        "deleted_count":len(deleted),"deleted_bytes":sum(r["bytes"] for r in rows if r["artifact_id"] in deleted_set),"remaining_candidate_count":len(remaining),
        "error_count":len(errors),"errors":errors,"blocked":blocked}
    Path(args.receipt).write_text(json.dumps(rec,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8"); Path(args.report).write_text(report(rec),encoding="utf-8")
    print(canonical({k:rec[k] for k in ("candidate_count","candidate_bytes","candidate_digest","blocked_count","blocked_bytes","deleted_count","deleted_bytes","remaining_candidate_count","error_count")}))
    if errors: raise Failure(f"{len(errors)} errors")

if __name__=="__main__":
    try: main()
    except Failure as exc:
        print(f"ERROR: {exc}",file=sys.stderr); raise SystemExit(1)
