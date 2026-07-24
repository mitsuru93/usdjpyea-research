#!/usr/bin/env python3
"""Validate the canonical USDJPY research-memory system."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any

def load_json(root: Path, rel: str) -> dict[str, Any]:
    path=root/rel
    if not path.is_file(): raise RuntimeError(f"missing required file: {rel}")
    try: return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc: raise RuntimeError(f"invalid JSON: {rel}: {exc}") from exc

def load_addendum_entries(root: Path, rel: str, ledger_path: str, seen: set[str]) -> list[dict[str, Any]]:
    if rel in seen: raise RuntimeError(f"addendum cycle: {rel}")
    seen.add(rel)
    addendum=load_json(root,rel)
    if addendum.get("base_ledger")!=ledger_path: raise RuntimeError(f"hypothesis-ledger addendum points to wrong base ledger: {rel}")
    rows=addendum.get("entries")
    if not isinstance(rows,list): raise RuntimeError(f"hypothesis-ledger addendum entries are not a list: {rel}")
    if addendum.get("entry_mode")=="DELTA_INHERIT_SUPERSEDES":
        parent=addendum.get("supersedes")
        if not isinstance(parent,str) or not parent: raise RuntimeError(f"delta addendum missing supersedes: {rel}")
        return load_addendum_entries(root,parent,ledger_path,seen)+rows
    return list(rows)

def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--root",type=Path,default=Path(".")); parser.add_argument("--output",type=Path); args=parser.parse_args(); root=args.root.resolve()
    manifest_path="configs/research/usdjpy_research_memory_manifest_v1.json"; manifest=load_json(root,manifest_path)
    required=[]
    for item in manifest.get("mandatory_startup_read_order",[]):
        rel=item.get("path")
        if not isinstance(rel,str) or not rel: raise RuntimeError("mandatory_startup_read_order contains an invalid path")
        required.append(rel)
        if not (root/rel).is_file(): raise RuntimeError(f"mandatory startup file missing: {rel}")
    pointers=manifest.get("canonical_pointers",{})
    for key,value in pointers.items():
        if not isinstance(value,str): raise RuntimeError(f"canonical pointer {key} is not a string")
        if value.startswith("mitsuru93/") and ":" in value: continue
        if not (root/value).is_file(): raise RuntimeError(f"canonical pointer missing: {key} -> {value}")
    registry_path=pointers["current_candidate_registry"]; contract_path=pointers["operating_contract"]; ledger_path=pointers["hypothesis_ledger"]; addendum_path=pointers.get("hypothesis_ledger_addendum")
    registry=load_json(root,registry_path); contract=load_json(root,contract_path); ledger=load_json(root,ledger_path)
    memory=registry.get("research_memory",{})
    if memory.get("manifest")!=manifest_path: raise RuntimeError("latest registry does not point to canonical memory manifest")
    if memory.get("hypothesis_ledger")!=ledger_path: raise RuntimeError("latest registry does not point to canonical hypothesis ledger")
    if memory.get("operating_contract")!=contract_path: raise RuntimeError("latest registry does not point to canonical operating contract")
    if addendum_path and memory.get("hypothesis_ledger_addendum")!=addendum_path: raise RuntimeError("latest registry does not point to canonical hypothesis-ledger addendum")
    if contract.get("research_memory_manifest")!=manifest_path: raise RuntimeError("operating contract does not point to canonical memory manifest")
    if contract.get("hypothesis_ledger")!=ledger_path: raise RuntimeError("operating contract does not point to canonical hypothesis ledger")
    required_fields=set(ledger.get("entry_required_fields",[])); base=ledger.get("entries")
    if not isinstance(base,list) or not base: raise RuntimeError("hypothesis ledger has no entries")
    entries=list(base)
    if addendum_path: entries.extend(load_addendum_entries(root,addendum_path,ledger_path,set()))
    ids=set(); family_to_ids={}
    for row in entries:
        if not isinstance(row,dict): raise RuntimeError("ledger entry is not an object")
        missing=sorted(required_fields-set(row))
        if missing: raise RuntimeError(f"ledger entry missing fields: {row.get('hypothesis_id')}: {missing}")
        hid=row["hypothesis_id"]
        if hid in ids: raise RuntimeError(f"duplicate hypothesis_id: {hid}")
        ids.add(hid)
        for fam in row.get("family_ids",[]): family_to_ids.setdefault(fam,[]).append(hid)
        if not row.get("evidence_refs"): raise RuntimeError(f"ledger entry has no evidence refs: {hid}")
        if str(row.get("status","")).startswith("CLOSED") and not row.get("prohibited_reuse"): raise RuntimeError(f"closed ledger entry has no prohibited_reuse: {hid}")
    closed=registry.get("closed_families",[]); missing=[f for f in closed if f not in family_to_ids]
    if missing: raise RuntimeError(f"closed registry families absent from ledger: {missing}")
    oq=registry.get("current_open_research_question")
    if oq and oq not in ids: raise RuntimeError(f"current open research question absent from ledger: {oq}")
    snap=manifest.get("current_state_snapshot",{})
    if snap.get("registry_status")!=registry.get("status"): raise RuntimeError("manifest registry-status snapshot is stale")
    if snap.get("next_action")!=registry.get("next_action"): raise RuntimeError("manifest next-action snapshot is stale")
    if snap.get("current_open_research_question")!=oq: raise RuntimeError("manifest open-question snapshot is stale")
    result={"schema_version":"usdjpy_research_memory_validation_receipt_v1","status":"PASS","manifest":manifest_path,"registry":registry_path,"registry_schema":registry.get("schema_version"),"registry_status":registry.get("status"),"operating_contract":contract_path,"hypothesis_ledger":ledger_path,"hypothesis_ledger_addendum":addendum_path,"base_hypothesis_count":len(base),"hypothesis_count":len(entries),"closed_family_count":len(closed),"current_open_research_question":oq,"next_action":registry.get("next_action"),"mandatory_startup_files":required}
    text=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if args.output: args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(text,encoding="utf-8")
    print(text,end="")
if __name__=="__main__": main()
