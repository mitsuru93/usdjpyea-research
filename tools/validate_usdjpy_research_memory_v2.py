#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

REQUIRED_ENTRY_FIELDS = {
    "hypothesis_id", "family_ids", "target_failure_mode", "causal_hypothesis",
    "pre_result_predictions", "tests", "decision", "status", "retained_findings",
    "falsified_or_unsupported_claims", "prohibited_reuse", "evidence_refs",
    "successor_questions",
}
REQUIRED_STATUS_UPDATE_FIELDS = {
    "hypothesis_id", "phase2_status", "decision", "evidence_refs", "authorization"
}

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def resolve_pointer(root: Path, value: str) -> Path | None:
    if not value or ":" in value or value.startswith("http"):
        return None
    return root / value

def load_addendum_chain(root: Path, path: Path, seen: set[Path] | None = None):
    seen = seen or set()
    path = path.resolve()
    if path in seen:
        raise RuntimeError(f"addendum cycle: {path}")
    seen.add(path)
    doc = load_json(path)
    inherited = []
    parent = doc.get("inherited_addendum") or doc.get("supersedes")
    if parent:
        parent_path = root / parent
        if parent_path.exists():
            inherited = load_addendum_chain(root, parent_path, seen)["all_entries"]
    return {
        "doc": doc,
        "current_entries": doc.get("entries", []),
        "all_entries": inherited + doc.get("entries", []),
        "status_updates": doc.get("hypothesis_status_updates", []),
    }

def validate_entry(row, *, strict: bool, warnings: list[dict]):
    if not row.get("hypothesis_id"):
        raise RuntimeError("ledger entry missing hypothesis_id")
    missing = sorted(REQUIRED_ENTRY_FIELDS - set(row))
    if missing:
        if strict:
            raise RuntimeError(f"ledger entry missing fields: {row.get('hypothesis_id')}: {missing}")
        warnings.append({
            "hypothesis_id": row.get("hypothesis_id"),
            "warning": "LEGACY_INHERITED_ENTRY_MISSING_CURRENT_SCHEMA_FIELDS",
            "missing_fields": missing,
        })
    if not row.get("family_ids"):
        if strict:
            raise RuntimeError(f"ledger entry missing family_ids: {row.get('hypothesis_id')}")
        warnings.append({
            "hypothesis_id": row.get("hypothesis_id"),
            "warning": "LEGACY_ENTRY_WITHOUT_FAMILY_IDS",
        })

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    manifest_path = root / "configs/research/usdjpy_research_memory_manifest_v1.json"
    manifest = load_json(manifest_path)
    pointers = manifest["canonical_pointers"]
    missing_paths = []
    for name, value in pointers.items():
        p = resolve_pointer(root, value)
        if p is not None and not p.exists():
            missing_paths.append({"pointer": name, "path": value})
    if missing_paths:
        raise RuntimeError(f"missing canonical pointers: {missing_paths}")

    registry_path = root / pointers["current_candidate_registry"]
    ledger_path = root / pointers["hypothesis_ledger"]
    addendum_path = root / pointers["hypothesis_ledger_addendum"]
    contract_path = root / pointers["operating_contract"]
    registry, ledger, contract = map(load_json, [registry_path, ledger_path, contract_path])
    chain = load_addendum_chain(root, addendum_path)
    inherited_entries = chain["all_entries"][:-len(chain["current_entries"])] if chain["current_entries"] else chain["all_entries"]
    current_entries = chain["current_entries"]
    raw_rows = ledger.get("entries", []) + chain["all_entries"]
    warnings = []
    for row in ledger.get("entries", []):
        validate_entry(row, strict=False, warnings=warnings)
    for row in inherited_entries:
        validate_entry(row, strict=False, warnings=warnings)
    for row in current_entries:
        validate_entry(row, strict=True, warnings=warnings)

    raw_ids = [row["hypothesis_id"] for row in raw_rows]
    duplicate_ids = sorted({x for x in raw_ids if raw_ids.count(x) > 1})
    current_ids = {row["hypothesis_id"] for row in current_entries}
    duplicate_current = sorted(current_ids.intersection(duplicate_ids))
    if duplicate_current:
        raise RuntimeError(f"current delta duplicates existing hypothesis IDs: {duplicate_current}")
    if duplicate_ids:
        warnings.append({
            "warning": "LEGACY_SNAPSHOT_REPEATED_IDS_COLLAPSED_TO_LATEST",
            "hypothesis_ids": duplicate_ids,
        })
    latest_by_id = {}
    ordered_ids = []
    for row in raw_rows:
        hid = row["hypothesis_id"]
        if hid not in latest_by_id:
            ordered_ids.append(hid)
        latest_by_id[hid] = row
    rows = [latest_by_id[hid] for hid in ordered_ids]
    id_set = set(ordered_ids)
    family_to_ids = {}
    for row in rows:
        for family in row.get("family_ids", []):
            family_to_ids.setdefault(family, []).append(row["hypothesis_id"])

    for update in chain["status_updates"]:
        missing = sorted(REQUIRED_STATUS_UPDATE_FIELDS - set(update))
        if missing:
            raise RuntimeError(f"status update missing fields: {update.get('hypothesis_id')}: {missing}")
        if update["hypothesis_id"] not in id_set:
            raise RuntimeError(f"status update references unknown hypothesis: {update['hypothesis_id']}")

    unknown_closed = [f for f in registry.get("closed_families", []) if f not in family_to_ids]
    if unknown_closed:
        raise RuntimeError(f"closed families absent from ledger: {unknown_closed}")
    if registry.get("research_memory", {}).get("manifest") != str(manifest_path.relative_to(root)):
        raise RuntimeError("registry does not point to canonical manifest")
    if registry.get("research_memory", {}).get("hypothesis_ledger") != str(ledger_path.relative_to(root)):
        raise RuntimeError("registry ledger pointer mismatch")
    if registry.get("research_memory", {}).get("hypothesis_ledger_addendum") != str(addendum_path.relative_to(root)):
        raise RuntimeError("registry addendum pointer mismatch")
    if contract.get("research_memory_manifest") != str(manifest_path.relative_to(root)):
        raise RuntimeError("operating contract manifest pointer mismatch")
    if contract.get("hypothesis_ledger") != str(ledger_path.relative_to(root)):
        raise RuntimeError("operating contract ledger pointer mismatch")
    validator_name = contract.get("research_memory_validator")
    if validator_name and validator_name not in {
        "tools/validate_usdjpy_research_memory_v1.py",
        "tools/validate_usdjpy_research_memory_v2.py",
    }:
        raise RuntimeError(f"unsupported operating contract validator pointer: {validator_name}")

    snapshot = manifest["current_state_snapshot"]
    for key in ["registry_status", "next_action", "current_open_research_question"]:
        registry_key = "status" if key == "registry_status" else key
        if snapshot.get(key) != registry.get(registry_key):
            raise RuntimeError(f"manifest/registry mismatch: {key}")
    for item in manifest["mandatory_startup_read_order"]:
        if not (root / item["path"]).exists():
            raise RuntimeError(f"missing startup file: {item['path']}")

    receipt = {
        "schema_version": "usdjpy_research_memory_validation_receipt_v2",
        "status": "PASS",
        "validator": "tools/validate_usdjpy_research_memory_v2.py",
        "manifest": str(manifest_path.relative_to(root)),
        "registry": str(registry_path.relative_to(root)),
        "registry_schema": registry.get("schema_version"),
        "registry_status": registry.get("status"),
        "hypothesis_ledger": str(ledger_path.relative_to(root)),
        "hypothesis_ledger_addendum": str(addendum_path.relative_to(root)),
        "raw_entry_count": len(raw_rows),
        "hypothesis_count": len(rows),
        "status_update_count": len(chain["status_updates"]),
        "legacy_schema_warnings": warnings,
        "current_open_research_question": registry.get("current_open_research_question"),
        "next_action": registry.get("next_action"),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
