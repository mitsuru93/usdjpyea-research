#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "docs/research/artifact_archives/usdjpy_csos_shock_failure_phase2_v1"
FREEZE_PATH = ROOT / "configs/research/usdjpy_csos_shock_failure_candidate_freeze_v1.json"
CONTRACT_PATH = ROOT / "configs/research/usdjpy_csos_shock_failure_implementation_contract_v1.json"
PLAN_PATH = ROOT / "configs/research/usdjpy_csos_shock_failure_core_parity_plan_v1.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    freeze = load(FREEZE_PATH)
    contract = load(CONTRACT_PATH)
    plan = load(PLAN_PATH)
    final = load(ARCHIVE / "final_decision.json")
    mechanism = load(ARCHIVE / "shock_failure_mechanism_contract.json")

    require(final["status"] == "PASS_PORTABLE_RESEARCH_CANDIDATE", "Phase 2 status changed")
    require(final["selected_candidate"] == "B_EXECUTABLE_T0_8BAR", "Phase 2 candidate changed")
    require(freeze["candidate_id"] == final["selected_candidate"], "freeze candidate mismatch")
    require(contract["candidate_id"] == freeze["candidate_id"], "contract candidate mismatch")
    require(plan["candidate_id"] == freeze["candidate_id"], "plan candidate mismatch")

    auth = freeze["authority"]
    expected_hashes = {
        "event_identity_ledger.csv": auth["event_identity_ledger_sha256"],
        "candidate_trade_ledger.csv.gz": auth["candidate_trade_ledger_gzip_sha256"],
        "shock_failure_mechanism_contract.json": auth["mechanism_contract_sha256"],
        "final_decision.json": auth["final_decision_sha256"],
    }
    for filename, expected in expected_hashes.items():
        require(sha256(ARCHIVE / filename) == expected, f"archive digest mismatch: {filename}")

    candidate = next(x for x in mechanism["candidate_catalog"] if x["candidate_id"] == freeze["candidate_id"])
    require(candidate["entry"] == "first raw tick timestamp >= failure_bar_end; LONG at Ask, SHORT at Bid", "entry mechanism changed")
    require(candidate["exit"] == "first raw tick timestamp >= entry_boundary_plus_120_minutes; LONG at Bid, SHORT at Ask", "exit mechanism changed")
    require(candidate["stop"] == "none" and candidate["timeout"] == "120 minutes", "exit controls changed")

    sem = freeze["frozen_semantics"]
    require(sem["rolling_reference"]["window_observed_bars"] == 96, "rolling window changed")
    require(sem["rolling_reference"]["includes_current_shock_bar"] is True, "rolling inclusion changed")
    require(sem["shock"]["tr_ratio_minimum"] == 2.5, "shock threshold changed")
    require(sem["shock"]["body_to_true_range_minimum"] == 0.65, "body threshold changed")
    require(sem["exit"]["not_measured_from_actual_fill"] is True, "exit anchor changed")
    require("j <= i + 9" in sem["reentry_suppression"]["exact_rule"], "reentry rule changed")

    for obj, label in [(freeze["research_scope"], "freeze"), (contract["authorization"], "contract"), (plan["authorization"], "plan")]:
        for key, value in obj.items():
            if key in {"core_changed", "mt4_accessed", "production_authorized", "core_source_change", "mt4_execution", "2025_access", "production", "live_orders", "core_source_change", "mt4", "2025"}:
                require(value is False, f"unauthorized flag enabled: {label}.{key}")
    require(freeze["research_scope"]["2025H1_accessed"] is False, "2025H1 accessed")
    require(freeze["research_scope"]["2025H2_accessed"] is False, "2025H2 accessed")

    stages = {x["stage"]: x for x in plan["stages"]}
    require(list(stages) == [
        "P0_RESEARCH_CONTRACT_VALIDATION",
        "P1_CORE_SHADOW_FORMULA_PARITY",
        "P2_RAW_TICK_EXECUTION_PARITY",
        "P3_RAKUTEN_BROKER_SOURCE_PORTABILITY",
        "P4_STANDALONE_MT4_PARITY",
        "P5_PORTFOLIO_INTEGRATION_PARITY",
        "P6_2025_GATE_APPLICATION",
    ], "parity stage order changed")
    require(stages["P0_RESEARCH_CONTRACT_VALIDATION"]["authorized_now"] is True, "P0 must be authorized")
    for name in list(stages)[1:]:
        require(stages[name]["authorized_now"] is False, f"downstream stage unexpectedly authorized: {name}")

    gates = stages["P3_RAKUTEN_BROKER_SOURCE_PORTABILITY"]["preregistered_gates"]
    require(gates["2023_expected_events"] == 56, "2023 authority count changed")
    require(gates["2024H1_canonical_recall_min"] == 0.80, "2024H1 recall gate changed")
    require(gates["2024H2_canonical_recall_min"] == 0.80, "2024H2 recall gate changed")
    require(gates["matched_side_agreement"] == 1.0, "side agreement gate changed")

    receipt = {
        "status": "PASS_SHOCK_FAILURE_CONTRACT_VALIDATION",
        "candidate_id": freeze["candidate_id"],
        "phase2_scientific_merge": auth["scientific_merge_commit"],
        "archive_files_verified": sorted(expected_hashes),
        "downstream_core_mt4_2025_authorized": False,
    }
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
