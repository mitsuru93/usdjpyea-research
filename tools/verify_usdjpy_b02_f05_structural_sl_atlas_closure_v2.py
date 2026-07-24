#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "configs/research/usdjpy_b02_f05_structural_sl_atlas_canonical_result_v2.json"
RECEIPT = ROOT / "configs/research/usdjpy_b02_f05_structural_sl_atlas_execution_receipt_v2.json"
MANIFEST = ROOT / "configs/research/usdjpy_b02_f05_structural_sl_atlas_canonical_manifest_v2.json"
REPORT = ROOT / "docs/research/USDJPY_B02_F05_structural_SL_atlas_v2.md"
PROTOCOL = ROOT / "configs/research/usdjpy_b02_f05_structural_sl_atlas_protocol_v2.json"
REMOVED = [
    ROOT / "configs/run_markers/usdjpy_structural_sl_atlas_v2_dispatch.json",
    ROOT / ".github/workflows/dispatch_usdjpy_structural_sl_atlas_v2.yml",
]


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def main() -> int:
    result = json.loads(RESULT.read_text())
    receipt = json.loads(RECEIPT.read_text())
    manifest = json.loads(MANIFEST.read_text())
    protocol = json.loads(PROTOCOL.read_text())
    report = REPORT.read_text()

    assert result["status"] == "ATLAS_COMPLETE_NO_ROBUST_FAMILY"
    assert result["population"] == {
        "B02_losers": 190,
        "B02_trades": 429,
        "F05_losers": 726,
        "F05_trades": 1453,
        "baseline_losers": 916,
        "trades": 1882,
    }
    assert result["search"]["deterministic_candidates"] == 303
    assert result["search"]["families"] == 12
    assert result["search"]["event_rows"] == 354304
    assert result["search"]["deterministic_nested_cv_rows"] == 144
    assert result["search"]["supervised_nested_cv_rows"] == 240
    assert result["search"]["unsupervised_nested_cv_rows"] == 72
    assert result["decision"]["exact_discovery_eligible"] == 0
    assert result["decision"]["nested_cv_promising_families"] == 0
    assert result["decision"]["nested_cv_promising_models"] == 0
    assert result["decision"]["nested_cv_promising_clusters"] == 0
    assert result["decision"]["candidate_frozen"] is False
    assert result["decision"]["implementation_authorized"] is False
    assert "PASS_RESEARCH_HISTORICAL_GATES" in result["decision"]["existing_F05_failed_reclaim"]

    near = result["principal_near_miss"]["candidate"]
    assert near["family"] == "CROSS_COUNT_CHOP"
    assert near["triggers"] == 256
    assert near["losers_triggered"] == 175
    assert near["winners_triggered"] == 81
    assert near["total_delta_pips"] == 1305.9
    assert near["severe1_delta_pips"] == 1049.9
    assert near["winner_damage_pips"] == -2921.5
    assert near["date_qvalue"] == 0.520776
    assert result["principal_near_miss"]["nested_cv"]["2024H2_severe1_delta_pips"] == -5.9
    assert set(result["principal_near_miss"]["rejection_reasons"]) == {
        "winner_damage_limit",
        "monthly_breadth",
        "Benjamini-Hochberg q-value",
        "2024H2 severe-cost fold",
        "no connected preliminary neighbor",
    }

    gates = {x["scope"]: x for x in result["gate_counts"]}
    assert gates["ALL"]["all_fold_default_nonnegative"] == 0
    assert gates["B02"]["all_fold_default_nonnegative"] == 2
    assert gates["F05"]["all_fold_default_nonnegative"] == 1
    assert gates["F05"]["all_fold_severe_nonnegative"] == 0
    assert all(x["date_q_le_0p1"] == 0 for x in gates.values())

    assert receipt["status"] == "PASS_CANONICAL_RESULT_READY"
    assert receipt["workflow_run_id"] == 30106687299
    assert receipt["artifact"]["id"] == 8602116809
    assert receipt["artifact"]["digest"] == "sha256:167064e9a599a83171cb6cc825609911cf7b804d0b9adec6a5750eab06b32369"
    assert receipt["independent_reproduction"]["status"] == "PASS_SEMANTIC_EXACT"
    assert receipt["boundaries"]["mt4_accessed"] is False
    assert receipt["boundaries"]["2025H1_accessed"] is False
    assert receipt["boundaries"]["2025H2_accessed"] is False

    assert protocol["status"] == "FROZEN_BEFORE_OUTCOME_EXECUTION"
    assert protocol["candidate_count"] == 303
    assert len(protocol["deterministic_families"]) == 12
    assert protocol["authorization"]["notion_task_dependency"] is False

    canonical = manifest["canonical_files"]
    assert canonical[str(RESULT.relative_to(ROOT))]["git_blob_sha1"] == blob_sha(RESULT)
    assert canonical[str(RECEIPT.relative_to(ROOT))]["git_blob_sha1"] == blob_sha(RECEIPT)
    assert canonical[str(REPORT.relative_to(ROOT))]["git_blob_sha1"] == blob_sha(REPORT)
    assert manifest["status"] == "PASS_READY_FOR_CANONICAL_VALIDATION"
    assert all(not p.exists() for p in REMOVED)

    required_report_tokens = [
        "ATLAS_COMPLETE_NO_ROBUST_FAMILY",
        "354,304",
        "F05_FAILED_RECLAIM_BASIC_V1",
        "+1,305.9 pips",
        "BH-adjusted q-value: 0.5208",
        "minimum holdout fold -843.1 pips",
        "candidate frozen: false",
    ]
    assert all(token in report for token in required_report_tokens)

    output = {
        "schema_version": "usdjpy_b02_f05_structural_sl_atlas_closure_verification_v2",
        "status": "PASS_CANONICAL_CLOSURE",
        "trade_count": 1882,
        "baseline_loser_count": 916,
        "deterministic_candidates": 303,
        "event_rows": 354304,
        "exact_discovery_eligible": 0,
        "nested_cv_promising_total": 0,
        "artifact_id": 8602116809,
        "candidate_frozen": False,
        "implementation_authorized": False,
        "mt4_accessed": False,
        "2025_accessed": False,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
