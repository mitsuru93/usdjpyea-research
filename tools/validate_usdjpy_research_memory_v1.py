#!/usr/bin/env python3
"""Validate the canonical USDJPY research-memory system."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    if not path.is_file():
        raise RuntimeError(f"missing required file: {rel}")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise RuntimeError(f"invalid JSON: {rel}: {exc}") from exc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()

    manifest_path = "configs/research/usdjpy_research_memory_manifest_v1.json"
    manifest = load_json(root, manifest_path)

    required_files: list[str] = []
    for item in manifest.get("mandatory_startup_read_order", []):
        rel = item.get("path")
        if not isinstance(rel, str) or not rel:
            raise RuntimeError("mandatory_startup_read_order contains an invalid path")
        required_files.append(rel)
        if not (root / rel).is_file():
            raise RuntimeError(f"mandatory startup file missing: {rel}")

    pointers = manifest.get("canonical_pointers", {})
    for key, value in pointers.items():
        if not isinstance(value, str):
            raise RuntimeError(f"canonical pointer {key} is not a string")
        if value.startswith("mitsuru93/") and ":" in value:
            continue
        if not (root / value).is_file():
            raise RuntimeError(f"canonical pointer missing: {key} -> {value}")

    registry_path = pointers["current_candidate_registry"]
    contract_path = pointers["operating_contract"]
    ledger_path = pointers["hypothesis_ledger"]
    addendum_path = pointers.get("hypothesis_ledger_addendum")

    registry = load_json(root, registry_path)
    contract = load_json(root, contract_path)
    ledger = load_json(root, ledger_path)

    memory = registry.get("research_memory", {})
    if memory.get("manifest") != manifest_path:
        raise RuntimeError("latest registry does not point to the canonical memory manifest")
    if memory.get("hypothesis_ledger") != ledger_path:
        raise RuntimeError("latest registry does not point to the canonical hypothesis ledger")
    if memory.get("operating_contract") != contract_path:
        raise RuntimeError("latest registry does not point to the canonical operating contract")
    if addendum_path and memory.get("hypothesis_ledger_addendum") != addendum_path:
        raise RuntimeError("latest registry does not point to the canonical hypothesis-ledger addendum")
    if contract.get("research_memory_manifest") != manifest_path:
        raise RuntimeError("operating contract does not point to the canonical memory manifest")
    if contract.get("hypothesis_ledger") != ledger_path:
        raise RuntimeError("operating contract does not point to the canonical hypothesis ledger")

    required_entry_fields = set(ledger.get("entry_required_fields", []))
    base_entries = ledger.get("entries")
    if not isinstance(base_entries, list) or not base_entries:
        raise RuntimeError("hypothesis ledger has no entries")
    entries = list(base_entries)
    if addendum_path:
        addendum = load_json(root, addendum_path)
        if addendum.get("base_ledger") != ledger_path:
            raise RuntimeError("hypothesis-ledger addendum points to the wrong base ledger")
        addendum_entries = addendum.get("entries")
        if not isinstance(addendum_entries, list):
            raise RuntimeError("hypothesis-ledger addendum entries are not a list")
        entries.extend(addendum_entries)

    ids: set[str] = set()
    family_to_ids: dict[str, list[str]] = {}
    for row in entries:
        if not isinstance(row, dict):
            raise RuntimeError("ledger entry is not an object")
        missing = sorted(required_entry_fields - set(row))
        if missing:
            raise RuntimeError(f"ledger entry missing fields: {row.get('hypothesis_id')}: {missing}")
        hypothesis_id = row["hypothesis_id"]
        if hypothesis_id in ids:
            raise RuntimeError(f"duplicate hypothesis_id: {hypothesis_id}")
        ids.add(hypothesis_id)
        for family in row.get("family_ids", []):
            family_to_ids.setdefault(family, []).append(hypothesis_id)
        if not row.get("evidence_refs"):
            raise RuntimeError(f"ledger entry has no evidence refs: {hypothesis_id}")
        if str(row.get("status", "")).startswith("CLOSED") and not row.get("prohibited_reuse"):
            raise RuntimeError(f"closed ledger entry has no prohibited_reuse: {hypothesis_id}")

    closed_families = registry.get("closed_families", [])
    missing_families = [family for family in closed_families if family not in family_to_ids]
    if missing_families:
        raise RuntimeError(f"closed registry families absent from ledger: {missing_families}")

    open_question = registry.get("current_open_research_question")
    if open_question and open_question not in ids:
        raise RuntimeError(f"current open research question absent from ledger: {open_question}")

    snapshot = manifest.get("current_state_snapshot", {})
    if snapshot.get("registry_status") != registry.get("status"):
        raise RuntimeError("manifest registry-status snapshot is stale")
    if snapshot.get("next_action") != registry.get("next_action"):
        raise RuntimeError("manifest next-action snapshot is stale")
    if snapshot.get("current_open_research_question") != open_question:
        raise RuntimeError("manifest open-question snapshot is stale")

    result = {
        "schema_version": "usdjpy_research_memory_validation_receipt_v1",
        "status": "PASS",
        "manifest": manifest_path,
        "registry": registry_path,
        "registry_schema": registry.get("schema_version"),
        "registry_status": registry.get("status"),
        "operating_contract": contract_path,
        "hypothesis_ledger": ledger_path,
        "hypothesis_ledger_addendum": addendum_path,
        "base_hypothesis_count": len(base_entries),
        "hypothesis_count": len(entries),
        "closed_family_count": len(closed_families),
        "current_open_research_question": open_question,
        "next_action": registry.get("next_action"),
        "mandatory_startup_files": required_files,
    }

    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
