#!/usr/bin/env python3
"""Verify the canonical B02/F05 all-loss structural-SL closure package."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "configs/research/usdjpy_b02_f05_all_loss_structural_sl_output_manifest_v1.json"
RESULT = ROOT / "configs/research/usdjpy_b02_f05_all_loss_structural_sl_result_v1.json"
RECEIPT = ROOT / "configs/research/usdjpy_b02_f05_all_loss_structural_sl_execution_receipt_v1.json"
SUMMARY = ROOT / "configs/research/usdjpy_b02_f05_all_loss_structural_sl_event_summary_v1.csv"
REPORT = ROOT / "docs/research/USDJPY_B02_F05_all_loss_structural_SL_v1.md"
PROTOCOL = ROOT / "configs/research/usdjpy_b02_f05_all_loss_structural_sl_protocol_v1.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: Path) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(path.relative_to(ROOT))], cwd=ROOT, text=True
    ).strip()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    result = json.loads(RESULT.read_text())
    receipt = json.loads(RECEIPT.read_text())
    protocol = json.loads(PROTOCOL.read_text())

    require(manifest["status"] == "PASS_READY_FOR_CANONICAL_VALIDATION", "manifest status")
    require(manifest["decision"] == "DESCRIPTIVE_COMPLETE_NO_CANDIDATE_FROZEN", "manifest decision")

    for rel, identity in manifest["canonical_files"].items():
        path = ROOT / rel
        require(path.is_file(), f"missing canonical file: {rel}")
        require(git_blob(path) == identity["git_blob_sha1"], f"git blob mismatch: {rel}")
        if "sha256" in identity:
            require(sha256(path) == identity["sha256"], f"SHA-256 mismatch: {rel}")

    require(result["schema_version"] == "usdjpy_b02_f05_all_loss_structural_sl_result_v1", "result schema")
    require(result["status"] == "DESCRIPTIVE_COMPLETE_NO_CANDIDATE_FROZEN", "result status")
    require(result["research_commit"] == "b1bb2d4fd12d6dc7722f30a6da8ad18c7a387309", "evaluation commit")
    require(result["workflow_run_id"] == 30101951761, "run id")
    require(result["population"]["trade_count"] == 1882, "trade count")
    require(result["population"]["baseline_loser_count"] == 916, "loser count")
    require(result["population"]["counts"] == {
        "2023H1": {"B02": 121, "F05": 367},
        "2023H2": {"B02": 109, "F05": 363},
        "2024H1": {"B02": 97, "F05": 331},
        "2024H2": {"B02": 102, "F05": 392},
    }, "fold/strategy counts")

    decision = result["decision"]
    require(decision["overall_status"] == "DESCRIPTIVE_COMPLETE_NO_CANDIDATE_FROZEN", "overall decision")
    require(decision["shared_b02_f05_rule"]["status"] == "REJECT_SHARED_STOP_ARCHITECTURE", "shared rule")
    require(decision["f05_failed_reclaim"]["status"] == "PROMISING_EXPLORATORY_MECHANISM_NOT_CONFIRMATORY", "F05 decision")
    require(decision["b02"]["status"] == "NO_ROBUST_STRUCTURAL_STOP_FOUND", "B02 decision")
    require(decision["profit_armed_generic_termination"]["status"] == "REJECTED_AS_OVERBROAD", "profit-armed decision")
    require(not decision["implementation_authorized"], "implementation authorization")
    require(not decision["mt4_authorized"], "MT4 authorization")
    require(not decision["2025_authorized"], "2025 authorization")

    boundaries = result["boundaries"]
    for key in [
        "fixed_pip_stop_evaluated", "mt4_accessed", "2025H1_accessed",
        "2025H2_accessed", "implementation_authorized", "candidate_frozen",
        "notion_used_as_task_source",
    ]:
        require(boundaries[key] is False, f"boundary must be false: {key}")
    require(boundaries["portfolio_replay_computed"] is True, "portfolio replay boundary")

    expected_sha = {
        "m15_2023": "4c10ab3244996d73d0955850675231a533f918da09a41ac642c9a3e287b7ac78",
        "m1_2023": "167509bde6553a468ffe48b082ed79de183cc57991f668cf4b3e7341350d307e",
        "events_2024h1": "9560d6382e2457eaec83415316fb59d4989244d49c9977ce76cbdd717f32f09a",
        "events_2024h2": "a5a871d7105c6e68548e804c9ab517ee6bc0b08553474b158799f47ebd32edcd",
        "m1_2024": "f9f56be2daa39f07dc39cec197306fb87821ead01e4a640a73f17715bf27dde0",
    }
    require(result["source_sha256"] == expected_sha, "source identity")

    events = result["event_summary"]
    require(len(events) == 7, "event family count")
    focal = events["SHARED_FAILED_RECLAIM_STRICT_NO_PROFIT_V1"]
    f05 = focal["by_strategy"]["F05"]
    b02 = focal["by_strategy"]["B02"]
    require((f05["triggers"], f05["losers_triggered"], f05["winners_triggered"]) == (15, 11, 4), "F05 focal counts")
    require(f05["total_delta_pips"] == 200.6, "F05 focal total")
    require(f05["loser_benefit_pips"] == 285.5, "F05 loser benefit")
    require(f05["winner_damage_pips"] == -84.9, "F05 winner damage")
    require(f05["fold_delta_pips"] == {"2023H1": 69.3, "2023H2": 14.1, "2024H1": 110.7, "2024H2": 6.5}, "F05 folds")
    require(f05["direction_delta_pips"] == {"long": 65.2, "short": 135.4}, "F05 directions")
    require(f05["negative_fold_strategy_direction_cells"] == 1, "F05 negative cell")
    require(f05["delta_after_best_date_removed_pips"] == 134.4, "F05 date removal")
    require(b02["total_delta_pips"] == -16.9, "B02 focal total")

    generic = events["PROFIT_ARMED_M5_RANGE_FAILURE_V1"]["overall"]
    require(generic["triggers"] == 1481, "generic triggers")
    require(generic["total_delta_pips"] == -2052.2, "generic total")
    require(generic["loser_benefit_pips"] == 26707.9, "generic loser benefit")
    require(generic["winner_damage_pips"] == -28760.1, "generic winner damage")

    with SUMMARY.open(newline="") as f:
        rows = list(csv.DictReader(f))
    require(len(rows) == 7, "summary row count")
    for row in rows:
        event = events[row["event_id"]]["overall"]
        require(int(row["triggers"]) == event["triggers"], f"summary triggers: {row['event_id']}")
        require(int(row["losers_triggered"]) == event["losers_triggered"], f"summary losers: {row['event_id']}")
        require(int(row["winners_triggered"]) == event["winners_triggered"], f"summary winners: {row['event_id']}")
        require(float(row["total_delta_pips"]) == event["total_delta_pips"], f"summary delta: {row['event_id']}")

    require(receipt["status"] == "PASS_CANONICAL_RESULT_READY", "receipt status")
    require(receipt["workflow_run_id"] == 30101951761, "receipt run")
    require(receipt["artifact"]["id"] == 8599982482, "receipt artifact")
    require(receipt["artifact"]["digest"] == "sha256:203e0bcba871d40e7f3f3863a963fdc24f3f3a782f9cf16206cbdb7ad08bbcd7", "receipt digest")
    require(receipt["independent_artifact_readback"]["result_v1.json"]["sha256"] == "c6b9b1436cb8cdae4d46fe8859d961955cc6d41254f756e050f0b8077b1fd4e9", "artifact result hash")

    require(protocol["status"] == "FROZEN_BEFORE_OUTCOME_EXECUTION", "protocol status")
    require(protocol["population"]["trade_count"] == 1882, "protocol population")
    require(len(protocol["event_family"]["event_ids"]) == 7, "protocol events")

    report = REPORT.read_text()
    for text in [
        "REJECT_SHARED_STOP_ARCHITECTURE",
        "PROMISING_EXPLORATORY_MECHANISM_NOT_CONFIRMATORY",
        "NO_ROBUST_STRUCTURAL_STOP_FOUND",
        "REJECTED_AS_OVERBROAD",
    ]:
        require(text in report, f"report missing: {text}")

    for rel in manifest["cleanup"]["removed_run_markers"]:
        require(not (ROOT / rel).exists(), f"obsolete marker remains: {rel}")
    removed_workflow = manifest["cleanup"]["removed_obsolete_signed_transfer_workflow"]
    require(not (ROOT / removed_workflow).exists(), "obsolete signed workflow remains")

    output = {
        "schema_version": "usdjpy_b02_f05_all_loss_structural_sl_closure_verification_v1",
        "status": "PASS_CANONICAL_CLOSURE",
        "trade_count": 1882,
        "baseline_loser_count": 916,
        "event_count": 7,
        "workflow_run_id": 30101951761,
        "candidate_frozen": False,
        "mt4_accessed": False,
        "2025_accessed": False,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
