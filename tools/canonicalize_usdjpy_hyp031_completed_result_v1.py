#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


HYPOTHESIS_ID = "USDJPY-HYP-031"
FAMILY_ID = "S_ASIAN_RANGE_SWEEP_REGIME_ROUTING"
DECISION = "NO_PORTABLE_REGIME_RULE"
RUN_ID = 30317593695
ARTIFACT_ID = 8672872755
ARTIFACT_DIGEST = "sha256:a59aec0841568c0036e4031631e1f009a65527a1828af4290e4dbe05be7636ee"
EVALUATOR_SHA256 = "652c55d408339cf6609896071fdddcb7c50241a874e163a4a6aede1731b6fc2c"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_result(result: dict[str, Any]) -> None:
    assert result["hypothesis_id"] == HYPOTHESIS_ID
    assert result["family_id"] == FAMILY_ID
    assert result["decision_class"] == DECISION
    assert result["selected_candidate_id"] is None
    assert result["2025_accessed"] is False
    assert result["pre2023_strategy_outcomes_accessed"] is False
    assert result["authorization"] == {
        "2025": False,
        "Core": False,
        "MT4": False,
        "backward_validation": False,
    }
    assert result["audits"]["native_events"] == 544
    assert result["audits"]["canonical_events"] == 545
    assert result["audits"]["hyp030_mismatch_rows"] == 20


def update_registry(repo: Path) -> Path:
    source = repo / "configs/research/usdjpy_research_candidate_registry_v52.json"
    registry = load_json(source)
    registry["schema_version"] = "usdjpy_research_candidate_registry_v53"
    registry["supersedes"] = str(source.relative_to(repo))
    registry["status"] = (
        "USDJPY_HYP027_REMAINS_ACTIVE_HYP028_HYP029_HYP030_HYP031_CLOSED"
    )
    registry["next_action"] = (
        "Continue the separately governed HYP-027 Phase 2 sequence unchanged. "
        "HYP-031 is closed as NO_PORTABLE_REGIME_RULE: neither R1 nor R2 passed "
        "every preregistered development gate, no candidate was frozen, and "
        "2020-2022 strategy outcomes, Core/MT4 and 2025 remain unopened. "
        "HYP-028, HYP-029 and HYP-030 remain closed. Any successor requires a "
        "new Hypothesis ID and outcome-free preregistration; do not promote "
        "Long-only or alter side/regime thresholds."
    )

    hyp31 = {
        "hypothesis_id": HYPOTHESIS_ID,
        "family_id": FAMILY_ID,
        "status": "COMPLETE_NO_PORTABLE_REGIME_RULE",
        "selected_candidate_id": None,
        "tested_candidate_ids": [
            "R1_H4_SYMMETRIC_TRANSITION_BLOCK",
            "R2_D1_SYMMETRIC_TRANSITION_BLOCK",
        ],
        "diagnostics_not_candidates": [
            "HYP030_STYLE_RAW_NATIVE_BOTH",
            "LONG_ONLY_DIAGNOSTIC",
            "SHORT_ONLY_DIAGNOSTIC",
        ],
        "preregistration": (
            "configs/research/"
            "usdjpy_asian_range_sweep_directional_regime_prereg_v1.json"
        ),
        "result": (
            "configs/research/"
            "usdjpy_asian_range_sweep_regime_development_result_v1.json"
        ),
        "result_report": (
            "docs/research/USDJPY_ASIAN_RANGE_SWEEP_REGIME_ROUTING_RESULT_V1.md"
        ),
        "technical_repair_receipt": (
            "configs/research/"
            "usdjpy_asian_range_sweep_regime_technical_repair_receipt_v1.json"
        ),
        "period_access_receipt": (
            "configs/research/"
            "usdjpy_asian_range_sweep_regime_period_access_receipt_v1.json"
        ),
        "output_manifest": (
            "configs/research/"
            "usdjpy_asian_range_sweep_regime_output_manifest_v1.json"
        ),
        "scientific_run_id": RUN_ID,
        "artifact_id": ARTIFACT_ID,
        "artifact_digest": ARTIFACT_DIGEST,
        "decision": DECISION,
        "authorization": (
            "NONE_NO_BACKWARD_VALIDATION_NO_CORE_NO_MT4_NO_EXTERNAL_GATE"
        ),
        "2025_role": "NOT_ACCESSED_NOT_AUTHORIZED",
    }
    parallel = [
        row
        for row in registry.get("parallel_or_closed_studies", [])
        if row.get("hypothesis_id") != HYPOTHESIS_ID
    ]
    parallel.append(hyp31)
    registry["parallel_or_closed_studies"] = parallel

    closed_families = registry.setdefault("closed_families", [])
    if FAMILY_ID not in closed_families:
        closed_families.append(FAMILY_ID)

    closed_catalogs = [
        row
        for row in registry.get("closed_hypothesis_catalogs", [])
        if row.get("hypothesis_id") != HYPOTHESIS_ID
    ]
    closed_catalogs.append(
        {
            "hypothesis_id": HYPOTHESIS_ID,
            "catalog": "S_ASIAN_RANGE_SWEEP_REGIME_ROUTING_R1_R2_V1",
            "decision": DECISION,
            "scope": (
                "The frozen source-native R1 H4 and R2 D1 symmetric "
                "transition-block rules only. R1 failed source identity, "
                "minimum-fold and top-five-winner-removal gates; R2 additionally "
                "failed aligned Short, PF, side/regime dependency, spread and "
                "delay gates. Long-only remains diagnostic."
            ),
        }
    )
    registry["closed_hypothesis_catalogs"] = closed_catalogs
    registry.setdefault("research_memory", {})["hypothesis_ledger_addendum"] = (
        "configs/research/usdjpy_hypothesis_ledger_addendum_v27.json"
    )
    registry.setdefault("run_authorization", {}).update(
        {
            "HYP031_backward_validation": False,
            "HYP031_core_contract": False,
            "HYP031_mt4_standalone": False,
            "HYP031_mt4_integrated": False,
            "HYP031_external_2025_gate": False,
            "HYP031_production": False,
            "HYP031_live_orders": False,
        }
    )
    output = repo / "configs/research/usdjpy_research_candidate_registry_v53.json"
    dump_json(output, registry)
    return output


def write_ledger_addendum(repo: Path) -> Path:
    entry = {
        "hypothesis_id": HYPOTHESIS_ID,
        "family_ids": [FAMILY_ID],
        "candidate_ids": [
            "R1_H4_SYMMETRIC_TRANSITION_BLOCK",
            "R2_D1_SYMMETRIC_TRANSITION_BLOCK",
        ],
        "status": "COMPLETE_NO_PORTABLE_REGIME_RULE",
        "origin_analysis": (
            "HYP-030 showed Long 239 trades / +JPY13176 / PF1.579 and "
            "Short 305 trades / -JPY8653 / PF0.767 after source-native "
            "reconstruction. HYP-031 tested whether a completed-information "
            "symmetric H4 or D1 trend permission could make both aligned sides "
            "portable."
        ),
        "causal_hypothesis": (
            "Stable Up should permit Long and stable Down should permit Short, "
            "while Neutral and Transition are blocked, using same-source Raw "
            "Bid/Ask signals and completed exact H4/D1 buckets."
        ),
        "tests": [
            {
                "period": "2023H1_2023H2_2024H1_2024H2",
                "type": "source_native_directional_regime_development",
                "run_id": RUN_ID,
                "result": {
                    "decision": DECISION,
                    "native_events": 544,
                    "canonical_events": 545,
                    "common_intersection": 504,
                    "canonical_only": 41,
                    "raw_only": 40,
                    "side_disagreement": 0,
                    "ambiguous_both_side": 16,
                    "chronology_unresolved": 4,
                    "R1_net_jpy": 4841.0,
                    "R1_pf": 1.1679619734924807,
                    "R1_minimum_fold_net_jpy": -4586.0,
                    "R1_aligned_long_net_jpy": 2974.0,
                    "R1_aligned_short_net_jpy": 1867.0,
                    "R2_net_jpy": 985.0,
                    "R2_pf": 1.0341184620713644,
                    "R2_minimum_fold_net_jpy": -3227.0,
                    "R2_aligned_long_net_jpy": 3400.0,
                    "R2_aligned_short_net_jpy": -2415.0,
                },
            }
        ],
        "decision": (
            "NO_PORTABLE_REGIME_RULE. R1 produced positive aligned Long and "
            "Short but failed exact source-native identity, the preregistered "
            "minimum-fold floor and top-five-winner-removal robustness. R2 "
            "failed directional symmetry because aligned Short-Down remained "
            "negative and all positive contribution was Long-Up, with "
            "additional PF, dependency, spread, delay and concentration failures."
        ),
        "retained_findings": [
            "Raw-native signal reconstruction produced 544 executable events "
            "versus 545 canonical events.",
            "The 20 HYP-030 mismatches contributed +JPY3758 and were fully attributed.",
            "R1 showed a potentially useful but non-portable symmetric H4 pattern: "
            "Long-Up +JPY2974 and Short-Down +JPY1867.",
            "R2 remained secular-trend dependent: Long-Up +JPY3400 and "
            "Short-Down -JPY2415.",
        ],
        "prohibited_reuse": [
            "Do not promote Long-only or Short-only diagnostics.",
            "Do not retune EMA spans, transition definition, side permission, "
            "thresholds, session or period filters from this result.",
            "Do not open 2020-2022 strategy outcomes, Core/MT4 or 2025 for HYP-031.",
            "Do not relabel R1 positive aggregate economics as a passing portable candidate.",
        ],
        "evidence_refs": [
            {"repository": "mitsuru93/usdjpyea-research", "pull_request": 336},
            {
                "repository": "mitsuru93/usdjpyea-research",
                "run_id": RUN_ID,
                "artifact_id": ARTIFACT_ID,
                "artifact_digest": ARTIFACT_DIGEST,
            },
            {"repository": "mitsuru93/usdjpyea-research", "issue": 350},
        ],
    }
    ledger = {
        "schema_version": "usdjpy_hypothesis_ledger_addendum_v27",
        "status": "ACTIVE_APPEND_ONLY_DELTA",
        "entry_mode": "DELTA_INHERIT_SUPERSEDES",
        "base_ledger": "configs/research/usdjpy_hypothesis_ledger_v1.json",
        "supersedes": "configs/research/usdjpy_hypothesis_ledger_addendum_v26.json",
        "inherited_addendum": (
            "configs/research/usdjpy_hypothesis_ledger_addendum_v26.json"
        ),
        "entries": [entry],
    }
    output = repo / "configs/research/usdjpy_hypothesis_ledger_addendum_v27.json"
    dump_json(output, ledger)
    return output


def update_memory(repo: Path, registry_path: Path, ledger_path: Path) -> Path:
    path = repo / "configs/research/usdjpy_research_memory_manifest_v1.json"
    manifest = load_json(path)
    pointers = manifest["canonical_pointers"]
    pointers["current_candidate_registry"] = str(registry_path.relative_to(repo))
    pointers["hypothesis_ledger_addendum"] = str(ledger_path.relative_to(repo))
    pointers.update(
        {
            "hyp031_preregistration": (
                "configs/research/"
                "usdjpy_asian_range_sweep_directional_regime_prereg_v1.json"
            ),
            "hyp031_result": (
                "configs/research/"
                "usdjpy_asian_range_sweep_regime_development_result_v1.json"
            ),
            "hyp031_result_report": (
                "docs/research/"
                "USDJPY_ASIAN_RANGE_SWEEP_REGIME_ROUTING_RESULT_V1.md"
            ),
            "hyp031_technical_repair_receipt": (
                "configs/research/"
                "usdjpy_asian_range_sweep_regime_technical_repair_receipt_v1.json"
            ),
            "hyp031_period_access_receipt": (
                "configs/research/"
                "usdjpy_asian_range_sweep_regime_period_access_receipt_v1.json"
            ),
            "hyp031_output_manifest": (
                "configs/research/"
                "usdjpy_asian_range_sweep_regime_output_manifest_v1.json"
            ),
        }
    )
    registry = load_json(registry_path)
    snapshot = manifest["current_state_snapshot"]
    snapshot["registry_status"] = registry["status"]
    snapshot["next_action"] = registry["next_action"]
    manifest.setdefault("parallel_track_state", {})[HYPOTHESIS_ID] = {
        "family": FAMILY_ID,
        "candidate": None,
        "tested_candidates": [
            "R1_H4_SYMMETRIC_TRANSITION_BLOCK",
            "R2_D1_SYMMETRIC_TRANSITION_BLOCK",
        ],
        "status": "COMPLETE_NO_PORTABLE_REGIME_RULE",
        "decision": DECISION,
        "development_run_id": RUN_ID,
        "artifact_id": ARTIFACT_ID,
        "pre2023_strategy_outcomes_accessed": False,
        "backward_validation_authorized": False,
        "core_authorized": False,
        "mt4_authorized": False,
        "2025H1_authorized": False,
        "2025H2_authorized": False,
        "production_authorized": False,
        "live_orders_authorized": False,
        "does_not_change_HYP027": True,
    }
    dump_json(path, manifest)
    return path


def write_output_manifest(repo: Path, archive: Path, tracked: list[Path]) -> Path:
    files = tracked + sorted(path for path in archive.iterdir() if path.is_file())
    output = {
        "schema_version": "usdjpy_asian_range_sweep_regime_output_manifest_v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "decision": DECISION,
        "scientific_run_id": RUN_ID,
        "artifact_id": ARTIFACT_ID,
        "artifact_digest": ARTIFACT_DIGEST,
        "evaluator_sha256": EVALUATOR_SHA256,
        "files": [
            {
                "path": str(path.relative_to(repo)),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in files
        ],
    }
    path = (
        repo
        / "configs/research/usdjpy_asian_range_sweep_regime_output_manifest_v1.json"
    )
    dump_json(path, output)
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    source = Path(args.artifact_dir).resolve()
    result = load_json(source / "final_decision.json")
    validate_result(result)

    archive = (
        repo
        / "docs/research/artifact_archives/"
        "usdjpy_asian_range_sweep_regime_development_v1"
    )
    if archive.exists():
        shutil.rmtree(archive)
    shutil.copytree(source, archive)

    result_path = (
        repo
        / "configs/research/"
        "usdjpy_asian_range_sweep_regime_development_result_v1.json"
    )
    freeze_path = (
        repo
        / "configs/research/"
        "usdjpy_asian_range_sweep_regime_development_closure_freeze_v1.json"
    )
    dump_json(result_path, result)
    dump_json(freeze_path, load_json(source / "development_candidate_freeze.json"))

    registry_path = update_registry(repo)
    ledger_path = write_ledger_addendum(repo)
    memory_path = update_memory(repo, registry_path, ledger_path)

    tracked = [
        repo
        / "configs/research/"
        "usdjpy_asian_range_sweep_directional_regime_prereg_v1.json",
        result_path,
        freeze_path,
        repo
        / "configs/research/"
        "usdjpy_asian_range_sweep_regime_technical_repair_receipt_v1.json",
        repo
        / "configs/research/"
        "usdjpy_asian_range_sweep_regime_period_access_receipt_v1.json",
        registry_path,
        ledger_path,
        memory_path,
        repo
        / "docs/research/"
        "USDJPY_ASIAN_RANGE_SWEEP_REGIME_ROUTING_RESULT_V1.md",
        repo
        / "docs/research/"
        "USDJPY_HYP031_TECHNICAL_FAILURE_POSTMORTEM_V1.md",
    ]
    write_output_manifest(repo, archive, tracked)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
