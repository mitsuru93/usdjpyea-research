#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

OLD = '''        if len(clusters):
            clusters.insert(0, "variant_id", variant)
            clusters.insert(0, "family_id", lib.VARIANT_TO_FAMILY[variant])
            loss_cluster_tables.append(clusters)
'''

NEW = '''        if len(clusters):
            clusters = clusters.copy()
            clusters["variant_id"] = variant
            clusters["family_id"] = lib.VARIANT_TO_FAMILY[variant]
            ordered_columns = ["family_id", "variant_id"] + [column for column in clusters.columns if column not in {"family_id", "variant_id"}]
            loss_cluster_tables.append(clusters.loc[:, ordered_columns])
'''


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    before = args.target.read_bytes()
    text = before.decode("utf-8")
    count = text.count(OLD)
    if count != 1:
        raise RuntimeError(f"expected exactly one table-annotation defect block, found {count}")
    repaired = text.replace(OLD, NEW, 1)
    after = repaired.encode("utf-8")
    args.target.write_bytes(after)

    receipt = {
        "schema_version": "usdjpy_csos_remaining_family_atlas_evaluator_table_annotation_patch_v1",
        "status": "PASS_TECHNICAL_TABLE_ANNOTATION_REPAIR",
        "target": args.target.name,
        "before_sha256": digest(before),
        "after_sha256": digest(after),
        "replacement_count": 1,
        "defect": "portfolio_metrics returns a mixed loss-cluster/overlap table whose overlap rows already create variant_id; inserting variant_id again raises ValueError",
        "repair": "assign the frozen variant_id to the existing column, add family_id, and order metadata columns without changing any row values used by metrics or gates",
        "scientific_contract_changed": False,
        "family_contract_changed": False,
        "source_changed": False,
        "cost_assumption_changed": False,
        "ranking_metric_changed": False,
        "shortlist_gate_changed": False,
        "trade_outcomes_changed": False,
        "partial_outcome_conditioning": False,
        "analysis_2020_2022_accessed": False,
        "external_validation_2025_accessed": False,
        "candidate_freeze_authorized": False,
        "core_mt4_authorized": False,
        "production_authorized": False,
        "live_authorized": False,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
